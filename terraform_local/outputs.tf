locals {
  pipeline_sa_email = google_service_account.pipeline_sa.email
}

output "data_bucket" {
  description = "GCS bucket for raw ArXiv data"
  value       = google_storage_bucket.arxiv_data_bucket.name
}

output "ingestion_dataset" {
  description = "BigQuery dataset ID for raw ingested data"
  value       = google_bigquery_dataset.ingestion_dataset.dataset_id
}

output "processed_dataset" {
  description = "BigQuery dataset ID for processed data"
  value       = google_bigquery_dataset.processed_dataset.dataset_id
}

output "pipeline_sa_email" {
  description = "Service account email for local pipeline runs"
  value       = local.pipeline_sa_email
}
