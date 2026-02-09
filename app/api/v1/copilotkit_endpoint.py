"""
Endpoint oficial de CopilotKit usando SDK y LangGraph
"""

import logging

from copilotkit import CopilotKitRemoteEndpoint, LangGraphAgent
from copilotkit.integrations.fastapi import add_fastapi_endpoint
from fastapi import APIRouter

from app.graph.workflow import IthakaWorkflow

logger = logging.getLogger(__name__)

ithaka_workflow = IthakaWorkflow()


def create_copilotkit_sdk():
    """Crea el SDK de CopilotKit con el agente de LangGraph"""

    sdk = CopilotKitRemoteEndpoint(
        agents=lambda context: [
            LangGraphAgent(
                name="ithaka_agent",
                description="Agente de ITHAKA para responder preguntas sobre programas, cursos, Fellows y servicios del centro de emprendimiento e innovación",
                graph=ithaka_workflow.graph,
                langgraph_config={
                    "thread_id": context.get("thread_id", "default"),
                    "properties": context.get("properties", {})
                }
            )
        ]
    )

    return sdk


router = APIRouter()

sdk = create_copilotkit_sdk()

add_fastapi_endpoint(router, sdk, "/copilotkit")

logger.info("✅ CopilotKit SDK configurado correctamente con LangGraph")
