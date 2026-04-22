# Setup Instructions

This guide covers two deployment paths:

- **Local Kestra + GCP** (recommended): Kestra runs on your machine via Docker Compose, GCS and BigQuery are on GCP. Simpler setup, no VM cost.
- **Fully Online**: Everything runs on GCP. Kestra runs on a VM provisioned by Terraform.

Both paths share the prerequisites below.


## Prerequisites

### 1. Install gcloud CLI

```bash
curl -O https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-cli-linux-x86_64.tar.gz
tar -xf google-cloud-cli-linux-x86_64.tar.gz
./google-cloud-sdk/install.sh
source ~/.bashrc
```

### 2. Install Terraform

Follow the instructions at https://developer.hashicorp.com/terraform/tutorials/aws-get-started/install-cli

### 3. Install Docker

Required for both paths (local Docker Compose for Local Kestra path; Docker for building images in the online path).

Follow the instructions at https://docs.docker.com/engine/install/

### 4. Authenticate to GCP

```bash
gcloud auth login
gcloud auth application-default login
```

### 5. Create GCP Project

```bash
export PROJECT=your-unique-project-id
export REGION=europe-west1
export ZONE=europe-west1-b

gcloud projects create ${PROJECT} --name="ArXiv Data Pipeline"
gcloud config set project ${PROJECT}
gcloud auth application-default set-quota-project ${PROJECT}
```

Or create the project via the web console at https://console.cloud.google.com and then run:

```bash
gcloud config set project ${PROJECT}
gcloud auth application-default set-quota-project ${PROJECT}
```

### 6. Link Billing Account

Go to https://console.cloud.google.com, switch to your new project, click Billing and attach a billing account.

### 7. Create GCS Bucket for Terraform State

GCS bucket names are globally unique. Choose a name that is not already taken.

```bash
gcloud storage buckets create gs://arxiv-tf-state-${PROJECT} --location=${REGION}
gcloud storage buckets update gs://arxiv-tf-state-${PROJECT} --versioning
```

### 8. Create SSH Key (online path only)

Terraform uses this key to configure SSH access to the Kestra VM. Skip if `~/.ssh/id_ed25519.pub` already exists.

```bash
ssh-keygen -t ed25519 -C "your_email@example.com"
```

### 9. Kaggle API Key

The pipeline uses the [Kaggle arXiv dataset](https://www.kaggle.com/datasets/Cornell-University/arxiv) for historical ingestion.

1. Create a free account at https://www.kaggle.com
2. Go to Settings > API > Create New Token. This downloads `kaggle.json` containing:
```json
{"username": "your-username", "key": "your-api-key"}
```

Keep these values handy. They are needed when configuring Kestra credentials below.


## Local Kestra + GCP Setup

Provisions GCS + BigQuery + service account on GCP via Terraform. Kestra runs locally via Docker Compose.

Terraform apply is run twice: once before Kestra starts (`deploy_kestra = false`) to create GCP resources and the SA key, and once after (`deploy_kestra = true`) to seed the Kestra KV store and upload namespace files.

### 1. Configure terraform.tfvars

```bash
cp terraform_local/terraform.tfvars.example terraform_local/terraform.tfvars
```

Fill in your values:

```hcl
project_id             = "your-gcp-project-id"
region                 = "europe-west1"
force_destroy_resource = false
data_bucket            = "arxiv-data-bucket-yourname"   # must be globally unique
bq_dataset             = "ingestion_dataset"
categories             = "cs.CV,cs.RO"
data_dir               = "/absolute/path/to/pipeline/data"
kestra_url             = "http://localhost:8080"
kestra_username        = "admin@kestra.io"
kestra_password        = "Admin1234!"
deploy_kestra          = false
```

`data_dir` must be the absolute path to the `pipeline/data` directory on your machine. It is mounted into the Docker container so Kestra can read and write the Kaggle dataset file.

### 2. First Terraform Apply (GCP resources + SA key)

```bash
terraform -chdir=terraform_local init -backend-config="bucket=arxiv-tf-state-${PROJECT}"
terraform -chdir=terraform_local apply -var-file="terraform.tfvars" -auto-approve
```

This creates GCS, BigQuery datasets, the service account, and writes `credentials/pipeline-sa.json`.

### 3. Configure Kestra Credentials

```bash
cp kestra/.env.example kestra/.env
```

Fill in `kestra/.env` with base64-encoded values:

```bash
echo -n "your-kaggle-username" | base64
echo -n "your-kaggle-api-key" | base64
base64 -w 0 credentials/pipeline-sa.json
```

Paste the outputs into the three variables in `kestra/.env`.

### 4. Start Kestra

```bash
docker compose -f kestra/docker-compose.yml up -d
```

Kestra UI is available at http://localhost:8080. Login with `admin@kestra.io` / `Admin1234!`.

### 5. Second Terraform Apply (seeds KV store + uploads namespace files)

```bash
terraform -chdir=terraform_local apply -var-file="terraform.tfvars" -var="deploy_kestra=true" -auto-approve
```

### 6. Run the Pipeline

Open http://localhost:8080 and trigger the flows in order:

1. `kaggle_ingestion`: ingests historical data from the Kaggle snapshot
2. `arxiv_pipeline`: fetches recent papers from the ArXiv API, loads to BigQuery, runs dbt

### 7. Tear Down (after you are done)

This deletes all GCP resources including BigQuery datasets and the GCS bucket.

```bash
terraform -chdir=terraform_local destroy -var-file="terraform.tfvars" -auto-approve
docker compose -f kestra/docker-compose.yml down -v
```


## Pre-Commit Hooks (optional)

Install `pre-commit` with `pipx` or `uv`:

```bash
pipx install pre-commit
# or
uv tool install pre-commit
```

Register the hooks with git (once per clone):

```bash
pre-commit install
```

The hooks run automatically on every `git commit`. Config: [.pre-commit-config.yaml](./.pre-commit-config.yaml)


<details>
<summary>Fully Online Setup (Kestra on GCP VM)</summary>

In this setup everything runs on GCP. Terraform provisions a Compute Engine VM that runs Kestra via Docker. GCS and BigQuery are the same as the local path. The dashboard uses Looker Studio connecting directly to BigQuery.

GitHub Actions and Cloud Run are only needed if you want automated Docker image deployments of a custom dashboard. They are not required to run the pipeline.

### 1. Configure terraform.tfvars

```bash
cp terraform/terraform.tfvars.example terraform/terraform.tfvars
```

Fill in your values:

```hcl
project_id             = "your-gcp-project-id"
region                 = "europe-west1"
my_ip                  = "0.0.0.0/0"
tf_state_bucket        = "arxiv-tf-state-your-project-id"
force_destroy_resource = true
kaggle_username        = "your-kaggle-username"
kaggle_key             = "your-kaggle-api-key"
```

### 2. Apply Terraform

```bash
terraform -chdir=terraform init
terraform -chdir=terraform plan -var-file="terraform.tfvars"
terraform -chdir=terraform apply -var-file="terraform.tfvars" -auto-approve
```

This provisions: GCS bucket, BigQuery datasets, Artifact Registry, Kestra VM, Cloud Run service, service accounts, IAM bindings, and firewall rules.

### 3. Get Outputs

```bash
terraform -chdir=terraform output
```

```
data_bucket       = "arxiv-data-bucket"
docker_registry   = "europe-west1-docker.pkg.dev/<project-id>/arxiv-pipeline"
ingestion_dataset = "ingestion_dataset"
kestra_vm_ip      = "<vm-external-ip>"
processed_dataset = "arxiv_dataset"
streamlit_url     = "https://<cloud-run-url>"
```

### 4. Access Kestra UI

Open `http://<kestra_vm_ip>:8080` in your browser.

### 5. Stop and Start the VM (without destroying it)

```bash
gcloud compute instances stop kestra-vm --zone=${ZONE}
gcloud compute instances start kestra-vm --zone=${ZONE}
```

After restart the VM gets a new external IP. Retrieve it with:

```bash
terraform -chdir=terraform output kestra_vm_ip
```

### 6. Tear Down

```bash
terraform -chdir=terraform destroy -var-file="terraform.tfvars" -auto-approve
```

### GitHub Actions Setup (Docker dashboard deployment only)

This is only needed if you want GitHub Actions to automatically build and deploy a Dockerized dashboard to Cloud Run on every push to `main`.

#### Obtain the github-sa key

During `terraform apply` the key is written to `credentials/github-sa.json`. To regenerate it manually:

```bash
gcloud iam service-accounts keys create credentials/github-sa.json \
    --iam-account=github-sa@${PROJECT}.iam.gserviceaccount.com
```

#### Add secrets to GitHub

| Secret | Value |
| --- | --- |
| `GCP_SA_KEY` | base64-encoded contents of `credentials/github-sa.json` |
| `GCP_PROJECT_ID` | your project ID |
| `GCP_REGION` | e.g. `europe-west1` |
| `ARTIFACT_REGISTRY_REPO` | `arxiv-pipeline` |
| `CLOUD_RUN_SERVICE_NAME` | `arxiv-streamlit-dashboard` |

Via gh CLI:

```bash
gh secret set GCP_SA_KEY --body "$(base64 -w 0 credentials/github-sa.json)"
gh secret set GCP_PROJECT_ID --body "${PROJECT}"
gh secret set GCP_REGION --body "${REGION}"
gh secret set ARTIFACT_REGISTRY_REPO --body "arxiv-pipeline"
gh secret set CLOUD_RUN_SERVICE_NAME --body "arxiv-streamlit-dashboard"
```

</details>
