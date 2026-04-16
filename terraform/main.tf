terraform {
  backend "gcs" {
    bucket = "arxiv-tf-state"
    prefix = "terraform/state"
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

  lifecycle_rule { # Deletes raw data after ~2 months
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

# Artifact Registry for Docker Images
resource "google_artifact_registry_repository" "artifact_docker_repo" {
  location      = var.region
  repository_id = "arxiv-pipeline"
  format        = "DOCKER"
  depends_on    = [google_project_service.required_apis]
}

# Google Computer Instance VM for Kestra Orchstration Tool
resource "google_compute_instance" "kestra_instance" {
  name         = "kestra-vm"
  machine_type = "e2-medium"
  zone         = "${var.region}-b"

  tags = ["kestra", "orchestration"]
  boot_disk {
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-2204-lts"
      size  = 20
    }
  }
  network_interface {
    network = "default"
    access_config {} # gives external IP (returned in tf outputs)
  }

  service_account {
    email  = google_service_account.kestra_sa.email
    scopes = ["cloud-platform"]
  }

  metadata = {
    ssh-keys = "ubuntu:${file("~/.ssh/id_ed25519.pub")}"
  }

  metadata_startup_script = file("${path.module}/scripts/startup.sh")
}

# Firewall for access to the orchestration Compute Instance
resource "google_compute_firewall" "kestra_firewall" {
  name    = "kestra-firewall"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["8080"]
  }

  target_tags   = ["kestra"]
  source_ranges = [var.my_ip]
}

# Cloudrun
resource "google_cloud_run_v2_service" "st_dashboard" {
  project             = var.project_id
  name                = "arxiv-streamlit-dashboard"
  location            = var.region
  deletion_protection = !var.force_destroy_resource
  ingress             = "INGRESS_TRAFFIC_ALL"

  template {
    containers {
      name  = "streamlit-bi-dashboard"
      image = "us-docker.pkg.dev/cloudrun/container/hello" # placeholder; replaced by GitHub Actions on first deploy
      ports {
        container_port = 8501
      }
    }
    service_account = google_service_account.cloudrun_sa.email
  }
  depends_on = [google_project_service.required_apis]
}

resource "google_cloud_run_v2_service_iam_member" "cloud_run_access" {
  project  = google_cloud_run_v2_service.st_dashboard.project
  location = google_cloud_run_v2_service.st_dashboard.location
  name     = google_cloud_run_v2_service.st_dashboard.name
  role     = "roles/run.invoker"
  member   = "allUsers" # member = "allAuthenticatedUsers"
}