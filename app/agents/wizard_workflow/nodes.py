import logging

from langchain_core.messages import AIMessage

from app.config.questions import WIZARD_QUESTIONS
from app.graph.state import WizardState
from app.utils.validators import ValidationError, validate_ci, validate_email, validate_phone

logger = logging.getLogger(__name__)


def _normalize_answer(value):
    if isinstance(value, str):
        return value.strip().lower()
    return value


def _is_question_applicable(question_cfg: dict, wizard_responses: dict) -> bool:
    """Return True when a question should be shown based on conditional metadata."""
    if not question_cfg.get("conditional", False):
        return True

    condition_field = question_cfg.get("condition_field")
    condition_values = question_cfg.get("condition_values", [])
    if not condition_field:
        return True

    current_value = wizard_responses.get(condition_field)
    normalized_current = _normalize_answer(current_value)
    normalized_allowed = {_normalize_answer(v) for v in condition_values}
    return normalized_current in normalized_allowed


def _get_next_question_index(current_q: int, wizard_responses: dict):
    """Return next applicable question index after current_q, or None if finished."""
    for q_idx in sorted(k for k in WIZARD_QUESTIONS.keys() if k > current_q):
        q_cfg = WIZARD_QUESTIONS.get(q_idx, {})
        if _is_question_applicable(q_cfg, wizard_responses):
            return q_idx
    return None


def _normalize_option_answer(answer: str, options: list[str]):
    """Return canonical option from options if answer matches (case-insensitive)."""
    normalized = _normalize_answer(answer)
    for option in options:
        if normalized == _normalize_answer(option):
            return option
    return answer


def _validate_wizard_answer(question_cfg: dict, answer: str):
    validation = question_cfg.get("validation")
    required = bool(question_cfg.get("required", False))
    cleaned = (answer or "").strip()

    if not cleaned:
        if required:
            raise ValidationError("Este campo es obligatorio.")
        return cleaned

    if validation == "email":
        validate_email(cleaned)
        return cleaned.lower()
    if validation == "phone":
        validate_phone(cleaned)
        return cleaned
    if validation == "ci":
        validate_ci(cleaned)
        return cleaned
    if validation == "yes_no":
        options = question_cfg.get("options", ["NO", "SI"])
        canonical = _normalize_option_answer(cleaned, options)
        if _normalize_answer(canonical) not in {_normalize_answer(o) for o in options}:
            raise ValidationError(f"Respuesta inválida. Opciones válidas: {', '.join(options)}.")
        return canonical
    if validation in {"campus", "ucu_relation", "faculty", "discovery_method", "project_stage", "support_needed"}:
        options = question_cfg.get("options", [])
        if options:
            canonical = _normalize_option_answer(cleaned, options)
            if _normalize_answer(canonical) not in {_normalize_answer(o) for o in options}:
                raise ValidationError(f"Respuesta inválida. Opciones válidas: {', '.join(options)}.")
            return canonical
        return cleaned
    if validation == "text_min_length":
        min_length = int(question_cfg.get("min_length", 1))
        if len(cleaned) < min_length:
            raise ValidationError(f"La respuesta debe tener al menos {min_length} caracteres.")
        return cleaned
    if validation == "name":
        if len(cleaned) < 3:
            raise ValidationError("Ingresa nombre y apellido.")
        return cleaned
    if validation == "location":
        if len(cleaned) < 3:
            raise ValidationError("Ingresa país y localidad.")
        return cleaned
    if validation in {"optional_text", "rubrica"}:
        return cleaned

    return cleaned


def _get_current_or_next_applicable_question(current_q: int, wizard_responses: dict):
    q_cfg = WIZARD_QUESTIONS.get(current_q, {})
    if q_cfg and _is_question_applicable(q_cfg, wizard_responses):
        return current_q
    return _get_next_question_index(current_q - 1, wizard_responses)


def ask_question_node(state: WizardState):
    wizard_responses = dict(state.get("wizard_responses", {}))
    current_q = state["current_question"]
    i = _get_current_or_next_applicable_question(current_q, wizard_responses)
    if i is None:
        completion_message = (
            "Muchas gracias por completar el formulario de postulación de Ithaka!\n\n"
            "Hemos registrado todas tus respuestas. Nuestro equipo revisará tu postulación "
            "y te contactará a la brevedad.\n\n"
            "Esperamos poder acompañarte en tu emprendimiento!"
        )
        return {
            **state,
            "messages": [AIMessage(content=completion_message)],
            "completed": True,
            "awaiting_answer": False,
            "wizard_status": "COMPLETED",
        }

    question = WIZARD_QUESTIONS[i]["text"]
    logger.debug("-" * 60)
    logger.debug(f"[WIZARD/ask_question] Asking question #{i}")
    logger.debug(f"[WIZARD/ask_question] Question type: {WIZARD_QUESTIONS[i].get('type')}")
    logger.debug(f"[WIZARD/ask_question] Question text: {question[:120]!r}...")
    return {
        **state,
        "messages": [AIMessage(content=question)],
        "current_question": i,
        "awaiting_answer": True,
    }


def store_answer_node(state: WizardState):
    user_message = [m.content for m in state["messages"] if m.type == "human"][-1]

    current_q = state["current_question"]
    q_config = WIZARD_QUESTIONS.get(current_q, {})
    field_name = q_config.get("field_name", str(current_q))
    normalized_answer = user_message

    try:
        normalized_answer = _validate_wizard_answer(q_config, user_message)
    except ValidationError as exc:
        logger.debug(f"[WIZARD/store_answer] Validation failed for question #{current_q}: {exc}")
        return {
            **state,
            "messages": [AIMessage(content=f"El dato no es válido: {exc}\n\nIntenta nuevamente.")],
            "awaiting_answer": True,
            "completed": False,
        }

    wizard_responses = dict(state.get("wizard_responses", {}))
    wizard_responses[field_name] = normalized_answer
    next_q = _get_next_question_index(current_q, wizard_responses)
    is_completed = next_q is None
    new_index = next_q if next_q is not None else current_q

    logger.debug("-" * 60)
    logger.debug(f"[WIZARD/store_answer] Storing answer for question #{current_q} (field={field_name!r})")
    logger.debug(f"[WIZARD/store_answer] User answer: {normalized_answer[:200]!r}")
    logger.debug(f"[WIZARD/store_answer] Next applicable question index: {new_index}")
    logger.debug(f"[WIZARD/store_answer] Is completed: {is_completed}")
    logger.debug(f"[WIZARD/store_answer] Total answers so far: {len(state.get('answers', []))}")

    return {
        **state,
        "answers": state.get("answers", []) + [normalized_answer],
        "wizard_responses": wizard_responses,
        "current_question": new_index,
        "completed": is_completed,
        "awaiting_answer": False,
    }
