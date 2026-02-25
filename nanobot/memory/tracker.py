"""Opportunity tracker for managing proactive messages."""

import json
from datetime import datetime, timedelta
from typing import Optional

from loguru import logger

from nanobot.memory.opportunity import Opportunity, OpportunitySource, OpportunityStatus


class OpportunityTracker:
    """Track and manage opportunities, handle deduplication."""

    BASE_URI = "viking://user/proactive"

    def __init__(self, openviking_client):
        self.client = openviking_client
        self._cache: dict[str, Opportunity] = {}

    async def should_send(self, opportunity: Opportunity) -> bool:
        """
        Determine if message should be sent (deduplication check).

        Check logic:
        1. If similar message sent in last N days
        2. If follow-up type and not yet due
        3. If status is PENDING
        """
        # 1. Check for similar messages recently sent
        recent = await self._get_recent_sent(days=30)
        for sent in recent:
            if self._is_duplicate(opportunity, sent):
                # If follow-up type, check time interval
                if opportunity.source == OpportunitySource.FOLLOW_UP:
                    if not self._is_follow_up_due(opportunity, sent):
                        continue
                return False  # Duplicate, don't send

        # 2. Check status
        if opportunity.status != OpportunityStatus.PENDING:
            return False

        # 3. Check reminder count
        if opportunity.reminder_count >= 3:
            opportunity.status = OpportunityStatus.EXPIRED
            await self._save(opportunity)
            return False

        return True

    def _is_duplicate(self, new: Opportunity, existing: Opportunity) -> bool:
        """Check if two opportunities are duplicates."""
        # Check if tags intersect
        if set(new.tags) & set(existing.tags):
            return True

        # Check if titles are the same
        if new.title == existing.title:
            return True

        return False

    def _is_follow_up_due(self, new: Opportunity, existing: Opportunity) -> bool:
        """Check if follow-up is due."""
        if not existing.sent_at:
            return False

        sent_time = datetime.fromisoformat(existing.sent_at)
        days_since = (datetime.now() - sent_time).days

        return days_since >= new.follow_up_interval_days

    async def mark_sent(self, opportunity: Opportunity) -> None:
        """Mark message as sent."""
        opportunity.status = OpportunityStatus.SENT
        opportunity.sent_at = datetime.now().isoformat()
        opportunity.reminder_count += 1

        # Save to sent directory
        await self._save_to_sent(opportunity)

    async def create_follow_up(self, original: Opportunity, new_context: str) -> Opportunity:
        """Create follow-up opportunity for sent message."""
        follow_up = Opportunity(
            source=OpportunitySource.FOLLOW_UP,
            title=original.title,
            content=new_context,
            context=f"跟进: {original.title}",
            priority=original.priority,
            status=OpportunityStatus.PENDING,
            session_id=original.session_id,
            parent_id=original.id,
            tags=original.tags.copy(),
            follow_up_interval_days=original.follow_up_interval_days,
        )

        # Save to opportunities
        await self._save(follow_up)
        return follow_up

    async def get_pending_opportunities(self) -> list[Opportunity]:
        """Get pending opportunities sorted by priority."""
        opportunities = []
        try:
            # List opportunities directory
            if hasattr(self.client, "client"):
                results = await self.client.client.list(f"{self.BASE_URI}/opportunities")
                if hasattr(results, "items"):
                    for item in results.items:
                        if item.uri.endswith(".json"):
                            opp = await self._load_from_uri(item.uri)
                            if opp and opp.status == OpportunityStatus.PENDING:
                                opportunities.append(opp)
        except Exception as e:
            logger.warning("Failed to get pending opportunities: {}", e)

        # Sort by priority (higher first)
        opportunities.sort(key=lambda x: x.priority, reverse=True)
        return opportunities

    async def _get_recent_sent(self, days: int = 30) -> list[Opportunity]:
        """Get recently sent messages."""
        sent = []
        try:
            if hasattr(self.client, "client"):
                results = await self.client.client.list(f"{self.BASE_URI}/sent")
                if hasattr(results, "items"):
                    cutoff = datetime.now() - timedelta(days=days)
                    for item in results.items:
                        if item.uri.endswith(".json"):
                            opp = await self._load_from_uri(item.uri)
                            if opp and opp.sent_at:
                                sent_time = datetime.fromisoformat(opp.sent_at)
                                if sent_time >= cutoff:
                                    sent.append(opp)
        except Exception as e:
            logger.warning("Failed to get recent sent: {}", e)

        return sent

    async def _save(self, opportunity: Opportunity) -> None:
        """Save opportunity to storage."""
        uri = f"{self.BASE_URI}/opportunities/{opportunity.id}.json"
        data = json.dumps(opportunity.to_dict(), ensure_ascii=False)
        if hasattr(self.client, "client"):
            await self.client.client.set(uri, data)
        self._cache[opportunity.id] = opportunity

    async def _save_to_sent(self, opportunity: Opportunity) -> None:
        """Save to sent list."""
        uri = f"{self.BASE_URI}/sent/{opportunity.id}.json"
        data = json.dumps(opportunity.to_dict(), ensure_ascii=False)
        if hasattr(self.client, "client"):
            await self.client.client.set(uri, data)

    async def _load_from_uri(self, uri: str) -> Optional[Opportunity]:
        """Load opportunity from URI."""
        if uri in self._cache:
            return self._cache[uri]

        try:
            if hasattr(self.client, "client"):
                data = await self.client.client.get(uri)
                if data:
                    opp = Opportunity.from_dict(data)
                    self._cache[opp.id] = opp
                    return opp
        except Exception as e:
            logger.warning("Failed to load opportunity from {}: {}", uri, e)

        return None
