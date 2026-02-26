"""
WizardAgent -- routable node that guides users through the postulacion flow.

Wraps the wizard sub-graph (wizard_workflow/wizard_graph) behind the
standard AgentNode interface so the supervisor can route to it by
description.
"""

import logging
import uuid
from pathlib import Path

import yaml

from .base import AgentNode
from ..db.config.database import SessionLocal
from ..graph.state import ConversationState
from ..services import conversation_service
from ..services.backoffice_service import (
    BackofficeIntegrationDisabled,
    send_postulation_to_backoffice,
)
from .wizard_workflow.wizard_graph import wizard_graph

logger = logging.getLogger(__name__)

_config = yaml.safe_load((Path(__file__).parent / "config" / "wizard.yaml").read_text())


class WizardAgent(AgentNode):
    """Guia al usuario a traves del proceso de postulacion de Ithaka."""

    name: str = _config["name"]
    description: str = _config["description"]

    async def __call__(self, state: ConversationState) -> ConversationState:
        """Ejecuta el sub-grafo del wizard y devuelve el estado actualizado."""

        logger.debug("=" * 60)
        logger.debug("[WIZARD_NODE] __call__ invoked")

        wizard_state = state.get("wizard_state")

        if not wizard_state:
            logger.debug("[WIZARD_NODE] No existing wizard_state, creating new one")
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

        logger.debug("[WIZARD_NODE] Wizard state before sub-graph invoke:")
        logger.debug("[WIZARD_NODE]   session_id=%s", wizard_state.get("wizard_session_id"))
        logger.debug("[WIZARD_NODE]   current_question=%s", wizard_state.get("current_question"))
        logger.debug("[WIZARD_NODE]   wizard_status=%s", wizard_state.get("wizard_status"))
        logger.debug("[WIZARD_NODE]   awaiting_answer=%s", wizard_state.get("awaiting_answer"))
        logger.debug("[WIZARD_NODE]   completed=%s", wizard_state.get("completed"))
        logger.debug("[WIZARD_NODE]   answers count=%d", len(wizard_state.get("answers", [])))
        logger.debug("[WIZARD_NODE]   messages count=%d", len(wizard_state.get("messages", [])))
        for i, msg in enumerate(wizard_state.get("messages", [])):
            logger.debug("[WIZARD_NODE]   msg[%d] type=%s content=%r...", i, msg.type, msg.content[:100])

        result = await wizard_graph.ainvoke(wizard_state)

        response_content = (
            result.get("messages", [])[-1].content if result.get("messages") else ""
        )

        logger.debug("[WIZARD_NODE] Sub-graph result:")
        logger.debug("[WIZARD_NODE]   current_question=%s", result.get("current_question"))
        logger.debug("[WIZARD_NODE]   completed=%s", result.get("completed"))
        logger.debug("[WIZARD_NODE]   wizard_status=%s", result.get("wizard_status"))
        logger.debug("[WIZARD_NODE]   response (first 200 chars): %r", response_content[:200])

        # --- Persistencia en DB ---
        conv_id = state.get("conversation_id")
        wizard_responses = result.get("wizard_responses", {})
        email = wizard_responses.get("email")

        try:
            async with SessionLocal() as db_session:
                try:
                    conv_id = await conversation_service.get_or_create_conversation(
                        db_session, conv_id, email=email
                    )

                    # Guardar mensaje del usuario
                    user_msgs = [m for m in state.get("messages", []) if m.type == "human"]
                    if user_msgs:
                        await conversation_service.save_message(
                            db_session, conv_id, "user", user_msgs[-1].content
                        )

                    # Guardar respuesta del asistente
                    if response_content:
                        await conversation_service.save_message(
                            db_session, conv_id, "assistant", response_content
                        )

                    # Actualizar WizardSession con los datos del paso actual
                    ws = await conversation_service.get_or_create_wizard_session(db_session, conv_id)
                    wizard_state_str = "COMPLETED" if result.get("completed") else "ACTIVE"
                    await conversation_service.update_wizard_session(
                        db_session,
                        ws,
                        result.get("current_question", 1),
                        wizard_responses,
                        wizard_state_str,
                    )

                    await db_session.commit()
                except Exception:
                    await db_session.rollback()
                    raise
        except Exception as exc:
            logger.error("[WIZARD_NODE] Error al persistir en DB: %s", exc, exc_info=True)

        # --- Enviar al Backoffice API cuando el wizard termina ---
        logger.info(
            "[WIZARD_NODE] Evaluando envio al Backoffice: completed=%s, has_wizard_responses=%s, email=%s",
            bool(result.get("completed")),
            bool(wizard_responses),
            email,
        )

        if result.get("completed") and wizard_responses:
            logger.info(
                "[WIZARD_NODE] Iniciando envio al Backoffice para email=%s con %d campos en wizard_responses",
                email,
                len(wizard_responses),
            )
            try:
                id_emp, id_caso = await send_postulation_to_backoffice(wizard_responses)
                logger.info(
                    "[WIZARD_NODE] Postulacion enviada al backoffice: id_emprendedor=%s, id_caso=%s",
                    id_emp,
                    id_caso,
                )
            except BackofficeIntegrationDisabled:
                logger.debug("[WIZARD_NODE] Integracion backoffice desactivada, omitiendo envio.")
            except Exception as exc:
                logger.error(
                    "[WIZARD_NODE] Error al enviar postulacion al backoffice: %s",
                    exc,
                    exc_info=True,
                )
        else:
            logger.debug(
                "[WIZARD_NODE] No se envia al Backoffice: completed=%s, has_wizard_responses=%s",
                bool(result.get("completed")),
                bool(wizard_responses),
            )

        return {
            **state,
            "wizard_state": result,
            "messages": result.get("messages", []),
            "agent_context": {"response": response_content},
            "conversation_id": conv_id,
        }


# ------------------------------------------------------------------
# Module-level instance & wrapper for LangGraph
# ------------------------------------------------------------------

wizard_agent = WizardAgent()


async def handle_wizard_flow(state: ConversationState) -> ConversationState:
    """Funcion wrapper para LangGraph."""
    return await wizard_agent(state)
