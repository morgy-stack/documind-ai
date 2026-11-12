# Development notes

## RAG pipeline

1. Validate file extension and size.
2. Extract text and page metadata.
3. Split text into overlapping chunks.
4. Create embeddings using the configured embedding model.
5. Persist chunks and metadata in Chroma.
6. Embed/search a user question using semantic similarity.
7. Supply retrieved passages to the chat model.
8. Return the answer and source metadata to the UI.

## Useful improvements

- Add OCR for scanned PDFs.
- Add tables and image extraction.
- Add hybrid keyword + vector search.
- Add a cross-encoder reranker.
- Add query rewriting and contextual compression.
- Add RAG evaluation with a curated question/answer dataset.
- Move ingestion to a background worker for large files.
- Add user accounts and tenant-aware collections.
