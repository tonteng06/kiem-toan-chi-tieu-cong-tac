from dataclasses import dataclass


@dataclass
class Document:
    doc_id: str
    title: str
    version: str
    date: str
    owner: str
    content: str


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    title: str
    version: str
    date: str
    owner: str
    content: str


@dataclass
class SearchResult:
    chunk: Chunk
    score: float
    mode: str
    dense_score: float | None = None
    bm25_score: float | None = None
