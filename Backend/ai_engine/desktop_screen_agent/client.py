"""
本机循环：拉取屏幕配置 → 可选区域检测 → 上报 screen-events。
环境变量：
  FLOWLY_API_BASE   如 http://127.0.0.1:8000/api
  FLOWLY_ACCESS_TOKEN  JWT（与前端登录后一致）
"""

from __future__ import annotations

import logging
import os
import tempfile
import time
from pathlib import Path

import requests

from ai_engine.desktop_screen_agent.engine import areas_to_jsonable, get_chat_areas_from_profile

log = logging.getLogger(__name__)


def _truthy_env(name: str) -> bool:
    return str(os.getenv(name, "") or "").lower() in ("1", "true", "yes", "on")


def _save_full_screenshot_png() -> str | None:
    try:
        import pyautogui  # type: ignore[import-untyped]
    except ImportError:
        log.warning("未安装 pyautogui，无法截屏供 OCR")
        return None
    try:
        shot = pyautogui.screenshot()
        fd, path = tempfile.mkstemp(suffix=".png", prefix="flowly_ocr_")
        os.close(fd)
        shot.save(path, format="PNG")
        return path
    except Exception as e:
        log.warning("截屏失败: %s", e)
        return None


def _maybe_run_ocr_subprocess(areas: dict | None) -> dict | None:
    """
    若设置 FLOWLY_SCREEN_OCR_SUBPROCESS=1，则在子进程中调用参考 ocr.py。
    返回供写入 screen-events 的 payload；失败返回 {"error": "..."}。
    """
    if not _truthy_env("FLOWLY_SCREEN_OCR_SUBPROCESS"):
        return None
    if not areas:
        return {"skipped": True, "reason": "无区域"}
    chat_area = areas.get("chat_area")
    user_object = areas.get("user_object")
    if not chat_area or not user_object:
        return {"skipped": True, "reason": "缺少 chat_area 或 user_object"}

    img_path = _save_full_screenshot_png()
    if not img_path:
        return {"error": "截屏不可用"}

    from ai_engine.desktop_screen_agent.ocr_subprocess import chat_lines_to_preview, run_ocr_subprocess

    try:
        u = run_ocr_subprocess("user_area", image_path=img_path, box=tuple(int(x) for x in user_object))
        c = run_ocr_subprocess("chat_window", image_path=img_path, box=tuple(int(x) for x in chat_area))
        inp_txt = ""
        ib = areas.get("input_box")
        if ib and len(ib) == 4:
            inp = run_ocr_subprocess("input_area", image_path=img_path, box=tuple(int(x) for x in ib))
            if inp.get("ok"):
                inp_txt = str(inp.get("text") or "")

        out: dict = {
            "ocr_user_ok": bool(u.get("ok")),
            "ocr_chat_ok": bool(c.get("ok")),
            "user_text": (u.get("text") or "")[:200] if u.get("ok") else "",
            "input_preview": inp_txt[:300],
        }
        if c.get("ok") and isinstance(c.get("lines"), list):
            lines = c["lines"]
            out["chat_line_count"] = len(lines)
            out["chat_preview"] = chat_lines_to_preview(lines, max_chars=800)
        else:
            out["chat_line_count"] = 0
            out["chat_preview"] = ""
            if not c.get("ok"):
                out["chat_error"] = str(c.get("error") or "")
        if not u.get("ok"):
            out["user_error"] = str(u.get("error") or "")
        return out
    finally:
        try:
            Path(img_path).unlink(missing_ok=True)
        except OSError:
            pass


def _headers() -> dict[str, str]:
    token = (os.getenv("FLOWLY_ACCESS_TOKEN") or "").strip()
    if not token:
        raise RuntimeError("请设置环境变量 FLOWLY_ACCESS_TOKEN")
    return {"Authorization": f"Bearer {token}"}


def _api_base() -> str:
    base = (os.getenv("FLOWLY_API_BASE") or "").strip().rstrip("/")
    if not base:
        raise RuntimeError("请设置环境变量 FLOWLY_API_BASE，例如 http://127.0.0.1:8000/api")
    return base


def fetch_screen_profile(session: requests.Session) -> dict:
    r = session.get(f"{_api_base()}/auto-reply/screen-profile", headers=_headers(), timeout=30)
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, dict):
        raise RuntimeError("screen-profile 响应格式错误")
    return data


def post_screen_event(session: requests.Session, event_type: str, message: str = "", payload: dict | None = None):
    body = {"event_type": event_type, "message": message, "payload": payload or {}}
    r = session.post(
        f"{_api_base()}/auto-reply/screen-events",
        headers=_headers(),
        json=body,
        timeout=30,
    )
    r.raise_for_status()


def post_monitor_log(session: requests.Session, line: str, level: str = "info", extra: dict | None = None) -> None:
    try:
        r = session.post(
            f"{_api_base()}/auto-reply/monitor-logs",
            headers=_headers(),
            json={"level": level, "line": line, "extra": extra or {}},
            timeout=15,
        )
        r.raise_for_status()
    except requests.RequestException as e:
        log.debug("monitor-logs 上报失败: %s", e)


def patch_screen_layout(session: requests.Session, body: dict) -> dict:
    r = session.patch(
        f"{_api_base()}/auto-reply/screen-profile/layout",
        headers=_headers(),
        json=body,
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, dict):
        raise RuntimeError("layout patch 响应无效")
    return data


def _areas_to_layout_payload(areas: dict, ack_nonce: int) -> dict:
    m: dict = {"region_detect_ack_nonce": ack_nonce}
    if areas.get("chat_area"):
        m["chat_window_box"] = [int(x) for x in areas["chat_area"]]
    if areas.get("input_box"):
        m["input_box_pos"] = [int(x) for x in areas["input_box"]]
    if areas.get("user_object"):
        m["user_name_box"] = [int(x) for x in areas["user_object"]]
    if areas.get("friend_list"):
        m["friend_list_box"] = [int(x) for x in areas["friend_list"]]
    return m


def main_loop() -> None:
    session = requests.Session()
    log.info("Flowly 屏幕代理启动；按 Ctrl+C 结束")
    while True:
        interval = 10
        try:
            profile = fetch_screen_profile(session)
            wp = (profile.get("yolo_weights_path") or "").strip()
            if wp:
                # 兼容历史/错误配置：只有存在的权重路径才写入 env，避免覆盖后端默认权重位置
                try:
                    if Path(wp).is_file():
                        os.environ["FLOWLY_SCREEN_YOLO_WEIGHTS"] = wp
                    else:
                        os.environ.pop("FLOWLY_SCREEN_YOLO_WEIGHTS", None)
                except Exception:
                    os.environ.pop("FLOWLY_SCREEN_YOLO_WEIGHTS", None)

            nonce = int(profile.get("region_detect_nonce") or 0)
            ack = int(profile.get("region_detect_ack_nonce") or 0)
            areas = None
            msg = ""
            if nonce > ack:
                areas2, msg2 = get_chat_areas_from_profile(profile)
                if areas2:
                    try:
                        patch_screen_layout(session, _areas_to_layout_payload(areas2, nonce))
                        post_monitor_log(session, f"区域识别已写回：{msg2}", "info")
                        profile = fetch_screen_profile(session)
                        areas, msg = areas2, msg2
                    except requests.RequestException as e:
                        post_monitor_log(session, f"写回区域失败：{e}", "warn")
                else:
                    post_monitor_log(session, f"区域识别未成功：{msg2}", "warn")

            if not profile.get("monitoring_active"):
                post_screen_event(
                    session,
                    "heartbeat",
                    "监控已暂停（仅轮询配置）",
                    {"paused": True, "chat_software": profile.get("chat_software")},
                )
                interval = max(12, int(profile.get("check_interval_seconds") or 3) * 4)
                time.sleep(interval)
                continue

            interval = max(1, int(profile.get("check_interval_seconds") or 3))
            if areas is None:
                areas, msg = get_chat_areas_from_profile(profile)
            base_payload: dict = {
                "areas": areas_to_jsonable(areas),
                "chat_software": profile.get("chat_software"),
            }
            ocr_extra = None
            if profile.get("monitoring_active") and _truthy_env("FLOWLY_SCREEN_OCR_SUBPROCESS"):
                ocr_extra = _maybe_run_ocr_subprocess(areas)
            if ocr_extra is not None:
                base_payload["ocr"] = ocr_extra
            post_screen_event(session, "heartbeat", msg, base_payload)
            if ocr_extra is not None:
                err_parts = [
                    ocr_extra.get("error"),
                    ocr_extra.get("user_error"),
                    ocr_extra.get("chat_error"),
                ]
                joined = "; ".join(str(x) for x in err_parts if x)
                if joined:
                    post_screen_event(session, "ocr_error", joined[:500], {"ocr": ocr_extra})
        except requests.RequestException as e:
            log.warning("请求失败: %s", e)
            try:
                post_screen_event(session, "error", str(e), {})
            except Exception:
                pass
            interval = 10
        except Exception as e:
            log.exception("循环异常: %s", e)
            interval = 10
        time.sleep(interval)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    main_loop()


if __name__ == "__main__":
    main()
