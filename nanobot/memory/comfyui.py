"""ComfyUI client for text-to-image generation."""

from __future__ import annotations

import asyncio
import json
import random
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import aiohttp

if TYPE_CHECKING:
    from loguru import Logger


class ComfyUIClient:
    """Async ComfyUI client for text-to-image generation."""

    DEFAULT_WORKFLOW = "workflow_api.json"

    def __init__(
        self,
        server_address: str = "127.0.0.1:8188",
        workflow_dir: Optional[Path] = None,
        default_width: int = 768,
        default_height: int = 1024,
        default_steps: int = 20,
        negative_prompt: str = "",
        logger: Optional["Logger"] = None,
    ):
        """Initialize ComfyUI client.

        Args:
            server_address: ComfyUI server address (e.g., "127.0.0.1:8188")
            workflow_dir: Directory containing workflow JSON files
            default_width: Default image width
            default_height: Default image height
            default_steps: Default sampling steps
            negative_prompt: Default negative prompt
            logger: Optional logger
        """
        self.server_address = server_address
        self.url = f"http://{server_address}"
        self.workflow_dir = workflow_dir or Path.cwd() / "data" / "comfyui_workflows"

        self.default_width = default_width
        self.default_height = default_height
        self.default_steps = default_steps
        self.negative_prompt = negative_prompt

        # Node IDs for workflow injection
        self.input_id = "6"
        self.neg_node_id = ""
        self.output_id = ""

        self._logger = logger

    def _log(self, level: str, msg: str) -> None:
        """Log a message."""
        if self._logger:
            getattr(self._logger, level)(f"[ComfyUI] {msg}")
        else:
            print(f"[ComfyUI] {msg}")

    def reload_config(
        self,
        filename: str = "workflow_api.json",
        input_id: Optional[str] = None,
        output_id: Optional[str] = None,
        neg_node_id: Optional[str] = None,
    ) -> bool:
        """Reload workflow configuration.

        Args:
            filename: Workflow filename
            input_id: Input node ID
            output_id: Output node ID
            neg_node_id: Negative prompt node ID

        Returns:
            True if workflow file exists
        """
        self.workflow_path = self.workflow_dir / filename

        if input_id:
            self.input_id = str(input_id)
        if output_id:
            self.output_id = str(output_id)
        if neg_node_id:
            self.neg_node_id = str(neg_node_id)

        exists = self.workflow_path.exists()
        self._log(
            "info",
            f"Workflow: {filename} | Input: {self.input_id} | "
            f"Neg: {self.neg_node_id} | Output: {self.output_id or 'auto'}",
        )
        return exists

    def _load_workflow(self) -> dict:
        """Load workflow JSON from file.

        Returns:
            Workflow dictionary
        """
        if not hasattr(self, "workflow_path") or not self.workflow_path.exists():
            raise FileNotFoundError(f"Workflow file not found: {getattr(self, 'workflow_path', 'unknown')}")

        with open(self.workflow_path, encoding="utf-8") as f:
            return json.load(f)

    def _inject_params(
        self,
        workflow: dict,
        prompt: str,
        width: int,
        height: int,
        steps: int,
        negative_prompt: str = "",
    ) -> None:
        """Inject parameters into workflow.

        Args:
            workflow: Workflow dictionary
            prompt: Positive prompt
            width: Image width
            height: Image height
            steps: Sampling steps
            negative_prompt: Negative prompt
        """
        # Inject positive prompt
        node = workflow.get(self.input_id)
        if node:
            inputs = node.get("inputs", {})
            for key in ("text", "opt_text", "string", "text_positive", "positive", "prompt", "wildcard_text"):
                if key in inputs:
                    inputs[key] = prompt
                    break

        # Inject negative prompt (use parameter or fallback to default)
        neg_prompt = negative_prompt or self.negative_prompt
        if self.neg_node_id and neg_prompt:
            neg_node = workflow.get(self.neg_node_id)
            if neg_node:
                n_inputs = neg_node.get("inputs", {})
                for key in ("text", "string", "negative", "text_negative", "prompt"):
                    if key in n_inputs:
                        existing = str(n_inputs.get(key, "")).strip()
                        if existing:
                            n_inputs[key] = f"{existing}, {neg_prompt}"
                        else:
                            n_inputs[key] = neg_prompt
                        break

        # Randomize seeds and inject dimensions/steps
        base_seed = random.randint(1, 999999999999999)
        offset = 0

        for node_id, node_data in workflow.items():
            if not isinstance(node_data, dict):
                continue
            n_inputs = node_data.get("inputs", {})
            if not isinstance(n_inputs, dict):
                continue

            # Randomize seeds
            if "seed" in n_inputs:
                n_inputs["seed"] = base_seed + offset
                offset += 1
            if "noise_seed" in n_inputs:
                n_inputs["noise_seed"] = base_seed + offset
                offset += 1

            # Inject dimensions
            if "width" in n_inputs:
                n_inputs["width"] = width
            if "height" in n_inputs:
                n_inputs["height"] = height
            if "steps" in n_inputs:
                n_inputs["steps"] = steps

    async def generate(
        self,
        prompt: str,
        width: Optional[int] = None,
        height: Optional[int] = None,
        steps: Optional[int] = None,
        negative_prompt: Optional[str] = None,
    ) -> tuple[Optional[bytes], Optional[str]]:
        """Generate an image from text prompt.

        Args:
            prompt: Positive prompt
            width: Image width (default from config)
            height: Image height (default from config)
            steps: Sampling steps (default from config)
            negative_prompt: Override default negative prompt

        Returns:
            Tuple of (image_bytes, error_message)
        """
        width = width or self.default_width
        height = height or self.default_height
        steps = steps or self.default_steps

        client_id = str(random.randint(100000, 999999))

        try:
            workflow = self._load_workflow()
        except Exception as e:
            return None, f"Failed to load workflow: {e}"

        # Inject parameters
        self._inject_params(workflow, prompt, width, height, steps, negative_prompt)

        payload = {"prompt": workflow, "client_id": client_id}
        self._log("info", f"Generating image | Prompt: {prompt[:50]}...")

        try:
            async with aiohttp.ClientSession() as session:
                # Submit prompt
                async with session.post(
                    f"{self.url}/prompt",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=300),
                ) as resp:
                    if resp.status != 200:
                        return None, f"Request failed: HTTP {resp.status}"
                    res_json = await resp.json()
                    prompt_id = res_json.get("prompt_id")

                if not prompt_id:
                    return None, "Server did not return prompt_id"

                # Poll for completion
                for _ in range(300):
                    await asyncio.sleep(1)
                    try:
                        async with session.get(
                            f"{self.url}/history/{prompt_id}",
                            timeout=aiohttp.ClientTimeout(total=10),
                        ) as h_resp:
                            if h_resp.status != 200:
                                continue
                            history = await h_resp.json()
                    except Exception:
                        continue

                    if prompt_id in history:
                        outputs = history[prompt_id].get("outputs", {})
                        img_info = None

                        # Find output image
                        if self.output_id and self.output_id in outputs:
                            imgs = outputs[self.output_id].get("images", [])
                            if imgs:
                                img_info = imgs[0]

                        if not img_info:
                            for node_out in outputs.values():
                                if isinstance(node_out, dict) and "images" in node_out and node_out["images"]:
                                    img_info = node_out["images"][0]
                                    break

                        if img_info:
                            fname = img_info["filename"]
                            sfolder = img_info.get("subfolder", "")
                            itype = img_info.get("type", "output")
                            img_url = f"{self.url}/view?filename={fname}&subfolder={sfolder}&type={itype}"

                            async with session.get(img_url) as img_res:
                                if img_res.status == 200:
                                    self._log("info", f"Image generated: {fname}")
                                    return await img_res.read(), None
                                else:
                                    return None, f"Failed to download image: HTTP {img_res.status}"
                        else:
                            return None, "No output image found"

                return None, "Generation timeout"

        except asyncio.TimeoutError:
            return None, "Request timeout"
        except aiohttp.ClientError as e:
            return None, f"Network error: {e}"
        except Exception as e:
            return None, f"Generation failed: {e}"
