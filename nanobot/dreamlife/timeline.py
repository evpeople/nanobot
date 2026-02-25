"""Timeline management for DreamLife."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any, Optional


class TimelineEvent:
    """Represents an event in AI's timeline."""

    # Mood types
    MOOD_HAPPY = "happy"
    MOOD_NERVOUS = "nervous"
    MOOD_TIRED = "tired"
    MOOD_EXCITED = "excited"
    MOOD_SAD = "sad"
    MOOD_NEUTRAL = "neutral"

    VALID_MOODS = [MOOD_HAPPY, MOOD_NERVOUS, MOOD_TIRED, MOOD_EXCITED, MOOD_SAD, MOOD_NEUTRAL]

    def __init__(
        self,
        event: str,
        mood: str = MOOD_NEUTRAL,
        location: str = "",
        character: Optional[str] = None,
        time: Optional[str] = None,
    ):
        self.event = event
        self.mood = mood if mood in TimelineEvent.VALID_MOODS else TimelineEvent.MOOD_NEUTRAL
        self.location = location
        self.character = character
        self.time = time or datetime.now().isoformat()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "event": self.event,
            "mood": self.mood,
            "location": self.location,
            "character": self.character,
            "time": self.time,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TimelineEvent:
        """Create from dictionary."""
        return cls(
            event=data["event"],
            mood=data.get("mood", cls.MOOD_NEUTRAL),
            location=data.get("location", ""),
            character=data.get("character"),
            time=data.get("time"),
        )


class DailyTimeline:
    """Represents a day's timeline."""

    def __init__(self, date: Optional[str] = None):
        self.date = date or datetime.now().strftime("%Y-%m-%d")
        self.events: list[TimelineEvent] = []

    def add_event(self, event: TimelineEvent) -> None:
        """Add an event to the timeline."""
        self.events.append(event)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "date": self.date,
            "events": [e.to_dict() for e in self.events],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DailyTimeline:
        """Create from dictionary."""
        timeline = cls(date=data.get("date"))
        timeline.events = [TimelineEvent.from_dict(e) for e in data.get("events", [])]
        return timeline

    def to_markdown(self) -> str:
        """Convert timeline to markdown format."""
        md = f"# {self.date} 生活记录\n\n"
        if not self.events:
            md += "今天没什么特别的事情发生呢~\n"
        else:
            for e in self.events:
                time_str = datetime.fromisoformat(e.time).strftime("%H:%M")
                mood_emoji = {
                    TimelineEvent.MOOD_HAPPY: "😊",
                    TimelineEvent.MOOD_NERVOUS: "😰",
                    TimelineEvent.MOOD_TIRED: "😴",
                    TimelineEvent.MOOD_EXCITED: "🤩",
                    TimelineEvent.MOOD_SAD: "😢",
                    TimelineEvent.MOOD_NEUTRAL: "😐",
                }.get(e.mood, "😐")

                location = f" @ {e.location}" if e.location else ""
                character = f" (和{e.character})" if e.character else ""
                md += f"- {time_str} {mood_emoji} {e.event}{location}{character}\n"
        return md


class TimelineManager:
    """Manages AI's life timeline."""

    BASE_URI = "viking://user/ai_life/timeline"

    def __init__(self, openviking_client):
        """Initialize the timeline manager.

        Args:
            openviking_client: OpenViking client instance
        """
        self.client = openviking_client
        self._today_timeline: Optional[DailyTimeline] = None

    def _timeline_uri(self, date: str) -> str:
        """Get the URI for a timeline."""
        return f"{self.BASE_URI}/{date}.json"

    async def initialize(self) -> None:
        """Initialize and load today's timeline."""
        await self.load_today()

    async def load_today(self) -> DailyTimeline:
        """Load today's timeline.

        Returns:
            Today's timeline
        """
        today = datetime.now().strftime("%Y-%m-%d")
        return await self.load_date(today)

    async def load_date(self, date: str) -> DailyTimeline:
        """Load timeline for a specific date.

        Args:
            date: Date in YYYY-MM-DD format

        Returns:
            The daily timeline
        """
        uri = self._timeline_uri(date)
        try:
            data = await self.client.get(uri)
            if data:
                timeline = DailyTimeline.from_dict(json.loads(data))
                if date == datetime.now().strftime("%Y-%m-%d"):
                    self._today_timeline = timeline
                return timeline
        except Exception:
            pass

        # Return empty timeline if not found
        timeline = DailyTimeline(date=date)
        if date == datetime.now().strftime("%Y-%m-%d"):
            self._today_timeline = timeline
        return timeline

    async def save_timeline(self, timeline: DailyTimeline) -> None:
        """Save a timeline.

        Args:
            timeline: Timeline to save
        """
        uri = self._timeline_uri(timeline.date)
        await self.client.set(uri, json.dumps(timeline.to_dict()))

    async def add_event(
        self,
        event: str,
        mood: str = TimelineEvent.MOOD_NEUTRAL,
        location: str = "",
        character: Optional[str] = None,
    ) -> TimelineEvent:
        """Add an event to today's timeline.

        Args:
            event: Event description
            mood: Event mood
            location: Event location
            character: Character involved

        Returns:
            The created event
        """
        if not self._today_timeline:
            await self.load_today()

        timeline_event = TimelineEvent(
            event=event,
            mood=mood,
            location=location,
            character=character,
        )

        self._today_timeline.add_event(timeline_event)
        await self.save_timeline(self._today_timeline)

        return timeline_event

    def get_today_timeline(self) -> Optional[DailyTimeline]:
        """Get today's timeline (cached).

        Returns:
            Today's timeline or None if not loaded
        """
        return self._today_timeline

    async def get_date_range(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> list[DailyTimeline]:
        """Get timelines for a date range.

        Args:
            start_date: Start date in YYYY-MM-DD format (default: 7 days ago)
            end_date: End date in YYYY-MM-DD format (default: today)

        Returns:
            List of daily timelines
        """
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if not start_date:
            start_date = (datetime.now() - timedelta(days=6)).strftime("%Y-%m-%d")

        timelines = []
        current = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")

        while current <= end:
            date_str = current.strftime("%Y-%m-%d")
            timeline = await self.load_date(date_str)
            timelines.append(timeline)
            current += timedelta(days=1)

        return timelines

    async def get_weekly_summary(self) -> str:
        """Get a summary of the week's events.

        Returns:
            Weekly summary in markdown format
        """
        timelines = await self.get_date_range()

        md = "# 本周生活摘要\n\n"
        for timeline in timelines:
            md += timeline.to_markdown()
            md += "\n---\n\n"

        return md
