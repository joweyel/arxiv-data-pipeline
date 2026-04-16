# Setup Instructions

## Creating GCP project

### 0. Install `google-cloud-cli`

Link: https://docs.cloud.google.com/sdk/docs/install-sdk

```bash
curl -O https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-cli-linux-x86_64.tar.gz
tar -xf google-cloud-cli-linux-x86_64.tar.gz
./google-cloud-sdk/install.sh
source ~/.bashrc  # reload PATH so gcloud is available
```

### 1. Authentication to GCP

```bash
gcloud auth login                      # browser opens, log in with your Google account
gcloud auth application-default login  # grants SDK tools (Terraform, gsutil etc.) access
```

### 2. Creating GCP project

```bash
gcloud projects create arxiv-data-pipeline --name="ArXiv Data Pipeline"  # create project
gcloud config set project arxiv-data-pipeline                             # set as active project
gcloud auth application-default set-quota-project arxiv-data-pipeline    # point ADC quota to new project
```

### 3. Link billing account 
- Go to console.cloud.google.com
- Change to newly created project
- Click on Billing and attach Billing account to project

### 4. Create GCS Bucket for Terraform State

```bash
gcloud storage buckets create gs://arxiv-tf-state --location=europe-west1  # create state bucket
gcloud storage buckets update gs://arxiv-tf-state --versioning              # enable versioning for recovery
```

### 5. Enable Required APIs (can be skipped)

This activates Google Cloud APIs to be used. This is later also done in Terraform's provisioning of cloud resources. This step is here for completeness sake.

```bash
gcloud services enable \
    cloudresourcemanager.googleapis.com \
    iam.googleapis.com \
    storage.googleapis.com \
    bigquery.googleapis.com \
    artifactregistry.googleapis.com \
    run.googleapis.com \
    compute.googleapis.com
```

Check the enabled services
```bash
gcloud services list --enabled
```


Check if everything is correctly set up:
```bash
gcloud config list
gcloud projects describe arxiv-data-pipeline
gcloud services list --enabled
```


## Terraform Infrastructure Provisioning

Provisions all GCP resources in one command: GCS bucket, BigQuery datasets, Artifact Registry for Docker container, Kestra VM for orchestration, Cloud Run service, service accounts, IAM bindings and firewall rules.

### 1. Install Terraform

Follow instructions to install Terraform [here](https://developer.hashicorp.com/terraform/tutorials/aws-get-started/install-cli).

### 2. Configure variables

Copy the example tfvars-file and fill in your values:
```bash
cp terraform/terraform.tfvars.example terraform/terraform.tfvars
```

### 3. Create resources

> `-chdir=terraform` can be dropped if you execute everything terraform-related in the [`terraform/`](./terraform/) folder. It has to be specified, when everything is done from the project-root.

Initialize, plan and apply the creation of the GCP insfrastructure.

```bash
terraform -chdir=terraform init
terraform -chdir=terraform plan -var-file="terraform.tfvars"
terraform -chdir=terraform apply -var-file="terraform.tfvars" -auto-approve
```

### 4. Tear down resources

```bash
terraform -chdir=terraform destroy -var-file="terraform.tfvars" -auto-approve
```

### Get relevant output data from terraform

```bash
terraform -chdir=terraform output
```

You will get outputs like this:
```bash
data_bucket       = "arxiv-data-bucket"                                        # GCS bucket for ingested data
docker_registry   = "europe-west1-docker.pkg.dev/<project-id>/arxiv-pipeline"  # Your dashboard's container is saved here
ingestion_dataset = "ingestion_dataset"                                        # "Unprocessed" data in BigQuery
kestra_vm_ip      = "<vm-external-ip>"                                         # External IP of Kestra's Cloud VM
processed_dataset = "arxiv_dataset"                                            # "Processed" data in BigQuery
streamlit_url     = "https://<cloud-run-url>"                                  # BI-Dashboard URL
```
