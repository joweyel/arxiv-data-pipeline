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
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

############################
###      RESOURCES       ###
############################

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
