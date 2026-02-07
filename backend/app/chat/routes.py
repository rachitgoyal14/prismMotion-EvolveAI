import os
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from typing import Optional
import uuid

# Import local modules (adjust import paths based on your structure)
from app.chat.models import (
    ChatSendRequest,
    ChatSendResponse,
    ChatHistoryResponse,
    DocumentUploadResponse,
    ClearChatResponse,
    UserDocumentsResponse,
    ChatMessage,
    DocumentInfo
)
from app.chat.document_processor import DocumentProcessor
from app.chat.rag_service import RAGService
from app.chat.service import ChatService
from app import db

# Configuration
VECTOR_DB_DIR = os.getenv("VECTOR_DB_DIR", "./app/vector_db")

# Initialize services
document_processor = DocumentProcessor()
rag_service = RAGService(vector_db_dir=VECTOR_DB_DIR)
chat_service = ChatService()

# Create router
router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/upload-document", response_model=DocumentUploadResponse)
async def upload_document(
    user_id: str,
    file: UploadFile = File(...)
):
    """
    Upload and vectorize a document for RAG.
    
    Args:
        user_id: User ID
        file: PDF document file
        
    Returns:
        Document upload confirmation with document_id
    """
    try:
        # Ensure user exists
        await db.ensure_user(user_id)
        
        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=400,
                detail="Only PDF files are supported"
            )
        
        # Read file content
        content = await file.read()
        
        # Process document
        try:
            full_text, chunks = document_processor.process_document(
                file=content,
                filename=file.filename
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        
        # Generate document ID
        document_id = str(uuid.uuid4())
        
        # Vectorize and store
        success = rag_service.add_documents(user_id, chunks)
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to vectorize document"
            )
        
        # Save document metadata to DB
        await db.save_user_document(
            user_id=user_id,
            document_id=document_id,
            filename=file.filename
        )
        
        return DocumentUploadResponse(
            document_id=document_id,
            filename=file.filename,
            success=True,
            message=f"Document '{file.filename}' uploaded and vectorized successfully"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Upload failed: {str(e)}"
        )


@router.post("/send", response_model=ChatSendResponse)
async def send_message(request: ChatSendRequest):
    """
    Send a chat message and get a response.
    
    Args:
        request: Chat message request with user_id and message
        
    Returns:
        Assistant's response
    """
    try:
        # Ensure user exists
        await db.ensure_user(request.user_id)
        
        # Get chat history
        chat_history = await db.get_chat_history(request.user_id, limit=50)
        
        # Check if user has documents and should use RAG
        retrieved_docs = None
        if request.use_rag:
            has_docs = await db.has_user_documents(request.user_id)
            
            if has_docs:
                # Determine if it's a summary question
                is_summary = chat_service.is_summary_question(request.message)
                
                # Retrieve relevant documents
                retrieval_query = (
                    "summary of the document" if is_summary else request.message
                )
                
                retrieved_docs = rag_service.retrieve_documents(
                    user_id=request.user_id,
                    query=retrieval_query,
                    k=12,
                    score_threshold=0.6,
                    is_summary=is_summary
                )
        
        # Generate answer
        answer = chat_service.answer_question(
            question=request.message,
            retrieved_docs=retrieved_docs,
            chat_history=chat_history
        )
        
        # Save user message to DB
        await db.save_chat_message(
            user_id=request.user_id,
            role="user",
            content=request.message
        )
        
        # Save assistant response to DB
        await db.save_chat_message(
            user_id=request.user_id,
            role="assistant",
            content=answer
        )
        
        return ChatSendResponse(
            answer=answer,
            role="assistant",
            success=True
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Chat error: {str(e)}"
        )


@router.get("/history/{user_id}", response_model=ChatHistoryResponse)
async def get_history(user_id: str, limit: int = 50):
    """
    Get chat history for a user.
    
    Args:
        user_id: User ID
        limit: Maximum number of messages to retrieve
        
    Returns:
        Chat history
    """
    try:
        # Ensure user exists
        await db.ensure_user(user_id)
        
        # Get history
        messages = await db.get_chat_history(user_id, limit=limit)
        
        # Convert to ChatMessage models
        chat_messages = [
            ChatMessage(
                role=msg["role"],
                content=msg["content"],
                created_at=msg["created_at"]
            )
            for msg in messages
        ]
        
        return ChatHistoryResponse(
            messages=chat_messages,
            total=len(chat_messages)
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve history: {str(e)}"
        )


@router.delete("/clear/{user_id}", response_model=ClearChatResponse)
async def clear_chat(user_id: str):
    """
    Clear chat history and vectors for a user.
    
    Args:
        user_id: User ID
        
    Returns:
        Confirmation of deletion
    """
    try:
        # Clear chat history
        await db.clear_chat_history(user_id)
        
        # Clear vectors
        rag_service.delete_user_vectors(user_id)
        
        # Clear document metadata
        await db.delete_user_documents(user_id)
        
        return ClearChatResponse(
            success=True,
            message="Chat history and documents cleared successfully"
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear chat: {str(e)}"
        )


@router.get("/documents/{user_id}", response_model=UserDocumentsResponse)
async def get_user_documents(user_id: str):
    """
    Get all documents uploaded by a user.
    
    Args:
        user_id: User ID
        
    Returns:
        List of user documents
    """
    try:
        # Ensure user exists
        await db.ensure_user(user_id)
        
        # Get documents
        docs = await db.get_user_documents(user_id)
        
        # Convert to DocumentInfo models
        documents = [
            DocumentInfo(
                document_id=doc["document_id"],
                filename=doc["filename"],
                uploaded_at=doc["uploaded_at"]
            )
            for doc in docs
        ]
        
        return UserDocumentsResponse(
            documents=documents,
            total=len(documents)
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve documents: {str(e)}"
        )