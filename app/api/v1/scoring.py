from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services.ai_score_engine import evaluar_postulacion_ai
from app.services.scoring_service import procesar_postulaciones, procesar_postulacion_especifica, obtener_postulaciones

router = APIRouter()


class ScoringRequest(BaseModel):
    texto: str
    use_ai: bool = False
    ai_provider: str = "openai"


class ScoringResponse(BaseModel):
    creatividad: int
    claridad: int
    compromiso: int
    score_total: float
    analisis: Optional[str] = None


class PostulationResponse(BaseModel):
    id: int
    texto: str
    score_total: Optional[float]
    score_creatividad: Optional[int]
    score_claridad: Optional[int]
    score_compromiso: Optional[int]


@router.post("/scoring/evaluate", response_model=ScoringResponse)
async def evaluate_text(request: ScoringRequest) -> ScoringResponse:
    """
    Evalúa un texto de postulación y retorna los scores.
    
    Args:
        request: Contiene el texto a evaluar y configuración del motor
    
    Returns:
        Scores calculados con análisis opcional
    """
    try:
        if request.use_ai:
            scores = await evaluar_postulacion_ai(request.texto)
        else:
            from app.services.score_engine import evaluar_postulacion
            scores = evaluar_postulacion(request.texto)

        return ScoringResponse(**scores)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en evaluación: {str(e)}")


@router.post("/scoring/process-all")
async def process_all_postulations(
        use_ai: bool = Query(False, description="Usar motor de IA en lugar de reglas"),
        ai_provider: str = Query("openai", description="Proveedor de IA (solo 'openai' disponible)")
):
    """
    Procesa todas las postulaciones sin score en la base de datos.
    
    Args:
        use_ai: Si usar motor de IA (OpenAI) en lugar de reglas
        ai_provider: Proveedor de IA (solo "openai" disponible)
    
    Returns:
        Mensaje de confirmación
    """
    try:
        await procesar_postulaciones(use_ai=use_ai, ai_provider=ai_provider)
        return {"message": "Procesamiento completado exitosamente"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en procesamiento: {str(e)}")


@router.post("/scoring/process/{postulation_id}")
async def process_specific_postulation(
        postulation_id: int,
        use_ai: bool = Query(False, description="Usar motor de IA en lugar de reglas"),
        ai_provider: str = Query("openai", description="Proveedor de IA (solo 'openai' disponible)")
):
    """
    Procesa una postulación específica por ID.
    
    Args:
        postulation_id: ID de la postulación a procesar
        use_ai: Si usar motor de IA (OpenAI) en lugar de reglas
        ai_provider: Proveedor de IA (solo "openai" disponible)
    
    Returns:
        Scores calculados para la postulación
    """
    try:
        scores = await procesar_postulacion_especifica(postulation_id, use_ai=use_ai, ai_provider=ai_provider)

        if scores is None:
            raise HTTPException(status_code=404, detail=f"Postulación {postulation_id} no encontrada")

        return {
            "postulation_id": postulation_id,
            "scores": scores,
            "message": f"Postulación {postulation_id} procesada exitosamente"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error procesando postulación: {str(e)}")


@router.get("/scoring/postulations", response_model=List[PostulationResponse])
async def get_postulations():
    """
    Obtiene todas las postulaciones con sus scores.
    
    Returns:
        Lista de postulaciones con scores
    """
    try:
        postulaciones = await obtener_postulaciones()
        return [PostulationResponse(**post) for post in postulaciones]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo postulaciones: {str(e)}")


@router.get("/scoring/health")
async def health_check():
    """
    Verifica el estado del servicio de scoring.
    
    Returns:
        Estado del servicio
    """
    return {
        "status": "healthy",
        "available_engines": ["rules", "openai"],
        "message": "Servicio de scoring funcionando correctamente"
    }
