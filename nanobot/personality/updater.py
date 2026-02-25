"""Personality updater - scheduled task to update personality from conversation history."""

from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING, Any

from loguru import logger

if TYPE_CHECKING:
    from nanobot.providers.base import LLMProvider

from nanobot.personality.service import PersonalityService

ANALYSIS_SYSTEM_PROMPT = """你是一个性格分析助手。根据用户和AI的对话历史，分析并更新AI的人格参数。

请分析对话中体现的用户偏好和互动模式，返回JSON格式的更新建议。

返回格式：
```json
{
    "name": "保留原名或更新",
    "age": 保留原年龄或微调,
    "personality": "性格关键词（逗号分隔）",
    "traits": "详细性格特点（换行分隔）",
    "update_summary": "本次更新的简要说明"
}
```

注意：只返回必要的更新，不要做大幅度改变。保持AI角色的一致性。"""


class PersonalityUpdater:
    """Scheduled personality updater.

    Analyzes conversation history using LLM and updates
    personality configuration dynamically.
    """

    def __init__(
        self,
        personality_service: PersonalityService,
        provider: LLMProvider,
        model: str = "gpt-4o-mini",
        update_interval_hours: int = 24,
    ) -> None:
        self.personality_service = personality_service
        self.provider = provider
        self.model = model
        self.update_interval_hours = update_interval_hours
        self._last_update_time: float | None = None

    def should_update(self) -> bool:
        """Check if it's time to update personality.

        Returns:
            True if enough time has passed since last update
        """
        if self._last_update_time is None:
            return True

        elapsed_hours = (time.time() - self._last_update_time) / 3600
        return elapsed_hours >= self.update_interval_hours

    def _build_analysis_prompt(self, conversation: list[dict[str, str]]) -> str:
        """Build prompt for LLM analysis.

        Args:
            conversation: List of message dicts with role and content

        Returns:
            Formatted prompt string
        """
        config = self.personality_service.config

        conversation_text = "\n".join(
            f"{msg['role']}: {msg['content']}"
            for msg in conversation
        )

        return f"""当前人格配置：
- 名字: {config.name}
- 年龄: {config.age}
- 身份: {config.identity}
- 性格: {config.personality}
- 特点: {config.traits}

对话历史：
{conversation_text}

请分析上述对话，返回JSON格式的人格更新建议："""

    async def update_from_conversation(
        self,
        conversation: list[dict[str, str]],
    ) -> bool:
        """Update personality from conversation history.

        Args:
            conversation: List of message dicts with role and content

        Returns:
            True if update was successful
        """
        if not conversation:
            logger.debug("PersonalityUpdater: No conversation to analyze")
            return False

        try:
            prompt = self._build_analysis_prompt(conversation)

            response = await self.provider.chat(
                messages=[
                    {"role": "system", "content": ANALYSIS_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                model=self.model,
            )

            if not response.content:
                logger.warning("PersonalityUpdater: Empty LLM response")
                return False

            # Parse JSON from response
            update_data = self._parse_json_response(response.content)

            if not update_data:
                logger.warning("PersonalityUpdater: Failed to parse LLM response")
                return False

            # Apply updates to config
            self._apply_update(update_data)

            self._last_update_time = time.time()
            logger.info(
                "PersonalityUpdater: Updated personality - {}",
                update_data.get("update_summary", "No summary")
            )

            # Clear cached system prompt
            self.personality_service._system_prompt = ""

            return True

        except Exception as e:
            logger.error("PersonalityUpdater: Update failed - {}", e)
            return False

    def _parse_json_response(self, content: str) -> dict[str, Any] | None:
        """Parse JSON from LLM response.

        Args:
            content: LLM response content

        Returns:
            Parsed JSON dict or None if parsing fails
        """
        # Try to extract JSON from markdown code blocks
        import re

        # Look for JSON in code blocks
        json_match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", content)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try to parse entire content as JSON
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # Try to find JSON object anywhere in content
        try:
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

        return None

    def _apply_update(self, update_data: dict[str, Any]) -> None:
        """Apply parsed update data to personality config.

        Args:
            update_data: Dict with personality update fields
        """
        config = self.personality_service.config

        # Only update fields that are present in update_data
        if "name" in update_data and update_data["name"]:
            config.name = update_data["name"]

        if "age" in update_data:
            try:
                config.age = int(update_data["age"])
            except (ValueError, TypeError):
                pass

        if "personality" in update_data and update_data["personality"]:
            config.personality = update_data["personality"]

        if "traits" in update_data and update_data["traits"]:
            config.traits = update_data["traits"]

        if "tone" in update_data and update_data["tone"]:
            config.tone = update_data["tone"]

        if "fillers" in update_data and update_data["fillers"]:
            config.fillers = update_data["fillers"]

        if "habits" in update_data and update_data["habits"]:
            config.habits = update_data["habits"]

        if "background" in update_data and update_data["background"]:
            config.background = update_data["background"]
