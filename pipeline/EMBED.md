# Paper Embedding Pipeline

Generates semantic embeddings and PwC keyword mappings for all arXiv papers in the dataset using [SPECTER2](https://huggingface.co/allenai/specter2_base) with the [proximity adapter](https://huggingface.co/allenai/specter2).

## What it does

Two-pass pipeline per paper:

1. **Pass 1**: encode `title + abstract` with SPECTER2 + proximity adapter, then match against the Papers with Code task taxonomy using cosine similarity to extract the top-N most relevant task keywords
2. **Pass 2**: encode `title + abstract + keywords` to produce a final embedding enriched with the keyword signal

Source table: `arxiv_dataset.fct_papers_embeddings`

Outputs written to `arxiv_dataset`:

- `paper_keywords`: one row per keyword per paper (`arxiv_id`, `keyword`, `score`, `extracted_at`)
- `paper_embeddings`: one row per paper (`arxiv_id`, `keywords`, `embedding`, `model_version`, `embedded_at`)

The 768-dimensional embeddings can be used for semantic search via BigQuery `VECTOR_SEARCH`, RAG pipelines, or clustering. Join both tables with `fct_papers` to get full paper metadata.

## Running locally (GPU)

```bash
BACKFILL_ALL=true ./pipeline/run_embed_gpu.sh
```

For incremental runs (only papers not yet embedded):

```bash
./pipeline/run_embed_gpu.sh
```

## Environment variables

| Variable         | Default         | Description                                                           |
| ---------------- | --------------- | --------------------------------------------------------------------- |
| `GCP_PROJECT_ID` | required        | GCP project ID                                                        |
| `BQ_DATASET`     | `arxiv_dataset` | BigQuery dataset for output tables                                    |
| `BATCH_SIZE`     | `128`           | Papers per GPU batch                                                  |
| `TOP_N_KEYWORDS` | `8`             | PwC keywords to extract per paper                                     |
| `BACKFILL_ALL`   | ``              | Set to `true` to process all papers regardless of existing embeddings |

## PwC candidate list

The candidate pool consists of 5101 task names from the Papers with Code taxonomy, sourced from the [J0nasW/paperswithcode](https://huggingface.co/datasets/J0nasW/paperswithcode) HuggingFace dataset (a third-party export preserved before PwC was shut down in July 2025). Stored locally in `pipeline/data/pwc_tasks.csv`. All candidates are encoded once with SPECTER2 at startup. For each paper, the top-N candidates with highest cosine similarity to the paper embedding are selected as keywords.
