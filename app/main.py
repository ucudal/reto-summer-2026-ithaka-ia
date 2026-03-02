import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

log_level = os.getenv("LOG_LEVEL", "DEBUG").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.DEBUG),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    force=True,
)

from app.api.v1.agui_ws import router as agui_ws_router
from app.api.v1.conversations import router as conversations_router
from app.api.v1.documents import router as documents_router
from app.api.v1.scoring import router as scoring_router

v1 = '/api/v1'

app = FastAPI(title="Chatbot Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000",
                   "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(conversations_router, prefix=v1, tags=["Conversations"])
app.include_router(agui_ws_router, prefix=v1, tags=["AG-UI WebSocket"])
app.include_router(documents_router, prefix=v1, tags=["Documents"])
app.include_router(scoring_router, prefix=v1, tags=["Scoring"])


@app.get("/")
def root():
    return {"message": "API está corriendo"}


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "ithaka-backend"}
