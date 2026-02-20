"""
Agente FAQ - Responde preguntas frecuentes usando búsqueda vectorial
"""

import logging
import os
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from jinja2 import Environment, FileSystemLoader
from langchain_core.messages import AIMessage
from openai import AsyncOpenAI

from .base import AgentNode
from ..db.config.database import get_async_session
from ..graph.state import ConversationState
from ..services.embedding_service import embedding_service
from ..services import conversation_service

logger = logging.getLogger(__name__)

_AGENTS_DIR = Path(__file__).parent
_config = yaml.safe_load((_AGENTS_DIR / "config" / "faq.yaml").read_text())
_prompts = Environment(loader=FileSystemLoader(str(_AGENTS_DIR / "prompts")), keep_trailing_newline=True)


def to_serializable(obj):
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, dict):
        return {k: to_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [to_serializable(v) for v in obj]
    return obj


class FAQAgent(AgentNode):
    """Agente para responder preguntas frecuentes usando base vectorial"""

    name: str = _config["name"]
    description: str = _config["description"]

    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")

        self.client = AsyncOpenAI(api_key=api_key)
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.max_results = int(os.getenv("MAX_FAQ_RESULTS", "5"))
        self.similarity_threshold = float(
            os.getenv("SIMILARITY_THRESHOLD", "0.4"))

    async def __call__(self, state: ConversationState) -> ConversationState:
        """Procesa una consulta FAQ del usuario"""

        messages = state.get("messages", [])
        user_message = [m.content for m in messages if m.type == "human"][-1]
        # Build conversation history excluding the current user message (last one)
        history = messages[:-1] if messages else []

        logger.debug("=" * 60)
        logger.debug("[FAQ] __call__ invoked")
        logger.debug(f"[FAQ] User message: {user_message!r}")
        logger.debug(f"[FAQ] similarity_threshold={self.similarity_threshold}, max_results={self.max_results}")

        try:
            # Obtener sesión de base de datos
            async for session in get_async_session():
                # Buscar FAQs similares
                similar_faqs = await embedding_service.search_similar_faqs(
                    query=user_message,
                    session=session,
                    limit=self.max_results,
                    similarity_threshold=self.similarity_threshold
                )

                logger.debug(f"[FAQ] Found {len(similar_faqs)} similar FAQs")
                for i, faq in enumerate(similar_faqs):
                    logger.debug(f"[FAQ]   faq[{i}] similarity={faq.get('similarity', '?'):.3f} "
                                 f"q={faq.get('question', '')[:80]!r}")

                if similar_faqs:
                    # Generar respuesta contextualizada con las FAQs encontradas
                    response = await self._generate_contextual_response(
                        user_message, similar_faqs, history
                    )

                    state["faq_results"] = to_serializable(similar_faqs)
                    state["next_action"] = "send_response"
                    state["should_continue"] = False

                else:
                    # No se encontraron FAQs relevantes
                    response = await self._generate_no_results_response(user_message, history)

                    state["faq_results"] = []
                    state["next_action"] = "send_response"
                    state["should_continue"] = False

                # Actualizar estado con la respuesta
                state["agent_context"] = {
                    "response": response,
                    "found_faqs": len(similar_faqs),
                    "query_processed": True
                }

                # --- Persistencia en DB ---
                conv_id = state.get("conversation_id")
                try:
                    conv_id = await conversation_service.get_or_create_conversation(
                        session, conv_id
                    )
                    await conversation_service.save_message(session, conv_id, "user", user_message)
                    await conversation_service.save_message(session, conv_id, "assistant", response)
                except Exception as db_err:
                    logger.error(f"[FAQ] Error al persistir mensajes en DB: {db_err}", exc_info=True)

                # Devolver delta de messages para que add_messages lo agregue
                return {
                    "agent_context": state["agent_context"],
                    "faq_results": state.get("faq_results", []),
                    "next_action": state["next_action"],
                    "should_continue": state["should_continue"],
                    "messages": [AIMessage(content=response)],
                    "conversation_id": conv_id,
                }

        except Exception as e:
            logger.error(f"Error in FAQ query processing: {e}")

            # Respuesta de fallback en caso de error
            fallback_response = """
Lo siento, tuve un problema técnico procesando tu consulta. 

Mientras tanto, puedes:
• Contactarnos directamente por nuestras redes sociales
• Visitar nuestro sitio web para más información
• Reformular tu pregunta de manera más específica

¿Hay algo más en lo que pueda ayudarte?
"""

            state["agent_context"] = {
                "response": fallback_response,
                "error": True,
                "query_processed": False
            }
            state["next_action"] = "send_response"
            state["should_continue"] = False
            return {
                "agent_context": state["agent_context"],
                "next_action": state["next_action"],
                "should_continue": state["should_continue"],
                "messages": [AIMessage(content=fallback_response)]
            }

    async def _generate_contextual_response(
            self,
            user_query: str,
            similar_faqs: list[dict[str, Any]],
            history: list = None,
    ) -> str:
        """Genera una respuesta contextualizada basada en FAQs similares"""

        try:
            faq_context = ""
            for i, faq in enumerate(similar_faqs, 1):
                faq_context += (
                    f"\nFAQ {i} (similitud: {faq['similarity']:.2f}):\n"
                    f"Pregunta: {faq['question']}\n"
                    f"Respuesta: {faq['answer']}\n"
                )

            prompt = _prompts.get_template("faq_contextual.j2").render(
                user_query=user_query,
                faq_context=faq_context,
            )

            system_content = _config["system_prompts"]["contextual"]
            logger.debug("-" * 60)
            logger.debug("[FAQ] Contextual LLM call")
            logger.debug(f"[FAQ] FAQ context passed to prompt:\n{faq_context}")
            logger.debug(f"[FAQ] System prompt:\n{system_content}")
            logger.debug(f"[FAQ] User prompt:\n{prompt}")

            chat_messages = [{"role": "system", "content": system_content}]
            for msg in (history or []):
                if msg.type == "human":
                    chat_messages.append({"role": "user", "content": msg.content})
                elif msg.type == "ai" and msg.content:
                    chat_messages.append({"role": "assistant", "content": msg.content})
            chat_messages.append({"role": "user", "content": prompt})

            model_cfg = _config["model"]
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=chat_messages,
                temperature=model_cfg["temperature_contextual"],
                max_tokens=model_cfg["max_tokens_contextual"],
            )

            answer = response.choices[0].message.content
            logger.debug(f"[FAQ] LLM contextual response:\n{answer}")
            return answer

        except Exception as e:
            logger.error(f"Error generating contextual response: {e}")

            best_faq = similar_faqs[0] if similar_faqs else None
            if best_faq:
                return (
                    f"Basándome en tu consulta, creo que esto te puede ayudar:\n\n"
                    f"**{best_faq['question']}**\n\n"
                    f"{best_faq['answer']}\n\n"
                    f"¿Esto responde a tu pregunta o necesitas información adicional?"
                )

            return "Lo siento, no pude procesar tu consulta correctamente. ¿Podrías reformularla?"

    async def _generate_no_results_response(self, user_query: str, history: list = None) -> str:
        """Genera respuesta cuando no se encuentran FAQs relevantes"""

        try:
            prompt = _prompts.get_template("faq_no_results.j2").render(
                user_query=user_query,
            )

            system_content = _config["system_prompts"]["no_results"]
            logger.debug("-" * 60)
            logger.debug("[FAQ] No-results LLM call")
            logger.debug(f"[FAQ] System prompt:\n{system_content}")
            logger.debug(f"[FAQ] User prompt:\n{prompt}")

            chat_messages = [{"role": "system", "content": system_content}]
            for msg in (history or []):
                if msg.type == "human":
                    chat_messages.append({"role": "user", "content": msg.content})
                elif msg.type == "ai" and msg.content:
                    chat_messages.append({"role": "assistant", "content": msg.content})
            chat_messages.append({"role": "user", "content": prompt})

            model_cfg = _config["model"]
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=chat_messages,
                temperature=model_cfg["temperature_no_results"],
                max_tokens=model_cfg["max_tokens_no_results"],
            )

            answer = response.choices[0].message.content
            logger.debug(f"[FAQ] LLM no-results response:\n{answer}")
            return answer

        except Exception as e:
            logger.error(f"Error generating no results response: {e}")
            return (
                "No encontré información específica sobre tu consulta en nuestras FAQs.\n\n"
                "Te sugiero:\n"
                "• Contactar directamente al equipo de Ithaka\n"
                "• Revisar nuestro sitio web oficial\n"
                "• Seguirnos en redes sociales para estar al día\n\n"
                "¿Hay algo más sobre emprendimiento o nuestros programas en lo que pueda ayudarte?"
            )


# Instancia global del agente
faq_agent = FAQAgent()


async def handle_faq_query(state: ConversationState) -> ConversationState:
    """Función wrapper para LangGraph"""
    return await faq_agent(state)
