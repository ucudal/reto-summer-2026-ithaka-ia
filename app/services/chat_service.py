"""
Servicio de chat actualizado para integrar con el sistema de agentes LangGraph
"""

import logging
from typing import Any, Optional, Dict

from sqlalchemy import select, and_

from ..db.config.database import get_async_session
from ..db.models import Conversation, Message, WizardSession
from ..graph.workflow import process_user_message

logger = logging.getLogger(__name__)


class ChatService:
    """Servicio principal de chat integrado con agentes IA"""

    def init(self):
        pass

    async def _with_session(self, operation):
        """Helper method to handle session acquisition pattern"""
        async for session in get_async_session():
            try:
                result = await operation(session)
                return result
            except Exception as e:
                await session.rollback()
                raise
            finally:
                break

    async def process_message(
        self,
        user_message: str,
        user_email: str = None,
        conversation_id: int = None
    ) -> dict[str, Any]:
        """Procesa un mensaje del usuario usando el sistema de agentes"""

        try:
            # Obtener o crear conversación
            if not conversation_id and user_email:
                conversation_id = await self._get_or_create_conversation(user_email)
            elif not conversation_id and not user_email:
                # Para preguntas FAQ sin email, crear conversación temporal
                conversation_id = await self._create_temporary_conversation()

            # Obtener historial de la conversación
            chat_history = []
            if conversation_id:
                chat_history = await self._get_chat_history(conversation_id)
            
            # Recuperar estado del wizard si existe
            wizard_state = await self._get_wizard_state(conversation_id)
            logger.info(f"Retrieved wizard state: {wizard_state}")

            # Procesar mensaje a través del workflow de agentes
            result = await process_user_message(
                user_message=user_message,
                conversation_id=conversation_id,
                chat_history=chat_history,
                user_email=user_email,
                wizard_state=wizard_state
            )

            # Guardar mensajes en la base de datos
            if conversation_id:
                await self._save_messages(
                    conversation_id=conversation_id,
                    user_message=user_message,
                    bot_response=result["response"]
                )
            
            # Persistir estado del wizard si es necesario
            if result.get("wizard_state") in ["ACTIVE", "COMPLETED", "PAUSED", "INACTIVE"]:
                logger.info(f"Saving wizard state: {result.get('wizard_state')}, question: {result.get('current_question')}")
                await self._save_wizard_state(
                    conversation_id=conversation_id,
                    wizard_session_id=result.get("wizard_session_id"),
                    wizard_state=result.get("wizard_state"),
                    current_question=result.get("current_question"),
                    wizard_responses=result.get("wizard_responses", {})
                )

            # Actualizar email de conversación si se proporcionó durante el wizard
            if user_email and conversation_id:
                await self._update_conversation_email(conversation_id, user_email)

            return {
                "success": True,
                "response": result["response"],
                "conversation_id": result["conversation_id"] or conversation_id,
                "agent_used": result["agent_used"],
                "wizard_session_id": result.get("wizard_session_id"),
                "wizard_state": result.get("wizard_state", "INACTIVE"),
                "current_question": result.get("current_question"),
                "human_feedback_needed": result.get("human_feedback_needed", False),
                "human_validation_needed": result.get("human_validation_needed", False),
                "metadata": {
                    "next_action": result.get("next_action"),
                    "faq_results": result.get("faq_results"),
                    "validation_results": result.get("validation_results")
                }
            }

        except Exception as e:
            logger.error(f"Error in chat service: {e}")
            return {
                "success": False,
                "response": "Lo siento, tuve un problema procesando tu mensaje. ¿Podrías intentar de nuevo?",
                "error": str(e),
                "conversation_id": conversation_id,
                "agent_used": "error_handler"
            }

    async def _get_or_create_conversation(self, user_email: str) -> int:
        """Obtiene conversación existente o crea una nueva"""
        try: 
            async for session in get_async_session():
                # Buscar conversación existente por email
                stmt = select(Conversation).where(
                    Conversation.email == user_email)
                result = await session.execute(stmt)
                existing_conversation = result.scalar_one_or_none()

                if existing_conversation:
                    logger.info(
                        f"Found existing conversation {existing_conversation.id} for {user_email}")
                    return existing_conversation.id

                # Crear nueva conversación
                new_conversation = Conversation(email=user_email)
                session.add(new_conversation)
                await session.commit()
                await session.refresh(new_conversation)

                logger.info(
                    f"Created new conversation {new_conversation.id} for {user_email}")
                return new_conversation.id

        #try:
           # return await self._with_session(operation)
        except Exception as e:
            logger.error(f"Error managing conversation: {e}")
            raise

    async def _get_chat_history(self, conversation_id: int, limit: int = 10) -> list[dict[str, str]]:
        """Obtiene historial reciente de la conversación"""

        async def operation(session):
            stmt = select(Message).where(
                Message.conv_id == conversation_id
            ).order_by(
                Message.ts.desc()
            ).limit(limit)

            result = await session.execute(stmt)
            messages = result.scalars().all()

            # Convertir a formato de historial (más reciente primero, luego revertir)
            history = []
            for message in reversed(messages):
                history.append({
                    "role": message.role,
                    "content": message.content,
                    "timestamp": message.ts.isoformat()
                })

            return history

        try:
            return await self._with_session(operation)
        except Exception as e:
            logger.error(f"Error getting chat history: {e}")
            return []

    async def _save_messages(
        self,
        conversation_id: int,
        user_message: str,
        bot_response: str
    ):
        """Guarda mensajes del usuario y bot en la base de datos"""
        try:
            #async def operation(session):
            async for session in get_async_session():
                # Mensaje del usuario
                user_msg = Message(
                    conv_id=conversation_id,
                    role="user",
                    content=user_message
                )
                session.add(user_msg)

                # Respuesta del bot
                bot_msg = Message(
                    conv_id=conversation_id,
                    role="assistant",
                    content=bot_response
                )
                session.add(bot_msg)

                await session.commit()
                logger.info(
                    f"Saved messages for conversation {conversation_id}")

            #try:
                #await self._with_session(operation)
        except Exception as e:
            logger.error(f"Error saving messages: {e}")
            # No re-lanzar el error para no interrumpir el flujo principal

    async def _update_conversation_email(self, conversation_id: int, email: str):
        """Actualiza el email de una conversación si no lo tenía"""

        async def operation(session):
            stmt = select(Conversation).where(
                Conversation.id == conversation_id)
            result = await session.execute(stmt)
            conversation = result.scalar_one_or_none()

            if conversation and not conversation.email:
                conversation.email = email
                await session.commit()
                logger.info(
                    f"Updated email for conversation {conversation_id}")

        try:
            await self._with_session(operation)
        except Exception as e:
            logger.error(f"Error updating conversation email: {e}")

    async def get_conversation_info(self, conversation_id: int) -> Optional[dict[str, Any]]:
        """Obtiene información de una conversación"""

        async def operation(session):
            stmt = select(Conversation).where(
                Conversation.id == conversation_id)
            result = await session.execute(stmt)
            conversation = result.scalar_one_or_none()

            if conversation:
                return {
                    "id": conversation.id,
                    "email": conversation.email,
                    "started_at": conversation.started_at.isoformat(),
                    "message_count": len(conversation.messages) if conversation.messages else 0
                }

            return None

        try:
            return await self._with_session(operation)
        except Exception as e:
            logger.error(f"Error getting conversation info: {e}")
            return None

    async def _create_temporary_conversation(self) -> int:
        """Crea una conversación temporal para preguntas FAQ sin email"""

        async def operation(session):
            # Crear conversación temporal sin email
            new_conversation = Conversation(
                email=None,  # Sin email para conversaciones temporales
            )

            session.add(new_conversation)
            await session.commit()
            await session.refresh(new_conversation)

            logger.info(
                f"Created temporary conversation {new_conversation.id}")
            return new_conversation.id

        try:
            return await self._with_session(operation)
        except Exception as e:
            logger.error(f"Error creating temporary conversation: {e}")
            # Si falla, devolver un ID temporal negativo para indicar que es temporal
            return -1

    async def _get_wizard_state(self, conversation_id: int) -> Optional[Dict[str, Any]]:
        """Recupera el estado del wizard desde la base de datos"""
        try:
            async for session in get_async_session():
                # Obtener todas las sesiones activas para esta conversación
                stmt = select(WizardSession).where(
                    and_(
                        WizardSession.conv_id == conversation_id,
                        WizardSession.state.in_(["ACTIVE", "PAUSED", "STARTING"])
                    )
                ).order_by(WizardSession.updated_at.desc())
                
                result = await session.execute(stmt)
                wizard_sessions = result.scalars().all()
                
                if wizard_sessions:
                    # Si hay múltiples sesiones, mantener solo la más reciente y limpiar las demás
                    if len(wizard_sessions) > 1:
                        logger.warning(f"Found {len(wizard_sessions)} wizard sessions for conversation {conversation_id}, keeping only the most recent")
                        
                        # Mantener solo la sesión más reciente
                        latest_session = wizard_sessions[0]  # Ya está ordenado por updated_at desc
                        
                        # Marcar las sesiones más antiguas como COMPLETED para limpiarlas
                        for old_session in wizard_sessions[1:]:
                            old_session.state = "COMPLETED"
                        
                        await session.commit()
                        logger.info(f"Cleaned up {len(wizard_sessions) - 1} old wizard sessions")
                    else:
                        latest_session = wizard_sessions[0]
                    
                    wizard_state = {
                        "wizard_session_id": f"wizard_{latest_session.id}",
                        "wizard_state": latest_session.state,
                        "current_question": latest_session.current_question,
                        "wizard_responses": latest_session.responses or {}
                    }
                    logger.info(f"Found wizard session: {wizard_state}")
                    return wizard_state
                
                break
        except Exception as e:
            logger.error(f"Error getting wizard state: {e}")
        
        return None

    async def _save_wizard_state(
        self,
        conversation_id: int,
        wizard_session_id: str,
        wizard_state: str,
        current_question: int,
        wizard_responses: dict[str, Any]
    ):
        """Guarda o actualiza el estado del wizard en la base de datos"""
        try: 
             async for session in get_async_session():
                # Buscar sesiones existentes
                stmt = select(WizardSession).where(
                    and_(
                        WizardSession.conv_id == conversation_id,
                        WizardSession.state.in_(["ACTIVE", "PAUSED", "STARTING", "INACTIVE"])
                    )
                ).order_by(WizardSession.updated_at.desc())
                result = await session.execute(stmt)
                existing_sessions = result.scalars().all()
                
                if existing_sessions:
                    # Si hay múltiples sesiones, limpiar las antiguas
                    if len(existing_sessions) > 1:
                        logger.warning(f"Found {len(existing_sessions)} existing wizard sessions, cleaning up old ones")
                        for old_session in existing_sessions[1:]:
                            old_session.state = "COMPLETED"
                    
                    # Actualizar la sesión más reciente
                    latest_session = existing_sessions[0]
                    logger.info(f"Updating existing wizard session: {latest_session.id}")
                    latest_session.current_question = current_question
                    latest_session.responses = wizard_responses
                    latest_session.state = wizard_state
                else:
                    # Crear nueva sesión
                    logger.info(f"Creating new wizard session for conversation {conversation_id}")
                    new_session = WizardSession(
                        conv_id=conversation_id,
                        current_question=current_question,
                        responses=wizard_responses,
                        state=wizard_state
                    )
                    session.add(new_session)
                
                await session.commit()
                logger.info(f"Saved wizard state for conversation {conversation_id}")

        #try:
         #   await self._with_session(operation)
        except Exception as e:
            logger.error(f"Error saving wizard state: {e}")

# Instancia global del servicio
chat_service = ChatService()
