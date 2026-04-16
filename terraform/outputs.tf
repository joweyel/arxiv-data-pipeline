# GCS Data Lake
output "data_bucket" {
  description = "Name of the GCS bucket where raw ArXiv data is stored"
  value       = google_storage_bucket.arxiv_data_bucket.name
}

# BigQuery Datasets
output "ingestion_dataset" {
  description = "BigQuery dataset ID for raw ingested data"
  value       = google_bigquery_dataset.ingestion_dataset.dataset_id
}

output "processed_dataset" {
  description = "BigQuery dataset ID for fully processed data"
  value       = google_bigquery_dataset.processed_dataset.dataset_id
}

# Artifact Registry
output "docker_registry" {
  description = "Artifact Registry path for Docker images"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/arxiv-pipeline"
}

# Kestra VM
output "kestra_vm_ip" {
  description = "External IP address of the Kestra orchestration VM"
  value       = google_compute_instance.kestra_instance.network_interface[0].access_config[0].nat_ip
}

# Cloud Run - Streamlit Dashboard
output "streamlit_url" {
  description = "Public URL of the Streamlit dashboard on Cloud Run"
  value       = google_cloud_run_v2_service.st_dashboard.uri
}