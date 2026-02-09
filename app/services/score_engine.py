import re
from typing import Dict, Any


def evaluar_postulacion(texto: str) -> Dict[str, Any]:
    """
    Evalúa una postulación basándose en el texto de respuesta abierta.
    Retorna un diccionario con los scores de creatividad, claridad, compromiso y score total.
    """
    if not texto or not texto.strip():
        return {
            "creatividad": 0,
            "claridad": 0,
            "compromiso": 0,
            "score_total": 0
        }

    # Normalizar el texto
    texto = texto.lower().strip()

    # Métricas para evaluar
    creatividad = evaluar_creatividad(texto)
    claridad = evaluar_claridad(texto)
    compromiso = evaluar_compromiso(texto)

    # Calcular score total (promedio ponderado)
    score_total = (creatividad * 0.4 + claridad * 0.3 + compromiso * 0.3)

    return {
        "creatividad": creatividad,
        "claridad": claridad,
        "compromiso": compromiso,
        "score_total": round(score_total, 2)
    }


def evaluar_creatividad(texto: str) -> int:
    """
    Evalúa la creatividad basándose en:
    - Uso de vocabulario variado
    - Ideas originales
    - Estructura narrativa
    """
    score = 0

    # Vocabulario variado (palabras únicas)
    palabras = re.findall(r'\b\w+\b', texto)
    palabras_unicas = set(palabras)
    diversidad_vocabulario = len(palabras_unicas) / max(len(palabras), 1)

    if diversidad_vocabulario > 0.7:
        score += 30
    elif diversidad_vocabulario > 0.5:
        score += 20
    elif diversidad_vocabulario > 0.3:
        score += 10

    # Longitud del texto (indica desarrollo de ideas)
    if len(texto) > 500:
        score += 25
    elif len(texto) > 300:
        score += 15
    elif len(texto) > 100:
        score += 10

    # Palabras que indican creatividad
    palabras_creativas = ['innovar', 'crear', 'diseñar', 'desarrollar', 'imaginar',
                          'explorar', 'experimentar', 'transformar', 'revolucionar']
    score_creatividad = sum(1 for palabra in palabras_creativas if palabra in texto) * 5

    return min(score + score_creatividad, 100)


def evaluar_claridad(texto: str) -> int:
    """
    Evalúa la claridad basándose en:
    - Estructura del texto
    - Uso de conectores
    - Coherencia
    """
    score = 0

    # Conectores que mejoran la claridad
    conectores = ['además', 'también', 'por otro lado', 'sin embargo', 'por lo tanto',
                  'en consecuencia', 'en primer lugar', 'finalmente', 'en resumen']

    score_conectores = sum(1 for conector in conectores if conector in texto) * 8

    # Puntuación (indica estructura)
    signos_puntuacion = texto.count('.') + texto.count('!') + texto.count('?')
    if signos_puntuacion > 5:
        score += 20
    elif signos_puntuacion > 3:
        score += 15
    elif signos_puntuacion > 1:
        score += 10

    # Longitud moderada (no muy corto, no muy largo)
    if 100 < len(texto) < 1000:
        score += 25
    elif 50 < len(texto) < 1500:
        score += 15

    return min(score + score_conectores, 100)


def evaluar_compromiso(texto: str) -> int:
    """
    Evalúa el compromiso basándose en:
    - Expresiones de motivación
    - Planes específicos
    - Expresiones de dedicación
    """
    score = 0

    # Palabras que indican compromiso
    palabras_compromiso = ['compromiso', 'dedicación', 'esfuerzo', 'trabajar', 'estudiar',
                           'aprender', 'mejorar', 'desarrollar', 'crecer', 'lograr',
                           'alcanzar', 'conseguir', 'perseverar', 'constancia']

    score_palabras = sum(1 for palabra in palabras_compromiso if palabra in texto) * 6

    # Expresiones de tiempo futuro (indica planificación)
    expresiones_futuro = ['voy a', 'planeo', 'pretendo', 'tengo la intención', 'me propongo',
                          'quiero', 'deseo', 'aspirar', 'objetivo', 'meta']

    score_futuro = sum(1 for expr in expresiones_futuro if expr in texto) * 5

    # Expresiones de motivación personal
    expresiones_motivacion = ['me apasiona', 'me interesa', 'me gusta', 'me emociona',
                              'me motiva', 'me inspira', 'me desafía']

    score_motivacion = sum(1 for expr in expresiones_motivacion if expr in texto) * 4

    return min(score_palabras + score_futuro + score_motivacion, 100)
