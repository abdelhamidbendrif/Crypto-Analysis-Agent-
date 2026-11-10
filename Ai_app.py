import sys
from uuid import uuid4

from langchain_core.messages import AIMessage, HumanMessage

from crypto_agent.graph import react_graph_with_memory


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")

    # Keep one thread throughout the conversation
    config = {
        "configurable": {
            "thread_id": str(uuid4()),
        },
        "recursion_limit": 20,
    }

    print("Crypto Analysis Agent")
    print("Type exit or quit to leave. Ctrl+C also exits.")

    while True:
        try:
            user_input = input("\nYou: ").strip()

            # Ignore empty messages
            if not user_input:
                continue

            # Handle explicit exit commands
            if user_input.lower() in {"exit", "quit"}:
                print("Agent: Goodbye!")
                break

            # Send only the new message; the checkpointer restores history
            result = react_graph_with_memory.invoke(
                {"messages": [HumanMessage(content=user_input)]},
                config=config,
            )

            # Find the final assistant reply
            last_ai = next(
                (
                    message
                    for message in reversed(result["messages"])
                    if isinstance(message, AIMessage)
                    and not message.tool_calls
                ),
                None,
            )

            if last_ai is not None and last_ai.content:
                print(f"\nAgent:\n{last_ai.content}")
            else:
                print("Agent: No final reply was generated. Please try again.")

        except (KeyboardInterrupt, EOFError):
            print("\nAgent: Goodbye!")
            break

        except Exception as error:
            print(
                f"\nAgent: The request failed ({type(error).__name__}). "
                "Check your connection, API settings, or usage limits."
            )

            # Start a clean thread after an interrupted or failed graph run
            config["configurable"]["thread_id"] = str(uuid4())
            print(
                "Agent: A new conversation has been started. "
                "Please ask your question again."
            )