import sys

from langchain_core.messages import HumanMessage

from crypto_agent.graph import react_graph_with_memory


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")

    # Reuse the same thread for both turns
    config = {
        "configurable": {
            "thread_id": "crypto-thread-1",
        }
    }

    questions = [
        "Give me current market data for BTC.",
        "Give me three recent news articles about the same cryptocurrency.",
    ]

    seen_messages = 0

    for turn, question in enumerate(questions, start=1):
        print(f"\n========== Turn {turn} ==========")

        # Send only the new user message
        result = react_graph_with_memory.invoke(
            {"messages": [HumanMessage(content=question)]},
            config=config,
        )

        # Display only messages added during this turn
        for message in result["messages"][seen_messages:]:
            message.pretty_print()

        seen_messages = len(result["messages"])