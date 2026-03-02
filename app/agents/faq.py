"""
FAQ Agent -- answers user questions using vector search via tool calling.

Uses the LangGraph-idiomatic pattern: ChatOpenAI.bind_tools() lets the LLM
decide *when* to search the FAQ knowledge base, and ToolNode executes the
call automatically.  The agent loops (LLM -> tools -> LLM) until the model
produces a final text answer.
"""

import logging
import os
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from jinja2 import Environment, FileSystemLoader
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import ToolNode
from langsmith import traceable
from langchain_core.tracers.context import tracing_v2_enabled

from .base import AgentNode
from ..db.config.database import get_async_session
from ..graph.state import ConversationState
from ..services import conversation_service
from ..tools import search_faqs

logger = logging.getLogger(__name__)

_AGENTS_DIR = Path(__file__).parent
_config = yaml.safe_load((_AGENTS_DIR / "config" / "faq.yaml").read_text())

_TOOLS = [search_faqs]


class FAQAgent(AgentNode):
    """Answers frequently-asked questions using a tool-calling loop."""
    
    name: str = _config["name"]
    description: str = _config["description"]

    def __init__(self):
        super().__init__()
        
        model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        model_cfg = _config["model"]

        # LangSmith configuration
        self.tracing_enabled = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
        self.project_name = os.getenv("LANGCHAIN_PROJECT", "ithaka-project")
        
        if self.tracing_enabled:
            logger.info(f"LangSmith tracing enabled for FAQ agent in project: {self.project_name}")

        self.llm = ChatOpenAI(
            model=model_name,
            temperature=model_cfg["temperature_contextual"],
            max_tokens=model_cfg["max_tokens_contextual"],
        ).bind_tools(_TOOLS)

        self.tool_node = ToolNode(_TOOLS)
        self.system_message = SystemMessage(
            content=_config["system_prompts"]["contextual"]
        )

    @traceable(run_type="chain")
    async def __call__(self, state: ConversationState) -> ConversationState:
        """Run the tool-calling loop and return the updated conversation state."""

        logger.debug("=" * 60)
        logger.debug("[FAQ] __call__ invoked (tool-calling pattern)")

        try:
            raw_messages = list(state.get("messages", []))
            messages = self._sanitize_messages(raw_messages)

            user_message = next(
                (m.content for m in reversed(messages) if isinstance(m, HumanMessage)),
                "",
            )

            doc_context = state.get("document_context")
            if doc_context:
                doc_filename = state.get("document_filename", "documento")
                cap = 12_000
                snippet = doc_context[:cap] + ("..." if len(doc_context) > cap else "")
                for i in range(len(messages) - 1, -1, -1):
                    if isinstance(messages[i], HumanMessage):
                        prev = messages[i].content or ""
                        messages[i] = HumanMessage(
                            content=f"{prev}\n\n[Documento adjunto: {doc_filename}]\n{snippet}"
                        )
                        break

            if not any(isinstance(m, SystemMessage) for m in messages):
                messages = [self.system_message] + messages

            response = await self._tool_calling_loop(messages)

            conv_id = state.get("conversation_id")
            async for session in get_async_session():
                try:
                    conv_id = await conversation_service.get_or_create_conversation(
                        session, conv_id
                    )
                    await conversation_service.save_message(session, conv_id, "user", user_message or "")
                    await conversation_service.save_message(session, conv_id, "assistant", response)
                    await session.commit()
                except Exception as db_err:
                    await session.rollback()
                    logger.error(f"[FAQ] Error persisting messages to DB: {db_err}", exc_info=True)
                    conv_id = state.get("conversation_id")

            return {
                "agent_context": {
                    "response": response,
                    "query_processed": True,
                },
                "messages": [AIMessage(content=response)],
                "conversation_id": conv_id,
            }

        except Exception as e:
            logger.error(f"Error in FAQ agent: {e}", exc_info=True)
            fallback = (
                "Lo siento, tuve un problema técnico procesando tu consulta.\n\n"
                "Mientras tanto, puedes:\n"
                "• Contactarnos directamente por nuestras redes sociales\n"
                "• Visitar nuestro sitio web para más información\n"
                "• Reformular tu pregunta de manera más específica\n\n"
                "¿Hay algo más en lo que pueda ayudarte?"
            )
            return {
                "agent_context": {
                    "response": fallback,
                    "error": True,
                    "query_processed": False,
                },
                "messages": [AIMessage(content=fallback)],
            }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _sanitize_messages(messages: list) -> list:
        """Ensure every message has ``content`` as a plain string.

        The LangGraph checkpointer (``add_messages``) may replay old
        ``HumanMessage`` objects whose ``content`` is a list of
        multimodal parts from before the WS-layer extraction fix.
        OpenAI rejects these, so we flatten them here.
        """
        clean: list = []
        for m in messages:
            content = getattr(m, "content", None)
            if isinstance(content, list):
                text_parts = [
                    p.get("text", "")
                    for p in content
                    if isinstance(p, dict) and p.get("type") == "text"
                ]
                flat = " ".join(t.strip() for t in text_parts).strip() or ""
                if getattr(m, "type", None) == "ai":
                    clean.append(AIMessage(content=flat))
                elif isinstance(m, SystemMessage):
                    clean.append(SystemMessage(content=flat))
                else:
                    clean.append(HumanMessage(content=flat))
            else:
                clean.append(m)
        return clean

    @traceable(run_type="chain")
    async def _tool_calling_loop(
        self,
        messages: list,
        max_iterations: int = 5,
    ) -> str:
        """Call the LLM, execute any tool calls, feed results back, repeat."""

        for _ in range(max_iterations):
            ai_msg = await self.llm.ainvoke(messages)
            messages.append(ai_msg)

            if not ai_msg.tool_calls:
                return ai_msg.content or ""

            logger.debug(
                "[FAQ] LLM requested %d tool call(s)", len(ai_msg.tool_calls)
            )

            tool_result = await self.tool_node.ainvoke({"messages": messages})
            tool_messages = tool_result["messages"]
            messages.extend(tool_messages)

        last = messages[-1]
        return last.content if hasattr(last, "content") and last.content else ""


faq_agent = FAQAgent()


# Función para usar en el grafo LangGraph
@traceable(run_type="chain")
async def handle_faq_query(state: ConversationState) -> ConversationState:
    """Wrapper function for LangGraph."""
    return await faq_agent(state)
