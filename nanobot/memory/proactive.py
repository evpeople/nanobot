"""Proactive service for AI girlfriend care and attention."""

from __future__ import annotations

import random
from datetime import datetime
from typing import TYPE_CHECKING, Protocol

from nanobot.memory.config import MemoryConfig

if TYPE_CHECKING:
    pass


class MessageSender(Protocol):
    """Protocol for sending messages to users."""

    async def send(self, session_id: str, message: str) -> None:
        """Send a message to a session."""
        ...


class ProactiveService:
    """Proactive care service for AI girlfriend.

    Periodically checks if users need attention and sends caring messages.
    """

    # Default caring messages
    DEFAULT_MESSAGES: list[str] = [
        "干嘛去了~想你啦",
        "最近怎么样呀？",
        "在忙什么呀？",
        "怎么这么久不理人家~",
        "有空的话陪我聊聊天嘛~",
    ]

    def __init__(self, config: MemoryConfig, sender: MessageSender):
        """Initialize the proactive service.

        Args:
            config: Memory configuration with proactive settings
            sender: Message sender that implements the MessageSender protocol
        """
        self.config = config
        self.sender = sender
        self._last_message_time: dict[str, datetime] = {}
        self._today_count: dict[str, int] = {}

    def record_message(self, session_id: str) -> None:
        """Record the last message time for a session.

        Should be called whenever a user sends a message.

        Args:
            session_id: The session identifier
        """
        self._last_message_time[session_id] = datetime.now()

    def get_last_message_time(self, session_id: str) -> datetime | None:
        """Get the last message time for a session.

        Args:
            session_id: The session identifier

        Returns:
            The last message time, or None if no messages recorded
        """
        return self._last_message_time.get(session_id)

    def get_today_count(self, session_id: str) -> int:
        """Get today's message count for a session.

        Args:
            session_id: The session identifier

        Returns:
            The number of proactive messages sent today
        """
        today = datetime.now().date()
        return self._today_count.get(today, {}).get(session_id, 0)

    async def pulse_check(self) -> list[str]:
        """Perform a pulse check to see if proactive messages should be sent.

        Returns:
            List of session IDs that received proactive messages
        """
        if not self.config.proactive_enabled:
            return []

        sent_messages: list[str] = []

        # Check if daily limit exceeded
        today = datetime.now().date()
        if today not in self._today_count:
            self._today_count[today] = {}

        today_total = sum(self._today_count[today].values())
        if today_total >= self.config.proactive_max_per_day:
            return []

        # Check each session for care
        for session_id, last_time in list(self._last_message_time.items()):
            # Skip if already sent max per session today
            session_today_count = self._today_count[today].get(session_id, 0)
            if session_today_count >= self.config.proactive_max_per_day:
                continue

            hours_since = (datetime.now() - last_time).total_seconds() / 3600
            if hours_since >= self.config.proactive_min_interval_hours:
                message = await self._send_caring_message(session_id)
                if message:
                    sent_messages.append(session_id)

        return sent_messages

    async def _send_caring_message(self, session_id: str) -> str | None:
        """Send a caring message to a session.

        Args:
            session_id: The session identifier

        Returns:
            The sent message, or None if failed
        """
        message = self._generate_caring_message()
        try:
            await self.sender.send(session_id, message)

            # Record the message
            today = datetime.now().date()
            if today not in self._today_count:
                self._today_count[today] = {}
            self._today_count[today][session_id] = self._today_count[today].get(session_id, 0) + 1

            return message
        except Exception:
            return None

    def _generate_caring_message(self) -> str:
        """Generate a random caring message.

        Returns:
            A caring message string
        """
        return random.choice(self.DEFAULT_MESSAGES)

    def reset_daily_count(self) -> None:
        """Reset daily counts. Should be called at midnight."""
        self._today_count.clear()
