"""Opportunity data class for proactive messaging."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class OpportunitySource(Enum):
    """Opportunity source."""

    MEMORY_USER = "memory_user"  # User memory (things user mentioned)
    MEMORY_AI = "memory_ai"  # AI's own memory
    DREAMLIFE = "dreamlife"  # Second life
    FOLLOW_UP = "follow_up"  # Follow up to previous messages


class OpportunityStatus(Enum):
    """Opportunity status."""

    PENDING = "pending"  # Pending
    SENT = "sent"  # Sent
    COMPLETED = "completed"  # Completed (no more sending needed)
    IGNORED = "ignored"  # Ignored
    EXPIRED = "expired"  # Expired


@dataclass
class Opportunity:
    """Opportunity for proactive messaging."""

    id: str = ""  # Unique identifier (UUID)
    source: OpportunitySource = OpportunitySource.MEMORY_USER  # Source
    title: str = ""  # Title (e.g., "user's project")
    content: str = ""  # Detailed content
    context: str = ""  # Context summary (for message generation)
    priority: int = 50  # Priority (0-100)
    status: OpportunityStatus = OpportunityStatus.PENDING  # Current status

    # Association info
    session_id: str = ""  # Associated session
    related_uri: str = ""  # Associated memory URI
    dreamlife_event_id: str = ""  # Associated second life event

    # Time info
    created_at: str = ""  # Created time
    sent_at: Optional[str] = None  # Sent time
    last_reminded_at: Optional[str] = None  # Last reminded time
    reminder_count: int = 0  # Reminder count

    # Deduplication info
    parent_id: str = ""  # Parent opportunity ID (for follow-up)
    follow_up_interval_days: int = 7  # Follow-up interval (days)
    tags: list[str] = field(default_factory=list)  # Tags for deduplication

    def __post_init__(self) -> None:
        """Post-initialization to set defaults."""
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.id:
            import uuid

            self.id = str(uuid.uuid4())

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "source": self.source.value,
            "title": self.title,
            "content": self.content,
            "context": self.context,
            "priority": self.priority,
            "status": self.status.value,
            "session_id": self.session_id,
            "related_uri": self.related_uri,
            "dreamlife_event_id": self.dreamlife_event_id,
            "created_at": self.created_at,
            "sent_at": self.sent_at,
            "last_reminded_at": self.last_reminded_at,
            "reminder_count": self.reminder_count,
            "parent_id": self.parent_id,
            "follow_up_interval_days": self.follow_up_interval_days,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Opportunity":
        """Create from dictionary."""
        return cls(
            id=data.get("id", ""),
            source=OpportunitySource(data.get("source", "memory_user")),
            title=data.get("title", ""),
            content=data.get("content", ""),
            context=data.get("context", ""),
            priority=data.get("priority", 50),
            status=OpportunityStatus(data.get("status", "pending")),
            session_id=data.get("session_id", ""),
            related_uri=data.get("related_uri", ""),
            dreamlife_event_id=data.get("dreamlife_event_id", ""),
            created_at=data.get("created_at", ""),
            sent_at=data.get("sent_at"),
            last_reminded_at=data.get("last_reminded_at"),
            reminder_count=data.get("reminder_count", 0),
            parent_id=data.get("parent_id", ""),
            follow_up_interval_days=data.get("follow_up_interval_days", 7),
            tags=data.get("tags", []),
        )
