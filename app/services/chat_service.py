"""
ChatService -- orchestrates the LangGraph workflow with DB persistence.

Every user message and assistant response is saved to the ``messages`` table
through ``conversation_service``.  The service opens its own async session
so callers (WebSocket handler, future REST fallback, etc.) don't need to
manage transactions.
""" 

from __future__ import annotations

import logging
from typing import Any, Optional

from app.db.config.database import SessionLocal
from app.graph.workflow import IthakaWorkflow
from app.services.conversation_service import save_message

logger = logging.getLogger(__name__)


class ChatService:
    """Orquesta el flujo LangGraph para cada mensaje del usuario."""

    def __init__(self) -> None:
        self.workflow = IthakaWorkflow()

    async def process_message(
        self,
        message: str,
        conversation_id: int,
        wizard_state: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Send *message* through the workflow, persisting both sides to DB."""

        thread_id = str(conversation_id)

        async with SessionLocal() as session:
            await save_message(session, conversation_id, "user", message)
            await session.commit()

        result = await self.workflow.process_message(
            user_message=message,
            wizard_state=wizard_state,
            thread_id=thread_id,
        )

        response_text = result.get("response", "")

        async with SessionLocal() as session:
            await save_message(session, conversation_id, "assistant", response_text)
            await session.commit()

        return result


chat_service = ChatService()
