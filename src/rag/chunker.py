from src.models.document import Chunk, Document


DEFAULT_CHUNK_SIZE = 500
DEFAULT_OVERLAP = 100


def chunk_document(
    document: Document,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> list[Chunk]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")

    if overlap < 0:
        raise ValueError("overlap must not be negative")

    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    chunks: list[Chunk] = []

    start = 0
    chunk_number = 1

    while start < len(document.content):
        end = start + chunk_size

        chunk_content = document.content[start:end].strip()

        if chunk_content:
            chunk = Chunk(
                chunk_id=f"{document.doc_id}_CH{chunk_number:03d}",
                doc_id=document.doc_id,
                title=document.title,
                version=document.version,
                date=document.date,
                owner=document.owner,
                content=chunk_content,
            )

            chunks.append(chunk)
            chunk_number += 1

        start += chunk_size - overlap

    return chunks


def chunk_documents(
    documents: list[Document],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> list[Chunk]:
    chunks: list[Chunk] = []

    for document in documents:
        chunks.extend(
            chunk_document(
                document=document,
                chunk_size=chunk_size,
                overlap=overlap,
            )
        )

    return chunks
