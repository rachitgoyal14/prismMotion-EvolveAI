import io
from typing import BinaryIO
from PyPDF2 import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter


class DocumentProcessor:
    """Handles document text extraction and chunking."""
    
    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
    
    def extract_text_from_pdf(self, file: BinaryIO) -> str:
        try:
            # 🔥 Convert bytes → file-like object if needed
            if isinstance(file, bytes):
                file = io.BytesIO(file)

            file.seek(0)  # Always reset pointer

            pdf_reader = PdfReader(file)
            text_parts = []

            for page in pdf_reader.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)

            full_text = "\n\n".join(text_parts)
            return full_text.strip()

        except Exception as e:
            raise ValueError(f"Failed to extract text from PDF: {str(e)}")

    
    def chunk_text(self, text: str) -> list[str]:
        """
        Split text into chunks for vectorization.
        
        Args:
            text: Full document text
            
        Returns:
            List of text chunks
        """
        if not text or not text.strip():
            return []
        
        chunks = self.text_splitter.split_text(text)
        return chunks
    
    def process_document(self, file: BinaryIO, filename: str) -> tuple[str, list[str]]:
        """
        Process document: extract text and chunk it.
        
        Args:
            file: Binary file object
            filename: Name of the file
            
        Returns:
            Tuple of (full_text, chunks)
        """
        # Determine file type and extract text
        if filename.lower().endswith('.pdf'):
            full_text = self.extract_text_from_pdf(file)
        else:
            raise ValueError(f"Unsupported file type: {filename}")
        
        if not full_text:
            raise ValueError("No text could be extracted from the document")
        
        # Chunk the text
        chunks = self.chunk_text(full_text)
        
        if not chunks:
            raise ValueError("Document chunking failed")
        
        return full_text, chunks