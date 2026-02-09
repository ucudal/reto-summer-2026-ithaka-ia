"""
Agente Wizard - Maneja formularios interactivos para postulación de proyectos de Ithaka
"""

import logging
import os
from typing import Dict, Any, Optional, List

from langchain_core.messages import AIMessage
from openai import AsyncOpenAI

from .validation_agent import ValidationAgent
from .validator import validator_agent
from ..config.questions import get_question, is_conditional_question, should_continue_after_question_11
from ..graph.state import ConversationState

logger = logging.getLogger(__name__)


class WizardAgent:

    # Inicializa el agente
    def __init__(self):
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.validation = ValidationAgent()
        self._initialize_nodes()

    # Crea la estructura de nodos del formulario basado en questions.py
    def _initialize_nodes(self):
        self.nodes: Dict[str, Dict[str, Any]] = {
            "welcome": {
                "node_id": "welcome",
                "node_type": "welcome_question",
                "content": "¿Quieres postular una idea/proyecto o empezar a desarrollar tu espíritu emprendedor?",
                "example": "Responde SI o NO",
                "validation": "Extrae si el usuario quiere continuar (SI/NO).",
                "error_msg": "Por favor responde SI o NO.",
                "next": "question_1",
                "prev": None,
                "id": "welcome_response",
                "options": [
                    {"value": "si", "label": "SI"},
                    {"value": "no", "label": "NO"}
                ],
                "required": True
            }
        }

        # Agregar nodos basados en  questions.py
        for question_num in range(1, 21):  # Preguntas 1-20
            question_config = get_question(question_num)
            if question_config:
                node_id = f"question_{question_num}"
                prev_node = f"question_{question_num - 1}" if question_num > 1 else "welcome"
                next_node = f"question_{question_num + 1}" if question_num < 20 else "completion"

                # Determinar el tipo de nodo basado en la configuración (ej: multiple_choice)
                node_type = self._get_node_type_from_config(question_config)

                # Crear el nodo
                self.nodes[node_id] = {
                    "node_id": node_id,
                    "node_type": node_type,
                    "content": question_config.get("text", ""),
                    "example": self._get_example_from_config(question_config),
                    "validation": question_config.get("validation", ""),
                    "error_msg": self._get_error_msg_from_config(question_config),
                    "next": next_node,
                    "prev": prev_node,
                    "id": question_config.get("field_name", f"field_{question_num}"),
                    "options": self._get_options_from_config(question_config),
                    "required": question_config.get("required", True),
                    "question_config": question_config  # Guardar la configuración completa
                }

        # Nodo de completación
        self.nodes["completion"] = {
            "node_id": "completion",
            "node_type": "completion",
            "content": "¡Muchas gracias por completar el formulario de Ithaka! Hemos recibido tus respuestas y te contactaremos a la brevedad.",
            "next": None,
            "prev": "question_20",
            "id": None,
            "example": None,
            "validation": None,
            "error_msg": None,
            "options": None,
            "required": False
        }

    def _get_node_type_from_config(self, question_config: Dict[str, Any]) -> str:
        """Determina el tipo de nodo basado en la configuración"""
        validation_type = question_config.get("validation", "")
        options = question_config.get("options", [])

        if validation_type == "yes_no":
            return "yes_no"
        elif options:
            if question_config.get("type") == "evaluative":
                return "conditional_multiselect"
            else:
                return "multiple_choice"
        else:
            return "question"

    # Proporcionar ejemplos específicos basados en el tipo de validación requerida para cada pregunta
    def _get_example_from_config(self, question_config: Dict[str, Any]) -> Optional[str]:
        validation_type = question_config.get("validation", "")

        examples = {
            "name": "Ejemplo: Pérez, Juan",
            "email": "Ejemplo: juan@ejemplo.com",
            "phone": "Ejemplo: 099123456",
            "ci": "Ejemplo: 12345678",
            "text_min_length": "Cuéntanos más detalles...",
            "rubrica": "Describe detalladamente..."
        }

        return examples.get(validation_type, None)

    # Proporcionar mensajes de error específicos y útiles basados en el tipo de validación
    def _get_error_msg_from_config(self, question_config: Dict[str, Any]) -> str:
        """Obtiene el tipo de validación de la configuración de la pregunta"""
        validation_type = question_config.get("validation", "")

        """Selecciona el mensaje correspondiente"""
        error_messages = {
            "name": "No pude identificar tu nombre completo. Por favor usa: Apellido, Nombre",
            "email": "Correo electrónico inválido. Por favor ingresa un correo válido.",
            "phone": "Por favor ingresa un número de teléfono válido.",
            "ci": "Por favor ingresa un número de documento válido.",
            "text_min_length": "Por favor proporciona más detalles.",
            "rubrica": "Por favor describe con más detalle."
        }

        return error_messages.get(validation_type, "Por favor proporciona una respuesta válida.")

    def _get_options_from_config(self, question_config: Dict[str, Any]) -> Optional[List[Dict[str, str]]]:
        """Obtiene las opciones de la configuración"""
        options = question_config.get("options", [])
        if not options:
            return None

        return [{"value": opt.lower().replace(" ", "_"), "label": opt} for opt in options]

    """Maneja el flujo del wizard en el contexto de LangGraph"""

    async def handle_wizard_flow(self, state: ConversationState) -> ConversationState:

        user_message = [m.content for m in state["messages"] if m.type == "human"][0]
        wizard_state = state.get("wizard_state", "INACTIVE")
        current_question = state.get("current_question", 1)
        wizard_responses = state.get("wizard_responses", {})

        try:
            # Si es la primera vez o si se envía "postular" para reiniciar
            # Reinicia el proceso si es primera vez o si el usuario solicita explícitamente
            if wizard_state == "INACTIVE" or user_message.lower().strip() == "postular":
                return await self._start_wizard(state)

            # Si ya está activo, procesar la respuesta
            if wizard_state == "ACTIVE":
                return await self._process_wizard_response(state)

            # Si está completado, mostrar resumen
            if wizard_state == "COMPLETED":
                return await self._show_completion_summary(state)

        except Exception as e:
            raise e
            logger.error(f"Error in wizard flow: {e}")
            return self._handle_wizard_error(state, str(e))

        return state

    async def _start_wizard(self, state: ConversationState) -> ConversationState:
        """Inicia el wizard"""
        try:
            # Inicializar estado del wizard
            state["wizard_state"] = "ACTIVE"
            state["current_question"] = 1  # Empezar con el welcome
            state["wizard_responses"] = {}
            state["wizard_session_id"] = f"wizard_{state.get('conversation_id', 'new')}"

            # Obtener nodo welcome
            current_node = self.nodes["welcome"]
            response = self._format_node_response(current_node)

            state["agent_context"] = {
                "response": response,
                "wizard_started": True,
                "current_node": current_node["node_id"]
            }
            state["next_action"] = "send_response"
            state["should_continue"] = False

            return {
                "agent_context": state["agent_context"],
                "next_action": state["next_action"],
                "should_continue": state["should_continue"],
                "wizard_state": state["wizard_state"],
                "current_question": state["current_question"],
                "wizard_responses": state["wizard_responses"],
                "wizard_session_id": state["wizard_session_id"],
                "messages": [AIMessage(content=response)]
            }

        except Exception as e:
            raise e
            logger.error(f"Error starting wizard: {e}")
            return self._handle_wizard_error(state, str(e))

    async def _process_wizard_response(self, state: ConversationState) -> ConversationState:
        """Procesa la respuesta del usuario en el wizard"""
        try:
            user_message = [m.content for m in state["messages"] if m.type == "human"][0]
            current_question = state.get("current_question", 1)
            wizard_responses = state.get("wizard_responses", {})

            # Verificar si estamos esperando validación humana
            if state.get("human_validation_needed"):
                return await self._handle_human_validation_response(state, user_message)

            # Determinar el nodo actual basado en la pregunta
            current_node_id = self._get_node_id_by_question(current_question)
            current_node = self.nodes[current_node_id]

            # Procesar comandos especiales
            if user_message.lower() in ["atras", "back", "anterior"]:
                return await self._go_back(state)

            if user_message.lower() in ["guardar", "save", "pausar"]:
                return await self._save_progress(state)

            if user_message.lower() in ["cancelar", "cancel", "salir", "exit"]:
                return await self._cancel_wizard(state)

            # Procesar respuesta según tipo de nodo
            if current_node["node_type"] == "welcome_question":
                return await self._process_welcome_question_response(state, current_node, user_message)

            elif current_node["node_type"] == "question":
                result = await self._process_question_response(state, current_node, user_message)

            elif current_node["node_type"] == "multiple_choice":
                result = await self._process_multiple_choice_response(state, current_node, user_message)

            elif current_node["node_type"] == "yes_no":
                result = await self._process_yes_no_response(state, current_node, user_message)

            elif current_node["node_type"] == "conditional_multiselect":
                result = await self._process_multiselect_response(state, current_node, user_message)

            elif current_node["node_type"] == "completion":
                return await self._complete_wizard(state)

            else:
                result = {"error": "Tipo de nodo no soportado"}

            # Si hay error, mantener en la misma pregunta
            if "error" in result:
                state["agent_context"] = {
                    "response": result["error"],
                    "current_node": current_node["node_id"],
                    "validation_error": True
                }
                state["next_action"] = "send_response"
                state["should_continue"] = False
                return {
                    "agent_context": state["agent_context"],
                    "next_action": state["next_action"],
                    "should_continue": state["should_continue"],
                    "messages": [AIMessage(content=result["error"])]
                }

            # Si se necesita validación humana
            if result.get("status") == "human_validation_needed":
                state["agent_context"] = {
                    "response": result["message"],
                    "current_node": current_node["node_id"],
                    "human_validation_needed": True,
                    "pending_validation": user_message
                }
                state["next_action"] = "send_response"
                state["should_continue"] = False
                return {
                    "agent_context": state["agent_context"],
                    "next_action": state["next_action"],
                    "should_continue": state["should_continue"],
                    "messages": [AIMessage(content=result["message"])]
                }

            # Avanzar al siguiente nodo
            return await self._advance_to_next(state, current_node)

        except Exception as e:
            raise e
            logger.error(f"Error processing wizard response: {e}")
            return self._handle_wizard_error(state, str(e))

    async def _process_welcome_question_response(self, state: ConversationState, node: Dict[str, Any],
                                                 user_input: str) -> ConversationState:
        """Procesa la respuesta de la pregunta de bienvenida (SI/NO)"""
        try:
            user_input_lower = user_input.lower().strip()

            if user_input_lower in ["si", "sí", "yes", "y"]:
                validated = "SI"
            elif user_input_lower in ["no", "n"]:
                validated = "NO"
            else:
                # Error de validación
                state["agent_context"] = {
                    "response": "Por favor responde SI o NO.",
                    "current_node": node["node_id"],
                    "validation_error": True
                }
                state["next_action"] = "send_response"
                state["should_continue"] = False
                return state

            # Guardar respuesta
            wizard_responses = state.get("wizard_responses", {})
            wizard_responses[node["id"]] = validated
            state["wizard_responses"] = wizard_responses

            # Si el usuario responde "SI", continuar con el formulario
            if validated == "SI":
                return await self._advance_to_next(state, node)
            else:
                # Si el usuario responde "NO", terminar el wizard
                state["wizard_state"] = "COMPLETED"
                state["agent_context"] = {
                    "response": "Entendido. Si en el futuro quieres postular una idea o desarrollar tu espíritu emprendedor, no dudes en contactarnos. ¡Que tengas un excelente día!",
                    "wizard_completed": True,
                    "user_declined": True
                }
                state["next_action"] = "send_response"
                state["should_continue"] = False
                return state

        except Exception as e:
            logger.error(f"Error processing welcome question response: {e}")
            return self._handle_wizard_error(state, node["error_msg"])

    async def _process_question_response(self, state: ConversationState, node: Dict[str, Any], user_input: str) -> Dict[
        str, Any]:
        """Procesa respuesta de pregunta abierta usando la configuración"""
        try:
            question_config = node.get("question_config", {})
            validation_type = question_config.get("validation", "")
            field_name = question_config.get("field_name", "")

            # Usar validación específica según el tipo de pregunta
            validated = None
            error_message = None

            # Validación específica por tipo de campo
            if validation_type == "email":
                validated, error_message = await self.validation.validate_email(user_input)
            elif validation_type == "name":
                validated, error_message = await self.validation.validate_name(user_input)
            elif validation_type == "phone":
                validated, error_message = await self.validation.validate_phone(user_input)
            elif validation_type == "ci":
                validated, error_message = await self.validation.validate_document_id(user_input)

            elif validation_type == "location":
                result = validator_agent._validate_location(user_input)
                if not result["is_valid"]:
                    logger.warning(f"Error en ubicación: {result['error']}")
                return result

            elif validation_type == "text_min_length":
                min_length = question_config.get("min_length", 10)
                if len(user_input.strip()) >= min_length:
                    validated = user_input
                else:
                    error_message = f"Por favor proporciona al menos {min_length} caracteres."
            elif validation_type == "optional_text":
                # Para texto opcional, aceptar cualquier entrada o texto vacío
                if user_input.strip():
                    validated = user_input.strip()
                else:
                    validated = "Sin comentarios adicionales"
            elif validation_type == "rubrica":
                validated, error_message = await self.validation.validate_question(user_input,
                                                                                   question_config.get("text", ""))
            else:
                # Validación genérica
                validated, error_message = await self.validation.validate_question(user_input,
                                                                                   question_config.get("text", ""))

            # Si se necesita validación humana
            if validated == "HUMAN_VALIDATION_NEEDED":
                return {
                    "status": "human_validation_needed",
                    "message": f"Necesito validación humana para: '{user_input}'. Por favor confirma o corrige la información."
                }

            # Si hay error de validación
            if error_message:
                return {"error": error_message}

            if not validated:
                return {"error": node["error_msg"]}

            # Guardar respuesta validada
            wizard_responses = state.get("wizard_responses", {})
            wizard_responses[field_name] = validated
            state["wizard_responses"] = wizard_responses

            return {"status": "success"}

        except Exception as e:
            logger.error(f"Error validating question response: {e}")
            return {"error": "Ocurrió un error al validar tu respuesta. Por favor intenta de nuevo."}

    async def _process_multiple_choice_response(self, state: ConversationState, node: Dict[str, Any],
                                                user_input: str) -> Dict[str, Any]:
        """Procesa respuesta de selección única"""
        try:
            if not node["options"]:
                return {"error": "Opciones no definidas"}

            # Buscar opción seleccionada
            selected_option = None
            user_input_lower = user_input.lower().strip()

            for option in node["options"]:
                if (user_input_lower == option["value"].lower() or
                        user_input_lower == option["label"].lower() or
                        user_input_lower in option["label"].lower()):
                    selected_option = option
                    break

            if not selected_option:
                # Mostrar opciones disponibles
                options_text = "\n".join([f"• {opt['label']}" for opt in node["options"]])
                return {"error": f"Por favor selecciona una de estas opciones:\n{options_text}"}

            # Guardar respuesta
            wizard_responses = state.get("wizard_responses", {})
            field_name = node.get("question_config", {}).get("field_name", node["id"])
            wizard_responses[field_name] = selected_option["value"]
            state["wizard_responses"] = wizard_responses

            return {"status": "success"}

        except Exception as e:
            raise e
            logger.error(f"Error processing multiple choice: {e}")
            return {"error": node["error_msg"]}

    async def _process_yes_no_response(self, state: ConversationState, node: Dict[str, Any], user_input: str) -> Dict[
        str, Any]:
        """Procesa respuesta SI/NO"""
        try:
            user_input_lower = user_input.lower().strip()

            if user_input_lower in ["si", "sí", "yes", "y"]:
                validated = "SI"
            elif user_input_lower in ["no", "n"]:
                validated = "NO"
            else:
                return {"error": "Por favor responde SI o NO"}

            # Guardar respuesta
            wizard_responses = state.get("wizard_responses", {})
            field_name = node.get("question_config", {}).get("field_name", node["id"])
            wizard_responses[field_name] = validated
            state["wizard_responses"] = wizard_responses

            return {"status": "success"}

        except Exception as e:
            raise e
            logger.error(f"Error processing yes/no response: {e}")
            return {"error": node["error_msg"]}

    async def _process_multiselect_response(self, state: ConversationState, node: Dict[str, Any], user_input: str) -> \
    Dict[str, Any]:
        """Procesa respuesta de selección múltiple"""
        try:
            if not node["options"]:
                return {"error": "Opciones no definidas"}

            # Parsear selecciones múltiples
            selections = [s.strip().lower() for s in user_input.split(",")]
            selected_values = []

            for selection in selections:
                for option in node["options"]:
                    if (selection == option["value"].lower() or
                            selection == option["label"].lower() or
                            selection in option["label"].lower()):
                        selected_values.append(option["value"])
                        break

            if not selected_values and node["required"]:
                options_text = "\n".join([f"• {opt['label']}" for opt in node["options"]])
                return {"error": f"Por favor selecciona al menos una opción:\n{options_text}"}

            # Guardar respuesta
            wizard_responses = state.get("wizard_responses", {})
            field_name = node.get("question_config", {}).get("field_name", node["id"])
            wizard_responses[field_name] = selected_values
            state["wizard_responses"] = wizard_responses

            return {"status": "success"}

        except Exception as e:
            raise e
            logger.error(f"Error processing multiselect: {e}")
            return {"error": node["error_msg"]}

    async def _advance_to_next(self, state: ConversationState, current_node: Dict[str, Any]) -> ConversationState:
        """Avanza al siguiente nodo usando la configuración centralizada"""
        if not current_node["next"]:
            return await self._complete_wizard(state)

        # Actualizar pregunta actual
        next_question = state.get("current_question", 1) + 1
        state["current_question"] = next_question

        # Obtener siguiente nodo
        next_node = self.nodes[current_node["next"]]

        # Verificar si el siguiente nodo es condicional y debe saltarse
        if next_node.get("question_config"):
            question_config = next_node["question_config"]
            if not is_conditional_question(next_question, state.get("wizard_responses", {})):
                # Saltar este nodo y continuar con el siguiente
                return await self._advance_to_next(state, next_node)

        # Verificar si debemos continuar después de la pregunta 11
        if next_question == 12 and not should_continue_after_question_11(state.get("wizard_responses", {})):
            # Saltar a la pregunta 20 
            state["current_question"] = 20
            next_node = self.nodes["question_20"]

        response = self._format_node_response(next_node)

        state["agent_context"] = {
            "response": response,
            "current_node": next_node["node_id"],
            "question_number": next_question
        }
        state["next_action"] = "send_response"
        state["should_continue"] = False

        return {
            "agent_context": state["agent_context"],
            "next_action": state["next_action"],
            "should_continue": state["should_continue"],
            "current_question": state["current_question"],
            "messages": [AIMessage(content=response)]
        }

    async def _go_back(self, state: ConversationState) -> ConversationState:
        """Retrocede a la pregunta anterior"""
        current_question = state.get("current_question", 1)

        if current_question <= 1:
            state["agent_context"] = {
                "response": "No hay preguntas anteriores. ¿Quieres cancelar el formulario?",
                "current_node": "welcome"
            }
            state["next_action"] = "send_response"
            state["should_continue"] = False
            return state

        # Retroceder una pregunta
        previous_question = current_question - 1
        state["current_question"] = previous_question

        # Obtener nodo anterior
        previous_node_id = self._get_node_id_by_question(previous_question)
        previous_node = self.nodes[previous_node_id]
        response = self._format_node_response(previous_node)

        state["agent_context"] = {
            "response": response,
            "current_node": previous_node["node_id"],
            "question_number": previous_question
        }
        state["next_action"] = "send_response"
        state["should_continue"] = False

        return {
            "agent_context": state["agent_context"],
            "next_action": state["next_action"],
            "should_continue": state["should_continue"],
            "current_question": state["current_question"],
            "messages": [AIMessage(content=response)]
        }

    async def _save_progress(self, state: ConversationState) -> ConversationState:
        """Guarda el progreso actual"""
        try:
            progress = {
                "wizard_session_id": state.get("wizard_session_id"),
                "current_question": state.get("current_question"),
                "wizard_responses": state.get("wizard_responses", {}),
                "wizard_state": state.get("wizard_state")
            }

            # TODO: Guardar en base de datos cuando esté disponible
            # await self._save_to_database(progress)

            state["agent_context"] = {
                "response": "Progreso guardado exitosamente. Puedes continuar más tarde.",
                "progress_saved": True
            }
            state["next_action"] = "send_response"
            state["should_continue"] = False

            return {
                "agent_context": state["agent_context"],
                "next_action": state["next_action"],
                "should_continue": state["should_continue"],
                "messages": [AIMessage(content="Progreso guardado exitosamente. Puedes continuar más tarde.")]
            }

        except Exception as e:
            raise e
            logger.error(f"Error saving progress: {e}")
            return self._handle_wizard_error(state, "Error al guardar el progreso")

    async def _cancel_wizard(self, state: ConversationState) -> ConversationState:
        """Cancela el wizard y reinicia el estado"""
        try:
            # Limpiar estado del wizard
            state["wizard_state"] = "INACTIVE"
            state["current_question"] = 1
            state["wizard_responses"] = {}
            state["wizard_session_id"] = None

            # Limpiar contexto de validación si existe
            if "human_validation_needed" in state:
                del state["human_validation_needed"]
            if "pending_validation" in state:
                del state["pending_validation"]

            state["agent_context"] = {
                "response": "Formulario cancelado. Si quieres volver a empezar, escribe 'postular' o simplemente comienza una nueva conversación.",
                "wizard_cancelled": True
            }
            state["next_action"] = "send_response"
            state["should_continue"] = False

            return {
                "agent_context": state["agent_context"],
                "next_action": state["next_action"],
                "should_continue": state["should_continue"],
                "messages": [AIMessage(
                    content="Formulario cancelado. Si quieres volver a empezar, escribe 'postular' o simplemente comienza una nueva conversación.")]
            }

        except Exception as e:
            raise e
            logger.error(f"Error cancelling wizard: {e}")
            return self._handle_wizard_error(state, "Error al cancelar el formulario")

    async def _complete_wizard(self, state: ConversationState) -> ConversationState:
        """Completa el wizard y muestra resumen"""
        try:
            wizard_responses = state.get("wizard_responses", {})

            # Generar resumen usando IA
            summary = await self._generate_completion_summary(wizard_responses)

            state["wizard_state"] = "COMPLETED"
            state["agent_context"] = {
                "response": summary,
                "wizard_completed": True,
                "final_responses": wizard_responses
            }
            state["next_action"] = "send_response"
            state["should_continue"] = False

            return {
                "agent_context": state["agent_context"],
                "next_action": state["next_action"],
                "should_continue": state["should_continue"],
                "wizard_state": state["wizard_state"],
                "wizard_responses": state["wizard_responses"],
                "messages": [AIMessage(content=summary)]
            }

        except Exception as e:
            raise e
            logger.error(f"Error completing wizard: {e}")
            return self._handle_wizard_error(state, str(e))

    async def _generate_completion_summary(self, responses: Dict[str, Any]) -> str:
        """Genera un resumen de las respuestas usando IA"""
        try:
            responses_text = "\n".join([f"• {key}: {value}" for key, value in responses.items()])

            prompt = f"""
Genera un resumen amigable y profesional de las respuestas del formulario de postulación de Ithaka:

RESPUESTAS RECIBIDAS:
{responses_text}

INSTRUCCIONES:
1. Agradece por completar el formulario de Ithaka
2. Resume brevemente la información proporcionada
3. Menciona que el equipo de Ithaka revisará la información
4. Indica que se contactarán a la brevedad
5. Mantén un tono profesional pero amigable
6. Incluye información de contacto si es relevante

RESUMEN:
"""

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system",
                     "content": "Eres el asistente de Ithaka. Genera resúmenes profesionales y amigables."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=300
            )

            return response.choices[0].message.content

        except Exception as e:
            raise e
            logger.error(f"Error generating completion summary: {e}")
            return """
¡Muchas gracias por completar el formulario de Ithaka!

Hemos recibido tu información y nuestro equipo la revisará cuidadosamente. Te contactaremos a la brevedad para continuar con el proceso.

Si tienes alguna pregunta, no dudes en contactarnos.

¡Que tengas un excelente día!
"""

    def _format_node_response(self, node: Dict[str, Any]) -> str:
        """Formatea la respuesta del nodo para el usuario"""
        response = node["content"]

        if node["example"]:
            response += f"\n\n{node['example']}"

        if node["options"]:
            response += "\n\nOpciones disponibles:"
            for i, option in enumerate(node["options"], 1):
                response += f"\n{i}. {option['label']}"

        if node["node_type"] == "conditional_multiselect":
            response += "\n\n(Puedes seleccionar múltiples opciones separadas por comas)"

        response += "\n\nComandos disponibles: 'atras', 'guardar', 'cancelar'"

        return response

    def _get_node_id_by_question(self, question_number: int) -> str:
        """Obtiene el ID del nodo basado en el número de pregunta"""
        if question_number == 0:
            return "welcome"
        elif question_number == 1:
            return "welcome"
        elif question_number <= 20:
            return f"question_{question_number}"
        else:
            return "completion"

    def _handle_wizard_error(self, state: ConversationState, error_message: str) -> ConversationState:
        """Maneja errores del wizard"""
        logger.error(f"Wizard error: {error_message}")

        state["agent_context"] = {
            "response": f"Lo siento, tuve un problema técnico: {error_message}\n\n¿Quieres intentar de nuevo o cancelar el formulario?",
            "error": True
        }
        state["next_action"] = "send_response"
        state["should_continue"] = False

        return {
            "agent_context": state["agent_context"],
            "next_action": state["next_action"],
            "should_continue": state["should_continue"],
            "messages": [AIMessage(content=state["agent_context"]["response"])]
        }

    async def _show_completion_summary(self, state: ConversationState) -> ConversationState:
        """Muestra el resumen de completación"""
        wizard_responses = state.get("wizard_responses", {})
        summary = await self._generate_completion_summary(wizard_responses)

        state["agent_context"] = {
            "response": summary,
            "wizard_completed": True
        }
        state["next_action"] = "send_response"
        state["should_continue"] = False

        return {
            "agent_context": state["agent_context"],
            "next_action": state["next_action"],
            "should_continue": state["should_continue"],
            "messages": [AIMessage(content=summary)]
        }

    async def _handle_human_validation_response(self, state: ConversationState,
                                                user_response: str) -> ConversationState:
        """Maneja la respuesta de validación humana"""
        try:
            pending_validation = state.get("pending_validation", "")
            current_node_id = state.get("current_node")
            current_node = self.nodes[current_node_id]

            # Si el usuario confirma, usar la respuesta original
            if user_response.lower() in ["sí", "si", "yes", "confirmar", "confirm", "ok", "correcto"]:
                validated_result = pending_validation
            else:
                # Si el usuario corrige, validar la nueva entrada
                validated_result = await self.validation.validate_question(user_response, current_node["validation"])
                if validated_result == "HUMAN_VALIDATION_NEEDED":
                    validated_result = user_response  # Usar la entrada del usuario directamente

            # Guardar respuesta validada
            wizard_responses = state.get("wizard_responses", {})
            field_name = current_node.get("question_config", {}).get("field_name", current_node["id"])
            wizard_responses[field_name] = validated_result
            state["wizard_responses"] = wizard_responses

            # Limpiar estado de validación humana
            state["human_validation_needed"] = False
            state["pending_validation"] = None

            # Avanzar al siguiente nodo
            return await self._advance_to_next(state, current_node)

        except Exception as e:
            raise e
            logger.error(f"Error handling human validation: {e}")
            return self._handle_wizard_error(state, str(e))


# Instancia global del agente
wizard_agent = WizardAgent()


# Función para usar en el grafo LangGraph
async def handle_wizard_flow(state: ConversationState) -> ConversationState:
    """Función wrapper para LangGraph"""
    x = await wizard_agent.handle_wizard_flow(state)
    return x
