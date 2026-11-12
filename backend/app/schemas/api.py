from pydantic import BaseModel, Field


class SourceItem(BaseModel):
    filename: str
    page: int | None = None
    excerpt: str
    chunk_id: str


class ChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=4000)


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceItem]


class DocumentItem(BaseModel):
    id: str
    filename: str
    chunks: int
    uploaded_at: str


class UploadResponse(DocumentItem):
    message: str
