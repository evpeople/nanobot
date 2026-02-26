"""Memory service for nanobot AI girlfriend."""

from datetime import datetime
from typing import Any, Optional
from zoneinfo import ZoneInfo

from nanobot.memory.client import OpenVikingClient
from nanobot.memory.config import MemoryConfig


class MemoryService:
    """Memory service core class.

    Handles message storage, commit logic, and memory retrieval.
    """

    def __init__(self, config: MemoryConfig, client: OpenVikingClient):
        self.config = config
        self.client = client
        self._message_count: dict[str, int] = {}  # {session_id: count}

    async def initialize(self) -> None:
        """Initialize the memory service."""
        await self.client.initialize()

    async def add_message(self, session_id: str, role: str, content: str) -> None:
        """Add a message to the session.

        Args:
            session_id: Session identifier
            role: Message role (user/assistant)
            content: Message content
        """
        # Add timestamp prefix if enabled
        if self.config.timestamp_enabled:
            tz = ZoneInfo(self.config.timestamp_timezone)
            timestamp = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
            content = f"[{timestamp}] {content}"

        await self.client.add_message(session_id, role, content)

        # Check threshold to trigger commit
        self._message_count[session_id] = self._message_count.get(session_id, 0) + 1
        if self.config.auto_commit:
            if self._message_count[session_id] >= self.config.commit_threshold:
                await self.commit(session_id)

    async def commit(self, session_id: str) -> None:
        """Manually trigger commit to extract memories.

        Args:
            session_id: Session identifier
        """
        await self.client.commit_session(session_id)
        await self.client.wait_processed()
        self._message_count[session_id] = 0

    def should_trigger_search(self, message: str) -> bool:
        """Determine if memory search should be triggered.

        Args:
            message: User message to check

        Returns:
            True if search should be triggered
        """
        if self.config.retrieval_strategy == "always":
            return True
        if self.config.retrieval_strategy == "never":
            return False

        # keyword strategy
        triggers = self.config.keyword_triggers.split(",")
        skips = self.config.keyword_skips.split(",")

        if any(s in message for s in skips):
            return False
        return any(t in message for t in triggers)

    async def search(self, session_id: str, query: str, limit: Optional[int] = None) -> Any:
        """Semantic search for memories.

        Args:
            session_id: Session identifier
            query: Search query
            limit: Maximum results (defaults to config.search_limit)

        Returns:
            Search results
        """
        limit = limit or self.config.search_limit
        return await self.client.find(
            query=query,
            target_uri="viking://user/memories",
            limit=limit,
        )

    async def close(self) -> None:
        """Close the memory service."""
        await self.client.close()
