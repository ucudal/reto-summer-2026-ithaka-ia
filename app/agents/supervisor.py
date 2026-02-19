"""
Agente Supervisor - Router principal del sistema
Analiza la intención del usuario y decide a qué agente derivar
usando las descripciones de los nodos registrados.
"""

import logging
import os
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader
from openai import AsyncOpenAI

from ..graph.agent_descriptions import (
    DEFAULT_AGENT,
    ROUTABLE_AGENT_NAMES,
    ROUTABLE_AGENTS,
)
from ..graph.state import ConversationState

logger = logging.getLogger(__name__)

_AGENTS_DIR = Path(__file__).parent
_config = yaml.safe_load((_AGENTS_DIR / "config" / "supervisor.yaml").read_text())
_prompts = Environment(loader=FileSystemLoader(str(_AGENTS_DIR / "prompts")), keep_trailing_newline=True)


class SupervisorAgent:
    """Agente supervisor que rutea conversaciones basándose en las
    descripciones de los agentes disponibles."""

    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")

        self.client = AsyncOpenAI(api_key=api_key)
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # ------------------------------------------------------------------
    # Public interface used by the LangGraph workflow
    # ------------------------------------------------------------------

    async def route_message(self, state: ConversationState) -> ConversationState:
        """Analiza el mensaje del usuario y decide el routing."""

        messages = state.get("messages", [])
        chat_history = [m.content for m in messages if m.type == "human"]
        user_message = chat_history[-1].strip()

        # 1. Estado: si hay wizard activo, mantenerlo sin llamar al LLM
        wizard_state_obj = state.get("wizard_state")
        if wizard_state_obj:
            wizard_status = wizard_state_obj.get("wizard_status", "INACTIVE")
            awaiting_answer = wizard_state_obj.get("awaiting_answer", False)
            wizard_session_id = wizard_state_obj.get("wizard_session_id")

            if wizard_session_id and (wizard_status == "ACTIVE" or awaiting_answer):
                logger.info("Manteniendo wizard activo - session detectada")
                return self._route_to(state, "wizard")

        # 2. Routing basado 100% en LLM usando contexto conversacional completo
        intention = await self._route_by_descriptions(user_message, messages)

        state["supervisor_decision"] = intention
        state["current_agent"] = intention

        logger.info(
            f"Supervisor decision: {intention} for message: {user_message[:50]}")

        return state

    def decide_next_agent(self, state: ConversationState) -> str:
        """Decide el próximo agente en el flujo del grafo."""

        supervisor_decision = state.get("supervisor_decision")

        if supervisor_decision in ROUTABLE_AGENT_NAMES:
            return supervisor_decision

        return DEFAULT_AGENT

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _route_by_descriptions(self, message: str, messages: list) -> str:
        """Usa el LLM para elegir el agente cuya descripción mejor
        coincide con la intención del usuario."""

        try:
            # Construir la sección de agentes disponibles
            agents_block = "\n".join(
                f'- "{name}": {description}'
                for name, description in ROUTABLE_AGENTS
            )
            valid_names = ", ".join(
                f'"{name}"' for name, _ in ROUTABLE_AGENTS
            )

            # Contexto conversacional completo (últimos turnos user/assistant)
            context = ""
            if messages:
                context = "\n".join(
                    f"- {'Usuario' if msg.type == 'human' else 'Asistente'}: {msg.content}"
                    for msg in messages[-6:]
                )

            prompt = _prompts.get_template("supervisor_route.j2").render(
                agents_block=agents_block,
                valid_names=valid_names,
                message=message,
                context=context,
            )

            model_cfg = _config["model"]
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": _prompts.get_template("supervisor_system.j2").render()},
                    {"role": "user", "content": prompt},
                ],
                temperature=model_cfg["temperature"],
                max_tokens=model_cfg["max_tokens"],
            )

            intention = response.choices[0].message.content.strip().lower()

            if intention in ROUTABLE_AGENT_NAMES:
                return intention

            logger.warning(
                f"LLM returned invalid agent name: '{intention}'. "
                f"Falling back to '{DEFAULT_AGENT}'."
            )
            return DEFAULT_AGENT

        except Exception as e:
            logger.error(f"Error in description-based routing: {e}")
            return DEFAULT_AGENT

    @staticmethod
    def _route_to(state: ConversationState, agent: str) -> ConversationState:
        """Rutea directamente a un agente específico."""
        state["supervisor_decision"] = agent
        state["current_agent"] = agent
        return state


# ------------------------------------------------------------------
# Module-level instances & wrapper functions for LangGraph
# ------------------------------------------------------------------

supervisor_agent = SupervisorAgent()


async def route_message(state: ConversationState) -> ConversationState:
    """Función wrapper para LangGraph."""
    return await supervisor_agent.route_message(state)


def decide_next_agent_wrapper(state: ConversationState) -> str:
    """Función wrapper para routing condicional en LangGraph."""
    return supervisor_agent.decide_next_agent(state)
