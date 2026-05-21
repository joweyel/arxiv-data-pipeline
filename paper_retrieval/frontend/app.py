import streamlit as st
import pandas as pd
from retrieval import search, get_intent_parser
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
    with st.spinner("Parsing query..."):
        intent = get_intent_parser().invoke({"query": query})

    with st.expander("Detected Intent", expanded=True):
        col1, col2, col3 = st.columns(3)
        col1.metric(
            "Categories", ", ".join(intent.categories) if intent.categories else "all"
        )
        col2.metric(
            "Years",
            f"{intent.start_year or start_year} - {intent.end_year or end_year}",
        )
        col3.metric("Surveys only", "yes" if intent.surveys_only else "no")

    resolved_categories = intent.categories or selected_categories
    resolved_start = intent.start_year or start_year
    resolved_end = intent.end_year or end_year
    resolved_top_k = intent.top_k or top_k

    with st.spinner("Searching..."):
        if mode == "Search":
            results = search(
                intent.query,
                resolved_categories,
                resolved_start,
                resolved_end,
                resolved_top_k,
                use_hyde,
                intent.surveys_only,
            )
            answer = None
        elif mode == "Ask":
            answer, results = ask(
                intent.query,
                resolved_categories,
                resolved_start,
                resolved_end,
                resolved_top_k,
                intent.surveys_only,
            )
        else:
            raise ValueError(f"Query-Mode [{mode}] not implemented.")

    if mode == "Ask" and answer:
        st.subheader("Answer")
        st.write(answer)
        st.divider()

    st.subheader(f"Retrieved Papers ({len(results)})")
    st.dataframe(pd.DataFrame(results))
