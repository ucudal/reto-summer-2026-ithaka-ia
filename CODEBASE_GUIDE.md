# 📚 Ithaka Backend - Complete Codebase Guide

**A comprehensive guide to understanding the Ithaka AI-powered chatbot system**

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Tech Stack](#2-tech-stack)
3. [Project Structure](#3-project-structure)
4. [How Workflows Work](#4-how-workflows-work)
5. [Agent Routing & Orchestration](#5-agent-routing--orchestration)
6. [Postulations System](#6-postulations-system)
7. [Database Models](#7-database-models)
8. [Key Components Explained](#8-key-components-explained)
9. [Setup & Running](#9-setup--running)
10. [API Endpoints](#10-api-endpoints)
11. [Development Guide](#11-development-guide)

---

## 1. Project Overview

### What is Ithaka Backend?

This is a **FastAPI-based backend** for **Ithaka**, an entrepreneurship incubator at Universidad Católica del Uruguay (UCU). It uses AI agents to handle conversations, answer FAQs, validate data, and guide users through a 20-question application form.

### Main Features

- 🤖 **AI-powered conversational interface** using OpenAI GPT-4
- 🎯 **Intelligent agent routing** with LangGraph
- ❓ **FAQ system** with semantic search (PGVector)
- 📝 **Conversational 20-question wizard** for applications
- 💾 **PostgreSQL database** for persistence
- 🔔 **Notifications** via Email and WhatsApp (Twilio)
- 📊 **AI-powered scoring** of applications

---

## 2. Tech Stack

### Core Framework
- **FastAPI** - Modern web framework
- **Python 3.12+** - Programming language
- **PostgreSQL + PGVector** - Database with vector search

### AI/LLM Stack
- **OpenAI GPT-4o-mini** - Language model for conversations
- **OpenAI text-embedding-3-small** - Vector embeddings
- **LangGraph** - Agent orchestration framework
- **LangChain** - AI framework primitives

### Infrastructure
- **Docker** - Containerization
- **Kubernetes** - Orchestration
- **Azure Container Registry** - Image hosting
- **Twilio** - WhatsApp notifications
- **SQLAlchemy** - Async ORM

### Key Dependencies

```
fastapi==0.115.14
uvicorn==0.35.0
sqlalchemy==2.0.42
asyncpg==0.30.0
pgvector==0.4.1
openai==1.99.1
langgraph==0.2.76
pydantic==2.11.7
```

---

## 3. Project Structure

```
app/
├── agents/                    # AI agents (core intelligence)
│   ├── supervisor.py         # Routes messages to appropriate agents
│   ├── faq.py               # Answers FAQs using vector search
│   ├── wizard.py            # Conversational form (legacy)
│   ├── validator.py         # Data validation agent
│   └── wizard_workflow/     # New wizard implementation
│       ├── nodes.py         # Workflow nodes (ask/store)
│       ├── wizard_graph.py  # LangGraph workflow definition
│       └── validator.py     # Input validation
│
├── api/v1/                   # REST/WebSocket endpoints
│   ├── conversations.py     # CRUD for conversations
│   ├── copilotkit_endpoint.py  # CopilotKit integration
│   └── scoring.py           # Application scoring API
│
├── graph/                    # LangGraph workflow orchestration
│   ├── workflow.py          # Main workflow logic
│   └── state.py             # State definitions (TypedDict)
│
├── services/                 # Business logic layer
│   ├── chat_service.py      # Main chat processing service
│   ├── embedding_service.py # Vector embeddings management
│   ├── scoring_service.py   # Application scoring logic
│   ├── score_engine.py      # Rule-based scoring
│   └── ai_score_engine.py   # AI-powered scoring (GPT-4)
│
├── db/                       # Database layer
│   ├── models.py            # SQLAlchemy models
│   └── config/
│       ├── database.py      # DB connection and session
│       └── create_tables.py # Table creation script
│
├── config/                   # Configuration
│   ├── questions.py         # 20-question wizard config
│   └── rubrica.json         # Scoring rubric
│
├── utils/                    # Utilities
│   ├── validators.py        # Email, phone, CI validation
│   └── notifier.py          # Email/WhatsApp notifications
│
└── main.py                   # FastAPI app entry point

scripts/
└── populate_faqs.py         # Script to populate FAQ embeddings

k8s/                         # Kubernetes deployment configs
docs/                        # Documentation
```

---

## 4. How Workflows Work

### Overview: Two Main Workflows

The system uses **LangGraph** (a state machine framework) with two workflows:

1. **Main Workflow** - Routes between different agents (Supervisor, FAQ, Wizard)
2. **Wizard Sub-Workflow** - Handles the 20-question form

### Main Workflow Structure

```
┌──────────────────────────────────────────────┐
│         USER MESSAGE ARRIVES                  │
└──────────────┬───────────────────────────────┘
               │
               ▼
        ┌─────────────┐
        │ SUPERVISOR  │ ◄── Entry Point
        │  (Router)   │
        └──────┬──────┘
               │
               │ Analyzes intent
               │
        ┌──────▼──────┐
        │  Conditional │
        │   Decision   │
        └──────┬───────┘
               │
       ┌───────┼───────┐
       │       │       │
       ▼       ▼       ▼
   ┌─────┐ ┌─────┐ ┌──────┐
   │ FAQ │ │WIZARD│ │ END  │
   └──┬──┘ └──┬──┘ └──────┘
      │       │
      │       │ (nested workflow)
      │       │
      ▼       ▼
    ┌──────────┐
    │   END    │
    └──────────┘
```

### State Structure

```python
class ConversationState(TypedDict):
    messages: Annotated[list, add_messages]  # Chat history
    conversation_id: Optional[int]           # DB ID
    user_email: Optional[str]               # User email
    current_agent: str                      # Active agent name
    agent_context: Dict[str, Any]           # Agent-specific data
    wizard_state: Optional[WizardState]     # Nested wizard state
```

### Workflow Code Example

```python
class IthakaWorkflow:
    def _build_graph(self) -> CompiledStateGraph:
        # 1. Create state graph
        workflow = StateGraph(ConversationState)
        
        # 2. Add agent nodes
        workflow.add_node("supervisor", route_message)
        workflow.add_node("wizard", handle_wizard_flow_good)
        workflow.add_node("faq", handle_faq_query)
        
        # 3. Set entry point
        workflow.set_entry_point("supervisor")
        
        # 4. Add conditional routing
        workflow.add_conditional_edges(
            "supervisor",
            decide_next_agent_wrapper,
            {
                "wizard": "wizard",
                "faq": "faq",
                "end": END
            }
        )
        
        # 5. Terminal edges
        workflow.add_edge("wizard", END)
        workflow.add_edge("faq", END)
        
        # 6. Compile with memory
        return workflow.compile(checkpointer=InMemorySaver())
```

### Wizard Sub-Workflow

```
START
  │
  ▼
┌───────┐
│ ENTRY │ (Conditional entry point)
└───┬───┘
    │
    │ Decision: Has user answered?
    │
    ├─────────────────────┐
    │                     │
   NO                    YES
    │                     │
    ▼                     ▼
┌──────────────┐   ┌──────────────┐
│ ASK_QUESTION │   │ STORE_ANSWER │
│              │   │              │
│ - Get Q #i   │   │ - Save answer│
│ - Send to    │   │ - Increment  │
│   user       │   │   question # │
└──────┬───────┘   └──────┬───────┘
       │                  │
       │                  │ Check: All done?
       │                  │
       │            ┌─────┴─────┐
       │           NO          YES
       │            │            │
       └────────────┤            ▼
                    │   ┌─────────────────┐
                    │   │ COMPLETION_MSG  │
                    │   │                 │
                    │   │ "Gracias!"     │
                    │   └────────┬────────┘
                    │            │
                    ▼            ▼
              ┌──────────┐
              │  FINISH  │
              └────┬─────┘
                   │
                   ▼
                  END
```

### Key Workflow Concepts

#### 1. State Reducers

```python
# add_messages is a reducer that merges messages
messages: Annotated[list, add_messages]

# This means:
# Old state: [msg1, msg2]
# New update: [msg3]
# Result: [msg1, msg2, msg3]  (not replaced, merged!)
```

#### 2. Conditional Edges

```python
workflow.add_conditional_edges(
    "supervisor",           # From this node
    decide_next_agent,      # Run this function
    {                       # Map return value to next node
        "wizard": "wizard",
        "faq": "faq",
        "end": END
    }
)
```

#### 3. Checkpointing

```python
workflow.compile(checkpointer=InMemorySaver())
# Saves state in memory between invocations
# Allows conversation continuity
```

---

## 5. Agent Routing & Orchestration

### The Orchestration Flow

```
User Message
    ↓
FastAPI Endpoint (WebSocket/REST)
    ↓
ChatService.process_message()
    ↓
IthakaWorkflow.process_message()
    ↓
workflow.graph.ainvoke(initial_state)  ← LangGraph starts
```

### The Supervisor Agent (Router)

Located in `app/agents/supervisor.py`

**Responsibilities:**
- Analyzes user intent
- Checks if wizard is already active
- Routes to appropriate agent
- Updates state with routing decision

**Routing Logic:**

```python
async def route_message(state: ConversationState):
    user_message = state["messages"][-1].content
    
    # STEP 1: Check if wizard is already active
    wizard_state = state.get("wizard_state")
    if wizard_state and wizard_state["wizard_status"] == "ACTIVE":
        return route_to_wizard(state)
    
    # STEP 2: Simple pattern matching (fast path)
    intention = analyze_intention_simple(user_message)
    
    # STEP 3: AI analysis if unclear (slow path)
    if intention == "unclear":
        intention = await analyze_intention_with_ai(user_message)
    
    # STEP 4: Update state
    state["supervisor_decision"] = intention
    state["current_agent"] = intention
    
    return state
```

### Intent Analysis Methods

#### Method 1: Pattern Matching (Fast ⚡)

```python
def analyze_intention_simple(message: str) -> str:
    message = message.lower()
    
    # Wizard patterns
    wizard_keywords = [
        "postular", "inscribirme", "tengo una idea",
        "emprender", "formulario"
    ]
    
    # FAQ patterns
    faq_keywords = [
        "pregunta", "qué es", "cómo", "programa", "curso"
    ]
    
    if any(kw in message for kw in wizard_keywords):
        return "wizard"
    
    if any(kw in message for kw in faq_keywords):
        return "faq"
    
    return "unclear"
```

#### Method 2: AI Analysis (Smart 🧠)

```python
async def analyze_intention_with_ai(message: str) -> str:
    prompt = f"""
Analiza la intención y clasifica como:
- "faq" - Preguntas sobre programas
- "wizard" - Quiere postularse

MENSAJE: "{message}"
Responde ÚNICAMENTE: faq o wizard
"""
    
    response = await openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=10
    )
    
    return response.choices[0].message.content.strip().lower()
```

### Conditional Edge Decision

```python
def decide_next_agent_wrapper(state: ConversationState) -> str:
    """LangGraph calls this to decide routing"""
    
    supervisor_decision = state.get("supervisor_decision")
    
    if supervisor_decision == "faq":
        return "faq"      # Go to FAQ agent
    
    if supervisor_decision == "wizard":
        return "wizard"   # Go to Wizard agent
    
    return "faq"  # Default fallback
```

### FAQ Agent Execution

Located in `app/agents/faq.py`

**Process:**

```python
async def handle_faq_query(state: ConversationState):
    user_message = state["messages"][-1].content
    
    # 1. Generate embedding for query
    query_embedding = await embedding_service.generate_embedding(user_message)
    
    # 2. Search similar FAQs in PostgreSQL with PGVector
    similar_faqs = await embedding_service.search_similar_faqs(
        query=user_message,
        limit=5,
        similarity_threshold=0.4
    )
    
    # 3. Generate contextual response with OpenAI
    if similar_faqs:
        response = await generate_contextual_response(
            user_message, similar_faqs
        )
    else:
        response = await generate_no_results_response(user_message)
    
    # 4. Return state updates
    return {
        "agent_context": {
            "response": response,
            "found_faqs": len(similar_faqs)
        },
        "messages": [AIMessage(content=response)],
        "faq_results": similar_faqs
    }
```

### Complete Flow Example

**User asks: "¿Qué es el programa Fellows?"**

```
1. Message arrives → ChatService
2. Create initial state:
   {
     messages: [HumanMessage("¿Qué es...")],
     current_agent: "supervisor",
     wizard_state: None
   }

3. workflow.ainvoke(state)
   LangGraph starts

4. SUPERVISOR NODE executes:
   - Check wizard state → INACTIVE
   - Analyze: "¿Qué es..." → Pattern match "qué es" → "faq"
   - Update: supervisor_decision = "faq"

5. Conditional edge:
   decide_next_agent_wrapper(state)
   → Returns "faq"

6. FAQ NODE executes:
   - Generate embedding
   - Vector search → Find 3 similar FAQs
   - Ask OpenAI to generate response
   - Return: messages + agent_context

7. Edge to END → Workflow terminates

8. Return final state with response

9. ChatService extracts response

10. Return to user
```

### Routing Decision Tree

```
User Message
    │
    ▼
Is wizard active?
    │
    ├─ YES → Route to wizard
    │
    └─ NO → Analyze intent
            │
            ├─ Contains "postular"? → wizard
            ├─ Contains "qué es"? → faq
            └─ Unclear? → Ask OpenAI
                          ├─ "wizard" → wizard
                          ├─ "faq" → faq
                          └─ default → faq
```

---

## 6. Postulations System

### Current State: Two-Phase Process

#### Phase 1: Wizard Collects Data ✅ (Implemented)

**Location:** `app/agents/wizard_workflow/`

**The 20 Questions:**

```
Q1-11: Personal Data (Required)
  Q1:  Full name
  Q2:  Email
  Q3:  Phone number
  Q4:  Document ID
  Q5:  Location (country + city)
  Q6:  Preferred campus (Maldonado/Montevideo/Salto)
  Q7:  UCU relation (Student/Graduate/Staff/None)
  Q8:  Faculty (conditional on Q7)
  Q9:  How did you find Ithaka?
  Q10: Motivation
  Q11: Do you have an idea? (YES/NO)

Q12: Optional comments (if Q11 = NO, wizard stops here)

Q13-20: Entrepreneurship Details (if Q11 = YES)
  Q13: Team composition
  Q14: Problem description
  Q15: Solution description
  Q16: Innovation & differential value
  Q17: Business model
  Q18: Project stage
  Q19: Support needed
  Q20: Additional information
```

**Wizard Flow:**

```
User: "Quiero postularme"
    ↓
Supervisor → Wizard Agent
    ↓
Ask Q1 → Store Answer → Ask Q2 → Store Answer → ...
    ↓
All 20 questions completed
    ↓
Save to wizard_sessions table
    ↓
Show completion message
```

**Database Storage:**

```sql
-- wizard_sessions table
{
    "id": 1,
    "conv_id": 123,
    "current_question": 20,
    "responses": {
        "full_name": "Juan Pérez",
        "email": "juan@example.com",
        "phone": "+598123456",
        ... all 20 answers as JSON
    },
    "state": "COMPLETED"
}
```

#### Phase 2: Create Postulation Record ⚠️ (NOT IMPLEMENTED)

**The Problem:** After wizard completion, **no code creates a record in the `postulations` table**.

**What SHOULD happen:**

```python
# MISSING CODE
async def _save_postulation(conversation_id, wizard_responses):
    """Create postulation record from wizard responses"""
    
    postulation = Postulation(
        conv_id=conversation_id,
        payload_json=wizard_responses,  # All answers as JSON
        created_at=datetime.now()
    )
    
    session.add(postulation)
    await session.commit()
```

**The Gap:**

```
┌─────────────────┐
│ User completes  │
│ 20 questions    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Saved to        │  ✅ This happens
│ wizard_sessions │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ ❌ GAP HERE ❌   │  ⚠️ Missing code
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Should create   │  ❌ This doesn't happen
│ postulation     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Score postula-  │  ✅ Works (if postulation exists)
│ tion (optional) │
└─────────────────┘
```

### Scoring System

Located in `app/api/v1/scoring.py` and `app/services/scoring_service.py`

**Evaluates postulations on 3 dimensions:**

1. **Creatividad (40%)** - Innovation, vocabulary, originality
2. **Claridad (30%)** - Structure, coherence, organization
3. **Compromiso (30%)** - Motivation, dedication, vision

**Two scoring engines:**
- **Rule-based** (fast, free, keyword-based)
- **AI-powered** (GPT-4, contextual, detailed analysis)

**API Endpoints:**

```bash
# Get all postulations
GET /api/v1/scoring/postulations

# Score all unscored postulations
POST /api/v1/scoring/process-all?use_ai=true

# Score specific postulation
POST /api/v1/scoring/process/123?use_ai=true

# Evaluate text manually
POST /api/v1/scoring/evaluate
{
    "texto": "Text to evaluate...",
    "use_ai": true
}
```

---

## 7. Database Models

Located in `app/db/models.py`

### Conversation

```python
class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True)
    email = Column(String(255), nullable=True)
    started_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    messages = relationship("Message", back_populates="conversation")
    postulations = relationship("Postulation", back_populates="conversation")
    wizard_sessions = relationship("WizardSession", back_populates="conversation")
```

### Message

```python
class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True)
    conv_id = Column(Integer, ForeignKey("conversations.id"))
    role = Column(String(50))  # "user" or "assistant"
    content = Column(String)
    ts = Column(DateTime, server_default=func.now())
```

### Postulation

```python
class Postulation(Base):
    __tablename__ = "postulations"
    
    id = Column(Integer, primary_key=True)
    conv_id = Column(Integer, ForeignKey("conversations.id"))
    payload_json = Column(JSON, nullable=False)  # All wizard answers
    created_at = Column(DateTime, server_default=func.now())
    
    # Scoring fields
    creatividad = Column(Integer)
    claridad = Column(Integer)
    compromiso = Column(Integer)
    score_total = Column(Float)
```

### WizardSession

```python
class WizardSession(Base):
    __tablename__ = "wizard_sessions"
    
    id = Column(Integer, primary_key=True)
    conv_id = Column(Integer, ForeignKey("conversations.id"))
    current_question = Column(Integer, default=1)
    responses = Column(JSON, default={})  # All wizard answers
    state = Column(String(50), default="ACTIVE")  # ACTIVE/COMPLETED/PAUSED
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
```

### FAQEmbedding

```python
class FAQEmbedding(Base):
    __tablename__ = "faq_embeddings"
    
    id = Column(Integer, primary_key=True)
    question = Column(String, nullable=False)
    answer = Column(Text, nullable=False)
    embedding = Column(Vector(1536))  # OpenAI embeddings dimension
    created_at = Column(DateTime, server_default=func.now())
```

### Entity Relationships

```
Conversation ──< Message
            └─< Postulation
            └─< WizardSession

FAQEmbedding (independent; for FAQ search)
```

---

## 8. Key Components Explained

### ChatService

Located in `app/services/chat_service.py`

**Main orchestrator for chat interactions**

**Key Methods:**

```python
async def process_message(
    user_message: str,
    user_email: str = None,
    conversation_id: int = None
) -> dict:
    """Main entry point for processing messages"""
    
    # 1. Get or create conversation
    # 2. Get chat history
    # 3. Get wizard state
    # 4. Process through workflow
    # 5. Save messages
    # 6. Update wizard state
    # 7. Return response
```

### EmbeddingService

Located in `app/services/embedding_service.py`

**Manages vector embeddings for FAQ search**

**Key Methods:**

```python
async def generate_embedding(text: str) -> List[float]:
    """Generate embedding using OpenAI"""

async def search_similar_faqs(
    query: str,
    session: AsyncSession,
    limit: int = 5,
    similarity_threshold: float = 0.7
) -> List[dict]:
    """Search FAQs using cosine similarity"""
```

### Validators

Located in `app/utils/validators.py`

**Validation functions:**

```python
def validate_email(email: str) -> bool:
    """RFC 5322 email validation"""

def validate_phone(phone: str) -> bool:
    """8-12 digit phone validation"""

def validate_ci(ci: str) -> bool:
    """Uruguayan ID validation"""
```

### Notifier

Located in `app/utils/notifier.py`

**Notification functions:**

```python
def send_email_confirmation(email: str, nombre: str):
    """Send email notification"""

def send_whatsapp_message(phone: str, message: str):
    """Send WhatsApp via Twilio"""
```

---

## 9. Setup & Running

### Prerequisites

- Python 3.12+
- PostgreSQL with PGVector extension
- OpenAI API key
- Twilio account (optional, for WhatsApp)

### Installation

#### 1. Clone and setup environment

```bash
git clone <repo-url>
cd reto-winter-2025-ithaka-backend

python3 -m venv .venv
source .venv/bin/activate
```

#### 2. Install dependencies

```bash
pip install uv
uv pip install -r requirements.txt
```

#### 3. Configure environment variables

Copy `.env.example` to `.env`:

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:password@host:port/database

# OpenAI
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Embeddings
EMBEDDING_DIMENSION=1536
MAX_FAQ_RESULTS=5

# Notifications
EMAIL_USER=your-email@gmail.com
EMAIL_PASS=your-app-password
TWILIO_ACCOUNT_SID=your-sid
TWILIO_AUTH_TOKEN=your-token
```

#### 4. Setup database

```bash
# Create database and user
psql -U postgres
CREATE USER myuser WITH PASSWORD 'mypassword';
CREATE DATABASE ithaka_db OWNER myuser;
GRANT ALL PRIVILEGES ON DATABASE ithaka_db TO myuser;

# Enable PGVector extension
\c ithaka_db
CREATE EXTENSION IF NOT EXISTS vector;
```

#### 5. Create tables

```bash
python -m app.db.config.create_tables
```

#### 6. Populate FAQs (optional)

```bash
python scripts/populate_faqs.py
```

#### 7. Run the server

```bash
uvicorn app.main:app --reload
```

Access the API at: `http://localhost:8000`

API documentation at: `http://localhost:8000/docs`

### Docker Setup

#### Option A: Use pre-built image

```bash
docker pull crretoxmas2024.azurecr.io/ithaka-backend:latest
docker run -p 8000:8000 \
  -e DATABASE_URL=your-db-url \
  -e OPENAI_API_KEY=your-key \
  crretoxmas2024.azurecr.io/ithaka-backend:latest
```

#### Option B: Build locally

```bash
docker build -t ithaka-backend .
docker run -p 8000:8000 ithaka-backend
```

#### Option C: Docker Compose

```bash
docker-compose up
```

---

## 10. API Endpoints

### Conversations

```bash
# Create conversation
POST /conversations
{
    "email": "user@example.com"
}

# Get all conversations
GET /conversations
```

### Scoring

```bash
# Evaluate text
POST /api/v1/scoring/evaluate
{
    "texto": "Mi idea es...",
    "use_ai": true,
    "ai_provider": "openai"
}

# Process all postulations
POST /api/v1/scoring/process-all?use_ai=true

# Process specific postulation
POST /api/v1/scoring/process/{postulation_id}?use_ai=true

# Get all postulations
GET /api/v1/scoring/postulations

# Health check
GET /api/v1/scoring/health
```

### CopilotKit

```bash
# CopilotKit endpoint
POST /api/v1/copilotkit
```

### Health

```bash
# Root endpoint
GET /

# Health check
GET /health
```

---

## 11. Development Guide

### Adding a New Agent

1. **Create agent file** in `app/agents/`

```python
# app/agents/my_agent.py

async def handle_my_agent(state: ConversationState) -> ConversationState:
    """My custom agent logic"""
    user_message = state["messages"][-1].content
    
    # Process message
    response = process(user_message)
    
    # Return state updates
    return {
        "agent_context": {"response": response},
        "messages": [AIMessage(content=response)]
    }
```

2. **Add to workflow** in `app/graph/workflow.py`

```python
from ..agents.my_agent import handle_my_agent

# In _build_graph():
workflow.add_node("my_agent", handle_my_agent)

workflow.add_conditional_edges(
    "supervisor",
    decide_next_agent_wrapper,
    {
        "wizard": "wizard",
        "faq": "faq",
        "my_agent": "my_agent",  # Add this
        "end": END
    }
)

workflow.add_edge("my_agent", END)
```

3. **Update supervisor** in `app/agents/supervisor.py`

```python
# Add keywords
my_agent_keywords = ["keyword1", "keyword2"]

if any(kw in message for kw in my_agent_keywords):
    return "my_agent"
```

### Running Tests

```bash
# Lint code
ruff check .

# Run tests
pytest

# Test specific module
pytest tests/test_scoring.py
```

### Database Migrations

When adding new models or fields:

```bash
# After updating models.py
python -m app.db.config.create_tables
```

### Debugging

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

View logs:
- Supervisor decisions
- Agent routing
- Database queries
- API calls

### Code Quality

```bash
# Format code
ruff format .

# Check linting
ruff check .

# Fix auto-fixable issues
ruff check --fix .
```

---

## Key Takeaways

### What Works ✅
- AI-powered agent routing with LangGraph
- FAQ system with semantic search
- 20-question wizard for applications
- Conversation persistence
- Scoring system (rules + AI)

### What's Missing ❌
- Postulation creation from wizard responses
- Link between wizard_sessions → postulations

### Architecture Strengths 💪
- **Stateful**: Maintains context across messages
- **Flexible**: Easy to add new agents
- **Intelligent**: Combines fast rules + smart AI
- **Scalable**: Docker + Kubernetes ready
- **Observable**: Comprehensive logging

### Performance ⚡
- **Fast path** (pattern matching): ~1ms
- **Slow path** (AI analysis): ~200-500ms
- **Vector search**: ~50-100ms
- **End-to-end response**: ~500-1000ms

---

## Additional Resources

- [LangGraph Documentation](https://python.langchain.com/docs/langgraph)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [PGVector Documentation](https://github.com/pgvector/pgvector)
- [OpenAI API Documentation](https://platform.openai.com/docs)

---

**Last Updated:** February 2026

**Maintained by:** Ithaka Backend Team
