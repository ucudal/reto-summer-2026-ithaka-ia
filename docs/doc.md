# 🧠 Ithaka Conversational AI – Backend

**Centro de Emprendimiento e Innovación – Universidad Católica del Uruguay**

---

## Tabla de Contenidos

1. [Introducción](#introducción)
2. [Arquitectura General](#arquitectura-general)
3. [Flujo Conversacional y Agentes](#flujo-conversacional-y-agentes)
4. [Servicios Principales](#servicios-principales)
5. [Modelo de Datos](#modelo-de-datos)
6. [Validaciones](#validaciones)
7. [Notificaciones](#notificaciones)
8. [WebSockets](#websockets)
9. [Persistencia y Manejo de Conversaciones](#persistencia-y-manejo-de-conversaciones)
10. [Testing](#testing)
11. [Extensiones y Roadmap](#extensiones-y-roadmap)
12. [Apéndice: Troubleshooting y Configuración](#apéndice-troubleshooting-y-configuración)

---

## 1. Introducción

Este backend implementa el asistente conversacional para **Ithaka**, ayudando a emprendedores a postularse y a resolver dudas en tiempo real.

### Funcionalidades principales:

- Orienta al usuario con respuestas FAQ (búsqueda semántica).
- Guía y valida postulaciones mediante un wizard de IA.
- Persiste todas las interacciones y postulaciones.
- Notifica automáticamente por email y WhatsApp.
- Extensible a nuevos agentes y canales.

---

## 2. Arquitectura General

```
Usuario
   │
   ▼
[FastAPI + WebSocket]
   │
   ▼
[ChatService] → [LangGraph Workflow]
                      │
          ┌───────────┼────────────┐
          ▼           ▼            ▼
     [Supervisor] [FAQ Agent] [Wizard Agent*]
          │
    [Validadores*]
          │
   [Persistencia (PostgreSQL + ChromaDB)]
          │
   [Notificaciones (Twilio, Email)]
          │
          ▼
 Respuesta usuario
```
\*Agentes marcados con asterisco están planificados o parcialmente integrados.

- **LangGraph**: Core del enrutamiento inteligente entre agentes.
- **OpenAI GPT & Embeddings**: FAQ y contexto conversacional.
- **PostgreSQL**: Mensajes, conversaciones, postulaciones.
- **ChromaDB**: Embeddings para búsqueda semántica en FAQ.
- **Twilio/SMTP**: Notificaciones.

---

## 3. Flujo Conversacional y Agentes

### 🧩 Orquestación con LangGraph

**Archivo clave:** `app/graph/workflow.py`

- Punto de entrada: **Supervisor** (detecta intención y deriva).
- Agentes actuales:
    - **FAQ Agent:** Busca respuestas en base de embeddings y responde.
    - **Wizard Agent:** (Próximamente) Guía al usuario en la postulación, valida respuestas.
    - **Validator:** (Futuro) Validaciones personalizadas.

**Ejemplo de flujo:**
1. Usuario: _"¿Cuáles son los requisitos para postular?"_
    - Supervisor → FAQ Agent → Respuesta → Fin.
2. Usuario: _"Quiero postularme"_
    - Supervisor → Wizard Agent → Preguntas → Validación → Guardado → Notificación → Fin.

**Estado de la conversación:**
- conversation_id, historial, email, nombre
- Estado del wizard, respuestas, pregunta actual
- Resultados de validación, contexto de agentes, etc.

---

## 4. Servicios Principales

### 💬 ChatService (`app/services/chat_service.py`)

#### Funciones principales:
- **process_message:** Orquesta el flujo end-to-end de cada mensaje.
- Busca/construye conversación.
- Recupera historial reciente.
- Llama al workflow de agentes.
- Persiste mensajes y actualiza datos relevantes.
- Responde estructuradamente para el frontend.

#### Ejemplo de ciclo:
```python
# Lado backend
result = await chat_service.process_message(
    user_message="Quiero postularme",
    user_email="juan@example.com"
)
# result['response'] → texto a mostrar
# result['wizard_state'] → INACTIVE / ACTIVE / COMPLETED
```

#### Persistencia:
- Conversaciones y mensajes se guardan **siempre**.
- Si es FAQ anónima, crea conversación temporal.

---

## 5. Modelo de Datos

### Esquema principal (`app/db/models.py`):

- **Conversation:**  
  - id, email, started_at
  - Relaciones: messages, postulations, wizard_sessions

- **Message:**  
  - id, conv_id (FK), role (user/assistant), content, ts

- **Postulation:**  
  - id, conv_id (FK), payload_json (wizard responses), created_at

- **WizardSession:**  
  - id, conv_id (FK), current_question, responses, state

- **FAQEmbedding:**  
  - id, question, answer, embedding (vector), created_at

#### Relaciones:

```
Conversation ──< Message
            └─< Postulation
            └─< WizardSession
FAQEmbedding (independiente; para búsqueda FAQ)
```

---

## 6. Validaciones

### Implementadas en: `app/utils/validators.py`

#### Tipos:
- **Email** (RFC básico)
- **Teléfono** (8-12 dígitos)
- **Cédula uruguaya** (algoritmo nacional)

#### Ejemplo de uso:
```python
from app.utils.validators import validate_email, validate_phone, validate_ci
try:
    validate_email("no@mail.com")
except ValidationError as e:
    # manejar error
```

#### Extensibilidad:
- Se pueden añadir nuevas funciones y usarlas como hooks en el Wizard o en validadores de agentes.

---

## 7. Notificaciones

### Definidas en: `app/utils/notifier.py`

#### Canales:
- **Email:** Confirmación de postulación exitosa.
- **WhatsApp:** (Twilio) Mensajes automáticos.

#### Ejemplo de uso:
```python
send_email_confirmation("mail@host.com", nombre="Lucía")
send_whatsapp_message("+598XXXXXXXX", "¡Tu postulación fue registrada!")
```

#### Eventos disparadores:
- Principal: **al finalizar la postulación** (después del Wizard).
- Extensible: Se puede integrar Slack, SMS, etc.

---

## 8. WebSockets

### Stack en: `app/websockets/`

#### Componentes:
- **manager.py:** Maneja conexiones, envío/broadcast de eventos.
- **handlers.py:** (Definición y lógica de eventos)
- **schemas.py, enums.py:** Definición de mensajes/eventos tipados.

#### Uso típico:
- Permite push de respuestas en tiempo real.
- Recomendado para frontend reactivo y/o multiusuario.

---

## 9. Persistencia y Manejo de Conversaciones

- **Mensajes:** Se persisten siempre, rol (`user`, `assistant`) y timestamp.
- **Conversaciones temporales:** Para usuarios sin email (ej: FAQ anónima).
- **Postulaciones:** Guardado estructurado en JSON tras completar el Wizard.
- **Embeddings:** Se guardan para acelerar búsqueda FAQ semántica.
- **Historial:** El ChatService expone métodos para recuperar historial reciente.

---

## 10. Testing

### Test automatizados:
- **test_final_verification.py**
- **test_frontend_simulation.py**
- **test_integration.py**
- **test_timeout_issue.py**

#### Recomendaciones:
- Correr con entorno aislado (DB test).
- Cubren integración completa del flujo de conversación, validaciones y persistencia.

---

## 11. Extensiones y Roadmap

- **Wizard Agent completo:** Soporte para todo el flujo de postulación.
- **Validator Agent:** Validaciones más avanzadas y/o personalizadas.
- **Scoring de postulaciones:** Implementación de fit-score automático.
- **Nuevos canales:** Slack, SMS, panel administrativo, API pública.

---

## 12. Apéndice: Troubleshooting y Configuración

### Variables de entorno (principales):
- `EMAIL_USER`, `EMAIL_PASS`, `EMAIL_HOST`, `EMAIL_PORT`
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_NUMBER`
- (Agregar los de conexión a DB, OpenAI, ChromaDB según tu entorno)

### Logs:
- Se loguean eventos críticos y errores en cada servicio.
- Para debugging, revisar logs de FastAPI y servicios de background.

---
