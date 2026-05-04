import os
import streamlit as st
from google.cloud import bigquery

GCP_PROJECT_ID: str = os.environ["GCP_PROJECT_ID"]
BQ_DATASET: str = os.getenv("BQ_DATASET", "arxiv_dataset")


@st.cache_resource
def get_bq_client() -> bigquery.Client:
    return bigquery.Client(project=GCP_PROJECT_ID)


def vector_search(
    query_embeddings: list[float],
    categories: list[str],
    start_year: int,
    end_year: int,
    top_k: int = 10,
    surveys_only: bool = False,
) -> list[dict]:
    """Semantic vector search with paper embeddings.

    Parameters
    ----------
    query_embeddings: list[float]
        768-dimensional query vector from SPECTER2.
    categories: list[str]
        ArXiv category filters (e.g. ["cs.CV", "cs.LG"]).
    start_year: int
        Earliest publication year.
    end_year: int
        Latest publication year.
    top_k: int (default: 10, optional)
        Number of results to return.
    surveys_only: bool (default: False, optional)
        Weither to use only survey/overview papers in the search.

    Returns
    -------
    list[dict] (default: 10)
        Ranked papers with arxiv_id, title, date_published, primary_category,
        abstract, and similarity score.
    """
    client = get_bq_client()
    embedding_str: str = ", ".join(str(x) for x in query_embeddings)

    survey_join: str = (
        f"""
        JOIN `{GCP_PROJECT_ID}.{BQ_DATASET}.fct_papers` AS f
            ON f.arxiv_id = q.base.arxiv_id
    """
        if surveys_only
        else ""
    )
    survey_filter: str = "AND f.is_survey = TRUE" if surveys_only else ""

    query: str = f"""
        SELECT
            e.arxiv_id,
            e.title,
            e.date_published,
            e.primary_category,
            e.abstract,
            ROUND(1 - q.distance, 4) AS similarity
        FROM VECTOR_SEARCH(
            TABLE `{GCP_PROJECT_ID}.{BQ_DATASET}.paper_embeddings`,
            'embedding',
            (SELECT [{embedding_str}] AS embedding),
            top_k => 500,
            distance_type => 'COSINE'
        ) AS q
        JOIN `{GCP_PROJECT_ID}.{BQ_DATASET}.fct_papers_embeddings` AS e
            ON e.arxiv_id = q.base.arxiv_id
        {survey_join}
        WHERE
            e.primary_category IN UNNEST(@categories) AND
            EXTRACT(YEAR FROM e.date_published) BETWEEN @start_year AND @end_year
            {survey_filter}
        ORDER BY
            q.distance
        LIMIT
            {top_k}
    """
    # BQ-Vector Search: https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/search_functions#vector_search

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ArrayQueryParameter("categories", "STRING", categories),
            bigquery.ScalarQueryParameter("start_year", "INT64", start_year),
            bigquery.ScalarQueryParameter("end_year", "INT64", end_year),
        ]
    )

    rows = client.query(query, job_config=job_config).result()
    return [dict(row) for row in rows]
