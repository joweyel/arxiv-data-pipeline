from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate


class SearchQuery(BaseModel):
    """Search arxiv papers using vector similarity."""

    query: str = Field(description="Natural language search query for arXiv papers.")
    surveys_only: bool = Field(
        description="Set to True when the user asks for surveys, reviews, or overviews.",
        default=False,
    )


class QueryIntent(BaseModel):
    """Structured intent parsed from a natural language arXiv search query."""

    query: str = Field(
        description=(
            "The core semantic topic to search for, stripped of metadata "
            "like year, category, or code availability."
        )
    )
    categories: list[str] | None = Field(
        default=None,
        description=(
            "ArXiv category codes detected in the query, e.g. ['cs.CV', 'cs.RO']. "
            "Null if no specific category was mentioned."
        ),
    )
    start_year: int | None = Field(
        default=None,
        description="Earliest publication year detected in the query. Null if not mentioned.",
    )
    end_year: int | None = Field(
        default=None,
        description="Latest publication year detected in the query. Null if not mentioned.",
    )
    has_code: bool | None = Field(
        default=None,
        description=(
            "True if the user explicitly wants papers with code/implementation. "
            "Null if not mentioned."
        ),
    )
    surveys_only: bool = Field(
        default=False,
        description="True if the user asks for surveys, reviews, or overviews.",
    )
    top_k: int | None = Field(
        default=None,
        description="Number of results requested by the user. Null if not specified.",
    )


def model_fields(model: type[BaseModel]) -> str:
    """Format Pydantic model fields as a bullet list of name: description pairs.

    Parameters
    ----------
    model : type[BaseModel]
        Any Pydantic model class.

    Returns
    -------
    str
        Newline-separated bullet list, one entry per field.
    """
    field_string = "\n".join(
        f"- {name}: {field.description}" for name, field in model.model_fields.items()
    )
    return field_string


INTENT_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "You are a query parser for an arXiv paper search engine. "
                "Extract the following fields from the user's natural language query:\n\n"
                "{fields}\n\n"
                "Only populate fields that are explicitly or clearly implied. "
                "Leave everything else as null."
            ),
        ),
        ("human", "{query}"),
    ]
)
