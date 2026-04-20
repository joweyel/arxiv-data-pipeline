{{ config(
    materialized='table',
    partition_by={
        'field': 'date_published',
        'data_type': 'timestamp',
        'granularity': 'month'
    },
    cluster_by=['primary_category']
) }}

WITH extended_arxiv_data AS (
    SELECT
        *
    FROM
        {{ ref('int_papers_categories') }}
),

extended_arxiv_data_visualization AS (
    SELECT
        -- identifiers
        arxiv_id,

        -- content
        title,

        -- authors
        authors,

        -- categories
        primary_category,
        all_categories,
        category_name AS category,
        category_group AS subject_group,

        -- metadata
        version,
        doi,
        journal_ref,
        is_published,
        comment,

        -- dates
        CAST(date_published AS TIMESTAMP) AS date_published,
        date_updated,
        submission_year AS year,
        submission_month AS month,

        -- derived flags
        has_code,
        is_survey

    FROM
        extended_arxiv_data
)

SELECT
    *
FROM
    extended_arxiv_data_visualization
