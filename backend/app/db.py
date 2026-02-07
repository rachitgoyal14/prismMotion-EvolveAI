import os
import uuid
import asyncio
import json
from typing import Optional, List, Dict
from datetime import datetime

import asyncpg


DATABASE_URL_ENV = "DATABASE_URL"

pool: Optional[asyncpg.pool.Pool] = None


async def init_db(dsn: Optional[str] = None):
    global pool
    if pool:
        return

    dsn = dsn or os.getenv(DATABASE_URL_ENV)
    if not dsn:
        raise RuntimeError("DATABASE_URL not set in environment")

    pool = await asyncpg.create_pool(dsn, min_size=5, max_size=20)

    # Create tables
    create_sql = """
    CREATE TABLE IF NOT EXISTS users (
        id UUID PRIMARY KEY,
        created_at TIMESTAMPTZ DEFAULT now()
    );

    CREATE TABLE IF NOT EXISTS sessions (
        id UUID PRIMARY KEY,
        user_id UUID REFERENCES users(id) ON DELETE CASCADE,
        video_id UUID,
        status TEXT,
        metadata JSONB,
        created_at TIMESTAMPTZ DEFAULT now()
    );

    CREATE TABLE IF NOT EXISTS videos (
        id UUID PRIMARY KEY,
        session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
        path TEXT,
        state TEXT,
        created_at TIMESTAMPTZ DEFAULT now()
    );

    CREATE TABLE IF NOT EXISTS chat_messages (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID REFERENCES users(id) ON DELETE CASCADE,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TIMESTAMPTZ DEFAULT now()
    );

    CREATE TABLE IF NOT EXISTS user_documents (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID REFERENCES users(id) ON DELETE CASCADE,
        document_id TEXT NOT NULL,
        filename TEXT,
        uploaded_at TIMESTAMPTZ DEFAULT now()
    );

    CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
    CREATE INDEX IF NOT EXISTS idx_videos_session_id ON videos(session_id);
    CREATE INDEX IF NOT EXISTS idx_chat_messages_user_id ON chat_messages(user_id);
    CREATE INDEX IF NOT EXISTS idx_chat_messages_created_at ON chat_messages(created_at);
    CREATE INDEX IF NOT EXISTS idx_chat_messages_user_created ON chat_messages(user_id, created_at DESC);
    CREATE INDEX IF NOT EXISTS idx_user_documents_user_id ON user_documents(user_id);
    """

    async with pool.acquire() as conn:
        # run as a single batch
        await conn.execute(create_sql)


async def close_db():
    global pool
    if pool:
        await pool.close()
        pool = None


async def ensure_user(user_id: Optional[str] = None) -> str:
    """Ensure a user exists. If user_id is None, generate and return new UUID."""
    global pool
    if not pool:
        raise RuntimeError("DB pool is not initialized")

    if not user_id:
        user_id = str(uuid.uuid4())

    uid = user_id
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO users (id) VALUES ($1) ON CONFLICT (id) DO NOTHING",
            uid,
        )
    return uid


async def create_session(user_id: str, video_id: str, status: str = "processing", metadata: Optional[dict] = None) -> str:
    global pool
    if not pool:
        raise RuntimeError("DB pool is not initialized")

    sid = str(uuid.uuid4())
    meta = json.dumps(metadata) if metadata is not None else None
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO sessions (id, user_id, video_id, status, metadata) VALUES ($1,$2,$3,$4,$5)",
            sid,
            user_id,
            video_id,
            status,
            meta,
        )
    return sid


async def create_video_record(video_id: str, session_id: str, path: Optional[str] = None, state: str = "processing") -> str:
    global pool
    if not pool:
        raise RuntimeError("DB pool is not initialized")

    vid = video_id
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO videos (id, session_id, path, state) VALUES ($1,$2,$3,$4) ON CONFLICT (id) DO NOTHING",
            vid,
            session_id,
            path,
            state,
        )
    return vid


async def update_video_state(video_id: str, state: Optional[str] = None, path: Optional[str] = None):
    global pool
    if not pool:
        raise RuntimeError("DB pool is not initialized")

    parts = []
    args = []
    idx = 1
    if state is not None:
        parts.append(f"state = ${idx}")
        args.append(state)
        idx += 1
    if path is not None:
        parts.append(f"path = ${idx}")
        args.append(path)
        idx += 1

    if not parts:
        return

    sql = "UPDATE videos SET " + ",".join(parts) + f" WHERE id = ${idx}"
    args.append(video_id)

    async with pool.acquire() as conn:
        await conn.execute(sql, *args)


# ==================== OPTIMIZED CHAT FUNCTIONS ====================

async def save_chat_message(user_id: str, role: str, content: str) -> str:
    """
    Save a chat message to the database.
    Returns the message ID immediately without fetching.
    """
    global pool
    if not pool:
        raise RuntimeError("DB pool is not initialized")

    msg_id = str(uuid.uuid4())
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO chat_messages (id, user_id, role, content) VALUES ($1, $2, $3, $4)",
            msg_id,
            user_id,
            role,
            content,
        )
    return msg_id


async def save_chat_messages_batch(user_id: str, messages: List[Dict[str, str]]) -> List[str]:
    """
    Save multiple chat messages in a single transaction.
    
    Args:
        user_id: User ID
        messages: List of dicts with 'role' and 'content'
    
    Returns:
        List of message IDs
    """
    global pool
    if not pool:
        raise RuntimeError("DB pool is not initialized")

    msg_ids = [str(uuid.uuid4()) for _ in messages]
    
    async with pool.acquire() as conn:
        async with conn.transaction():
            for msg_id, msg in zip(msg_ids, messages):
                await conn.execute(
                    "INSERT INTO chat_messages (id, user_id, role, content) VALUES ($1, $2, $3, $4)",
                    msg_id,
                    user_id,
                    msg["role"],
                    msg["content"],
                )
    
    return msg_ids


async def get_chat_history(
    user_id: str, 
    limit: int = 50, 
    offset: int = 0,
    after_timestamp: Optional[datetime] = None
) -> List[dict]:
    """
    Retrieve chat history for a user with pagination and optional filtering.
    
    Args:
        user_id: User ID
        limit: Maximum number of messages to retrieve
        offset: Number of messages to skip (for pagination)
        after_timestamp: Only fetch messages after this timestamp
    
    Returns:
        List of message dicts in chronological order
    """
    global pool
    if not pool:
        raise RuntimeError("DB pool is not initialized")

    if after_timestamp:
        sql = """
            SELECT role, content, created_at 
            FROM chat_messages 
            WHERE user_id = $1 AND created_at > $2
            ORDER BY created_at ASC 
            LIMIT $3
        """
        args = [user_id, after_timestamp, limit]
    else:
        sql = """
            SELECT role, content, created_at 
            FROM chat_messages 
            WHERE user_id = $1 
            ORDER BY created_at DESC 
            LIMIT $2 OFFSET $3
        """
        args = [user_id, limit, offset]

    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, *args)
    
    # Return in chronological order (oldest first)
    if after_timestamp:
        messages = [
            {
                "role": row["role"],
                "content": row["content"],
                "created_at": row["created_at"].isoformat(),
            }
            for row in rows
        ]
    else:
        messages = [
            {
                "role": row["role"],
                "content": row["content"],
                "created_at": row["created_at"].isoformat(),
            }
            for row in reversed(rows)
        ]
    
    return messages


async def get_recent_chat_messages(user_id: str, count: int = 6) -> List[dict]:
    """
    Get only the most recent N messages for context building.
    This is optimized for chat context (no full history needed).
    
    Args:
        user_id: User ID
        count: Number of recent messages to fetch
    
    Returns:
        List of recent messages in chronological order
    """
    global pool
    if not pool:
        raise RuntimeError("DB pool is not initialized")

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT role, content, created_at 
            FROM chat_messages 
            WHERE user_id = $1 
            ORDER BY created_at DESC 
            LIMIT $2
            """,
            user_id,
            count,
        )
    
    # Return in chronological order (oldest first)
    messages = [
        {
            "role": row["role"],
            "content": row["content"],
            "created_at": row["created_at"].isoformat(),
        }
        for row in reversed(rows)
    ]
    return messages


async def get_chat_message_count(user_id: str) -> int:
    """
    Get total count of messages for a user (lightweight query).
    
    Args:
        user_id: User ID
    
    Returns:
        Total message count
    """
    global pool
    if not pool:
        raise RuntimeError("DB pool is not initialized")

    async with pool.acquire() as conn:
        count = await conn.fetchval(
            "SELECT COUNT(*) FROM chat_messages WHERE user_id = $1",
            user_id,
        )
    return count or 0


async def clear_chat_history(user_id: str) -> int:
    """
    Clear all chat messages for a user.
    Returns the number of messages deleted.
    """
    global pool
    if not pool:
        raise RuntimeError("DB pool is not initialized")

    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM chat_messages WHERE user_id = $1",
            user_id,
        )
    
    # Extract count from result string "DELETE N"
    deleted_count = int(result.split()[-1]) if result else 0
    return deleted_count


async def delete_chat_messages_before(user_id: str, before_timestamp: datetime) -> int:
    """
    Delete messages older than a specific timestamp.
    Useful for cleanup/archiving.
    
    Args:
        user_id: User ID
        before_timestamp: Delete messages before this time
    
    Returns:
        Number of messages deleted
    """
    global pool
    if not pool:
        raise RuntimeError("DB pool is not initialized")

    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM chat_messages WHERE user_id = $1 AND created_at < $2",
            user_id,
            before_timestamp,
        )
    
    deleted_count = int(result.split()[-1]) if result else 0
    return deleted_count


# ==================== OPTIMIZED DOCUMENT FUNCTIONS ====================

async def save_user_document(user_id: str, document_id: str, filename: str) -> str:
    """Save document metadata for a user."""
    global pool
    if not pool:
        raise RuntimeError("DB pool is not initialized")

    doc_id = str(uuid.uuid4())
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO user_documents (id, user_id, document_id, filename) VALUES ($1, $2, $3, $4)",
            doc_id,
            user_id,
            document_id,
            filename,
        )
    return doc_id


async def get_user_documents(user_id: str, limit: int = 100) -> List[dict]:
    """
    Get all documents for a user with optional limit.
    
    Args:
        user_id: User ID
        limit: Maximum number of documents to retrieve
    
    Returns:
        List of document dicts
    """
    global pool
    if not pool:
        raise RuntimeError("DB pool is not initialized")

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT document_id, filename, uploaded_at 
            FROM user_documents 
            WHERE user_id = $1 
            ORDER BY uploaded_at DESC
            LIMIT $2
            """,
            user_id,
            limit,
        )
    
    documents = [
        {
            "document_id": row["document_id"],
            "filename": row["filename"],
            "uploaded_at": row["uploaded_at"].isoformat(),
        }
        for row in rows
    ]
    return documents


async def get_user_document_count(user_id: str) -> int:
    """
    Get count of documents for a user (lightweight).
    
    Args:
        user_id: User ID
    
    Returns:
        Total document count
    """
    global pool
    if not pool:
        raise RuntimeError("DB pool is not initialized")

    async with pool.acquire() as conn:
        count = await conn.fetchval(
            "SELECT COUNT(*) FROM user_documents WHERE user_id = $1",
            user_id,
        )
    return count or 0


async def has_user_documents(user_id: str) -> bool:
    """
    Check if user has any documents uploaded (optimized EXISTS query).
    
    Args:
        user_id: User ID
    
    Returns:
        True if user has documents
    """
    global pool
    if not pool:
        raise RuntimeError("DB pool is not initialized")

    async with pool.acquire() as conn:
        exists = await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM user_documents WHERE user_id = $1 LIMIT 1)",
            user_id,
        )
    return exists or False


async def delete_user_documents(user_id: str) -> int:
    """
    Delete all document records for a user.
    Returns the number of documents deleted.
    """
    global pool
    if not pool:
        raise RuntimeError("DB pool is not initialized")

    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM user_documents WHERE user_id = $1",
            user_id,
        )
    
    deleted_count = int(result.split()[-1]) if result else 0
    return deleted_count


async def delete_user_document_by_id(user_id: str, document_id: str) -> bool:
    """
    Delete a specific document by ID.
    
    Args:
        user_id: User ID
        document_id: Document ID to delete
    
    Returns:
        True if document was deleted
    """
    global pool
    if not pool:
        raise RuntimeError("DB pool is not initialized")

    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM user_documents WHERE user_id = $1 AND document_id = $2",
            user_id,
            document_id,
        )
    
    deleted_count = int(result.split()[-1]) if result else 0
    return deleted_count > 0