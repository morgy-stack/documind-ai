from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routes import health, documents, chat

app = FastAPI(
    title="DocuMind AI API",
    description="Document-based Retrieval-Augmented Generation assistant.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(documents.router, prefix="/api", tags=["Documents"])
app.include_router(chat.router, prefix="/api", tags=["Chat"])


@app.get("/")
def root():
    return {"name": "DocuMind AI", "docs": "/docs"}
