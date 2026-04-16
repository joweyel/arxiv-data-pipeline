locals {
  required_services = concat(
    ["serviceusage.googleapis.com", "iam.googleapis.com"],
    var.gcp_service_apis,
  )
}

resource "google_project_service" "required_apis" {
  project  = var.project_id
  for_each = toset(local.required_services)
  service  = each.key

  disable_on_destroy = false
}