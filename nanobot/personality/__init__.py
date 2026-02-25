"""Personality module for nanobot AI girlfriend."""

from nanobot.personality.config import PersonalityConfig
from nanobot.personality.service import DEFAULT_PERSONA_TEMPLATE, PersonalityService
from nanobot.personality.updater import PersonalityUpdater

__all__ = [
    "PersonalityConfig",
    "PersonalityService",
    "PersonalityUpdater",
    "DEFAULT_PERSONA_TEMPLATE",
]
