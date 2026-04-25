import time

import pyautogui
import pyperclip

from src.core.logger import sender_logger

# 发送消息计数和时间记录（用于统计，不参与业务逻辑）
send_count = 0
send_times = []


def send_reply(reply_text, input_box_pos):
    """发送回复（剪贴板粘贴 + Enter）。

    返回：实际发送的文本（去除首尾空白）。
    """
    global send_count, send_times

    reply_text = str(reply_text or "").strip()
    if not reply_text:
        return ""
    
    try:
        x1, y1, x2, y2 = input_box_pos
        click_x = int((int(x1) + int(x2)) / 2)
        click_y = int((int(y1) + int(y2)) / 2)
        pyautogui.click((click_x, click_y))
        pyperclip.copy(reply_text)
        pyautogui.hotkey('ctrl', 'v')
        pyautogui.press('enter')
        sender_logger.info(f"已发送回复: {reply_text[:50]}...")
        
        # 记录发送时间
        send_times.append(time.time())
        return reply_text
    except Exception as e:
        sender_logger.error(f"发送失败: {e}")
        return ""
