WITH source AS (
    SELECT
        *
    FROM
        {{ source('ingestion_dataset', 'papers') }}
),

renamed AS (
    SELECT
        -- identifiers
        arxiv_id,

        -- content
        title,
        abstract,

        -- authors
        authors,

        -- categories
        primary_category,
        all_categories,

        -- metadata
        CAST(version AS INTEGER) AS version,
        doi,
        journal_ref,
        (doi IS NOT NULL OR journal_ref IS NOT NULL) AS is_published,
        comment,

        -- dates
        CAST(date_published AS DATE) AS date_published,
        CAST(date_updated AS DATE) AS date_updated,
        CAST(submission_year AS INTEGER) AS submission_year,
        CAST(submission_month AS INTEGER) AS submission_month,

        -- derived flags
        has_code,
        is_survey
    FROM
        source
)

SELECT
    *
FROM
    renamed
