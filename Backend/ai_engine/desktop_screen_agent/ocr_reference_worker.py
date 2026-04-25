"""
OpenOCR 入口（不依赖 ocr_reference_bundle）。

- **默认**：由 ``ocr_subprocess.run_ocr_subprocess`` 在**当前后端 Python 进程**内调用
  ``run_reference_ocr_request``（与 runserver / 屏幕代理同环境，无需单独子解释器装包）。
- **可选**：仍可用本脚本作独立子进程（``FLOWLY_OCR_USE_SUBPROCESS=1`` 时由 ocr_subprocess 走子进程）。

命令行::

    python ocr_reference_worker.py <request.json> <response.json>

request.json::

    {"op": "user_area"|"chat_window"|"input_area"|"friend_list"|"all_area",
     "image_path": "/abs/path.png",
     "box": [x1, y1, x2, y2]}
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def _serialize_chat_lines(lines) -> list[dict]:
    out: list[dict] = []
    for ln in lines or []:
        if not isinstance(ln, dict):
            continue
        item = {
            "text": str(ln.get("text", ""))[:800],
            "top": ln.get("top"),
            "bottom": ln.get("bottom"),
            "left": ln.get("left"),
            "right": ln.get("right"),
            "source": ln.get("source"),
            "img_w": ln.get("img_w"),
            "img_h": ln.get("img_h"),
        }
        out.append(item)
    return out


def run_reference_ocr_request(req: dict[str, Any]) -> dict[str, Any]:
    """
    在**当前进程**内执行 OCR（不依赖 ocr_reference_bundle）。
    """
    try:
        import openocr  # noqa: F401
    except ImportError:
        return {
            "ok": False,
            "error": (
                "未安装 openocr-python。请在与本后端相同的虚拟环境中执行："
                "pip install openocr-python==0.1.5（依赖已写入 Backend/requirements.txt）。"
            ),
        }

    op = str(req.get("op") or "")
    image_path = req.get("image_path")
    box = req.get("box")
    if not image_path or not isinstance(box, (list, tuple)) or len(box) != 4:
        return {"ok": False, "error": "image_path 与 box[4] 必填"}
    try:
        box_t = tuple(int(x) for x in box)
    except Exception:
        return {"ok": False, "error": "box 须为四个整数"}

    from PIL import Image
    from ai_engine.desktop_screen_agent.openocr_runtime import (
        ocr_all_area,
        ocr_chat_window,
        ocr_friend_list_area,
        ocr_input_area,
        ocr_user_area,
    )

    try:
        img = Image.open(str(image_path))
    except Exception as e:
        return {"ok": False, "error": f"打开图片失败: {e}"}

    try:
        if op == "user_area":
            text = ocr_user_area(box_t, img)
            return {"ok": True, "op": op, "text": str(text or "")}
        if op == "chat_window":
            lines = ocr_chat_window(box_t, img)
            return {"ok": True, "op": op, "lines": _serialize_chat_lines(lines)}
        if op == "input_area":
            text = ocr_input_area(box_t, img)
            return {"ok": True, "op": op, "text": str(text or "")}
        if op == "friend_list":
            text = ocr_friend_list_area(box_t, img)
            return {"ok": True, "op": op, "text": str(text or "")}
        if op == "all_area":
            text = ocr_all_area(box_t, img)
            return {"ok": True, "op": op, "text": str(text or "")}
        return {"ok": False, "error": f"未知 op: {op}"}
    except Exception as e:
        return {"ok": False, "error": str(e), "op": op}


def main() -> None:
    if len(sys.argv) < 3:
        print("usage: ocr_reference_worker.py <request.json> <response.json>", file=sys.stderr)
        sys.exit(2)
    req_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2])

    try:
        req = json.loads(req_path.read_text(encoding="utf-8"))
    except Exception as e:
        out_path.write_text(json.dumps({"ok": False, "error": f"请求 JSON 无效: {e}"}, ensure_ascii=False), encoding="utf-8")
        sys.exit(1)

    payload = run_reference_ocr_request(req)
    out_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    if not payload.get("ok"):
        sys.exit(1)


if __name__ == "__main__":
    main()
