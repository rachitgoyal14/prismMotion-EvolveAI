import os
import uuid
import asyncio
import json
from typing import Optional

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

    pool = await asyncpg.create_pool(dsn)

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

    CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
    CREATE INDEX IF NOT EXISTS idx_videos_session_id ON videos(session_id);
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
