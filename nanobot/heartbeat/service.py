"""Heartbeat service - periodic agent wake-up to check for tasks."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Coroutine

from loguru import logger

if TYPE_CHECKING:
    from nanobot.memory.proactive import ProactiveService
    from nanobot.personality.updater import PersonalityUpdater
    from nanobot.providers.base import LLMProvider

_HEARTBEAT_TOOL = [
    {
        "type": "function",
        "function": {
            "name": "heartbeat",
            "description": "Report heartbeat decision after reviewing tasks.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["skip", "run"],
                        "description": "skip = nothing to do, run = has active tasks",
                    },
                    "tasks": {
                        "type": "string",
                        "description": "Natural-language summary of active tasks (required for run)",
                    },
                },
                "required": ["action"],
            },
        },
    }
]


class HeartbeatService:
    """
    Periodic heartbeat service that wakes the agent to check for tasks.

    Phase 1 (decision): reads HEARTBEAT.md and asks the LLM — via a virtual
    tool call — whether there are active tasks.  This avoids free-text parsing
    and the unreliable HEARTBEAT_OK token.

    Phase 2 (execution): only triggered when Phase 1 returns ``run``.  The
    ``on_execute`` callback runs the task through the full agent loop and
    returns the result to deliver.
    """

    def __init__(
        self,
        workspace: Path,
        provider: LLMProvider,
        model: str,
        on_execute: Callable[[str], Coroutine[Any, Any, str]] | None = None,
        on_notify: Callable[[str], Coroutine[Any, Any, None]] | None = None,
        interval_s: int = 30 * 60,
        enabled: bool = True,
        proactive_service: ProactiveService | None = None,
        personality_updater: "PersonalityUpdater" | None = None,
    ):
        self.workspace = workspace
        self.provider = provider
        self.model = model
        self.on_execute = on_execute
        self.on_notify = on_notify
        self.interval_s = interval_s
        self.enabled = enabled
        self.proactive_service = proactive_service
        self.personality_updater = personality_updater
        self._running = False
        self._task: asyncio.Task | None = None
        self._proactive_task: asyncio.Task | None = None
        self._personality_task: asyncio.Task | None = None

    @property
    def heartbeat_file(self) -> Path:
        return self.workspace / "HEARTBEAT.md"

    def _read_heartbeat_file(self) -> str | None:
        if self.heartbeat_file.exists():
            try:
                return self.heartbeat_file.read_text(encoding="utf-8")
            except Exception:
                return None
        return None

    async def _decide(self, content: str) -> tuple[str, str]:
        """Phase 1: ask LLM to decide skip/run via virtual tool call.

        Returns (action, tasks) where action is 'skip' or 'run'.
        """
        response = await self.provider.chat(
            messages=[
                {
                    "role": "system",
                    "content": "You are a heartbeat agent. Call the heartbeat tool to report your decision.",
                },
                {
                    "role": "user",
                    "content": (
                        "Review the following HEARTBEAT.md and decide whether there are active tasks.\n\n"
                        f"{content}"
                    ),
                },
            ],
            tools=_HEARTBEAT_TOOL,
            model=self.model,
        )

        if not response.has_tool_calls:
            return "skip", ""

        args = response.tool_calls[0].arguments
        return args.get("action", "skip"), args.get("tasks", "")

    async def start(self) -> None:
        """Start the heartbeat service."""
        if not self.enabled:
            logger.info("Heartbeat disabled")
            return
        if self._running:
            logger.warning("Heartbeat already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop())

        # Start proactive pulse check if service is provided
        if self.proactive_service:
            proactive_interval = self.proactive_service.config.proactive_pulse_interval
            self._proactive_task = asyncio.create_task(self._run_proactive_loop(proactive_interval))
            logger.info("Proactive pulse check started (every {}s)", proactive_interval)

        # Start personality update loop if updater is provided
        if self.personality_updater:
            update_interval_hours = self.personality_updater.update_interval_hours
            update_interval_s = update_interval_hours * 3600
            self._personality_task = asyncio.create_task(self._run_personality_loop(update_interval_s))
            logger.info("Personality update loop started (every {} hours)", update_interval_hours)

        logger.info("Heartbeat started (every {}s)", self.interval_s)

    def stop(self) -> None:
        """Stop the heartbeat service."""
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None

        # Stop proactive pulse check
        if self._proactive_task:
            self._proactive_task.cancel()
            self._proactive_task = None

        # Stop personality update loop
        if self._personality_task:
            self._personality_task.cancel()
            self._personality_task = None

    async def _run_loop(self) -> None:
        """Main heartbeat loop."""
        while self._running:
            try:
                await asyncio.sleep(self.interval_s)
                if self._running:
                    await self._tick()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Heartbeat error: {}", e)

    async def _run_proactive_loop(self, interval_s: int) -> None:
        """Proactive pulse check loop."""
        while self._running:
            try:
                await asyncio.sleep(interval_s)
                if self._running and self.proactive_service:
                    await self._proactive_tick()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Proactive pulse error: {}", e)

    async def _proactive_tick(self) -> None:
        """Execute a single proactive pulse check."""
        if not self.proactive_service:
            return

        try:
            sent_sessions = await self.proactive_service.pulse_check()
            if sent_sessions:
                logger.info("Proactive: sent caring messages to {} sessions", len(sent_sessions))
        except Exception:
            logger.exception("Proactive pulse check failed")

    async def _run_personality_loop(self, interval_s: int) -> None:
        """Personality update loop."""
        while self._running:
            try:
                await asyncio.sleep(interval_s)
                if self._running and self.personality_updater:
                    await self._personality_tick()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Personality update error: {}", e)

    async def _personality_tick(self) -> None:
        """Execute a single personality update."""
        if not self.personality_updater:
            return

        # Check if it's time to update
        if not self.personality_updater.should_update():
            logger.debug("PersonalityUpdater: not time to update yet")
            return

        try:
            success = await self.personality_updater.update_from_all_sessions()
            if success:
                logger.info("PersonalityUpdater: personality updated successfully")
            else:
                logger.info("PersonalityUpdater: no update needed or update failed")
        except Exception:
            logger.exception("Personality update failed")

    async def _tick(self) -> None:
        """Execute a single heartbeat tick."""
        content = self._read_heartbeat_file()
        if not content:
            logger.debug("Heartbeat: HEARTBEAT.md missing or empty")
            return

        logger.info("Heartbeat: checking for tasks...")

        try:
            action, tasks = await self._decide(content)

            if action != "run":
                logger.info("Heartbeat: OK (nothing to report)")
                return

            logger.info("Heartbeat: tasks found, executing...")
            if self.on_execute:
                response = await self.on_execute(tasks)
                if response and self.on_notify:
                    logger.info("Heartbeat: completed, delivering response")
                    await self.on_notify(response)
        except Exception:
            logger.exception("Heartbeat execution failed")

    async def trigger_now(self) -> str | None:
        """Manually trigger a heartbeat."""
        content = self._read_heartbeat_file()
        if not content:
            return None
        action, tasks = await self._decide(content)
        if action != "run" or not self.on_execute:
            return None
        return await self.on_execute(tasks)
