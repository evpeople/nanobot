"""Personality module for nanobot AI girlfriend."""

from nanobot.personality.config import PersonalityConfig
from nanobot.personality.service import DEFAULT_PERSONA_TEMPLATE, PersonalityService

__all__ = [
    "PersonalityConfig",
    "PersonalityService",
    "DEFAULT_PERSONA_TEMPLATE",
]
