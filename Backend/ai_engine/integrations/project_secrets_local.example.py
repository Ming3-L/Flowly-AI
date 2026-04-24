"""
项目内本地密钥模板（可提交到 Git）。

使用方法
--------
1. 将本文件**复制**为同目录下的 ``project_secrets_local.py``。
2. 按你实际接的厂商填写；用不到的类别保持空字符串即可。
3. ``project_secrets_local.py`` 已在 ``.gitignore`` 中，不会被提交。

读取规则
--------
见 ``secrets_loader``：环境变量非空优先，否则读本文件同名变量。

说明
----
- **语言类**：文本对话、函数调用、部分「多模态理解」可与视觉模型字段配合使用。
- **图片类**：文生图 / 图生图等；若走 OpenAI 图像接口，通常与下方 OpenAI 密钥共用。
- **音频类**：TTS、语音识别等。
- **视频类**：视频生成或理解类 API 占位。
- **向量 / 嵌入类**：RAG、语义检索等（与对话模型密钥可能不同）。

安全提醒
--------
勿将填好的 ``project_secrets_local.py`` 提交仓库或外传。
"""

# =============================================================================
# 一、语言类（文本对话 / Agent / 工具调用等）
# =============================================================================

# --- OpenAI 或兼容 OpenAI Chat Completions 的网关 ---
OPENAI_API_KEY = ""
OPENAI_BASE_URL = ""
OPENAI_MODEL = ""
# 用于多模态「看图说话」等；不配则可用 OPENAI_MODEL 兼任
OPENAI_VISION_MODEL = ""

# --- Anthropic Claude ---
ANTHROPIC_API_KEY = ""
ANTHROPIC_MODEL = ""

# --- Ollama（本地）---
OLLAMA_BASE_URL = ""
OLLAMA_MODEL = ""

# --- VectorEngine 等 OpenAI 兼容聚合网关 ---
VECTORENGINE_API_KEY = ""
VECTORENGINE_BASE_URL = ""
VECTORENGINE_MODEL = ""

# --- Google Gemini（语言）---
GOOGLE_API_KEY = ""
GOOGLE_GEMINI_MODEL = ""
GOOGLE_API_BASE_URL = ""

# --- Azure OpenAI（语言部署）---
AZURE_OPENAI_API_KEY = ""
AZURE_OPENAI_ENDPOINT = ""
AZURE_OPENAI_DEPLOYMENT_CHAT = ""
AZURE_OPENAI_API_VERSION = ""

# --- DeepSeek ---
DEEPSEEK_API_KEY = ""
DEEPSEEK_BASE_URL = ""
DEEPSEEK_MODEL = ""

# --- Moonshot / Kimi ---
MOONSHOT_API_KEY = ""
MOONSHOT_BASE_URL = ""
MOONSHOT_MODEL = ""

# --- 火山方舟 / 豆包（OpenAI 兼容；与 DOUBAO_API_KEY / ARK_API_KEY 环境变量二选一即可）---
DOUBAO_API_KEY = ""
ARK_API_KEY = ""
DOUBAO_ARK_BASE_URL = ""
DOUBAO_ARK_MODEL = ""

# =============================================================================
# 二、图片类（文生图 / 图生图 / 独立图像 API）
# =============================================================================

# 与 OpenAI 密钥共用；仅指定图像模型 id（如 dall-e-3）
OPENAI_IMAGE_MODEL = ""

STABILITY_API_KEY = ""
STABILITY_BASE_URL = ""

REPLICATE_API_TOKEN = ""

# =============================================================================
# 三、音频类（TTS / ASR）
# =============================================================================

ELEVENLABS_API_KEY = ""
ELEVENLABS_DEFAULT_VOICE_ID = ""

ASSEMBLYAI_API_KEY = ""

# Whisper 等；通常与 OPENAI_API_KEY 共用
OPENAI_WHISPER_MODEL = ""
OPENAI_TTS_MODEL = ""

# =============================================================================
# 四、视频类（生成 / 编辑 / 理解占位）
# =============================================================================

RUNWAY_API_KEY = ""
RUNWAY_BASE_URL = ""

# =============================================================================
# 五、向量 / 嵌入类（RAG、重排序等可后续扩展）
# =============================================================================

OPENAI_EMBEDDING_MODEL = ""

COHERE_API_KEY = ""
COHERE_EMBEDDING_MODEL = ""

JINA_API_KEY = ""

VOYAGE_API_KEY = ""
VOYAGE_EMBEDDING_MODEL = ""

# --- Azure OpenAI（嵌入部署，可与语言共用 endpoint，部署名不同）---
AZURE_OPENAI_DEPLOYMENT_EMBEDDINGS = ""
