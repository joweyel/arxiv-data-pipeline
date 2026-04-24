import os
import io
import json
import zipfile
from collections import defaultdict
from datetime import datetime
from email.utils import parsedate_to_datetime

from google.cloud import storage
from kaggle.api.kaggle_api_extended import KaggleApi

KAGGLE_JSONL: str = os.environ["KAGGLE_JSONL"]
GCS_BUCKET_NAME: str = os.getenv("GCS_BUCKET")
CATEGORIES: list[str] = os.getenv("CATEGORIES", "cs.CV,cs.RO,cs.LG").split(",")
START_YEAR: int = int(os.getenv("START_YEAR", "2022"))
END_YEAR: int = int(os.getenv("END_YEAR", "2022"))
START_MONTH: int = int(os.getenv("START_MONTH", "1"))
END_MONTH: int = int(os.getenv("END_MONTH", "12"))
START_PERIOD: int = START_YEAR * 100 + START_MONTH
END_PERIOD: int = END_YEAR * 100 + END_MONTH
FORCE_FETCH: bool = os.getenv("FORCE_FETCH", "").lower() == "true"
FORCE_DOWNLOAD: bool = os.getenv("FORCE_DOWNLOAD", "").lower() == "true"
GCS_SNAPSHOT_BLOB: str = "raw/kaggle-snapshot/arxiv.zip"


def parse_rfc_date(rfc_date: str) -> str | None:
    """Converts RFC 2822 (email format) date to ISO 8601.

    Parameters
    ----------
    rfc: str
        Date string in RFC 2822 format, e.g. "Mon, 2 Apr 2007 19:18:42 GMT".

    Returns
    -------
    str | None
        ISO 8601 string or None if parsing fails.
    """
    try:
        return parsedate_to_datetime(rfc_date).isoformat()
    except ValueError as ve:
        print(f"Error during rfc-date parsing: {ve}")
        return None


def blob_exists_gcs(storage_client: storage.Client, destination_blob_name: str) -> bool:
    """Check if blob/file exists at specified path in gcs bucket."""
    return storage_client.bucket(GCS_BUCKET_NAME).blob(destination_blob_name).exists()


def upload_to_gcs(
    storage_client: storage.Client,
    destination_blob_name: str,
    papers: list[dict],
) -> None:
    """Upload papers as NDJSON to a GCS bucket.

    Parameters
    ----------
    storage_client: storage.Client
        Authenticated GCS client.
    destination_blob_name: str
        Target path in the bucket (e.g. "raw/arxiv/202604.ndjson").
    papers: list[dict]
        List of paper dicts to serialize and upload.

    Returns
    -------
    None
    """
    ndjson = "\n".join(json.dumps(paper, ensure_ascii=False) for paper in papers)
    bucket = storage_client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_string(ndjson, content_type="application/x-ndjson")
    print(
        f"Uploaded {len(papers)} papers to gs://{GCS_BUCKET_NAME}/{destination_blob_name}.",
        flush=True,
    )


def convert_entry(entry: dict) -> dict | None:
    """Convert a Kaggle arXiv snapshot entry to the pipeline paper format.

    Parameters
    ----------
    entry: dict
        Raw entry from the Kaggle arXiv JSONL snapshot.

    Returns
    -------
    dict | None
        Converted paper dict, or None if entry should be skipped.
    """
    entry_categories = entry.get("categories", "").split()
    primary = entry_categories[0] if entry_categories else None
    if primary not in CATEGORIES:
        return None

    versions: list = entry.get("versions", [])
    published = parse_rfc_date(versions[0]["created"]) if versions else None
    if not published:
        return None

    dt = datetime.fromisoformat(published)
    period = dt.year * 100 + dt.month
    if not (START_PERIOD <= period <= END_PERIOD):
        return None

    authors_parsed: list[list[str]] = entry.get("authors_parsed", [])
    authors: list[str] = [
        f"{first} {last}".strip() for first, last, *_ in authors_parsed
    ]

    return {
        "arxiv_id": entry["id"],
        "title": entry.get("title", "").replace("\n", " ").strip(),
        "abstract": entry.get("abstract", "").replace("\n", " ").strip(),
        "authors": authors,
        "primary_category": primary,
        "all_categories": entry_categories,
        "published": published,
        "updated": entry.get("update_date")
        or datetime.fromisoformat(published).date().isoformat(),
        "version": len(versions),
        "doi": entry.get("doi"),
        "journal_ref": entry.get("journal-ref"),
        "comment": entry.get("comments"),
    }


def open_kaggle_file(path: str):
    """Open the Kaggle JSONL either directly or from inside a zip archive."""
    if path.endswith(".zip"):
        archive = zipfile.ZipFile(path)
        name = next(n for n in archive.namelist() if n.endswith(".json"))
        return io.TextIOWrapper(archive.open(name), encoding="utf-8")
    return open(path, encoding="utf-8")


def download_kaggle_dataset(path: str) -> None:
    """Download the Kaggle arXiv dataset to a persistent local path.
    1. Local file exists -> use it
    2. Missing -> download from Kaggle and save to path
    Set FORCE_DOWNLOAD=true to re-download even if file exists.
    """
    if not FORCE_DOWNLOAD and os.path.exists(path):
        print(f"Using local dataset at {path}.")
        return

    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    print("Downloading Kaggle arXiv dataset ...", flush=True)
    api = KaggleApi()
    api.authenticate()
    api.dataset_download_files(
        "Cornell-University/arxiv", path=os.path.dirname(path) or ".", unzip=False
    )
    downloaded = os.path.join(os.path.dirname(path) or ".", "arxiv.zip")
    if downloaded != path:
        os.rename(downloaded, path)
    print("Download complete.", flush=True)


def main():
    download_kaggle_dataset(KAGGLE_JSONL)
    storage_client = storage.Client()

    # { ("cs.CV", "202201"): [...], ("cs.LG", "202201"): [...], ... }
    by_cat_month: dict[tuple[str, str], list[dict]] = defaultdict(list)

    print(f"Reading {KAGGLE_JSONL} ...", flush=True)
    with open_kaggle_file(KAGGLE_JSONL) as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            paper = convert_entry(entry)
            if paper:
                month_key = datetime.fromisoformat(paper["published"]).strftime("%Y%m")
                by_cat_month[(paper["primary_category"], month_key)].append(paper)
            if i % 200_000 == 0 and i > 0:
                print(f"  {i:,} records scanned ...", flush=True)

    print(
        f"Done reading. Uploading {len(by_cat_month)} category/month files to GCS ...",
        flush=True,
    )

    for (cat, month), papers in sorted(by_cat_month.items()):
        destination_blob_name = f"raw/arxiv/{cat}/{month}.ndjson"
        if not FORCE_FETCH and blob_exists_gcs(storage_client, destination_blob_name):
            print(f"Skip {cat}/{month} (already in GCS)")
            continue
        upload_to_gcs(storage_client, destination_blob_name, papers)

    print("Done.", flush=True)


if __name__ == "__main__":
    main()
