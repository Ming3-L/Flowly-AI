"""
AI 相关密钥与端点配置的**唯一封装入口**。

数据来源（按优先级）
--------------------
1. **数据库** ``PlatformAIProviderSecrets``（单例加密存储；后台管理员维护）— 某 key 非空则优先。
2. 进程环境变量（可由 ``Backend/.env`` 注入）。
3. ``project_secrets_local.py``（从 ``project_secrets_local.example.py`` 复制，已 gitignore）。
4. 代码内默认值（仅少量非敏感项）。

返回结构 ``AIProviderSettings`` 按**能力维度**分组（语言 / 图片 / 音频 / 视频 / 向量），
便于工作流里不同节点各取所需。业务代码请统一使用 ``get_ai_provider_settings()``。

与数据库的关系
--------------
``WorkflowGraphNode.config`` 等 JSON 不得存放 API Key；平台级密钥来自数据库或本模块路径。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Final

# 与 ``project_secrets_local.example.py`` 中模块级变量名一致（亦可用作环境变量名）
_LOCAL_ENV_KEYS: Final[tuple[str, ...]] = (
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "OPENAI_MODEL",
    "OPENAI_VISION_MODEL",
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_MODEL",
    "OLLAMA_BASE_URL",
    "OLLAMA_MODEL",
    "VECTORENGINE_API_KEY",
    "VECTORENGINE_BASE_URL",
    "VECTORENGINE_MODEL",
    "GOOGLE_API_KEY",
    "GOOGLE_GEMINI_MODEL",
    "GOOGLE_API_BASE_URL",
    "AZURE_OPENAI_API_KEY",
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_DEPLOYMENT_CHAT",
    "AZURE_OPENAI_DEPLOYMENT_EMBEDDINGS",
    "AZURE_OPENAI_API_VERSION",
    "DEEPSEEK_API_KEY",
    "DEEPSEEK_BASE_URL",
    "DEEPSEEK_MODEL",
    "MOONSHOT_API_KEY",
    "MOONSHOT_BASE_URL",
    "MOONSHOT_MODEL",
    "DOUBAO_API_KEY",
    "ARK_API_KEY",
    "DOUBAO_ARK_BASE_URL",
    "DOUBAO_ARK_MODEL",
    "DOUBAO_ARK_SMART_ROUTER_ENDPOINT",
    "OPENAI_IMAGE_MODEL",
    "STABILITY_API_KEY",
    "STABILITY_BASE_URL",
    "REPLICATE_API_TOKEN",
    "ELEVENLABS_API_KEY",
    "ELEVENLABS_DEFAULT_VOICE_ID",
    "ASSEMBLYAI_API_KEY",
    "OPENAI_WHISPER_MODEL",
    "RUNWAY_API_KEY",
    "RUNWAY_BASE_URL",
    "OPENAI_EMBEDDING_MODEL",
    "COHERE_API_KEY",
    "COHERE_EMBEDDING_MODEL",
    "JINA_API_KEY",
    "VOYAGE_API_KEY",
    "VOYAGE_EMBEDDING_MODEL",
    # 行为开关（与 workflow 中 openai 默认走方舟一致）
    "FLOWLY_USE_DOUBAO_DEFAULT",
    # ── 豆包语音（OpenSpeech，独立鉴权）─────────────────────────────────────
    "OPENSPEECH_APPID",
    "OPENSPEECH_ACCESS_TOKEN",
    "OPENSPEECH_API_KEY",
    "OPENSPEECH_TTS_URL",
    "OPENSPEECH_CLUSTER",
    "OPENSPEECH_VOICE_TYPE",
    # 管理员可维护的 TTS 音色列表（JSON 字符串）
    "OPENSPEECH_TTS_VOICES_JSON",
    # v3 / seed-tts-2.0 默认 speaker 与音色列表（JSON 字符串）
    "OPENSPEECH_TTS2_SPEAKER",
    "OPENSPEECH_TTS2_VOICES_JSON",
    # ASR（当前仅存储，后续接入）
    "OPENSPEECH_ASR_STREAM_CLUSTER",
    "OPENSPEECH_ASR_FILE_CLUSTER",
    # OpenSpeech ASR v3 WebSocket（bigmodel_nostream 等）
    "OPENSPEECH_ASR_WS_URL",
    "OPENSPEECH_ASR_RESOURCE_ID",
    "OPENSPEECH_ASR_MODEL_NAME",
    "OPENSPEECH_ASR_LANGUAGE",
    "OPENSPEECH_ASR_AUDIO_RATE",
    "OPENSPEECH_AUC_SUBMIT_URL",
    "OPENSPEECH_AUC_QUERY_URL",
    "OPENSPEECH_AUC_RESOURCE_ID",
)

_local_overrides_cache: dict[str, str] | None = None
_db_overrides_cache: dict[str, str] | None = None


def _load_local_module_overrides() -> dict[str, str]:
    """从 ``project_secrets_local`` 读取与 ``_LOCAL_ENV_KEYS`` 同名的变量。"""
    global _local_overrides_cache
    if _local_overrides_cache is not None:
        return _local_overrides_cache
    try:
        from ai_engine.integrations import project_secrets_local as pl
    except ImportError:
        _local_overrides_cache = {}
        return _local_overrides_cache
    out: dict[str, str] = {}
    for key in _LOCAL_ENV_KEYS:
        raw = getattr(pl, key, "")
        out[key] = "" if raw is None else str(raw)
    _local_overrides_cache = out
    return _local_overrides_cache


def clear_local_secrets_cache() -> None:
    """清除本地模块与数据库解析缓存（测试、保存平台配置后调用）。"""
    global _local_overrides_cache, _db_overrides_cache
    _local_overrides_cache = None
    _db_overrides_cache = None


def _load_db_overrides() -> dict[str, str]:
    """进程内缓存的数据库覆盖项（解密后）。"""
    global _db_overrides_cache
    if _db_overrides_cache is not None:
        return _db_overrides_cache
    try:
        from ai_engine.integrations.db_platform_secrets import load_plain_entries

        _db_overrides_cache = load_plain_entries()
    except Exception:
        _db_overrides_cache = {}
    return _db_overrides_cache


def managed_ai_config_key_names() -> tuple[str, ...]:
    """与平台后台可编辑项一致的环境变量名列表。"""
    return _LOCAL_ENV_KEYS


def describe_managed_keys_for_admin() -> list[dict[str, str | bool]]:
    """管理员只读状态：每项当前生效层与是否非空（不返回明文）。"""
    db = _load_db_overrides()
    rows: list[dict[str, str | bool]] = []
    for key in _LOCAL_ENV_KEYS:
        in_db = key in db and str(db.get(key, "")).strip() != ""
        env_raw = os.environ.get(key)
        env_set = env_raw is not None and str(env_raw).strip() != ""
        loc = _load_local_module_overrides().get(key, "")
        local_set = str(loc).strip() != ""

        if in_db:
            winning = "database"
        elif env_set:
            winning = "environment"
        elif local_set:
            winning = "local_file"
        else:
            winning = "default"

        eff = _resolve(key, default="")
        rows.append(
            {
                "key": key,
                "winning_source": winning,
                "is_effective_non_empty": bool(str(eff).strip()),
            }
        )
    return rows


def _resolve(name: str, *, default: str = "") -> str:
    """数据库非空优先，其次环境变量，其次 ``project_secrets_local``，否则 ``default``。"""
    db_map = _load_db_overrides()
    if name in db_map:
        db_raw = db_map.get(name, "")
        if str(db_raw).strip() != "":
            return str(db_raw).strip()
    env_raw = os.environ.get(name)
    if env_raw is not None and str(env_raw).strip() != "":
        return str(env_raw).strip()
    local_val = _load_local_module_overrides().get(name, "")
    if str(local_val).strip() != "":
        return str(local_val).strip()
    return default


def _doubao_ark_api_key() -> str:
    """豆包/火山方舟：``DOUBAO_API_KEY`` 与 ``ARK_API_KEY`` 任一非空即可。"""
    for key in ("DOUBAO_API_KEY", "ARK_API_KEY"):
        v = _resolve(key)
        if v:
            return v
    return ""


# -----------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class LanguageModelSettings:
    """语言类：对话、Agent、工具调用；视觉模型字段用于多模态理解（与 chat 可同厂商）。"""

    openai_api_key: str
    openai_base_url: str
    openai_model: str
    openai_vision_model: str
    anthropic_api_key: str
    anthropic_model: str
    ollama_base_url: str
    ollama_model: str
    vectorengine_api_key: str
    vectorengine_base_url: str
    vectorengine_model: str
    google_api_key: str
    google_gemini_model: str
    google_api_base_url: str
    azure_openai_api_key: str
    azure_openai_endpoint: str
    azure_openai_deployment_chat: str
    azure_openai_api_version: str
    deepseek_api_key: str
    deepseek_base_url: str
    deepseek_model: str
    moonshot_api_key: str
    moonshot_base_url: str
    moonshot_model: str
    doubao_ark_api_key: str
    doubao_ark_base_url: str
    doubao_ark_model: str
    doubao_ark_smart_router_endpoint: str
    flowly_use_doubao_default: str


@dataclass(frozen=True, slots=True)
class ImageModelSettings:
    """图片类：文生图 / 图生图等。OpenAI 图像接口通常复用 ``language.openai_api_key``。"""

    openai_image_model: str
    stability_api_key: str
    stability_base_url: str
    replicate_api_token: str


@dataclass(frozen=True, slots=True)
class AudioModelSettings:
    """音频类：TTS、语音识别等。"""

    elevenlabs_api_key: str
    elevenlabs_default_voice_id: str
    assemblyai_api_key: str
    openai_whisper_model: str


@dataclass(frozen=True, slots=True)
class OpenSpeechSettings:
    """豆包语音（OpenSpeech）独立鉴权与默认参数。"""

    appid: str
    access_token: str
    api_key: str
    tts_url: str
    tts_cluster: str
    tts_voice_type: str
    tts_voices_json: str
    tts2_speaker: str
    tts2_voices_json: str
    asr_stream_cluster: str
    asr_file_cluster: str
    asr_ws_url: str
    asr_resource_id: str
    asr_model_name: str
    asr_language: str
    asr_audio_rate: int
    auc_submit_url: str
    auc_query_url: str
    auc_resource_id: str


def get_openspeech_settings() -> OpenSpeechSettings:
    return OpenSpeechSettings(
        appid=_resolve("OPENSPEECH_APPID", default=""),
        access_token=_resolve("OPENSPEECH_ACCESS_TOKEN", default=""),
        api_key=_resolve("OPENSPEECH_API_KEY", default=""),
        tts_url=_resolve("OPENSPEECH_TTS_URL", default="https://openspeech.bytedance.com/api/v1/tts"),
        tts_cluster=_resolve("OPENSPEECH_CLUSTER", default="volcano_tts"),
        tts_voice_type=_resolve("OPENSPEECH_VOICE_TYPE", default="zh_male_M392_conversation_wvae_bigtts"),
        tts_voices_json=_resolve("OPENSPEECH_TTS_VOICES_JSON", default=""),
        tts2_speaker=_resolve("OPENSPEECH_TTS2_SPEAKER", default="zh_female_vv_uranus_bigtts"),
        tts2_voices_json=_resolve("OPENSPEECH_TTS2_VOICES_JSON", default=""),
        asr_stream_cluster=_resolve("OPENSPEECH_ASR_STREAM_CLUSTER", default="volc_streaming_asr"),
        asr_file_cluster=_resolve("OPENSPEECH_ASR_FILE_CLUSTER", default="volc_asr"),
        asr_ws_url=_resolve(
            "OPENSPEECH_ASR_WS_URL",
            default="wss://openspeech.bytedance.com/api/v3/sauc/bigmodel_nostream",
        ),
        asr_resource_id=_resolve("OPENSPEECH_ASR_RESOURCE_ID", default="volc.seedasr.sauc.duration"),
        asr_model_name=_resolve("OPENSPEECH_ASR_MODEL_NAME", default="bigmodel"),
        asr_language=_resolve("OPENSPEECH_ASR_LANGUAGE", default="zh-CN"),
        asr_audio_rate=int(_resolve("OPENSPEECH_ASR_AUDIO_RATE", default="16000") or "16000"),
        auc_submit_url=_resolve(
            "OPENSPEECH_AUC_SUBMIT_URL",
            default="https://openspeech.bytedance.com/api/v3/auc/bigmodel/submit",
        ),
        auc_query_url=_resolve(
            "OPENSPEECH_AUC_QUERY_URL",
            default="https://openspeech.bytedance.com/api/v3/auc/bigmodel/query",
        ),
        auc_resource_id=_resolve("OPENSPEECH_AUC_RESOURCE_ID", default="volc.seedasr.auc"),
    )


@dataclass(frozen=True, slots=True)
class VideoModelSettings:
    """视频类：生成、编辑或理解类 API（按你接入的厂商填写）。"""

    runway_api_key: str
    runway_base_url: str


@dataclass(frozen=True, slots=True)
class EmbeddingModelSettings:
    """向量 / 嵌入类：RAG、语义检索、重排等。"""

    openai_embedding_model: str
    azure_openai_deployment_embeddings: str
    cohere_api_key: str
    cohere_embedding_model: str
    jina_api_key: str
    voyage_api_key: str
    voyage_embedding_model: str


@dataclass(frozen=True, slots=True)
class AIProviderSettings:
    """
    全部分类配置的聚合根。

    使用示例::

        s = get_ai_provider_settings()
        key = s.language.openai_api_key
        img = s.image.openai_image_model
    """

    language: LanguageModelSettings
    image: ImageModelSettings
    audio: AudioModelSettings
    video: VideoModelSettings
    embedding: EmbeddingModelSettings


def get_ai_provider_settings() -> AIProviderSettings:
    """
    构造当前进程可见的完整 AI 配置。

    切勿将返回值或其中任意字段序列化给前端或写入明文日志。
    """
    language = LanguageModelSettings(
        openai_api_key=_resolve("OPENAI_API_KEY"),
        openai_base_url=_resolve("OPENAI_BASE_URL", default="https://api.openai.com/v1"),
        openai_model=_resolve("OPENAI_MODEL", default="gpt-4o"),
        openai_vision_model=_resolve("OPENAI_VISION_MODEL"),
        anthropic_api_key=_resolve("ANTHROPIC_API_KEY"),
        anthropic_model=_resolve("ANTHROPIC_MODEL", default="claude-3-5-sonnet-20241022"),
        ollama_base_url=_resolve("OLLAMA_BASE_URL"),
        ollama_model=_resolve("OLLAMA_MODEL", default="llama3"),
        vectorengine_api_key=_resolve("VECTORENGINE_API_KEY"),
        vectorengine_base_url=_resolve("VECTORENGINE_BASE_URL"),
        vectorengine_model=_resolve("VECTORENGINE_MODEL"),
        google_api_key=_resolve("GOOGLE_API_KEY"),
        google_gemini_model=_resolve("GOOGLE_GEMINI_MODEL"),
        google_api_base_url=_resolve("GOOGLE_API_BASE_URL"),
        azure_openai_api_key=_resolve("AZURE_OPENAI_API_KEY"),
        azure_openai_endpoint=_resolve("AZURE_OPENAI_ENDPOINT"),
        azure_openai_deployment_chat=_resolve("AZURE_OPENAI_DEPLOYMENT_CHAT"),
        azure_openai_api_version=_resolve("AZURE_OPENAI_API_VERSION", default="2024-02-15-preview"),
        deepseek_api_key=_resolve("DEEPSEEK_API_KEY"),
        deepseek_base_url=_resolve("DEEPSEEK_BASE_URL", default="https://api.deepseek.com"),
        deepseek_model=_resolve("DEEPSEEK_MODEL", default="deepseek-chat"),
        moonshot_api_key=_resolve("MOONSHOT_API_KEY"),
        moonshot_base_url=_resolve("MOONSHOT_BASE_URL", default="https://api.moonshot.cn/v1"),
        moonshot_model=_resolve("MOONSHOT_MODEL", default="moonshot-v1-8k"),
        doubao_ark_api_key=_doubao_ark_api_key(),
        doubao_ark_base_url=_resolve(
            "DOUBAO_ARK_BASE_URL",
            default="https://ark.cn-beijing.volces.com/api/v3",
        ),
        doubao_ark_model=_resolve("DOUBAO_ARK_MODEL", default=""),
        doubao_ark_smart_router_endpoint=_resolve("DOUBAO_ARK_SMART_ROUTER_ENDPOINT", default=""),
        flowly_use_doubao_default=_resolve("FLOWLY_USE_DOUBAO_DEFAULT", default="1"),
    )
    image = ImageModelSettings(
        openai_image_model=_resolve("OPENAI_IMAGE_MODEL", default="dall-e-3"),
        stability_api_key=_resolve("STABILITY_API_KEY"),
        stability_base_url=_resolve("STABILITY_BASE_URL", default="https://api.stability.ai"),
        replicate_api_token=_resolve("REPLICATE_API_TOKEN"),
    )
    audio = AudioModelSettings(
        elevenlabs_api_key=_resolve("ELEVENLABS_API_KEY"),
        elevenlabs_default_voice_id=_resolve("ELEVENLABS_DEFAULT_VOICE_ID"),
        assemblyai_api_key=_resolve("ASSEMBLYAI_API_KEY"),
        openai_whisper_model=_resolve("OPENAI_WHISPER_MODEL", default="whisper-1"),
    )
    video = VideoModelSettings(
        runway_api_key=_resolve("RUNWAY_API_KEY"),
        runway_base_url=_resolve("RUNWAY_BASE_URL", default="https://api.dev.runwayml.com"),
    )
    embedding = EmbeddingModelSettings(
        openai_embedding_model=_resolve("OPENAI_EMBEDDING_MODEL", default="text-embedding-3-small"),
        azure_openai_deployment_embeddings=_resolve("AZURE_OPENAI_DEPLOYMENT_EMBEDDINGS"),
        cohere_api_key=_resolve("COHERE_API_KEY"),
        cohere_embedding_model=_resolve("COHERE_EMBEDDING_MODEL"),
        jina_api_key=_resolve("JINA_API_KEY"),
        voyage_api_key=_resolve("VOYAGE_API_KEY"),
        voyage_embedding_model=_resolve("VOYAGE_EMBEDDING_MODEL"),
    )
    return AIProviderSettings(
        language=language,
        image=image,
        audio=audio,
        video=video,
        embedding=embedding,
    )
