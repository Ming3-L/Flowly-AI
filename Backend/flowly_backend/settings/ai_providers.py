"""AI 提供方兼容变量（与 ``ai_engine.integrations.get_ai_provider_settings`` 同步）。"""

import os

try:
    from ai_engine.integrations import get_ai_provider_settings as _flowly_ai_settings

    _S = _flowly_ai_settings()
    VECTORENGINE_API_KEY = _S.language.vectorengine_api_key or os.getenv("VECTORENGINE_API_KEY", "")
    VECTORENGINE_BASE_URL = _S.language.vectorengine_base_url or os.getenv(
        "VECTORENGINE_BASE_URL", "https://api.vectorengine.cn/v1"
    )
    VECTORENGINE_MODEL = _S.language.vectorengine_model or os.getenv("VECTORENGINE_MODEL", "codex")
    OPENAI_API_KEY = _S.language.openai_api_key or os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL = _S.language.openai_model or os.getenv("OPENAI_MODEL", "gpt-4o")
    OPENAI_BASE_URL = _S.language.openai_base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    ANTHROPIC_API_KEY = _S.language.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL = _S.language.anthropic_model or os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
    OLLAMA_BASE_URL = _S.language.ollama_base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL = _S.language.ollama_model or os.getenv("OLLAMA_MODEL", "llama3")
except Exception:
    VECTORENGINE_API_KEY = os.getenv("VECTORENGINE_API_KEY", "")
    VECTORENGINE_BASE_URL = os.getenv("VECTORENGINE_BASE_URL", "https://api.vectorengine.cn/v1")
    VECTORENGINE_MODEL = os.getenv("VECTORENGINE_MODEL", "codex")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
    OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

USE_VECTORENGINE = bool(VECTORENGINE_API_KEY)


def get_ai_config():
    """返回当前默认聊天提供方（与 ``get_ai_provider_settings`` 逻辑一致）。"""
    if USE_VECTORENGINE:
        return {
            "provider": "vectorengine",
            "api_key": VECTORENGINE_API_KEY,
            "base_url": VECTORENGINE_BASE_URL,
            "model": VECTORENGINE_MODEL,
        }
    if OPENAI_API_KEY:
        return {
            "provider": "openai",
            "api_key": OPENAI_API_KEY,
            "base_url": OPENAI_BASE_URL,
            "model": OPENAI_MODEL,
        }
    return {
        "provider": "ollama",
        "base_url": OLLAMA_BASE_URL,
        "model": OLLAMA_MODEL,
    }
