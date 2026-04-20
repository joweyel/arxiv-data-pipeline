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

### 2. Create SSH Key

Terraform uses this key to configure SSH access to the Kestra VM.

```bash
ssh-keygen -t ed25519 -C "your_email@example.com"  # creates ~/.ssh/id_ed25519 + id_ed25519.pub
```

Skip if `~/.ssh/id_ed25519.pub` already exists.

### 3. Creating GCP project

```bash
gcloud projects create arxiv-data-pipeline --name="ArXiv Data Pipeline"  # create project
gcloud config set project arxiv-data-pipeline                             # set as active project
gcloud auth application-default set-quota-project arxiv-data-pipeline    # point ADC quota to new project
```

### 4. Link billing account
- Go to https://console.cloud.google.com
- Change to newly created project
- Click on Billing and attach Billing account to project

### 5. Create GCS Bucket for Terraform State

Required for both local and production Terraform deployments. GCS bucket names are globally unique, so choose a name that is not already taken (e.g. `arxiv-tf-state-YOUR_PROJECT_ID`).

```bash
gcloud storage buckets create gs://arxiv-tf-state-YOUR_PROJECT_ID --location=europe-west1   # create state bucket
gcloud storage buckets update gs://arxiv-tf-state-YOUR_PROJECT_ID --versioning              # enable versioning for recovery
```

Also set a unique name for the data bucket in `terraform_local/terraform.tfvars` (the default `arxiv-data-bucket` may already be taken).

### 6. Enable Required APIs (can be skipped)

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

### Final Checks

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

### Start and Stop Cloud VM
A helpful command to stop the VM where the Orchestrator is running on, without deleting it with terraform, the following commands can be used:

```bash
ZONE=europe-west1-b  # Example

# Stop the vm instance without deleting
gcloud compute instances stop kestra-vm --zone=${ZONE}

# Check the state of the resource
gcloud compute instances describe kestra-vm --zone=${ZONE} --format="value(status)"

# Restart the vm instance
gcloud compute instances start kestra-vm --zone=${ZONE}
```

> **`Note`**: Stopping and restarting the VM assigns a new external IP. After restart, get the new IP with:
> ```bash
> terraform -chdir=terraform output kestra_vm_ip
> ```


## GitHub Actions Setup

To access GCP services, GitHub Actions requires a service account key to push Docker images to Artifact Registry and deploy them to Cloud Run.

### 1. Obtain the key

During `terraform apply`, the github-sa key is automatically generated and written to `credentials/github-sa.json`. If you need to regenerate it manually:

```bash
# Generate and download github-sa key to credentials/
gcloud iam service-accounts keys create credentials/github-sa.json \
    --iam-account=github-sa@arxiv-data-pipeline.iam.gserviceaccount.com
```

### 2. Add secrets to GitHub

The following secrets must be added to the GitHub repository:

| Secret                   | Value                                                   |
| ------------------------ | ------------------------------------------------------- |
| `GCP_SA_KEY`             | base64-encoded contents of `credentials/github-sa.json` |
| `GCP_PROJECT_ID`         | `arxiv-data-pipeline`                                   |
| `GCP_REGION`             | `europe-west1`                                          |
| `ARTIFACT_REGISTRY_REPO` | `arxiv-pipeline`                                        |
| `CLOUD_RUN_SERVICE_NAME` | `arxiv-streamlit-dashboard`                             |

#### **Option A (Web UI):**

Follow the [GitHub secrets documentation](https://docs.github.com/en/actions/security-guides/encrypted-secrets).

#### **Option B (gh CLI):**

If you have installed the [Github CLI](https://cli.github.com/) and are authenticated, you can use the following commands instead of adding every secret by hand:

```bash
gh secret set GCP_SA_KEY --body "$(base64 -w 0 credentials/github-sa.json)"
gh secret set GCP_PROJECT_ID --body "arxiv-data-pipeline"
gh secret set GCP_REGION --body "europe-west1"
gh secret set ARTIFACT_REGISTRY_REPO --body "arxiv-pipeline"
gh secret set CLOUD_RUN_SERVICE_NAME --body "arxiv-streamlit-dashboard"
```

> The values above are examples and can be replaced by your values.

![Github Secrets](./assets/images/gh-secrets.png)


## Local Kestra + GCP Setup

Provisions GCS + BigQuery + service account on GCP via Terraform. Kestra runs locally via Docker Compose.

> **`Terraform apply is run twice`**: once before Kestra starts (`deploy_kestra = false`) to create GCP resources and the SA key, and once after (`deploy_kestra = true`) to seed the Kestra KV store and upload namespace files.

### 1. Configure terraform.tfvars

```bash
cp terraform_local/terraform.tfvars.example terraform_local/terraform.tfvars
```

Fill in `project_id`, `data_bucket` (globally unique name), and `data_dir` (absolute path to `pipeline/data`). Leave `deploy_kestra = false` for now.

### 2. First Terraform apply (GCP resources + SA key)

```bash
terraform -chdir=terraform_local init
terraform -chdir=terraform_local apply -var-file="terraform.tfvars" -auto-approve
```

This creates GCS, BigQuery datasets, the service account, and writes `credentials/pipeline-sa.json`.

### 3. Configure Kestra credentials

```bash
cp kestra/.env.example kestra/.env
```

Fill in `kestra/.env` (all values must be base64-encoded):

```bash
echo -n "your-kaggle-username" | base64
echo -n "your-kaggle-api-key" | base64
base64 -w 0 credentials/pipeline-sa.json
```

Paste outputs into `kestra/.env`.

### 4. Start Kestra

```bash
docker compose -f kestra/docker-compose.yml up -d
```

Kestra UI is available at `http://localhost:8080`. Login with `admin@kestra.io` and `Admin1234!`.

### 5. Second Terraform apply (seeds KV store + uploads namespace files)

```bash
terraform -chdir=terraform_local apply -var-file="terraform.tfvars" -var="deploy_kestra=true" -auto-approve
```

### 6. Tear down

```bash
terraform -chdir=terraform_local destroy -var-file="terraform.tfvars" -auto-approve
```


## Pre-Commit Hooks

To allow pre-commit CI tools you have to install `pre-commit` on your system. This can be done with `pipx` or `uv`:

```bash
# Option 1: with pipx
pipx install pre-commit

# Option 2: with uv
uv tool install pre-commit
```

Then register the hooks with git (required once per clone):

```bash
pre-commit install
```

The hooks run automatically on every `git commit`. Config: [.pre-commit-config.yaml](./.pre-commit-config.yaml)
