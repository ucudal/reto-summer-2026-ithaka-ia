"""
Scoring-related tools for future agent use.

These wrap the existing scoring services so agents can evaluate
postulations via function calling when needed.
"""

import logging

from langchain_core.tools import tool

from ..services.ai_score_engine import evaluar_postulacion_ai
from ..services.score_engine import evaluar_postulacion

logger = logging.getLogger(__name__)


@tool
async def score_postulation_ai(text: str) -> str:
    """Score an application text using the AI engine.

    Evaluates creativity, clarity, and commitment on a 0-100 scale and
    returns a JSON-like summary with the total weighted score plus a
    short qualitative analysis.  Use this when you need to assess the
    quality of a user's postulation answer.
    """
    scores = await evaluar_postulacion_ai(text)
    return (
        f"Creatividad: {scores['creatividad']}/100, "
        f"Claridad: {scores['claridad']}/100, "
        f"Compromiso: {scores['compromiso']}/100, "
        f"Total: {scores['score_total']}/100. "
        f"Análisis: {scores.get('analisis', 'N/A')}"
    )


@tool
def score_postulation_rules(text: str) -> str:
    """Score an application text using the deterministic rule engine.

    Evaluates creativity, clarity, and commitment on a 0-100 scale and
    returns a summary with the total weighted score.  Faster than the AI
    engine but less nuanced.
    """
    scores = evaluar_postulacion(text)
    return (
        f"Creatividad: {scores['creatividad']}/100, "
        f"Claridad: {scores['claridad']}/100, "
        f"Compromiso: {scores['compromiso']}/100, "
        f"Total: {scores['score_total']}/100"
    )
