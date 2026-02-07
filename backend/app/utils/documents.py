import io
import logging
from typing import Union

logger = logging.getLogger(__name__)


def extract_documents_text(files: list | None) -> str:
    """Extract text from uploaded document files (PDF, DOCX, TXT).
    
    Args:
        files: List of UploadFile-like objects or None
        
    Returns:
        Concatenated text from all documents, or empty string if no valid files
    """
    if not files or not isinstance(files, list):
        return ""
    
    texts = []

    for file in files:
        # Skip strings
        if isinstance(file, str):
            continue
        
        # ✅ Check if it has the UploadFile interface (duck typing)
        if not hasattr(file, 'filename') or not hasattr(file, 'file'):
            continue
        
        if not file.filename:
            continue
        
        logger.info(f"  Processing document: {file.filename}")
        
        # Ensure we're reading from the start
        try:
            file.file.seek(0)
        except Exception as e:
            logger.warning(f"  Failed to seek {file.filename}: {e}")
            continue

        try:
            content = file.file.read()
            logger.info(f"  Read {len(content)} bytes from {file.filename}")
        except Exception as e:
            logger.warning(f"  Failed to read {file.filename}: {e}")
            continue

        if not content:
            logger.warning(f"  Empty content in {file.filename}")
            continue

        # Reset pointer
        try:
            file.file.seek(0)
        except Exception:
            pass

        # Process based on file extension
        filename_lower = file.filename.lower()
        
        if filename_lower.endswith(".txt"):
            try:
                text = content.decode("utf-8")
                texts.append(text)
                logger.info(f"  ✓ Extracted {len(text)} chars from TXT")
            except Exception as e:
                logger.warning(f"  Failed to decode txt {file.filename}: {e}")

        elif filename_lower.endswith(".pdf"):
            try:
                from pypdf import PdfReader
                reader = PdfReader(io.BytesIO(content))
                pdf_text = "\n".join(page.extract_text() or "" for page in reader.pages)
                if pdf_text.strip():
                    texts.append(pdf_text)
                    logger.info(f"  ✓ Extracted {len(pdf_text)} chars from PDF ({len(reader.pages)} pages)")
                else:
                    logger.warning(f"  PDF {file.filename} had no extractable text")
            except Exception as e:
                logger.warning(f"  Failed to parse PDF {file.filename}: {e}")

        elif filename_lower.endswith(".docx"):
            try:
                from docx import Document
                doc = Document(io.BytesIO(content))
                docx_text = "\n".join(p.text for p in doc.paragraphs)
                if docx_text.strip():
                    texts.append(docx_text)
                    logger.info(f"  ✓ Extracted {len(docx_text)} chars from DOCX")
                else:
                    logger.warning(f"  DOCX {file.filename} had no text")
            except Exception as e:
                logger.warning(f"  Failed to parse DOCX {file.filename}: {e}")

    combined_text = "\n\n".join(texts)
    logger.info(f"extract_documents_text: Returning {len(combined_text)} total characters from {len(texts)} documents")
    
    return combined_text