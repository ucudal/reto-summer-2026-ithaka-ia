"""
Service for submitting completed wizard postulations to the external Ithaka API.

The flow requires two sequential HTTP calls:
  1. POST /api/v1/emprendedores/  -- creates the entrepreneur record
  2. POST /api/v1/caso/           -- creates the case linked to that entrepreneur

The base URL is read from ITHAKA_API_BASE_URL (env var).
"""

import logging
import os

import aiohttp

logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "http://localhost:8000"


async def submit_postulation(wizard_responses: dict) -> dict:
    """Submit a completed wizard postulation to the external Ithaka API.

    Args:
        wizard_responses: The ``wizard_responses`` dict produced by the wizard
            sub-graph, keyed by ``field_name`` values from WIZARD_QUESTIONS.

    Returns:
        ``{"id_emprendedor": int, "id_caso": int}`` on success.

    Raises:
        aiohttp.ClientResponseError: if either API call returns a non-2xx status.
        aiohttp.ClientError: on network/connection errors.
    """
    base_url = os.getenv("ITHAKA_API_BASE_URL", _DEFAULT_BASE_URL).rstrip("/")

    emprendedor_payload = {
        "nombre": wizard_responses.get("full_name", ""),
        "email": wizard_responses.get("email", ""),
        "telefono": wizard_responses.get("phone"),
        "vinculo_institucional": wizard_responses.get("ucu_relation"),
    }

    caso_payload_base = {
        "nombre_caso": wizard_responses.get("problem_description", "Postulación Ithaka"),
        "descripcion": wizard_responses.get("solution_description", ""),
        "datos_chatbot": wizard_responses,
        "consentimiento_datos": True,
        "id_estado": 1,
    }

    logger.debug(f"[POSTULATION_SERVICE] Submitting to {base_url}")
    logger.debug(f"[POSTULATION_SERVICE] Emprendedor payload: {emprendedor_payload}")

    async with aiohttp.ClientSession() as session:
        # Step 1: create the entrepreneur
        async with session.post(
            f"{base_url}/api/v1/emprendedores/",
            json=emprendedor_payload,
            headers={"Content-Type": "application/json"},
        ) as resp:
            resp.raise_for_status()
            emprendedor_data = await resp.json()

        id_emprendedor = emprendedor_data["id_emprendedor"]
        logger.debug(f"[POSTULATION_SERVICE] Emprendedor created: id={id_emprendedor}")

        # Step 2: create the case linked to the entrepreneur
        caso_payload = {**caso_payload_base, "id_emprendedor": id_emprendedor}
        logger.debug(f"[POSTULATION_SERVICE] Caso payload: {caso_payload}")

        async with session.post(
            f"{base_url}/api/v1/caso/",
            json=caso_payload,
            headers={"Content-Type": "application/json"},
        ) as resp:
            resp.raise_for_status()
            caso_data = await resp.json()

        id_caso = caso_data["id_caso"]
        logger.debug(f"[POSTULATION_SERVICE] Caso created: id={id_caso}")

    return {"id_emprendedor": id_emprendedor, "id_caso": id_caso}
