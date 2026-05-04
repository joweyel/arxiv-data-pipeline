import os
import torch
import streamlit as st

# HF
from transformers import AutoTokenizer
from adapters import AutoAdapterModel

# LangChain
from langchain_core.embeddings import Embeddings
from langchain_core.prompts import PromptTemplate
from langchain_classic.chains.hyde.base import HypotheticalDocumentEmbedder
from langchain_openai import ChatOpenAI

MODEL_ID: str = "allenai/specter2_base"
ADAPTER_ID: str = "allenai/specter2"


@st.cache_resource
def load_specter2_model():
    """Load SPECTER2 base model with proximity adapter.

    Returns
    -------
    tuple[AutoTokenizer, AutoAdapterModel]
        Tokenizer and model with activated proximity adapter.
    """
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tokenizer = AutoTokenizer.from_pretrained(pretrained_model_name_or_path=MODEL_ID)
    model = AutoAdapterModel.from_pretrained(pretrained_model_name_or_path=MODEL_ID)
    model.load_adapter(ADAPTER_ID, source="hf", load_as="proximity", set_active=True)
    model = model.to(device)
    model.eval()
    return tokenizer, model


@torch.no_grad()
def get_query_embedding(query: str) -> list[float]:
    """Embed input query with SPECTER2 and return the CLS-token.

    Parameters
    ----------
    query: str
        Input query text to embed.

    Returns
    -------
    list[float]
        SPECTER2-Embedding vector (768 dimensional).
    """
    tokenizer, model = load_specter2_model()
    inputs = tokenizer(
        query,
        padding=True,
        truncation=True,
        return_tensors="pt",
        max_length=512,
    )
    output = model(**inputs)
    embedding = output.last_hidden_state[:, 0, :].squeeze()
    return embedding.float().tolist()


class Specter2Embeddings(Embeddings):
    """LangChain-compatible embeddings wrapper for SPECTER2."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed list of documents.

        Parameters
        ----------
        texts: list[str]

        Returns
        -------
        list[list[float]]
            List of embedding vectors.
        """
        return [get_query_embedding(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        """Embed single input query.

        Parameters
        ----------
        text: str
            Query to embed.

        Returns
        -------
        list[float]
            Embedding vector
        """
        return get_query_embedding(text)


@st.cache_resource
def get_embedder(use_hyde: bool = True) -> Embeddings:
    """Get Embedder, optionally wrapped with HyDE
    - Hypothetical Document Embeddings
    - https://arxiv.org/abs/2212.10496

    Parameters
    ----------
    use_hyde: bool (default: True)
        If True, wraps SPECTER2 with HypotheticalDocumentEmbedder so that
        queries are expanded into hypothetical abstracts before embedding.

    Returns
    -------
    Embeddings
        Specter2Embeddings or HypotheticalDocumentEmbedder instance.
    """
    specter2 = Specter2Embeddings()
    if not use_hyde:
        return specter2
    hyde_prompt = PromptTemplate.from_template(
        "Write a concise arXiv abstract for a paper about: {QUESTION}"
    )
    specter2_hyde = HypotheticalDocumentEmbedder.from_llm(
        llm=ChatOpenAI(
            model="gpt-4o-mini",
            api_key=os.getenv("OPENAI_API_KEY"),
        ),
        base_embeddings=specter2,
        custom_prompt=hyde_prompt,
    )
    return specter2_hyde


def search(
    query: str,
    categories: list[str],
    start_year: int,
    end_year: int,
    top_k: int = 10,
    use_hyde: bool = True,
) -> list[dict]:
    """Search papers that are semantically relevant to the input query.

    Parameter
    ---------
    query: str
        Search query.
    categories: list[str]
        Relevant arxiv categories to search.
    start_year: int
        Earliest year of publication.
    end_year: int
        Latest year of publication.
    top_k: int (default: 10, optional)
        Number of top results to return.
    use_hyde: bool (default: True, optional)
        Wether to use a HyDE Query before Embedding or not.

    Returns
    -------
    list[dict]
        Ranked list of query results from DWH with following content.
        - arxiv_id
        - title, authors
        - date_published
        - primary_category
        - abstract
        - similarity score
    """

    from bq_queries import vector_search

    embedder = get_embedder(use_hyde)
    embedding = embedder.embed_query(query)
    return vector_search(embedding, categories, start_year, end_year, top_k)
