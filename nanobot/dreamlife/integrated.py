"""DreamLife integration for smart proactive messaging."""

from typing import TYPE_CHECKING

from nanobot.memory.opportunity import Opportunity, OpportunitySource, OpportunityStatus
from nanobot.memory.tracker import OpportunityTracker

if TYPE_CHECKING:
    from nanobot.dreamlife.service import DreamLifeService


class DreamLifeIntegration:
    """DreamLife and SmartProactive integration."""

    def __init__(self, dreamlife_service: "DreamLifeService", tracker: OpportunityTracker):
        self.dreamlife_service = dreamlife_service
        self.tracker = tracker

    async def get_shareable_moments(self, session_id: str = "default") -> list[Opportunity]:
        """Get shareable life moments as opportunities.

        Args:
            session_id: The session ID to associate with the opportunity.
        """
        opportunities = []

        # 1. Check if there's anything worth sharing today
        try:
            summary = await self.dreamlife_service.get_daily_summary()
            if summary and "没什么特别" not in summary:
                # Generate opportunity
                opp = Opportunity(
                    source=OpportunitySource.DREAMLIFE,
                    title="今日生活分享",
                    content=summary,
                    context=f"今天的生活: {summary}",
                    priority=50,  # Medium priority
                    status=OpportunityStatus.PENDING,
                    session_id=session_id,
                    tags=["dreamlife", "daily"],
                )
                opportunities.append(opp)
        except Exception:
            pass

        # 2. Check if there's a follow-up to share
        # (if user responded/had follow-up after previous share)

        return opportunities

    async def generate_share_message(self) -> str | None:
        """Generate a share message from DreamLife."""
        try:
            message, _ = await self.dreamlife_service.generate_share_moment()
            return message
        except Exception:
            return None
