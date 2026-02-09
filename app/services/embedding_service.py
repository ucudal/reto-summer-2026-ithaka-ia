import logging
import os
from typing import List, Optional

import numpy as np
from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import FAQEmbedding

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Servicio para generar y gestionar embeddings usando OpenAI"""

    def __init__(self):
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = os.getenv("OPENAI_EMBEDDING_MODEL",
                               "text-embedding-3-small")
        self.dimension = int(os.getenv("EMBEDDING_DIMENSION", "1536"))

    async def generate_embedding(self, text: str) -> List[float]:
        """Genera embedding para un texto dado"""
        try:
            response = await self.client.embeddings.create(
                model=self.model,
                input=text.strip()
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise

    async def generate_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Genera embeddings para múltiples textos en batch"""
        try:
            response = await self.client.embeddings.create(
                model=self.model,
                input=texts
            )
            return [data.embedding for data in response.data]
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {e}")
            raise

    async def search_similar_faqs(
            self,
            query: str,
            session: AsyncSession,
            limit: int = 5,
            similarity_threshold: float = 0.7
    ) -> List[dict]:
        """Busca FAQs similares usando similitud de coseno"""
        try:
            # Generar embedding para la query
            query_embedding = await self.generate_embedding(query)

            # Búsqueda vectorial en PostgreSQL
            stmt = select(FAQEmbedding).order_by(
                FAQEmbedding.embedding.cosine_distance(query_embedding)
            ).limit(limit)

            result = await session.execute(stmt)
            faqs = result.scalars().all()

            # Calcular similitudes y filtrar por threshold
            similar_faqs = []
            for faq in faqs:
                # Calcular similitud de coseno
                similarity = self._cosine_similarity(
                    query_embedding, faq.embedding)

                if similarity >= similarity_threshold:
                    similar_faqs.append({
                        "id": faq.id,
                        "question": faq.question,
                        "answer": faq.answer,
                        "similarity": similarity
                    })

            return similar_faqs

        except Exception as e:
            logger.error(f"Error searching similar FAQs: {e}")
            return []

    async def add_faq_embedding(
            self,
            question: str,
            answer: str,
            session: AsyncSession
    ) -> Optional[FAQEmbedding]:
        """Agrega una nueva FAQ con su embedding"""
        try:
            # Combinar pregunta y respuesta para el embedding
            combined_text = f"Pregunta: {question}\nRespuesta: {answer}"
            embedding = await self.generate_embedding(combined_text)

            # Crear nuevo registro
            faq_embedding = FAQEmbedding(
                question=question,
                answer=answer,
                embedding=embedding
            )

            session.add(faq_embedding)
            await session.commit()
            await session.refresh(faq_embedding)

            logger.info(f"FAQ embedding added with ID: {faq_embedding.id}")
            return faq_embedding

        except Exception as e:
            logger.error(f"Error adding FAQ embedding: {e}")
            await session.rollback()
            return None

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calcula similitud de coseno entre dos vectores"""
        try:
            vec1_np = np.array(vec1)
            vec2_np = np.array(vec2)

            dot_product = np.dot(vec1_np, vec2_np)
            norm1 = np.linalg.norm(vec1_np)
            norm2 = np.linalg.norm(vec2_np)

            if norm1 == 0 or norm2 == 0:
                return 0.0

            return dot_product / (norm1 * norm2)
        except Exception as e:
            logger.error(f"Error calculating cosine similarity: {e}")
            return 0.0


# Instancia global del servicio
embedding_service = EmbeddingService()
