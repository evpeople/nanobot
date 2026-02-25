"""Memory module for nanobot AI girlfriend."""

from nanobot.memory.client import OpenVikingClient
from nanobot.memory.comfyui import ComfyUIClient
from nanobot.memory.config import MemoryConfig, SmartProactiveConfig
from nanobot.memory.explorer_agent import ExplorerAgent
from nanobot.memory.opportunity import Opportunity, OpportunitySource, OpportunityStatus
from nanobot.memory.proactive import ProactiveService
from nanobot.memory.service import MemoryService
from nanobot.memory.smart_proactive import SmartProactiveService
from nanobot.memory.tracker import OpportunityTracker

__all__ = [
    "MemoryConfig",
    "SmartProactiveConfig",
    "OpenVikingClient",
    "MemoryService",
    "ProactiveService",
    "SmartProactiveService",
    "ExplorerAgent",
    "OpportunityTracker",
    "Opportunity",
    "OpportunitySource",
    "OpportunityStatus",
    "ComfyUIClient",
]
