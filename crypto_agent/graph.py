"""Model configuration and LangGraph workflow for crypto analysis."""

from langchain_core.messages import SystemMessage
from langchain_groq import ChatGroq
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from crypto_agent.config import GROQ_API_KEY
from crypto_agent.prompts import SYSTEM_PROMPT
from crypto_agent.reporting import build_grounded_report
from crypto_agent.tools import (
    crypto_list_tool,
    crypto_data_tool,
    crypto_news_tool,
)


llm = ChatGroq(
    model="openai/gpt-oss-120b",
    api_key=GROQ_API_KEY,
    temperature=0,
    timeout=30,
    max_retries=1,
)

# Register the available tools
tools = [
    crypto_list_tool,
    crypto_data_tool,
    crypto_news_tool,
]

# Prepare the node responsible for executing tool calls
tool_node = ToolNode(tools=tools)

# Bind tool definitions to the model
llm_with_tools = llm.bind_tools(tools)

# Define the agent's role and operating rules
system_message = SystemMessage(content=SYSTEM_PROMPT)


def assistant(state: MessagesState):
    """Call the tool-enabled model with the conversation history."""
    response = llm_with_tools.invoke(
        [system_message] + state["messages"]
    )

    # Finish collecting tools before rendering source-grounded final content.
    if not response.tool_calls:
        report = build_grounded_report(state["messages"])
        if report is not None:
            response = response.model_copy(update={"content": report})

    return {"messages": [response]}


# Create the graph and register its nodes
builder = StateGraph(MessagesState)

builder.add_node("assistant", assistant)
builder.add_node("tools", tool_node)

# Start with the assistant
builder.add_edge(START, "assistant")

# Route to tools when requested; otherwise, finish
builder.add_conditional_edges(
    "assistant",
    tools_condition,
)

# Return tool results to the assistant
builder.add_edge("tools", "assistant")

# Compile a graph without conversation persistence
react_graph = builder.compile()

# Compile a graph with in-memory conversation persistence
memory = InMemorySaver()
react_graph_with_memory = builder.compile(checkpointer=memory)
