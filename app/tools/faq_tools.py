"""
FAQ-related tools that agents can invoke via function calling.
"""

import logging
import os

import numpy as np
from langchain_core.tools import tool

from ..db.config.database import get_async_session
from ..services.embedding_service import embedding_service

logger = logging.getLogger(__name__)

_MAX_RESULTS = int(os.getenv("MAX_FAQ_RESULTS", "5"))
_SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.4"))


def _to_serializable(obj):
    """Convert numpy types to plain Python so JSON serialisation works."""
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, dict):
        return {k: _to_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_serializable(v) for v in obj]
    return obj


@tool
async def search_faqs(query: str) -> str:
    """Search the Ithaka FAQ knowledge base.

    Use this tool whenever you need to look up information about Ithaka
    programmes (Fellows, minor, courses), costs, campus locations,
    application requirements, deadlines, or any other frequently asked
    question.  Pass the user's question (or a refined version) as the
    query.
    """
    async for session in get_async_session():
        results = await embedding_service.search_similar_faqs(
            query=query,
            session=session,
            limit=_MAX_RESULTS,
            similarity_threshold=_SIMILARITY_THRESHOLD,
        )

    results = _to_serializable(results)

    if not results:
        return "No se encontraron FAQs relevantes para esta consulta."

    lines: list[str] = []
    for i, faq in enumerate(results, 1):
        lines.append(
            f"FAQ {i} (similitud: {faq['similarity']:.2f}):\n"
            f"Pregunta: {faq['question']}\n"
            f"Respuesta: {faq['answer']}"
        )
    return "\n\n".join(lines)
