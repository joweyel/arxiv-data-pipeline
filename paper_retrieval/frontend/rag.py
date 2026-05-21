import json
from typing import Literal
from langchain_core.messages import ToolMessage
from langgraph.graph import START, END, StateGraph, MessagesState

from chains import agent_chain
from tool_executor import _search_context, execute_tools, set_search_context


def agent_node(state: MessagesState) -> MessagesState:
    """Call the LLM agent to decide the next action or generate final answer."""
    response = agent_chain.invoke(
        {
            "messages": state["messages"],
            "categories": ", ".join(_search_context.get("categories", [])),
        }
    )
    return {"messages": [response]}


def should_continue(state: MessagesState) -> Literal["execute_tools", END]:
    """Route to tool execution if the LLM made a tool call, otherwise end."""
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "execute_tools"
    return END


################################
# Building the LangGraph Graph #
################################

# Graph
builder = StateGraph(MessagesState)

# Nodes
builder.add_node("agent", agent_node)
builder.add_node("execute_tools", execute_tools)

# Edges
builder.add_edge(START, "agent")
builder.add_conditional_edges("agent", should_continue, ["execute_tools", END])
builder.add_edge("execute_tools", "agent")

graph = builder.compile()


def ask(
    question: str,
    categories: list[str],
    start_year: int,
    end_year: int,
    top_k: int = 10,
    surveys_only: bool = False,
) -> tuple[str, list[dict]]:
    """Run the LangGraph agent on a research question and return answer with sources.

    Parameters
    ----------
    question: str
        Natural language research question.
    categories: list[str]
        ArXiv category filters.
    start_year: int
        Earliest publication year.
    end_year: int
        Latest publication year.
    top_k: int (default: 10, optional)
        Number of papers to retrieve per tool call.
    surveys_only: bool (default: False, optional)
        Whether to restrict results to survey/overview papers.

    Returns
    -------
    tuple[str, list[dict]]
        Generated answer string and list of retrieved papers.
    """
    set_search_context(categories, start_year, end_year, top_k, surveys_only)

    result = graph.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": question,
                }
            ]
        }
    )
    answer = result["messages"][-1].content

    retrieved = []
    seen_ids: set[str] = set()
    for msg in result["messages"]:
        if isinstance(msg, ToolMessage) and isinstance(msg.content, str):
            try:
                papers = json.loads(msg.content)
                if isinstance(papers, list):
                    for p in papers:
                        if p["arxiv_id"] not in seen_ids:
                            seen_ids.add(p["arxiv_id"])
                            retrieved.append(p)
            except (json.JSONDecodeError, TypeError):
                pass
    return answer, retrieved
