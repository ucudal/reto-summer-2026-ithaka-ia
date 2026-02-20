import logging

from langchain_core.messages import AIMessage

from app.config.questions import WIZARD_QUESTIONS
from app.graph.state import WizardState

logger = logging.getLogger(__name__)


def ask_question_node(state: WizardState):
    i = state["current_question"]
    question = WIZARD_QUESTIONS[i]["text"]
    logger.debug("-" * 60)
    logger.debug(f"[WIZARD/ask_question] Asking question #{i}")
    logger.debug(f"[WIZARD/ask_question] Question type: {WIZARD_QUESTIONS[i].get('type')}")
    logger.debug(f"[WIZARD/ask_question] Question text: {question[:120]!r}...")
    return {
        "messages": [AIMessage(content=question)],
        "awaiting_answer": True,
    }


def store_answer_node(state: WizardState):
    user_message = [m.content for m in state["messages"] if m.type == "human"][-1]

    new_index = state["current_question"] + 1
    is_completed = new_index > max(WIZARD_QUESTIONS.keys())

    logger.debug("-" * 60)
    logger.debug(f"[WIZARD/store_answer] Storing answer for question #{state['current_question']}")
    logger.debug(f"[WIZARD/store_answer] User answer: {user_message[:200]!r}")
    logger.debug(f"[WIZARD/store_answer] Next question index: {new_index}")
    logger.debug(f"[WIZARD/store_answer] Is completed: {is_completed}")
    logger.debug(f"[WIZARD/store_answer] Total answers so far: {len(state.get('answers', []))}")

    return {
        **state,
        "answers": state.get("answers", []) + [user_message],
        "current_question": new_index,
        "completed": is_completed,
        "awaiting_answer": False,
    }
