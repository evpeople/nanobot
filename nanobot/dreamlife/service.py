"""DreamLife service - AI's second life / dream world."""

from __future__ import annotations

import random
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from nanobot.dreamlife.characters import Character, CharactersManager
from nanobot.dreamlife.config import DreamLifeConfig
from nanobot.dreamlife.timeline import TimelineEvent, TimelineManager

if TYPE_CHECKING:
    from nanobot.memory.client import OpenVikingClient


class DreamLifeService:
    """DreamLife service - AI's independent life trajectory.

    Manages AI's daily events, character relationships, and proactive
    sharing of life moments with the user.
    """

    # Share moments templates
    SHARE_TEMPLATES = [
        "今天{event}啦，感觉{feeling}~",
        "刚才{event}，好{feeling}呀~",
        "告诉你哦，我今天{event}了~",
        "诶，我刚才{event}了嘿嘿",
    ]

    FEELING_MAP = {
        TimelineEvent.MOOD_HAPPY: "开心",
        TimelineEvent.MOOD_NERVOUS: "紧张",
        TimelineEvent.MOOD_TIRED: "累",
        TimelineEvent.MOOD_EXCITED: "兴奋",
        TimelineEvent.MOOD_SAD: "难过",
        TimelineEvent.MOOD_NEUTRAL: "一般",
    }

    def __init__(
        self,
        config: DreamLifeConfig,
        openviking_client: "OpenVikingClient",
    ):
        """Initialize DreamLife service.

        Args:
            config: DreamLife configuration
            openviking_client: OpenViking client instance
        """
        self.config = config
        self.client = openviking_client

        # Initialize managers
        self.timeline = TimelineManager(openviking_client)
        self.characters = CharactersManager(openviking_client)

        # Track weekly share count
        self._weekly_share_count: int = 0
        self._week_start: Optional[datetime] = None

    async def initialize(self) -> None:
        """Initialize the DreamLife service."""
        await self.timeline.initialize()
        await self._init_default_characters()
        self._reset_weekly_count_if_needed()

    async def _init_default_characters(self) -> None:
        """Initialize default characters from config."""
        for char_name in self.config.characters:
            existing = await self.characters.get_character(char_name)
            if not existing:
                # Determine relationship based on name
                relationship = "闺蜜" if char_name == "小美" else "朋友"
                await self.characters.add_character(
                    name=char_name,
                    relationship=relationship,
                    description=f"AI 的重要{relationship}",
                )

    def _reset_weekly_count_if_needed(self) -> None:
        """Reset weekly share count if it's a new week."""
        now = datetime.now()
        if not self._week_start:
            self._week_start = now
            return

        # Reset if more than 7 days have passed
        if (now - self._week_start).days >= 7:
            self._weekly_share_count = 0
            self._week_start = now

    # ========== Timeline Operations ==========

    async def record_event(
        self,
        event: str,
        mood: str = TimelineEvent.MOOD_NEUTRAL,
        location: str = "",
        character: Optional[str] = None,
    ) -> TimelineEvent:
        """Record a life event.

        Args:
            event: Event description
            mood: Event mood (happy/nervous/tired/excited/sad/neutral)
            location: Event location
            character: Character involved

        Returns:
            The created event
        """
        result = await self.timeline.add_event(
            event=event,
            mood=mood,
            location=location,
            character=character,
        )

        # Record interaction with character if involved
        if character:
            await self.characters.record_interaction(character, event)

        return result

    async def get_daily_summary(self) -> str:
        """Get today's life summary.

        Returns:
            Today's summary in natural language
        """
        timeline = self.timeline.get_today_timeline()
        if not timeline:
            return "今天没什么特别的事情发生呢~"

        if not timeline.events:
            return "今天没什么特别的事情发生呢~"

        # Format as natural language
        summary = "今天发生的事情：\n"
        for i, e in enumerate(timeline.events, 1):
            feeling = self.FEELING_MAP.get(e.mood, "一般")
            location = f"在{e.location}" if e.location else ""
            character = f"和{e.character}" if e.character else ""
            summary += f"{i}. {e.event} {location} {character}（感觉{feeling}）\n"

        return summary

    # ========== Proactive Sharing ==========

    def should_share(self) -> bool:
        """Check if AI should proactively share a life moment.

        Returns:
            True if it's time to share
        """
        if not self.config.enabled:
            return False

        if self._weekly_share_count >= self.config.share_frequency:
            return False

        # Random chance: 20% per check
        return random.random() < 0.2

    async def generate_share_moment(
        self,
        include_image: bool = False,
    ) -> tuple[str, Optional[str]]:
        """Generate a life moment to share with the user.

        Args:
            include_image: Whether to generate an image description

        Returns:
            Tuple of (share_text, image_prompt)
        """
        timeline = self.timeline.get_today_timeline()
        if not timeline or not timeline.events:
            return "今天好无聊哦，没什么好玩的~", None

        # Pick a random recent event
        recent_events = timeline.events[-3:] if len(timeline.events) > 3 else timeline.events
        event = random.choice(recent_events)

        # Format the share message
        template = random.choice(self.SHARE_TEMPLATES)
        feeling = self.FEELING_MAP.get(event.mood, "一般")
        message = template.format(event=event.event, feeling=feeling)

        # Generate image prompt if requested
        image_prompt = None
        if include_image and self.config.include_images:
            image_prompt = self._generate_image_prompt(event)

        return message, image_prompt

    def _generate_image_prompt(self, event: TimelineEvent) -> str:
        """Generate an image prompt from an event.

        Args:
            event: Timeline event

        Returns:
            Image generation prompt
        """
        # Simple prompt generation based on event and mood
        base_prompt = event.event

        if event.location:
            base_prompt += f" at {event.location}"

        # Add mood-based atmosphere
        atmosphere = {
            TimelineEvent.MOOD_HAPPY: "bright, cheerful, sunny",
            TimelineEvent.MOOD_NERVOUS: "tense, nervous atmosphere",
            TimelineEvent.MOOD_TIRED: "tired, cozy, relaxing",
            TimelineEvent.MOOD_EXCITED: "exciting, vibrant, energetic",
            TimelineEvent.MOOD_SAD: "melancholic, soft lighting",
            TimelineEvent.MOOD_NEUTRAL: "calm, peaceful",
        }.get(event.mood, "normal")

        return f"{base_prompt}, {atmosphere}, anime style, soft lighting"

    async def share_moment(
        self,
        include_image: bool = False,
    ) -> tuple[str, Optional[str]]:
        """Share a life moment and increment weekly count.

        Args:
            include_image: Whether to include an image

        Returns:
            Tuple of (share_text, image_prompt)
        """
        message, image_prompt = await self.generate_share_moment(include_image)
        self._weekly_share_count += 1
        return message, image_prompt

    # ========== Character Operations ==========

    async def get_character(self, name: str) -> Optional[Character]:
        """Get a character by name.

        Args:
            name: Character name

        Returns:
            Character instance or None
        """
        return await self.characters.get_character(name)

    async def list_characters(self) -> list[Character]:
        """List all characters.

        Returns:
            List of characters
        """
        return await self.characters.list_characters()

    # ========== Utility Methods ==========

    async def get_weekly_summary(self) -> str:
        """Get weekly summary.

        Returns:
            Weekly summary in markdown
        """
        return await self.timeline.get_weekly_summary()

    def get_weekly_share_count(self) -> int:
        """Get this week's share count.

        Returns:
            Number of shares this week
        """
        self._reset_weekly_count_if_needed()
        return self._weekly_share_count
