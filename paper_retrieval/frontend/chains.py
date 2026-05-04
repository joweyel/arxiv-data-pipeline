import os
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from schemas import SearchQuery

llm = ChatOpenAI(model="gpt-4o", api_key=os.getenv("OPENAI_API_KEY"))

agent_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are a research paper assistant with access to a database of arXiv papers.
Available categories: {categories}

Use the SearchQuery tool to retrieve relevant papers before answering.
- For general queries: call SearchQuery with surveys_only=False
- For survey, review, or overview requests: call SearchQuery with surveys_only=True
- You may call SearchQuery multiple times with different queries if needed

When answering, cite papers by their arxiv_id in brackets like [2301.12345].
Keep your answer concise and grounded in the retrieved papers.""",
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
)

# Agent chain - LLM decides when to call SearchQuery and when to stop
agent_chain = agent_prompt | llm.bind_tools([SearchQuery])
