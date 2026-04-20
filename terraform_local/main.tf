terraform {
  backend "gcs" {
    bucket = "arxiv-tf-state"
    prefix = "terraform/state-local"
  }
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
    kestra = {
      source  = "kestra-io/kestra"
      version = "~> 0.19"
    }
    local = {
      source  = "hashicorp/local"
      version = "~> 2.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

############################
###      RESOURCES       ###
############################

# Service Account for pipeline
resource "google_service_account" "pipeline_sa" {
  account_id   = "pipeline-sa-local"
  display_name = "Pipeline SA (local)"
}

resource "google_project_iam_member" "pipeline_sa_roles" {
  for_each = toset(var.pipeline_sa_roles_list)
  project  = var.project_id
  role     = each.value
  member   = "serviceAccount:${google_service_account.pipeline_sa.email}"
}

resource "google_service_account_key" "pipeline_sa_key" {
  service_account_id = google_service_account.pipeline_sa.name
}

resource "local_file" "pipeline_sa_key_file" {
  content         = base64decode(google_service_account_key.pipeline_sa_key.private_key)
  filename        = "${path.module}/../credentials/pipeline-sa.json"
  file_permission = "0600"
}

# GCS Bucket for ingestions
resource "google_storage_bucket" "arxiv_data_bucket" {
  name                        = var.data_bucket
  location                    = var.region
  force_destroy               = var.force_destroy_resource
  uniform_bucket_level_access = true

  lifecycle_rule {
    condition {
      age = 60
    }
    action {
      type = "Delete"
    }
  }
}

# BigQuery Dataset for ingested data
resource "google_bigquery_dataset" "ingestion_dataset" {
  dataset_id                 = "ingestion_dataset"
  location                   = var.region
  description                = "Dataset where initial data is stored"
  delete_contents_on_destroy = var.force_destroy_resource
}

# BigQuery Dataset for fully processed data
resource "google_bigquery_dataset" "processed_dataset" {
  dataset_id                 = "arxiv_dataset"
  location                   = var.region
  description                = "Dataset where final processed data is stored"
  delete_contents_on_destroy = var.force_destroy_resource
}
