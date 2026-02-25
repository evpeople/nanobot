"""OpenViking client wrapper for memory service."""

import threading
from typing import Any, Dict, Optional

from openviking import AsyncOpenViking


class OpenVikingClient:
    """OpenViking client wrapper for memory service.

    This is a singleton wrapper around AsyncOpenViking for use in the
    memory service. It provides thread-safe lazy initialization and
    proper cleanup capabilities.
    """

    _instance: Optional["OpenVikingClient"] = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = object.__new__(cls)
        return cls._instance

    def __init__(self, storage_path: Optional[str] = None):
        # Singleton guard for repeated initialization
        if hasattr(self, "_singleton_initialized") and self._singleton_initialized:
            return

        self.storage_path = storage_path or "~/.nanobot/openviking"
        self.client = AsyncOpenViking(path=self.storage_path)
        self._initialized = False
        self._singleton_initialized = True

    async def initialize(self) -> None:
        """Initialize the OpenViking client."""
        await self.client.initialize()
        self._initialized = True

    async def close(self) -> None:
        """Close the OpenViking client and reset singleton."""
        await self.client.close()
        self._initialized = False
        self._singleton_initialized = False
        OpenVikingClient._instance = None

    @classmethod
    async def reset(cls) -> None:
        """Reset the singleton instance (mainly for testing)."""
        with cls._lock:
            if cls._instance is not None:
                await cls._instance.close()

    def session(self, session_id: Optional[str] = None) -> Any:
        """Get or create a session."""
        return self.client.session(session_id)

    async def add_message(self, session_id: str, role: str, content: str) -> Dict[str, Any]:
        """Add a message to a session."""
        return await self.client.add_message(session_id=session_id, role=role, content=content)

    async def commit_session(self, session_id: str) -> Dict[str, Any]:
        """Commit a session to extract memories."""
        return await self.client.commit_session(session_id)

    async def wait_processed(self, timeout: Optional[float] = None) -> Dict[str, Any]:
        """Wait for all queued processing to complete."""
        return await self.client.wait_processed(timeout=timeout)

    async def find(
        self,
        query: str,
        target_uri: str = "",
        limit: int = 10,
    ) -> Any:
        """Semantic search for memories."""
        return await self.client.find(
            query=query,
            target_uri=target_uri,
            limit=limit,
        )

    async def search(
        self,
        query: str,
        target_uri: str = "",
        session_id: Optional[str] = None,
        limit: int = 10,
    ) -> Any:
        """Complex search with session context."""
        return await self.client.search(
            query=query,
            target_uri=target_uri,
            session_id=session_id,
            limit=limit,
        )
