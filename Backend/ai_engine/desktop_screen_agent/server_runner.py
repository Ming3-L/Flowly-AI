"""
服务端本机屏幕代理（独立进程）：

- 直接读取/写入 Django ORM（无需 JWT / HTTP 回调）
- 复用 desktop_screen_agent.engine 的 YOLO 区域识别逻辑
- 不再将“监控事件/监控日志”写入数据库（按需求下线）

注意：该代理需要在**有桌面会话**的机器上运行（Windows 需要可用的截图 API）。
"""

from __future__ import annotations

import logging
import os
import tempfile
import time
from typing import Any

from django.conf import settings
from django.db import transaction
from django.utils import timezone as django_timezone

from ai_engine.desktop_screen_agent.engine import get_chat_areas_from_profile
from ai_engine.models import AutoReplyJob, AutoReplyRule, AutoReplyScreenProfile

log = logging.getLogger(__name__)


def _log(level: str, msg: str, extra: dict[str, Any] | None = None) -> None:
    lv = (level or "info").strip().lower()
    payload = {"extra": extra or {}}
    if lv == "error":
        log.error(msg, extra=payload)
    elif lv == "warn" or lv == "warning":
        log.warning(msg, extra=payload)
    else:
        log.info(msg, extra=payload)


def _try_screenshot_png() -> str | None:
    try:
        import pyautogui  # type: ignore[import-untyped]
    except ImportError:
        return None
    try:
        shot = pyautogui.screenshot()
        fd, path = tempfile.mkstemp(suffix=".png", prefix="flowly_screen_")
        os.close(fd)
        shot.save(path, format="PNG")
        return path
    except Exception:
        return None


def _run_chat_ocr(image_path: str, chat_box: tuple[int, int, int, int]) -> dict[str, Any]:
    from ai_engine.desktop_screen_agent.ocr_subprocess import chat_lines_to_preview, run_ocr_subprocess

    res = run_ocr_subprocess("chat_window", image_path=image_path, box=chat_box)
    if not res.get("ok"):
        return {"ok": False, "error": str(res.get("error") or "ocr_failed")}
    lines = res.get("lines") if isinstance(res.get("lines"), list) else []
    preview = chat_lines_to_preview(lines, max_chars=1200)
    last_line = ""
    for ln in reversed(lines or []):
        t = str((ln or {}).get("text", "")).strip()
        if t:
            last_line = t
            break
    return {"ok": True, "preview": preview, "last_line": last_line, "line_count": len(lines)}


def _run_user_ocr(image_path: str, user_box: tuple[int, int, int, int]) -> dict[str, Any]:
    """从“用户/好友名区域”粗略 OCR 出当前会话对方显示名。"""
    from ai_engine.desktop_screen_agent.ocr_subprocess import run_ocr_subprocess

    res = run_ocr_subprocess("user_name", image_path=image_path, box=user_box)
    if not res.get("ok"):
        return {"ok": False, "error": str(res.get("error") or "ocr_failed")}
    lines = res.get("lines") if isinstance(res.get("lines"), list) else []
    text = ""
    for ln in lines or []:
        t = str((ln or {}).get("text", "")).strip()
        if t:
            text = t
            break
    text = (text or "").strip()
    return {"ok": True, "text": text}


def _try_send_text_via_pyautogui(text: str, input_box: tuple[int, int, int, int]) -> tuple[bool, str]:
    t = (text or "").strip()
    if not t:
        return False, "empty_reply"
    try:
        import pyautogui  # type: ignore[import-untyped]
    except ImportError:
        return False, "pyautogui_not_installed"
    try:
        x1, y1, x2, y2 = [int(v) for v in input_box]
        cx = int((x1 + x2) / 2)
        cy = int((y1 + y2) / 2)
        pyautogui.click(cx, cy)
        time.sleep(0.05)
        pyautogui.typewrite(t, interval=0.01)
        pyautogui.press("enter")
        return True, "sent"
    except Exception as exc:
        return False, str(exc)


def _profile_to_dict(p: AutoReplyScreenProfile) -> dict[str, Any]:
    mf = p.monitored_friends if isinstance(p.monitored_friends, list) else []
    fo = p.friends_overrides if isinstance(p.friends_overrides, dict) else {}
    return {
        "chat_software": p.chat_software or "wechat",
        "chat_window_box": p.chat_window_box,
        "input_box_pos": p.input_box_pos,
        "user_name_box": p.user_name_box,
        "friend_list_box": p.friend_list_box,
        "monitored_friends": [str(x) for x in mf],
        "friends_overrides": fo,
        "check_interval_seconds": int(p.check_interval_seconds or 3),
        "use_yolo": bool(p.use_yolo),
        "knowledge_reply_enabled": bool(p.knowledge_reply_enabled),
        "monitoring_active": bool(getattr(p, "monitoring_active", False)),
        "yolo_weights_path": (p.yolo_weights_path or "").strip(),
        "region_detect_nonce": int(getattr(p, "region_detect_nonce", 0) or 0),
        "region_detect_ack_nonce": int(getattr(p, "region_detect_ack_nonce", 0) or 0),
        "default_rule_id": p.default_rule_id,
        "updated_at": p.updated_at.isoformat() if p.updated_at else "",
    }


def _apply_detected_layout(*, user_id: int, nonce: int, areas: dict[str, Any]) -> None:
    """将识别结果写回 ScreenProfile 坐标，并回写已处理的 nonce。"""
    with transaction.atomic():
        p = AutoReplyScreenProfile.objects.select_for_update().filter(user_id=int(user_id)).first()
        if p is None:
            return
        # 若 nonce 已过期，忽略
        if int(p.region_detect_nonce or 0) != int(nonce):
            return
        if areas.get("chat_area"):
            p.chat_window_box = [int(x) for x in areas["chat_area"]]
        if areas.get("input_box"):
            p.input_box_pos = [int(x) for x in areas["input_box"]]
        if areas.get("user_object"):
            p.user_name_box = [int(x) for x in areas["user_object"]]
        if areas.get("friend_list"):
            p.friend_list_box = [int(x) for x in areas["friend_list"]]
        p.region_detect_ack_nonce = int(nonce)
        p.save(update_fields=["chat_window_box", "input_box_pos", "user_name_box", "friend_list_box", "region_detect_ack_nonce", "updated_at"])


def run_server_screen_agent(*, user_id: int, stop_event=None) -> None:
    """
    阻塞循环：读取 profile → 识别 → 执行自动回复闭环。
    设计为在 multiprocessing 子进程中运行。
    """
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    uid = int(user_id)
    _log("info", "本机屏幕代理已启动", {"pid": os.getpid(), "user_id": uid})

    last_chat_signature = ""
    last_auto_reply_at = 0.0

    while True:
        try:
            if stop_event is not None and getattr(stop_event, "is_set", None) and stop_event.is_set():
                _log("info", "本机屏幕代理已收到停止信号", {"pid": os.getpid(), "user_id": uid})
                break
        except Exception:
            pass
        interval = 10
        try:
            p = AutoReplyScreenProfile.objects.filter(user_id=uid).first()
            if p is None:
                # 没配置就休眠
                time.sleep(10)
                continue
            prof = _profile_to_dict(p)
            interval = max(1, int(prof.get("check_interval_seconds") or 3))

            # 区域识别：仅在前端请求的 nonce > ack 时执行并写回
            nonce = int(prof.get("region_detect_nonce") or 0)
            ack = int(prof.get("region_detect_ack_nonce") or 0)
            if nonce > ack:
                areas2, msg2 = get_chat_areas_from_profile(
                    prof,
                    yolo_weights_path=str(getattr(settings, "FLOWLY_SCREEN_YOLO_WEIGHTS", "") or "").strip() or None,
                )
                if areas2:
                    _apply_detected_layout(user_id=uid, nonce=nonce, areas=areas2)
                    _log("info", f"区域识别已写回：{msg2}", {"nonce": nonce, "user_id": uid})
                else:
                    _log("warn", f"区域识别未成功：{msg2}", {"nonce": nonce, "user_id": uid})

            if not prof.get("monitoring_active"):
                time.sleep(max(12, interval * 4))
                continue

            areas, msg = get_chat_areas_from_profile(
                prof,
                yolo_weights_path=str(getattr(settings, "FLOWLY_SCREEN_YOLO_WEIGHTS", "") or "").strip() or None,
            )
            flags = {
                "detected_chat_area": bool(areas and areas.get("chat_area")),
                "detected_user": bool(areas and areas.get("user_object")),
                "detected_input_box": bool(areas and areas.get("input_box")),
                "detected_friend_list": bool(areas and areas.get("friend_list")),
            }
            # 优先用 OCR 的 chat_preview 做签名（更接近“新消息变化”），无 OCR 时退化为 chat_area 可用性。
            ocr_info: dict[str, Any] | None = None
            chat_sig = "0"
            if flags["detected_chat_area"] and areas and areas.get("chat_area"):
                img_path = _try_screenshot_png()
                if img_path:
                    try:
                        cb = tuple(int(x) for x in areas["chat_area"])
                        ocr_info = _run_chat_ocr(img_path, cb)
                        if ocr_info.get("ok"):
                            chat_sig = str(ocr_info.get("preview") or "")[:800]
                        else:
                            chat_sig = "1"
                    finally:
                        try:
                            os.unlink(img_path)
                        except OSError:
                            pass
                else:
                    chat_sig = "1"
            message_detected = bool(chat_sig and chat_sig != last_chat_signature and flags["detected_chat_area"])
            last_chat_signature = chat_sig

            if message_detected:
                _log("info", f"检测到疑似新消息变化：{msg}", {"flags": flags, "user_id": uid})

            snap_last_line = ""
            if ocr_info and ocr_info.get("ok"):
                snap_last_line = str(ocr_info.get("last_line") or "").strip()
            try:
                AutoReplyScreenProfile.objects.filter(pk=p.pk).update(
                    agent_runtime_snapshot={
                        "updated_at": django_timezone.now().isoformat(),
                        "detected_chat_area": bool(flags["detected_chat_area"]),
                        "detected_input_box": bool(flags["detected_input_box"]),
                        "detected_user_name_area": bool(flags["detected_user"]),
                        "detected_friend_list": bool(flags["detected_friend_list"]),
                        "detected_message_change": bool(message_detected),
                        "chat_area_source": str(msg or ""),
                        "chat_ocr_preview": (
                            str(ocr_info.get("preview") or "")[:800]
                            if ocr_info and ocr_info.get("ok")
                            else ""
                        ),
                        "chat_last_line": snap_last_line[:500],
                    }
                )
            except Exception:
                pass

            # ── 自动回复闭环：检测到变化 + 有输入框坐标 → 生成回复 → 尝试发送 ─────────────
            if message_detected and flags["detected_input_box"] and areas and areas.get("input_box"):
                now = time.time()
                # 简单防抖：避免 OCR 抖动导致频繁触发
                if now - last_auto_reply_at < max(2.0, float(interval) * 0.8):
                    continue
                last_auto_reply_at = now

                last_line = ""
                if ocr_info and ocr_info.get("ok"):
                    last_line = str(ocr_info.get("last_line") or "").strip()
                if not last_line:
                    _log("warn", "检测到变化，但 OCR 未取到最后一句文本，跳过自动回复", {"user_id": uid})
                    continue

                friend_name = ""
                try:
                    if areas.get("user_name_area"):
                        img2 = _try_screenshot_png()
                        if img2:
                            try:
                                ub = tuple(int(x) for x in areas["user_name_area"])
                                uocr = _run_user_ocr(img2, ub)
                                if uocr.get("ok"):
                                    friend_name = str(uocr.get("text") or "").strip()[:128]
                            finally:
                                try:
                                    os.unlink(img2)
                                except OSError:
                                    pass
                except Exception:
                    friend_name = ""

                # 如果配置了监听好友列表，则仅对命中的好友触发
                mf = prof.get("monitored_friends") if isinstance(prof.get("monitored_friends"), list) else []
                if mf and friend_name and friend_name not in {str(x) for x in mf}:
                    continue

                rule = None
                rid: int | None = None
                fo = prof.get("friends_overrides") if isinstance(prof.get("friends_overrides"), dict) else {}
                if friend_name and isinstance(fo, dict):
                    o = fo.get(friend_name)
                    if isinstance(o, dict):
                        try:
                            rid = int(o.get("rule_id")) if o.get("rule_id") not in (None, "", 0) else None
                        except Exception:
                            rid = None
                if rid is None:
                    rid2 = prof.get("default_rule_id")
                    rid = int(rid2) if isinstance(rid2, int) else None
                if isinstance(rid, int):
                    rule = AutoReplyRule.objects.filter(pk=rid, user_id=uid, is_active=True).first()

                job = AutoReplyJob.objects.create(
                    user_id=uid,
                    rule=rule,
                    input_text=last_line[:16000],
                    friend_name=friend_name,
                    status=AutoReplyJob.Status.PENDING,
                )
                _log("info", f"检测到新消息，已创建回复任务 #{job.pk}", {"job_id": job.pk, "user_id": uid})

                from ai_engine.auto_reply.runner import run_auto_reply_job_sync

                run_auto_reply_job_sync(int(job.pk))
                job.refresh_from_db()
                if job.status != AutoReplyJob.Status.COMPLETED or not (job.reply_text or "").strip():
                    _log("error", f"回复生成失败：{job.error_message or 'unknown_error'}", {"job_id": job.pk, "user_id": uid})
                    continue

                ok, detail = _try_send_text_via_pyautogui(str(job.reply_text), tuple(int(x) for x in areas["input_box"]))
                _log("info" if ok else "error", "已发送回复" if ok else f"发送失败：{detail}", {"job_id": job.pk, "user_id": uid})
        except Exception as e:
            _log("error", f"屏幕代理异常：{e}", {"user_id": uid})
            interval = 10
        time.sleep(interval)

