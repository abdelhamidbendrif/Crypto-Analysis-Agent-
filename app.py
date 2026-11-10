"""Command-line entry point for a single crypto analysis query."""

import argparse
import sys

from langchain_core.messages import HumanMessage

# Keep both graph imports available for existing callers.
from crypto_agent.graph import react_graph, react_graph_with_memory


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
