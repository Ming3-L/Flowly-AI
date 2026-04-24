"""
服务端本机屏幕代理（独立进程）：

- 直接读取/写入 Django ORM（无需 JWT / HTTP 回调）
- 复用 desktop_screen_agent.engine 的 YOLO 区域识别逻辑
- 将状态写入 AutoReplyScreenEvent / AutoReplyMonitorLogLine，供前端展示

注意：该代理需要在**有桌面会话**的机器上运行（Windows 需要可用的截图 API）。
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

from django.conf import settings
from django.db import transaction

from ai_engine.desktop_screen_agent.engine import areas_to_jsonable, get_chat_areas_from_profile
from ai_engine.models import AutoReplyMonitorLogLine, AutoReplyScreenEvent, AutoReplyScreenProfile

log = logging.getLogger(__name__)


def _emit_event(*, user_id: int, event_type: str, message: str = "", payload: dict[str, Any] | None = None) -> None:
    AutoReplyScreenEvent.objects.create(
        user_id=int(user_id),
        event_type=(event_type or "").strip()[:40],
        message=(message or "")[:4000],
        payload=dict(payload or {}),
    )


def _emit_log(*, user_id: int, level: str, line: str, extra: dict[str, Any] | None = None) -> None:
    lv = (level or "info").strip().lower()
    if lv not in {x[0] for x in AutoReplyMonitorLogLine.Level.choices}:
        lv = AutoReplyMonitorLogLine.Level.INFO
    AutoReplyMonitorLogLine.objects.create(
        user_id=int(user_id),
        level=lv,
        line=(line or "").strip()[:8000],
        extra=dict(extra or {}),
    )


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
    """将识别结果写回 ScreenProfile 坐标，并 ack nonce。"""
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
    阻塞循环：读取 profile → 识别 → 写 events/logs。
    设计为在 multiprocessing 子进程中运行。
    """
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    uid = int(user_id)
    _emit_log(user_id=uid, level="info", line="本机屏幕代理（服务端进程）已启动", extra={"pid": os.getpid()})

    last_chat_signature = ""

    while True:
        try:
            if stop_event is not None and getattr(stop_event, "is_set", None) and stop_event.is_set():
                _emit_log(user_id=uid, level="info", line="本机屏幕代理已收到停止信号", extra={"pid": os.getpid()})
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

            # region-detect：只在前端请求 nonce > ack 时执行并写回
            nonce = int(prof.get("region_detect_nonce") or 0)
            ack = int(prof.get("region_detect_ack_nonce") or 0)
            if nonce > ack:
                areas2, msg2 = get_chat_areas_from_profile(
                    prof,
                    yolo_weights_path=str(getattr(settings, "FLOWLY_SCREEN_YOLO_WEIGHTS", "") or "").strip() or None,
                )
                if areas2:
                    _apply_detected_layout(user_id=uid, nonce=nonce, areas=areas2)
                    _emit_log(user_id=uid, level="info", line=f"区域识别已写回：{msg2}", extra={"nonce": nonce})
                else:
                    _emit_log(user_id=uid, level="warn", line=f"区域识别未成功：{msg2}", extra={"nonce": nonce})

            if not prof.get("monitoring_active"):
                _emit_event(
                    user_id=uid,
                    event_type="heartbeat",
                    message="监控已暂停（仅轮询配置）",
                    payload={"paused": True, "chat_software": prof.get("chat_software")},
                )
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
            # “检测到消息”在未启用 OCR 时只能粗略：以 chat_area 是否存在代替；
            # 后续可接 OCR/对比增量识别。
            chat_sig = "1" if flags["detected_chat_area"] else "0"
            message_detected = chat_sig != last_chat_signature and flags["detected_chat_area"]
            last_chat_signature = chat_sig

            payload = {
                "areas": areas_to_jsonable(areas),
                "chat_software": prof.get("chat_software"),
                "message_detected": bool(message_detected),
                **flags,
            }
            _emit_event(user_id=uid, event_type="heartbeat", message=msg, payload=payload)
        except Exception as e:
            _emit_event(user_id=uid, event_type="error", message=str(e), payload={"exception": str(e)})
            _emit_log(user_id=uid, level="error", line=f"屏幕代理异常：{e}", extra={})
            interval = 10
        time.sleep(interval)

