import argparse
import sys

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from crypto_agent.config import GROQ_API_KEY
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
system_message = SystemMessage(
    content="""
You are a Crypto Market Analyst.

Use tools whenever current cryptocurrency data or news is needed:
- crypto_list_tool: discover supported cryptocurrency symbols.
- crypto_data_tool: retrieve market data for a specific symbol.
- crypto_news_tool: search for relevant cryptocurrency news.

For comparisons, retrieve data for every requested coin and search for
each coin's news when requested. Keep tool results compact.
Use the conversation history to understand follow-up questions, and
retrieve a fresh snapshot when the user asks for current data.

Never invent prices, article details, currency, timezone, range period,
percentage-change baseline, liquidity, or future performance.
Treat field_context as metadata describing what the response does not specify.
Explain tool failures honestly. Never treat a news headline as proof of causation.

The application renders tool-backed final reports directly from the returned
data in English. Focus on gathering the evidence required for the question.
For conversational replies without tool results, match the user's language
and keep internal function names out of the answer.
"""
)


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

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Run a crypto analysis test query.")
    parser.add_argument(
        "query",
        nargs="?",
        default="Give me current market data for BTC and explain the key metrics in bullets.",
    )
    args = parser.parse_args()

    # Create the user's test message
    messages = [HumanMessage(content=args.query)]

    # Run the complete agent workflow
    out = react_graph.invoke({"messages": messages})

    # Display the conversation, tool calls, and tool results
    for message in out["messages"]:
        message.pretty_print()
