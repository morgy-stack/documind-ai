import json
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.core.config import settings
from app.rag.ingestion import ingest_file, SUPPORTED_EXTENSIONS
from app.rag.vector_store import get_vector_store

router = APIRouter()
SAMPLE_PATH = Path(__file__).resolve().parents[2] / "samples" / "northwind-handbook.txt"


def manifest_path() -> Path:
    # Demo and OpenAI modes keep separate indexes, so each needs its own document list.
    name = "documents_demo.json" if settings.use_demo else "documents.json"
    return Path(settings.upload_dir) / name


def read_manifest() -> list[dict]:
    path = manifest_path()
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def write_manifest(items: list[dict]) -> None:
    path = manifest_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(items, indent=2), encoding="utf-8")


@router.get("/documents")
def list_documents():
    return read_manifest()


@router.post("/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    filename = Path(file.filename or "upload").name
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=415, detail="Supported formats: PDF, DOCX, TXT.")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if len(content) > settings.max_file_size_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File exceeds {settings.max_file_size_mb} MB limit.")

    return index_document(filename, content)


@router.post("/documents/sample")
def upload_sample_document():
    """Index the bundled sample handbook so visitors can try the app without their own files."""
    return index_document(SAMPLE_PATH.name, SAMPLE_PATH.read_bytes())


def index_document(filename: str, content: bytes) -> dict:
    try:
        result = ingest_file(filename, content)
        items = read_manifest()
        items.append(result)
        write_manifest(items)
        return {**result, "message": "Document indexed successfully."}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Document processing failed: {exc}")


@router.delete("/documents/{document_id}")
def delete_document(document_id: str):
    items = read_manifest()
    match = next((item for item in items if item["id"] == document_id), None)
    if not match:
        raise HTTPException(status_code=404, detail="Document not found.")
    try:
        get_vector_store().delete(where={"document_id": document_id})
        write_manifest([item for item in items if item["id"] != document_id])
        return {"message": f"Deleted {match['filename']}."}
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
