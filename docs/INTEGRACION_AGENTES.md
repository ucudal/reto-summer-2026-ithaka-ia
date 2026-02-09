# 🔧 Guía de Integración de Agentes

Esta guía explica cómo integrar los agentes de **Wizard** y **Validator** al sistema existente.

## 📋 Estado Actual

### ✅ Agentes Funcionales

- **Supervisor** - Router inteligente
- **FAQ** - Búsqueda vectorial de preguntas frecuentes

### 🚧 Agentes Pendientes de Integración

- **Wizard** - Formulario conversacional
- **Validator** - Validación de datos

## 🔄 Cómo Integrar el Validator Agent

### 1. Descomentar en `app/graph/workflow.py`

```python
# Cambiar de:
# from ..agents.validator import validate_data

# A:
from ..agents.validator import validate_data
```

```python
# Cambiar de:
# workflow.add_node("validator", validate_data)

# A:
workflow.add_node("validator", validate_data)
```

```python
# Cambiar de:
# "validator": "validator",

# A:
"validator": "validator",
```

```python
# Cambiar de:
# workflow.add_edge("validator", END)

# A:
workflow.add_edge("validator", END)
```

### 2. Actualizar `app/agents/supervisor.py`

```python
# Cambiar de:
# TODO: "validator" - SOLO para validar datos específicos cuando esté disponible

# A:
- "validator" - SOLO para validar datos específicos (email, teléfono, etc.)
```

```python
# Cambiar de:
# TODO: "valida este email: test@test.com" → validator (cuando esté disponible)

# A:
- "valida este email: test@test.com" → validator
```

```python
# Cambiar de:
Responde ÚNICAMENTE con una palabra: faq

# A:
Responde ÚNICAMENTE con una palabra: faq, validator
```

```python
# Cambiar de:
if intention in ["faq"]:  # TODO: Agregar "validator" y "wizard" cuando estén disponibles

# A:
if intention in ["faq", "validator"]:  # TODO: Agregar "wizard" cuando esté disponible
```

```python
# Cambiar de:
if supervisor_decision in ["faq"]:  # TODO: Agregar "validator" y "wizard" cuando estén disponibles

# A:
if supervisor_decision in ["faq", "validator"]:  # TODO: Agregar "wizard" cuando esté disponible
```

### 3. Verificar que `app/agents/validator.py` esté presente

El archivo ya existe y contiene:

- Validación de emails (RFC 5322)
- Validación de teléfonos (8-12 dígitos)
- Validación de cédulas uruguayas
- Validación de opciones predefinidas
- Validación de longitud mínima de texto

## 🧙‍♂️ Cómo Integrar el Wizard Agent

### 1. Descomentar en `app/graph/workflow.py`

```python
# Cambiar de:
# from ..agents.wizard import handle_wizard_flow

# A:
from ..agents.wizard import handle_wizard_flow
```

```python
# Cambiar de:
# workflow.add_node("wizard", handle_wizard_flow)

# A:
workflow.add_node("wizard", handle_wizard_flow)
```

```python
# Cambiar de:
# "wizard": "wizard",

# A:
"wizard": "wizard",
```

```python
# Cambiar de:
# workflow.add_edge("wizard", END)

# A:
workflow.add_edge("wizard", END)
```

### 2. Actualizar `app/agents/supervisor.py`

```python
# Descomentar las funciones del wizard:
# TODO: Verificar sesiones activas del wizard cuando esté disponible
# if state.get("wizard_session_id") and state.get("wizard_state") == "ACTIVE":
#     logger.info("Routing to wizard - active session detected in state")
#     return self._route_to_wizard(state)

# TODO: Verificar sesiones en BD cuando wizard esté disponible
# if conversation_id:
#     active_wizard_session = await self._check_active_wizard_session(conversation_id)
#     if active_wizard_session:
#         logger.info(f"Routing to wizard - active session {active_wizard_session['id']} found in DB")
#         state["wizard_session_id"] = active_wizard_session["id"]
#         state["wizard_state"] = active_wizard_session["state"]
#         state["current_question"] = active_wizard_session["current_question"]
#         state["wizard_responses"] = active_wizard_session["responses"]
#         return self._route_to_wizard(state)
```

```python
# Descomentar patrones del wizard:
# TODO: Patrones para wizard cuando esté disponible
# wizard_keywords = [
#     "postular", "emprender", "formulario", "idea", "negocio",
#     "startup", "proyecto", "emprendimiento", "incubadora",
#     "quiero postular", "tengo una idea"
# ]

# TODO: Comandos del wizard cuando esté disponible
# wizard_commands = ["volver", "cancelar", "continuar", "siguiente"]

# TODO: Verificar comandos del wizard cuando esté disponible
# if any(cmd in message for cmd in wizard_commands):
#     return "wizard"

# TODO: Verificar patrones de postulación cuando wizard esté disponible
# if any(keyword in message for keyword in wizard_keywords):
#     return "wizard"
```

```python
# Descomentar funciones del wizard:
# TODO: Implementar cuando wizard esté disponible
# def _route_to_wizard(self, state: ConversationState) -> ConversationState:
#     """Rutea específicamente al wizard"""
#     state["supervisor_decision"] = "wizard"
#     state["current_agent"] = "wizard"
#     return state

# TODO: Implementar cuando wizard esté disponible
# async def _check_active_wizard_session(self, conversation_id: int) -> Optional[Dict[str, Any]]:
#     """Verifica si hay una sesión activa del wizard en la base de datos"""
#     # ... implementación completa
```

### 3. Verificar archivos necesarios

Asegúrate de que existan:

- `app/agents/wizard.py` - Agente del wizard
- `app/config/questions.py` - Configuración de preguntas
- `app/config/rubrica.json` - Rúbrica de evaluación
- `app/services/evaluation_service.py` - Servicio de evaluación

### 4. Configurar base de datos

La tabla `wizard_sessions` ya está definida en `app/db/models.py` y se creará automáticamente con:

```bash
python -m app.db.config.create_tables
```

## 🧪 Testing de Integración

### Test del Validator

```python
import asyncio
from app.services.chat_service import chat_service

async def test_validator():
    result = await chat_service.process_message(
        user_message="valida este email: test@example.com",
        user_email=None,
        conversation_id=None
    )
    print(f"Agent usado: {result.get('agent_used')}")
    print(f"Respuesta: {result.get('response')}")

asyncio.run(test_validator())
```

### Test del Wizard

```python
import asyncio
from app.services.chat_service import chat_service

async def test_wizard():
    try:
        # TODO: Uncomment when wizard agent is implemented
        # from app.agents.wizard import wizard_agent

        result = await chat_service.process_message(
            user_message="Quiero postular mi idea",
            user_email=None,
            conversation_id=None
        )
        print(f"Agent usado: {result.get('agent_used')}")
        print(f"Respuesta: {result.get('response')}")
    except ImportError as e:
        print(f"Wizard agent not yet implemented: {e}")

asyncio.run(test_wizard())
```

## 🚨 Consideraciones Importantes

### Para el Validator

- ✅ Ya está implementado y funcional
- ✅ Integra con `utils/validators.py`
- ✅ Solo necesita descomentarse

### Para el Wizard

- ⚠️ Requiere implementación completa
- ⚠️ Necesita configuración de preguntas
- ⚠️ Requiere rúbrica de evaluación
- ⚠️ Necesita servicio de evaluación IA

### Orden de Integración Recomendado

1. **Primero Validator** - Más simple, ya está listo
2. **Luego Wizard** - Más complejo, requiere más trabajo

## 📝 Checklist de Integración

### Validator

- [ ] Descomentar imports en workflow.py
- [ ] Descomentar nodo en workflow.py
- [ ] Descomentar edges en workflow.py
- [ ] Actualizar supervisor.py
- [ ] Test de integración

### Wizard

- [ ] Implementar wizard.py completo
- [ ] Crear questions.py
- [ ] Crear rubrica.json
- [ ] Implementar evaluation_service.py
- [ ] Descomentar todo en workflow.py
- [ ] Descomentar todo en supervisor.py
- [ ] Test de integración completa

## 🔍 Debugging

### Logs Útiles

```python
import logging
logging.basicConfig(level=logging.INFO)

# Ver decisiones del supervisor
# Ver routing entre agentes
# Ver errores de validación
# Ver progreso del wizard
```

### Verificar Estado

```python
# Verificar que el agente se carga correctamente
from app.agents.validator import validator_agent
from app.agents.wizard import wizard_agent

# Verificar que el workflow funciona
from app.graph.workflow import process_user_message
```

---

**¿Necesitas ayuda?** Revisa los logs y verifica que todos los archivos estén presentes antes de descomentar las integraciones.
