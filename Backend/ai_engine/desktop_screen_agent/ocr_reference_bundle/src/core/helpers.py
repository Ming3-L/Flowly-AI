def validate_api_response(response):
    """
    验证 API 响应结构是否符合预期
    :param response: dict / None
    :return: bool
    """
    try:
        if not response:
            return False
        if "choices" not in response:
            return False
        if not response["choices"]:
            return False
        choice0 = response["choices"][0]
        if "message" not in choice0:
            return False
        if "content" not in choice0["message"]:
            return False
        return True
    except Exception:
        return False


def safe_get_api_response(response):
    """
    安全获取 API 返回的文本内容
    :param response: dict / None
    :return: str
    """
    try:
        if validate_api_response(response):
            return response["choices"][0]["message"]["content"].strip()
        return "抱歉，我暂时无法回复~"
    except Exception:
        return "抱歉，我暂时无法回复~"

