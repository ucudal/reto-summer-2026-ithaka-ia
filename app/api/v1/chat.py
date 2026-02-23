import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.chat_service import chat_service

logger = logging.getLogger(__name__)

router = APIRouter()


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    wizard_state: Optional[dict[str, Any]] = None
    thread_id: Optional[str] = Field(
        default="default",
        description="Identificador del hilo para LangGraph (default: 'default')",
    )


class ChatResponse(BaseModel):
    response: str
    agent_used: str
    wizard_session_id: Optional[str] = None
    wizard_state: Optional[str] = None
    current_question: Optional[int] = None
    wizard_responses: dict[str, Any] = Field(default_factory=dict)
    awaiting_answer: bool = False
    error: Optional[str] = None


@router.post("/chat", response_model=ChatResponse, summary="Procesa un mensaje de chat")
async def chat_endpoint(payload: ChatRequest) -> ChatResponse:
    """
    Endpoint REST principal para interactuar con el workflow de agentes.

    Recibe el mensaje del usuario, delega en el ChatService (LangGraph) y devuelve
    tanto la respuesta generada como metadatos útiles (agente que respondió, estado del wizard, etc.).
    """

    try:
        result = await chat_service.process_message(
            message=payload.message,
            wizard_state=payload.wizard_state,
            thread_id=payload.thread_id or "default",
        )

        return ChatResponse(
            response=result.get("response", ""),
            agent_used=result.get("agent_used", "unknown"),
            wizard_session_id=result.get("wizard_session_id"),
            wizard_state=result.get("wizard_state"),
            current_question=result.get("current_question"),
            wizard_responses=result.get("wizard_responses") or {},
            awaiting_answer=bool(result.get("awaiting_answer", False)),
            error=result.get("error"),
        )
    except Exception as exc:  # pragma: no cover - logging side-effect
        logger.error("Error processing chat message", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error processing chat message: {exc}",
        ) from exc
