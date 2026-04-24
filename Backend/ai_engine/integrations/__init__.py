"""
integrations 包：与外部 AI / 媒体服务对接时的配置边界。

通过 ``secrets_loader`` 统一加载：优先环境变量，其次 ``project_secrets_local.py``。
不包含网络请求或 SDK 初始化逻辑。
"""

from ai_engine.integrations.secrets_loader import (
    AIProviderSettings,
    AudioModelSettings,
    EmbeddingModelSettings,
    ImageModelSettings,
    LanguageModelSettings,
    VideoModelSettings,
    clear_local_secrets_cache,
    get_ai_provider_settings,
)

__all__ = [
    "AIProviderSettings",
    "AudioModelSettings",
    "EmbeddingModelSettings",
    "ImageModelSettings",
    "LanguageModelSettings",
    "VideoModelSettings",
    "clear_local_secrets_cache",
    "get_ai_provider_settings",
]
