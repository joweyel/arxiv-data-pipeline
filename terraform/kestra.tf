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

resource "kestra_kv" "gcp_region" {
  namespace  = "arxiv"
  key        = "GCP_REGION"
  value      = jsonencode(var.region)
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

resource "kestra_namespace_file" "pipeline_files" {
  for_each   = fileset("${path.module}/../pipeline", "*.py")
  namespace  = "arxiv"
  filename   = "/pipeline/${each.key}"
  content    = file("${path.module}/../pipeline/${each.key}")
  depends_on = [google_compute_instance.kestra_instance]
}

resource "kestra_namespace_file" "dbt_files" {
  for_each   = fileset("${path.module}/../arxiv", "**/*.{sql,yml,yaml,csv,md,txt,toml}")
  namespace  = "arxiv"
  filename   = "/arxiv/${each.key}"
  content    = file("${path.module}/../arxiv/${each.key}")
  depends_on = [google_compute_instance.kestra_instance]
}

resource "kestra_flow" "kaggle_ingestion" {
  namespace  = "arxiv"
  flow_id    = "kaggle_ingestion"
  content    = file("${path.module}/../kestra/flows/main_arxiv_kaggle_ingestion.yml")
  depends_on = [google_compute_instance.kestra_instance]
}

resource "kestra_flow" "arxiv_pipeline" {
  namespace  = "arxiv"
  flow_id    = "arxiv_pipeline"
  content    = file("${path.module}/../kestra/flows/main_arxiv_arxiv_pipeline.yml")
  depends_on = [google_compute_instance.kestra_instance]
}
