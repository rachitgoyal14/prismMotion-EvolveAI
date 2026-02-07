"""
Chat module for RAG-based chat service.
Provides document upload, vectorization, and question answering.
"""

from app.chat.routes import router

__all__ = ["router"]