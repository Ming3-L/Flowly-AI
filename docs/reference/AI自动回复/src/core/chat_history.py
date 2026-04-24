import os
import re
from datetime import datetime

from src.config.constants import PROJECT_ROOT


def _safe_filename(name: str) -> str:
    """
    将用户名转成可作为 Windows 文件名的字符串：
    - 去掉控制字符
    - 替换 <>:"/\\|?* 等非法字符为下划线
    - 去掉末尾空格/点（Windows 不允许）
    """
    s = str(name or "").strip()
    if not s:
        s = "unknown"
    s = re.sub(r"[\x00-\x1f]", "", s)
    s = re.sub(r'[<>:"/\\\\|?*]+', "_", s)
    s = s.rstrip(" .")
    return s or "unknown"


def append_chat_history(user_name: str, sender: str, content: str, *, when: datetime | None = None) -> str:
    """
    追加写入聊天记录到：<项目根>/chat_history/<user>.txt

    格式（每条消息之间空一行）：
      时间: 2026-04-16 11:10:23
      发送方: <好友昵称>/我
      内容:
      <消息正文>
    """
    ts = when or datetime.now()
    ts_str = ts.strftime("%Y-%m-%d %H:%M:%S")

    sender_norm = str(sender or "").strip().lower()
    if sender_norm in {"me", "self", "i", "我", "自己"}:
        sender_cn = "我"
    elif sender_norm in {"other", "peer", "friend", "对方"}:
        # 对方消息：发送方显示为当前会话好友名（与文件名对应的 user_name）
        peer = str(user_name or "").strip()
        sender_cn = peer if peer else "对方"
    else:
        sender_cn = str(sender or "").strip() or "未知"

    text = str(content or "").rstrip()
    dir_path = os.path.join(PROJECT_ROOT, "chat_history")
    os.makedirs(dir_path, exist_ok=True)

    file_path = os.path.join(dir_path, f"{_safe_filename(user_name)}.txt")
    block = (
        f"时间: {ts_str}\n"
        f"发送方: {sender_cn}\n"
        f"内容:\n"
        f"{text}\n"
        f"\n"
    )
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(block)
    return file_path

