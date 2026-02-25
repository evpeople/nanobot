"""Explorer Agent for memory exploration."""

import json
from typing import TYPE_CHECKING, Optional

from loguru import logger

from nanobot.agent.tools.registry import ToolRegistry
from nanobot.memory.config import SmartProactiveConfig
from nanobot.memory.explorer_tools import (
    CreateOpportunityTool,
    GetRecentSessionsTool,
    MemoryOverviewTool,
    MemorySearchTool,
    RelationsTool,
)
from nanobot.memory.opportunity import Opportunity, OpportunitySource

if TYPE_CHECKING:
    from nanobot.providers.base import LLMProvider


class ExplorerAgent:
    """
    Memory Explorer Agent - independent AI Agent for exploring memory and generating opportunities.

    Reuses nanobot SubagentManager design pattern:
    - Use ToolRegistry for dedicated tools
    - Use LLM for autonomous decision-making
    - Support multi-round tool calls
    """

    SYSTEM_PROMPT = """你是记忆探索专家，负责为 AI 女友找出可以主动发消息的机会。

## 你的任务
分析用户和 AI 的对话记忆，找出以下类型的机会点：

### 机会点类型

1. **用户正在做的事情**
   - 用户最近提到的项目、学习、工作
   - 用户说的"在做..."、"最近在搞..."
   - 优先级：高

2. **用户提到的重点人物**
   - 用户提到的朋友、家人、同事
   - 用户说的"XX 最近..."
   - 优先级：中

3. **用户最近的烦恼/开心事**
   - 用户倾诉的情绪
   - 用户说的"烦死了"、"今天超开心"
   - 优先级：中

4. **跟进机会**（如果有）
   - 之前发送的主动消息对应的跟进
   - 之前关心过的话题是否有后续
   - 优先级：高

## 工具
你有两个专用工具：
- `memory_search`: 搜索记忆库（语义搜索）
- `memory_overview`: 获取记忆的摘要信息
- `relations`: 获取相关联的记忆
- `get_recent_sessions`: 获取最近的对话 session

## 输出格式
找到机会点后，调用 `create_opportunity` 工具创建机会点。
每个机会点需要包含：
- title: 简短标题（如"项目的进展"）
- content: 详细描述
- priority: 优先级 0-100
- tags: 标签列表（用于去重）
- reason: 为什么适合作为主动消息

## 重要规则
1. 同一个话题在 30 天内不会重复生成机会点（系统会自动去重）
2. 优先找最近 7 天内的新鲜记忆
3. 如果发现已经跟进过的话题，考虑生成"跟进"类型的机会点"""

    def __init__(
        self,
        provider: "LLMProvider",
        openviking_client,
        config: "SmartProactiveConfig",
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ):
        """
        Initialize Explorer Agent.

        Args:
            provider: LLM Provider (reuse existing nanobot provider)
            openviking_client: OpenViking client
            config: Smart proactive config
            model: Model to use
            temperature: Temperature parameter
            max_tokens: Max tokens
        """
        self.provider = provider
        self.client = openviking_client
        self.config = config
        self.model = model or provider.get_default_model()
        self.temperature = temperature
        self.max_tokens = max_tokens

    async def run(self, session_id: str) -> list[Opportunity]:
        """
        Run explorer agent to generate opportunities for a session.

        Args:
            session_id: Session ID to explore

        Returns:
            List of Opportunities
        """
        logger.info("ExplorerAgent: Starting exploration for session {}", session_id)

        # Build tools
        tools = self._build_tools()

        # Build initial messages
        context = await self._prepare_context(session_id)
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"探索 session {session_id} 的记忆，找出可以主动发消息的机会点。\n\n{context}",
            },
        ]

        # Run agent loop
        opportunities = []
        max_iterations = self.config.explorer_max_iterations
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            response = await self.provider.chat(
                messages=messages,
                tools=tools.get_definitions(),
                model=self.model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

            if not response.tool_calls:
                # No more tool calls, exploration done
                break

            # Process tool calls
            for tool_call in response.tool_calls:
                # Add assistant message
                messages.append(
                    {
                        "role": "assistant",
                        "content": response.content or "",
                        "tool_calls": [self._tool_call_to_dict(tool_call)],
                    }
                )

                # Execute tool
                result = await self._execute_tool(tool_call, tools)

                # If create_opportunity, collect the opportunity
                if tool_call.name == "create_opportunity":
                    try:
                        opp = self._parse_opportunity_result(result)
                        if opp:
                            opportunities.append(opp)
                    except Exception as e:
                        logger.warning("Failed to parse opportunity: {}", e)

                # Add tool result
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_call.name,
                        "content": result,
                    }
                )

        logger.info(
            "ExplorerAgent: Exploration complete, found {} opportunities",
            len(opportunities),
        )
        return opportunities

    def _build_tools(self) -> ToolRegistry:
        """Build Explorer Agent tools."""
        tools = ToolRegistry()
        tools.register(MemorySearchTool(self.client))
        tools.register(MemoryOverviewTool(self.client))
        tools.register(RelationsTool(self.client))
        tools.register(GetRecentSessionsTool(self.client))
        tools.register(CreateOpportunityTool())
        return tools

    async def _prepare_context(self, session_id: str) -> str:
        """Prepare exploration context."""
        # Get recent sent context (for deduplication)
        recent_sent = await self._get_recent_sent_context()

        context = f"""## Session {session_id} 背景

最近发送的主动消息（用于去重）：
{recent_sent}

请开始探索记忆。"""

        return context

    async def _get_recent_sent_context(self) -> str:
        """Get recent sent messages context."""
        try:
            results = await self.client.find(
                query="主动消息 关心 跟进",
                target_uri="viking://user/proactive/sent",
                limit=5,
            )
            if not hasattr(results, "items") or not results.items:
                return "（暂无已发送记录）"

            lines = []
            for item in results.items:
                overview = await self.client.client.overview(item.uri)
                lines.append(f"- {overview[:100]}" if overview else "")
            return "\n".join(lines) if lines else "（暂无）"
        except Exception:
            return "（获取失败）"

    async def _execute_tool(self, tool_call, tools: ToolRegistry) -> str:
        """Execute tool call."""
        tool_name = tool_call.name
        args = tool_call.arguments
        return await tools.execute(tool_name, args)

    def _tool_call_to_dict(self, tool_call) -> dict:
        """Convert tool call to dict."""
        return {
            "id": tool_call.id,
            "type": "function",
            "function": {
                "name": tool_call.name,
                "arguments": json.dumps(tool_call.arguments, ensure_ascii=False),
            },
        }

    def _parse_opportunity_result(self, result: str) -> Optional[Opportunity]:
        """Parse opportunity from tool result."""
        try:
            data = json.loads(result)
            if not data.get("success"):
                return None

            opp_data = data.get("opportunity", {})
            return Opportunity(
                source=OpportunitySource(opp_data.get("source", "memory_user")),
                title=opp_data["title"],
                content=opp_data["content"],
                context=opp_data.get("context", ""),
                priority=opp_data.get("priority", 50),
                session_id=opp_data["session_id"],
                tags=opp_data.get("tags", []),
                related_uri=opp_data.get("related_uri", ""),
            )
        except Exception as e:
            logger.warning("Failed to parse opportunity: {} - {}", result, e)
            return None
