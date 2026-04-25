"""
参考项目 ``src/core/ocr.py``（OpenOCR）调用入口。

默认在**当前后端 Python 进程**内执行（与 ``runserver``、屏幕代理线程同一环境、同一套已安装依赖），
不再依赖「子进程用的解释器是否另装过 openocr」。

环境变量
--------
FLOWLY_OCR_USE_SUBPROCESS
    设为 ``1`` / ``true`` 时改为**独立子进程**调用（旧行为，用于隔离崩溃/依赖；需 ``FLOWLY_OCR_PYTHON`` 环境一致）。
FLOWLY_OCR_PYTHON
    仅子进程模式：Python 可执行文件，默认 ``sys.executable``。
FLOWLY_OCR_SUBPROCESS_TIMEOUT
    仅子进程模式：超时秒数，默认 120。
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


def _truthy_env(name: str) -> bool:
    return (os.environ.get(name) or "").strip().lower() in ("1", "true", "yes", "on")


def default_reference_root() -> Path:
    """兼容旧配置：已不再需要 reference bundle，保留函数名避免外部脚本引用报错。"""
    return Path(__file__).resolve().parent


def worker_script_path() -> Path:
    return Path(__file__).resolve().parent / "ocr_reference_worker.py"


def run_ocr_subprocess(
    op: str,
    *,
    image_path: str | Path,
    box: tuple[int, int, int, int],
) -> dict[str, Any]:
    """
    同步执行参考 OCR。

    默认同进程（``run_reference_ocr_request``）；仅当 ``FLOWLY_OCR_USE_SUBPROCESS=1`` 时走子进程。

    :param op: user_area | chat_window | input_area | friend_list | all_area
    :return: 至少含 ``ok`` 键。
    """
    req: dict[str, Any] = {"op": op, "image_path": str(Path(image_path).resolve()), "box": list(box)}

    if not _truthy_env("FLOWLY_OCR_USE_SUBPROCESS"):
        from ai_engine.desktop_screen_agent.ocr_reference_worker import run_reference_ocr_request

        try:
            return run_reference_ocr_request(req)
        except Exception as e:
            log.exception("参考 OCR 同进程执行失败")
            return {"ok": False, "error": str(e)}

    worker = worker_script_path()
    if not worker.is_file():
        return {"ok": False, "error": f"未找到 worker: {worker}"}

    exe = (os.environ.get("FLOWLY_OCR_PYTHON") or sys.executable or "python").strip()
    timeout = int(os.environ.get("FLOWLY_OCR_SUBPROCESS_TIMEOUT", "120"))

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

    try:
        proc = subprocess.run(
            [exe, str(worker), req_path, out_path],
            cwd=str(Path(__file__).resolve().parent),
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
