from typing import Optional, Annotated, List, Any, Dict

from langgraph.graph import add_messages
from typing_extensions import TypedDict


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
    # Documento subido por el usuario: texto extraído y nombre del archivo.
    # Persiste en el estado para toda la conversación y se reemplaza
    # cuando el usuario sube un nuevo documento.
    document_context: Optional[str]
    document_filename: Optional[str]
