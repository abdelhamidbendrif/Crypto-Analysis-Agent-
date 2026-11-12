"""Session-only navigation and conversation switching, independent of API logic."""

from uuid import uuid4


TURN_KEYS = ("history", "chat", "evidence", "last_report", "elapsed", "live_graph")


def initialize(state):
    """Create defaults without replacing existing conversations or preferences."""
    for key, value in (("appearance", "Light"), ("mode", "Demo"), ("view", "Research Desk"),
                       ("conversations", {}), ("first_asset", "BTC"), ("second_asset", "ETH"),
                       ("news_topic", "bitcoin")):
        state.setdefault(key, value)
    if "thread_id" not in state:
        state["thread_id"] = str(uuid4())
    for key, value in (("history", []), ("chat", []), ("evidence", []),
                       ("last_report", ""), ("elapsed", None)):
        state.setdefault(key, value)
    state.setdefault("active_mode", state["mode"])


def save_conversation(state):
    """Retain the checkpoint graph with the conversation it belongs to."""
    if state.get("chat"):
        record = {key: state[key] for key in TURN_KEYS if key in state}
        record["mode"] = state.get("active_mode", state["mode"])
        state["conversations"][state["thread_id"]] = record


def new_conversation(state, archive=True):
    """Start a fresh thread while retaining theme, selections and saved sessions."""
    if archive:
        save_conversation(state)
    else:
        state["conversations"].pop(state["thread_id"], None)
    for key in (*TURN_KEYS, "notice"):
        state.pop(key, None)
    state["thread_id"] = str(uuid4())
    state["active_mode"] = state["mode"]
    state["view"] = "Research Desk"
    initialize(state)


def change_mode(state):
    """Archive the previous mode before creating an isolated thread for the new mode."""
    new_conversation(state)


def open_conversation(state, thread_id):
    """Restore a same-mode conversation, including its private live graph."""
    record = state["conversations"][thread_id]
    if record["mode"] != state["mode"]:
        raise ValueError("Cannot restore a conversation from another data mode")
    save_conversation(state)
    for key in TURN_KEYS:
        state.pop(key, None)
        if key in record:
            state[key] = record[key]
    state["thread_id"] = thread_id
    state["active_mode"] = record["mode"]
    state["view"] = "Research Desk"
    initialize(state)


def set_view(state, view):
    state["view"] = view


def keep_selection(state, key):
    """Preserve selections when Streamlit cleans up widgets on hidden views."""
    state[key] = state[f"_{key}"]
