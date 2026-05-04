import streamlit as st
import pandas as pd
from retrieval import search
from rag import ask

CATEGORIES: list[str] = ["cs.CV", "cs.LG", "cs.RO", "cs.AI"]


st.set_page_config(page_title="ArXiv Paper Search", layout="wide")
st.title("ArXiv Paper Search")

with st.sidebar:
    mode = st.radio("Mode", ["Search", "Ask"], horizontal=True)
    use_hyde = st.toggle("HyDE (for abstract queries)")
    selected_categories = st.multiselect(
        "Categories", CATEGORIES, default=["cs.CV", "cs.LG", "cs.RO", "cs.AI"]
    )
    start_year, end_year = st.slider(
        "Years", min_value=2007, max_value=2026, value=(2020, 2026)
    )
    top_k = st.slider("Results", 5, 20, 10)


query = st.text_input(
    "Query", placeholder="e. g. foundational papers for diffusion models"
)

if st.button("Search") and query:
    # Search and Ask mode
    # - Search (Semantic Search): get list of most relevant files
    # - Ask (RAG): get most relevant files and answer question based on result
    with st.spinner("Searching..."):
        if mode == "Search":
            results = search(
                query,
                selected_categories,
                start_year,
                end_year,
                top_k,
                use_hyde,
            )
            answer = None
        elif mode == "Ask":
            answer, results = ask(
                query,
                selected_categories,
                start_year,
                end_year,
                top_k,
            )
        else:
            raise ValueError(f"Query-Mode [{mode}] not implemented.")

    if mode == "Ask" and answer:
        st.subheader("Answer")
        st.write(answer)
        st.divider()

    st.subheader(f"Retrieved Papers ({len(results)})")
    st.dataframe(pd.DataFrame(results))
