"""LangGraph agent state definition."""
from typing import Annotated, Any, Dict, List, Optional, TypedDict
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """Shared state flowing through the LangGraph agent."""

    # Conversation history (LangGraph message reducer appends new messages)
    messages: Annotated[list, add_messages]

    # Sales rep identity
    rep_id: str

    # Session key for multi-turn chat
    session_id: str

    # Currently discussed / selected HCP
    current_hcp: Optional[Dict[str, Any]]

    # Partially filled form fields extracted from chat / tools
    form_data: Dict[str, Any]

    # Last tool execution result (raw)
    tool_output: Optional[Any]

    # Names of tools invoked in this turn (for frontend visibility)
    tools_used: List[str]

    # Interaction id if one was created/updated this turn
    interaction_id: Optional[int]

    # Final user-facing reply
    final_response: str
