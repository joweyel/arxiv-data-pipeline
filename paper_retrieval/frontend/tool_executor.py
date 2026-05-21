import json
from langchain_core.tools import StructuredTool
from langgraph.prebuilt import ToolNode
from retrieval import get_embedder
from bq_queries import vector_search
from schemas import SearchQuery

# Injected at query time via set_search_context()
_search_context: dict = {}


def set_search_context(
    categories: list[str],
    start_year: int,
    end_year: int,
    top_k: int = 10,
    surveys_only: bool = False,
) -> None:
    """Set the search context for the current query.

    Parameters
    ----------
    categories: list[str]
        List of arXiv categories to filter.
    start_year: int
        Earliest publication year.
    end_year: int
        Latest publication year.
    top_k: int (default: 10, optional)
        Number of papers to retrieve per tool call. Default is 10.
    surveys_only: bool (default: False, optional)
        Whether to restrict results to survey/overview papers.
    """
    global _search_context
    _search_context = {
        "categories": categories,
        "start_year": start_year,
        "end_year": end_year,
        "top_k": top_k,
        "surveys_only": surveys_only,
    }


def run_vector_search(
    query: str,
) -> str:
    """Run BQ VECTOR_SEARCH with SPECTER2 + HyDE embeddings.

    Parameters
    ----------
    query: str
        Search query.

    Returns
    -------
    str
        JSON-serialized list of ranked papers with arxiv_id, title,
        date_published, primary_category, abstract, and similarity score.
    """
    context: dict = _search_context
    embedder = get_embedder(use_hyde=True)
    embedding = embedder.embed_query(query)
    results: list[dict] = vector_search(
        query_embeddings=embedding,
        categories=context["categories"],
        start_year=context["start_year"],
        end_year=context["end_year"],
        top_k=context.get("top_k", 10),
        surveys_only=context.get("surveys_only", False),
    )
    return json.dumps(results, default=str)


execute_tools = ToolNode(
    [StructuredTool.from_function(run_vector_search, name=SearchQuery.__name__)]
)
