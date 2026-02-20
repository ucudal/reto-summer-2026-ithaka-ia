"""
Servicio para persistir datos de conversaciones en la base de datos.

Centraliza las operaciones de DB relacionadas a conversaciones, mensajes
y sesiones del wizard. Todos los métodos reciben una sesión activa de
SQLAlchemy para poder participar de la misma transacción.
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
    """
    if conv_id is not None:
        if email:
            conv = await session.get(Conversation, conv_id)
            if conv and not conv.email:
                conv.email = email
                await session.commit()
        return conv_id

    conv = Conversation(email=email)
    session.add(conv)
    await session.flush()
    await session.commit()
    logger.debug(f"[CONV_SERVICE] Nueva conversación creada id={conv.id}")
    return conv.id


async def save_message(
    session: AsyncSession,
    conv_id: int,
    role: str,
    content: str,
) -> None:
    """Guarda un mensaje en la tabla messages."""
    msg = Message(conv_id=conv_id, role=role, content=content)
    session.add(msg)
    await session.commit()
    logger.debug(f"[CONV_SERVICE] Mensaje guardado role={role!r} conv_id={conv_id}")


async def get_or_create_wizard_session(
    session: AsyncSession,
    conv_id: int,
) -> WizardSession:
    """Obtiene la WizardSession activa para la conversación o crea una nueva."""
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
    status: str,
) -> None:
    """Actualiza current_question, responses y state de la WizardSession."""
    wizard_session.current_question = current_question
    wizard_session.responses = responses
    wizard_session.state = status
    await session.commit()
    logger.debug(
        f"[CONV_SERVICE] WizardSession actualizada id={wizard_session.id} "
        f"question={current_question} status={status!r}"
    )
