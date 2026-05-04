from pydantic import BaseModel, Field


class SearchQuery(BaseModel):
    """Search arxiv papers using vector similarity."""

    query: str = Field(description="Natural language search query for arXiv papers.")
    surveys_only: bool = Field(
        description="Set to True when the user asks for surveys, reviews, or overviews.",
        default=False,
    )
