#!/usr/bin/env bash
set -euo pipefail

IMAGE="embed-papers-gpu"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

docker build -f "${REPO_ROOT}/pipeline/Dockerfile.embed.gpu" \
  -t "${IMAGE}" \
  "${REPO_ROOT}/pipeline"

docker run --rm --gpus all \
  -e GCP_PROJECT_ID="${GCP_PROJECT_ID:-arxiv-data-pipeline}" \
  -e BQ_DATASET="${BQ_DATASET:-ingestion_dataset}" \
  -e BATCH_SIZE="${BATCH_SIZE:-128}" \
  -e TOP_N_KEYWORDS="${TOP_N_KEYWORDS:-8}" \
  -e BACKFILL_ALL="${BACKFILL_ALL:-}" \
  -v "${HOME}/.config/gcloud:/root/.config/gcloud:ro" \
  "${IMAGE}"
