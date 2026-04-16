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
  ]
}

variable "kestra_sa_roles_list" {
  description = "List of Roles that the kestra service account can use"
  type        = list(string)
  default = [
    "roles/bigquery.dataEditor",
    "roles/bigquery.jobUser",
    "roles/storage.objectAdmin",
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


variable "github_sa_roles_list" {
  description = "List of Roles that can be used for Github Actions"
  type        = list(string)
  default = [
    "roles/artifactregistry.writer",
    "roles/run.developer",
    "roles/iam.serviceAccountUser",
  ]
}