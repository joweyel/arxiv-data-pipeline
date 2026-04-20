# arxiv dbt project

Transforms raw ArXiv paper metadata from BigQuery into analytics-ready mart tables.

## Models

- `staging/stg_papers`: cleaned and typed view over `ingestion_dataset.papers`
- `intermediate/int_papers_categories`: joins papers with ArXiv category taxonomy seed
- `marts/fct_papers`: final fact table, partitioned by month, clustered by primary_category
- `marts/fct_papers_embeddings`: paper text fields for downstream embedding/enrichment

## Seeds

- `arxiv_categories.csv`: ArXiv category taxonomy (id, name, group)

## Running

```bash
dbt run
dbt test
```

Requires `GCP_PROJECT_ID` env var and a valid `~/.dbt/profiles.yml` pointing to BigQuery.
