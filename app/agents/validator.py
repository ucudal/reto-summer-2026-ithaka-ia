"""
ValidatorAgent -- verifica datos sensibles antes de persistirlos.

Este agente cubre validaciones de campos basicos (email, telefono y CI)
y ofrece feedback directo en la conversacion para que el usuario corrija
los valores antes de continuar con el flujo.
"""

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml
from langchain_core.messages import AIMessage

from .base import AgentNode
from ..graph.state import ConversationState
from utils.validators import (
    ValidationError,
    validate_ci,
    validate_email,
    validate_phone,
)

logger = logging.getLogger(__name__)

_AGENTS_DIR = Path(__file__).parent
_config = yaml.safe_load((_AGENTS_DIR / "config" / "validator.yaml").read_text())


@dataclass
class DetectionResult:
    field: Optional[str]
    raw_value: Optional[str]


class ValidatorAgent(AgentNode):
    """Valida correos, telefonos y cedulas mencionados en la conversacion."""

    name: str = _config["name"]
    description: str = _config["description"]

    _FIELD_KEYWORDS = {
        "email": ["email", "correo", "mail"],
        "phone": ["telefono", "celular", "cel", "whatsapp"],
        "ci": ["ci", "cedula", "documento", "dni"],
    }
    _FIELD_LABELS = {
        "email": "correo",
        "phone": "telefono",
        "ci": "cedula",
    }

    _EMAIL_TOKEN_PATTERN = re.compile(r"[^\s,;<>]+@[^\s,;<>]+")

    async def __call__(self, state: ConversationState) -> ConversationState:
        """Analiza el ultimo mensaje y valida el dato detectado."""

        messages = state.get("messages", [])
        user_message = [m.content for m in messages if m.type == "human"][-1]
        logger.debug("=" * 60)
        logger.debug("[VALIDATOR] __call__ invoked")
        logger.debug(f"[VALIDATOR] User message: {user_message!r}")

        detection = self._detect_field(user_message)
        logger.debug(f"[VALIDATOR] Detection result: {detection}")

        if not detection.field or not detection.raw_value:
            response = (
                "Puedo ayudarte a validar datos como un correo electronico, "
                "telefono o cedula. Indica el dato y el valor, por ejemplo: "
                "'valida este email: ejemplo@correo.com'."
            )
            return self._build_state_response(
                state,
                response=response,
                context={
                    "field": None,
                    "value": None,
                    "valid": False,
                    "error": "no_field_detected",
                },
            )

        normalized_value = self._normalize_value(detection.field, detection.raw_value)

        logger.debug(f"[VALIDATOR] Normalized value: {normalized_value!r} for field {detection.field}")

        validator_fn = {
            "email": validate_email,
            "phone": validate_phone,
            "ci": validate_ci,
        }.get(detection.field)

        if not validator_fn:
            logger.warning(f"[VALIDATOR] Unsupported field detected: {detection.field}")
            response = (
                "Por ahora solo puedo validar correos electronicos, telefonos y cedulas. "
                "Indicame cual de esos datos queres revisar."
            )
            return self._build_state_response(
                state,
                response=response,
                context={
                    "field": detection.field,
                    "value": normalized_value,
                    "valid": False,
                    "error": "unsupported_field",
                },
            )

        try:
            validator_fn(normalized_value)
            label = self._FIELD_LABELS.get(detection.field, detection.field)
            response = (
                f"Perfecto, el {label} \"{normalized_value}\" es valido. "
                "Podemos continuar con la postulacion."
            )
            return self._build_state_response(
                state,
                response=response,
                context={
                    "field": detection.field,
                    "value": normalized_value,
                    "valid": True,
                    "error": None,
                },
            )
        except ValidationError as exc:
            label = self._FIELD_LABELS.get(detection.field, detection.field)
            response = (
                f"Parece que el {label} \"{normalized_value}\" no es valido: {exc}.\n"
                "Revisalo y enviame el dato corregido antes de guardarlo."
            )
            return self._build_state_response(
                state,
                response=response,
                context={
                    "field": detection.field,
                    "value": normalized_value,
                    "valid": False,
                    "error": str(exc),
                },
            )

    # ------------------------------------------------------------------
    # Detection helpers
    # ------------------------------------------------------------------

    def _detect_field(self, message: str) -> DetectionResult:
        lower_msg = message.lower()

        for field, keywords in self._FIELD_KEYWORDS.items():
            for keyword in keywords:
                if keyword in lower_msg:
                    value = self._extract_value_from_keyword(message, lower_msg, keyword, field)
                    if value:
                        return DetectionResult(field=field, raw_value=value)

        email_candidate = self._extract_email_candidate(message)
        if email_candidate:
            return DetectionResult(field="email", raw_value=email_candidate)

        digit_bundle = re.sub(r"\D", "", message)
        if len(digit_bundle) >= 8:
            if len(digit_bundle) == 8:
                return DetectionResult(field="ci", raw_value=digit_bundle)
            return DetectionResult(field="phone", raw_value=digit_bundle)

        return DetectionResult(field=None, raw_value=None)

    def _extract_value_from_keyword(
        self,
        original_message: str,
        lower_message: str,
        keyword: str,
        field: str,
    ) -> Optional[str]:
        idx = lower_message.find(keyword)
        if idx == -1:
            return None

        snippet = original_message[idx + len(keyword):].lstrip(" :.=,-")

        if field == "email":
            match = self._EMAIL_TOKEN_PATTERN.search(snippet)
            if match:
                return match.group(0).strip()
            return snippet.split()[0].strip(" ,.;") if snippet else None

        if field in {"phone", "ci"}:
            digits = re.sub(r"\D", "", snippet)
            if digits:
                return digits

        return snippet.strip() if snippet else None

    def _extract_email_candidate(self, message: str) -> Optional[str]:
        match = self._EMAIL_TOKEN_PATTERN.search(message)
        if match:
            return match.group(0).strip()
        return None

    def _normalize_value(self, field: str, value: str) -> str:
        if field == "email":
            return value.strip().lower()
        if field in {"phone", "ci"}:
            return re.sub(r"\D", "", value)
        return value.strip()

    # ------------------------------------------------------------------
    # Response helper
    # ------------------------------------------------------------------

    def _build_state_response(
        self,
        state: ConversationState,
        response: str,
        context: dict,
    ) -> ConversationState:
        logger.debug(f"[VALIDATOR] Response: {response}")
        return {
            "agent_context": {
                "response": response,
                "validator": context,
            },
            "messages": [AIMessage(content=response)],
            **{k: v for k, v in state.items() if k not in {"agent_context", "messages"}},
        }


validator_agent = ValidatorAgent()


async def handle_validation(state: ConversationState) -> ConversationState:
    """Wrapper para LangGraph."""
    return await validator_agent(state)
