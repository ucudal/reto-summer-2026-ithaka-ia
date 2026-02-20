from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class DocumentCreate(BaseModel):
    question: str = Field(..., min_length=3, description="Pregunta o titulo del documento")
    answer: str = Field(..., min_length=3, description="Respuesta o contenido del documento")


class DocumentResponse(BaseModel):
    id: int
    question: str
    answer: str
    created_at: Optional[datetime]


class DocumentUploadResponse(BaseModel):
    filename: str
    file_type: str
    chunks_created: int
    document_ids: list[int]
