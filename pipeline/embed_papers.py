import os
import torch
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from google.cloud import bigquery
from transformers import AutoTokenizer, AutoModel
from tqdm import tqdm

GCP_PROJECT_ID: str = os.environ["GCP_PROJECT_ID"]
BQ_DATASET: str = os.getenv("BQ_DATASET", "ingestion_dataset")
BATCH_SIZE: int = int(os.getenv("BATCH_SIZE", "32"))
TOP_N_KEYWORDS: int = int(os.getenv("TOP_N_KEYWORDS", "8"))
BACKFILL_ALL: bool = os.getenv("BACKFILL_ALL", "").lower() == "true"
MODEL_ID: str = "allenai/specter2_base"
PWC_TASKS_CSV: str = os.path.join(os.path.dirname(__file__), "data", "pwc_tasks.csv")

KEYWORDS_TABLE: str = "paper_keywords"
EMBEDDINGS_TABLE: str = "paper_embeddings"

KEYWORDS_SCHEMA = [
    bigquery.SchemaField("arxiv_id", "STRING"),
    bigquery.SchemaField("keyword", "STRING"),
    bigquery.SchemaField("score", "FLOAT64"),
    bigquery.SchemaField("extracted_at", "TIMESTAMP"),
]

EMBEDDINGS_SCHEMA = [
    bigquery.SchemaField("arxiv_id", "STRING"),
    bigquery.SchemaField("keywords", "STRING", mode="REPEATED"),
    bigquery.SchemaField("embedding", "FLOAT64", mode="REPEATED"),
    bigquery.SchemaField("model_version", "STRING"),
    bigquery.SchemaField("embedded_at", "TIMESTAMP"),
]


def load_pwc_candidates() -> list[str]:
    """Load PwC task titles from the local CSV file."""
    df = pd.read_csv(PWC_TASKS_CSV, usecols=["title"])
    candidates = df["title"].dropna().str.strip().str.lower().unique().tolist()
    print(f"Loaded {len(candidates)} PwC task candidates from {PWC_TASKS_CSV}")
    return sorted(candidates)


def load_model(device: torch.device):
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    model = AutoModel.from_pretrained(MODEL_ID).to(device)
    model.eval()
    return tokenizer, model


@torch.no_grad()
def encode_texts(
    texts: list[str], tokenizer, model, device: torch.device
) -> np.ndarray:
    """Encode a list of texts to CLS-token embeddings. Returns (N, 768) float32 array."""
    inputs = tokenizer(
        texts,
        padding=True,
        truncation=True,
        max_length=512,
        return_tensors="pt",
    ).to(device)
    outputs = model(**inputs)
    embeddings = outputs.last_hidden_state[:, 0, :]  # CLS token
    return embeddings.cpu().float().numpy()


def cosine_similarity(doc_emb: np.ndarray, candidate_embs: np.ndarray) -> np.ndarray:
    doc_norm = doc_emb / (np.linalg.norm(doc_emb) + 1e-10)
    cand_norms = candidate_embs / (
        np.linalg.norm(candidate_embs, axis=1, keepdims=True) + 1e-10
    )
    return cand_norms @ doc_norm


def top_keywords(
    doc_emb: np.ndarray,
    candidate_embs: np.ndarray,
    candidates: list[str],
    top_n: int,
) -> list[tuple[str, float]]:
    scores = cosine_similarity(doc_emb, candidate_embs)
    top_idx = np.argpartition(scores, -top_n)[-top_n:]
    top_idx = top_idx[np.argsort(scores[top_idx])[::-1]]
    return [(candidates[i], float(scores[i])) for i in top_idx]


def fetch_papers_without_embeddings(bq_client: bigquery.Client) -> pd.DataFrame:
    if BACKFILL_ALL:
        query = f"""
            SELECT arxiv_id, title, abstract
            FROM `{GCP_PROJECT_ID}.{BQ_DATASET}.papers`
        """
    else:
        query = f"""
            SELECT p.arxiv_id, p.title, p.abstract
            FROM `{GCP_PROJECT_ID}.{BQ_DATASET}.papers` p
            LEFT JOIN `{GCP_PROJECT_ID}.{BQ_DATASET}.{EMBEDDINGS_TABLE}` e
              ON p.arxiv_id = e.arxiv_id
            WHERE e.arxiv_id IS NULL
        """
    return bq_client.query(query).to_dataframe()


def ensure_tables(bq_client: bigquery.Client) -> None:
    for table_id, schema in [
        (KEYWORDS_TABLE, KEYWORDS_SCHEMA),
        (EMBEDDINGS_TABLE, EMBEDDINGS_SCHEMA),
    ]:
        ref = f"{GCP_PROJECT_ID}.{BQ_DATASET}.{table_id}"
        table = bigquery.Table(ref, schema=schema)
        bq_client.create_table(table, exists_ok=True)


def write_batch(
    bq_client: bigquery.Client,
    keyword_rows: list[dict],
    embedding_rows: list[dict],
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    for row in keyword_rows:
        row["extracted_at"] = now
    for row in embedding_rows:
        row["embedded_at"] = now

    for table_id, rows, schema in [
        (KEYWORDS_TABLE, keyword_rows, KEYWORDS_SCHEMA),
        (EMBEDDINGS_TABLE, embedding_rows, EMBEDDINGS_SCHEMA),
    ]:
        if not rows:
            continue
        df = pd.DataFrame(rows)
        ref = f"{GCP_PROJECT_ID}.{BQ_DATASET}.{table_id}"
        job = bq_client.load_table_from_dataframe(
            df,
            destination=ref,
            job_config=bigquery.LoadJobConfig(
                schema=schema,
                write_disposition="WRITE_APPEND",
            ),
        )
        job.result()


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    candidates = load_pwc_candidates()

    print("Loading SPECTER2 model ...")
    tokenizer, model = load_model(device)

    print("Pre-computing candidate embeddings ...")
    cand_embs = []
    for i in tqdm(range(0, len(candidates), 256), desc="Encoding candidates"):
        batch = candidates[i : i + 256]
        cand_embs.append(encode_texts(batch, tokenizer, model, device))
    candidate_embs = np.vstack(cand_embs)

    bq_client = bigquery.Client(project=GCP_PROJECT_ID)
    ensure_tables(bq_client)

    print("Fetching papers without embeddings from BigQuery ...")
    papers_df = fetch_papers_without_embeddings(bq_client)
    print(f"Papers to process: {len(papers_df)}")

    if papers_df.empty:
        print("Nothing to do.")
        return

    keyword_rows: list[dict] = []
    embedding_rows: list[dict] = []

    for i in tqdm(range(0, len(papers_df), BATCH_SIZE), desc="Embedding papers"):
        batch = papers_df.iloc[i : i + BATCH_SIZE]

        # Pass 1: title + abstract
        pass1_texts = [
            row.title + tokenizer.sep_token + (row.abstract or "")
            for row in batch.itertuples()
        ]
        pass1_embs = encode_texts(pass1_texts, tokenizer, model, device)

        # Extract PwC keywords per paper using pass 1 embeddings
        batch_keywords: list[list[tuple[str, float]]] = []
        for doc_emb in pass1_embs:
            kws = top_keywords(doc_emb, candidate_embs, candidates, TOP_N_KEYWORDS)
            batch_keywords.append(kws)

        # Pass 2: title + abstract + keywords
        pass2_texts = [
            row.title
            + tokenizer.sep_token
            + (row.abstract or "")
            + tokenizer.sep_token
            + " ".join(kw for kw, _ in kws)
            for row, kws in zip(batch.itertuples(), batch_keywords)
        ]
        pass2_embs = encode_texts(pass2_texts, tokenizer, model, device)

        for row, kws, final_emb in zip(batch.itertuples(), batch_keywords, pass2_embs):
            for kw, score in kws:
                keyword_rows.append(
                    {"arxiv_id": row.arxiv_id, "keyword": kw, "score": score}
                )
            embedding_rows.append(
                {
                    "arxiv_id": row.arxiv_id,
                    "keywords": [kw for kw, _ in kws],
                    "embedding": final_emb.tolist(),
                    "model_version": MODEL_ID,
                }
            )

        # Write to BQ every 512 papers to avoid large in-memory accumulation
        if len(embedding_rows) >= 512:
            write_batch(bq_client, keyword_rows, embedding_rows)
            keyword_rows.clear()
            embedding_rows.clear()

    # Write remaining rows
    if embedding_rows:
        write_batch(bq_client, keyword_rows, embedding_rows)

    print(f"Done. Processed {len(papers_df)} papers.")


if __name__ == "__main__":
    main()
