import json
from typing import Dict, Any, Optional

from sqlalchemy import text

from app.db.config.database import SessionLocal
from app.services.ai_score_engine import evaluar_postulacion_ai
from app.services.score_engine import evaluar_postulacion


async def procesar_postulaciones(use_ai: bool = False, ai_provider: str = "openai"):
    """
    Procesa todas las postulaciones en la base de datos y actualiza sus scores.
    
    Args:
        use_ai: Si usar motor de IA (OpenAI) en lugar de reglas
        ai_provider: Proveedor de IA (solo "openai" disponible)
    """
    async with SessionLocal() as session:
        # Obtener todas las postulaciones sin score
        result = await session.execute(
            text("SELECT id, payload_json FROM postulations WHERE score_total IS NULL")
        )

        for row in result:
            postulacion_id = row[0]
            payload_json = row[1]

            # Extraer texto del payload JSON
            texto = extraer_texto_del_payload(payload_json)
            if not texto or not texto.strip():
                continue

            try:
                # Evaluar según el motor seleccionado
                if use_ai:
                    scores = await evaluar_postulacion_ai(texto)
                else:
                    scores = evaluar_postulacion(texto)

                # Actualizar la base de datos
                await session.execute(
                    text("UPDATE postulations SET score_total = :score_total, "
                         "creatividad = :creatividad, "
                         "claridad = :claridad, "
                         "compromiso = :compromiso "
                         "WHERE id = :id"),
                    {
                        "score_total": scores["score_total"],
                        "creatividad": scores["creatividad"],
                        "claridad": scores["claridad"],
                        "compromiso": scores["compromiso"],
                        "id": postulacion_id
                    }
                )

                print(f"✅ Postulación {postulacion_id} procesada: {scores['score_total']}")

            except Exception as e:
                print(f"❌ Error procesando postulación {postulacion_id}: {e}")
                continue

        await session.commit()
        print("🎉 Procesamiento completado!")


async def procesar_postulacion_especifica(postulacion_id: int, use_ai: bool = False, ai_provider: str = "openai") -> \
Optional[Dict[str, Any]]:
    """
    Procesa una postulación específica por ID.
    
    Args:
        postulacion_id: ID de la postulación a procesar
        use_ai: Si usar motor de IA (OpenAI) en lugar de reglas
        ai_provider: Proveedor de IA (solo "openai" disponible)
    
    Returns:
        Dict con los scores calculados o None si no se encuentra
    """
    async with SessionLocal() as session:
        # Obtener la postulación específica
        result = await session.execute(
            text("SELECT id, payload_json FROM postulations WHERE id = :id"),
            {"id": postulacion_id}
        )

        postulacion = result.fetchone()
        if not postulacion:
            print(f"❌ Postulación {postulacion_id} no encontrada")
            return None

        payload_json = postulacion[1]
        texto = extraer_texto_del_payload(payload_json)
        if not texto or not texto.strip():
            print(f"❌ Postulación {postulacion_id} tiene texto vacío")
            return None

        try:
            # Evaluar según el motor seleccionado
            if use_ai:
                scores = await evaluar_postulacion_ai(texto)
            else:
                scores = evaluar_postulacion(texto)

            # Actualizar la base de datos
            await session.execute(
                text("UPDATE postulations SET score_total = :score_total, "
                     "creatividad = :creatividad, "
                     "claridad = :claridad, "
                     "compromiso = :compromiso "
                     "WHERE id = :id"),
                {
                    "score_total": scores["score_total"],
                    "creatividad": scores["creatividad"],
                    "claridad": scores["claridad"],
                    "compromiso": scores["compromiso"],
                    "id": postulacion_id
                }
            )

            await session.commit()
            print(f"✅ Postulación {postulacion_id} procesada: {scores['score_total']}")
            return scores

        except Exception as e:
            print(f"❌ Error procesando postulación {postulacion_id}: {e}")
            return None


async def obtener_postulaciones():
    """
    Obtiene todas las postulaciones con sus scores.
    
    Returns:
        Lista de postulaciones con scores
    """
    async with SessionLocal() as session:
        result = await session.execute(
            text("SELECT id, payload_json, score_total, creatividad, claridad, compromiso "
                 "FROM postulations ORDER BY id")
        )

        postulaciones = []
        for row in result:
            payload_json = row[1]
            texto = extraer_texto_del_payload(payload_json)

            postulaciones.append({
                "id": row[0],
                "texto": texto,
                "score_total": row[2],
                "score_creatividad": row[3],
                "score_claridad": row[4],
                "score_compromiso": row[5]
            })

        return postulaciones


def extraer_texto_del_payload(payload_json) -> str:
    """
    Extrae el texto de la respuesta abierta del payload JSON.
    
    Args:
        payload_json: El payload JSON de la postulación
    
    Returns:
        El texto extraído o string vacío si no se encuentra
    """
    if not payload_json:
        return ""

    # Si payload_json es string, intentar parsearlo
    if isinstance(payload_json, str):
        try:
            payload_json = json.loads(payload_json)
        except json.JSONDecodeError:
            return payload_json  # Si no es JSON válido, usar como texto

    # Si es dict, buscar campos comunes
    if isinstance(payload_json, dict):
        # Buscar campos comunes que podrían contener la respuesta
        for key in ['idea', 'datos', 'comentario', 'motivacion', 'descripcion', 'texto', 'proyecto', 'emprendimiento',
                    'adicionales']:
            if key in payload_json and payload_json[key]:
                return str(payload_json[key])

        # Si no se encuentra, convertir todo el payload a string
        return str(payload_json)

    # Si es otro tipo, convertir a string
    return str(payload_json)
