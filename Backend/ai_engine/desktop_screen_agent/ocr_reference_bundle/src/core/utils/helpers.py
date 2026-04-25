def format_message_history(history, max_lines=5):
    """
    格式化消息历史，限制长度
    :param history: 原始消息历史
    :param max_lines: 最大保留行数
    :return: 格式化后的消息历史
    """
    if not history:
        return ""
    lines = history.split('\n')
    recent_lines = lines[-max_lines:]
    return '\n'.join(recent_lines)


def validate_api_response(response):
    """
    验证API响应
    :param response: API响应对象
    :return: 是否有效
    """
    try:
        if not response:
            return False
        if "choices" not in response:
            return False
        if not response["choices"]:
            return False
        if "message" not in response["choices"][0]:
            return False
        if "content" not in response["choices"][0]["message"]:
            return False
        return True
    except Exception:
        return False


def safe_get_api_response(response):
    """
    安全获取API响应内容
    :param response: API响应对象
    :return: 响应内容或默认值
    """
    try:
        if validate_api_response(response):
            return response["choices"][0]["message"]["content"].strip()
        return "抱歉，我暂时无法回复~"
    except Exception:
        return "抱歉，我暂时无法回复~"
