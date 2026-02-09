from langchain_core.messages import AIMessage

from app.config.questions import WIZARD_QUESTIONS
from app.graph.state import WizardState


def ask_question_node(state: WizardState):
    i = state["current_question"]
    question = WIZARD_QUESTIONS[i]["text"]
    return {
        "messages": [AIMessage(content=question)]
    }


def store_answer_node(state: WizardState):
    user_message = [m.content for m in state["messages"] if m.type == "human"][-1]

    new_index = state["current_question"] + 1
    # Corregir: está completado cuando el nuevo índice es MAYOR a la última pregunta
    is_completed = new_index > max(WIZARD_QUESTIONS.keys())

    return {
        **state,
        "answers": state.get("answers", []) + [user_message],
        "current_question": new_index,
        "completed": is_completed
    }
