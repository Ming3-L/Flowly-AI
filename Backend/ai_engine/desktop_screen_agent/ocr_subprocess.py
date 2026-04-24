"""
通过子进程调用参考项目 ``src/core/ocr.py``（需在 **FLOWLY_OCR_REFERENCE_ROOT** 下可 import，
且该 Python 环境已安装 openocr 等依赖）。

环境变量
--------
FLOWLY_OCR_REFERENCE_ROOT
    参考项目根（含 ``src/``），默认指向 Flowly 仓库内 ``docs/reference/AI自动回复``。
FLOWLY_OCR_PYTHON
    用于子进程的 Python 可执行文件；默认 ``sys.executable``。
FLOWLY_OCR_SUBPROCESS_TIMEOUT
    超时秒数，默认 120。
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)


def _flowly_repo_root() -> Path:
    # .../Backend/ai_engine/desktop_screen_agent/ocr_subprocess.py -> parents[3] = 仓库根
    return Path(__file__).resolve().parents[3]


def default_reference_root() -> Path:
    return _flowly_repo_root() / "docs" / "reference" / "AI自动回复"


def reference_root() -> Path:
    override = (os.environ.get("FLOWLY_OCR_REFERENCE_ROOT") or "").strip()
    if override:
        return Path(override)
    return default_reference_root()


def worker_script_path() -> Path:
    return Path(__file__).resolve().parent / "ocr_reference_worker.py"


def run_ocr_subprocess(
    op: str,
    *,
    image_path: str | Path,
    box: tuple[int, int, int, int],
) -> dict[str, Any]:
    """
    同步执行 OCR 子进程。

    :param op: user_area | chat_window | input_area | friend_list | all_area
    :return: 与 worker 写入的 response JSON 一致，至少含 ``ok`` 键。
    """
    ref = reference_root()
    if not ref.is_dir():
        return {"ok": False, "error": f"参考项目目录不存在: {ref}"}

    worker = worker_script_path()
    if not worker.is_file():
        return {"ok": False, "error": f"未找到 worker: {worker}"}

    exe = (os.environ.get("FLOWLY_OCR_PYTHON") or sys.executable or "python").strip()
    timeout = int(os.environ.get("FLOWLY_OCR_SUBPROCESS_TIMEOUT", "120"))

    req = {"op": op, "image_path": str(Path(image_path).resolve()), "box": list(box)}
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".req.json",
        delete=False,
    ) as f_req:
        json.dump(req, f_req, ensure_ascii=False)
        req_path = f_req.name
    out_path = req_path.replace(".req.json", ".out.json")

    env = os.environ.copy()
    env["FLOWLY_OCR_REFERENCE_ROOT"] = str(ref)

    try:
        proc = subprocess.run(
            [exe, str(worker), req_path, out_path],
            cwd=str(ref),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if proc.returncode != 0 and not Path(out_path).is_file():
            err = (proc.stderr or proc.stdout or "").strip()[:2000]
            return {"ok": False, "error": f"子进程退出 {proc.returncode}: {err}"}
        if not Path(out_path).is_file():
            return {"ok": False, "error": "子进程未写入响应文件"}
        data = json.loads(Path(out_path).read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {"ok": False, "error": "响应 JSON 格式错误"}
        return data
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"OCR 子进程超时（>{timeout}s）"}
    except Exception as e:
        log.exception("OCR 子进程失败")
        return {"ok": False, "error": str(e)}
    finally:
        for p in (req_path, out_path):
            try:
                Path(p).unlink(missing_ok=True)
            except OSError:
                pass


def chat_lines_to_preview(lines: list[dict], max_chars: int = 600) -> str:
    parts: list[str] = []
    for ln in lines or []:
        t = str((ln or {}).get("text", "")).strip()
        if t:
            parts.append(t)
    s = "\n".join(parts).strip()
    if len(s) <= max_chars:
        return s
    return s[: max_chars - 1] + "…"
