from langgraph.graph import StateGraph, END
from langchain_core.messages import AIMessage

from app.agents.wizard_workflow.nodes import ask_question_node, store_answer_node
from app.graph.state import WizardState

def should_continue_after_store(state: WizardState) -> str:
    """Decide si continuar con el wizard o terminar después de guardar respuesta"""
    # Chequear si ya completamos todas las preguntas (el store_answer_node ya calculó esto)
    if state.get("completed", False):
        return "completion_message"
    return "ask_question"

def should_ask_or_store(state: WizardState) -> str:
    """Decide si hacer pregunta o guardar respuesta basado en si hay respuesta del usuario"""
    messages = state.get("messages", [])

    # Si no hay mensajes o el último mensaje es del AI, hacer pregunta
    if not messages or messages[-1].type == "ai":
        return "ask_question"

    # Si el último mensaje es del usuario, guardar respuesta
    if messages[-1].type == "human":
        return "store_answer"

    # Default: hacer pregunta
    return "ask_question"

def completion_message_node(state: WizardState):
    """Nodo que genera el mensaje de finalización del wizard"""
    completion_msg = "¡Muchas gracias por completar el formulario de postulación de Ithaka! 🎉\n\nHemos registrado todas tus respuestas. Nuestro equipo revisará tu postulación y te contactaremos a la brevedad.\n\n¡Esperamos poder acompañarte en tu emprendimiento!"

    return {
        **state,
        "messages": [AIMessage(content=completion_msg)],
        "wizard_status": "COMPLETED"  # Cambiar el status del wizard, no el campo completed
    }

builder = StateGraph(WizardState)

# Agregar nodos
builder.add_node("ask_question", ask_question_node)
builder.add_node("store_answer", store_answer_node)
builder.add_node("completion_message", completion_message_node)  # Nuevo nodo
builder.add_node("finish", lambda state: {**state, "completed": True})

# Punto de entrada condicional
builder.set_entry_point("entry")
builder.add_node("entry", lambda state: state)  # Nodo dummy para decidir flujo inicial

# Desde entry, decidir si hacer pregunta o guardar respuesta
builder.add_conditional_edges(
    "entry",
    should_ask_or_store,
    {
        "ask_question": "ask_question",
        "store_answer": "store_answer"
    }
)

# Después de hacer pregunta, terminar (esperar respuesta del usuario)
builder.add_edge("ask_question", "finish")

# Después de guardar respuesta, decidir si continuar o mostrar mensaje final
builder.add_conditional_edges(
    "store_answer",
    should_continue_after_store,
    {
        "ask_question": "ask_question",
        "completion_message": "completion_message"  # Ir a mensaje final
    }
)

# Después del mensaje de finalización, terminar
builder.add_edge("completion_message", "finish")

# finish termina el flujo
builder.add_edge("finish", END)

wizard_graph = builder.compile()
