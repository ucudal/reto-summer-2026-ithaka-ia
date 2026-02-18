from datetime import datetime
from io import BytesIO
import csv
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.config.database import get_async_session
from app.db.models import FAQEmbedding
from app.services.embedding_service import embedding_service

router = APIRouter()


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


def _read_txt_like(content: bytes) -> str:
    for encoding in ("utf-8", "latin-1"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise HTTPException(status_code=400, detail="No se pudo decodificar el archivo")


def _read_csv_content(content: bytes) -> str:
    text = _read_txt_like(content)
    reader = csv.DictReader(text.splitlines())
    lines: list[str] = []

    for row in reader:
        rendered = ", ".join(
            f"{column}: {value}" for column, value in row.items() if value is not None
        )
        if rendered:
            lines.append(rendered)

    if lines:
        return "\n".join(lines)

    # Fallback for CSV without headers
    return text


def _read_pdf_content(content: bytes) -> str:
    try:
        from pypdf import PdfReader
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Falta dependencia para PDF: instala pypdf"
        ) from exc

    try:
        reader = PdfReader(BytesIO(content))
        pages = [page.extract_text() or "" for page in reader.pages]
        text = "\n".join(page.strip() for page in pages if page and page.strip())
        if not text:
            raise HTTPException(
                status_code=400,
                detail="No se pudo extraer texto del PDF"
            )
        return text
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail="PDF invalido o corrupto") from exc


def _split_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    cleaned = text.strip()
    if not cleaned:
        return []

    chunks: list[str] = []
    start = 0
    text_length = len(cleaned)

    while start < text_length:
        end = min(start + chunk_size, text_length)
        chunk = cleaned[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= text_length:
            break
        start = end - chunk_overlap

    return chunks


def _extract_file_text(filename: str, content: bytes) -> tuple[str, str]:
    extension = filename.rsplit(".", maxsplit=1)[-1].lower() if "." in filename else ""

    if extension in {"txt", "md"}:
        return extension, _read_txt_like(content)
    if extension == "csv":
        return extension, _read_csv_content(content)
    if extension == "pdf":
        return extension, _read_pdf_content(content)

    raise HTTPException(
        status_code=400,
        detail="Formato no soportado. Usa pdf, txt, md o csv"
    )


@router.post("/documents", response_model=DocumentResponse, status_code=201)
async def create_document(
        document: DocumentCreate,
        session: AsyncSession = Depends(get_async_session)
) -> DocumentResponse:
    try:
        created = await embedding_service.add_faq_embedding(
            question=document.question,
            answer=document.answer,
            session=session
        )

        if created is None:
            raise HTTPException(
                status_code=500,
                detail="No se pudo crear el documento y su embedding"
            )

        return DocumentResponse(
            id=created.id,
            question=created.question,
            answer=created.answer,
            created_at=created.created_at
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Error creando documento")


@router.post("/documents/upload", response_model=DocumentUploadResponse, status_code=201)
async def upload_document(
        file: UploadFile = File(...),
        chunk_size: int = Query(1200, ge=200, le=4000),
        chunk_overlap: int = Query(150, ge=0, le=1000),
        session: AsyncSession = Depends(get_async_session)
) -> DocumentUploadResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Archivo sin nombre")

    if chunk_overlap >= chunk_size:
        raise HTTPException(
            status_code=400,
            detail="chunk_overlap debe ser menor que chunk_size"
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Archivo vacio")

    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Archivo demasiado grande (max 20MB)")

    file_type, text = _extract_file_text(file.filename, content)
    chunks = _split_text(text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    if not chunks:
        raise HTTPException(status_code=400, detail="No se encontro texto util en el archivo")

    created_ids: list[int] = []
    total = len(chunks)

    try:
        for index, chunk in enumerate(chunks, start=1):
            title = f"{file.filename} - fragmento {index}/{total}"
            combined_text = f"Pregunta: {title}\nRespuesta: {chunk}"
            vector = await embedding_service.generate_embedding(combined_text)
            item = FAQEmbedding(question=title, answer=chunk, embedding=vector)
            session.add(item)
            await session.flush()
            created_ids.append(item.id)

        await session.commit()
    except Exception:
        await session.rollback()
        raise HTTPException(status_code=500, detail="Error procesando el archivo")

    return DocumentUploadResponse(
        filename=file.filename,
        file_type=file_type,
        chunks_created=len(created_ids),
        document_ids=created_ids
    )


@router.get("/documents", response_model=list[DocumentResponse])
async def list_documents(
        limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0),
        session: AsyncSession = Depends(get_async_session)
) -> list[DocumentResponse]:
    try:
        stmt = (
            select(FAQEmbedding)
            .order_by(FAQEmbedding.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await session.execute(stmt)
        documents = result.scalars().all()

        return [
            DocumentResponse(
                id=document.id,
                question=document.question,
                answer=document.answer,
                created_at=document.created_at
            ) for document in documents
        ]
    except Exception:
        raise HTTPException(status_code=500, detail="Error listando documentos")


@router.delete("/documents/{document_id}")
async def delete_document(
        document_id: int,
        session: AsyncSession = Depends(get_async_session)
) -> dict:
    try:
        result = await session.execute(
            select(FAQEmbedding).where(FAQEmbedding.id == document_id)
        )
        document = result.scalar_one_or_none()

        if document is None:
            raise HTTPException(status_code=404, detail="Documento no encontrado")

        await session.delete(document)
        await session.commit()

        return {"message": f"Documento {document_id} eliminado correctamente"}
    except HTTPException:
        raise
    except Exception:
        await session.rollback()
        raise HTTPException(status_code=500, detail="Error eliminando documento")
