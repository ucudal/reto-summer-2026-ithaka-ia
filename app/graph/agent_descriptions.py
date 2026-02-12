"""
Registry of routable agents and their descriptions.

Descriptions are defined on each AgentNode subclass (single source of truth).
This module collects them so both the workflow (conditional edges) and the
supervisor (LLM routing prompt) can import a flat list without depending on
each agent module directly.

To add a new agent:
  1. Create a class that inherits from AgentNode (define name, description, handle).
  2. Import the class here and add it to _AGENT_CLASSES.
  3. Register its node in workflow.py.
"""

from ..agents.faq import FAQAgent
from ..agents.wizard_node import WizardAgent

_AGENT_CLASSES = [FAQAgent, WizardAgent]

ROUTABLE_AGENTS: list[tuple[str, str]] = [
    (cls.name, cls.description) for cls in _AGENT_CLASSES
]

# Derived helpers
ROUTABLE_AGENT_NAMES: set[str] = {name for name, _ in ROUTABLE_AGENTS}
DEFAULT_AGENT: str = "faq"
