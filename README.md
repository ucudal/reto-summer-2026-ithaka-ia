# reto-winter-2025-ithaka-backend

##  Opciones de Ejecución

Puedes ejecutar esta aplicación de **dos formas**:

### 1.  **Docker (Recomendado para producción)**
```bash
# Opción A: Usar imagen del registry
docker pull crretoxmas2024.azurecr.io/ithaka-backend:latest
docker run -p 8000:8000 crretoxmas2024.azurecr.io/ithaka-backend:latest

# Opción B: Construir localmente
docker build -t ithaka-backend .
docker run -p 8000:8000 ithaka-backend

# Opción C: Docker Compose (desarrollo)
docker-compose up
```

### 2.  **Desarrollo Local (Python)**

## Requisitos

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) (gestor de paquetes compatible con pip)
- PostgreSQL con extensión PGVector

## Instalación

### 1. Crear entorno virtual

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Instalar `uv`
Si no lo tenés instalado, escribí en la terminal:

```bash
pip install uv
```

### 3. Instalar dependencias
```bash
uv pip install -r requirements.txt
```

### 4. Configurar variables de entorno

Copia `config/env.example` a `.env` y configura las variables necesarias:

```bash
# Base de Datos
DATABASE_URL=postgresql+asyncpg://user:password@host:port/database

# OpenAI (requerido para agentes IA)
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Configuración de agentes
EMBEDDING_DIMENSION=1536
MAX_FAQ_RESULTS=5
WIZARD_SESSION_TIMEOUT=3600

# Email y Twilio (existentes)
EMAIL_USER=your-email@gmail.com
EMAIL_PASS=your-app-password
TWILIO_ACCOUNT_SID=your-sid
TWILIO_AUTH_TOKEN=your-token
```

### 5. Configurar base de datos

#### Crear usuario y base de datos (si no existen):

```sql
CREATE USER <USUARIO> WITH PASSWORD '<PASSWORD>';
CREATE DATABASE <NOMBRE_DB> OWNER <USUARIO>;
GRANT ALL PRIVILEGES ON DATABASE <NOMBRE_DB> TO <USUARIO>;
```

#### Habilitar extensión PGVector:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

#### Crear tablas:

```bash
python -m app.db.config.create_tables
```

### 6. Poblar FAQs (opcional)

```bash
python scripts/populate_faqs.py
```

### 7. Ejecución
Para ejecutarlo ir a la raíz del proyecto y ejecutar:

```bash
uvicorn app.main:app --reload
```

### Documentación
Podes revisar la doc en http://127.0.0.1:8000/docs

## 🤖 Sistema de Agentes IA

### Agentes Disponibles

1. **🎯 Supervisor** - Router inteligente que analiza intenciones del usuario
2. **❓ FAQ** - Responde consultas usando búsqueda vectorial (PGVector)
3. **✅ Validator** - Detecta correos, teléfonos y cédulas dentro de la conversación, valida su formato y guía al usuario para corregirlos antes de guardarlos.
4. **📝 Wizard** - Formulario conversacional (próximamente)

### Uso del Sistema

#### WebSocket Endpoint
**URL:** `ws://localhost:8000/api/v1/ws/`

#### Ejemplos de Mensajes

**FAQ (Preguntas Frecuentes):**
```json
{"content": "¿Qué es el programa Fellows?"}
{"content": "¿Cuánto cuestan los cursos?"}
{"content": "¿Cómo me entero de las convocatorias?"}
```

**API REST:**
```bash
curl -X POST "http://localhost:8000/api/v1/chat" \
     -H "Content-Type: application/json" \
     -d '{"message": "¿Qué es el programa Fellows?"}'
```
**Respuesta típica:**
```json
{
  "response": "Aquí va la respuesta generada por el agente.",
  "agent_used": "faq",
  "wizard_session_id": null,
  "wizard_state": "INACTIVE",
  "current_question": 1,
  "wizard_responses": {},
  "awaiting_answer": false
}
```

**Validator (Validación de datos):**
```json
{"message": "Podés validar este email: persona@example.com?"}
{"message": "Mi teléfono es +598 9876 5432, confirmá si está correcto."}
{"message": "La cédula 48903345 es válida?"}
```

### Tecnologías Utilizadas

- **LangGraph** - Orquestación de agentes
- **LangChain** - Framework de IA
- **OpenAI** - LLM y embeddings
- **PGVector** - Búsqueda semántica de FAQs
- **PostgreSQL** - Persistencia

### Validación en Tiempo Real

- El Supervisor detecta cuando una intención incluye revisar o enviar datos personales (correo, teléfono, cédula) y enrutará el mensaje al agente **validator** automáticamente.
- El Validator normaliza el dato, ejecuta las reglas de `utils/validators.py` y responde en la misma conversación indicando si es válido.
- Ante errores, devuelve el motivo exacto y pide el dato corregido antes de permitir que continúe el flujo (ideal para evitar guardar información inconsistente).

## 🗄️ Base de Datos

### Tablas Existentes

- `conversations` - Conversaciones
- `messages` - Historial de mensajes
- `postulations` - Postulaciones completadas

### Nuevas Tablas

```sql
-- FAQs con embeddings vectoriales
CREATE TABLE faq_embeddings (
    id SERIAL PRIMARY KEY,
    question VARCHAR NOT NULL,
    answer TEXT NOT NULL,
    embedding VECTOR(1536),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Sesiones del wizard (próximamente)
CREATE TABLE wizard_sessions (
    id SERIAL PRIMARY KEY,
    conv_id INTEGER REFERENCES conversations(id),
    current_question INTEGER DEFAULT 1,
    responses JSON DEFAULT '{}',
    state VARCHAR(50) DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

## 🔧 Debugging y Logs

### Activar Logs Detallados

```python
import logging
logging.basicConfig(level=logging.INFO)
```

### Test de Componentes

```python
# Test FAQ
from app.services.chat_service import chat_service

result = await chat_service.process_message("¿Qué es el programa Fellows?")
print(result)
```

## 🚨 Troubleshooting

### Error: "No module named 'langchain'"
```bash
uv pip install -r requirements.txt
```

### Error: "Extension vector does not exist"
```sql
CREATE EXTENSION vector;
```

### Error: "OpenAI API key not found"
```bash
export OPENAI_API_KEY="sk-your-key-here"
```

### Error: "Database connection failed"
Verificar `DATABASE_URL` en `.env`

## 📈 Próximas Integraciones

### Wizard Agent
- Formulario conversacional de 20 preguntas
- Human-in-the-loop para mejoras
- Evaluación IA con rúbrica
- Persistencia de sesiones

### Cómo Integrar Nuevos Agentes

1. **Crear el agente** en `app/agents/`
2. **Agregar al workflow** en `app/graph/workflow.py`
3. **Actualizar supervisor** en `app/agents/supervisor.py`
4. **Agregar tests** y documentación

---

# Instrucciones para usar la base de datos y el ORM

## 1. Instalar dependencias

Asegúrate de tener las dependencias necesarias:

```
uv pip install -r requirements.txt
```

## 2. Configurar variables de entorno

Crea un archivo `.env` en la raíz del proyecto con el siguiente contenido (ajusta los valores según tu entorno):

```
DATABASE_URL=postgresql+asyncpg://<USUARIO>:<PASSWORD>@<HOST>:<PUERTO>/<NOMBRE_DB>
```

## 3. Crear la base de datos y usuario en PostgreSQL

Solo ejecuta este bloque si el usuario y la base de datos NO existen:

```
CREATE USER <USUARIO> WITH PASSWORD '<PASSWORD>';
CREATE DATABASE <NOMBRE_DB> OWNER <USUARIO>;
GRANT ALL PRIVILEGES ON DATABASE <NOMBRE_DB> TO <USUARIO>;
```

> **Nota:**
> Si el usuario o la base de datos ya existen, puedes omitir estos comandos y solo asegurarte de que el usuario tiene permisos sobre la base de datos.

## 4. Crear las tablas en la base de datos

Ejecuta el siguiente comando desde la raíz del proyecto:

```
python -m app.db.config.create_tables
```

Esto creará las tablas `conversations`, `messages`, `postulations`, `faq_embeddings` y `wizard_sessions`.

## 5. Correr la API

Inicia el servidor de desarrollo:

```
uvicorn app.main:app --reload
```

# Cómo usar ruff

- Analizar el código:
  ```bash
  ruff check .
  ```

## CI/CD y Docker

### Pipeline Automático
- **Trigger:** Push a ramas `DevOps` o `main`
- **Registry:** `crretoxmas2024.azurecr.io/ithaka-backend`
- **Tags:** Automático por rama y commit SHA

### Usar imagen de producción
```bash
# Pull de la imagen del registry
docker pull crretoxmas2024.azurecr.io/ithaka-backend:latest

# Ejecutar contenedor
docker run -p 8000:8000 -e DATABASE_URL=sqlite+aiosqlite:///./app.db crretoxmas2024.azurecr.io/ithaka-backend:latest
```

### Variables de entorno para Docker
```env
DATABASE_URL=sqlite+aiosqlite:///./app.db  # Para desarrollo con SQLite
# O para PostgreSQL:
# DATABASE_URL=postgresql+asyncpg://user:password@host:5432/database
```

---

# Funcionamiento de notificación por WhatsApp
- Ingresar a https://console.twilio.com/us1/develop/sms/try-it-out/whatsapp-learn?frameUrl=%2Fconsole%2Fsms%2Fwhatsapp%2Flearn%3Fx-target-region%3Dus1
- Enviar mensaje al número de WhatsApp +14155238886 con el mensaje `join may-steady`
- Obtener las credenciales y token de Twilio
- Agregar un archivo .env con las credenciales de Twilio

# CI/CD Pipeline Test - Wed Jul 30 11:49:28 -03 2025
