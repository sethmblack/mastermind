"""Scratchpad service for shared working memory."""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.database import AsyncSessionLocal
from ..db.models import Scratchpad

logger = logging.getLogger(__name__)


@dataclass
class ScratchpadEntry:
    """An entry in the scratchpad."""
    key: str
    value: str
    author: Optional[str]
    version: int
    created_at: datetime
    updated_at: Optional[datetime]


class ScratchpadService:
    """
    Shared working memory service for multi-agent sessions.

    Provides a key-value store that personas can use to:
    - Store intermediate results
    - Share structured data
    - Track decisions and action items
    - Maintain a shared knowledge base

    Supports versioning for tracking changes over time.
    """

    def __init__(self, session_id: int):
        self.session_id = session_id
        self._cache: Dict[str, ScratchpadEntry] = {}

    async def get(self, key: str) -> Optional[str]:
        """Get a value from the scratchpad."""
        # Check cache first
        if key in self._cache:
            return self._cache[key].value

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Scratchpad)
                .where(
                    Scratchpad.session_id == self.session_id,
                    Scratchpad.key == key,
                )
                .order_by(Scratchpad.version.desc())
                .limit(1)
            )
            entry = result.scalar_one_or_none()

            if entry:
                self._cache[key] = ScratchpadEntry(
                    key=entry.key,
                    value=entry.value,
                    author=entry.author_persona,
                    version=entry.version,
                    created_at=entry.created_at,
                    updated_at=entry.updated_at,
                )
                return entry.value

            return None

    async def set(
        self,
        key: str,
        value: str,
        author: Optional[str] = None,
    ) -> ScratchpadEntry:
        """Set a value in the scratchpad."""
        async with AsyncSessionLocal() as db:
            # Get current version
            result = await db.execute(
                select(Scratchpad)
                .where(
                    Scratchpad.session_id == self.session_id,
                    Scratchpad.key == key,
                )
                .order_by(Scratchpad.version.desc())
                .limit(1)
            )
            existing = result.scalar_one_or_none()
            version = (existing.version + 1) if existing else 1

            # Create new entry
            entry = Scratchpad(
                session_id=self.session_id,
                key=key,
                value=value,
                author_persona=author,
                version=version,
            )
            db.add(entry)
            await db.commit()
            await db.refresh(entry)

            cached = ScratchpadEntry(
                key=entry.key,
                value=entry.value,
                author=entry.author_persona,
                version=entry.version,
                created_at=entry.created_at,
                updated_at=entry.updated_at,
            )
            self._cache[key] = cached

            logger.debug(f"Scratchpad set: {key}={value[:50]}... (v{version})")
            return cached

    async def delete(self, key: str) -> bool:
        """Delete a key from the scratchpad (marks as deleted, preserves history)."""
        return await self.set(key, "", author="system") is not None

    async def get_all(self) -> Dict[str, str]:
        """Get all current values in the scratchpad."""
        async with AsyncSessionLocal() as db:
            # Get latest version of each key
            result = await db.execute(
                select(Scratchpad)
                .where(Scratchpad.session_id == self.session_id)
                .order_by(Scratchpad.key, Scratchpad.version.desc())
            )
            entries = result.scalars().all()

            # Group by key, take latest
            latest: Dict[str, Scratchpad] = {}
            for entry in entries:
                if entry.key not in latest:
                    latest[entry.key] = entry

            return {
                key: entry.value
                for key, entry in latest.items()
                if entry.value  # Exclude deleted (empty) entries
            }

    async def get_history(self, key: str) -> List[ScratchpadEntry]:
        """Get version history for a key."""
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Scratchpad)
                .where(
                    Scratchpad.session_id == self.session_id,
                    Scratchpad.key == key,
                )
                .order_by(Scratchpad.version.desc())
            )
            entries = result.scalars().all()

            return [
                ScratchpadEntry(
                    key=e.key,
                    value=e.value,
                    author=e.author_persona,
                    version=e.version,
                    created_at=e.created_at,
                    updated_at=e.updated_at,
                )
                for e in entries
            ]

    async def append(
        self,
        key: str,
        value: str,
        author: Optional[str] = None,
        separator: str = "\n",
    ) -> ScratchpadEntry:
        """Append to an existing value."""
        existing = await self.get(key)
        if existing:
            new_value = existing + separator + value
        else:
            new_value = value
        return await self.set(key, new_value, author)

    async def increment(
        self,
        key: str,
        amount: int = 1,
        author: Optional[str] = None,
    ) -> ScratchpadEntry:
        """Increment a numeric value."""
        existing = await self.get(key)
        try:
            current = int(existing) if existing else 0
        except ValueError:
            current = 0
        return await self.set(key, str(current + amount), author)

    # Convenience methods for common patterns

    async def add_decision(self, decision: str, author: Optional[str] = None):
        """Add a decision to the decisions list."""
        return await self.append("decisions", f"- {decision}", author)

    async def add_action_item(
        self,
        action: str,
        assignee: Optional[str] = None,
        author: Optional[str] = None,
    ):
        """Add an action item."""
        item = f"- [ ] {action}"
        if assignee:
            item += f" (@{assignee})"
        return await self.append("action_items", item, author)

    async def add_key_insight(self, insight: str, author: Optional[str] = None):
        """Add a key insight."""
        return await self.append("key_insights", f"- {insight}", author)

    async def add_open_question(self, question: str, author: Optional[str] = None):
        """Add an open question."""
        return await self.append("open_questions", f"- {question}", author)

    async def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the scratchpad contents."""
        all_data = await self.get_all()

        return {
            "session_id": self.session_id,
            "entry_count": len(all_data),
            "keys": list(all_data.keys()),
            "decisions": all_data.get("decisions", "").split("\n") if all_data.get("decisions") else [],
            "action_items": all_data.get("action_items", "").split("\n") if all_data.get("action_items") else [],
            "key_insights": all_data.get("key_insights", "").split("\n") if all_data.get("key_insights") else [],
            "open_questions": all_data.get("open_questions", "").split("\n") if all_data.get("open_questions") else [],
        }

    def clear_cache(self):
        """Clear the local cache."""
        self._cache.clear()
