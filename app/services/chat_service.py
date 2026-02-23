"""
ChatService -- capa fina para exponer IthakaWorkflow

Centraliza la creación del workflow y provee un método asíncrono
`process_message` que podrán reutilizar los endpoints REST o cualquier
integración futura (p. ej., tareas background).
"""

from __future__ import annotations

from typing import Any, Optional

from app.graph.workflow import IthakaWorkflow


class ChatService:
    """Orquesta el flujo LangGraph para cada mensaje del usuario."""

    def __init__(self) -> None:
        self.workflow = IthakaWorkflow()

    async def process_message(
        self,
        message: str,
        wizard_state: Optional[dict[str, Any]] = None,
        thread_id: str = "default",
    ) -> dict[str, Any]:
        """Envia el mensaje al workflow y devuelve el resultado bruto."""

        return await self.workflow.process_message(
            user_message=message,
            wizard_state=wizard_state,
            thread_id=thread_id,
        )


chat_service = ChatService()
