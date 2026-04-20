provider "kestra" {
  url      = var.kestra_url
  username = var.kestra_username
  password = var.kestra_password
}

resource "kestra_namespace_file" "arxiv_api_fetch" {
  namespace = "arxiv"
  filename  = "/pipeline/arxiv_api_fetch.py"
  content   = file("${path.module}/../pipeline/arxiv_api_fetch.py")
}

resource "kestra_namespace_file" "kaggle_to_gcs" {
  namespace = "arxiv"
  filename  = "/pipeline/kaggle_to_gcs.py"
  content   = file("${path.module}/../pipeline/kaggle_to_gcs.py")
}

resource "kestra_namespace_file" "load" {
  namespace = "arxiv"
  filename  = "/pipeline/load.py"
  content   = file("${path.module}/../pipeline/load.py")
}

resource "kestra_kv" "data_dir" {
  namespace = "arxiv"
  key       = "DATA_DIR"
  value     = jsonencode(var.data_dir)
  type      = "STRING"
}

resource "kestra_kv" "gcs_bucket" {
  namespace = "arxiv"
  key       = "GCS_BUCKET"
  value     = jsonencode(var.data_bucket)
  type      = "STRING"
}

resource "kestra_kv" "gcp_project_id" {
  namespace = "arxiv"
  key       = "GCP_PROJECT_ID"
  value     = jsonencode(var.project_id)
  type      = "STRING"
}

resource "kestra_kv" "bq_dataset" {
  namespace = "arxiv"
  key       = "BQ_DATASET"
  value     = jsonencode(var.bq_dataset)
  type      = "STRING"
}

resource "kestra_kv" "categories" {
  namespace = "arxiv"
  key       = "CATEGORIES"
  value     = jsonencode(var.categories)
  type      = "STRING"
}
