import csv
from io import BytesIO

from fastapi import HTTPException


class DocumentIngestionService:
    """Handles text extraction and chunking for uploaded documents."""

    supported_extensions = {"pdf", "txt", "md", "csv"}
    max_file_size_bytes = 20 * 1024 * 1024

    def read_txt_like(self, content: bytes) -> str:
        for encoding in ("utf-8", "latin-1"):
            try:
                return content.decode(encoding)
            except UnicodeDecodeError:
                continue
        raise HTTPException(status_code=400, detail="No se pudo decodificar el archivo")

    def read_csv_content(self, content: bytes) -> str:
        text = self.read_txt_like(content)
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

        return text

    def read_pdf_content(self, content: bytes) -> str:
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

    def extract_file_text(self, filename: str, content: bytes) -> tuple[str, str]:
        extension = filename.rsplit(".", maxsplit=1)[-1].lower() if "." in filename else ""

        if extension in {"txt", "md"}:
            return extension, self.read_txt_like(content)
        if extension == "csv":
            return extension, self.read_csv_content(content)
        if extension == "pdf":
            return extension, self.read_pdf_content(content)

        raise HTTPException(
            status_code=400,
            detail="Formato no soportado. Usa pdf, txt, md o csv"
        )

    def split_text(self, text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
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


document_ingestion_service = DocumentIngestionService()
