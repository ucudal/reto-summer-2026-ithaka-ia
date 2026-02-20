from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.documents import (
    DocumentCreate,
    DocumentResponse,
    DocumentUploadResponse,
)
from app.db.config.database import get_async_session
from app.db.models import FAQEmbedding
from app.security.auth import AuthUser, require_admin_user
from app.services.document_ingestion_service import document_ingestion_service
from app.services.embedding_service import embedding_service

router = APIRouter()


@router.post("/documents", response_model=DocumentResponse, status_code=201)
async def create_document(
        document: DocumentCreate,
        _current_user: AuthUser = Depends(require_admin_user),
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
        _current_user: AuthUser = Depends(require_admin_user),
        session: AsyncSession = Depends(get_async_session)
) -> DocumentUploadResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Archivo sin nombre")

    if chunk_overlap >= chunk_size:
        raise HTTPException(
            status_code=400,
            detail="chunk_overlap debe ser menor que chunk_size"
        )
    if chunk_overlap * 2 >= chunk_size:
        raise HTTPException(
            status_code=400,
            detail="chunk_overlap debe ser menor al 50% de chunk_size"
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Archivo vacio")

    if len(content) > document_ingestion_service.max_file_size_bytes:
        raise HTTPException(status_code=400, detail="Archivo demasiado grande (max 20MB)")

    file_type, text = document_ingestion_service.extract_file_text(file.filename, content)
    chunks = document_ingestion_service.split_text(
        text,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

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
        _current_user: AuthUser = Depends(require_admin_user),
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
