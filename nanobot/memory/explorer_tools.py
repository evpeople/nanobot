"""Explorer Agent tools for memory exploration."""

import json
from typing import Any

from nanobot.agent.tools.base import Tool


class MemorySearchTool(Tool):
    """Semantic search for memories."""

    name = "memory_search"
    description = "Semantic search for user and AI conversation memories"

    def __init__(self, openviking_client):
        self.client = openviking_client

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "limit": {"type": "integer", "default": 5},
                "target_uri": {
                    "type": "string",
                    "default": "viking://user/memories",
                },
            },
            "required": ["query"],
        }

    async def execute(
        self,
        query: str,
        limit: int = 5,
        target_uri: str = "viking://user/memories",
        **kwargs: Any,
    ) -> str:
        """Execute semantic search."""
        results = await self.client.find(query=query, target_uri=target_uri, limit=limit)
        # Format results
        items = []
        if hasattr(results, "items"):
            for item in results.items:
                overview = await self.client.client.overview(item.uri)
                items.append(
                    {
                        "uri": item.uri,
                        "score": item.score,
                        "overview": overview[:500] if overview else "",
                    }
                )
        return json.dumps({"success": True, "items": items})


class MemoryOverviewTool(Tool):
    """Get memory overview."""

    name = "memory_overview"
    description = "Get detailed overview of a memory"

    def __init__(self, openviking_client):
        self.client = openviking_client

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "uri": {"type": "string", "description": "Memory URI"},
            },
            "required": ["uri"],
        }

    async def execute(self, uri: str, **kwargs: Any) -> str:
        """Execute memory overview."""
        overview = await self.client.client.overview(uri)
        return json.dumps({"success": True, "overview": overview})


class RelationsTool(Tool):
    """Get related memories."""

    name = "relations"
    description = "Get related memories for a given memory"

    def __init__(self, openviking_client):
        self.client = openviking_client

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "uri": {"type": "string", "description": "Memory URI"},
            },
            "required": ["uri"],
        }

    async def execute(self, uri: str, **kwargs: Any) -> str:
        """Execute relations query."""
        relations = await self.client.client.relations(uri)
        return json.dumps({"success": True, "relations": relations})


class GetRecentSessionsTool(Tool):
    """Get recent conversation sessions."""

    name = "get_recent_sessions"
    description = "Get recent conversation session list"

    def __init__(self, openviking_client):
        self.client = openviking_client

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 10},
            },
        }

    async def execute(self, limit: int = 10, **kwargs: Any) -> str:
        """Execute get recent sessions."""
        try:
            sessions = await self.client.client.list_sessions()
            # Only return the most recent N
            recent = sessions[:limit]
            return json.dumps({"success": True, "sessions": recent})
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})


class CreateOpportunityTool(Tool):
    """Create opportunity (Explorer Agent only)."""

    name = "create_opportunity"
    description = "Create a proactive messaging opportunity"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Opportunity title"},
                "content": {"type": "string", "description": "Detailed description"},
                "context": {"type": "string", "description": "Context summary"},
                "priority": {"type": "integer", "default": 50},
                "source": {"type": "string", "default": "memory_user"},
                "tags": {"type": "array", "items": {"type": "string"}},
                "session_id": {
                    "type": "string",
                    "description": "Associated session ID",
                },
                "related_uri": {"type": "string", "description": "Related memory URI"},
            },
            "required": ["title", "content", "session_id"],
        }

    async def execute(
        self,
        title: str,
        content: str,
        session_id: str,
        context: str = "",
        priority: int = 50,
        source: str = "memory_user",
        tags: list = None,
        related_uri: str = "",
        **kwargs: Any,
    ) -> str:
        """Execute create opportunity."""
        return json.dumps(
            {
                "success": True,
                "opportunity": {
                    "title": title,
                    "content": content,
                    "context": context,
                    "priority": priority,
                    "source": source,
                    "tags": tags or [],
                    "session_id": session_id,
                    "related_uri": related_uri,
                },
            }
        )
