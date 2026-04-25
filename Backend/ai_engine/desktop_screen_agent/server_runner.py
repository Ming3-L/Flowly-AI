"""
服务端本机屏幕代理（独立进程）：

- 直接读取/写入 Django ORM（无需 JWT / HTTP 回调）
- 复用 desktop_screen_agent.engine 的 YOLO 区域识别逻辑
- 不再将“监控事件/监控日志”写入数据库（按需求下线）

注意：该代理需要在**有桌面会话**的机器上运行（Windows 需要可用的截图 API）。
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import tempfile
import time
import subprocess
from typing import Any

from django.conf import settings
from django.utils import timezone as django_timezone

from ai_engine.desktop_screen_agent.engine import get_chat_areas_from_profile
from ai_engine.models import AutoReplyJob, AutoReplyRule, AutoReplyScreenProfile

log = logging.getLogger(__name__)

_SEND_KEY_RAW = (os.getenv("FLOWLY_SCREEN_SEND_KEY") or "").strip().lower()
_SEND_KEY = _SEND_KEY_RAW if _SEND_KEY_RAW in ("enter", "ctrl_enter") else "enter"
_SEND_METHOD_RAW = (os.getenv("FLOWLY_SCREEN_SEND_METHOD") or "").strip().lower()
_SEND_METHOD = _SEND_METHOD_RAW if _SEND_METHOD_RAW in ("clipboard", "typewrite") else "clipboard"


def _log(level: str, msg: str, extra: dict[str, Any] | None = None) -> None:
    lv = (level or "info").strip().lower()
    payload = {"extra": extra or {}}
    if lv == "error":
        log.error(msg, extra=payload)
    elif lv == "warn" or lv == "warning":
        log.warning(msg, extra=payload)
    elif lv == "debug":
        log.debug(msg, extra=payload)
    else:
        log.info(msg, extra=payload)


def _try_screenshot_png() -> str | None:
    try:
        import pyautogui  # type: ignore[import-untyped]
    except ImportError:
        _log("warn", "pyautogui 未安装，无法截图", {})
        return None
    try:
        shot = pyautogui.screenshot()
        fd, path = tempfile.mkstemp(suffix=".png", prefix="flowly_screen_")
        os.close(fd)
        shot.save(path, format="PNG")
        return path
    except Exception:
        _log("warn", "截图失败（pyautogui.screenshot 抛异常）", {})
        return None


def _run_chat_ocr(image_path: str, chat_box: tuple[int, int, int, int]) -> dict[str, Any]:
    from ai_engine.desktop_screen_agent.ocr_subprocess import chat_lines_to_preview, run_ocr_subprocess

    res = run_ocr_subprocess("chat_window", image_path=image_path, box=chat_box)
    if not res.get("ok"):
        return {"ok": False, "error": str(res.get("error") or "ocr_failed")}
    lines = res.get("lines") if isinstance(res.get("lines"), list) else []
    preview = chat_lines_to_preview(lines, max_chars=1200)
    last_line = ""
    last_ln: dict[str, Any] | None = None
    for ln in reversed(lines or []):
        if not isinstance(ln, dict):
            continue
        t = str((ln or {}).get("text", "")).strip()
        if t:
            last_line = t
            last_ln = ln
            break

    # 归属判断（粗略）：利用气泡位置（left/right）判断是否为“自己发出”
    # - 参考 bundle 的 ocr 会给出每行 left/right/img_w（相对裁剪图）
    # - 一般微信：对方在左，自己在右
    last_from_me: bool | None = None
    try:
        if last_ln:
            img_w = last_ln.get("img_w")
            left = last_ln.get("left")
            right = last_ln.get("right")
            if isinstance(img_w, (int, float)) and isinstance(left, (int, float)) and isinstance(right, (int, float)) and img_w:
                center = (float(left) + float(right)) / 2.0
                # 0.55 是经验阈值：留一点中间容错，避免居中系统提示误判
                last_from_me = center >= float(img_w) * 0.55
    except Exception:
        last_from_me = None

    return {
        "ok": True,
        "preview": preview,
        "last_line": last_line,
        "line_count": len(lines),
        "last_from_me": last_from_me,
        "lines": lines,
    }


def _infer_last_message_by_position(chat_lines: list[dict]) -> tuple[str, bool | None]:
    """
    参考旧项目 @core 思路：将 OCR 行合并为“气泡块”，用左右边距/中心线判断归属。

    返回：(last_text, last_from_me)；无法判断时 last_from_me=None。
    """
    if not chat_lines:
        return "", None

    # 计算聊天区域宽度（优先用 img_w，避免 min/max 被文本内容拉歪）
    img_w = None
    for ln in chat_lines:
        w = (ln or {}).get("img_w")
        if isinstance(w, (int, float)) and w:
            img_w = int(w)
            break
    if img_w is None:
        try:
            img_w = max(int((ln or {}).get("right", 0)) for ln in chat_lines)
        except Exception:
            img_w = None
    if not img_w:
        return "", None
    img_w = max(1, int(img_w))

    def _is_time_or_system_line(text: str) -> bool:
        s = (text or "").strip()
        if not s:
            return True
        # 极短纯数字多为噪声；更长数字可能是真实内容（金额/验证码）
        if s.isdigit():
            return len(s) <= 2
        if ":" in s and len(s) <= 8:
            parts = s.split(":")
            if len(parts) == 2 and all(p.isdigit() for p in parts):
                try:
                    hh = int(parts[0])
                    mm = int(parts[1])
                    if 0 <= hh <= 23 and 0 <= mm <= 59:
                        return True
                except Exception:
                    pass
        keep = [ch for ch in s if ch not in " \t\r\n"]
        if keep and all(ch.isdigit() or ch in ":.-/" for ch in keep):
            return True
        return False

    def _is_ascii_noise_short(text: str) -> bool:
        s = "".join(str(text or "").split())
        if not s:
            return True
        # 仅 ASCII 的超短 token 很可能是噪声（边框/分隔符）
        if len(s) > 2:
            return False
        return bool(re.fullmatch(r"[A-Za-z0-9:./\\-_]+", s))

    rows: list[dict[str, Any]] = []
    for ln in chat_lines or []:
        if not isinstance(ln, dict):
            continue
        text = str((ln or {}).get("text", "")).strip()
        if _is_time_or_system_line(text) or _is_ascii_noise_short(text):
            continue
        try:
            left = int((ln or {}).get("left", 0))
            right = int((ln or {}).get("right", 0))
            top = int((ln or {}).get("top", 0))
            bottom = int((ln or {}).get("bottom", top))
        except Exception:
            continue
        if not text:
            continue
        rows.append({"text": text, "left": left, "right": right, "top": top, "bottom": bottom})

    if not rows:
        return "", None

    rows.sort(key=lambda x: (int(x["top"]), int(x["left"])))

    # 合并为气泡块：按垂直相邻 + 水平重叠/贴边
    blocks: list[dict[str, Any]] = []
    for r in rows:
        if blocks:
            b = blocks[-1]
            v_gap = int(r["top"]) - int(b["bottom"])
            b_h = max(1, int(b["bottom"]) - int(b["top"]))
            overlap = max(0, min(int(r["right"]), int(b["right"])) - max(int(r["left"]), int(b["left"])))
            overlap_ratio = overlap / float(max(1, min(int(r["right"]) - int(r["left"]), int(b["right"]) - int(b["left"]))))
            close_left = abs(int(r["left"]) - int(b["left"])) <= 20
            close_right = abs(int(r["right"]) - int(b["right"])) <= 35
            same_bubble = v_gap <= max(18, int(b_h * 0.9)) and (overlap_ratio >= 0.22 or close_left or close_right)
            if same_bubble:
                b["texts"].append(r["text"])
                b["left"] = min(int(b["left"]), int(r["left"]))
                b["right"] = max(int(b["right"]), int(r["right"]))
                b["top"] = min(int(b["top"]), int(r["top"]))
                b["bottom"] = max(int(b["bottom"]), int(r["bottom"]))
                continue
        blocks.append(
            {
                "texts": [r["text"]],
                "left": int(r["left"]),
                "right": int(r["right"]),
                "top": int(r["top"]),
                "bottom": int(r["bottom"]),
            }
        )

    # 取“最靠下”的块作为最后一条消息
    blocks.sort(key=lambda x: (int(x.get("bottom", 0)), int(x.get("top", 0)), int(x.get("left", 0))))
    last = blocks[-1]
    last_text = "\n".join([t for t in last.get("texts", []) if str(t).strip()]).strip()
    if not last_text:
        return "", None

    chat_left = 0
    chat_right = img_w
    chat_width = max(1, chat_right - chat_left)
    margin_bias_px = max(12, int(chat_width * 0.02))
    left_margin = max(0.0, float(int(last["left"]) - chat_left))
    right_margin = max(0.0, float(chat_right - int(last["right"])))
    center_x = (float(int(last["left"])) + float(int(last["right"]))) / 2.0
    rel_center = (center_x - chat_left) / float(chat_width)

    if right_margin + margin_bias_px < left_margin:
        return last_text, True
    if left_margin + margin_bias_px < right_margin:
        return last_text, False
    return last_text, (rel_center >= 0.5)


def _run_user_ocr(image_path: str, user_box: tuple[int, int, int, int]) -> dict[str, Any]:
    """从“用户/好友名区域”粗略 OCR 出当前会话对方显示名。"""
    from ai_engine.desktop_screen_agent.ocr_subprocess import run_ocr_subprocess

    # ocr_reference_worker 支持的 op 为 user_area（返回 text 字段）
    res = run_ocr_subprocess("user_area", image_path=image_path, box=user_box)
    if not res.get("ok"):
        return {"ok": False, "error": str(res.get("error") or "ocr_failed")}
    text = str(res.get("text") or "").strip()
    return {"ok": True, "text": text}


def _run_input_ocr(image_path: str, input_box: tuple[int, int, int, int]) -> dict[str, Any]:
    """OCR 输入框内容（用于判断是否已真正发送/清空）。"""
    from ai_engine.desktop_screen_agent.ocr_subprocess import run_ocr_subprocess

    res = run_ocr_subprocess("input_area", image_path=image_path, box=input_box)
    if not res.get("ok"):
        return {"ok": False, "error": str(res.get("error") or "ocr_failed")}
    text = str(res.get("text") or "").strip()
    return {"ok": True, "text": text}


def _set_clipboard_text(text: str) -> tuple[bool, str]:
    """
    Windows 优先使用系统剪贴板（不额外引入依赖）：
    - 若安装了 pyperclip 则使用它
    - 否则用 PowerShell Set-Clipboard
    """
    t = str(text or "")
    try:
        import pyperclip  # type: ignore[import-untyped]

        pyperclip.copy(t)
        return True, "pyperclip"
    except Exception:
        pass
    try:
        # PowerShell Set-Clipboard 需要字符串；用 stdin 传入避免转义问题
        p = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "Set-Clipboard -Value ([Console]::In.ReadToEnd())"],
            input=t,
            text=True,
            capture_output=True,
            timeout=3,
        )
        if p.returncode == 0:
            return True, "powershell"
        return False, (p.stderr or p.stdout or f"exit={p.returncode}")[:300]
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"

def _postprocess_reply_text(text: str) -> str:
    """
    将模型输出处理为“可直接发送”的纯文本：
    - 去掉常见前缀（assistant/回复/答复等）
    - 去掉代码块围栏
    - 压缩多余空行
    """
    t = str(text or "")
    t = t.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not t:
        return ""

    # 去掉 markdown code fences（避免模型输出 ```...``` 直接发出去）
    if "```" in t:
        parts = [p for p in t.split("```") if p.strip()]
        if parts:
            # 取最长的一段作为正文（简单策略：避免只剩语言标记）
            parts.sort(key=lambda s: len(s.strip()), reverse=True)
            t = parts[0].strip()

    # 去掉常见“角色/说明”前缀
    for prefix in (
        "assistant:",
        "assistant：",
        "回复：",
        "答复：",
        "建议回复：",
        "可回复：",
        "可以回复：",
        "回复内容：",
    ):
        if t.lower().startswith(prefix.lower()):
            t = t[len(prefix) :].strip()
            break

    # 如果模型把内容包在引号/书名号里，去一层
    if len(t) >= 2 and ((t[0] == t[-1] == '"') or (t[0] == t[-1] == "'") or (t[0], t[-1]) in (("「", "」"), ("《", "》"), ("“", "”"))):
        t = t[1:-1].strip()

    # 压缩空行
    lines = [ln.rstrip() for ln in t.split("\n")]
    out_lines: list[str] = []
    blank = 0
    for ln in lines:
        if not ln.strip():
            blank += 1
            if blank <= 1:
                out_lines.append("")
            continue
        blank = 0
        out_lines.append(ln)
    t = "\n".join(out_lines).strip()
    return t


def _verify_sent_after_action(
    *,
    expected_reply: str,
    chat_box: tuple[int, int, int, int] | None,
    input_box: tuple[int, int, int, int],
    max_wait_s: float = 2.2,
) -> tuple[bool, str]:
    """
    发送动作后的“软校验”：
    - 优先看输入框是否清空（或不再包含我们刚输入的内容）
    - 若提供 chat_box，则额外 OCR 聊天区，判断最后一条是否为“自己发出”
    """
    exp = (expected_reply or "").strip()
    if not exp:
        return False, "empty_reply"
    deadline = time.time() + max(0.4, float(max_wait_s))

    last_err = ""
    while time.time() < deadline:
        img = _try_screenshot_png()
        if not img:
            last_err = "screenshot_failed"
            time.sleep(0.15)
            continue
        try:
            inp = _run_input_ocr(img, input_box)
            if inp.get("ok"):
                txt = str(inp.get("text") or "").strip()
                # 常见情况：发送成功后输入框清空
                if not txt:
                    return True, "input_cleared"
                # 兼容 OCR 不稳定：若输入框不再“包含”我们刚输入的前缀，也视为可能已发送
                if exp and (exp[:18] not in txt):
                    return True, "input_changed"
            else:
                last_err = f"input_ocr_failed:{inp.get('error')}"

            if chat_box:
                chat = _run_chat_ocr(img, chat_box)
                if chat.get("ok"):
                    lines = chat.get("lines") if isinstance(chat.get("lines"), list) else []
                    last_text2, last_from_me2 = _infer_last_message_by_position(lines)
                    if last_from_me2 is True:
                        # 若能取到文本，尽量校验包含我们发送的片段，避免“发到了别的会话/误判自己气泡”为成功
                        probe = exp.replace("\n", " ").strip()
                        probe = probe[:24]
                        if probe and last_text2 and probe not in last_text2:
                            last_err = "chat_last_from_me_but_text_mismatch"
                        else:
                            return True, "chat_last_from_me"
                else:
                    last_err = f"chat_ocr_failed:{chat.get('error')}"
        finally:
            try:
                os.unlink(img)
            except OSError:
                pass

        time.sleep(0.18)
    return False, last_err or "verify_timeout"


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
        w = max(1, int(x2 - x1))
        h = max(1, int(y2 - y1))
        # 点击输入框“偏左上”的可输入区域，避开右侧按钮/空白
        cx = int(x1 + w * 0.30)
        cy = int(y1 + h * 0.35)
        # 保底：确保在 box 内部（留 2px 边距）
        cx = max(x1 + 2, min(x2 - 2, cx))
        cy = max(y1 + 2, min(y2 - 2, cy))
        pyautogui.click(cx, cy)
        time.sleep(0.18)
        # 尽量覆盖已有输入（避免残留导致“没发出去但输入框里有内容”被误判）
        try:
            pyautogui.hotkey("ctrl", "a")
            time.sleep(0.03)
        except Exception:
            pass
        if _SEND_METHOD == "clipboard":
            okc, how = _set_clipboard_text(t)
            if not okc:
                return False, f"clipboard_failed:{how}"
            pyautogui.hotkey("ctrl", "v")
            time.sleep(0.06)
            send_detail = f"clipboard:{how}"
        else:
            pyautogui.typewrite(t, interval=0.01)
            time.sleep(0.05)
            send_detail = "typewrite"
        if _SEND_KEY == "ctrl_enter":
            pyautogui.hotkey("ctrl", "enter")
        else:
            pyautogui.press("enter")
        return True, f"action_ok:{_SEND_KEY}|{send_detail}"
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


def _runtime_boxes_from_areas(areas: dict[str, Any] | None) -> dict[str, Any]:
    """YOLO 本轮框：仅用于运行快照，不落库到 ScreenProfile 坐标字段。"""
    if not areas:
        return {}
    out: dict[str, Any] = {}
    if areas.get("chat_area"):
        out["runtime_chat_window_box"] = [int(x) for x in areas["chat_area"]]
    if areas.get("input_box"):
        out["runtime_input_box_pos"] = [int(x) for x in areas["input_box"]]
    if areas.get("user_object"):
        out["runtime_user_name_box"] = [int(x) for x in areas["user_object"]]
    if areas.get("friend_list"):
        out["runtime_friend_list_box"] = [int(x) for x in areas["friend_list"]]
    return out


def _snapshot_hash(payload: dict[str, Any]) -> str:
    """排除 updated_at 计算哈希，用于避免无意义的数据库 UPDATE。"""
    core = {k: v for k, v in payload.items() if k != "updated_at"}
    try:
        blob = json.dumps(core, ensure_ascii=False, sort_keys=True, default=str)
    except Exception:
        blob = str(core)
    return hashlib.sha256(blob.encode("utf-8", errors="replace")).hexdigest()


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
    last_flags_sig = ""
    last_snapshot_sig = ""
    last_friend_name = ""
    last_user_ocr_at = 0.0
    last_snapshot_core_hash = ""

    while True:
        try:
            if stop_event is not None and getattr(stop_event, "is_set", None) and stop_event.is_set():
                _log("info", "本机屏幕代理已收到停止信号", {"pid": os.getpid(), "user_id": uid})
                break
        except Exception:
            pass
        interval = 10
        try:
            p = (
                AutoReplyScreenProfile.objects.only(
                    "pk",
                    "user_id",
                    "monitoring_active",
                    "check_interval_seconds",
                    "use_yolo",
                    "monitored_friends",
                    "friends_overrides",
                    "default_rule_id",
                    "knowledge_reply_enabled",
                    "chat_software",
                    "region_detect_nonce",
                    "region_detect_ack_nonce",
                    "chat_window_box",
                    "input_box_pos",
                    "user_name_box",
                    "friend_list_box",
                    "agent_runtime_snapshot",
                )
                .filter(user_id=uid)
                .first()
            )
            if p is None:
                # 没配置就休眠
                _log("info", "未找到屏幕配置（AutoReplyScreenProfile），等待中", {"user_id": uid})
                time.sleep(10)
                continue
            prof = _profile_to_dict(p)
            interval = max(1, int(prof.get("check_interval_seconds") or 3))

            # 区域识别：仅在前端请求的 nonce > ack 时执行，结果写入运行快照并推进 ack（不写布局坐标字段）
            nonce = int(prof.get("region_detect_nonce") or 0)
            ack = int(prof.get("region_detect_ack_nonce") or 0)
            if nonce > ack:
                areas2, msg2 = get_chat_areas_from_profile(
                    prof,
                    yolo_weights_path=str(getattr(settings, "FLOWLY_SCREEN_YOLO_WEIGHTS", "") or "").strip() or None,
                )
                if areas2:
                    prev = p.agent_runtime_snapshot if isinstance(p.agent_runtime_snapshot, dict) else {}
                    snap2 = dict(prev)
                    snap2.update(_runtime_boxes_from_areas(areas2))
                    snap2["region_detect_msg"] = str(msg2 or "")
                    snap2["updated_at"] = django_timezone.now().isoformat()
                    AutoReplyScreenProfile.objects.filter(pk=p.pk).update(
                        region_detect_ack_nonce=int(nonce),
                        agent_runtime_snapshot=snap2,
                    )
                    _log("info", f"区域识别完成（仅写入运行快照，不落库坐标）：{msg2}", {"nonce": nonce, "user_id": uid})
                else:
                    _log("warn", f"区域识别未成功：{msg2}", {"nonce": nonce, "user_id": uid})

            if not prof.get("monitoring_active"):
                _log("info", "monitoring_active=false，代理暂不监控", {"user_id": uid})
                time.sleep(max(12, interval * 4))
                continue

            areas, msg = get_chat_areas_from_profile(
                prof,
                yolo_weights_path=str(getattr(settings, "FLOWLY_SCREEN_YOLO_WEIGHTS", "") or "").strip() or None,
            )
            if not areas:
                _log("info", f"区域识别未返回 areas：{msg}", {"user_id": uid})
            flags = {
                "detected_chat_area": bool(areas and areas.get("chat_area")),
                "detected_user": bool(areas and areas.get("user_object")),
                "detected_input_box": bool(areas and areas.get("input_box")),
                "detected_friend_list": bool(areas and areas.get("friend_list")),
            }

            flags_sig = "|".join(f"{k}={1 if v else 0}" for k, v in sorted(flags.items()))
            if flags_sig != last_flags_sig:
                last_flags_sig = flags_sig
                _log("info", "区域识别状态变化", {"user_id": uid, "flags": flags, "source": msg})
            # 优先用 OCR 的“最后一条对方消息”做触发签名（更贴近自动回复场景）。
            ocr_info: dict[str, Any] | None = None
            chat_sig = "0"
            last_other_text = ""
            last_from_me_pos: bool | None = None
            if flags["detected_chat_area"] and areas and areas.get("chat_area"):
                img_path = _try_screenshot_png()
                if img_path:
                    try:
                        cb = tuple(int(x) for x in areas["chat_area"])
                        t0 = time.time()
                        ocr_info = _run_chat_ocr(img_path, cb)
                        ocr_ms = int((time.time() - t0) * 1000)
                        if ocr_info.get("ok"):
                            last_text2, last_from_me2 = _infer_last_message_by_position(
                                ocr_info.get("lines") if isinstance(ocr_info.get("lines"), list) else []
                            )
                            last_from_me_pos = last_from_me2
                            # 只用“对方最后一句”作为签名来源；若最后一句为自己，则不触发
                            if last_text2 and last_from_me2 is False:
                                last_other_text = last_text2
                                chat_sig = last_text2[:800]
                            else:
                                chat_sig = "self_or_empty"
                            _log(
                            "debug",
                            "OCR 完成",
                                {
                                    "user_id": uid,
                                    "ms": ocr_ms,
                                    "last_from_me": last_from_me2,
                                    "last_other_text": last_other_text[:120],
                                },
                            )
                        else:
                            # OCR 失败时不应触发“消息变化”，否则会出现你现在看到的假触发链路
                            err_txt = str(ocr_info.get("error") or "ocr_failed")
                            _log("warn", f"OCR 失败：{err_txt[:500]}", {"user_id": uid})
                            chat_sig = last_chat_signature or "ocr_failed"
                    finally:
                        try:
                            os.unlink(img_path)
                        except OSError:
                            pass
                else:
                    chat_sig = "1"
                    _log("warn", "截图失败，无法 OCR", {"user_id": uid})
            message_detected = bool(chat_sig and chat_sig != last_chat_signature and flags["detected_chat_area"])
            last_chat_signature = chat_sig

            if message_detected:
                _log(
                    "info",
                    "检测到疑似新消息变化",
                    {
                        "user_id": uid,
                        "friend_name": (friend_name or "").strip()[:128],
                        "last_from_me": last_from_me_pos,
                        "last_other_text": (last_other_text or "").strip()[:300],
                        "sig": chat_sig[:80],
                    },
                )

            snap_last_line = ""
            snap_last_from_me: bool | None = None
            if ocr_info and ocr_info.get("ok"):
                snap_last_line = str(ocr_info.get("last_line") or "").strip()
                # 以“块归属判定”为准（更稳），拿不到时再退回简单 center 判定
                snap_last_from_me = last_from_me_pos if last_from_me_pos is not None else ocr_info.get("last_from_me")

            # 用户名 OCR：节流执行（默认 5s），只在识别到 user_object 时尝试
            friend_name = last_friend_name
            try:
                if flags["detected_user"] and areas and areas.get("user_object"):
                    now2 = time.time()
                    if now2 - last_user_ocr_at >= 5.0:
                        last_user_ocr_at = now2
                        img2 = _try_screenshot_png()
                        if img2:
                            try:
                                ub = tuple(int(x) for x in areas["user_object"])
                                uocr = _run_user_ocr(img2, ub)
                                if uocr.get("ok"):
                                    friend_name = str(uocr.get("text") or "").strip()[:128]
                            finally:
                                try:
                                    os.unlink(img2)
                                except OSError:
                                    pass
            except Exception:
                friend_name = last_friend_name
            if friend_name != last_friend_name:
                last_friend_name = friend_name
                _log("info", "识别到会话用户变化", {"user_id": uid, "friend_name": friend_name})

            snap_payload: dict[str, Any] = {
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
                "chat_last_from_me": snap_last_from_me,
                "chat_last_other_text": last_other_text[:500],
                "current_friend_name": friend_name[:128],
            }
            snap_payload.update(_runtime_boxes_from_areas(areas))
            try:
                core_h = _snapshot_hash(snap_payload)
                if core_h != last_snapshot_core_hash:
                    last_snapshot_core_hash = core_h
                    AutoReplyScreenProfile.objects.filter(pk=p.pk).update(agent_runtime_snapshot=snap_payload)
            except Exception:
                pass

            snap_sig = "|".join(
                [
                    f"msgchg={1 if message_detected else 0}",
                    f"fromme={snap_last_from_me}",
                    f"other={last_other_text[:80]}",
                ]
            )
            if snap_sig != last_snapshot_sig:
                last_snapshot_sig = snap_sig
                _log(
                    "debug",
                    "快照变化",
                    {
                        "user_id": uid,
                        "detected_message_change": bool(message_detected),
                        "chat_last_from_me": snap_last_from_me,
                        "chat_last_other_text": last_other_text[:120],
                    },
                )

            # ── 自动回复闭环：检测到变化 + 最后气泡块为“对方” + 有输入框坐标 → 生成回复 → 尝试发送 ─────────────
            last_from_me = last_from_me_pos
            if (
                message_detected
                and last_from_me is False
                and flags["detected_input_box"]
                and areas
                and areas.get("input_box")
            ):
                now = time.time()
                # 简单防抖：避免 OCR 抖动导致频繁触发
                if now - last_auto_reply_at < max(2.0, float(interval) * 0.8):
                    continue
                last_auto_reply_at = now

                last_line = (last_other_text or "").strip()
                if not last_line:
                    _log("warn", "检测到变化，但 OCR 未取到最后一句文本，跳过自动回复", {"user_id": uid})
                    continue

                # 此处复用循环中节流得到的 friend_name（避免重复截图+OCR）
                friend_name = (last_friend_name or "").strip()[:128]

                # 如果配置了监听好友列表，则仅对命中的好友触发
                mf = prof.get("monitored_friends") if isinstance(prof.get("monitored_friends"), list) else []
                if mf and friend_name and friend_name not in {str(x) for x in mf}:
                    _log("info", "好友不在监听列表，跳过自动回复", {"user_id": uid, "friend_name": friend_name})
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

                raw_reply_text = str(job.reply_text)
                reply_text = _postprocess_reply_text(raw_reply_text)
                if not reply_text.strip():
                    _log(
                        "error",
                        "回复文本处理后为空，已跳过发送",
                        {"job_id": job.pk, "user_id": uid, "raw_reply_text": raw_reply_text.strip()[:800]},
                    )
                    continue
                input_box = tuple(int(x) for x in areas["input_box"])
                chat_box = None
                try:
                    if areas.get("chat_area"):
                        chat_box = tuple(int(x) for x in areas["chat_area"])
                except Exception:
                    chat_box = None

                ok, detail = _try_send_text_via_pyautogui(reply_text, input_box)
                if ok:
                    ok2, vdetail = _verify_sent_after_action(
                        expected_reply=reply_text,
                        chat_box=chat_box,
                        input_box=input_box,
                    )
                    if ok2:
                        _log(
                            "info",
                            "已发送回复",
                            {
                                "job_id": job.pk,
                                "user_id": uid,
                                "friend_name": (friend_name or "").strip()[:128],
                                "detected_last_other_text": (last_line or "").strip()[:500],
                                "reply_text": reply_text.strip()[:1200],
                                "raw_reply_text": raw_reply_text.strip()[:1200],
                                "send_action": detail,
                                "verify": vdetail,
                                "boxes": {
                                    "chat_area": list(chat_box) if chat_box else None,
                                    "input_box": list(input_box) if input_box else None,
                                },
                            },
                        )
                    else:
                        _log(
                            "error",
                            "发送动作已执行，但未能确认已发送（可能未聚焦窗口/发送热键不匹配/坐标偏移）",
                            {
                                "job_id": job.pk,
                                "user_id": uid,
                                "friend_name": (friend_name or "").strip()[:128],
                                "detected_last_other_text": (last_line or "").strip()[:500],
                                "reply_text": reply_text.strip()[:1200],
                                "raw_reply_text": raw_reply_text.strip()[:1200],
                                "send_action": detail,
                                "verify": vdetail,
                                "boxes": {
                                    "chat_area": list(chat_box) if chat_box else None,
                                    "input_box": list(input_box) if input_box else None,
                                },
                            },
                        )
                else:
                    _log(
                        "error",
                        f"发送失败：{detail}",
                        {
                            "job_id": job.pk,
                            "user_id": uid,
                            "friend_name": (friend_name or "").strip()[:128],
                            "detected_last_other_text": (last_line or "").strip()[:500],
                            "reply_text": reply_text.strip()[:1200],
                            "raw_reply_text": raw_reply_text.strip()[:1200],
                            "boxes": {"input_box": list(input_box) if input_box else None},
                        },
                    )
            elif message_detected and last_from_me is True:
                _log("info", "检测到变化但最后一句为自己，跳过自动回复", {"user_id": uid})
            elif message_detected and last_from_me is None:
                _log("info", "检测到变化但无法判定归属，跳过自动回复", {"user_id": uid})
            elif message_detected:
                # 兜底：有变化但未进入发送分支，打印一条可读的原因提示（不刷屏，只在 message_detected 时出现）
                _log(
                    "info",
                    "检测到变化但未触发发送",
                    {
                        "user_id": uid,
                        "friend_name": (last_friend_name or "").strip()[:128],
                        "last_other_text": (last_other_text or "").strip()[:300],
                        "last_from_me": last_from_me,
                        "has_input_box": bool(areas and areas.get("input_box")),
                        "monitoring_active": bool(prof.get("monitoring_active")),
                    },
                )
        except Exception as e:
            _log("error", f"屏幕代理异常：{e}", {"user_id": uid})
            interval = 10
        time.sleep(interval)

