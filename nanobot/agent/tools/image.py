"""Image generation tools for AI girlfriend."""

from __future__ import annotations

import base64
import time
from pathlib import Path
from typing import Any, Optional

from nanobot.agent.tools.base import Tool
from nanobot.memory.comfyui import ComfyUIClient


class TXT2IMGTool(Tool):
    """Text-to-image generation tool using ComfyUI."""

    name = "txt2img"
    description = "使用 AI 根据文本描述生成图片"

    def __init__(
        self,
        comfyui_client: Optional[ComfyUIClient] = None,
        output_dir: Optional[Path] = None,
    ):
        """Initialize txt2img tool.

        Args:
            comfyui_client: ComfyUI client for image generation
            output_dir: Directory to save generated images
        """
        self.comfyui_client = comfyui_client
        self.output_dir = output_dir or Path.cwd() / "data" / "images"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "图片描述文本（英文效果更好）",
                },
                "width": {
                    "type": "integer",
                    "default": 768,
                    "description": "图片宽度",
                },
                "height": {
                    "type": "integer",
                    "default": 1024,
                    "description": "图片高度",
                },
                "steps": {
                    "type": "integer",
                    "default": 20,
                    "description": "采样步数（越多越精细）",
                },
                "negative_prompt": {
                    "type": "string",
                    "default": "",
                    "description": "负面提示词（不想要的内容）",
                },
            },
            "required": ["prompt"],
        }

    async def execute(
        self,
        prompt: str,
        width: int = 768,
        height: int = 1024,
        steps: int = 20,
        negative_prompt: str = "",
        **kwargs: Any,
    ) -> str:
        """Generate an image from text prompt.

        Args:
            prompt: Positive prompt
            width: Image width
            height: Image height
            steps: Sampling steps
            negative_prompt: Negative prompt

        Returns:
            Result message with image path or error
        """
        if not self.comfyui_client:
            return "错误：ComfyUI 未配置，请联系管理员"

        try:
            image_bytes, error = await self.comfyui_client.generate(
                prompt=prompt,
                width=width,
                height=height,
                steps=steps,
                negative_prompt=negative_prompt,
            )

            if error:
                return f"图片生成失败：{error}"

            if image_bytes:
                # Save to file
                filename = f"generated_{int(time.time())}.png"
                filepath = self.output_dir / filename
                filepath.write_bytes(image_bytes)

                # Return base64 for display
                b64 = base64.b64encode(image_bytes).decode("utf-8")
                return f"图片已生成：{filename}\n\n![image](data:image/png;base64,{b64})"

            return "图片生成失败：未收到图片数据"

        except Exception as e:
            return f"图片生成出错：{str(e)}"


class PhotoAlbumTool(Tool):
    """Photo album tool for viewing generated images."""

    name = "photo_album"
    description = "查看已生成的图片相册"

    def __init__(self, image_dir: Optional[Path] = None):
        """Initialize photo album tool.

        Args:
            image_dir: Directory containing images
        """
        self.image_dir = image_dir or Path.cwd() / "data" / "images"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["list", "count", "latest"],
                    "default": "list",
                    "description": "操作：list=列出图片，count=数量，latest=最新图片",
                },
                "limit": {
                    "type": "integer",
                    "default": 10,
                    "description": "返回图片数量",
                },
            },
        }

    async def execute(self, action: str = "list", limit: int = 10, **kwargs: Any) -> str:
        """List or count photos in album.

        Args:
            action: Action to perform
            limit: Maximum number of images to return

        Returns:
            Result message
        """
        if not self.image_dir.exists():
            return "相册目录不存在"

        # Get all image files (support png, jpg, jpeg)
        images = sorted(
            list(self.image_dir.glob("*.png"))
            + list(self.image_dir.glob("*.jpg"))
            + list(self.image_dir.glob("*.jpeg")),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        if action == "count":
            return f"相册共有 {len(images)} 张图片"

        if action == "latest":
            if not images:
                return "相册为空"
            latest = images[0]
            b64 = base64.b64encode(latest.read_bytes()).decode("utf-8")
            return f"最新图片：{latest.name}\n\n![image](data:image/png;base64,{b64})"

        # Default: list
        if not images:
            return "相册为空"

        result = f"相册共有 {len(images)} 张图片，最近 {min(limit, len(images))} 张：\n\n"
        for img in images[:limit]:
            result += f"- {img.name} ({img.stat().st_size // 1024}KB)\n"

        return result
