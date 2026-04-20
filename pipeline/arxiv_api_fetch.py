import os
import re
import json
from datetime import datetime

import arxiv
from google.cloud import storage

GCS_BUCKET_NAME: str = os.getenv("GCS_BUCKET")
CATEGORIES: list[str] = os.getenv("CATEGORIES", "cs.CV,cs.RO").split(",")
MAX_RESULTS = int(os.getenv("MAX_RESULTS", 0)) or float("inf")
FORCE_FETCH: bool = os.getenv("FORCE_FETCH", "").lower() == "true"

# Arxiv Client Parameters
PAGE_SIZE: int = int(os.getenv("PAGE_SIZE", 2000))
DELAY_SEC: float = float(os.getenv("DELAY_SEC", 3.0))
NUM_RETRIES: int = int(os.getenv("NUM_RETRIES", 3))

# Configurated client for data retrieval
client: arxiv.Client = arxiv.Client(
    page_size=PAGE_SIZE,
    delay_seconds=DELAY_SEC,
    num_retries=NUM_RETRIES,
)


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


def upload_to_gcs(
    storage_client: storage.Client,
    destination_blob_name: str,
    papers: list[dict],
):
    """Upload papers as NDJSON to a GCS bucket.

    Parameters
    ----------
    storage_client: storage.Client
        Authenticated GCS client.
    destination_blob_name: str
        Target path in the bucket (e.g. "raw/arxiv/202604.ndjson").
    papers: list[dict]
        List of paper dicts to serialize and upload.
    """
    ndjson = "\n".join(json.dumps(paper, ensure_ascii=False) for paper in papers)
    bucket = storage_client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_string(ndjson, content_type="application/x-ndjson")

    print(
        f"Uploaded {len(papers)} papers to gs://{GCS_BUCKET_NAME}/{destination_blob_name}."
    )


def save_local(papers: list[dict], path: str) -> None:
    """Save papers as NDJSON to a local file.

    Parameters
    ----------
    papers: list[dict]
        List of paper dicts to serialize.
    path: str
        Local file path to write to (e.g. "data/202604.ndjson").
    """
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(json.dumps(p, ensure_ascii=False) for p in papers))
    print(f"Saved {len(papers)} papers to {path}")


def fetch_arxiv_data(start_date: str, end_date: str) -> list[dict]:
    """Fetch all publications in the specified date range.

    Parameters
    ----------
    start_date: str
        Date from which publications should be obtained from the api.
    end_date: str
        Date until which dates should be obtained from the api.

    Returns
    -------
    list[dict]
        List of dictionaries containing paper metadata.
    """

    category_query = " OR ".join(f"cat:{cat}" for cat in CATEGORIES)
    query = f"({category_query}) AND submittedDate:[{start_date} TO {end_date}]"

    search = arxiv.Search(
        query=query,
        max_results=MAX_RESULTS,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Ascending,
    )

    # query the ArXiv database
    results = client.results(search)

    papers: list[dict] = []

    for result in results:
        short_id = result.get_short_id()  # gets the arxiv id (e.g. `2107.05580v1`)
        version_match = re.search(r"v(\d+)$", short_id)
        version = version_match.group(1) if version_match else None
        papers.append(
            {
                "arxiv_id": re.sub(r"v\d+$", "", short_id),
                "title": result.title,
                "abstract": result.summary,
                "authors": [author.name for author in result.authors],
                "primary_category": result.primary_category,
                "all_categories": result.categories,
                "published": result.published.isoformat(),
                "updated": result.updated.date().isoformat(),
                "version": int(version) if version else 1,
                "doi": result.doi,
                "journal_ref": result.journal_ref,
                "comment": result.comment,
            }
        )
    return papers


def main():
    start_date: str = parse_date(os.environ["START_DATE"])
    end_date: str = parse_date(os.environ["END_DATE"])
    output_dir: str = os.getenv("OUTPUT_DIR")  # if set: save locally instead of GCS

    print(f"Fetching data in time interval: [{start_date}] to [{end_date}]", flush=True)

    # LOCAL MODE
    if output_dir:
        local_path = os.path.join(output_dir, f"{start_date[:6]}.ndjson")
        if papers := fetch_arxiv_data(start_date, end_date):
            save_local(papers, local_path)
        else:
            print("No papers found for the specified interval")
    else:  # CLOUD MODE
        storage_client = storage.Client()
        destination_blob_name: str = f"raw/arxiv/{start_date[:6]}.ndjson"
        if not FORCE_FETCH and blob_exists_gcs(storage_client, destination_blob_name):
            print(f"Skip {start_date[:6]} (already in GCS)")
            return
        if papers := fetch_arxiv_data(start_date, end_date):
            upload_to_gcs(storage_client, destination_blob_name, papers)
        else:
            print("No papers found for the specified interval")


if __name__ == "__main__":
    main()
