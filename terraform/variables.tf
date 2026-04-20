variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "Region of Resources"
  type        = string
  default     = "europe-west1"
}

variable "my_ip" {
  description = "IP Range to allow access"
  type        = string
  default     = "0.0.0.0/0"
}

variable "data_bucket" {
  description = "Bucket for storing raw data"
  type        = string
  default     = "arxiv-data-bucket"
}

variable "tf_state_bucket" {
  description = "GCS bucklet where TF state is saved to"
  type        = string
  default     = "arxiv-tf-state"
}

variable "force_destroy_resource" {
  description = "Allowing deleting resource"
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
    "artifactregistry.googleapis.com",
    "run.googleapis.com",
    "compute.googleapis.com",
    "secretmanager.googleapis.com",
  ]
}

variable "kestra_sa_roles_list" {
  description = "List of Roles that the kestra service account can use"
  type        = list(string)
  default = [
    "roles/bigquery.dataEditor",
    "roles/bigquery.jobUser",
    "roles/storage.objectAdmin",
    "roles/secretmanager.secretAccessor",
  ]
}

variable "cloudrun_sa_roles_list" {
  description = "List of Roles that the cloudrun service account can use"
  type        = list(string)
  default = [
    "roles/bigquery.dataViewer",
    "roles/bigquery.jobUser",
  ]
}


variable "kaggle_username" {
  description = "Kaggle API username"
  type        = string
  sensitive   = true
}

variable "kaggle_key" {
  description = "Kaggle API key"
  type        = string
  sensitive   = true
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

variable "github_sa_roles_list" {
  description = "List of Roles that can be used for Github Actions"
  type        = list(string)
  default = [
    "roles/artifactregistry.writer",
    "roles/run.developer",
    "roles/iam.serviceAccountUser",
  ]
}
