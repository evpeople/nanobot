"""DreamLife configuration module."""

from pydantic import BaseModel


class DreamLifeConfig(BaseModel):
    """DreamLife service configuration."""

    # Enable/disable
    enabled: bool = False

    # Share frequency (times per week)
    share_frequency: int = 3

    # Include images in shares
    include_images: bool = True

    # Important characters in AI's life
    characters: list[str] = ["小美"]

    # OpenViking storage path
    storage_path: str = "~/.nanobot/openviking"
