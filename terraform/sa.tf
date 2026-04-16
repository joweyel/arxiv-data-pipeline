resource "google_service_account" "kestra_sa" {
  project      = var.project_id
  account_id   = "kestra-sa"
  display_name = "Kestra Pipline Service Account"
  depends_on   = [google_project_service.required_apis]
}

resource "google_service_account" "cloudrun_sa" {
  project      = var.project_id
  account_id   = "cloudrun-sa"
  display_name = "Cloud Run Service Account"
  depends_on   = [google_project_service.required_apis]
}

resource "google_service_account" "github_sa" {
  project      = var.project_id
  account_id   = "github-sa"
  display_name = "Github-Actions Service Account"
  depends_on   = [google_project_service.required_apis]
}

resource "google_project_iam_member" "kestra_sa_roles" {
  for_each   = toset(var.kestra_sa_roles_list)
  project    = var.project_id
  role       = each.value
  member     = "serviceAccount:${google_service_account.kestra_sa.email}"
  depends_on = [google_project_service.required_apis]
}

resource "google_project_iam_member" "cloudrun_sa_roles" {
  for_each   = toset(var.cloudrun_sa_roles_list)
  project    = var.project_id
  role       = each.value
  member     = "serviceAccount:${google_service_account.cloudrun_sa.email}"
  depends_on = [google_project_service.required_apis]
}

resource "google_project_iam_member" "github_sa_roles" {
  for_each   = toset(var.github_sa_roles_list)
  project    = var.project_id
  role       = each.value
  member     = "serviceAccount:${google_service_account.github_sa.email}"
  depends_on = [google_project_service.required_apis]
}