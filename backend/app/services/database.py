"""
Database service for SQLite connection and operations.
"""

import aiosqlite
import os
from pathlib import Path
from typing import Optional, List, Any

# Database path - relative to project root
DB_PATH = Path(__file__).parent.parent.parent.parent / "data" / "mini_lakebed.db"
SCHEMA_PATH = Path(__file__).parent.parent.parent.parent / "data" / "schema.sql"


async def get_db() -> aiosqlite.Connection:
    """Get database connection."""
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    return db


async def init_database():
    """Initialize database with schema."""
    # Ensure data directory exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    async with aiosqlite.connect(DB_PATH) as db:
        # Read and execute schema
        if SCHEMA_PATH.exists():
            with open(SCHEMA_PATH, "r") as f:
                schema = f.read()
            await db.executescript(schema)
            await db.commit()
            print(f"Database initialized at {DB_PATH}")
        else:
            print(f"Warning: Schema file not found at {SCHEMA_PATH}")


async def execute_query(query: str, params: tuple = ()) -> List[dict]:
    """Execute a SELECT query and return results as list of dicts."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def execute_one(query: str, params: tuple = ()) -> Optional[dict]:
    """Execute a SELECT query and return single result."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(query, params)
        row = await cursor.fetchone()
        return dict(row) if row else None


async def execute_insert(query: str, params: tuple = ()) -> int:
    """Execute an INSERT query and return last row id."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(query, params)
        await db.commit()
        return cursor.lastrowid


async def execute_update(query: str, params: tuple = ()) -> int:
    """Execute an UPDATE/DELETE query and return rows affected."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(query, params)
        await db.commit()
        return cursor.rowcount
