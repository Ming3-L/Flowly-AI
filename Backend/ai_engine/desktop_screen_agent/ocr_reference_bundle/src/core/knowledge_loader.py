import os
import re
from typing import List, Optional

from src.config.constants import KNOWLEDGE_ROOT


def ensure_knowledge_dirs() -> None:
    """创建资料库默认子目录。"""
    os.makedirs(os.path.join(KNOWLEDGE_ROOT, "shared"), exist_ok=True)
    os.makedirs(os.path.join(KNOWLEDGE_ROOT, "friends"), exist_ok=True)


def _safe_filename(name: str) -> str:
    s = str(name or "").strip()
    if not s:
        s = "unknown"
    s = re.sub(r"[\x00-\x1f]", "", s)
    s = re.sub(r'[<>:"/\\\\|?*]+', "_", s)
    s = s.rstrip(" .")
    return s or "unknown"


def _is_under_knowledge(abs_path: str) -> bool:
    root = os.path.abspath(os.path.normpath(KNOWLEDGE_ROOT))
    cand = os.path.abspath(os.path.normpath(abs_path))
    if os.name == "nt":
        root = os.path.normcase(root)
        cand = os.path.normcase(cand)
    return cand == root or cand.startswith(root + os.sep)


def _resolve_relative(rel: str) -> Optional[str]:
    """将相对路径（相对 KNOWLEDGE_ROOT）解析为绝对路径；禁止跳出 knowledge 目录。"""
    rel = str(rel or "").strip().replace("\\", "/")
    if not rel or rel.startswith("/"):
        return None
    # 禁止显式 .. 组件
    parts = [p for p in rel.split("/") if p and p != "."]
    if any(p == ".." for p in parts):
        return None
    joined = os.path.normpath(os.path.join(KNOWLEDGE_ROOT, *parts))
    if not _is_under_knowledge(joined):
        return None
    return joined


def load_knowledge_bundle(
    friend_display_name: str,
    extra_relative_paths: Optional[List[str]] = None,
    *,
    max_total_chars: int = 10000,
) -> str:
    """
    组装注入 AI 的参考资料文本：
    1) 若存在 knowledge/friends/<好友安全文件名>.txt 则自动读取
    2) 读取 extra_relative_paths 中列出的文件（路径相对 knowledge/）
    文本按顺序拼接，超长则截断。
    """
    ensure_knowledge_dirs()
    chunks: List[str] = []

    friend_file = os.path.join(KNOWLEDGE_ROOT, "friends", f"{_safe_filename(friend_display_name)}.txt")
    if os.path.isfile(friend_file) and _is_under_knowledge(friend_file):
        try:
            with open(friend_file, "r", encoding="utf-8") as f:
                body = f.read().strip()
            if body:
                chunks.append(f"[好友专属资料: friends/{_safe_filename(friend_display_name)}.txt]\n{body}")
        except OSError:
            pass

    for rel in extra_relative_paths or []:
        abs_p = _resolve_relative(rel)
        if not abs_p or not os.path.isfile(abs_p):
            continue
        try:
            with open(abs_p, "r", encoding="utf-8") as f:
                body = f.read().strip()
        except OSError:
            continue
        if not body:
            continue
        label = rel.strip().replace("\\", "/")
        chunks.append(f"[资料: {label}]\n{body}")

    if not chunks:
        return ""

    merged = "\n\n---\n\n".join(chunks)
    if len(merged) <= max_total_chars:
        return merged
    return merged[: max_total_chars - 20] + "\n\n...(已截断)"


def should_attach_knowledge_for_message(
    message: str, match_keywords: Optional[List[str]]
) -> bool:
    """
    本地关键词路由（子串匹配）：
    - 关键词列表为空：不限制，返回 True（仍受「资料库页总开关」控制）
    - 有关键词：对方消息中只要包含其中任意一条子串即返回 True
    """
    kws = [
        str(x).strip()
        for x in (match_keywords or [])
        if str(x).strip() and not str(x).strip().startswith("#")
    ]
    if not kws:
        return True
    msg = str(message or "")
    for kw in kws:
        if kw in msg:
            return True
    return False
