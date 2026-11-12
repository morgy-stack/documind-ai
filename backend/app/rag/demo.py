"""Offline demo mode: no API key, no network, no cost.

DemoEmbeddings replaces OpenAI embeddings with a hashed bag-of-words vector, so
passages that share words with the question are retrieved. extractive_answer
replaces the chat model by quoting the most relevant sentences instead of
writing a new answer. Both are deliberately simple: they show the full RAG
workflow working end to end, but the answers are weaker than a real model's.
"""
import hashlib
import math
import re

from langchain_core.embeddings import Embeddings

DEMO_NOTICE = "Demo mode (no AI model connected): here are the most relevant passages from your documents."

STOPWORDS = {
    "a", "about", "after", "all", "an", "and", "any", "are", "as", "at", "be", "by", "can", "do", "does",
    "document", "documents", "find", "for", "from", "give", "has", "have", "how", "i", "if", "in", "is",
    "it", "its", "me", "my", "of", "on", "or", "say", "says", "should", "so", "tell", "that", "the",
    "their", "there", "this", "to", "was", "we", "what", "when", "where", "which", "who", "why", "will",
    "with", "you", "your",
}


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _stem(word: str) -> str:
    # Crude plural folding so "deadlines" matches "deadline".
    return word[:-1] if len(word) > 3 and word.endswith("s") and not word.endswith("ss") else word


def _keywords(text: str) -> set[str]:
    return {_stem(w) for w in _words(text) if w not in STOPWORDS and len(w) > 1}


class DemoEmbeddings(Embeddings):
    dim = 512

    def _embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for word in _keywords(text):
            vec[int(hashlib.md5(word.encode()).hexdigest(), 16) % self.dim] += 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)


def _segments(text: str) -> list[tuple[str, bool]]:
    """Split into (text, is_heading). Headings are short lines without end punctuation."""
    segments = []
    for line in text.splitlines():
        for part in re.split(r"(?<=[.!?])\s+", line.strip()):
            part = re.sub(r"^\d+[.)]?\s*", "", part).strip()  # drop list numbers like "4."
            if not part:
                continue
            is_sentence = part[-1] in ".!?" or len(part.split()) >= 10
            segments.append((part, not is_sentence))
    return segments


def _sentences(text: str) -> list[str]:
    return [part for part, is_heading in _segments(text) if not is_heading and len(part.split()) >= 4]


def extractive_answer(question: str, passages: list[str], max_sentences: int = 3) -> str:
    """Quote the sentences that share the most keywords with the question, citing their source.

    A matching section heading (e.g. "Cancellation policy") is never quoted itself, but
    its score carries over to the sentences beneath it.
    """
    query = _keywords(question)
    scored = []
    seen = set()
    for source_index, passage in enumerate(passages, start=1):
        heading_score = 0
        for position, (part, is_heading) in enumerate(_segments(passage)):
            overlap = len(query & _keywords(part))
            if is_heading:
                heading_score = overlap
                continue
            if part in seen or len(part.split()) < 4:
                continue
            seen.add(part)
            score = overlap + heading_score
            if score:
                scored.append((-score, source_index, position, part))

    if scored:
        best = sorted(scored)[:max_sentences]
        best.sort(key=lambda item: (item[1], item[2]))  # read in document order
        lines = [f"• {sentence} [Source {source}]" for _, source, _, sentence in best]
        return DEMO_NOTICE + "\n\n" + "\n".join(lines)

    # No keyword match (e.g. "Summarize this document"): give the lead sentence of each passage,
    # which works as a rough overview across sections.
    lines = []
    for source_index, passage in enumerate(passages, start=1):
        sentences = _sentences(passage)
        if sentences:
            lines.append(f"• {sentences[0]} [Source {source_index}]")
    if not lines:
        return "Demo mode (no AI model connected): I couldn't find readable sentences in the matching passages."
    return ("Demo mode (no AI model connected): I couldn't match specific keywords, "
            "so here is an overview from the closest passages.\n\n" + "\n".join(lines[:max_sentences + 2]))
