from fastapi import APIRouter
from app.core.config import settings

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok", "service": "documind-api", "mode": "demo" if settings.use_demo else "openai"}
