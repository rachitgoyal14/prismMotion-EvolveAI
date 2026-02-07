from typing import Optional, List
from langchain_groq import ChatGroq
from dotenv import load_dotenv

load_dotenv()


class ChatService:
    """Orchestrates chat interactions with RAG and LLM."""
    
    # Summary keywords
    SUMMARY_KEYWORDS = [
        "summarize",
        "summary",
        "explain",
        "overview",
        "what is this document about",
        "key points",
        "gist",
        "eli5",
        "brief",
        "outline"
    ]
    
    def __init__(self):
        """Initialize chat service with LLM."""
        self.llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            temperature=0.2,
            max_tokens=512,
            timeout=30,
            max_retries=2,
        )
    
    def is_summary_question(self, question: str) -> bool:
        """
        Check if the question is asking for a summary.
        
        Args:
            question: User's question
            
        Returns:
            Whether it's a summary question
        """
        q = question.lower()
        return any(keyword in q for keyword in self.SUMMARY_KEYWORDS)
    
    def build_conversation_history(self, messages: List[dict]) -> str:
        """
        Build conversation context from message history.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            
        Returns:
            Formatted conversation history
        """
        if not messages:
            return ""
        
        # Take last 6 messages for context window management
        recent_messages = messages[-6:]
        
        history = []
        for msg in recent_messages:
            role = msg["role"].capitalize()
            content = msg["content"]
            history.append(f"{role}: {content}")
        
        return "\n".join(history)
    
    def generate_answer(
        self,
        question: str,
        retrieved_docs: Optional[List[str]] = None,
        conversation_history: Optional[str] = None
    ) -> str:
        """
        Generate an answer using LLM with optional RAG context.
        
        Args:
            question: User's question
            retrieved_docs: Retrieved document chunks from RAG
            conversation_history: Formatted conversation history
            
        Returns:
            Generated answer
        """
        if not question or not question.strip():
            return "No valid question could be determined."
        
        is_summary = self.is_summary_question(question)
        
        # RAG: Document-based answering
        if retrieved_docs:
            if not retrieved_docs:
                return "I don't know."
            
            doc_context = "\n".join(retrieved_docs)
            
            # Build conversation prefix
            conv_prefix = ""
            if conversation_history:
                conv_prefix = f"Previous conversation:\n{conversation_history}\n\n"
            
            # Build prompt based on summary or specific question
            if is_summary:
                prompt = f"""
You are an educational assistant.
Using ONLY the document content below, answer the user's request.
You may summarize, explain, or reorganize the information,
but do NOT add information not present in the document.

{conv_prefix}Document:
{doc_context}

Task:
{question}

Answer:
"""
            else:
                prompt = f"""
You are an educational assistant.
Answer the question ONLY using the context below.
If the answer is not present in the context, reply with:
"I don't know."

{conv_prefix}Context:
{doc_context}

Question:
{question}

Answer:
"""
        
        # No document: general question with conversation history
        else:
            if conversation_history:
                prompt = f"""
You are an educational assistant engaged in a conversation with a student.

Previous conversation:
{conversation_history}

Current question:
{question}

Provide a clear, concise, and helpful answer based on the conversation context.

Answer:
"""
            else:
                prompt = f"""
Answer the following question clearly and concisely.

Question:
{question}

Answer:
"""
        
        # Generate response
        response = self.llm.invoke(prompt)
        return response.content.strip()
    
    def answer_question(
        self,
        question: str,
        retrieved_docs: Optional[List[str]] = None,
        chat_history: Optional[List[dict]] = None
    ) -> str:
        """
        Main method to answer a question with RAG and chat history.
        
        Args:
            question: User's question
            retrieved_docs: Retrieved documents from RAG (if available)
            chat_history: Previous chat messages
            
        Returns:
            Generated answer
        """
        # Build conversation history
        conversation_history = None
        if chat_history:
            conversation_history = self.build_conversation_history(chat_history)
        
        # Generate answer
        answer = self.generate_answer(
            question=question,
            retrieved_docs=retrieved_docs,
            conversation_history=conversation_history
        )
        
        return answer