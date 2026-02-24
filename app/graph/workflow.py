"""
Workflow principal de LangGraph para orquestar todos los agentes del sistema Ithaka
"""

import logging
from typing import Any
import uuid

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph
from langchain_core.messages import HumanMessage

from .agent_descriptions import ROUTABLE_AGENTS
from .state import ConversationState
from ..agents.faq import handle_faq_query
from ..agents.supervisor import route_message, decide_next_agent_wrapper
from ..agents.validator import handle_validation
from ..agents.wizard_node import handle_wizard_flow

logger = logging.getLogger(__name__)


class IthakaWorkflow:
    """Workflow principal que maneja toda la lógica de conversación"""

    def __init__(self):
        self.graph = self._build_graph()

    def _build_graph(self) -> CompiledStateGraph:
        """Construye el grafo de estados LangGraph"""

        # Crear el grafo con el estado compartido
        workflow = StateGraph(ConversationState)

        # Agregar nodos (agentes)
        workflow.add_node("supervisor", route_message)
        workflow.add_node("wizard", handle_wizard_flow)
        workflow.add_node("validator", handle_validation)
        workflow.add_node("faq", handle_faq_query)

        # Definir punto de entrada
        workflow.set_entry_point("supervisor")

        # Agregar bordes condicionales desde el supervisor.
        # El mapa se construye desde ROUTABLE_AGENTS (single source of truth).
        edges = {name: name for name, _ in ROUTABLE_AGENTS}
        edges["end"] = END

        workflow.add_conditional_edges(
            "supervisor",
            decide_next_agent_wrapper,
            edges,
        )

        # Los otros agentes terminan el flujo
        workflow.add_edge("wizard", END)
        workflow.add_edge("validator", END)
        workflow.add_edge("faq", END)

        # Compilar el grafo
        return workflow.compile(checkpointer=InMemorySaver())

    def _create_initial_state(
            self,
            user_message: str,
            wizard_state: dict[str, Any] = None
    ) -> ConversationState:
        """Crea el estado inicial para el workflow"""

        # Crear WizardState - siempre crear uno si no existe para wizard
        wizard_state_obj = None
        if wizard_state:
            wizard_state_obj = {
                "wizard_session_id": wizard_state.get("wizard_session_id"),
                "current_question": wizard_state.get("current_question", 1),
                "answers": [],
                "wizard_responses": wizard_state.get("wizard_responses", {}),
                "wizard_status": wizard_state.get("wizard_state", "INACTIVE"),
                "awaiting_answer": wizard_state.get("awaiting_answer", False),
                "messages": [],
                "completed": wizard_state.get("wizard_state") == "COMPLETED"
            }
        else:
            # No iniciar wizard hasta que el supervisor lo decida.
            wizard_state_obj = None

        return {
            "messages": [HumanMessage(content=user_message)],
            "conversation_id": None,
            "user_email": None,
            "current_agent": "supervisor",
            "agent_context": {},
            "wizard_state": wizard_state_obj
        }

    async def process_message(
            self,
            user_message: str,
            wizard_state: dict[str, Any] = None,
            thread_id: str = "default"
    ) -> dict[str, Any]:
        """Procesa un mensaje del usuario a través del grafo de agentes"""

        try:
            # Crear estado inicial
            initial_state = self._create_initial_state(
                user_message=user_message,
                wizard_state=wizard_state
            )

            logger.debug("=" * 80)
            logger.debug("[WORKFLOW] process_message called")
            logger.debug(f"[WORKFLOW] User message: {user_message!r}")
            logger.debug(f"[WORKFLOW] Thread ID: {thread_id}")
            logger.debug(f"[WORKFLOW] Incoming wizard_state: {wizard_state}")
            logger.debug(f"[WORKFLOW] Initial state keys: {list(initial_state.keys())}")
            ws = initial_state.get("wizard_state") or {}
            logger.debug(f"[WORKFLOW] Initial wizard_state: status={ws.get('wizard_status')}, "
                         f"question={ws.get('current_question')}, "
                         f"awaiting={ws.get('awaiting_answer')}, "
                         f"completed={ws.get('completed')}")

            logger.info(f"Processing message: {user_message[:50]}...")
            config = {"configurable": {"thread_id": thread_id}}
            result = await self.graph.ainvoke(initial_state, config=config)

            logger.debug(f"[WORKFLOW] Graph result keys: {list(result.keys())}")
            logger.debug(f"[WORKFLOW] Result current_agent: {result.get('current_agent')}")
            logger.debug(f"[WORKFLOW] Result agent_context: {result.get('agent_context')}")

            # Extraer información relevante del resultado
            wizard_state_obj = result.get("wizard_state")
            response_data = {
                "response": result.get("agent_context", {}).get("response", "Lo siento, no pude procesar tu mensaje."),
                "agent_used": result.get("current_agent", "unknown")
            }

            # Si hay wizard state, extraer sus campos
            if wizard_state_obj:
                logger.debug(f"[WORKFLOW] Result wizard_state: status={wizard_state_obj.get('wizard_status')}, "
                             f"question={wizard_state_obj.get('current_question')}, "
                             f"completed={wizard_state_obj.get('completed')}")
                response_data.update({
                    "wizard_session_id": wizard_state_obj.get("wizard_session_id"),
                    "wizard_state": wizard_state_obj.get("wizard_status", "INACTIVE"),
                    "current_question": wizard_state_obj.get("current_question"),
                    "wizard_responses": wizard_state_obj.get("wizard_responses", {}),
                    "awaiting_answer": wizard_state_obj.get("awaiting_answer", False)
                })
            else:
                logger.debug("[WORKFLOW] No wizard_state in result")
                response_data.update({
                    "wizard_session_id": None,
                    "wizard_state": "INACTIVE",
                    "current_question": 1,
                    "wizard_responses": {},
                    "awaiting_answer": False
                })

            logger.info(f"[WORKFLOW] Message processed by {response_data['agent_used']}")
            logger.debug(f"[WORKFLOW] Final response (first 200 chars): {response_data['response'][:200]!r}")
            return response_data

        except Exception as e:
            logger.error(f"[WORKFLOW] Error processing message: {e}", exc_info=True)
            return {
                "response": "Lo siento, tuve un problema técnico procesando tu mensaje. ¿Podrías intentar de nuevo?",
                "agent_used": "error_handler",
                "wizard_session_id": None,
                "wizard_state": "INACTIVE",
                "current_question": 1,
                "awaiting_answer": False,
                "error": str(e)
            }
