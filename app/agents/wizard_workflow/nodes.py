import hashlib
import logging
import os

from langchain_core.messages import AIMessage

from app.config.questions import WIZARD_QUESTIONS
from app.graph.state import WizardState
from app.utils.validators import ValidationError, validate_ci, validate_email, validate_phone
from app.agents.wizard_workflow.messages import WIZARD_COMPLETION_MESSAGE

try:
    from guardrails import Guard
    from guardrails.hub import DetectJailbreak
except ImportError:  # pragma: no cover - optional dependency during local dev
    Guard = None
    DetectJailbreak = None

logger = logging.getLogger(__name__)

MAX_ANSWER_LENGTH = 2000
GUARDRAIL_BLOCK_PATTERNS = (
    "ignore previous instructions",
    "ignore all previous instructions",
    "ignora las instrucciones anteriores",
    "ignora todas las instrucciones anteriores",
    "follow system instructions",
    "sigue las instrucciones del sistema",
    "reveal system prompt",
    "show system prompt",
    "developer message",
    "prompt injection",
    "jailbreak",
    "<system>",
)

_DEFAULT_JAILBREAK_THRESHOLD = 0.9


def _env_flag(value: str | None, *, default: bool = True) -> bool:
    if value is None:
        return default
    return value.strip().lower() not in {"", "0", "false", "no", "off"}


_DETECT_JAILBREAK_ENABLED = _env_flag(os.getenv("WIZARD_DETECT_JAILBREAK_ENABLED"), default=True)


def _load_detect_jailbreak_guard():
    if not _DETECT_JAILBREAK_ENABLED:
        logger.info("[WIZARD/guardrails] DetectJailbreak disabled via env flag.")
        return None
    if Guard is None or DetectJailbreak is None:
        logger.warning(
            "[WIZARD/guardrails] guardrails-ai is not installed. "
            "Install guardrails-ai>=0.5.10 and the DetectJailbreak hub package."
        )
        return None

    raw_threshold = os.getenv("WIZARD_DETECT_JAILBREAK_THRESHOLD")
    try:
        threshold = float(raw_threshold) if raw_threshold is not None else _DEFAULT_JAILBREAK_THRESHOLD
    except ValueError:
        threshold = _DEFAULT_JAILBREAK_THRESHOLD
        logger.warning(
            "[WIZARD/guardrails] Invalid threshold %r. Falling back to %.2f.",
            raw_threshold,
            _DEFAULT_JAILBREAK_THRESHOLD,
        )

    try:
        return Guard().use(DetectJailbreak, threshold=threshold)
    except Exception:
        logger.exception(
            "[WIZARD/guardrails] Could not initialize DetectJailbreak. "
            "Run `guardrails hub install hub://guardrails/detect_jailbreak` and retry."
        )
        return None


_DETECT_JAILBREAK_GUARD = _load_detect_jailbreak_guard()


def _is_detected_as_jailbreak(message: str) -> bool:
    guard = _DETECT_JAILBREAK_GUARD
    if guard is None:
        return False

    try:
        result = guard.validate(message)
    except Exception:
        logger.exception("[WIZARD/guardrails] DetectJailbreak validation failed. Allowing message as fallback.")
        return False

    return not bool(getattr(result, "validation_passed", True))


def _blocked_guardrail_response(state: WizardState, current_q: int, cleaned: str, reason: str):
    msg_preview = cleaned[:64]
    msg_hash = hashlib.sha256(cleaned.encode("utf-8")).hexdigest()[:12]
    logger.warning(
        "[WIZARD/guardrails] %s session_id=%s current_question=%s msg_preview=%r msg_hash=%s",
        reason,
        state.get("wizard_session_id"),
        current_q,
        msg_preview,
        msg_hash,
    )
    return {
        **state,
        "messages": [
            AIMessage(
                content="Tu mensaje parece una instruccion para alterar el asistente. Responde solo con el dato solicitado."
            )
        ],
        "awaiting_answer": True,
        "completed": False,
        "wizard_status": "ACTIVE",
        "valid": False,
    }


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
            raise ValidationError(f"Respuesta invalida. Opciones validas: {', '.join(options)}.")
        return canonical
    if validation in {"campus", "ucu_relation", "faculty", "discovery_method", "project_stage", "support_needed"}:
        options = question_cfg.get("options", [])
        if options:
            canonical = _normalize_option_answer(cleaned, options)
            if _normalize_answer(canonical) not in {_normalize_answer(o) for o in options}:
                raise ValidationError(f"Respuesta invalida. Opciones validas: {', '.join(options)}.")
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


def _extract_last_human_message(state: WizardState):
    messages = state.get("messages", [])
    for message in reversed(messages):
        if getattr(message, "type", None) == "human":
            return message.content
    return None


def input_guardrails_node(state: WizardState):
    current_q = state.get("current_question")
    if current_q not in WIZARD_QUESTIONS:
        first_question = min(WIZARD_QUESTIONS.keys())
        return {
            **state,
            "messages": [AIMessage(content="Perdimos el estado del formulario. Reiniciamos desde el inicio.")],
            "current_question": first_question,
            "awaiting_answer": False,
            "completed": False,
            "wizard_status": "ACTIVE",
            "valid": False,
        }

    user_message = _extract_last_human_message(state)
    if user_message is None:
        return {
            **state,
            "messages": [AIMessage(content="No pude leer tu respuesta. Intenta enviarla nuevamente.")],
            "awaiting_answer": True,
            "completed": False,
            "wizard_status": "ACTIVE",
            "valid": False,
        }

    cleaned = user_message.strip()
    if not cleaned:
        return {
            **state,
            "messages": [AIMessage(content="Tu respuesta esta vacia. Por favor escribe una respuesta e intenta nuevamente.")],
            "awaiting_answer": True,
            "completed": False,
            "wizard_status": "ACTIVE",
            "valid": False,
        }

    if len(cleaned) > MAX_ANSWER_LENGTH:
        return {
            **state,
            "messages": [
                AIMessage(
                    content=f"La respuesta es demasiado larga (maximo {MAX_ANSWER_LENGTH} caracteres). Resumela e intenta nuevamente."
                )
            ],
            "awaiting_answer": True,
            "completed": False,
            "wizard_status": "ACTIVE",
            "valid": False,
        }

    lowered = cleaned.lower()
    if any(pattern in lowered for pattern in GUARDRAIL_BLOCK_PATTERNS):
        return _blocked_guardrail_response(
            state, current_q, cleaned, "Possible prompt-injection-like answer blocked."
        )

    if _is_detected_as_jailbreak(cleaned):
        return _blocked_guardrail_response(
            state,
            current_q,
            cleaned,
            "DetectJailbreak flagged potential jailbreak attempt.",
        )

    return {
        **state,
        "valid": True,
    }


def ask_question_node(state: WizardState):
    wizard_responses = dict(state.get("wizard_responses", {}))
    current_q = state["current_question"]
    i = _get_current_or_next_applicable_question(current_q, wizard_responses)
    if i is None:
        return {
            **state,
            "messages": [AIMessage(content=WIZARD_COMPLETION_MESSAGE)],
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
    user_message = _extract_last_human_message(state)
    if user_message is None:
        return {
            **state,
            "messages": [AIMessage(content="No pude leer tu respuesta. Intenta nuevamente.")],
            "awaiting_answer": True,
            "completed": False,
            "wizard_status": "ACTIVE",
            "valid": False,
        }

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
            "messages": [AIMessage(content=f"El dato no es valido: {exc}\n\nIntenta nuevamente.")],
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
