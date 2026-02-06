import io
from fastapi import UploadFile


def extract_documents_text(files: list[UploadFile]) -> str:
    texts = []

    for file in files:
        content = file.file.read()

        if file.filename.endswith(".txt"):
            texts.append(content.decode("utf-8"))

        elif file.filename.endswith(".pdf"):
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(content))
            texts.append(
                "\n".join(page.extract_text() or "" for page in reader.pages)
            )

        elif file.filename.endswith(".docx"):
            from docx import Document
            doc = Document(io.BytesIO(content))
            texts.append("\n".join(p.text for p in doc.paragraphs))

    return "\n\n".join(texts)
