terraform {
  backend "gcs" {
    prefix = "terraform/state"
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
  machine_type = "e2-standard-2"
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

# Kestra setup on VM (Official Kestra Terraform pattern):
# https://github.com/kestra-io/terraform-deployments/blob/main/gcp/terraform/gcp-aiven/opensource/main.tf
resource "null_resource" "kestra_deploy" {
  depends_on = [google_compute_instance.kestra_instance]

  provisioner "file" {
    source      = "${path.module}/../kestra/docker-compose-gcp.yml"
    destination = "/home/ubuntu/docker-compose.yml"

    connection {
      type        = "ssh"
      user        = "ubuntu"
      private_key = file("~/.ssh/id_ed25519")
      host        = google_compute_instance.kestra_instance.network_interface[0].access_config[0].nat_ip
    }
  }

  provisioner "remote-exec" {
    inline = [
      "until sudo docker info > /dev/null 2>&1; do echo 'Waiting for Docker...'; sleep 5; done",
      "sudo docker compose -f /home/ubuntu/docker-compose.yml up -d"
    ]

    connection {
      type        = "ssh"
      user        = "ubuntu"
      private_key = file("~/.ssh/id_ed25519")
      host        = google_compute_instance.kestra_instance.network_interface[0].access_config[0].nat_ip
    }
  }
}

# GCP Secret Manager secrets for Kestra
resource "google_secret_manager_secret" "kaggle_username" {
  secret_id  = "kaggle-username"
  depends_on = [google_project_service.required_apis]
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "kaggle_username_value" {
  secret      = google_secret_manager_secret.kaggle_username.id
  secret_data = var.kaggle_username
}

resource "google_secret_manager_secret" "kaggle_key" {
  secret_id  = "kaggle-key"
  depends_on = [google_project_service.required_apis]
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "kaggle_key_value" {
  secret      = google_secret_manager_secret.kaggle_key.id
  secret_data = var.kaggle_key
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
