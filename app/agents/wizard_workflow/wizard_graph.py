import logging

from langchain_core.messages import AIMessage
from langgraph.graph import END, StateGraph

from app.agents.wizard_workflow.nodes import ask_question_node, store_answer_node
from app.agents.wizard_workflow.messages import WIZARD_COMPLETION_MESSAGE
from app.graph.state import WizardState

logger = logging.getLogger(__name__)


def should_continue_after_store(state: WizardState) -> str:
    """Decide si continuar con el wizard o terminar después de guardar respuesta."""
    if state.get("awaiting_answer", False):
        logger.debug("[WIZARD_GRAPH] should_continue_after_store: awaiting_answer=True -> finish")
        return "finish"

    completed = state.get("completed", False)
    decision = "completion_message" if completed else "ask_question"
    logger.debug(f"[WIZARD_GRAPH] should_continue_after_store: completed={completed} -> {decision}")
    return decision


def should_ask_or_store(state: WizardState) -> str:
    """Decide si hacer pregunta o guardar respuesta basado en si hay respuesta del usuario."""
    # If the wizard hasn't asked a question yet in this turn, never treat an
    # existing human message as an answer; just ask the first question.
    if not state.get("awaiting_answer", False):
        logger.debug("[WIZARD_GRAPH] should_ask_or_store: awaiting_answer=False -> ask_question")
        return "ask_question"

    messages = state.get("messages", [])
    if not messages:
        logger.debug("[WIZARD_GRAPH] should_ask_or_store: no messages -> ask_question")
        return "ask_question"

    last_msg_type = messages[-1].type
    last_msg_content = messages[-1].content[:80] if messages[-1].content else "(empty)"

    if last_msg_type == "ai":
        logger.debug(
            f"[WIZARD_GRAPH] should_ask_or_store: last msg is AI -> ask_question "
            f"(content={last_msg_content!r})"
        )
        return "ask_question"

    if last_msg_type == "human":
        logger.debug(
            f"[WIZARD_GRAPH] should_ask_or_store: last msg is human -> store_answer "
            f"(content={last_msg_content!r})"
        )
        return "store_answer"

    logger.debug(f"[WIZARD_GRAPH] should_ask_or_store: unknown msg type={last_msg_type!r} -> ask_question")
    return "ask_question"


def completion_message_node(state: WizardState):
    """Nodo que genera el mensaje de finalización del wizard."""
    logger.debug("[WIZARD_GRAPH] completion_message_node: generating completion message")

    return {
        **state,
        "messages": [AIMessage(content=WIZARD_COMPLETION_MESSAGE)],
        "wizard_status": "COMPLETED",
    }


builder = StateGraph(WizardState)

# Agregar nodos
builder.add_node("ask_question", ask_question_node)
builder.add_node("store_answer", store_answer_node)
builder.add_node("completion_message", completion_message_node)
builder.add_node("finish", lambda state: {**state, "completed": state.get("completed", False)})

# Punto de entrada condicional
builder.set_entry_point("entry")
builder.add_node("entry", lambda state: state)

# Desde entry, decidir si hacer pregunta o guardar respuesta
builder.add_conditional_edges(
    "entry",
    should_ask_or_store,
    {
        "ask_question": "ask_question",
        "store_answer": "store_answer",
    },
)

# Después de hacer pregunta, terminar (esperar respuesta del usuario)
builder.add_edge("ask_question", "finish")

# Después de guardar respuesta, decidir si continuar o mostrar mensaje final
builder.add_conditional_edges(
    "store_answer",
    should_continue_after_store,
    {
        "ask_question": "ask_question",
        "completion_message": "completion_message",
        "finish": "finish",
    },
)

# Después del mensaje de finalización, terminar
builder.add_edge("completion_message", "finish")

# finish termina el flujo
builder.add_edge("finish", END)

wizard_graph = builder.compile()
