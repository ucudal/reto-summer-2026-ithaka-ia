"""
Servicio para persistir datos de conversaciones en la base de datos.

Centraliza las operaciones de DB relacionadas a conversaciones, mensajes
y sesiones del wizard. Ninguna función llama session.commit() — esa
responsabilidad es del caller para garantizar atomicidad de la transacción.
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import Conversation, Message, WizardSession

logger = logging.getLogger(__name__)


async def get_or_create_conversation(
    session: AsyncSession,
    conv_id: int | None,
    email: str | None = None,
) -> int:
    """Devuelve el conv_id existente o crea una nueva Conversation.

    Si se pasa email y la conversación no lo tiene guardado, lo actualiza.
    No commitea — el caller es responsable del commit.
    """
    if conv_id is not None:
        if email:
            conv = await session.get(Conversation, conv_id)
            if conv and not conv.email:
                conv.email = email
        return conv_id

    conv = Conversation(email=email)
    session.add(conv)
    await session.flush()
    await session.refresh(conv)
    logger.debug(f"[CONV_SERVICE] Nueva conversación creada id={conv.id}")
    return conv.id


async def save_message(
    session: AsyncSession,
    conv_id: int,
    role: str,
    content: str,
) -> None:
    """Agrega un mensaje a la sesión. El caller commitea.

    No commitea — el caller es responsable del commit.
    """
    msg = Message(conv_id=conv_id, role=role, content=content)
    session.add(msg)
    logger.debug(f"[CONV_SERVICE] Mensaje encolado role={role!r} conv_id={conv_id}")


async def get_or_create_wizard_session(
    session: AsyncSession,
    conv_id: int,
) -> WizardSession:
    """Obtiene la WizardSession activa para la conversación o crea una nueva.

    Hace flush si crea una nueva para poblar el ID. El caller commitea.
    """
    result = await session.execute(
        select(WizardSession)
        .where(WizardSession.conv_id == conv_id)
        .where(WizardSession.state == "ACTIVE")
        .order_by(WizardSession.created_at.desc())
        .limit(1)
    )
    ws = result.scalar_one_or_none()
    if ws is None:
        ws = WizardSession(
            conv_id=conv_id,
            current_question=1,
            responses={},
            state="ACTIVE",
        )
        session.add(ws)
        await session.flush()
        logger.debug(f"[CONV_SERVICE] Nueva WizardSession creada conv_id={conv_id}")
    return ws


async def update_wizard_session(
    session: AsyncSession,
    wizard_session: WizardSession,
    current_question: int,
    responses: dict,
    session_state: str,
) -> None:
    """Actualiza current_question, responses y state de la WizardSession.

    No commitea — el caller es responsable del commit.
    """
    wizard_session.current_question = current_question
    wizard_session.responses = responses
    wizard_session.state = session_state
    logger.debug(
        f"[CONV_SERVICE] WizardSession actualizada id={wizard_session.id} "
        f"question={current_question} state={session_state!r}"
    )
