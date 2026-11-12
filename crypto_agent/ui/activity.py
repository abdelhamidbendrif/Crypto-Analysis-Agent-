"""Forward safe tool lifecycle events from worker threads to the UI thread."""

from concurrent.futures import ThreadPoolExecutor
from queue import Empty, Queue

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import HumanMessage


TOOL_LABELS = {"crypto_list_tool": "Supported assets", "crypto_data_tool": "Market data", "crypto_news_tool": "News search"}


class ToolActivity(BaseCallbackHandler):
    def __init__(self, events):
        self.events = events

    def on_tool_start(self, serialized, input_str, *, run_id, **kwargs):
        name = (serialized or {}).get("name", "")
        self.events.put((str(run_id), TOOL_LABELS.get(name, "Research tool"), "Running"))

    def on_tool_end(self, output, *, run_id, **kwargs):
        self.events.put((str(run_id), None, "Returned"))

    def on_tool_error(self, error, *, run_id, **kwargs):
        self.events.put((str(run_id), None, "Failed"))


def invoke_with_activity(graph, query, thread_id, on_progress):
    """Keep Streamlit calls on the main thread while the existing graph invokes."""
    events = Queue()
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 20,
              "callbacks": [ToolActivity(events)]}
    steps = {}
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(graph.invoke, {"messages": [HumanMessage(content=query)]}, config=config)
        while True:
            try:
                run_id, name, status = events.get(timeout=0.1)
                prior = steps.get(run_id, ("Research tool", "Running"))
                steps[run_id] = (name or prior[0], status)
                on_progress(list(steps.values()))
            except Empty:
                if future.done():
                    break
        return future.result()
