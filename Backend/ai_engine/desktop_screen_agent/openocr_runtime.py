from __future__ import annotations

"""
OpenOCR 运行时封装（不依赖 ocr_reference_bundle）。

提供与旧 `src.core.ocr` 同形态的接口，供 `ocr_reference_worker.py` 调用：
- ocr_user_area
- ocr_chat_window（返回行级 dict 列表，含 text + bbox + img_w/img_h）
- ocr_input_area
- ocr_friend_list_area
- ocr_all_area
"""

from dataclasses import dataclass
from typing import Any
import tempfile
import os


_ENGINE = None


def _get_engine():
    global _ENGINE
    if _ENGINE is None:
        try:
            from openocr import OpenOCR  # type: ignore[import-untyped]
        except ImportError as e:  # pragma: no cover
            raise ImportError(
                "未安装 openocr-python。请在 Backend 环境中安装：openocr-python==0.1.5"
            ) from e
        # mobile 模式更轻量；精度要求更高可切 server（需要 torch）
        _ENGINE = OpenOCR(task="ocr", mode="mobile")
    return _ENGINE


@dataclass(frozen=True, slots=True)
class OcrItem:
    text: str
    score: float
    points: list[list[float]]  # 4 points [[x,y],...]


def _normalize_items(raw: Any) -> list[OcrItem]:
    """
    兼容 OpenOCR Python API 的多种返回形态，归一为 OcrItem 列表。
    只要能拿到 text + points 即可。
    """
    # OpenOCR 有时返回 (results, time_dict)
    if isinstance(raw, tuple) and raw:
        raw = raw[0]

    items: list[dict[str, Any]] = []

    def looks_like_item(d: Any) -> bool:
        return isinstance(d, dict) and any(k in d for k in ("text", "transcription", "rec_text", "label")) and any(
            k in d for k in ("points", "box", "poly", "polygon")
        )

    if isinstance(raw, list):
        for r in raw:
            if looks_like_item(r):
                items.append(r)
            elif isinstance(r, dict):
                cand = r.get("ocr_result") or r.get("result") or r.get("results") or r.get("data")
                if isinstance(cand, list):
                    for it in cand:
                        if isinstance(it, dict):
                            items.append(it)
    elif isinstance(raw, dict):
        if looks_like_item(raw):
            items = [raw]
        else:
            cand = raw.get("ocr_result") or raw.get("result") or raw.get("results") or raw.get("data")
            if isinstance(cand, list):
                items = [it for it in cand if isinstance(it, dict)]

    out: list[OcrItem] = []
    for it in items:
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
        score_raw = it.get("score", it.get("confidence", it.get("prob", 0.0)))
        try:
            score = float(score_raw)
        except Exception:
            score = 0.0
        points = it.get("points") or it.get("box") or it.get("poly") or it.get("polygon") or []
        pts: list[list[float]] = []
        if isinstance(points, (list, tuple)) and points:
            if len(points) == 8 and all(isinstance(v, (int, float)) for v in points):
                pts = [
                    [float(points[0]), float(points[1])],
                    [float(points[2]), float(points[3])],
                    [float(points[4]), float(points[5])],
                    [float(points[6]), float(points[7])],
                ]
            elif all(isinstance(p, (list, tuple)) and len(p) >= 2 for p in points):
                pts = [[float(p[0]), float(p[1])] for p in points[:4]]
        out.append(OcrItem(text=text, score=score, points=pts))
    return out


def _items_to_lines(items: list[OcrItem], *, score_threshold: float = 0.45, y_merge_px: int = 18) -> list[dict[str, Any]]:
    """
    将词/块级结果聚合成“行级”：
    输出 dict：{text,left,right,top,bottom,img_w,img_h}
    """
    boxes: list[dict[str, Any]] = []
    for it in items:
        if float(it.score or 0.0) < float(score_threshold):
            continue
        pts = it.points or []
        if not pts:
            continue
        xs = [p[0] for p in pts if isinstance(p, list) and len(p) >= 2]
        ys = [p[1] for p in pts if isinstance(p, list) and len(p) >= 2]
        if not xs or not ys:
            continue
        left, right = int(min(xs)), int(max(xs))
        top, bottom = int(min(ys)), int(max(ys))
        boxes.append({"text": it.text, "left": left, "right": right, "top": top, "bottom": bottom})
    if not boxes:
        return []
    boxes.sort(key=lambda x: (int(x["top"]), int(x["left"])))

    lines: list[dict[str, Any]] = []
    cur: dict[str, Any] | None = None
    for b in boxes:
        if cur is None:
            cur = {"texts": [b["text"]], "left": b["left"], "right": b["right"], "top": b["top"], "bottom": b["bottom"]}
            continue
        if abs(int(b["top"]) - int(cur["top"])) <= int(y_merge_px):
            cur["texts"].append(b["text"])
            cur["left"] = min(int(cur["left"]), int(b["left"]))
            cur["right"] = max(int(cur["right"]), int(b["right"]))
            cur["top"] = min(int(cur["top"]), int(b["top"]))
            cur["bottom"] = max(int(cur["bottom"]), int(b["bottom"]))
        else:
            text = " ".join([t for t in cur["texts"] if str(t).strip()]).strip()
            if text:
                lines.append({"text": text, "left": cur["left"], "right": cur["right"], "top": cur["top"], "bottom": cur["bottom"]})
            cur = {"texts": [b["text"]], "left": b["left"], "right": b["right"], "top": b["top"], "bottom": b["bottom"]}
    if cur is not None:
        text = " ".join([t for t in cur["texts"] if str(t).strip()]).strip()
        if text:
            lines.append({"text": text, "left": cur["left"], "right": cur["right"], "top": cur["top"], "bottom": cur["bottom"]})
    lines.sort(key=lambda x: (int(x.get("top", 0)), int(x.get("left", 0))))
    return lines


def _ocr_lines(img) -> list[dict[str, Any]]:
    engine = _get_engine()
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as f:
            tmp_path = f.name
        img.save(tmp_path)
        out = engine(image_path=tmp_path)  # OpenOCR 官方示例
        items = _normalize_items(out)
        return _items_to_lines(items)
    finally:
        if tmp_path:
            try:
                os.remove(tmp_path)
            except OSError:
                pass


def _crop(image, box: tuple[int, int, int, int]):
    x1, y1, x2, y2 = [int(v) for v in box]
    if x2 <= x1 or y2 <= y1:
        return None
    return image.crop((x1, y1, x2, y2))


def ocr_user_area(box: tuple[int, int, int, int], image) -> str:
    crop = _crop(image, box)
    if crop is None:
        return ""
    lines = _ocr_lines(crop)
    text = " ".join([str(ln.get("text", "")).strip() for ln in lines if str(ln.get("text", "")).strip()]).strip()
    return text


def ocr_input_area(box: tuple[int, int, int, int], image) -> str:
    crop = _crop(image, box)
    if crop is None:
        return ""
    lines = _ocr_lines(crop)
    text = " ".join([str(ln.get("text", "")).strip() for ln in lines if str(ln.get("text", "")).strip()]).strip()
    return text


def ocr_friend_list_area(box: tuple[int, int, int, int], image) -> str:
    crop = _crop(image, box)
    if crop is None:
        return ""
    lines = _ocr_lines(crop)
    text = "\n".join([str(ln.get("text", "")).strip() for ln in lines if str(ln.get("text", "")).strip()]).strip()
    return text


def ocr_all_area(box: tuple[int, int, int, int], image) -> str:
    crop = _crop(image, box)
    if crop is None:
        return ""
    lines = _ocr_lines(crop)
    text = "\n".join([str(ln.get("text", "")).strip() for ln in lines if str(ln.get("text", "")).strip()]).strip()
    return text


def ocr_chat_window(box: tuple[int, int, int, int], image) -> list[dict[str, Any]]:
    crop = _crop(image, box)
    if crop is None:
        return []
    lines = _ocr_lines(crop)
    try:
        w, h = crop.size
    except Exception:
        w, h = 0, 0
    for ln in lines:
        ln["img_w"] = int(w or 0)
        ln["img_h"] = int(h or 0)
        ln["source"] = "openocr_runtime"
    return lines

