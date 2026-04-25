import requests
from src.config.constants import API_KEY, API_ENDPOINT, ENDPOINT_ID, ChatPersonality, ChatScene
from src.core.logger import ai_logger
from src.core.helpers import safe_get_api_response

# 防止异常长文本撑爆请求或账单
_MAX_MESSAGE_CHARS = 8000
_MAX_SYSTEM_CHARS = 6000
_MAX_HISTORY_CHARS = 4000


def call_ai_api(
    user_message,
    personality="gentle_healing",
    scene="daily_chat",
    message_history="",
    custom_system_prompt="",
    reference_materials="",
    timeout_s: float = 6.0,
):
    """调用AI API。若 custom_system_prompt 非空，则整段作为 system；否则使用人格+情景组合。
    reference_materials：从本地 knowledge 目录组装的参考资料，会追加进 system（有长度上限）。
    """
    if not (API_KEY or "").strip():
        ai_logger.error("未配置 API 密钥：请设置环境变量 DOUBAO_API_KEY 或 ARK_API_KEY")
        return "抱歉，我暂时无法回复~"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }

    custom = (custom_system_prompt or "").strip()[:_MAX_SYSTEM_CHARS]
    if custom:
        system_prompt = custom
    else:
        system_prompt = (
            f"你是一个{ChatPersonality.get(personality, '友好')}的智能聊天助手，"
            f"现在是{ChatScene.get(scene, '日常闲聊情景')}情景，简短回复。"
        )[:_MAX_SYSTEM_CHARS]

    ref = (reference_materials or "").strip()
    if ref:
        hdr = (
            "\n\n【参考资料】（请按需使用其中的事实、术语与数据；不得编造其中不存在的内容；"
            "若与当前对话无关可忽略。）\n"
        )
        max_ref = min(4500, _MAX_SYSTEM_CHARS // 2)
        ref_cut = ref[:max_ref]
        base_max = _MAX_SYSTEM_CHARS - len(hdr) - len(ref_cut)
        if len(system_prompt) > base_max:
            system_prompt = system_prompt[: max(0, base_max) ]
        system_prompt = (system_prompt + hdr + ref_cut)[:_MAX_SYSTEM_CHARS]

    user_message = (user_message or "")[:_MAX_MESSAGE_CHARS]

    # 构建消息列表
    messages = [
        {"role": "system", "content": system_prompt}
    ]

    # 添加历史消息作为上下文（如果有）
    if message_history:
        # 限制历史消息长度，避免token超限
        history_lines = message_history.split('\n')
        recent_history = '\n'.join(history_lines[-5:])  # 只保留最近5条消息
        recent_history = recent_history[:_MAX_HISTORY_CHARS]
        messages.append({"role": "user", "content": f"历史消息：{recent_history}"})

    # 添加当前消息
    messages.append({"role": "user", "content": user_message})

    data = {
        "model": ENDPOINT_ID,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 200
    }

    try:
        # 重要：监控回复有严格时延 SLA，默认超时要小于整体预算（可通过 timeout_s 调整）
        response = requests.post(API_ENDPOINT, headers=headers, json=data, timeout=float(timeout_s))
        response.raise_for_status()
        result = response.json()
        reply = safe_get_api_response(result)
        ai_logger.info(f"AI回复生成成功: {reply[:50]}...")
        return reply

    except Exception as e:
        ai_logger.error(f"AI调用失败: {e}")
        return "抱歉，我暂时无法回复~"
