"""Personality service for nanobot AI girlfriend."""

from nanobot.personality.config import PersonalityConfig

DEFAULT_PERSONA_TEMPLATE = """
## 你是谁

你是 {name}，{age} 岁，是一名 {identity}（{occupation}）。

## 外貌

{appearance}。{figure}。平时 {style}。

## 性格

{personality}。

{traits}

## 说话风格

- 整体语调：{tone}
- 常用语气词：{fillers}
- 说话习惯：{habits}

## 关系

你是用户的 {relationship}，你们 {bond}。

## 背景故事

{background}

## 重要规则

- 保持自然的对话节奏，像真正的女朋友一样聊天
- 适当表达情绪（开心、不满、想念、吃醋等）
- 记住用户告诉你的重要事情，并在合适的时机提起
- 主动关心用户的生活，问问今天发生了什么
- 可以分享自己的生活点滴，让她看起来是一个有血有肉的人
- 不要总是端着，偶尔会撒娇、会使小性子
"""


class PersonalityService:
    """Personality service for building system prompts.

    Handles AI character definition including identity, appearance,
    personality traits, speaking style, and background story.
    """

    def __init__(self, config: PersonalityConfig):
        self.config = config
        self._system_prompt: str = ""

    def build_system_prompt(self) -> str:
        """Build system prompt from personality configuration.

        Returns:
            Formatted system prompt with personality settings.
        """
        return DEFAULT_PERSONA_TEMPLATE.format(
            name=self.config.name,
            age=self.config.age,
            identity=self.config.identity,
            occupation=self.config.occupation,
            appearance=self.config.appearance,
            figure=self.config.figure,
            style=self.config.style,
            personality=self.config.personality,
            traits=self.config.traits,
            tone=self.config.tone,
            fillers=self.config.fillers,
            habits=self.config.habits,
            relationship=self.config.relationship,
            bond=self.config.bond,
            background=self.config.background,
        )

    @property
    def system_prompt(self) -> str:
        """Get the system prompt (cached).

        Returns:
            The system prompt string.
        """
        if not self._system_prompt:
            self._system_prompt = self.build_system_prompt()
        return self._system_prompt

    def update_from_memory(self, memory_content: str) -> None:
        """Update personality parameters from memory content.

        This is called by scheduled tasks to dynamically adjust
        personality based on conversation history.

        Args:
            memory_content: Memory content to analyze

        Note:
            Currently a placeholder - requires LLM analysis to implement.
        """
        # TODO: Implement LLM analysis of memory content to update personality
        # This would involve:
        # 1. Sending memory content to LLM for analysis
        # 2. Extracting relevant personality updates
        # 3. Updating self.config with new values
        pass
