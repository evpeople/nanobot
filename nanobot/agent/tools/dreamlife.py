"""DreamLife tools for AI girlfriend."""

from __future__ import annotations

from typing import Any, Optional

from nanobot.agent.tools.base import Tool
from nanobot.dreamlife.service import DreamLifeService
from nanobot.dreamlife.timeline import TimelineEvent


class AILifeGetDailySummaryTool(Tool):
    """Get AI's daily life summary."""

    name = "ai_life_get_daily_summary"
    description = "获取 AI 今日生活摘要"

    def __init__(self, dreamlife_service: Optional[DreamLifeService] = None):
        """Initialize the tool.

        Args:
            dreamlife_service: DreamLife service instance
        """
        self.dreamlife_service = dreamlife_service

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
        }

    async def execute(self, **kwargs: Any) -> str:
        """Get daily summary.

        Returns:
            Daily summary text
        """
        if not self.dreamlife_service:
            return "错误：DreamLife 服务未启用"

        try:
            return await self.dreamlife_service.get_daily_summary()
        except Exception as e:
            return f"获取生活摘要失败：{str(e)}"


class AILifeRecordEventTool(Tool):
    """Record AI's life event."""

    name = "ai_life_record_event"
    description = "记录 AI 的生活事件"

    def __init__(self, dreamlife_service: Optional[DreamLifeService] = None):
        """Initialize the tool.

        Args:
            dreamlife_service: DreamLife service instance
        """
        self.dreamlife_service = dreamlife_service

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "event": {
                    "type": "string",
                    "description": "事件描述",
                },
                "mood": {
                    "type": "string",
                    "enum": [
                        TimelineEvent.MOOD_HAPPY,
                        TimelineEvent.MOOD_NERVOUS,
                        TimelineEvent.MOOD_TIRED,
                        TimelineEvent.MOOD_EXCITED,
                        TimelineEvent.MOOD_SAD,
                        TimelineEvent.MOOD_NEUTRAL,
                    ],
                    "default": TimelineEvent.MOOD_NEUTRAL,
                    "description": "心情（happy/nervous/tired/excited/sad/neutral）",
                },
                "location": {
                    "type": "string",
                    "default": "",
                    "description": "地点",
                },
                "character": {
                    "type": "string",
                    "default": "",
                    "description": "涉及的人物",
                },
            },
            "required": ["event"],
        }

    async def execute(
        self,
        event: str,
        mood: str = TimelineEvent.MOOD_NEUTRAL,
        location: str = "",
        character: str = "",
        **kwargs: Any,
    ) -> str:
        """Record a life event.

        Args:
            event: Event description
            mood: Event mood
            location: Event location
            character: Character involved

        Returns:
            Confirmation message
        """
        if not self.dreamlife_service:
            return "错误：DreamLife 服务未启用"

        try:
            await self.dreamlife_service.record_event(
                event=event,
                mood=mood,
                location=location,
                character=character or None,
            )
            return f"已记录：{event}"
        except Exception as e:
            return f"记录事件失败：{str(e)}"


class AILifeShareMomentTool(Tool):
    """Share AI's life moment with user."""

    name = "ai_life_share_moment"
    description = "向用户分享一个生活瞬间（可带图片）"

    def __init__(self, dreamlife_service: Optional[DreamLifeService] = None):
        """Initialize the tool.

        Args:
            dreamlife_service: DreamLife service instance
        """
        self.dreamlife_service = dreamlife_service

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "moment": {
                    "type": "string",
                    "description": "想分享的内容",
                },
                "generate_image": {
                    "type": "boolean",
                    "default": False,
                    "description": "是否生成配图",
                },
            },
            "required": ["moment"],
        }

    async def execute(
        self,
        moment: str,
        generate_image: bool = False,
        **kwargs: Any,
    ) -> str:
        """Share a life moment.

        Args:
            moment: Moment to share
            generate_image: Whether to generate an image

        Returns:
            Share message
        """
        if not self.dreamlife_service:
            return "错误：DreamLife 服务未启用"

        # Record the event first
        try:
            await self.dreamlife_service.record_event(
                event=moment,
                mood=TimelineEvent.MOOD_HAPPY,
            )
        except Exception:
            pass

        # Return the share message
        if generate_image:
            return f"{moment}\n\n[图片生成中...]"
        return moment


class AILifeGetWeeklySummaryTool(Tool):
    """Get AI's weekly life summary."""

    name = "ai_life_get_weekly_summary"
    description = "获取 AI 本周生活摘要"

    def __init__(self, dreamlife_service: Optional[DreamLifeService] = None):
        """Initialize the tool.

        Args:
            dreamlife_service: DreamLife service instance
        """
        self.dreamlife_service = dreamlife_service

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
        }

    async def execute(self, **kwargs: Any) -> str:
        """Get weekly summary.

        Returns:
            Weekly summary text
        """
        if not self.dreamlife_service:
            return "错误：DreamLife 服务未启用"

        try:
            return await self.dreamlife_service.get_weekly_summary()
        except Exception as e:
            return f"获取本周摘要失败：{str(e)}"


# Tool list for easy registration
TOOLS = [
    AILifeGetDailySummaryTool,
    AILifeRecordEventTool,
    AILifeShareMomentTool,
    AILifeGetWeeklySummaryTool,
]
