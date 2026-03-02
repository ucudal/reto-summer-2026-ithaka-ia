"""
Agente Supervisor - Router principal del sistema
Analiza la intención del usuario y decide a qué agente derivar
usando las descripciones de los nodos registrados.
"""

import json
import logging
import os
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader
from openai import AsyncOpenAI
from langsmith import traceable
from langchain_core.tracers.context import tracing_v2_enabled

from ..graph.agent_descriptions import (
    DEFAULT_AGENT,
    ROUTABLE_AGENT_NAMES,
    ROUTABLE_AGENTS,
)
from ..graph.state import ConversationState
from ..graph.document_extractor import extract_attachment, extract_text_from_message
from ..services.document_ingestion_service import document_ingestion_service

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
        
        # LangSmith configuration
        self.tracing_enabled = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
        self.project_name = os.getenv("LANGCHAIN_PROJECT", "ithaka-project")
        
        if self.tracing_enabled:
            logger.info(f"LangSmith tracing enabled for Supervisor agent in project: {self.project_name}")

    # ------------------------------------------------------------------
    # Public interface used by the LangGraph workflow
    # ------------------------------------------------------------------

    # Máximo de caracteres del documento que se inyecta como contexto.
    # ~30 000 chars ≈ 7 500 tokens, suficiente para un documento largo.
    _MAX_DOC_CHARS = 30_000

    @traceable(run_type="chain")
    async def route_message(self, state: ConversationState) -> ConversationState:
        """Analiza el mensaje del usuario y decide el routing."""

        messages = state.get("messages", [])
        human_messages = [m for m in messages if m.type == "human"]

        # Extraer texto del último mensaje humano (soporta contenido multimodal)
        user_message = extract_text_from_message(human_messages[-1]).strip() if human_messages else ""

        # --- Detección de documento adjunto ---
        if human_messages:
            self._maybe_extract_document(human_messages[-1], state)

        logger.debug("=" * 60)
        logger.debug("[SUPERVISOR] route_message called")
        logger.debug(f"[SUPERVISOR] User message: {user_message!r}")
        logger.debug(f"[SUPERVISOR] Document context: {bool(state.get('document_context'))} "
                     f"file={state.get('document_filename')!r}")
        logger.debug(f"[SUPERVISOR] Total messages in state: {len(messages)}")
        for i, m in enumerate(messages):
            text = extract_text_from_message(m)
            logger.debug(f"[SUPERVISOR]   msg[{i}] type={m.type} content={text[:100]!r}...")

        # 1. Estado: si hay wizard activo, mantenerlo sin llamar al LLM
        wizard_state_obj = state.get("wizard_state")
        if wizard_state_obj:
            wizard_status = wizard_state_obj.get("wizard_status", "INACTIVE")
            awaiting_answer = wizard_state_obj.get("awaiting_answer", False)
            wizard_session_id = wizard_state_obj.get("wizard_session_id")

            logger.debug(f"[SUPERVISOR] Wizard state check: status={wizard_status}, "
                         f"awaiting={awaiting_answer}, session_id={wizard_session_id}")

            if wizard_session_id and (wizard_status == "ACTIVE" or awaiting_answer):
                logger.info("[SUPERVISOR] Bypassing LLM - routing to wizard (active session)")
                return self._route_to(state, "wizard")

        # 2. Routing basado 100% en LLM usando contexto conversacional completo
        intention = await self._route_by_descriptions(user_message, messages, state=state)

        state["supervisor_decision"] = intention
        state["current_agent"] = intention

        logger.info(f"[SUPERVISOR] Final decision: {intention} for message: {user_message[:80]!r}")

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

            # Contexto conversacional (últimos turnos + documento si existe)
            context_lines = []
            if messages:
                for msg in messages[-6:]:
                    role = "Usuario" if msg.type == "human" else "Asistente"
                    text = extract_text_from_message(msg)
                    context_lines.append(f"- {role}: {text}")

            if state and state.get("document_context"):
                filename = state.get("document_filename", "documento")
                context_lines.append(
                    f"- [Sistema]: El usuario ha adjuntado el documento: {filename!r}"
                )

            context = "\n".join(context_lines)

            system_prompt = _prompts.get_template("supervisor_system.j2").render()
            prompt = _prompts.get_template("supervisor_route.j2").render(
                agents_block=agents_block,
                valid_names=valid_names,
                message=message,
                context=context,
            )

            logger.debug("-" * 60)
            logger.debug("[SUPERVISOR] LLM routing call")
            logger.debug(f"[SUPERVISOR] Agents block:\n{agents_block}")
            logger.debug(f"[SUPERVISOR] Valid names: {valid_names}")
            logger.debug(f"[SUPERVISOR] Conversation context:\n{context or '(empty)'}")
            logger.debug(f"[SUPERVISOR] System prompt:\n{system_prompt}")
            logger.debug(f"[SUPERVISOR] User prompt:\n{prompt}")

            model_cfg = _config["model"]
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                temperature=model_cfg["temperature"],
                max_tokens=model_cfg["max_tokens"],
            )

            raw = response.choices[0].message.content.strip()
            logger.debug(f"[SUPERVISOR] LLM raw response: {raw!r}")

            parsed = json.loads(raw)
            intention = parsed.get("agent", "").strip().lower()
            reasoning = parsed.get("reasoning", "")

            logger.debug(f"[SUPERVISOR] Parsed agent: {intention!r}, reasoning: {reasoning!r}")

            if intention in ROUTABLE_AGENT_NAMES:
                return intention

            logger.warning(
                f"[SUPERVISOR] LLM returned invalid agent name: {intention!r}. "
                f"Falling back to {DEFAULT_AGENT!r}."
            )
            return DEFAULT_AGENT

        except Exception as e:
            logger.error(f"[SUPERVISOR] Error in description-based routing: {e}", exc_info=True)
            return DEFAULT_AGENT

    def _maybe_extract_document(self, message, state: ConversationState) -> None:
        """Si el mensaje tiene un archivo adjunto, extrae el texto y lo guarda en el estado."""
        attachment = extract_attachment(message)
        if not attachment:
            return
        filename, file_bytes = attachment
        try:
            _, text = document_ingestion_service.extract_file_text(filename, file_bytes)
            if len(text) > self._MAX_DOC_CHARS:
                text = text[:self._MAX_DOC_CHARS]
                logger.info(
                    f"[SUPERVISOR] Documento truncado a {self._MAX_DOC_CHARS} chars: {filename!r}"
                )
            state["document_context"] = text
            state["document_filename"] = filename
            logger.info(f"[SUPERVISOR] Documento procesado: {filename!r} ({len(text)} chars)")
        except Exception as e:
            logger.error(
                f"[SUPERVISOR] Error al procesar documento adjunto {filename!r}: {e}",
                exc_info=True,
            )

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


@traceable(run_type="chain")
async def route_message(state: ConversationState) -> ConversationState:
    """Función wrapper para LangGraph."""
    return await supervisor_agent.route_message(state)


@traceable(run_type="chain")
def decide_next_agent_wrapper(state: ConversationState) -> str:
    """Función wrapper para routing condicional en LangGraph."""
    return supervisor_agent.decide_next_agent(state)
