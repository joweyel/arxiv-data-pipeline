# Artifact Registry for Docker Images
resource "google_artifact_registry_repository" "artifact_docker_repo" {
  location      = var.region
  repository_id = "arxiv-pipeline"
  format        = "DOCKER"
  depends_on    = [google_project_service.required_apis]
}

# Cloud Run service for the paper retrieval app
resource "google_cloud_run_v2_service" "paper_retrieval" {
  project             = var.project_id
  name                = "arxiv-paper-retrieval"
  location            = var.region
  deletion_protection = false
  ingress             = "INGRESS_TRAFFIC_ALL"

  template {
    containers {
      name  = "arxiv-paper-retrieval"
      image = "us-docker.pkg.dev/cloudrun/container/hello" # placeholder; replaced by GitHub Actions on first deploy
      ports {
        container_port = 8501
      }
      resources {
        limits = {
          memory = "4Gi"
          cpu    = "2"
        }
      }
    }
    service_account = google_service_account.cloudrun_sa.email
  }
  depends_on = [google_project_service.required_apis]
}

resource "google_cloud_run_v2_service_iam_member" "cloud_run_access" {
  project  = google_cloud_run_v2_service.paper_retrieval.project
  location = google_cloud_run_v2_service.paper_retrieval.location
  name     = google_cloud_run_v2_service.paper_retrieval.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
