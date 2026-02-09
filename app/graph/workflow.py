"""
Workflow principal de LangGraph para orquestar todos los agentes del sistema Ithaka
"""

import logging
from datetime import datetime
from typing import Any
import uuid

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph
from langchain_core.messages import HumanMessage

from .state import ConversationState
from ..agents.faq import handle_faq_query
from ..agents.supervisor import route_message, decide_next_agent_wrapper
from ..agents.wizard_workflow.wizard_graph import wizard_graph

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
        # workflow.add_node("wizard", handle_wizard_flow)

        workflow.add_node("wizard", handle_wizard_flow_good)

        workflow.add_node("faq", handle_faq_query)

        # Definir punto de entrada
        workflow.set_entry_point("supervisor")

        # Agregar bordes condicionales desde el supervisor
        workflow.add_conditional_edges(
            "supervisor",
            decide_next_agent_wrapper,
            {
                "wizard": "wizard",
                "faq": "faq",
                "end": END
            }
        )

        # El wizard puede continuar consigo mismo o terminar
        # workflow.add_conditional_edges(
        #     "wizard",
        #     self._wizard_should_continue,
        #     {
        #         "continue": "wizard",
        #         "end": END
        #     }
        # )

        # Los otros agentes terminan el flujo
        workflow.add_edge("wizard", END)
        workflow.add_edge("faq", END)

        # Compilar el grafo
        return workflow.compile(checkpointer=InMemorySaver())

    def _wizard_should_continue(self, state: ConversationState) -> str:
        """Determina si el wizard debe continuar o terminar"""
        wizard_state = state.get("wizard_state", "INACTIVE")
        next_action = state.get("next_action", "complete")

        # Si está completado o hay error, terminar
        if wizard_state in ["COMPLETED", "ERROR"]:
            return "end"

        # Si el wizard está activo y necesita enviar respuesta, terminar (no continuar)
        # El wizard debe terminar después de procesar la respuesta del usuario
        if wizard_state == "ACTIVE" and next_action == "send_response":
            return "end"

        # Si no hay decisión clara, terminar
        return "end"

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
                "current_question": wizard_state.get("current_question", 0),
                "answers": [],
                "wizard_responses": wizard_state.get("wizard_responses", {}),
                "wizard_status": wizard_state.get("wizard_state", "INACTIVE"),
                "awaiting_answer": wizard_state.get("awaiting_answer", False),
                "messages": [],
                "completed": wizard_state.get("wizard_state") == "COMPLETED"
            }
        else:
            # Crear WizardState por defecto para nuevos wizards
            wizard_state_obj = {
                "wizard_session_id": str(uuid.uuid4()),
                "current_question": 1,  # Cambiar de 0 a 1 - las preguntas empiezan en 1
                "answers": [],
                "wizard_responses": {},
                "wizard_status": "ACTIVE",
                "awaiting_answer": False,
                "messages": [],
                "completed": False,
                "valid": False  # Inicializar valid
            }

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
            wizard_state: dict[str, Any] = None
    ) -> dict[str, Any]:
        """Procesa un mensaje del usuario a través del grafo de agentes"""

        try:
            # Crear estado inicial
            initial_state = self._create_initial_state(
                user_message=user_message,
                wizard_state=wizard_state
            )

            logger.info(f"Processing message: {user_message[:50]}...")
            result = await self.graph.ainvoke(initial_state)

            # Extraer información relevante del resultado
            wizard_state_obj = result.get("wizard_state")
            response_data = {
                "response": result.get("agent_context", {}).get("response", "Lo siento, no pude procesar tu mensaje."),
                "agent_used": result.get("current_agent", "unknown")
            }

            # Si hay wizard state, extraer sus campos
            if wizard_state_obj:
                response_data.update({
                    "wizard_session_id": wizard_state_obj.get("wizard_session_id"),
                    "wizard_state": wizard_state_obj.get("wizard_status", "INACTIVE"),
                    "current_question": wizard_state_obj.get("current_question"),
                    "wizard_responses": wizard_state_obj.get("wizard_responses", {}),
                    "awaiting_answer": wizard_state_obj.get("awaiting_answer", False)
                })
            else:
                response_data.update({
                    "wizard_session_id": None,
                    "wizard_state": "INACTIVE",
                    "current_question": 1,
                    "wizard_responses": {},
                    "awaiting_answer": False
                })

            logger.info(f"Message processed successfully by {response_data['agent_used']}")
            return response_data

        except Exception as e:
            logger.error(f"Error processing message through workflow: {e}")
            return {
                "response": "Lo siento, tuve un problema técnico procesando tu mensaje. ¿Podrías intentar de nuevo?",
                "agent_used": "error_handler",
                "wizard_session_id": None,
                "wizard_state": "INACTIVE",
                "current_question": 1,
                "awaiting_answer": False,
                "error": str(e)
            }


async def handle_wizard_flow_good(state: dict) -> dict:
    """Maneja el flujo del wizard de manera correcta"""

    # Extraer el wizard_state del ConversationState
    wizard_state = state.get("wizard_state")

    if not wizard_state:
        # Si no hay wizard_state, crear uno por defecto
        import uuid
        wizard_state = {
            "wizard_session_id": str(uuid.uuid4()),
            "current_question": 1,  # Cambiar de 0 a 1 para coincidir con WIZARD_QUESTIONS
            "answers": [],
            "wizard_responses": {},
            "wizard_status": "ACTIVE",
            "awaiting_answer": False,
            "messages": state.get("messages", []),
            "completed": False,
            "valid": False  # Agregar campo valid
        }
    else:
        # Asegurar que tiene los mensajes del ConversationState
        wizard_state = dict(wizard_state)  # Hacer una copia
        wizard_state["messages"] = state.get("messages", [])

    # Pasar solo el wizard_state al wizard_graph
    result = await wizard_graph.ainvoke(wizard_state)

    # Actualizar el ConversationState con el resultado del wizard
    return {
        **state,  # Mantener campos del ConversationState
        "wizard_state": result,  # Actualizar con resultado del wizard
        "messages": result.get("messages", []),  # Usar los mensajes del wizard para el frontend
        "agent_context": {"response": result.get("messages", [])[-1].content if result.get("messages") else ""}
    }
