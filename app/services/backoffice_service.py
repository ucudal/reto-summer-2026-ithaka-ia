"""
Servicio para enviar postulaciones al Backoffice API de Ithaka.

Flujo: login -> POST emprendedores -> POST casos.
Usado cuando el wizard de postulacion termina (estado COMPLETED).
"""

import logging
import os
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)

# Config from env (same pattern as rest of app)
BACKOFFICE_BASE_URL = os.getenv("BACKOFFICE_BASE_URL", "http://localhost:8000").rstrip("/")
BACKOFFICE_API_PREFIX = "/api/v1"
BACKOFFICE_ADMIN_EMAIL = os.getenv("BACKOFFICE_ADMIN_EMAIL", "admin@ithaka.com")
BACKOFFICE_ADMIN_PASSWORD = os.getenv("BACKOFFICE_ADMIN_PASSWORD", "admin123")
BACKOFFICE_DEFAULT_ID_ESTADO = int(os.getenv("BACKOFFICE_DEFAULT_ID_ESTADO", "1"))


def _parse_full_name(full_name: str) -> tuple[str, str]:
    """Convierte 'Apellido, Nombre' o 'Nombre Apellido' en (nombre, apellido)."""
    if not (full_name or full_name.strip()):
        return "Usuario", "ChatBot"
    s = full_name.strip()
    if "," in s:
        parts = [p.strip() for p in s.split(",", 1)]
        apellido = parts[0] or "ChatBot"
        nombre = parts[1] if len(parts) > 1 else parts[0] or "Usuario"
        return nombre, apellido
    words = s.split()
    if len(words) >= 2:
        return " ".join(words[:-1]), words[-1]
    return s, ""


def _parse_location(location: str) -> tuple[str, str]:
    """Intenta extraer pais y ciudad de un string 'Pais, Ciudad' o similar."""
    if not (location or location.strip()):
        return "", ""
    s = location.strip()
    if "," in s:
        parts = [p.strip() for p in s.split(",", 1)]
        return (parts[0] or "", parts[1] if len(parts) > 1 else "")
    return s, ""


def _resolve_id_convocatoria(id_convocatoria: int | None) -> int | None:
    """Resolve id_convocatoria from argument or env, if present and valid."""
    if id_convocatoria is not None:
        return id_convocatoria

    raw = (os.getenv("BACKOFFICE_ID_CONVOCATORIA") or "").strip()
    if not raw:
        return None

    try:
        return int(raw)
    except ValueError:
        logger.warning(
            "[BACKOFFICE] BACKOFFICE_ID_CONVOCATORIA invalido=%r, se ignora.",
            raw,
        )
        return None


def _build_caso_description(wizard_responses: dict[str, Any]) -> str:
    """Build a non-empty case description from wizard fields."""
    desc_parts = []
    if wizard_responses.get("problem_description"):
        desc_parts.append(f"Problema: {str(wizard_responses.get('problem_description'))[:1000]}")
    if wizard_responses.get("solution_description"):
        desc_parts.append(f"Solucion: {str(wizard_responses.get('solution_description'))[:1000]}")
    if wizard_responses.get("motivation"):
        desc_parts.append(f"Motivacion: {str(wizard_responses.get('motivation'))[:500]}")
    if wizard_responses.get("additional_comments"):
        desc_parts.append(f"Comentarios: {str(wizard_responses.get('additional_comments'))[:1000]}")

    if desc_parts:
        return "\n\n".join(desc_parts)
    return "Postulacion generada desde ChatBot."


def _sanitize_chatbot_data(wizard_responses: dict[str, Any]) -> dict[str, Any]:
    """Keep only JSON-serializable primitives for datos_chatbot."""
    sanitized: dict[str, Any] = {}
    for key, value in (wizard_responses or {}).items():
        if value is None or value == "":
            continue
        if isinstance(value, (str, int, float, bool)):
            sanitized[key] = value
        else:
            sanitized[key] = str(value)
    return sanitized


def build_emprendedor_payload(wizard_responses: dict[str, Any]) -> dict[str, Any]:
    """Mapea wizard_responses al body de POST /api/v1/emprendedores/."""
    full_name = (wizard_responses.get("full_name") or "").strip()
    nombre, apellido = _parse_full_name(full_name)
    email = (wizard_responses.get("email") or "").strip()
    if not email:
        raise ValueError("email es requerido para crear emprendedor")

    location = wizard_responses.get("location") or ""
    pais, ciudad = _parse_location(location)

    payload: dict[str, Any] = {
        "nombre": nombre[:150],
        "apellido": apellido[:150],
        "email": email[:150],
    }
    if wizard_responses.get("phone"):
        payload["telefono"] = str(wizard_responses.get("phone"))[:50]
    if wizard_responses.get("document_id"):
        payload["documento_identidad"] = str(wizard_responses.get("document_id"))[:50]
    if pais:
        payload["pais_residencia"] = pais[:100]
    if ciudad:
        payload["ciudad_residencia"] = ciudad[:100]
    if wizard_responses.get("preferred_campus"):
        payload["campus_ucu"] = str(wizard_responses.get("preferred_campus"))[:100]
    if wizard_responses.get("ucu_relation"):
        payload["relacion_ucu"] = str(wizard_responses.get("ucu_relation"))[:100]
    if wizard_responses.get("faculty"):
        payload["facultad_ucu"] = str(wizard_responses.get("faculty"))[:100]
    # Canal de llegada: siempre ChatBot para postulaciones desde el asistente
    payload["canal_llegada"] = "ChatBot"
    if wizard_responses.get("motivation"):
        payload["motivacion"] = str(wizard_responses.get("motivation"))[:500]

    logger.debug(
        "[BACKOFFICE] build_emprendedor_payload: email=%s, keys=%s",
        email,
        list(payload.keys()),
    )

    return payload


def build_caso_payload(
    wizard_responses: dict[str, Any],
    id_emprendedor: int,
    id_convocatoria: int | None = None,
) -> dict[str, Any]:
    """Mapea wizard_responses al body de POST /api/v1/casos/."""
    # nombre_caso: usar problema/idea si existe, sino nombre generico
    nombre_caso = "Postulacion desde ChatBot"
    if wizard_responses.get("problem_description"):
        raw = str(wizard_responses.get("problem_description"))[:200]
        nombre_caso = raw if raw else nombre_caso
    elif wizard_responses.get("solution_description"):
        raw = str(wizard_responses.get("solution_description"))[:200]
        nombre_caso = raw if raw else nombre_caso

    payload: dict[str, Any] = {
        "nombre_caso": nombre_caso[:200],
        "id_emprendedor": id_emprendedor,
        "descripcion": _build_caso_description(wizard_responses),
        "consentimiento_datos": True,
        "id_estado": BACKOFFICE_DEFAULT_ID_ESTADO,
    }

    # datos_chatbot: respuestas estructuradas del wizard (recomendado por la integracion)
    datos = _sanitize_chatbot_data(wizard_responses)
    if datos:
        payload["datos_chatbot"] = datos

    resolved_convocatoria = _resolve_id_convocatoria(id_convocatoria)
    if resolved_convocatoria is not None:
        payload["id_convocatoria"] = resolved_convocatoria

    logger.debug(
        "[BACKOFFICE] build_caso_payload: id_emprendedor=%s, id_convocatoria=%s, id_estado=%s, keys=%s",
        id_emprendedor,
        resolved_convocatoria,
        payload.get("id_estado"),
        list(payload.keys()),
    )

    return payload


async def _get_access_token(session: aiohttp.ClientSession) -> str:
    """Login y devuelve access_token."""
    url = f"{BACKOFFICE_BASE_URL}{BACKOFFICE_API_PREFIX}/auth/login"
    logger.debug(
        "[BACKOFFICE] Solicitando access_token: url=%s, admin_email=%s",
        url,
        BACKOFFICE_ADMIN_EMAIL,
    )

    body = {
        "email": BACKOFFICE_ADMIN_EMAIL,
        "password": BACKOFFICE_ADMIN_PASSWORD,
    }
    async with session.post(url, json=body) as resp:
        if resp.status != 200:
            text = await resp.text()
            logger.error(
                "[BACKOFFICE] Login fallido en Backoffice: status=%s, body=%s",
                resp.status,
                text,
            )
            raise RuntimeError(f"Backoffice login failed {resp.status}: {text}")
        data = await resp.json()
    token = data.get("access_token")
    if not token:
        raise RuntimeError("Backoffice login response missing access_token")
    logger.debug("[BACKOFFICE] access_token obtenido correctamente.")
    return token


async def send_postulation_to_backoffice(
    wizard_responses: dict[str, Any],
    id_convocatoria: int | None = None,
) -> tuple[int, int]:
    """
    Ejecuta el flujo: login -> crear emprendedor -> crear caso.
    Devuelve (id_emprendedor, id_caso).
    Lanza excepcion si la API no esta configurada o falla.
    """
    resolved_convocatoria = _resolve_id_convocatoria(id_convocatoria)

    logger.info(
        "[BACKOFFICE] send_postulation_to_backoffice llamado: base_url=%s, id_convocatoria=%s, total_campos_respuestas=%s",
        BACKOFFICE_BASE_URL,
        resolved_convocatoria,
        len(wizard_responses or {}),
    )
    disabled = os.getenv("BACKOFFICE_INTEGRATION_ENABLED", "true").lower() in ("0", "false", "no")
    if disabled:
        logger.info(
            "[BACKOFFICE] Integration disabled (BACKOFFICE_INTEGRATION_ENABLED=false), skipping."
        )
        raise BackofficeIntegrationDisabled()

    headers: dict[str, str] = {"Content-Type": "application/json"}

    async with aiohttp.ClientSession() as session:
        token = await _get_access_token(session)
        headers["Authorization"] = f"Bearer {token}"
        logger.debug("[BACKOFFICE] Autenticado contra Backoffice, iniciando creacion de emprendedor.")

        # 1) Crear emprendedor
        emprendedor_body = build_emprendedor_payload(wizard_responses)
        url_emp = f"{BACKOFFICE_BASE_URL}{BACKOFFICE_API_PREFIX}/emprendedores/"
        logger.debug(
            "[BACKOFFICE] POST /emprendedores: url=%s, payload_keys=%s",
            url_emp,
            list(emprendedor_body.keys()),
        )
        async with session.post(url_emp, json=emprendedor_body, headers=headers) as resp:
            logger.debug("[BACKOFFICE] Respuesta POST /emprendedores: status=%s", resp.status)
            if resp.status not in (200, 201):
                text = await resp.text()
                logger.error(
                    "[BACKOFFICE] Error en POST /emprendedores: status=%s, body=%s",
                    resp.status,
                    text,
                )
                raise RuntimeError(f"Backoffice POST emprendedores failed {resp.status}: {text}")
            emp_data = await resp.json()
        logger.debug(
            "[BACKOFFICE] Datos respuesta /emprendedores: keys=%s",
            list((emp_data or {}).keys()),
        )
        id_emprendedor = emp_data.get("id_emprendedor")
        if id_emprendedor is None:
            raise RuntimeError("Backoffice emprendedor response missing id_emprendedor")
        logger.info("[BACKOFFICE] Emprendedor creado id_emprendedor=%s", id_emprendedor)

        # 2) Crear caso
        caso_body = build_caso_payload(wizard_responses, id_emprendedor, resolved_convocatoria)
        url_caso = f"{BACKOFFICE_BASE_URL}{BACKOFFICE_API_PREFIX}/casos/"
        logger.debug(
            "[BACKOFFICE] POST /casos: url=%s, payload_keys=%s",
            url_caso,
            list(caso_body.keys()),
        )
        async with session.post(url_caso, json=caso_body, headers=headers) as resp:
            logger.debug("[BACKOFFICE] Respuesta POST /casos: status=%s", resp.status)
            if resp.status not in (200, 201):
                text = await resp.text()
                logger.error(
                    "[BACKOFFICE] Error en POST /casos: status=%s, body=%s",
                    resp.status,
                    text,
                )
                raise RuntimeError(f"Backoffice POST casos failed {resp.status}: {text}")
            caso_data = await resp.json()
        logger.debug(
            "[BACKOFFICE] Datos respuesta /casos: keys=%s",
            list((caso_data or {}).keys()),
        )
        id_caso = caso_data.get("id_caso")
        if id_caso is None:
            raise RuntimeError("Backoffice caso response missing id_caso")
        logger.info("[BACKOFFICE] Caso creado id_caso=%s", id_caso)

    return int(id_emprendedor), int(id_caso)


class BackofficeIntegrationDisabled(Exception):
    """Raised when backoffice integration is explicitly disabled via env."""
