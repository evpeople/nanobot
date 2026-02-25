"""Memory configuration module."""

from pydantic import BaseModel


class SmartProactiveConfig(BaseModel):
    """Smart proactive messaging configuration."""

    # Basic switch
    enabled: bool = False

    # Frequency control
    max_per_day: int = 3  # Max proactive messages per day
    min_interval_hours: int = 4  # Min interval between messages

    # Explorer configuration
    explore_interval_minutes: int = 30  # Exploration interval (minutes)
    max_sessions_per_explore: int = 5  # Sessions per exploration
    max_opportunities_per_explore: int = 10  # Max opportunities per exploration
    opportunity_ttl_days: int = 30  # Opportunity TTL

    # Explorer Agent config
    explorer_model: str = "gpt-4o-mini"  # Explorer model
    explorer_temperature: float = 0.7  # Explorer temperature
    explorer_max_iterations: int = 10  # Explorer max iterations

    # Deduplication config
    duplicate_check_days: int = 30  # Duplicate check window (days)
    follow_up_enabled: bool = True  # Enable follow-up mechanism
    follow_up_interval_days: int = 7  # Default follow-up interval (days)
    max_reminders: int = 3  # Max reminder count

    # LLM config (message generation)
    use_llm_generation: bool = True  # Use LLM for message generation
    llm_model: str = "gpt-4o-mini"  # Model for message generation
    llm_temperature: float = 0.8  # Message generation temperature

    # AI persona (for message generation)
    ai_name: str = "Luna"
    relationship: str = "女朋友"

    # DreamLife integration
    dreamlife_share_enabled: bool = True  # Enable DreamLife sharing
    dreamlife_share_weight: float = 0.3  # DreamLife content weight (0-1)


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
    proactive_mode: str = "simple"  # simple / smart

    # 智能主动关怀 (Phase 10)
    smart_proactive: SmartProactiveConfig = SmartProactiveConfig()

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
