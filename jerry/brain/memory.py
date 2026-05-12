"""
Jerry's Memory System
SQLite-backed conversation storage with short-term and long-term memory.
Jerry remembers conversations and learns about the user over time.
"""

import sqlite3
import datetime
import logging
from typing import Optional, List, Dict

logger = logging.getLogger("jerry.memory")


class Memory:
    """Jerry's memory -- persistent conversation and user fact storage."""

    def __init__(self, db_path: str = "jerry_memory.db", short_term_limit: int = 20):
        """
        Initialize Jerry's memory system.

        Args:
            db_path: Path to SQLite database file (or ':memory:' for testing)
            short_term_limit: Max messages to keep in short-term context
        """
        self.db_path = db_path
        self.short_term_limit = short_term_limit
        self.current_messages: List[Dict[str, str]] = []
        self.session_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

        # Use a persistent connection so :memory: databases survive
        self._conn = sqlite3.connect(self.db_path)
        self._init_db()
        logger.info(f"Memory initialized. Session: {self.session_id}")

    def _get_conn(self) -> sqlite3.Connection:
        """Return the persistent database connection."""
        return self._conn

    def _init_db(self):
        """Create database tables if they don't exist."""
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                fact TEXT NOT NULL,
                source TEXT,
                confidence REAL DEFAULT 1.0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                summary TEXT NOT NULL,
                message_count INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()

    def add_message(self, role: str, content: str):
        """
        Add a message to memory.

        Args:
            role: 'user' or 'assistant'
            content: Message content
        """
        message = {"role": role, "content": content}
        self.current_messages.append(message)

        conn = self._get_conn()
        conn.execute(
            "INSERT INTO conversations (session_id, role, content) VALUES (?, ?, ?)",
            (self.session_id, role, content),
        )
        conn.commit()

    def get_context_messages(self) -> List[Dict[str, str]]:
        """
        Get messages for LLM context, respecting the short-term limit.

        Returns:
            List of recent messages within the context window
        """
        if len(self.current_messages) <= self.short_term_limit:
            return list(self.current_messages)

        # Keep first 2 messages (for context) + most recent ones
        first_two = self.current_messages[:2]
        recent = self.current_messages[-(self.short_term_limit - 2):]
        return first_two + recent

    def add_user_fact(self, category: str, fact: str, source: str = "conversation"):
        """
        Remember something about the user.

        Args:
            category: Category (e.g., 'preference', 'hobby', 'work', 'personal')
            fact: The fact to remember
            source: Where this fact came from
        """
        conn = self._get_conn()
        existing = conn.execute(
            "SELECT id FROM user_facts WHERE category = ? AND fact = ?",
            (category, fact),
        ).fetchone()

        if existing:
            conn.execute(
                "UPDATE user_facts SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (existing[0],),
            )
        else:
            conn.execute(
                "INSERT INTO user_facts (category, fact, source) VALUES (?, ?, ?)",
                (category, fact, source),
            )
        conn.commit()
        logger.info(f"Remembered: [{category}] {fact}")

    def get_user_facts(self, category: Optional[str] = None) -> List[Dict[str, str]]:
        """
        Retrieve stored user facts.

        Args:
            category: Optional filter by category

        Returns:
            List of user facts
        """
        conn = self._get_conn()
        if category:
            rows = conn.execute(
                "SELECT category, fact, source, created_at FROM user_facts WHERE category = ? ORDER BY updated_at DESC",
                (category,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT category, fact, source, created_at FROM user_facts ORDER BY updated_at DESC",
            ).fetchall()

        return [
            {"category": r[0], "fact": r[1], "source": r[2], "created_at": r[3]}
            for r in rows
        ]

    def get_past_summaries(self, limit: int = 5) -> List[str]:
        """
        Get summaries of past conversation sessions.

        Args:
            limit: Max number of summaries to return

        Returns:
            List of conversation summaries
        """
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT summary, created_at FROM conversation_summaries ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()

        return [f"[{r[1]}] {r[0]}" for r in rows]

    def save_session_summary(self, summary: str):
        """
        Save a summary of the current conversation session.

        Args:
            summary: Summary text
        """
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO conversation_summaries (session_id, summary, message_count) VALUES (?, ?, ?)",
            (self.session_id, summary, len(self.current_messages)),
        )
        conn.commit()
        truncated = summary[:80]
        logger.info(f"Session summary saved: {truncated}...")

    def get_memory_context(self) -> str:
        """
        Build a memory context string for the LLM.
        Includes user facts and recent session summaries.

        Returns:
            Formatted memory context string
        """
        context_parts: List[str] = []

        # User facts
        facts = self.get_user_facts()
        if facts:
            context_parts.append("## Things I Remember About You")
            for fact in facts[:15]:  # Limit to avoid context overflow
                cat = fact["category"]
                f = fact["fact"]
                context_parts.append(f"- [{cat}] {f}")

        # Past conversation summaries
        summaries = self.get_past_summaries(limit=3)
        if summaries:
            context_parts.append("\n## Recent Conversation History")
            for s in summaries:
                context_parts.append(f"- {s}")

        return "\n".join(context_parts) if context_parts else ""

    def get_stats(self) -> Dict[str, int]:
        """Get memory statistics."""
        conn = self._get_conn()
        total_messages = conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
        total_sessions = conn.execute("SELECT COUNT(DISTINCT session_id) FROM conversations").fetchone()[0]
        total_facts = conn.execute("SELECT COUNT(*) FROM user_facts").fetchone()[0]
        total_summaries = conn.execute("SELECT COUNT(*) FROM conversation_summaries").fetchone()[0]

        return {
            "total_messages": total_messages,
            "total_sessions": total_sessions,
            "user_facts": total_facts,
            "summaries": total_summaries,
            "current_session_messages": len(self.current_messages),
        }

    def clear_current_session(self):
        """Clear current session messages (not the database)."""
        self.current_messages.clear()

    def close(self):
        """Close the database connection."""
        if self._conn:
            self._conn.close()
