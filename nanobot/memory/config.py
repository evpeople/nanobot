"""Memory configuration module."""

from pydantic import BaseModel


class MemoryConfig(BaseModel):
    """Memory service configuration."""

    # 基础开关
    enabled: bool = True

    # OpenViking
    storage_path: str = "~/.nanobot/openviking"

    # Commit 策略
    auto_commit: bool = True
    commit_threshold: int = 10  # 每 N 条消息自动 commit
    commit_idle_timeout_minutes: int = 10  # 空闲超时 commit

    # 检索策略
    search_limit: int = 5
    retrieval_strategy: str = "keyword"  # keyword / always / never
    keyword_triggers: str = "还记得,上次,以前"
    keyword_skips: str = "哈哈好啊好的"

    # 主动关怀
    proactive_enabled: bool = False
    proactive_pulse_interval: int = 60  # 心跳检查间隔（秒）
    proactive_max_per_day: int = 3  # 每日最多主动消息数
    proactive_min_interval_hours: int = 6  # 最小主动消息间隔

    # 照片墙
    photo_album_enabled: bool = True
    photo_album_max_count: int = 100

    # ComfyUI 文生图
    comfyui_enabled: bool = False
    comfyui_server_address: str = "127.0.0.1:8188"
    comfyui_workflow_dir: str = "data/comfyui_workflows"
    comfyui_default_width: int = 768
    comfyui_default_height: int = 1024
    comfyui_default_steps: int = 20
    comfyui_negative_prompt: str = ""
