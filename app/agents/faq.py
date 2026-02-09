"""
Agente FAQ - Responde preguntas frecuentes usando búsqueda vectorial
"""

import logging
import os
from typing import Any

import numpy as np
from langchain_core.messages import AIMessage
from openai import AsyncOpenAI

from ..db.config.database import get_async_session
from ..graph.state import ConversationState
from ..services.embedding_service import embedding_service

logger = logging.getLogger(__name__)


def to_serializable(obj):
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, dict):
        return {k: to_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [to_serializable(v) for v in obj]
    return obj


class FAQAgent:
    """Agente para responder preguntas frecuentes usando base vectorial"""

    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")

        self.client = AsyncOpenAI(api_key=api_key)
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.max_results = int(os.getenv("MAX_FAQ_RESULTS", "5"))
        self.similarity_threshold = float(
            os.getenv("SIMILARITY_THRESHOLD", "0.4"))

    async def handle_faq_query(self, state: ConversationState) -> ConversationState:
        """Procesa una consulta FAQ del usuario"""

        user_message = [m.content for m in state["messages"] if m.type == "human"][-1]

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

                if similar_faqs:
                    # Generar respuesta contextualizada con las FAQs encontradas
                    response = await self._generate_contextual_response(
                        user_message, similar_faqs
                    )

                    state["faq_results"] = to_serializable(similar_faqs)
                    state["next_action"] = "send_response"
                    state["should_continue"] = False

                else:
                    # No se encontraron FAQs relevantes
                    response = await self._generate_no_results_response(user_message)

                    state["faq_results"] = []
                    state["next_action"] = "send_response"
                    state["should_continue"] = False

                # Actualizar estado con la respuesta
                state["agent_context"] = {
                    "response": response,
                    "found_faqs": len(similar_faqs),
                    "query_processed": True
                }

                # Devolver delta de messages para que add_messages lo agregue
                return {
                    "agent_context": state["agent_context"],
                    "faq_results": state.get("faq_results", []),
                    "next_action": state["next_action"],
                    "should_continue": state["should_continue"],
                    "messages": [AIMessage(content=response)]
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
            similar_faqs: list[dict[str, Any]]
    ) -> str:
        """Genera una respuesta contextualizada basada en FAQs similares"""

        try:
            # Preparar contexto de FAQs
            faq_context = ""
            for i, faq in enumerate(similar_faqs, 1):
                faq_context += f"""
FAQ {i} (similitud: {faq['similarity']:.2f}):
Pregunta: {faq['question']}
Respuesta: {faq['answer']}
"""

            prompt = f"""
Eres el asistente virtual inteligente de Ithaka (centro de emprendimiento UCU). Tu misión es ayudar de la manera más útil posible.

CONSULTA DEL USUARIO:
"{user_query}"

INFORMACIÓN RELEVANTE ENCONTRADA:
{faq_context}

INSTRUCCIONES INTELIGENTES:
1. **Flexibilidad**: Interpreta la intención aunque haya errores de tipeo ("corsos" = "cursos", "ithaka" mal escrito, etc.)
2. **Contextualidad**: Si preguntan sobre temas relacionados a emprendimiento/universidad, conecta con lo que ofrece Ithaka
3. **Inteligencia**: Aunque la pregunta no sea exacta, infiere qué información necesita (ej: "qué hacen" → explica programas y servicios)
4. **Completitud**: Da información útil incluso si no hay coincidencia perfecta
5. **Natural**: Responde conversacionalmente, como si fueras un consejero experto
6. **Proactivo**: Sugiere recursos adicionales y próximos pasos
7. **Amigable**: Termina invitando a hacer más preguntas

CONTEXTO ITHAKA:
- Centro de emprendimiento de la Universidad Católica del Uruguay
- Ofrece: cursos, minor de emprendimiento, programa Fellows, incubadora
- Todo gratuito para comunidad UCU
- Abierto también a emprendedores externos
- Foco en innovación, emprendimiento e impacto social

RESPUESTA INTELIGENTE:
"""

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Eres el asistente virtual oficial de Ithaka, centro de emprendimiento de la UCU. Respondes consultas de manera amigable y precisa."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=400
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Error generating contextual response: {e}")

            # Respuesta básica usando la FAQ más similar
            best_faq = similar_faqs[0] if similar_faqs else None
            if best_faq:
                return f"""
Basándome en tu consulta, creo que esto te puede ayudar:

**{best_faq['question']}**

{best_faq['answer']}

¿Esto responde a tu pregunta o necesitas información adicional?
"""

            return "Lo siento, no pude procesar tu consulta correctamente. ¿Podrías reformularla?"

    async def _generate_no_results_response(self, user_query: str) -> str:
        """Genera respuesta cuando no se encuentran FAQs relevantes"""

        try:
            prompt = f"""
El usuario preguntó: "{user_query}"

Aunque no encuentro FAQs específicas que coincidan exactamente, soy el asistente inteligente de Ithaka y puedo ayudar.

CONTEXTO ITHAKA:
- Centro de emprendimiento de la Universidad Católica del Uruguay
- Programas: Minor de emprendimiento, Programa Fellows, cursos electivos
- Servicios: Incubadora de startups, mentorías, capacitaciones
- Todo gratuito para comunidad UCU, abierto a emprendedores externos
- Campus: Montevideo, Maldonado, Salto
- Foco: Innovación, emprendimiento, impacto social

GENERA UNA RESPUESTA INTELIGENTE QUE:
1. **Interprete la intención**: Aunque la pregunta tenga errores o sea vaga, infiere qué necesita
2. **Proporcione valor**: Da información útil sobre Ithaka basándose en el contexto
3. **Sea proactiva**: Sugiere programas/servicios que podrían interesarle
4. **Mantenga conversación**: Invita a hacer preguntas más específicas
5. **Corrige sutilmente**: Si hay errores de tipeo, usa las palabras correctas en tu respuesta

Respuesta útil e inteligente:
"""

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Eres el asistente de Ithaka. Ayuda al usuario incluso cuando no tienes información específica."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=200
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Error generating no results response: {e}")
            return """
No encontré información específica sobre tu consulta en nuestras FAQs.

Te sugiero:
• Contactar directamente al equipo de Ithaka
• Revisar nuestro sitio web oficial
• Seguirnos en redes sociales para estar al día

¿Hay algo más sobre emprendimiento o nuestros programas en lo que pueda ayudarte?
"""


# Instancia global del agente
faq_agent = FAQAgent()


# Función para usar en el grafo LangGraph


async def handle_faq_query(state: ConversationState) -> ConversationState:
    """Función wrapper para LangGraph"""
    return await faq_agent.handle_faq_query(state)
