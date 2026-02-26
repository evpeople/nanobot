"""Smart proactive service for AI girlfriend."""

import asyncio
import random
from datetime import datetime
from typing import TYPE_CHECKING, Protocol

from loguru import logger

from nanobot.memory.config import SmartProactiveConfig
from nanobot.memory.explorer_agent import ExplorerAgent
from nanobot.memory.opportunity import Opportunity, OpportunitySource
from nanobot.memory.tracker import OpportunityTracker

if TYPE_CHECKING:
    from nanobot.dreamlife.integrated import DreamLifeIntegration
    from nanobot.providers.base import LLMProvider


class MessageSender(Protocol):
    """Protocol for sending messages to users."""

    async def send(self, session_id: str, message: str) -> None:
        """Send a message to a session."""
        ...


class SmartProactiveService:
    """Smart proactive messaging service.

    Core flow:
    1. pulse_check() is called periodically (reuse HeartbeatService)
    2. Call ExplorerAgent to explore memory (AI-driven)
    3. DreamLifeIntegration gets shareable moments
    4. OpportunityTracker filters and deduplicates
    5. Generate natural message content
    6. Send message and record status

    Reuse design:
    - Use HeartbeatService pulse mechanism
    - Use existing nanobot LLM Provider
    - Use ToolRegistry for Explorer tools
    """

    def __init__(
        self,
        config: SmartProactiveConfig,
        openviking_client,
        sender: MessageSender,
        llm_provider: "LLMProvider | None" = None,
        dreamlife_service=None,
    ):
        self.config = config
        self.client = openviking_client
        self.sender = sender
        self.llm_provider = llm_provider

        # Components: Use ExplorerAgent (AI-driven)
        if llm_provider:
            self.explorer = ExplorerAgent(
                provider=llm_provider,
                openviking_client=openviking_client,
                config=config,
                model=config.explorer_model,
                temperature=config.explorer_temperature,
            )
        else:
            self.explorer = None

        self.tracker = OpportunityTracker(openviking_client)

        # DreamLife integration - lazy import to avoid circular dependency
        self.dreamlife_service = dreamlife_service
        if dreamlife_service and config.dreamlife_share_enabled:
            from nanobot.dreamlife.integrated import DreamLifeIntegration

            self.dreamlife_integration = DreamLifeIntegration(dreamlife_service, self.tracker)
        else:
            self.dreamlife_integration = None

        # State
        self._today_count: dict[datetime.date, int] = {}
        self._last_explore_time: datetime | None = None
        self._explore_lock = asyncio.Lock()

    def _should_explore(self) -> bool:
        """Determine if should explore."""
        if not self._last_explore_time:
            return True

        minutes_since = (datetime.now() - self._last_explore_time).total_seconds() / 60
        return minutes_since >= self.config.explore_interval_minutes

    async def pulse_check(self) -> list[str]:
        """Execute pulse check (called by HeartbeatService)."""
        if not self.config.enabled:
            return []

        sent_messages: list[str] = []

        # 1. Check daily limit
        today = datetime.now().date()
        today_count = self._today_count.get(today, 0)
        if today_count >= self.config.max_per_day:
            return []

        # 2. Check explore interval (avoid frequent exploration)
        if self._should_explore():
            async with self._explore_lock:
                # Double check
                if self._should_explore():
                    await self._explore_and_queue()

        # 3. Get pending opportunities
        opportunities = await self._get_pending_opportunities()

        # 4. Send messages
        for opp in opportunities:
            if today_count >= self.config.max_per_day:
                break

            if await self.tracker.should_send(opp):
                message = await self._generate_message(opp)
                await self.sender.send(opp.session_id, message)
                await self.tracker.mark_sent(opp)

                # 5. Create follow-up opportunity
                if self.config.follow_up_enabled:
                    await self._create_follow_up_opportunity(opp)

                sent_messages.append(opp.session_id)
                today_count += 1

        self._today_count[today] = today_count
        return sent_messages

    async def _explore_and_queue(self) -> None:
        """Explore memory and generate opportunities (using ExplorerAgent)."""
        # Get active sessions
        sessions = await self._get_active_sessions()

        for session_id in sessions:
            # Use ExplorerAgent (AI-driven exploration)
            if self.explorer:
                opportunities = await self.explorer.run(session_id)

                # Save to storage
                for opp in opportunities:
                    await self.tracker._save(opp)

        # Get DreamLife shareable moments if enabled
        if self.dreamlife_integration and self.config.dreamlife_share_enabled:
            try:
                # Use the first session for DreamLife sharing
                default_session = sessions[0] if sessions else "default"
                dreamlife_opportunities = await self.dreamlife_integration.get_shareable_moments(
                    default_session
                )
                for opp in dreamlife_opportunities:
                    await self.tracker._save(opp)
            except Exception as e:
                logger.warning("DreamLife exploration failed: {}", e)

        self._last_explore_time = datetime.now()
        logger.info("ExplorerAgent: Exploration complete, processed {} sessions", len(sessions))

    async def _get_active_sessions(self) -> list[str]:
        """Get active sessions to explore."""
        # Get sessions with recent conversations
        try:
            if hasattr(self.client, "client"):
                sessions = await self.client.client.list_sessions()
                # Filter and sort, get recent N
                if hasattr(sessions, "items"):
                    session_list = [
                        {"session_id": s.uri.split("/")[-1], "updated_at": ""}
                        for s in sessions.items
                    ]
                else:
                    session_list = sessions

                recent = sorted(session_list, key=lambda x: x.get("updated_at", ""), reverse=True)
                return [s["session_id"] for s in recent[: self.config.max_sessions_per_explore]]
        except Exception as e:
            logger.warning("Failed to get sessions: {}", e)

        return []

    async def _get_pending_opportunities(self) -> list[Opportunity]:
        """Get pending opportunities (sorted by priority)."""
        return await self.tracker.get_pending_opportunities()

    async def _create_follow_up_opportunity(self, original: Opportunity) -> None:
        """Create follow-up opportunity for sent message."""
        # Automatically create follow-up after 7 days
        follow_up = await self.tracker.create_follow_up(original, "")
        logger.info("Created follow-up opportunity: {}", follow_up.id)

    async def _generate_message(self, opportunity: Opportunity) -> str:
        """Generate natural proactive message from opportunity."""
        if self.llm_provider and self.config.use_llm_generation:
            return await self._generate_with_llm(opportunity)

        # Template fallback
        return self._generate_with_template(opportunity)

    async def _generate_with_llm(self, opportunity: Opportunity) -> str:
        """Use LLM to generate more natural message."""
        prompt = f"""你是 {self.config.ai_name}，用户的 {self.config.relationship}。
你最近想起了一件事想要和用户分享/关心用户。

机会点信息:
- 标题: {opportunity.title}
- 上下文: {opportunity.context}
- 内容: {opportunity.content}
- 来源: {opportunity.source.value}

请生成一条自然的、符合你人设的主动消息。
要求:
- 50-100 字
- 语气自然，像真实女朋友/男朋友
- 可以适当撒个小娇
- 不要生硬地提起，试着自然地引入话题
- 如果是"跟进"类型，要像突然想起的样子

直接输出消息内容，不要加引号，不要有前缀。"""

        response = await self.llm_provider.chat(
            messages=[{"role": "user", "content": prompt}],
            model=self.config.llm_model,
        )
        return response.content

    def _generate_with_template(self, opportunity: Opportunity) -> str:
        """Generate message with template (fallback without LLM)."""
        templates = {
            OpportunitySource.MEMORY_USER: [
                "对了~你之前说的 {title} 怎么样了呀？",
                "想起来啦，你之前 {content}，后来呢？",
                "问你哦~ {title} 那个事情~",
            ],
            OpportunitySource.DREAMLIFE: [
                "告诉你哦，我今天 {content}",
                "刚才发生了一件有趣的事~ {content}",
            ],
            OpportunitySource.FOLLOW_UP: [
                "突然想起来~ {title} 那个后来怎样啦？",
            ],
        }

        source_templates = templates.get(
            opportunity.source, templates[OpportunitySource.MEMORY_USER]
        )
        template = random.choice(source_templates)
        return template.format(
            title=opportunity.title,
            content=opportunity.content,
            context=opportunity.context,
        )
