"""Characters management for DreamLife."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional


class Character:
    """Represents a character in AI's life."""

    def __init__(
        self,
        name: str,
        relationship: str,
        description: str = "",
        first_met: Optional[str] = None,
        last_interaction: Optional[str] = None,
        interaction_count: int = 0,
    ):
        self.name = name
        self.relationship = relationship  # e.g., "闺蜜", "妈妈", "同学"
        self.description = description
        self.first_met = first_met or datetime.now().isoformat()
        self.last_interaction = last_interaction
        self.interaction_count = interaction_count

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "relationship": self.relationship,
            "description": self.description,
            "first_met": self.first_met,
            "last_interaction": self.last_interaction,
            "interaction_count": self.interaction_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Character:
        """Create from dictionary."""
        return cls(
            name=data["name"],
            relationship=data["relationship"],
            description=data.get("description", ""),
            first_met=data.get("first_met"),
            last_interaction=data.get("last_interaction"),
            interaction_count=data.get("interaction_count", 0),
        )

    def record_interaction(self, note: str = "") -> None:
        """Record an interaction with this character."""
        self.last_interaction = datetime.now().isoformat()
        self.interaction_count += 1
        if note:
            self.description += f"\n[{datetime.now().date()}]: {note}"


class CharactersManager:
    """Manages characters in AI's dream life."""

    BASE_URI = "viking://user/ai_life/characters"

    def __init__(self, openviking_client):
        """Initialize the characters manager.

        Args:
            openviking_client: OpenViking client instance
        """
        self.client = openviking_client

    def _character_uri(self, name: str) -> str:
        """Get the URI for a character."""
        return f"{self.BASE_URI}/{name}.json"

    async def add_character(
        self,
        name: str,
        relationship: str,
        description: str = "",
    ) -> Character:
        """Add a new character.

        Args:
            name: Character name
            relationship: Relationship type (闺蜜, 妈妈, etc.)
            description: Character description

        Returns:
            The created Character instance
        """
        character = Character(
            name=name,
            relationship=relationship,
            description=description,
        )

        uri = self._character_uri(name)
        await self.client.set(uri, json.dumps(character.to_dict()))

        return character

    async def get_character(self, name: str) -> Optional[Character]:
        """Get a character by name.

        Args:
            name: Character name

        Returns:
            Character instance or None if not found
        """
        uri = self._character_uri(name)
        try:
            data = await self.client.get(uri)
            if data:
                return Character.from_dict(json.loads(data))
        except Exception:
            pass
        return None

    async def update_character(self, character: Character) -> None:
        """Update a character's information.

        Args:
            character: Character to update
        """
        uri = self._character_uri(character.name)
        await self.client.set(uri, json.dumps(character.to_dict()))

    async def list_characters(self) -> list[Character]:
        """List all characters.

        Returns:
            List of all characters
        """
        try:
            # List all characters under BASE_URI
            results = await self.client.list(prefix=self.BASE_URI)
            characters = []
            for item in results:
                try:
                    data = await self.client.get(item)
                    if data:
                        characters.append(Character.from_dict(json.loads(data)))
                except Exception:
                    continue
            return characters
        except Exception:
            return []

    async def delete_character(self, name: str) -> bool:
        """Delete a character.

        Args:
            name: Character name

        Returns:
            True if deleted, False if not found
        """
        uri = self._character_uri(name)
        try:
            await self.client.delete(uri)
            return True
        except Exception:
            return False

    async def record_interaction(
        self,
        character_name: str,
        note: str = "",
    ) -> bool:
        """Record an interaction with a character.

        Args:
            character_name: Character name
            note: Optional note about the interaction

        Returns:
            True if successful, False otherwise
        """
        character = await self.get_character(character_name)
        if not character:
            return False

        character.record_interaction(note)
        await self.update_character(character)
        return True
