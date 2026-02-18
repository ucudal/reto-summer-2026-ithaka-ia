import asyncio
import os

from sqlalchemy import text

from app.db.config.database import Base, engine
from app.db import models  # noqa: F401 - needed so SQLAlchemy registers model metadata

DATABASE_URL = os.getenv("DATABASE_URL", "")


async def create_tables():
    async with engine.begin() as conn:
        # PostgreSQL: habilitar extensión pgvector (necesaria para faq_embeddings)
        if "postgresql" in DATABASE_URL:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)

if __name__ == "__main__":
    asyncio.run(create_tables())
