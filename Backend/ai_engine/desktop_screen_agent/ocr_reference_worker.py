"""
在独立进程中加载参考项目 ``src.core.ocr``（OpenOCR），避免与 Flowly 主进程依赖混用。

由 ``ocr_subprocess.run_ocr_subprocess`` 启动；环境变量 **FLOWLY_OCR_REFERENCE_ROOT** 须为
参考项目根目录（含 ``src/`` 的目录，如仓库内 ``docs/reference/AI自动回复``）。

命令行::

    python ocr_reference_worker.py <request.json> <response.json>

request.json::

    {"op": "user_area"|"chat_window"|"input_area"|"friend_list"|"all_area",
     "image_path": "/abs/path.png",
     "box": [x1, y1, x2, y2]}
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


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


def main() -> None:
    if len(sys.argv) < 3:
        print("usage: ocr_reference_worker.py <request.json> <response.json>", file=sys.stderr)
        sys.exit(2)
    req_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2])
    ref_root = (os.environ.get("FLOWLY_OCR_REFERENCE_ROOT") or "").strip()
    if not ref_root or not Path(ref_root).is_dir():
        out_path.write_text(
            json.dumps({"ok": False, "error": "缺少或无效的环境变量 FLOWLY_OCR_REFERENCE_ROOT"}, ensure_ascii=False),
            encoding="utf-8",
        )
        sys.exit(1)

    os.chdir(ref_root)
    if ref_root not in sys.path:
        sys.path.insert(0, ref_root)

    try:
        req = json.loads(req_path.read_text(encoding="utf-8"))
    except Exception as e:
        out_path.write_text(json.dumps({"ok": False, "error": f"请求 JSON 无效: {e}"}, ensure_ascii=False), encoding="utf-8")
        sys.exit(1)

    op = str(req.get("op") or "")
    image_path = req.get("image_path")
    box = req.get("box")
    if not image_path or not isinstance(box, (list, tuple)) or len(box) != 4:
        out_path.write_text(
            json.dumps({"ok": False, "error": "image_path 与 box[4] 必填"}, ensure_ascii=False),
            encoding="utf-8",
        )
        sys.exit(1)
    try:
        box_t = tuple(int(x) for x in box)
    except Exception:
        out_path.write_text(json.dumps({"ok": False, "error": "box 须为四个整数"}, ensure_ascii=False), encoding="utf-8")
        sys.exit(1)

    from PIL import Image

    from src.core.ocr import (  # type: ignore[import-untyped]
        ocr_all_area,
        ocr_chat_window,
        ocr_friend_list_area,
        ocr_input_area,
        ocr_user_area,
    )

    try:
        img = Image.open(str(image_path))
    except Exception as e:
        out_path.write_text(json.dumps({"ok": False, "error": f"打开图片失败: {e}"}, ensure_ascii=False), encoding="utf-8")
        sys.exit(1)

    try:
        if op == "user_area":
            text = ocr_user_area(box_t, img)
            payload = {"ok": True, "op": op, "text": str(text or "")}
        elif op == "chat_window":
            lines = ocr_chat_window(box_t, img)
            payload = {"ok": True, "op": op, "lines": _serialize_chat_lines(lines)}
        elif op == "input_area":
            text = ocr_input_area(box_t, img)
            payload = {"ok": True, "op": op, "text": str(text or "")}
        elif op == "friend_list":
            text = ocr_friend_list_area(box_t, img)
            payload = {"ok": True, "op": op, "text": str(text or "")}
        elif op == "all_area":
            text = ocr_all_area(box_t, img)
            payload = {"ok": True, "op": op, "text": str(text or "")}
        else:
            payload = {"ok": False, "error": f"未知 op: {op}"}
    except Exception as e:
        payload = {"ok": False, "error": str(e), "op": op}

    out_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
