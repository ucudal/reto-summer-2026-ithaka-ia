"""
WizardAgent -- routable node that guides users through the postulación flow.

Wraps the wizard sub-graph (wizard_workflow/wizard_graph) behind the
standard AgentNode interface so the supervisor can route to it by
description.
"""

import uuid

from .base import AgentNode
from ..graph.state import ConversationState
from .wizard_workflow.wizard_graph import wizard_graph


class WizardAgent(AgentNode):
    """Guía al usuario a través del proceso de postulación de Ithaka."""

    name = "wizard"
    description = (
        "Guía al usuario a través del proceso de postulación/aplicación: "
        "postular una idea o proyecto, inscripción, formulario de "
        "postulación, emprendimiento, incubadora, startup. También maneja "
        "comandos de navegación del formulario como 'volver' o 'cancelar'."
    )

    async def handle(self, state: ConversationState) -> ConversationState:
        """Ejecuta el sub-grafo del wizard y devuelve el estado actualizado."""

        wizard_state = state.get("wizard_state")

        if not wizard_state:
            wizard_state = {
                "wizard_session_id": str(uuid.uuid4()),
                "current_question": 1,
                "answers": [],
                "wizard_responses": {},
                "wizard_status": "ACTIVE",
                "awaiting_answer": False,
                "messages": state.get("messages", []),
                "completed": False,
                "valid": False,
            }
        else:
            wizard_state = dict(wizard_state)
            wizard_state["messages"] = state.get("messages", [])

        result = await wizard_graph.ainvoke(wizard_state)

        return {
            **state,
            "wizard_state": result,
            "messages": result.get("messages", []),
            "agent_context": {
                "response": (
                    result.get("messages", [])[-1].content
                    if result.get("messages")
                    else ""
                )
            },
        }


# ------------------------------------------------------------------
# Module-level instance & wrapper for LangGraph
# ------------------------------------------------------------------

wizard_agent = WizardAgent()


async def handle_wizard_flow(state: ConversationState) -> ConversationState:
    """Función wrapper para LangGraph."""
    return await wizard_agent.handle(state)
