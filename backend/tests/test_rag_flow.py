"""End-to-end tests for upload -> index -> retrieve -> answer -> delete.

Most tests run in demo mode, which is fully offline, so they exercise the real
code with no fakes. test_openai_mode swaps OpenAI for fakes to cover the
production path without a key or network access.
"""
import io

import pytest
from docx import Document as DocxDocument
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from app.core.config import settings
from app.main import app
from app.rag import retrieval, vector_store
from app.rag.demo import DemoEmbeddings


class FakeChat:
    """Stands in for ChatOpenAI; echoes the first retrieved source back."""

    last_messages: list = []

    def __init__(self, **_kwargs):
        pass

    def invoke(self, messages):
        FakeChat.last_messages = messages
        context = messages[-1].content
        first = context.split("[Source 1]", 1)[1].split("\n", 2)[1]
        return AIMessage(content=f"According to the document: {first} [Source 1]")


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "")
    monkeypatch.setattr(settings, "demo_mode", False)
    monkeypatch.setattr(settings, "chroma_persist_directory", str(tmp_path / "chroma"))
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path / "uploads"))
    monkeypatch.setattr(settings, "top_k", 2)
    vector_store._build_store.cache_clear()
    yield TestClient(app)
    vector_store._build_store.cache_clear()


def make_docx(paragraphs: list[str]) -> bytes:
    doc = DocxDocument()
    for p in paragraphs:
        doc.add_paragraph(p)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def make_pdf(pages: list[str]) -> bytes:
    """Build a minimal valid PDF with one text line per page."""
    objects = ["<< /Type /Catalog /Pages 2 0 R >>", None,
               "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    kids = []
    for text in pages:
        stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET"
        objects.append(f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream")
        content_id = len(objects)
        objects.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                       f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>")
        kids.append(f"{len(objects)} 0 R")
    objects[1] = f"<< /Type /Pages /Kids [{' '.join(kids)}] /Count {len(kids)} >>"
    out = b"%PDF-1.4\n"
    offsets = []
    for i, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n{body}\nendobj\n".encode()
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    out += "".join(f"{o:010d} 00000 n \n" for o in offsets).encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()
    return out


def upload(client, name, content, mime="application/octet-stream"):
    return client.post("/api/documents/upload", files={"file": (name, content, mime)})


def test_txt_upload_chat_and_delete(client):
    text = ("The cancellation policy allows refunds within 30 days of purchase.\n\n"
            "Shipping takes five business days to Portugal and Spain.")
    res = upload(client, "policy.txt", text.encode(), "text/plain")
    assert res.status_code == 200, res.text
    doc = res.json()
    assert doc["filename"] == "policy.txt" and doc["chunks"] >= 1

    listed = client.get("/api/documents").json()
    assert [d["id"] for d in listed] == [doc["id"]]

    res = client.post("/api/chat", json={"question": "What is the cancellation policy for refunds?"})
    assert res.status_code == 200, res.text
    body = res.json()
    assert "30 days" in body["answer"]
    assert body["sources"][0]["filename"] == "policy.txt"
    assert body["sources"][0]["page"] is None

    res = client.delete(f"/api/documents/{doc['id']}")
    assert res.status_code == 200
    assert client.get("/api/documents").json() == []
    res = client.post("/api/chat", json={"question": "cancellation policy"})
    assert res.json()["sources"] == []


def test_pdf_pages_are_cited(client):
    pdf = make_pdf(["Introduction to the handbook", "The warranty period is two years"])
    res = upload(client, "handbook.pdf", pdf, "application/pdf")
    assert res.status_code == 200, res.text
    assert res.json()["chunks"] == 2

    body = client.post("/api/chat", json={"question": "How long is the warranty period?"}).json()
    top = body["sources"][0]
    assert top["filename"] == "handbook.pdf"
    assert top["page"] == 2
    assert "warranty" in top["excerpt"]


def test_docx_upload(client):
    res = upload(client, "guide.docx", make_docx(["Data retention is 90 days.", "Contact support by email."]))
    assert res.status_code == 200, res.text
    body = client.post("/api/chat", json={"question": "data retention days"}).json()
    assert "90 days" in body["sources"][0]["excerpt"]


def test_delete_only_removes_target_document(client):
    a = upload(client, "a.txt", b"Apples are red fruit.").json()
    b = upload(client, "b.txt", b"Bananas are yellow fruit.").json()
    assert client.delete(f"/api/documents/{a['id']}").status_code == 200
    body = client.post("/api/chat", json={"question": "fruit"}).json()
    assert {s["filename"] for s in body["sources"]} == {"b.txt"}
    assert [d["id"] for d in client.get("/api/documents").json()] == [b["id"]]


@pytest.mark.parametrize("name,content,status", [
    ("empty.txt", b"", 400),
    ("blank.txt", b"   \n\n  ", 400),
    ("binary.txt", b"\xff\xfe\x00bad", 400),
    ("broken.pdf", b"not a pdf", 400),
])
def test_bad_uploads_are_rejected(client, name, content, status):
    assert upload(client, name, content).status_code == status


def test_oversized_upload_rejected(client, monkeypatch):
    monkeypatch.setattr(settings, "max_file_size_mb", 1)
    assert upload(client, "big.txt", b"a" * (1024 * 1024 + 1)).status_code == 413


def test_delete_unknown_document_404(client):
    assert client.delete("/api/documents/does-not-exist").status_code == 404


def test_chat_validation(client):
    assert client.post("/api/chat", json={"question": "x"}).status_code == 422


def test_demo_mode_without_key(client):
    assert client.get("/api/health").json()["mode"] == "demo"
    upload(client, "policy.txt", b"Refunds are possible within 30 days. Offices close at 18:00.")
    answer = client.post("/api/chat", json={"question": "When are refunds possible?"}).json()["answer"]
    assert answer.startswith("Demo mode")
    assert "• Refunds are possible within 30 days. [Source 1]" in answer
    assert "18:00" not in answer


def test_demo_fallback_when_no_keyword_matches(client):
    upload(client, "notes.txt", b"First sentence is here. Second sentence is here.")
    answer = client.post("/api/chat", json={"question": "Summarize this"}).json()["answer"]
    assert "overview from the closest passages" in answer and "First sentence is here." in answer


def test_sample_document(client):
    res = client.post("/api/documents/sample")
    assert res.status_code == 200, res.text
    assert res.json()["filename"] == "northwind-handbook.txt"
    body = client.post("/api/chat", json={"question": "What is the cancellation policy?"}).json()
    assert "deposit is refunded in full" in body["answer"]
    assert "• Cancellation policy [" not in body["answer"]  # headings are not quoted


def test_openai_mode(client, monkeypatch):
    """With a key set, the OpenAI classes are used (replaced by fakes here)."""
    monkeypatch.setattr(settings, "openai_api_key", "test-key")
    monkeypatch.setattr(vector_store, "OpenAIEmbeddings", lambda **_kw: DemoEmbeddings())
    monkeypatch.setattr(retrieval, "ChatOpenAI", FakeChat)
    assert client.get("/api/health").json()["mode"] == "openai"
    upload(client, "policy.txt", b"The cancellation policy allows refunds within 30 days.")
    body = client.post("/api/chat", json={"question": "cancellation policy refunds"}).json()
    assert body["answer"].startswith("According to the document:")
    assert "Question: cancellation policy refunds" in FakeChat.last_messages[-1].content


def test_demo_and_openai_indexes_are_separate(client, monkeypatch):
    upload(client, "demo.txt", b"Uploaded while in demo mode.")
    monkeypatch.setattr(settings, "openai_api_key", "test-key")
    monkeypatch.setattr(vector_store, "OpenAIEmbeddings", lambda **_kw: DemoEmbeddings())
    assert client.get("/api/documents").json() == []
