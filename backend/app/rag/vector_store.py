import os

# Chroma's anonymous usage telemetry is on by default; keep document metadata local.
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

from functools import lru_cache
from langchain_chroma import Chroma
from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings
from app.core.config import settings
from app.rag.demo import DemoEmbeddings


def get_embeddings() -> Embeddings:
    if settings.use_demo:
        return DemoEmbeddings()
    return OpenAIEmbeddings(
        model=settings.openai_embedding_model,
        api_key=settings.openai_api_key,
    )


def get_vector_store() -> Chroma:
    return _build_store(settings.use_demo)


@lru_cache
def _build_store(demo: bool) -> Chroma:
    # Demo and OpenAI embeddings have different dimensions, so they never share a collection.
    return Chroma(
        collection_name="documind_documents_demo" if demo else "documind_documents",
        embedding_function=get_embeddings(),
        persist_directory=settings.chroma_persist_directory,
    )
