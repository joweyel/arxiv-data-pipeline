provider "kestra" {
  url      = "http://${local.kestra_ip}:8080"
  username = var.kestra_username
  password = var.kestra_password
}

resource "kestra_kv" "data_dir" {
  namespace  = "arxiv"
  key        = "DATA_DIR"
  value      = jsonencode("/opt/kestra/data")
  type       = "STRING"
  depends_on = [google_compute_instance.kestra_instance]
}

resource "kestra_kv" "gcs_bucket" {
  namespace  = "arxiv"
  key        = "GCS_BUCKET"
  value      = jsonencode(var.data_bucket)
  type       = "STRING"
  depends_on = [google_compute_instance.kestra_instance]
}

resource "kestra_kv" "gcp_project_id" {
  namespace  = "arxiv"
  key        = "GCP_PROJECT_ID"
  value      = jsonencode(var.project_id)
  type       = "STRING"
  depends_on = [google_compute_instance.kestra_instance]
}

resource "kestra_kv" "bq_dataset" {
  namespace  = "arxiv"
  key        = "BQ_DATASET"
  value      = jsonencode(var.bq_dataset)
  type       = "STRING"
  depends_on = [google_compute_instance.kestra_instance]
}

resource "kestra_kv" "categories" {
  namespace  = "arxiv"
  key        = "CATEGORIES"
  value      = jsonencode(var.categories)
  type       = "STRING"
  depends_on = [google_compute_instance.kestra_instance]
}
