from fastapi import APIRouter, HTTPException
from app.schemas.api import ChatRequest, ChatResponse
from app.rag.retrieval import answer_question

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest):
    try:
        result = answer_question(payload.question)
        return result
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unable to generate answer: {exc}")
