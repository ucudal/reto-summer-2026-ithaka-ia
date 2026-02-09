"""
Agente de Validación - Valida y formatea respuestas del usuario
"""

import logging
import os
import re
from typing import Optional, Tuple

from copilotkit import CopilotKitState
from copilotkit.langgraph import interrupt
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class ValidationAgent:
    """Agente para validar y formatear respuestas del usuario"""

    def __init__(self, copilot_state: CopilotKitState = None):
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.copilot_state = copilot_state or CopilotKitState()

    async def validate_question(self, user_input: str, validation_prompt: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Valida una pregunta abierta con IA
        Returns: (validated_data, error_message)
        """
        try:
            # Detectar si es la pregunta 13 (composición del equipo) y si es un proyecto individual
            if "composición del equipo" in validation_prompt.lower() or "equipo de trabajo" in validation_prompt.lower():
                user_input_lower = user_input.lower()
                individual_keywords = ["no tengo equipo", "proyecto solitario", "proyecto individual", "emprender solo",
                                       "trabajo solo", "sin equipo", "trabajo individual"]

                if any(keyword in user_input_lower for keyword in individual_keywords):
                    # Es un proyecto individual, validar que tenga suficiente información
                    if len(user_input.strip()) < 20:
                        return None, "Por favor proporciona más detalles sobre tu proyecto individual. Explica tu experiencia y por qué decides emprender solo."

                    # Aceptar la respuesta como válida para proyectos individuales
                    return user_input.strip(), None

            prompt = f"""
                        Eres un asistente que ayuda a formatear información.

                        INSTRUCCIÓN DE VALIDACIÓN:
                        {validation_prompt}

                        ENTRADA DEL USUARIO:
                        {user_input}

                        INSTRUCCIONES:
                        1. Analiza la entrada del usuario
                        2. Aplica la validación especificada
                        3. Si es válido, devuelve SOLO el dato formateado correctamente
                        4. Si NO es válido, devuelve "INVALID" seguido de un mensaje de error específico y útil

                        EJEMPLOS:
                        - Para email válido: "juan@ejemplo.com"
                        - Para email inválido: "INVALID: El formato del correo electrónico no es correcto. Debe incluir @ y un dominio válido (ej: usuario@dominio.com)"
                        - Para nombre válido: "Pérez, Juan"
                        - Para nombre inválido: "INVALID: El nombre debe incluir al menos apellido y nombre. Por favor usa el formato: Apellido, Nombre"

                        RESPUESTA:
                        """

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system",
                     "content": "Eres un validador experto que formatea información de manera precisa y proporciona mensajes de error útiles."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=150
            )

            result = response.choices[0].message.content.strip()

            # Verificar si es un error
            if result.startswith("INVALID:"):
                error_message = result[8:].strip()
                return None, error_message

            # Validación humana si es necesaria
            if await self._needs_human_validation(user_input, result):
                result = await self._get_human_validation(
                    f"Validar respuesta:\nUsuario: {user_input}\nIA: {result}"
                )

            # Verificar si la respuesta es válida
            if result.lower() == "none" or not result:
                return None, "No pude procesar la información proporcionada. Por favor intenta de nuevo."

            return result, None

        except Exception as e:
            logger.error(f"Error validating question: {e}")
            return None, "Ocurrió un error al procesar tu respuesta. Por favor intenta de nuevo."

    async def validate_email(self, email: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Valida formato de email
        Returns: (validated_email, error_message)
        """
        try:
            # Limpiar el email
            email = email.strip().lower()

            # Patrón básico de email
            pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

            if not re.match(pattern, email):
                # Análisis específico del error
                if '@' not in email:
                    return None, "El correo electrónico debe incluir el símbolo @. Ejemplo: usuario@dominio.com"
                elif email.count('@') > 1:
                    return None, "El correo electrónico solo puede tener un símbolo @. Ejemplo: usuario@dominio.com"
                elif '.' not in email.split('@')[1]:
                    return None, "El dominio del correo debe incluir un punto. Ejemplo: usuario@dominio.com"
                elif len(email.split('@')[1].split('.')[-1]) < 2:
                    return None, "La extensión del dominio debe tener al menos 2 caracteres. Ejemplo: usuario@dominio.com"
                else:
                    return None, "El formato del correo electrónico no es válido. Ejemplo: usuario@dominio.com"

            return email, None

        except Exception as e:
            logger.error(f"Error validating email: {e}")
            return None, "Error al validar el correo electrónico. Por favor intenta de nuevo."

    async def validate_name(self, name: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Valida y formatea nombre completo
        Returns: (formatted_name, error_message)
        """
        try:
            # Limpiar el nombre
            cleaned_name = name.strip()

            # Verificar que no esté vacío
            if not cleaned_name:
                return None, "Por favor ingresa tu nombre completo."

            # Verificar longitud mínima
            if len(cleaned_name) < 3:
                return None, "El nombre debe tener al menos 3 caracteres."

            # Verificar que tenga al menos 2 palabras
            parts = cleaned_name.split()
            if len(parts) < 2:
                return None, "Por favor ingresa tu nombre completo incluyendo apellido y nombre. Ejemplo: Juan Pérez o Pérez, Juan"

            # Si ya tiene coma, verificar formato
            if "," in cleaned_name:
                comma_parts = cleaned_name.split(",")
                if len(comma_parts) != 2:
                    return None, "El formato con coma debe ser: Apellido, Nombre. Ejemplo: Pérez, Juan"
                return cleaned_name, None

            # Formatear como "Apellido, Nombre"
            if len(parts) >= 2:
                return f"{parts[-1]}, {' '.join(parts[:-1])}", None

            return None, "No pude formatear el nombre correctamente. Por favor usa: Apellido, Nombre"

        except Exception as e:
            logger.error(f"Error validating name: {e}")
            return None, "Error al procesar el nombre. Por favor intenta de nuevo."

    async def validate_phone(self, phone: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Valida formato de teléfono
        Returns: (formatted_phone, error_message)
        """
        try:
            # Limpiar el teléfono
            phone = re.sub(r'[^\d+]', '', phone.strip())

            # Verificar que no esté vacío
            if not phone:
                return None, "Por favor ingresa un número de teléfono."

            # Verificar longitud mínima
            if len(phone) < 8:
                return None, "El número de teléfono debe tener al menos 8 dígitos."

            # Verificar longitud máxima
            if len(phone) > 15:
                return None, "El número de teléfono es demasiado largo. Verifica que sea correcto."

            # Verificar que solo tenga dígitos y +
            if not re.match(r'^[\d+]+$', phone):
                return None, "El número de teléfono solo puede contener dígitos y el símbolo +."

            return phone, None

        except Exception as e:
            logger.error(f"Error validating phone: {e}")
            return None, "Error al validar el número de teléfono. Por favor intenta de nuevo."

    async def validate_document_id(self, document: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Valida formato de documento de identidad
        Returns: (formatted_document, error_message)
        """
        try:
            # Limpiar el documento
            document = re.sub(r'[^\d]', '', document.strip())

            # Verificar que no esté vacío
            if not document:
                return None, "Por favor ingresa tu número de documento de identidad."

            # Verificar longitud (típicamente 7-8 dígitos en Uruguay)
            if len(document) < 7:
                return None, "El número de documento debe tener al menos 7 dígitos."

            if len(document) > 10:
                return None, "El número de documento es demasiado largo. Verifica que sea correcto."

            # Verificar que solo tenga dígitos
            if not document.isdigit():
                return None, "El número de documento solo puede contener dígitos."

            return document, None

        except Exception as e:
            logger.error(f"Error validating document: {e}")
            return None, "Error al validar el número de documento. Por favor intenta de nuevo."

    async def _needs_human_validation(self, user_input: str, ai_response: str) -> bool:
        """Determina si se necesita validación humana"""
        if ai_response.startswith("INVALID:"):
            return False

        if ai_response == "None":
            return True
        if len(ai_response.split()) < len(user_input.split()) / 2:
            return True
        return False

    async def _get_human_validation(self, prompt: str) -> str:
        """Obtiene validación humana a través de CopilotKit"""
        return await interrupt(prompt)
