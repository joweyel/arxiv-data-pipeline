WITH arxiv_data AS (
    SELECT
        *
    FROM
        {{ ref('stg_papers') }}
),
arxiv_categories AS (
    SELECT
        *
    FROM
        {{ ref('arxiv_categories') }}
),
extended_arxiv_data AS (
    SELECT
        ad.*,
        ac.group AS category_group,
        ac.name AS category_name
    FROM
        arxiv_data AS ad
    LEFT JOIN arxiv_categories AS ac
        ON ad.primary_category = ac.category_id
)

SELECT
    *
FROM
    extended_arxiv_data
