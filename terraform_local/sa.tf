resource "google_service_account" "pipeline_sa" {
  project      = var.project_id
  account_id   = "pipeline-sa"
  display_name = "Local Pipeline Service Account"
  depends_on   = [google_project_service.required_apis]
}

resource "google_service_account_key" "pipeline_sa_key" {
  service_account_id = google_service_account.pipeline_sa.name
}

resource "local_file" "pipeline_sa_key_file" {
  content  = base64decode(google_service_account_key.pipeline_sa_key.private_key)
  filename = "${path.module}/../credentials/pipeline-sa.json"
}

resource "google_project_iam_member" "pipeline_sa_roles" {
  for_each   = toset(var.pipeline_sa_roles_list)
  project    = var.project_id
  role       = each.value
  member     = "serviceAccount:${google_service_account.pipeline_sa.email}"
  depends_on = [google_project_service.required_apis]
}
