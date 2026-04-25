import time
import json
import os
import tempfile

from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import threading
import unicodedata
import re
from src.config.constants import MONITOR_LIST_FILE, PROJECT_ROOT
from src.config.config_manager import (
    friends_config,
    monitored_friends,
    save_config,
    UserConfig,
    set_monitored,
)
from src.core.logger import ocr_logger
from src.core.utils import take_screenshot, crop_image

import hashlib

_OPENOCR = None

# 解析聊天“最后一条消息归属”时的诊断信息（供监控线程按需打印）
_LAST_CHAT_PARSE_DEBUG = {}


def get_last_chat_parse_debug() -> dict:
    """返回最近一次 parse_chat_content_by_position 的诊断信息副本。"""
    try:
        return dict(_LAST_CHAT_PARSE_DEBUG or {})
    except Exception:
        return {}


def _get_openocr():
    global _OPENOCR
    if _OPENOCR is None:
        try:
            from openocr import OpenOCR  # type: ignore[import-untyped]
        except ImportError as e:
            raise ImportError(
                "未安装 openocr-python，无法进行参考 OCR。请在本机后端虚拟环境中执行："
                "pip install openocr-python==0.1.5 "
                "或 pip install -r ai_engine/desktop_screen_agent/ocr_reference_bundle/requirements.txt "
                "（与 Backend/requirements-desktop-agent.txt 中的 OCR 行一致）。"
            ) from e
        # mobile 模式更轻量；需要更高精度可改为 mode='server'（依赖 torch）
        _OPENOCR = OpenOCR(task="ocr", mode="mobile")
    return _OPENOCR

# region agent log
def _dbg(hypothesis_id: str, location: str, message: str, data: dict):
    try:
        payload = {
            "sessionId": "852d3a",
            "runId": "pre-fix",
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data,
            "timestamp": int(time.time() * 1000),
        }
        with open("debug-852d3a.log", "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _normalize_name(name: str) -> str:
    """
    规范化用户名用于比较：
    - Unicode 兼容规范化（NFKC）
    - 去空白 + 小写
    - 将常见“点”符号归一化为同一字符，避免 ° / 。 / . 误差导致不匹配
    """
    s = unicodedata.normalize("NFKC", str(name or ""))
    dot_like = {"。", "°", "·", "•", "．", "."}
    s = "".join("." if ch in dot_like else ch for ch in s)
    return "".join(s.split()).casefold()


def _to_codepoints(name: str) -> str:
    """将字符串表示为 Unicode 码点序列，便于排查隐藏字符差异。"""
    return " ".join(f"U+{ord(ch):04X}" for ch in str(name or ""))


def _rgb_to_hsv_approx(r: int, g: int, b: int):
    """轻量 HSV（H:0-360, S/V:0-1），用于颜色阈值判断。"""
    rf, gf, bf = r / 255.0, g / 255.0, b / 255.0
    mx = max(rf, gf, bf)
    mn = min(rf, gf, bf)
    diff = mx - mn
    if diff == 0:
        h = 0.0
    elif mx == rf:
        h = (60 * ((gf - bf) / diff) + 360) % 360
    elif mx == gf:
        h = (60 * ((bf - rf) / diff) + 120) % 360
    else:
        h = (60 * ((rf - gf) / diff) + 240) % 360
    s = 0.0 if mx == 0 else diff / mx
    v = mx
    return h, s, v


def _has_red_dot(friend_img: Image.Image, *, y1: int, y2: int, x_max: int) -> bool:
    """
    在好友列表裁剪图中检测“小红点/红色未读标记”。
    仅在行的左侧（x < x_max）与行的垂直范围（y1..y2）内查找红色像素占比。
    """
    try:
        if friend_img is None:
            return False
        img = friend_img.convert("RGB")
        w, h = img.size
        x_max = max(1, min(int(x_max), w))
        y1 = max(0, min(int(y1), h - 1))
        y2 = max(0, min(int(y2), h))
        if y2 <= y1 + 3:
            return False

        px = img.load()
        red = 0
        total = 0
        # 取样步长：降低开销
        step_x = 2
        step_y = 2
        for y in range(y1, y2, step_y):
            for x in range(0, x_max, step_x):
                r, g, b = px[x, y]
                # 红点通常是饱和红
                h_hsv, s_hsv, v_hsv = _rgb_to_hsv_approx(int(r), int(g), int(b))
                is_red = (0 <= h_hsv <= 20 or 340 <= h_hsv <= 360) and s_hsv >= 0.55 and v_hsv >= 0.55
                if is_red:
                    red += 1
                total += 1
        if total <= 0:
            return False
        # 红点面积很小，但在左侧窄区域会形成明显“红像素簇”
        return (red / total) >= 0.02
    except Exception:
        return False


def _is_red_pixel(r: int, g: int, b: int) -> bool:
    try:
        h_hsv, s_hsv, v_hsv = _rgb_to_hsv_approx(int(r), int(g), int(b))
        return (0 <= h_hsv <= 20 or 340 <= h_hsv <= 360) and s_hsv >= 0.55 and v_hsv >= 0.50
    except Exception:
        return False


def _detect_unread_badge(row_img: Image.Image):
    """
    在“单个好友项行图”中检测红色未读圆圈，并尽量识别圆圈内的数字。
    返回：(has_badge: bool, unread_count: int, bbox: [x1,y1,x2,y2] | None)
    """
    try:
        if row_img is None:
            return False, 0, None
        img = row_img.convert("RGB")
        w, h = img.size
        if w <= 10 or h <= 10:
            return False, 0, None

        # 搜索区域：左侧头像附近 + 上半部分（未读角标一般在头像边缘上方/右上角）
        sx2 = max(1, int(w * 0.40))
        sy2 = max(1, int(h * 0.60))
        px = img.load()

        step = 2
        xs = []
        ys = []
        for y in range(0, sy2, step):
            for x in range(0, sx2, step):
                r, g, b = px[x, y]
                if _is_red_pixel(r, g, b):
                    xs.append(x)
                    ys.append(y)

        if not xs:
            return False, 0, None

        x1 = max(0, min(xs) - 2)
        x2 = min(w, max(xs) + 3)
        y1 = max(0, min(ys) - 2)
        y2 = min(h, max(ys) + 3)

        bw = x2 - x1
        bh = y2 - y1
        # 角标尺寸：太小可能是噪声，太大可能是其它 UI
        if bw < 6 or bh < 6 or bw > int(h * 0.80) or bh > int(h * 0.80):
            return False, 0, [x1, y1, x2, y2]

        # 近似圆：宽高比不宜太离谱
        ar = bw / float(max(1, bh))
        if ar < 0.55 or ar > 1.80:
            # 仍然允许继续（有些主题角标会被拉伸），但降低误判概率：直接返回 has_badge=False
            return False, 0, [x1, y1, x2, y2]

        # OCR 角标内数字（尽量只取 badge 区域）
        badge_crop = row_img.crop((x1, y1, x2, y2))
        unread = 0
        try:
            pre = badge_crop.convert("L")
            pre = ImageOps.autocontrast(pre)
            pre = pre.resize((max(24, pre.size[0] * 4), max(24, pre.size[1] * 4)), Image.BICUBIC)
            pre = pre.filter(ImageFilter.SHARPEN)
            items = _openocr_run(pre)
            lines = _openocr_items_to_lines(items, score_threshold=0.20, y_merge_px=12)
            text = " ".join(str((ln or {}).get("text", "")).strip() for ln in (lines or [])).strip()
            digits = re.findall(r"\d+", text)
            if digits:
                unread = int(digits[0])
        except Exception:
            unread = 0

        # 有红圈但 OCR 没读到数字：至少当作 1 条未读
        if unread <= 0:
            unread = 1
        return True, unread, [x1, y1, x2, y2]
    except Exception:
        return False, 0, None


def _ocr_name_from_row(row_img: Image.Image) -> str:
    """
    从“单个好友项行图”里更稳地 OCR 出昵称：
    - 排除左侧头像
    - 排除右侧时间列
    - 只取上半部分（昵称行）
    """
    try:
        if row_img is None:
            return ""
        w, h = row_img.size
        if w <= 10 or h <= 10:
            return ""

        avatar_w = int(h * 0.95)  # 头像近似正方形
        x1 = max(0, min(avatar_w, w - 1))
        x2 = max(x1 + 1, int(w * 0.78))  # 右侧 22% 视为时间列
        y2 = max(1, int(h * 0.60))

        crop = row_img.crop((x1, 0, x2, y2))
        pre = _preprocess_for_ocr(crop, upscale=3)
        items = _openocr_run(pre)
        lines = _openocr_items_to_lines(items, score_threshold=0.20, y_merge_px=14)
        cands = []
        for ln in lines or []:
            t = str((ln or {}).get("text", "")).strip()
            if not t:
                continue
            # 过滤时间/纯数字/过长
            s = "".join(t.split())
            if len(s) > 18:
                continue
            if s.isdigit():
                continue
            # "10:56" 之类
            if ":" in s and len(s) <= 8:
                parts = s.split(":")
                if len(parts) == 2 and all(p.isdigit() for p in parts):
                    continue
            cands.append(t)
        if not cands:
            return ""
        # 倾向取最短且最靠前的文本（昵称通常更短）
        cands.sort(key=lambda x: (len("".join(str(x).split())), str(x)))
        return str(cands[0]).strip()
    except Exception:
        return ""


def parse_friend_list_rows(box, image=None):
    """
    从好友列表区域解析出“行”，输出：
      [{name, preview, row_bbox, name_bbox, preview_bbox, has_red_dot}, ...]
    说明：
    - name/preview 依赖 OCR，可能为空
    - has_red_dot 优先信号：基于颜色检测
    """
    if not box:
        return []
    if image is None:
        screenshot = take_screenshot(region=box)
    else:
        screenshot = crop_image(image, box)
    if not screenshot:
        return []

    # OCR items -> line boxes
    # 先对整块好友列表做预处理（放大/增强），提高像“。”这种小字符的召回率
    items = []
    lines = []
    try:
        pre_all = _preprocess_for_ocr(screenshot, upscale=3)
        items2 = _openocr_run(pre_all)
        lines2 = _openocr_items_to_lines(items2, score_threshold=0.30, y_merge_px=16)
        # 选择行数更多的一组作为主结果
        items = items2
        lines = lines2
    except Exception:
        items = _openocr_run(screenshot)
        lines = _openocr_items_to_lines(items, score_threshold=0.35, y_merge_px=16)
    if not lines:
        return []

    # 按 y 合并为“行块”（一个好友通常 1~2 行：名字 + 预览）
    lines_sorted = sorted(lines, key=lambda x: (int(x.get("top", 0)), int(x.get("left", 0))))
    rows = []
    cur = None
    for ln in lines_sorted:
        text = str(ln.get("text", "")).strip()
        if not text:
            continue
        left = int(ln.get("left", 0))
        right = int(ln.get("right", 0))
        top = int(ln.get("top", 0))
        bottom = int(ln.get("bottom", top))
        if cur is None:
            cur = {"lines": [ln], "top": top, "bottom": bottom, "left": left, "right": right}
            continue
        v_gap = top - cur["bottom"]
        # 好友项之间垂直间距通常更大；同一项（名字/预览）间距更小
        if v_gap <= 26:
            cur["lines"].append(ln)
            cur["top"] = min(cur["top"], top)
            cur["bottom"] = max(cur["bottom"], bottom)
            cur["left"] = min(cur["left"], left)
            cur["right"] = max(cur["right"], right)
        else:
            rows.append(cur)
            cur = {"lines": [ln], "top": top, "bottom": bottom, "left": left, "right": right}
    if cur:
        rows.append(cur)

    out = []
    w_img, h_img = screenshot.size
    for r in rows:
        r_lines = sorted(r["lines"], key=lambda x: (int(x.get("top", 0)), int(x.get("left", 0))))
        if not r_lines:
            continue
        def _is_time_like(text: str) -> bool:
            s = (text or "").strip()
            if not s:
                return True
            if ":" in s and len(s) <= 8:
                parts = s.split(":")
                if len(parts) == 2 and all(p.isdigit() for p in parts):
                    try:
                        hh = int(parts[0])
                        mm = int(parts[1])
                        return 0 <= hh <= 23 and 0 <= mm <= 59
                    except Exception:
                        return False
            keep = [ch for ch in s if ch not in " \t\r\n"]
            return bool(keep) and all(ch.isdigit() or ch in ":.-/" for ch in keep)

        def _is_bad_name(text: str) -> bool:
            s = "".join(str(text or "").split())
            if not s:
                return True
            # 红点数字/噪声：纯数字且很短
            if s.isdigit() and len(s) <= 3:
                return True
            # 预览里常见的“[转账]已收款”不是昵称
            if s.startswith("[") and "]" in s[:6]:
                return True
            # 太长的通常是预览，不是昵称
            if len(s) >= 18:
                return True
            # 时间行
            if _is_time_like(s):
                return True
            return False

        # 在同一 row 里挑“像昵称”的那一行：靠左、非时间、非纯数字、长度适中
        name_ln = None
        candidates = []
        for ln in r_lines:
            t = str(ln.get("text", "")).strip()
            if _is_bad_name(t):
                continue
            left = int(ln.get("left", 0))
            top = int(ln.get("top", 0))
            candidates.append((left, top, ln))
        if candidates:
            # 优先 left 更小，其次 top 更小（更靠上）
            candidates.sort(key=lambda x: (x[0], x[1]))
            name_ln = candidates[0][2]
        else:
            # 实在找不到，回退到最靠左的非时间行
            fallback = []
            for ln in r_lines:
                t = str(ln.get("text", "")).strip()
                if not t or _is_time_like(t):
                    continue
                fallback.append((int(ln.get("left", 0)), int(ln.get("top", 0)), ln))
            fallback.sort(key=lambda x: (x[0], x[1]))
            name_ln = fallback[0][2] if fallback else r_lines[0]

        name = str((name_ln or {}).get("text", "")).strip()

        # 若昵称被“时间列”污染（常见：同一行里把右侧 10:45 和左侧昵称拼在一起），
        # 则对该 row 的左侧区域做一次二次 OCR，尽量只读到昵称列。
        try:
            contaminated = False
            s0 = "".join(str(name or "").split())
            if ":" in s0:
                contaminated = True
            # 形如 "10:40 0" / "08:27 ..." 这类也视为污染
            if any(ch.isdigit() for ch in s0) and (":" in s0 or len(s0) <= 8):
                contaminated = True
            if contaminated:
                # 以当前 row 的 y 范围为准，x 只取左侧 65%（避开时间列）
                y1c = max(0, int(r["top"]) - 2)
                y2c = min(h_img, int(r["bottom"]) + 2)
                x2c = int(w_img * 0.65)
                x2c = max(60, min(x2c, w_img))
                sub = screenshot.crop((0, y1c, x2c, y2c))
                pre = _preprocess_for_ocr(sub, upscale=3)
                items_n = _openocr_run(pre)
                lines_n = _openocr_items_to_lines(items_n, score_threshold=0.25, y_merge_px=14)
                # 取最靠左/最靠上的一行作为昵称候选
                if lines_n:
                    lines_n.sort(key=lambda x: (int(x.get("left", 0)), int(x.get("top", 0))))
                    cand = str(lines_n[0].get("text", "")).strip()
                    if cand:
                        name = cand
        except Exception:
            pass

        # 预览：选择同一 row 中位于昵称下方（top 更大）且同样靠左的那一行
        preview_ln = None
        name_bottom = int((name_ln or {}).get("bottom", int((name_ln or {}).get("top", 0))))
        preview_cands = []
        for ln in r_lines:
            if ln is name_ln:
                continue
            t = str(ln.get("text", "")).strip()
            if not t or _is_time_like(t):
                continue
            top = int(ln.get("top", 0))
            left = int(ln.get("left", 0))
            if top >= name_bottom - 2:
                preview_cands.append((top, left, ln))
        preview_cands.sort(key=lambda x: (x[0], x[1]))
        preview_ln = preview_cands[0][2] if preview_cands else None
        preview = str((preview_ln or {}).get("text", "")).strip() if preview_ln else ""

        # 只依赖未读角标（红色圆圈 + 数字）来判断新消息
        row_x1, row_y1, row_x2, row_y2 = int(r["left"]), int(r["top"]), int(r["right"]), int(r["bottom"])
        row_x1 = max(0, min(row_x1, w_img - 1))
        row_y1 = max(0, min(row_y1, h_img - 1))
        row_x2 = max(row_x1 + 1, min(row_x2, w_img))
        row_y2 = max(row_y1 + 1, min(row_y2, h_img))
        row_img = screenshot.crop((row_x1, row_y1, row_x2, row_y2))

        # 更稳的昵称 OCR（避免被时间列、角标数字影响）
        name2 = _ocr_name_from_row(row_img)
        if name2:
            name = name2

        has_badge, unread_count, badge_bbox = _detect_unread_badge(row_img)

        out.append(
            {
                "name": name,
                "preview": preview,
                "row_bbox": [int(r["left"]), int(r["top"]), int(r["right"]), int(r["bottom"])],
                "name_bbox": [int(name_ln.get("left", 0)), int(name_ln.get("top", 0)), int(name_ln.get("right", 0)), int(name_ln.get("bottom", 0))],
                "preview_bbox": [int(preview_ln.get("left", 0)), int(preview_ln.get("top", 0)), int(preview_ln.get("right", 0)), int(preview_ln.get("bottom", 0))] if preview_ln else None,
                "has_unread_badge": bool(has_badge),
                "unread_count": int(unread_count or 0),
                "badge_bbox": badge_bbox,
            }
        )
    # region agent log
    try:
        _dbg(
            "HOCR1",
            "src/core/ocr.py:parse_friend_list_rows",
            "friend list parse summary",
            {
                "box": list(box) if isinstance(box, (list, tuple)) else str(box),
                "img_wh": list(getattr(screenshot, "size", (None, None))),
                "items_count": len(items or []),
                "lines_count": len(lines or []),
                "rows_blocks_count": len(rows or []),
                "out_count": len(out or []),
                "out_head": [
                    {
                        "name": str((it or {}).get("name", "")).strip(),
                        "preview": str((it or {}).get("preview", "")).strip()[:40],
                        "has_red_dot": bool((it or {}).get("has_red_dot")),
                    }
                    for it in (out or [])[:8]
                ],
            },
        )
    except Exception:
        pass
    # endregion
    return out


def find_monitored_friend_updates(friend_list_box, monitored_names, image=None):
    """
    在好友列表里查找“监控名单用户”的更新信号（红点优先，其次 preview 变化）。
    返回：[{name, reason, preview}, ...]
    - reason: "red_dot" | "preview_changed"
    注意：preview_changed 的判定需要由调用方做“上一次缓存”对比，本函数只返回可用信息。
    """
    rows = parse_friend_list_rows(friend_list_box, image=image)
    if not rows:
        return []
    monitored = [str(x).strip() for x in (monitored_names or []) if str(x).strip()]
    if not monitored:
        return []
    mon_norm = {_normalize_name(n): n for n in monitored}

    hits = []
    for r in rows:
        raw_name = str(r.get("name", "")).strip()
        norm = _normalize_name(raw_name)
        target = mon_norm.get(norm) if norm else None
        if not target:
            continue
        if r.get("has_red_dot"):
            hits.append({"name": target, "reason": "red_dot", "preview": str(r.get("preview", "")).strip()})
        else:
            hits.append({"name": target, "reason": "preview_changed", "preview": str(r.get("preview", "")).strip()})
    return hits

def _openocr_run(pil_img: Image.Image):
    """
    使用 OpenOCR 进行端到端 OCR，并尽可能解析出 [ {text, score, points} ] 的统一结构。
    points 期望为 4 个点的多边形（x,y）。
    """
    if pil_img is None:
        return []
    engine = _get_openocr()
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as f:
            tmp_path = f.name
        tmp_base = os.path.basename(tmp_path) if tmp_path else ""
        pil_img.save(tmp_path)
        out = engine(image_path=tmp_path)
        # OpenOCR 的 Python API 可能返回：
        # - (results, time_dicts)
        # - results
        if isinstance(out, tuple) and out:
            results = out[0]
        else:
            results = out

        def _looks_like_item(d: dict) -> bool:
            if not isinstance(d, dict):
                return False
            # OpenOCR/OpenRec 常见字段：transcription/text + points/box + score/confidence
            has_text = any(k in d for k in ("text", "transcription", "rec_text", "label"))
            has_points = any(k in d for k in ("points", "box", "poly", "polygon"))
            return bool(has_text and has_points)

        items = []
        if isinstance(results, list):
            # 可能是：
            # - 每张图一个元素（字符串/容器 dict）
            # - 直接就是 item 列表：[{transcription, points, score}, ...]
            for r in results:
                # 1) item dict（最常见的“直接列表”形式）
                if _looks_like_item(r):
                    items.append(r)
                    continue
                # 2) "name\t<json>"
                if isinstance(r, str) and "\t" in r:
                    try:
                        _, payload = r.split("\t", 1)
                        parsed = json.loads(payload)
                        cand = parsed.get("ocr_result") or parsed.get("result") or parsed.get("results") or parsed
                        if isinstance(cand, list):
                            for it in cand:
                                if _looks_like_item(it):
                                    items.append(it)
                                elif isinstance(it, dict):
                                    items.append(it)
                    except Exception:
                        pass
                    continue
                # 3) 容器 dict：里面可能包着 item 列表
                if isinstance(r, dict):
                    cand = r.get("ocr_result") or r.get("result") or r.get("results") or r.get("data")
                    if isinstance(cand, list):
                        for it in cand:
                            if _looks_like_item(it):
                                items.append(it)
                            elif isinstance(it, dict):
                                items.append(it)
                    elif _looks_like_item(r):
                        items.append(r)
        elif isinstance(results, dict):
            if _looks_like_item(results):
                items = [results]
            else:
                cand = results.get("ocr_result") or results.get("result") or results.get("results") or results.get("data")
                if isinstance(cand, list):
                    items = [it for it in cand if isinstance(it, dict)]

        # 兜底：某些 OpenOCR 版本 Python API 可能不返回结果，但会把结果写到 e2e_results/system_results.txt
        if not items and tmp_base:
            try:
                results_file = os.path.join(PROJECT_ROOT, "e2e_results", "system_results.txt")
                if os.path.isfile(results_file):
                    with open(results_file, "r", encoding="utf-8") as rf:
                        lines = rf.read().splitlines()
                    # 从末尾向前找本次 tmp 文件对应的那一行：<tmp>.png\t[JSON]
                    needle = tmp_base + "\t"
                    payload = None
                    for ln in reversed(lines[-500:]):
                        if ln.startswith(needle):
                            payload = ln[len(needle) :]
                            break
                    if payload:
                        parsed = json.loads(payload)
                        if isinstance(parsed, list):
                            items = [it for it in parsed if isinstance(it, dict)]
            except Exception:
                pass

        normalized = []
        for it in items or []:
            text = (
                it.get("text")
                or it.get("transcription")
                or it.get("rec_text")
                or it.get("label")
                or ""
            )
            text = str(text).strip()
            if not text:
                continue
            score = it.get("score", it.get("confidence", it.get("prob", 0.0)))
            try:
                score = float(score)
            except Exception:
                score = 0.0
            points = it.get("points") or it.get("box") or it.get("poly") or it.get("polygon")
            # points 可能是 [x1,y1,x2,y2...] 或 [[x,y]...]
            pts = []
            if isinstance(points, (list, tuple)) and points:
                if len(points) == 8 and all(isinstance(v, (int, float)) for v in points):
                    pts = [[points[0], points[1]], [points[2], points[3]], [points[4], points[5]], [points[6], points[7]]]
                elif all(isinstance(p, (list, tuple)) and len(p) >= 2 for p in points):
                    pts = [[float(p[0]), float(p[1])] for p in points[:4]]
            normalized.append({"text": text, "score": score, "points": pts})
        return normalized
    finally:
        if tmp_path:
            try:
                os.remove(tmp_path)
            except Exception:
                pass


def _openocr_items_to_lines(items, *, score_threshold: float = 0.45, y_merge_px: int = 18):
    """
    将 OpenOCR 结果（多为词/行块）聚合为“行级”文本，输出与旧代码兼容的 dict 列表：
    {text,left,right,top,bottom,width,height}
    """
    boxes = []
    for it in items or []:
        if float(it.get("score", 0.0) or 0.0) < score_threshold:
            continue
        pts = it.get("points") or []
        if not pts:
            continue
        xs = [p[0] for p in pts if isinstance(p, (list, tuple)) and len(p) >= 2]
        ys = [p[1] for p in pts if isinstance(p, (list, tuple)) and len(p) >= 2]
        if not xs or not ys:
            continue
        left, right = int(min(xs)), int(max(xs))
        top, bottom = int(min(ys)), int(max(ys))
        boxes.append(
            {
                "text": str(it.get("text", "")).strip(),
                "left": left,
                "right": right,
                "top": top,
                "bottom": bottom,
            }
        )
    if not boxes:
        return []
    boxes.sort(key=lambda x: (x["top"], x["left"]))

    lines = []
    cur = None
    for b in boxes:
        if cur is None:
            cur = {"texts": [b["text"]], "left": b["left"], "right": b["right"], "top": b["top"], "bottom": b["bottom"]}
            continue
        y_dist = abs(b["top"] - cur["top"])
        if y_dist <= y_merge_px:
            cur["texts"].append(b["text"])
            cur["left"] = min(cur["left"], b["left"])
            cur["right"] = max(cur["right"], b["right"])
            cur["top"] = min(cur["top"], b["top"])
            cur["bottom"] = max(cur["bottom"], b["bottom"])
        else:
            text = " ".join(cur["texts"]).strip()
            if text:
                lines.append(
                    {
                        "text": text,
                        "left": cur["left"],
                        "right": cur["right"],
                        "top": cur["top"],
                        "bottom": cur["bottom"],
                        "width": cur["right"] - cur["left"],
                        "height": cur["bottom"] - cur["top"],
                    }
                )
            cur = {"texts": [b["text"]], "left": b["left"], "right": b["right"], "top": b["top"], "bottom": b["bottom"]}
    if cur:
        text = " ".join(cur["texts"]).strip()
        if text:
            lines.append(
                {
                    "text": text,
                    "left": cur["left"],
                    "right": cur["right"],
                    "top": cur["top"],
                    "bottom": cur["bottom"],
                    "width": cur["right"] - cur["left"],
                    "height": cur["bottom"] - cur["top"],
                }
            )
    lines.sort(key=lambda x: (x.get("top", 0), x.get("left", 0)))
    return lines


def _preprocess_for_ocr(img: Image.Image, *, upscale: int = 2) -> Image.Image:
    """
    OCR 前处理（不依赖 OpenCV）：
    - 灰度
    - 放大（小字号更友好）
    - 对比度增强 + 锐化
    - 自适应阈值的近似：用中值做二值化
    """
    if img is None:
        return img
    try:
        im = img.convert("L")
        if upscale and upscale > 1:
            im = im.resize((im.width * upscale, im.height * upscale), Image.Resampling.LANCZOS)
        im = ImageOps.autocontrast(im)
        im = ImageEnhance.Contrast(im).enhance(1.6)
        im = im.filter(ImageFilter.SHARPEN)

        # 中值阈值二值化（简单、快）
        hist = im.histogram()
        total = sum(hist)
        acc = 0
        mid = 128
        for i, v in enumerate(hist):
            acc += v
            if acc >= total * 0.5:
                mid = i
                break
        thresh = max(90, min(170, mid))
        im = im.point(lambda p: 255 if p > thresh else 0)
        return im
    except Exception as e:
        ocr_logger.debug(f"OCR预处理失败，回退原图: {e}")
        return img

class MessageManager:
    """消息管理器"""
    def __init__(self):
        self._lock = threading.Lock()
        self.message_history = {}  # 存储用户消息历史
        self.message_count = {}    # 存储用户消息计数
        self.message_hash = {}     # 存储消息哈希，用于去重
        self.message_timestamp = {} # 存储消息时间戳
    
    def get_history(self, user_name):
        """获取用户的消息历史"""
        with self._lock:
            return self.message_history.get(user_name, "")
    
    def set_history(self, user_name, history):
        """设置用户的消息历史"""
        with self._lock:
            self.message_history[user_name] = history
    
    def get_count(self, user_name):
        """获取用户的消息计数"""
        with self._lock:
            return self.message_count.get(user_name, 0)
    
    def set_count(self, user_name, count):
        """设置用户的消息计数"""
        with self._lock:
            self.message_count[user_name] = count
    
    def increment_count(self, user_name):
        """增加用户的消息计数"""
        current_count = self.get_count(user_name)
        self.set_count(user_name, current_count + 1)
    
    def get_message_hash(self, message):
        """生成消息的哈希值"""
        return hashlib.md5(message.encode('utf-8')).hexdigest()
    
    def is_message_duplicate(self, user_name, message):
        """检查消息是否重复"""
        message_hash = self.get_message_hash(message)
        with self._lock:
            if user_name in self.message_hash:
                return self.message_hash[user_name] == message_hash
            return False
    
    def update_message_hash(self, user_name, message):
        """更新消息哈希"""
        with self._lock:
            self.message_hash[user_name] = self.get_message_hash(message)
            self.message_timestamp[user_name] = time.time()
    
    def get_time_since_last_message(self, user_name):
        """获取上次消息到现在的时间间隔"""
        with self._lock:
            if user_name in self.message_timestamp:
                return time.time() - self.message_timestamp[user_name]
            return float("inf")

# 创建消息管理器实例


message_manager = MessageManager()


def load_monitor_list():
    """加载监控好友列表（配置为主 + 文件兼容，统一合并去重）。"""
    file_list = []
    try:
        if os.path.exists(MONITOR_LIST_FILE):
            with open(MONITOR_LIST_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                file_list = [str(x).strip() for x in data if str(x).strip()]
    except (json.JSONDecodeError, OSError, TypeError):
        file_list = []

    cfg_list = [str(x).strip() for x in (monitored_friends or []) if str(x).strip()]
    merged = list(dict.fromkeys(cfg_list + file_list))
    return merged


def save_monitor_list(monitor_list):
    """保存监控好友列表（主写 config.json，兼容输出 monitor_list.json）"""
    with open(MONITOR_LIST_FILE, 'w', encoding='utf-8') as f:
        json.dump(monitor_list, f, ensure_ascii=False, indent=2)
    # 同步到统一配置（失败时仅记录，不阻断主流程）
    try:
        existing = set(monitored_friends or [])
        target = set(monitor_list or [])
        for name in sorted(target - existing):
            set_monitored(name, True)
        for name in sorted(existing - target):
            set_monitored(name, False)
    except Exception as e:
        ocr_logger.warning(f"同步监控名单到配置失败: {e}")


def add_monitor_friend(friend_name):
    """添加监控好友"""
    if not friend_name:
        return False
    monitor_list = load_monitor_list()
    if friend_name in monitor_list:
        return False
    monitor_list.append(friend_name)
    save_monitor_list(monitor_list)
    # 确保好友资料存在（便于监控页/风格页直接看到完整项）
    try:
        if friend_name not in friends_config:
            friends_config[friend_name] = UserConfig(name=friend_name)
            save_config()
    except Exception:
        pass
    ocr_logger.info(f"添加监控好友: {friend_name}")
    return True


def remove_monitor_friend(friend_name):
    """移除监控好友"""
    monitor_list = load_monitor_list()
    if friend_name in monitor_list:
        monitor_list.remove(friend_name)
        save_monitor_list(monitor_list)
        ocr_logger.info(f"移除监控好友: {friend_name}")
        return True
    return False


def get_monitor_list():
    """获取监控好友列表"""
    return load_monitor_list()


def is_monitored(friend_name):
    """检查好友是否在监控列表中"""
    monitor_list = load_monitor_list()
    exact = str(friend_name or "") in monitor_list
    norm_name = _normalize_name(friend_name)
    norm_list = {_normalize_name(n) for n in monitor_list}
    norm_hit = norm_name in norm_list if norm_name else False
    # region agent log
    _dbg(
        "H7",
        "src/core/ocr.py:is_monitored",
        "monitor compare result",
        {
            "exact": bool(exact),
            "normalized_hit": bool(norm_hit),
            "name_len": len(str(friend_name or "")),
            "name_hash8": hashlib.md5(str(friend_name or "").encode("utf-8")).hexdigest()[:8],
            "norm_hash8": hashlib.md5(norm_name.encode("utf-8")).hexdigest()[:8] if norm_name else "",
            "list_size": len(monitor_list),
            "cfg_monitored_size": len(monitored_friends or []),
            "name_codepoints": _to_codepoints(friend_name),
            "list_codepoints": [_to_codepoints(n) for n in monitor_list[:20]],
        },
    )
    # endregion
    # 允许规范化命中，降低 OCR 细小空白差异导致的误判
    return bool(exact or norm_hit)


def parse_chat_content_by_position(chat_lines):
    """
    解析聊天内容（不依赖气泡颜色），仅使用“消息块中心点”判断归属：
    - 将 OCR 行先合并为“气泡块”
    - 若块中心在聊天区域左半 => other；右半 => me
    返回与 parse_chat_content 一致的三元组：
      (other_messages, my_messages, message_sequence)
    """
    other_messages = []
    my_messages = []
    message_sequence = []
    if not chat_lines:
        return other_messages, my_messages, message_sequence

    # 计算聊天区域边界与中心
    # 注意：chat_lines 坐标是“聊天区域裁剪图”的局部坐标（左上角为 0,0），
    # 不能用本次 OCR 文本的 min_left/max_right 当作“聊天区域宽度”，否则当
    # 只出现右侧消息/消息很长跨过中线时会把中心线拉歪，导致误判归属。
    try:
        img_w = None
        for ln in chat_lines:
            w = (ln or {}).get("img_w")
            if isinstance(w, (int, float)) and w:
                img_w = int(w)
                break
        if img_w is None:
            # 兜底：退化为“文本框”最大 right（不理想，但比 min/max 同时受影响更稳）
            img_w = max(int((ln or {}).get("right", 0)) for ln in chat_lines)
        img_w = max(1, int(img_w))
    except Exception:
        return other_messages, my_messages, message_sequence
    chat_left = 0
    chat_right = img_w
    chat_width = max(1, chat_right - chat_left)
    chat_center_x = (chat_left + chat_right) / 2.0

    def _is_time_or_system_line(text: str) -> bool:
        s = (text or "").strip()
        if not s:
            return True
        # 纯数字很常见于真实聊天内容（如验证码/金额/“5201314”），不应一概当作系统时间行过滤。
        # 仅将极短纯数字（多为噪声/角标残留）视为系统/噪声。
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
        for ch in s:
            code = ord(ch)
            if 0x4E00 <= code <= 0x9FFF:
                return False
            if code > 127:
                return False
        return len(s) <= 2

    # 预过滤行：去掉时间/空/明显噪声（保留中文标点，如“。”）
    rows = []
    for ln in chat_lines or []:
        text = str((ln or {}).get("text", "")).strip()
        if _is_time_or_system_line(text):
            continue
        if _is_ascii_noise_short(text):
            # 仅 ASCII 的超短 token 大概率是噪声（边框、分隔符等）
            continue
        left = int((ln or {}).get("left", 0))
        right = int((ln or {}).get("right", 0))
        top = int((ln or {}).get("top", 0))
        bottom = int((ln or {}).get("bottom", top))
        rows.append({"text": text, "left": left, "right": right, "top": top, "bottom": bottom})

    if not rows:
        return other_messages, my_messages, message_sequence

    rows.sort(key=lambda x: (x["top"], x["left"]))

    # 合并为“气泡块”
    blocks = []
    for r in rows:
        txt = r["text"]
        left, right, top, bottom = r["left"], r["right"], r["top"], r["bottom"]
        width = max(1, right - left)
        if blocks:
            b = blocks[-1]
            b_width = max(1, b["right"] - b["left"])
            b_height = max(1, b["bottom"] - b["top"])
            v_gap = top - b["bottom"]
            overlap = max(0, min(right, b["right"]) - max(left, b["left"]))
            overlap_ratio = overlap / max(1, min(width, b_width))
            close_left = abs(left - b["left"]) <= 20
            close_right = abs(right - b["right"]) <= 35
            same_bubble = v_gap <= max(18, int(b_height * 0.9)) and (overlap_ratio >= 0.22 or close_left or close_right)
            if same_bubble:
                b["texts"].append(txt)
                b["left"] = min(b["left"], left)
                b["right"] = max(b["right"], right)
                b["top"] = min(b["top"], top)
                b["bottom"] = max(b["bottom"], bottom)
                continue
        blocks.append({"texts": [txt], "left": left, "right": right, "top": top, "bottom": bottom})

    # 块级归属（中心点左右半区）
    # 更稳判据：优先看“更贴近哪侧边界”（右边距更小 => 我方；左边距更小 => 对方）。
    # 解释：右侧消息气泡可能很宽，文本框中心会落到中线左侧，但其 right 通常贴近右边界。
    # 重要：最后一条消息应是“最靠下”的那条（bottom 最大），而不是 OCR 行的自然遍历顺序
    blocks.sort(key=lambda x: (int(x.get("bottom", 0)), int(x.get("top", 0)), int(x.get("left", 0))))

    margin_bias_px = max(12, int(chat_width * 0.02))  # 防抖偏置
    for b in blocks:
        text = "\n".join([t for t in b["texts"] if str(t).strip()]).strip()
        if not text:
            continue
        center_x = (b["left"] + b["right"]) / 2.0
        rel_center = (center_x - chat_left) / chat_width
        left_margin = max(0.0, float(b["left"] - chat_left))
        right_margin = max(0.0, float(chat_right - b["right"]))

        if right_margin + margin_bias_px < left_margin:
            side = "me"
            method = "margin"
        elif left_margin + margin_bias_px < right_margin:
            side = "other"
            method = "margin"
        else:
            side = "other" if rel_center < 0.5 else "me"
            method = "center"
        if side == "other":
            other_messages.append(text)
            message_sequence.append(("other", text))
        else:
            my_messages.append(text)
            message_sequence.append(("me", text))

        # 更新诊断信息（只保留最后一个有效块）
        try:
            _LAST_CHAT_PARSE_DEBUG.clear()
            _LAST_CHAT_PARSE_DEBUG.update(
                {
                    "chat_w": int(chat_right),
                    "chat_center_x": float(chat_center_x),
                    "block_bbox": [int(b["left"]), int(b["top"]), int(b["right"]), int(b["bottom"])],
                    "block_center_x": float(center_x),
                    "rel_center": float(rel_center),
                    "left_margin": float(left_margin),
                    "right_margin": float(right_margin),
                    "margin_bias_px": int(margin_bias_px),
                    "method": str(method),
                    "side": str(side),
                    "text_preview": str(text)[:60],
                }
            )
        except Exception:
            pass

    return other_messages, my_messages, message_sequence


"""返回区域坐标"""
# 总区域



def ocr_all_area(box, image=None):
    """OCR识别整个聊天软件区域"""
    if box:
        if image is None:
            screenshot = take_screenshot(region=box)
        else:
            # 从传入的图片中裁剪出box指定的区域
            screenshot = crop_image(image, box)
        if screenshot:
            # OpenOCR: 直接 OCR 后拼接
            items = _openocr_run(screenshot)
            lines = _openocr_items_to_lines(items, score_threshold=0.45)
            text = "\n".join([str(ln.get("text", "")).strip() for ln in lines if str(ln.get("text", "")).strip()])
            return text.strip()
    return ""


def ocr_chat_window(box, image=None):
    """OCR识别聊天窗口"""
    if box:
        if image is None:
            screenshot = take_screenshot(region=box)
        else:
            # 从传入的图片中裁剪出box指定的区域
            screenshot = crop_image(image, box)
        
        if screenshot:
            def _is_time_like(text: str) -> bool:
                s = (text or "").strip()
                if not s:
                    return True
                if ":" in s and len(s) <= 8:
                    parts = s.split(":")
                    if len(parts) == 2 and all(p.isdigit() for p in parts):
                        try:
                            hh = int(parts[0])
                            mm = int(parts[1])
                            return 0 <= hh <= 23 and 0 <= mm <= 59
                        except Exception:
                            pass
                keep = [ch for ch in s if ch not in " \t\r\n"]
                return bool(keep) and all(ch.isdigit() or ch in ":.-/" for ch in keep)

            def _is_ascii_noise_short(text: str) -> bool:
                s = "".join(str(text or "").split())
                if not s:
                    return True
                for ch in s:
                    code = ord(ch)
                    if 0x4E00 <= code <= 0x9FFF:
                        return False
                    if code > 127:
                        return False
                return len(s) <= 3

            def _text_stats(text: str):
                s = str(text or "")
                cjk = sum(1 for ch in s if 0x4E00 <= ord(ch) <= 0x9FFF)
                alpha = sum(1 for ch in s if ("a" <= ch.lower() <= "z"))
                return cjk, alpha

            def _meaningful_score(lines):
                score = 0
                for ln in lines or []:
                    t = str((ln or {}).get("text", "")).strip()
                    if not t:
                        continue
                    if _is_time_like(t):
                        continue
                    if _is_ascii_noise_short(t):
                        continue
                    score += 1
                return score

            def _candidate_summary(lines):
                valid = []
                for ln in lines or []:
                    t = str((ln or {}).get("text", "")).strip()
                    if not t or _is_time_like(t):
                        continue
                    y_mid = (int((ln or {}).get("top", 0)) + int((ln or {}).get("bottom", 0))) / 2.0
                    cjk, alpha = _text_stats(t)
                    valid.append(
                        {
                            "text": t[:40],
                            "y_mid": y_mid,
                            "cjk": cjk,
                            "alpha": alpha,
                        }
                    )
                valid.sort(key=lambda x: x["y_mid"], reverse=True)
                return valid[:5]

            # OpenOCR：直接取结果并转为行
            items = _openocr_run(screenshot)
            lines = _openocr_items_to_lines(items, score_threshold=0.45)
            selected_source = "openocr"
            coord_scale = 1.0
            for ln in lines or []:
                ln["source"] = selected_source
                ln["coord_scale"] = coord_scale
                # 关键：记录裁剪图的真实宽高，用于“最后一条消息归属”中心线计算
                try:
                    ln["img_w"] = int(getattr(screenshot, "width", 0) or screenshot.size[0])
                    ln["img_h"] = int(getattr(screenshot, "height", 0) or screenshot.size[1])
                except Exception:
                    ln["img_w"] = None
                    ln["img_h"] = None

            # 额外诊断：定位“。”被判到更上方的问题
            def _pick_dot_like(ls):
                res = []
                for ln in ls or []:
                    t = str((ln or {}).get("text", "")).strip()
                    if t in {"。", ".", "．", "·", "•"}:
                        top = int((ln or {}).get("top", 0))
                        bottom = int((ln or {}).get("bottom", top))
                        res.append(
                            {
                                "text": t,
                                "top": top,
                                "bottom": bottom,
                                "y_mid": (top + bottom) / 2.0,
                                "left": int((ln or {}).get("left", 0)),
                                "right": int((ln or {}).get("right", 0)),
                            }
                        )
                res.sort(key=lambda x: x["y_mid"], reverse=True)
                return res[:10]

            # region agent log
            _dbg(
                "H11",
                "src/core/ocr.py:ocr_chat_window",
                "chat ocr openocr",
                {
                    "box": list(box) if box else None,
                    "selected_source": selected_source,
                    "items_count": len(items or []),
                    "lines_count": len(lines or []),
                    "lines_top5": [x.get("text", "") for x in (lines or [])[:5]],
                },
            )
            # endregion

            return lines
    return []

# 识别输入框区域

def ocr_input_area(box, image=None):
    """OCR识别输入框区域"""
    if box:
        if image is None:
            screenshot = take_screenshot(region=box)
        else:
            # 从传入的图片中裁剪出box指定的区域
            screenshot = crop_image(image, box)
        if screenshot:
            items = _openocr_run(screenshot)
            lines = _openocr_items_to_lines(items, score_threshold=0.45)
            text = "\n".join([str(ln.get("text", "")).strip() for ln in lines if str(ln.get("text", "")).strip()])
            return text.strip()
    return ""

# 识别用户名区域


def ocr_user_area(box, image=None):
    """OCR识别用户名区域"""
    if box:
        if image is None:
            screenshot = take_screenshot(region=box)
        else:
            # 从传入的图片中裁剪出box指定的区域
            screenshot = crop_image(image, box)
        if screenshot:
            # 用户名区域只取左半部分：右侧常有按钮/图标/搜索框，容易干扰 OCR
            try:
                w, h = screenshot.size
                if isinstance(w, int) and isinstance(h, int) and w > 10 and h > 5:
                    screenshot = screenshot.crop((0, 0, int(w * 0.5), h))
            except Exception:
                pass

            def _extract_from_items(_items):
                _lines = _openocr_items_to_lines(_items, score_threshold=0.25)
                _selected = " ".join(
                    [str(ln.get("text", "")).strip() for ln in _lines if str(ln.get("text", "")).strip()]
                ).strip()
                if not _selected and _items:
                    direct = " ".join([str((it or {}).get("text", "")).strip() for it in (_items or [])]).strip()
                    if direct:
                        _selected = direct
                return _selected, _lines

            # 第一次：直接跑
            items = _openocr_run(screenshot)
            selected, lines = _extract_from_items(items)

            # 第二次兜底：对“极短/极小昵称”（如 "。" / "°"）做更强预处理后再跑
            items2 = []
            lines2 = []
            selected2 = ""
            if not selected:
                try:
                    pre = _preprocess_for_ocr(screenshot, upscale=3)
                except Exception:
                    pre = None
                if pre is not None:
                    items2 = _openocr_run(pre)
                    selected2, lines2 = _extract_from_items(items2)
                    if selected2:
                        selected = selected2
                        items = items2
                        lines = lines2
            # region agent log
            _dbg(
                "H9",
                "src/core/ocr.py:ocr_user_area",
                "user ocr openocr",
                {
                    "box": list(box) if box else None,
                    "items_count": len(items or []),
                    "items_head": [
                        {
                            "text": str((items[0] or {}).get("text", ""))[:40] if items else "",
                            "score": float((items[0] or {}).get("score", 0.0) or 0.0) if items else 0.0,
                            "points_len": len((items[0] or {}).get("points") or []) if items else 0,
                        }
                    ]
                    if items
                    else [],
                    "lines_count": len(lines or []),
                    "fallback2": {
                        "used": bool(selected2),
                        "items_count": len(items2 or []),
                        "lines_count": len(lines2 or []),
                        "selected_preview": str(selected2)[:40],
                    },
                    "selected_preview": str(selected)[:40],
                    "selected_codepoints": _to_codepoints(selected),
                },
            )
            # endregion
            # 单字符昵称纠错：OpenOCR 常把“。”误读为 0 / 〇 / O
            try:
                s = str(selected or "").strip()
                if len(s) == 1 and s in {"0", "〇", "O", "o", "Ｏ"}:
                    selected = "。"
            except Exception:
                pass
            return selected
    return ""

# 识别好友列表区域

def ocr_friend_list_area(box, image=None):
    """OCR识别好友列表区域"""
    if box:
        if image is None:
            screenshot = take_screenshot(region=box)
        else:
            # 从传入的图片中裁剪出box指定的区域
            screenshot = crop_image(image, box)
        if screenshot:
            items = _openocr_run(screenshot)
            lines = _openocr_items_to_lines(items, score_threshold=0.45)
            text = "\n".join([str(ln.get("text", "")).strip() for ln in lines if str(ln.get("text", "")).strip()])
            return text.strip()
    return ""