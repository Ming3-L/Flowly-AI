def is_using(old_msg, new_msg, count):
    """
    判断是否需要调用AI
    :param old_msg: 旧消息
    :param new_msg: 新消息
    :param count: 消息计数
    :return: 是否需要调用AI
    """
    # 1. 检查消息是否有变化
    if old_msg != new_msg:
        # 2. 检查消息是否为空
        if new_msg.strip():
            # 3. 检查消息计数，避免过于频繁调用
            if count < 4:
                return True
    return False
