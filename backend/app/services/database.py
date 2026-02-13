"""
Database service for SQLite connection and operations.

T05: Added payload hashing for audit log integrity.
"""

import aiosqlite
import os
import logging
from pathlib import Path
from typing import Optional, List, Any, Dict

from app.services.audit_hasher import get_audit_hasher, create_audit_entry

logger = logging.getLogger(__name__)

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


async def log_audit_entry(
    actor: str,
    event_type: str,
    payload: Dict[str, Any],
    regulatory_flags: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None
) -> int:
    """
    T05: Log audit entry with payload hash for tamper evidence.

    Per spec §5: Creates SHA-256 hash of payload for immutability verification.

    Args:
        actor: User or system that performed the action
        event_type: Type of event (e.g., "deal_created", "price_changed")
        payload: Data associated with the event
        regulatory_flags: Regulatory compliance flags (optional)
        session_id: Optional session ID for session-related entries

    Returns:
        ID of the inserted audit log entry
    """
    entry = create_audit_entry(
        actor=actor,
        event_type=event_type,
        payload=payload,
        regulatory_flags=regulatory_flags
    )

    logger.info(
        f"Audit log: {event_type} by {actor}, hash={entry['payload_hash'][:16]}..."
    )

    # Insert into audit_logs table
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO audit_logs (
                session_id, transaction_id, timestamp, actor, event_type,
                payload_hash, previous_hash, regulatory_flags
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                entry["transaction_id"],
                entry["timestamp"],
                entry["actor"],
                entry["event_type"],
                entry["payload_hash"],
                entry.get("previous_hash"),
                entry["regulatory_flags"]
            )
        )
        await db.commit()
        return cursor.lastrowid


async def get_audit_chain(limit: int = 100) -> List[Dict[str, Any]]:
    """
    T05: Retrieve audit log chain for integrity verification.

    Args:
        limit: Maximum number of entries to retrieve

    Returns:
        List of audit entries in chronological order
    """
    return await execute_query(
        """
        SELECT transaction_id, timestamp, actor, event_type,
               payload_hash, previous_hash, regulatory_flags
        FROM audit_logs
        ORDER BY id ASC
        LIMIT ?
        """,
        (limit,)
    )


async def verify_audit_chain() -> bool:
    """
    T05: Verify audit log chain integrity.

    Each entry's previous_hash should match the prior entry's payload_hash.

    Returns:
        True if chain is valid, False if tampered
    """
    hasher = get_audit_hasher()
    entries = await get_audit_chain()
    return hasher.verify_chain_from_dicts(entries)
