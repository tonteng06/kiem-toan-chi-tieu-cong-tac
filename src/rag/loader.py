from pathlib import Path

from src.models.document import Document


REQUIRED_METADATA = {
    "doc_id",
    "title",
    "version",
    "date",
    "owner",
}


def load_document(file_path: str | Path) -> Document:
    path = Path(file_path)

    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    if len(lines) < 5:
        raise ValueError(f"Invalid policy file: {path}")

    metadata: dict[str, str] = {}

    for line in lines[:5]:
        if ":" not in line:
            raise ValueError(f"Invalid metadata line in {path}: {line}")

        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip()

    missing = REQUIRED_METADATA - metadata.keys()

    if missing:
        raise ValueError(
            f"Missing metadata in {path}: {sorted(missing)}"
        )

    content = "\n".join(lines[5:]).strip()

    return Document(
        doc_id=metadata["doc_id"],
        title=metadata["title"],
        version=metadata["version"],
        date=metadata["date"],
        owner=metadata["owner"],
        content=content,
    )


def load_documents(folder: str | Path) -> list[Document]:
    folder_path = Path(folder)

    policy_files = sorted(folder_path.glob("*.txt"))

    return [
        load_document(file_path)
        for file_path in policy_files
    ]
