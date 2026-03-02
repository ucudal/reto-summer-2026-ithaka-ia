"""
Utilidad para detectar y extraer archivos adjuntos de mensajes de LangChain/CopilotKit.

Cuando el usuario sube un documento desde el chat de CopilotKit, el archivo llega
codificado dentro del contenido del HumanMessage. Este módulo normaliza los
formatos más comunes y devuelve (filename, raw_bytes) listos para pasar al
document_ingestion_service.

Formatos soportados
-------------------
1. Parte de tipo "file" o "document":
   {"type": "file", "data": "<base64>", "filename": "doc.pdf", "media_type": "application/pdf"}

2. Data URI en "image_url" con MIME no-imagen (PDF, TXT, CSV, MD):
   {"type": "image_url", "image_url": {"url": "data:application/pdf;base64,<data>"}}

Si el formato que llega no coincide con ninguno de estos patrones, se loguea un
warning con los keys recibidos para que el equipo de frontend pueda ajustar el formato.
"""

import base64
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_MEDIA_TYPE_TO_EXT: dict[str, str] = {
    "application/pdf": "pdf",
    "text/plain": "txt",
    "text/markdown": "md",
    "text/csv": "csv",
    "application/csv": "csv",
}

_MAX_FILE_BYTES = 20 * 1024 * 1024  # 20 MB


def _ext_from_media_type(media_type: str) -> str:
    clean = media_type.split(";")[0].strip().lower()
    return _MEDIA_TYPE_TO_EXT.get(clean, "txt")


def extract_text_from_message(message) -> Optional[str]:
    """Extrae el texto plano de un mensaje, manejando contenido multimodal (lista)."""
    content = getattr(message, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [
            p.get("text", "")
            for p in content
            if isinstance(p, dict) and p.get("type") == "text"
        ]
        return " ".join(parts).strip()
    return str(content) if content else ""


def _decode_bytes(raw_data: str, label: str) -> Optional[bytes]:
    """Decodifica base64 y valida el tamaño. Retorna None si hay error."""
    try:
        file_bytes = base64.b64decode(raw_data)
    except Exception as e:
        logger.warning("[DOC_EXTRACT] Error decodificando base64 (%s): %s", label, e)
        return None
    if len(file_bytes) > _MAX_FILE_BYTES:
        logger.warning(
            "[DOC_EXTRACT] %s demasiado grande (%d bytes). Se omite.",
            label,
            len(file_bytes),
        )
        return None
    return file_bytes


def _try_file_part(part: dict) -> Optional[tuple[str, bytes]]:
    """Maneja partes de tipo 'file' o 'document'."""
    raw_data = part.get("data") or part.get("source")
    if not raw_data:
        logger.warning("[DOC_EXTRACT] Parte 'file'/'document' sin campo 'data' o 'source'")
        return None
    filename = (
        part.get("filename")
        or part.get("name")
        or f"document.{_ext_from_media_type(part.get('media_type', ''))}"
    )
    file_bytes = _decode_bytes(raw_data, filename)
    if file_bytes is None:
        return None
    logger.info(
        "[DOC_EXTRACT] Archivo detectado: %r (%d bytes)", filename, len(file_bytes)
    )
    return filename, file_bytes


def _try_image_url_part(part: dict) -> Optional[tuple[str, bytes]]:
    """Maneja partes de tipo 'image_url' con data URI no-imagen."""
    url = part.get("image_url", {}).get("url", "")
    if not (url.startswith("data:") and ";base64," in url):
        return None
    header, encoded = url.split(";base64,", 1)
    media_type = header[len("data:") :]
    if media_type.startswith("image/"):
        # Imagen real, no documento
        return None
    filename = f"document.{_ext_from_media_type(media_type)}"
    file_bytes = _decode_bytes(encoded, filename)
    if file_bytes is None:
        return None
    logger.info(
        "[DOC_EXTRACT] Archivo detectado via data URI: %r (%d bytes)",
        filename,
        len(file_bytes),
    )
    return filename, file_bytes


def extract_attachment(message) -> Optional[tuple[str, bytes]]:
    """Busca un archivo adjunto en el contenido del mensaje.

    Retorna (filename, raw_bytes) si encuentra un archivo, o None si el mensaje
    es solo texto.
    """
    content = getattr(message, "content", None)
    logger.info(
        "[DOC_EXTRACT] extract_attachment: content type=%s, is_list=%s",
        type(content).__name__,
        isinstance(content, list),
    )
    if not isinstance(content, list):
        logger.info("[DOC_EXTRACT] Sin adjunto: mensaje no es lista de partes (solo texto)")
        return None

    part_types = [p.get("type", "?") for p in content if isinstance(p, dict)]
    logger.info("[DOC_EXTRACT] Partes del mensaje: %s", part_types)

    for part in content:
        if not isinstance(part, dict):
            continue
        part_type = part.get("type", "")

        if part_type in ("file", "document"):
            result = _try_file_part(part)
            if result:
                return result

        elif part_type == "image_url":
            result = _try_image_url_part(part)
            if result:
                return result

        elif part_type not in ("text",):
            logger.info(
                "[DOC_EXTRACT] Parte con type=%r no reconocida como adjunto. Keys: %s",
                part_type,
                list(part.keys()),
            )

    logger.info("[DOC_EXTRACT] No se encontró adjunto en el mensaje (solo text u otros tipos)")
    return None

