provider "kestra" {
  url      = var.kestra_url
  username = var.kestra_username
  password = var.kestra_password
}

resource "kestra_namespace_file" "arxiv_api_fetch" {
  count     = var.deploy_kestra ? 1 : 0
  namespace = "arxiv"
  filename  = "/pipeline/arxiv_api_fetch.py"
  content   = file("${path.module}/../pipeline/arxiv_api_fetch.py")
}

resource "kestra_namespace_file" "kaggle_to_gcs" {
  count     = var.deploy_kestra ? 1 : 0
  namespace = "arxiv"
  filename  = "/pipeline/kaggle_to_gcs.py"
  content   = file("${path.module}/../pipeline/kaggle_to_gcs.py")
}

resource "kestra_namespace_file" "load" {
  count     = var.deploy_kestra ? 1 : 0
  namespace = "arxiv"
  filename  = "/pipeline/load.py"
  content   = file("${path.module}/../pipeline/load.py")
}

resource "kestra_kv" "data_dir" {
  count     = var.deploy_kestra ? 1 : 0
  namespace = "arxiv"
  key       = "DATA_DIR"
  value     = jsonencode(var.data_dir)
  type      = "STRING"
}

resource "kestra_kv" "gcs_bucket" {
  count     = var.deploy_kestra ? 1 : 0
  namespace = "arxiv"
  key       = "GCS_BUCKET"
  value     = jsonencode(var.data_bucket)
  type      = "STRING"
}

resource "kestra_kv" "gcp_project_id" {
  count     = var.deploy_kestra ? 1 : 0
  namespace = "arxiv"
  key       = "GCP_PROJECT_ID"
  value     = jsonencode(var.project_id)
  type      = "STRING"
}

resource "kestra_kv" "bq_dataset" {
  count     = var.deploy_kestra ? 1 : 0
  namespace = "arxiv"
  key       = "BQ_DATASET"
  value     = jsonencode(var.bq_dataset)
  type      = "STRING"
}

resource "kestra_kv" "gcp_region" {
  count     = var.deploy_kestra ? 1 : 0
  namespace = "arxiv"
  key       = "GCP_REGION"
  value     = jsonencode(var.region)
  type      = "STRING"
}

resource "kestra_kv" "categories" {
  count     = var.deploy_kestra ? 1 : 0
  namespace = "arxiv"
  key       = "CATEGORIES"
  value     = jsonencode(var.categories)
  type      = "STRING"
}

resource "kestra_namespace_file" "dbt_files" {
  for_each  = var.deploy_kestra ? fileset("${path.module}/../arxiv", "**/*.{sql,yml,yaml,csv,md,txt,toml}") : toset([])
  namespace = "arxiv"
  filename  = "/arxiv/${each.key}"
  content   = file("${path.module}/../arxiv/${each.key}")
}
