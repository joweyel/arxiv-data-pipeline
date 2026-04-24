import os
import re
import json
from datetime import datetime, date
import pandas as pd
from google.cloud import storage, bigquery


def parse_blob_path(name: str) -> tuple[str, str] | None:
    """Return (category, YYYYMM) for 'raw/arxiv/{cat}/{YYYYMM}.ndjson', else None."""
    if not name.startswith("raw/arxiv/") or not name.endswith(".ndjson"):
        return None
    inner = name[len("raw/arxiv/") : -len(".ndjson")]  # e.g. "cs.CV/202603"
    if "/" not in inner:
        return None  # flat file, skip
    cat, yyyymm = inner.rsplit("/", 1)
    if not yyyymm.isdigit() or len(yyyymm) != 6:
        return None
    return cat, yyyymm


GCS_BUCKET_NAME: str = os.getenv("GCS_BUCKET")
GCP_PROJECT_ID: str = os.getenv("GCP_PROJECT_ID")
BQ_DATASET: str = os.getenv("BQ_DATASET", "raw")
CATEGORIES: set[str] = set(os.getenv("CATEGORIES", "cs.CV,cs.RO,cs.LG").split(","))
START_YEAR: int = int(os.getenv("START_YEAR", "2000"))
END_YEAR: int = int(os.getenv("END_YEAR", "2100"))
START_MONTH: int = int(os.getenv("START_MONTH", "1"))
END_MONTH: int = int(os.getenv("END_MONTH", "12"))
START_PERIOD: int = START_YEAR * 100 + START_MONTH
END_PERIOD: int = END_YEAR * 100 + END_MONTH
BULK_LOAD: bool = os.getenv("BULK_LOAD", "true").lower() == "true"

# Regular Expressions for information extraction
CODE_RE = re.compile(r"github\.com", re.IGNORECASE)
SURVEY_RE = re.compile(r"\bsurvey\b", re.IGNORECASE)

SCHEMA: list[bigquery.SchemaField] = [
    bigquery.SchemaField("arxiv_id", "STRING"),
    bigquery.SchemaField("title", "STRING"),
    bigquery.SchemaField("abstract", "STRING"),
    bigquery.SchemaField("authors", "STRING", mode="REPEATED"),
    bigquery.SchemaField("primary_category", "STRING"),
    bigquery.SchemaField("all_categories", "STRING", mode="REPEATED"),
    bigquery.SchemaField("version", "INTEGER"),
    bigquery.SchemaField("doi", "STRING"),
    bigquery.SchemaField("journal_ref", "STRING"),
    bigquery.SchemaField("comment", "STRING"),
    bigquery.SchemaField("date_published", "DATE"),
    bigquery.SchemaField("date_updated", "DATE"),
    bigquery.SchemaField("submission_year", "INTEGER"),
    bigquery.SchemaField("submission_month", "INTEGER"),
    bigquery.SchemaField("has_code", "BOOL"),
    bigquery.SchemaField("is_survey", "BOOL"),
]

UPDATE_COLUMNS: list[str] = [col.name for col in SCHEMA if col.name != "arxiv_id"]


def parse_date(iso_date: str) -> str:
    """Parse ISO 8601 to Arxiv time format YYYYMMDDHHMM.

    Output-format: "202401150600"

    Parameters
    ----------
    iso_date: str
        Timestamp in iso 8601 format like "2024-01-15T06:00:00.983335847Z".

    Returns
    -------
    str
        Timestamp in ArXiv foramt required for querying the database "202401150600".
    """
    dt = datetime.strptime(iso_date[:16], "%Y-%m-%dT%H:%M")
    return dt.strftime("%Y%m%d%H%M")


def blob_exists_gcs(storage_client: storage.Client, destination_blob_name: str) -> bool:
    """Check if blob/file exists at specified path in gcs bucket."""
    return storage_client.bucket(GCS_BUCKET_NAME).blob(destination_blob_name).exists()


def load_from_gcs(
    storage_client: storage.Client,
    destination_blob_name: str,
) -> list[dict]:
    """Download and parse an NDJSON blob from GCS.

    Parameters
    ----------
    storage_client: storage.Client
        Authenticated GCS client.
    destination_blob_name: str
        Path to the blob in the bucket (e.g. "raw/arxiv/202604.ndjson").

    Returns
    -------
    list[dict]
        List of parsed paper dicts.
    """
    bucket = storage_client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(destination_blob_name)
    content = blob.download_as_text(encoding="utf-8")
    return [
        json.loads(data_entry)
        for data_entry in content.splitlines()
        if data_entry.strip()
    ]  # parses ndjson data with splitlines


def add_columns(paper: dict) -> dict:
    """Adds derived columns to the previously extracted
    raw data

    Parameters
    ----------
    paper: dict
        Raw paper data.

    Returns
    -------
    dict
        Augmented / extended paper entry.
    """
    title: str = paper.get("title") or ""
    comment: str = paper.get("comment") or ""
    abstract: str = paper.get("abstract") or ""
    has_code_in_comment: bool = bool(CODE_RE.search(comment))
    has_code_in_abstract: bool = bool(CODE_RE.search(abstract))
    is_survey_in_title: bool = bool(SURVEY_RE.search(title))

    published_str = paper.get("published") or ""
    date_published = (
        date.fromisoformat(published_str[:10]) if published_str else date.today()
    )

    paper_extended: dict = {
        **paper,
        "date_published": date_published.isoformat(),
        "date_updated": paper["updated"][:10],
        "submission_year": date_published.year,
        "submission_month": date_published.month,
        "has_code": has_code_in_comment or has_code_in_abstract,
        "is_survey": is_survey_in_title,
    }
    return paper_extended


def merge_data_bigquery(
    bq_client: bigquery.Client,
    rows: list[dict],
    data_date: str,
) -> None:
    """Load augmented paper rows into a temp table and MERGE into raw.papers.

    Parameters
    ----------
    bq_client: bigquery.Client
        Authenticated BigQuery client.
    rows: list[dict]
        Augmented paper dicts (output of add_columns).
    data_date: str
        YYYYMM string used to name the temp table and identify the batch.
    """
    tmp_table: str = f"{GCP_PROJECT_ID}.{BQ_DATASET}.tmp_papers_{data_date}"
    destination_table: str = f"{GCP_PROJECT_ID}.{BQ_DATASET}.papers"

    df = pd.DataFrame(rows).drop(columns=["published", "updated"], errors="ignore")
    df["date_published"] = pd.to_datetime(df["date_published"]).dt.date
    df["date_updated"] = pd.to_datetime(df["date_updated"]).dt.date
    df = df.sort_values("date_updated").drop_duplicates(
        subset=["arxiv_id"], keep="last"
    )

    job = bq_client.load_table_from_dataframe(
        df,
        destination=tmp_table,
        job_config=bigquery.LoadJobConfig(
            schema=SCHEMA,
            write_disposition="WRITE_TRUNCATE",
        ),
    )
    job.result()
    print(f"Staged [{len(df)}] rows to table: [{tmp_table}]")

    # Column names of the used destination schema
    column_names = [col.name for col in SCHEMA]

    # Update value assignments from tmp_table -> destination_table
    update_set = ",\n".join(f"T.{col} = S.{col}" for col in UPDATE_COLUMNS)

    # List of column names in which data is inserted into
    column_names_insert = ", ".join(column_names)

    # List of values from the `tmp_table` table to be inserted
    column_names_values = ", ".join(f"S.{col}" for col in column_names)

    merge_query: str = f"""
        MERGE INTO `{destination_table}` AS T
        USING `{tmp_table}` AS S
          ON T.arxiv_id = S.arxiv_id
        WHEN MATCHED THEN UPDATE SET
          {update_set}
        WHEN NOT MATCHED THEN
          INSERT ({column_names_insert})
          VALUES ({column_names_values})
    """
    table = bigquery.Table(destination_table, schema=SCHEMA)
    table.time_partitioning = bigquery.TimePartitioning(
        type_=bigquery.TimePartitioningType.MONTH,
        field="date_published",
    )
    table.clustering_fields = ["primary_category"]
    bq_client.create_table(table, exists_ok=True)
    bq_client.query(merge_query).result()
    print(f"MERGE completed to {destination_table}")

    bq_client.delete_table(tmp_table)


def load_month(
    storage_client: storage.Client,
    bq_client: bigquery.Client,
    data_date: str,
) -> None:
    """Load all category NDJSON files for one month from GCS and MERGE into BigQuery.

    Parameters
    ----------
    storage_client: storage.Client
        Authenticated GCS client.
    bq_client: bigquery.Client
        Authenticated BigQuery client.
    data_date: str
        Month identifier in YYYYMM format (e.g. "202201").
    """
    blobs_for_month = [
        b.name
        for b in storage_client.list_blobs(GCS_BUCKET_NAME, prefix="raw/arxiv/")
        if (parsed := parse_blob_path(b.name)) is not None
        and parsed[0] in CATEGORIES
        and parsed[1] == data_date
    ]
    if not blobs_for_month:
        print(f"Skip {data_date} (not in GCS)")
        return
    all_papers = []
    for blob_name in blobs_for_month:
        print(f"Loading {blob_name}", flush=True)
        all_papers.extend(load_from_gcs(storage_client, blob_name))
    rows = [add_columns(paper) for paper in all_papers]
    merge_data_bigquery(bq_client, rows, data_date)
    print(f"DONE: {len(rows)} papers for {data_date}")


def main():
    storage_client = storage.Client()
    bq_client = bigquery.Client(project=GCP_PROJECT_ID)

    if "START_DATE" not in os.environ:

        def in_scope(name: str) -> bool:
            parsed = parse_blob_path(name)
            if parsed is None:
                return False
            cat, yyyymm = parsed
            return cat in CATEGORIES and START_PERIOD <= int(yyyymm) <= END_PERIOD

        blobs = sorted(
            b.name
            for b in storage_client.list_blobs(GCS_BUCKET_NAME, prefix="raw/arxiv/")
            if in_scope(b.name)
        )
        print(
            f"Found {len(blobs)} monthly files for categories {sorted(CATEGORIES)}.",
            flush=True,
        )
        if BULK_LOAD:
            # Collect all rows into memory, then do a single MERGE (faster, higher RAM)
            all_rows = []
            for name in blobs:
                papers = load_from_gcs(storage_client, name)
                all_rows.extend(add_columns(p) for p in papers)
            print(f"Total rows: {len(all_rows)}", flush=True)
            merge_data_bigquery(bq_client, all_rows, "bulk")
        else:
            # One MERGE per unique month (slower, lower RAM -- use on memory-constrained VMs)
            months_seen = sorted(
                {name.split("/")[-1].replace(".ndjson", "") for name in blobs}
            )
            for data_date in months_seen:
                load_month(storage_client, bq_client, data_date)
    else:
        # Single-month mode: load exactly the month derived from START_DATE
        start_date: str = parse_date(os.environ["START_DATE"])
        data_date: str = start_date[:6]
        load_month(storage_client, bq_client, data_date)


if __name__ == "__main__":
    main()
