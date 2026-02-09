"""
Agente Validator - Valida datos específicos del usuario
Integra con las funciones de validación existentes en utils/validators.py
"""

import logging
from typing import Any

from ..graph.state import ConversationState

logger = logging.getLogger(__name__)


class ValidatorAgent:
    """Agente para validar datos del usuario usando funciones existentes"""

    def __init__(self):
        # Opciones válidas para campos específicos
        self.valid_options = {
            "campus": ["Maldonado", "Montevideo", "Salto"],
            "ucu_relation": [
                "Estudiante", "Graduado", "Funcionario o Docente",
                "Solía estudiar allí", "No tengo relación con la UCU"
            ],
            "faculty": [
                "Ciencias de la Salud", "Ciencias Empresariales",
                "Ciencias Humanas + Derecho", "Ingeniería y Tecnologías"
            ],
            "discovery_method": [
                "Redes Sociales", "Curso de Grado", "Curso de Posgrado",
                "Buscando en la web", "Por alguna actividad de UCU",
                "A través de ANII/ANDE cuando buscaba una IPE"
            ],
            "yes_no": ["NO", "SI"],
            "project_stage": [
                "Idea inicial", "Prototipo/MVP", "Producto desarrollado",
                "Ventas/Tracción inicial", "Escalando"
            ],
            "support_needed": [
                "Tutoría para validar la idea",
                "Soporte para armar el plan de negocios",
                "Ayuda para obtener financiamiento para el proyecto",
                "Capacitación", "Ayuda para un tema específico", "Otro"
            ]
        }

    async def validate_data(self, state: ConversationState) -> ConversationState:
        """Valida datos según el tipo especificado en el contexto del agente"""

        user_response = state["user_message"].strip()
        validation_context = state.get("agent_context", {})
        validation_type = validation_context.get("validation_type")

        if not validation_type:
            logger.error("No validation type specified in agent context")
            state["validation_results"] = {
                "is_valid": False,
                "error": "Tipo de validación no especificado"
            }
            return state

        try:
            # Ejecutar validación según el tipo
            validation_result = self._validate_by_type(
                validation_type, user_response)

            state["validation_results"] = validation_result
            state["next_action"] = "validation_complete"
            state["should_continue"] = not validation_result["is_valid"]

        except Exception as e:
            logger.error(f"Error in validation: {e}")
            state["validation_results"] = {
                "is_valid": False,
                "error": f"Error en validación: {str(e)}"
            }

        return state

    def _validate_by_type(self, validation_type: str, value: str) -> dict[str, Any]:
        """Ejecuta validación específica según el tipo"""

        try:
            """if validation_type == "email":
                return self._validate_email(value)

            elif validation_type == "phone":
                return self._validate_phone(value)

            elif validation_type == "ci":
                return self._validate_ci(value)

            elif validation_type == "name":
                return self._validate_name(value)"""

            if validation_type == "location":
                return self._validate_location(value)

            elif validation_type == "text_min_length":
                return self._validate_text_min_length(value, 10)

            elif validation_type == "optional_text":
                return {"is_valid": True, "message": "Texto opcional válido"}

            elif validation_type in self.valid_options:
                return self._validate_options(validation_type, value)

            else:
                return {"is_valid": False, "error": f"Tipo de validación desconocido: {validation_type}"}

        except Exception as e:
            return {"is_valid": False, "error": str(e)}

    """def _validate_email(self, email: str) -> dict[str, Any]:
        try:
            validate_email(email)
            return {
                "is_valid": True,
                "message": "Email válido",
                "normalized_value": email.lower().strip()
            }
        except ValidationError as e:
            return {"is_valid": False, "error": str(e)}"""

    """def _validate_phone(self, phone: str) -> dict[str, Any]:
        try:
            validate_phone(phone)
            return {
                "is_valid": True,
                "message": "Teléfono válido",
                "normalized_value": phone.strip()
            }
        except ValidationError as e:
            return {"is_valid": False, "error": str(e)}"""

    """def _validate_ci(self, ci: str) -> dict[str, Any]:
        try:
            validate_ci(ci)
            return {
                "is_valid": True,
                "message": "Cédula válida",
                "normalized_value": re.sub(r'\D', '', ci)  # Solo números
            }
        except ValidationError as e:
            return {"is_valid": False, "error": str(e)}"""

    """def _validate_name(self, name: str) -> dict[str, Any]:
        name = name.strip()

        if len(name) < 2:
            return {"is_valid": False, "error": "El nombre debe tener al menos 2 caracteres"}

        if not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$', name):
            return {"is_valid": False, "error": "El nombre solo puede contener letras y espacios"}

        # Verificar que tenga al menos apellido y nombre
        parts = name.split()
        if len(parts) < 2:
            return {"is_valid": False, "error": "Por favor ingresa apellido y nombre"}

        return {
            "is_valid": True,
            "message": "Nombre válido",
            "normalized_value": name.title()  # Primera letra mayúscula
        }
"""

    def _validate_location(self, location: str) -> dict[str, Any]:
        """Valida ubicación con tolerancia a formatos"""
        if not location:
            return {"is_valid": False, "error": "La ubicación no puede estar vacía"}

        location = location.strip()
        logger.debug(f"Validando ubicación: '{location}'")

        # Acepta: "Ciudad, País", "Ciudad País", o "Ciudad-País"
        if len(location) < 4:
            return {"is_valid": False, "error": "Ubicación demasiado corta"}

        # Normaliza a "Ciudad, País"
        if ',' not in location:
            location = location.replace(' ', ', ', 1)  # Reemplaza solo el primer espacio

        return {
            "is_valid": True,
            "message": "Ubicación válida",
            "normalized_value": location.title()
        }

    def _validate_text_min_length(self, text: str, min_length: int = 10) -> dict[str, Any]:
        """Valida texto con longitud mínima"""
        text = text.strip()

        if len(text) < min_length:
            return {
                "is_valid": False,
                "error": f"La respuesta debe tener al menos {min_length} caracteres"
            }

        return {
            "is_valid": True,
            "message": "Texto válido",
            "normalized_value": text
        }

    def _validate_options(self, option_type: str, value: str) -> dict[str, Any]:
        """Valida que el valor esté entre las opciones válidas"""
        value = value.strip()
        valid_options = self.valid_options.get(option_type, [])

        # Buscar coincidencia exacta
        if value in valid_options:
            return {
                "is_valid": True,
                "message": "Opción válida",
                "normalized_value": value
            }

        # Buscar coincidencia case-insensitive
        for option in valid_options:
            if value.lower() == option.lower():
                return {
                    "is_valid": True,
                    "message": "Opción válida",
                    "normalized_value": option
                }

        # Buscar coincidencia parcial
        partial_matches = [
            opt for opt in valid_options if value.lower() in opt.lower()]
        if len(partial_matches) == 1:
            return {
                "is_valid": True,
                "message": f"Interpretamos tu respuesta como: {partial_matches[0]}",
                "normalized_value": partial_matches[0]
            }

        # No hay coincidencia
        options_text = "\n".join([f"• {opt}" for opt in valid_options])
        return {
            "is_valid": False,
            "error": f"Opción no válida. Las opciones disponibles son:\n{options_text}"
        }

    def validate_wizard_response(
            self,
            question_config: dict[str, Any],
            user_response: str
    ) -> dict[str, Any]:
        """Método específico para validar respuestas del wizard"""

        validation_type = question_config.get("validation")

        if validation_type == "rubrica":
            # Para preguntas evaluativas, validación básica de longitud
            return self._validate_text_min_length(user_response, 20)

        # Usar validación estándar
        return self._validate_by_type(validation_type, user_response)


# Instancia global del agente
validator_agent = ValidatorAgent()


# Función para usar en el grafo LangGraph


async def validate_data(state: ConversationState) -> ConversationState:
    """Función wrapper para LangGraph"""
    return await validator_agent.validate_data(state)
