{{
    config(
        materialized='table'
    )
}}

WITH extended_arxiv_data AS (
    SELECT
        *
    FROM
        {{ ref('int_papers_categories') }}
),
extended_arxiv_data_embedding_input AS (
    SELECT
        arxiv_id,
        title,
        abstract,
        primary_category,
        category_name AS category,
        date_published,
        submission_year AS year,
        submission_month AS month
    FROM
        extended_arxiv_data
)

SELECT
    *
from extended_arxiv_data_embedding_input
