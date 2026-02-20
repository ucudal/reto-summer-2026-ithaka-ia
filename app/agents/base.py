"""
Base class for all routable agent nodes in the Ithaka workflow.

Every agent that the supervisor can route to should inherit from AgentNode
and define `name`, `description`, and `handle`.
"""

from abc import ABC, abstractmethod

from ..graph.state import ConversationState


class AgentNode(ABC):
    """Abstract base for a routable agent node.

    Subclasses must define:
        name        – short identifier used as the graph node key (e.g. "faq").
        description – natural-language purpose used by the supervisor to route
                      user messages to the right agent.
        __call__()  – async entry point that LangGraph invokes.
    """

    name: str
    description: str

    @abstractmethod
    async def __call__(self, state: ConversationState) -> ConversationState:
        """Process the current conversation state and return the updated state."""
        ...
