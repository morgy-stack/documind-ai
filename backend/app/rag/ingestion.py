import io
import uuid
from datetime import datetime, timezone
from pathlib import Path
from docx import Document as DocxDocument
from pypdf import PdfReader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.core.config import settings
from app.rag.vector_store import get_vector_store

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}


def extract_pages(filename: str, content: bytes) -> list[tuple[str, int | None]]:
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError("Unsupported file type. Upload PDF, DOCX, or TXT.")
    try:
        if suffix == ".pdf":
            reader = PdfReader(io.BytesIO(content))
            return [(page.extract_text() or "", index + 1) for index, page in enumerate(reader.pages)]
        if suffix == ".docx":
            doc = DocxDocument(io.BytesIO(content))
            text = "\n".join(paragraph.text for paragraph in doc.paragraphs if paragraph.text.strip())
            return [(text, None)]
        return [(content.decode("utf-8-sig"), None)]
    except UnicodeDecodeError as exc:
        raise ValueError("Text files must be UTF-8 encoded.") from exc
    except Exception as exc:
        raise ValueError(f"Could not read this {suffix[1:].upper()} file. It may be corrupted or password-protected.") from exc


def ingest_file(filename: str, content: bytes) -> dict:
    pages = extract_pages(filename, content)
    if not any(text.strip() for text, _ in pages):
        raise ValueError("No readable text was found in this file.")

    document_id = str(uuid.uuid4())
    uploaded_at = datetime.now(timezone.utc).isoformat()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks: list[Document] = []
    for text, page in pages:
        if not text.strip():
            continue
        for chunk_index, chunk in enumerate(splitter.split_text(text)):
            chunks.append(Document(
                page_content=chunk,
                metadata={
                    "document_id": document_id,
                    "filename": filename,
                    "page": page if page is not None else "",
                    "chunk_id": f"{document_id}:{page or 0}:{chunk_index}",
                    "uploaded_at": uploaded_at,
                },
            ))

    if not chunks:
        raise ValueError("The file did not produce any searchable text chunks.")

    ids = [chunk.metadata["chunk_id"] for chunk in chunks]
    get_vector_store().add_documents(chunks, ids=ids)
    return {
        "id": document_id,
        "filename": filename,
        "chunks": len(chunks),
        "uploaded_at": uploaded_at,
    }
