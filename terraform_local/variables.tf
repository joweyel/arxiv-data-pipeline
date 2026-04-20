variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "Region of Resources"
  type        = string
  default     = "europe-west1"
}

variable "data_bucket" {
  description = "Bucket for storing raw data"
  type        = string
  default     = "arxiv-data-bucket"
}

variable "force_destroy_resource" {
  description = "Allow deleting resources with contents"
  type        = bool
  default     = false
}

variable "gcp_service_apis" {
  description = "List of APIs required for the project"
  type        = list(string)
  default = [
    "cloudresourcemanager.googleapis.com",
    "storage.googleapis.com",
    "bigquery.googleapis.com",
  ]
}

variable "data_dir" {
  description = "Absolute host path for persistent dataset storage mounted into Kestra task containers"
  type        = string
}

variable "kestra_url" {
  description = "Kestra server URL"
  type        = string
  default     = "http://localhost:8080"
}

variable "kestra_username" {
  description = "Kestra admin username"
  type        = string
  default     = "admin@kestra.io"
}

variable "kestra_password" {
  description = "Kestra admin password"
  type        = string
  sensitive   = true
}

variable "bq_dataset" {
  description = "BigQuery dataset for ingested data"
  type        = string
  default     = "ingestion_dataset"
}

variable "categories" {
  description = "ArXiv categories to ingest"
  type        = string
  default     = "cs.CV,cs.RO"
}

variable "pipeline_sa_roles_list" {
  description = "Roles for the local pipeline service account"
  type        = list(string)
  default = [
    "roles/bigquery.dataEditor",
    "roles/bigquery.jobUser",
    "roles/storage.objectAdmin",
  ]
}
