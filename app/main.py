from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.conversations import router as conversations_router
from app.api.v1.copilotkit_endpoint import router as copilotkit_router
from app.api.v1.scoring import router as scoring_router

v1 = '/api/v1'

app = FastAPI(title="Chatbot Backend", version="1.0.0")

# Configurar CORS para permitir conexiones desde el frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000",
                   "http://localhost:3001"],  # Frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(conversations_router)
app.include_router(scoring_router, prefix=v1, tags=["Scoring"])
app.include_router(copilotkit_router, prefix=v1, tags=["CopilotKit"])


@app.get("/")
def root():
    return {"message": "API está corriendo"}


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "ithaka-backend"}
