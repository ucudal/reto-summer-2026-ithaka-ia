"""
AG-UI WebSocket endpoint.

Implements the Agent-User Interaction protocol over WebSockets.
Each connection is authenticated via a JWT query-param that embeds the
``conversationId``.  Messages are persisted through ``ChatService``.
"""

import json
import logging
import uuid

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.security.auth import verify_conversation_token
from app.services.chat_service import chat_service

logger = logging.getLogger(__name__)

router = APIRouter()


def _agui_event(event_type: str, **fields) -> str:
    """Serialise a single AG-UI event as a JSON text frame."""
    return json.dumps({"type": event_type, **fields})


def _extract_text_and_attachment(
    raw_message,
) -> tuple[str, dict | None]:
    """Split a raw WS message into (text, attachment_dict|None).

    ``raw_message`` can be:
    - ``str`` – plain text, no attachment.
    - ``list`` – multimodal parts from the frontend
      (``{type:"text", text:"…"}``, ``{type:"file", filename:"…", data:"…", media_type:"…"}``).
    """
    if isinstance(raw_message, str):
        return raw_message.strip(), None

    if not isinstance(raw_message, list) or not raw_message:
        return "", None

    text_parts: list[str] = []
    attachment: dict | None = None

    for part in raw_message:
        if not isinstance(part, dict):
            continue
        ptype = part.get("type", "")
        if ptype == "text":
            text_parts.append(part.get("text", ""))
        elif ptype in ("file", "document") and attachment is None:
            attachment = {
                "filename": part.get("filename") or part.get("name") or "document",
                "data": part.get("data") or part.get("source") or "",
                "media_type": part.get("media_type", "application/octet-stream"),
            }

    text = " ".join(t.strip() for t in text_parts).strip()
    if not text and attachment:
        text = f"[Documento adjunto: {attachment['filename']}]"

    return text, attachment


@router.websocket("/ws")
async def agui_websocket(
    websocket: WebSocket,
    token: str = Query(...),
):
    conversation_id = verify_conversation_token(token)
    await websocket.accept()
    logger.info(f"[AG-UI] WebSocket connected  conv_id={conversation_id}")

    try:
        while True:
            raw = await websocket.receive_text()

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_text(
                    _agui_event("RUN_ERROR", message="Invalid JSON", code="BAD_REQUEST")
                )
                continue

            raw_message = data.get("message")
            user_message, attachment = _extract_text_and_attachment(raw_message)

            logger.info(
                "[AG-UI] Incoming message type=%s, text_len=%d, has_attachment=%s",
                type(raw_message).__name__,
                len(user_message),
                attachment is not None,
            )

            if not user_message and not attachment:
                await websocket.send_text(
                    _agui_event("RUN_ERROR", message="Empty message", code="BAD_REQUEST")
                )
                continue

            wizard_state = data.get("wizard_state")
            run_id = str(uuid.uuid4())
            thread_id = str(conversation_id)

            await websocket.send_text(
                _agui_event("RUN_STARTED", threadId=thread_id, runId=run_id)
            )

            try:
                result = await chat_service.process_message(
                    message=user_message,
                    conversation_id=conversation_id,
                    wizard_state=wizard_state,
                    attachment=attachment,
                )

                response_text = result.get("response", "")
                message_id = str(uuid.uuid4())

                await websocket.send_text(
                    _agui_event("TEXT_MESSAGE_START", messageId=message_id, role="assistant")
                )
                await websocket.send_text(
                    _agui_event("TEXT_MESSAGE_CONTENT", messageId=message_id, delta=response_text)
                )
                await websocket.send_text(
                    _agui_event("TEXT_MESSAGE_END", messageId=message_id)
                )

                state_snapshot = _build_state_snapshot(result)
                if state_snapshot:
                    await websocket.send_text(
                        _agui_event("STATE_SNAPSHOT", snapshot=state_snapshot)
                    )

                await websocket.send_text(
                    _agui_event("RUN_FINISHED", threadId=thread_id, runId=run_id)
                )

            except Exception as exc:
                logger.error(f"[AG-UI] Error processing message: {exc}", exc_info=True)
                await websocket.send_text(
                    _agui_event("RUN_ERROR", message=str(exc), code="INTERNAL_ERROR")
                )
                await websocket.send_text(
                    _agui_event("RUN_FINISHED", threadId=thread_id, runId=run_id)
                )

    except WebSocketDisconnect:
        logger.info(f"[AG-UI] WebSocket disconnected  conv_id={conversation_id}")


def _build_state_snapshot(result: dict) -> dict | None:
    """Extract wizard / agent metadata into an AG-UI STATE_SNAPSHOT payload."""
    snapshot: dict = {}

    if result.get("wizard_state") and result["wizard_state"] != "INACTIVE":
        snapshot["wizard_state"] = result.get("wizard_state")
        snapshot["current_question"] = result.get("current_question")
        snapshot["wizard_responses"] = result.get("wizard_responses", {})
        snapshot["awaiting_answer"] = result.get("awaiting_answer", False)
        snapshot["wizard_session_id"] = result.get("wizard_session_id")

    snapshot["agent_used"] = result.get("agent_used", "unknown")

    return snapshot if snapshot else None
