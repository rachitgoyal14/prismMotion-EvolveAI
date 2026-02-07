from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class ChatMessage(BaseModel):
    role: str = Field(..., description="Role of the message sender (user/assistant)")
    content: str = Field(..., description="Message content")
    created_at: Optional[str] = None


class ChatSendRequest(BaseModel):
    user_id: str = Field(..., description="User ID")
    message: str = Field(..., description="User's message/question")
    use_rag: bool = Field(default=True, description="Whether to use RAG for this query")


class ChatSendResponse(BaseModel):
    answer: str = Field(..., description="Assistant's response")
    role: str = Field(default="assistant", description="Response role")
    success: bool = Field(default=True)


class ChatHistoryResponse(BaseModel):
    messages: List[ChatMessage]
    total: int


class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    success: bool
    message: str


class ClearChatResponse(BaseModel):
    success: bool
    message: str


class DocumentInfo(BaseModel):
    document_id: str
    filename: str
    uploaded_at: str


class UserDocumentsResponse(BaseModel):
    documents: List[DocumentInfo]
    total: int