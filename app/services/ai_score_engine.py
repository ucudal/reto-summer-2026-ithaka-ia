import json
import os
from typing import Dict, Any

from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()


class AIScoreEngine:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    async def evaluar_postulacion(self, texto: str) -> Dict[str, Any]:
        """
        Evalúa una postulación usando GPT-4 para análisis sofisticado.
        """
        if not texto or not texto.strip():
            return {
                "creatividad": 0,
                "claridad": 0,
                "compromiso": 0,
                "score_total": 0,
                "analisis": "Texto vacío"
            }

        try:
            # Prompt optimizado para GPT-4
            prompt = f"""
            Analyze the following job application text and evaluate the candidate in three dimensions:

            TEXT: "{texto}"

            Please evaluate on a scale of 0-100:

            1. CREATIVITY (0-100): Ability to generate original ideas, innovative thinking, varied vocabulary, development of unique concepts, and creative problem-solving approaches.

            2. CLARITY (0-100): Effective communication, text structure, use of connectors, logical coherence, ease of understanding, and well-organized thoughts.

            3. COMMITMENT (0-100): Demonstrated motivation, dedication, future planning, expressions of genuine interest, clear goals, and long-term vision.

            Respond ONLY with a valid JSON in this exact format:
            {{
                "creatividad": [number 0-100],
                "claridad": [number 0-100],
                "compromiso": [number 0-100],
                "score_total": [weighted average: creativity*0.4 + clarity*0.3 + commitment*0.3],
                "analisis": "Detailed analysis of 3-4 sentences explaining the evaluation with specific examples from the text"
            }}
            """

            response = await self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system",
                     "content": "You are an expert job application evaluator with deep understanding of human resources and candidate assessment. Analyze texts objectively, fairly, and provide detailed insights. Always respond with valid JSON format."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,  # Más bajo para mayor consistencia
                max_tokens=500  # Más tokens para análisis detallado
            )

            # Extraer y parsear la respuesta JSON
            content = response.choices[0].message.content.strip()

            # Intentar extraer JSON del texto
            try:
                # Buscar JSON en la respuesta
                start = content.find('{')
                end = content.rfind('}') + 1
                if start != -1 and end != 0:
                    json_str = content[start:end]
                    scores = json.loads(json_str)

                    # Validar que los scores estén en el rango correcto
                    for key in ['creatividad', 'claridad', 'compromiso']:
                        if key in scores:
                            scores[key] = max(0, min(100, int(scores[key])))

                    # Calcular score total si no está presente
                    if 'score_total' not in scores:
                        scores['score_total'] = round(
                            scores['creatividad'] * 0.4 +
                            scores['claridad'] * 0.3 +
                            scores['compromiso'] * 0.3, 2
                        )

                    return scores
                else:
                    raise ValueError("No se encontró JSON válido en la respuesta")

            except (json.JSONDecodeError, ValueError) as e:
                print(f"Error parseando respuesta de GPT-4: {e}")
                print(f"Respuesta recibida: {content}")
                # Fallback a evaluación básica
                return self._evaluacion_fallback(texto)

        except Exception as e:
            print(f"Error en evaluación con GPT-4: {e}")
            # Fallback a evaluación básica
            return self._evaluacion_fallback(texto)

    def _evaluacion_fallback(self, texto: str) -> Dict[str, Any]:
        """
        Evaluación básica de fallback cuando GPT-4 no está disponible.
        """
        # Análisis básico basado en longitud y palabras clave
        score_base = min(100, len(texto) // 2)

        return {
            "creatividad": score_base,
            "claridad": score_base,
            "compromiso": score_base,
            "score_total": round(score_base, 2),
            "analisis": "Evaluación básica (GPT-4 no disponible)"
        }


# Instancia global
ai_engine = AIScoreEngine()


async def evaluar_postulacion_ai(texto: str) -> Dict[str, Any]:
    """
    Función wrapper para evaluar postulaciones con GPT-4.
    """
    return await ai_engine.evaluar_postulacion(texto)
