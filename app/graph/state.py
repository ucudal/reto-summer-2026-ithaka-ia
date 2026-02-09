from typing import Optional, Annotated, List, Any, Dict

from langgraph.graph import add_messages
from typing_extensions import TypedDict


class WizardQuestionState(TypedDict):
    """Estado específico para una pregunta del wizard"""
    question_number: int
    question_text: str
    question_type: str  # "personal", "evaluativa", "opcional"
    user_response: Optional[str]
    is_valid: bool
    validation_errors: list[str]
    evaluation_feedback: Optional[str]
    needs_improvement: bool
    iteration_count: int


class WizardState(TypedDict):
    wizard_session_id: Optional[str]
    current_question: int
    answers: List[Any]  # Agregar este campo que falta
    wizard_responses: Dict[str, Any]
    wizard_status: str  # "INACTIVE", "ACTIVE", "COMPLETED"
    awaiting_answer: bool
    messages: Annotated[list, add_messages]
    completed: bool
    valid: bool  # Para las funciones condicionales del wizard graph


class ConversationState(TypedDict):
    messages: Annotated[list, add_messages]
    # Solo campos básicos del workflow
    conversation_id: Optional[int]
    user_email: Optional[str]
    current_agent: str
    agent_context: Dict[str, Any]
    # Referencia al wizard state, no los campos del wizard
    wizard_state: Optional[WizardState]
