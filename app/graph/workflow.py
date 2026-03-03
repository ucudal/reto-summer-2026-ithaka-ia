"""
Workflow principal de LangGraph para orquestar todos los agentes del sistema Ithaka
"""

import base64
import logging
import os
from typing import Any
import uuid

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph
from langchain_core.messages import HumanMessage
from langsmith import traceable
from langchain_core.tracers.context import tracing_v2_enabled
from langchain_core.tracers.langchain import LangChainTracer

from .agent_descriptions import ROUTABLE_AGENTS
from .state import ConversationState
from ..agents.faq import handle_faq_query
from ..agents.supervisor import route_message, decide_next_agent_wrapper
from ..agents.validator import handle_validation
from ..agents.wizard_node import handle_wizard_flow
from ..services.document_ingestion_service import document_ingestion_service

logger = logging.getLogger(__name__)


class IthakaWorkflow:
    """Workflow principal que maneja toda la lógica de conversación"""

    def __init__(self):
        # Initialize LangSmith tracing
        self.tracing_enabled = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
        self.project_name = os.getenv("LANGCHAIN_PROJECT", "ithaka-project")
        
        if self.tracing_enabled:
            logger.info(f"LangSmith tracing enabled for project: {self.project_name}")
        
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
        # Usar configuración básica para el checkpointer
        return workflow.compile(checkpointer=InMemorySaver())

    _MAX_DOC_CHARS = 30_000

    def _create_initial_state(
        self,
        user_message: str,
        wizard_state: dict[str, Any] | None = None,
        conversation_id: int | None = None,
        user_email: str | None = None,
        attachment: dict | None = None,
    ) -> ConversationState:
        """Crea el estado inicial para el workflow.

        ``user_message`` is always a plain string.  If the frontend sent
        a file, the WS layer passes it via ``attachment`` (dict with
        *filename*, *data* (base64), *media_type*).  We decode it here
        and populate ``document_context`` / ``document_filename``.
        """

        base_state: ConversationState = {
            "messages": [HumanMessage(content=user_message)],
            "conversation_id": conversation_id,
            "user_email": user_email,
            "current_agent": "supervisor",
            "agent_context": {},
        }

        if attachment:
            self._process_attachment(attachment, base_state)

        if wizard_state:
            wizard_state_obj = {
                "wizard_session_id": wizard_state.get("wizard_session_id"),
                "current_question": wizard_state.get("current_question", 1),
                "answers": [],
                "wizard_responses": wizard_state.get("wizard_responses", {}),
                "wizard_status": wizard_state.get("wizard_state", "INACTIVE"),
                "awaiting_answer": wizard_state.get("awaiting_answer", False),
                "messages": [],
                "completed": wizard_state.get("wizard_state") == "COMPLETED",
                "valid": False,
            }
            base_state["wizard_state"] = wizard_state_obj

        return base_state

    def _process_attachment(
        self, attachment: dict, state: ConversationState
    ) -> None:
        """Decode base64 file from *attachment* and store extracted text in state."""
        filename = attachment.get("filename", "document")
        raw_b64 = attachment.get("data", "")
        if not raw_b64:
            logger.warning("[WORKFLOW] Attachment present but 'data' is empty")
            return
        try:
            file_bytes = base64.b64decode(raw_b64)
            _, text = document_ingestion_service.extract_file_text(filename, file_bytes)
            if len(text) > self._MAX_DOC_CHARS:
                text = text[: self._MAX_DOC_CHARS]
            state["document_context"] = text
            state["document_filename"] = filename
            logger.info(
                "[WORKFLOW] Documento procesado: %r (%d chars)", filename, len(text)
            )
        except Exception as e:
            logger.error("[WORKFLOW] Error procesando adjunto: %s", e, exc_info=True)

    @traceable(run_type="chain")
    async def process_message(
        self,
        user_message: str,
        wizard_state: dict[str, Any] | None = None,
        conversation_id: int | None = None,
        thread_id: str | None = None,
        attachment: dict | None = None,
    ) -> dict[str, Any]:
        """Procesa un mensaje del usuario a través del grafo de agentes.

        ``user_message`` is always a plain string.
        ``attachment``, if present, carries the raw file metadata from the WS layer.
        """

        try:
            initial_state = self._create_initial_state(
                user_message=user_message,
                wizard_state=wizard_state,
                conversation_id=conversation_id,
                attachment=attachment,
            )

            if thread_id is None:
                thread_id = str(conversation_id) if conversation_id is not None else "default"

            has_doc = bool(initial_state.get("document_context"))
            logger.info(
                "[WORKFLOW] process_message: text_len=%d has_doc=%s doc_file=%r",
                len(user_message),
                has_doc,
                initial_state.get("document_filename"),
            )
            logger.debug("[WORKFLOW] User message: %r", user_message[:120])
            logger.debug(f"[WORKFLOW] Thread ID: {thread_id}")
            logger.debug(f"[WORKFLOW] Initial state keys: {list(initial_state.keys())}")

            logger.info("Processing message: %s", user_message[:50] + "..." if len(user_message) > 50 else user_message)
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
