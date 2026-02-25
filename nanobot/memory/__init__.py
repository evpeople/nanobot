"""Memory module for nanobot AI girlfriend."""

from nanobot.memory.client import OpenVikingClient
from nanobot.memory.config import MemoryConfig
from nanobot.memory.service import MemoryService

__all__ = ["MemoryConfig", "OpenVikingClient", "MemoryService"]
