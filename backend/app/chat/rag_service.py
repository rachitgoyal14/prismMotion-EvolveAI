import os
import shutil
from typing import Optional, List
from langchain_chroma import Chroma
from langchain_nomic import NomicEmbeddings
from langchain_core.documents import Document


class RAGService:
    """Handles vector database operations and document retrieval."""
    
    def __init__(self, vector_db_dir: str):
        """
        Initialize RAG service.
        
        Args:
            vector_db_dir: Directory to persist vector database
        """
        self.vector_db_dir = vector_db_dir
        self.embedding_function = NomicEmbeddings(
            model="nomic-embed-text-v1.5",
        )
        
        # Ensure directory exists
        os.makedirs(vector_db_dir, exist_ok=True)
    
    def _get_collection_name(self, user_id: str) -> str:
        """Get collection name for a user."""
        return f"user_{user_id}"
    
    def vectorize_documents(self, user_id: str, chunks: List[str]) -> bool:
        """
        Vectorize and store document chunks for a user.
        
        Args:
            user_id: User ID
            chunks: List of text chunks
            
        Returns:
            Success status
        """
        try:
            collection_name = self._get_collection_name(user_id)
            
            # Create Document objects
            documents = [
                Document(page_content=chunk, metadata={"user_id": user_id})
                for chunk in chunks
            ]
            
            # Create or update vector store
            vector_db = Chroma.from_documents(
                documents=documents,
                embedding=self.embedding_function,
                collection_name=collection_name,
                persist_directory=self.vector_db_dir,
            )
            
            return True
        
        except Exception as e:
            print(f"Vectorization error: {str(e)}")
            return False
    
    def add_documents(self, user_id: str, chunks: List[str]) -> bool:
        """
        Add more documents to existing user collection.
        
        Args:
            user_id: User ID
            chunks: List of text chunks
            
        Returns:
            Success status
        """
        try:
            collection_name = self._get_collection_name(user_id)
            
            # Get existing vector store
            vector_db = Chroma(
                collection_name=collection_name,
                embedding_function=self.embedding_function,
                persist_directory=self.vector_db_dir,
            )
            
            # Create Document objects
            documents = [
                Document(page_content=chunk, metadata={"user_id": user_id})
                for chunk in chunks
            ]
            
            # Add documents
            vector_db.add_documents(documents)
            
            return True
        
        except Exception as e:
            print(f"Add documents error: {str(e)}")
            # If collection doesn't exist, create it
            return self.vectorize_documents(user_id, chunks)
    
    def retrieve_documents(
        self,
        user_id: str,
        query: str,
        k: int = 12,
        score_threshold: float = 0.6,
        is_summary: bool = False
    ) -> List[str]:
        """
        Retrieve relevant documents for a query.
        
        Args:
            user_id: User ID
            query: Search query
            k: Number of documents to retrieve
            score_threshold: Maximum similarity score (lower is better)
            is_summary: Whether this is a summary request
            
        Returns:
            List of relevant document contents
        """
        try:
            collection_name = self._get_collection_name(user_id)
            
            # Get vector store
            vector_db = Chroma(
                collection_name=collection_name,
                embedding_function=self.embedding_function,
                persist_directory=self.vector_db_dir,
            )
            
            # Perform similarity search
            docs_with_score = vector_db.similarity_search_with_score(query, k=k)
            
            # Debug logging
            print(f"Collection: {collection_name}")
            print(f"Query: {query}")
            print(f"Docs retrieved: {len(docs_with_score)}")
            for _, score in docs_with_score:
                print(f"Similarity score: {score}")
            
            # Filter by score threshold
            if is_summary:
                # For summaries, take all retrieved docs
                docs = [doc for doc, _ in docs_with_score]
            else:
                # For specific questions, filter by threshold
                docs = [doc for doc, score in docs_with_score if score < score_threshold]
            
            # Extract content
            return [doc.page_content for doc in docs]
        
        except Exception as e:
            print(f"Retrieval error: {str(e)}")
            return []
    
    def collection_exists(self, user_id: str) -> bool:
        """
        Check if a user has a vector collection.
        
        Args:
            user_id: User ID
            
        Returns:
            Whether collection exists
        """
        try:
            collection_name = self._get_collection_name(user_id)
            vector_db = Chroma(
                collection_name=collection_name,
                embedding_function=self.embedding_function,
                persist_directory=self.vector_db_dir,
            )
            # Try to get collection
            collection = vector_db._collection
            return collection is not None
        except:
            return False
    
    def delete_user_vectors(self, user_id: str) -> bool:
        """
        Delete all vectors for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Success status
        """
        try:
            collection_name = self._get_collection_name(user_id)
            
            # Delete the collection
            vector_db = Chroma(
                collection_name=collection_name,
                embedding_function=self.embedding_function,
                persist_directory=self.vector_db_dir,
            )
            vector_db.delete_collection()
            
            return True
        except Exception as e:
            print(f"Delete vectors error: {str(e)}")
            return False