"""
从参考项目 ``monitor.py`` 精简移植：区域检测 + 手动坐标回退。
不依赖 Django；供本机 ``python -m ai_engine.desktop_screen_agent`` 调用。
"""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

log = logging.getLogger(__name__)

SOFTWARE_CLASS_TO_TYPE = {
    "software_wechat": "wechat",
    "software_qq": "qq",
    "software_tim": "tim",
    "software_other": "other",
}
_SOFTWARE_CLASSES = set(SOFTWARE_CLASS_TO_TYPE.keys()) | {"chat_software"}

_LAST_NO_MODEL_LOG_AT = 0.0
_NO_MODEL_LOG_INTERVAL_S = 20.0

_yolo_model = None
_yolo_model_path_loaded: str | None = None


def _default_yolo_weights_path() -> str:
    """
    模块内默认权重位置（随项目迁移/部署）。
    注意：不要依赖进程 cwd，避免从不同入口启动时找错路径。
    """
    try:
        p = (Path(__file__).resolve().parent / "weights" / "best.pt")
        return str(p) if p.is_file() else ""
    except Exception:
        return ""


def _resolve_yolo_weights_path(weights_path: str) -> str:
    """
    兼容历史配置：若传入路径不存在，尝试回退到模块默认权重。
    """
    raw = (weights_path or "").strip()
    if not raw:
        return ""
    try:
        if os.path.isfile(raw):
            return raw
    except Exception:
        # 若 isfile 异常（极少见），直接回退逻辑
        pass

    fallback = _default_yolo_weights_path()
    if fallback and fallback != raw:
        return fallback
    return raw


def _coerce_box4(value: Any) -> tuple[int, int, int, int] | None:
    if value is None:
        return None
    if isinstance(value, (list, tuple)) and len(value) == 4:
        try:
            return tuple(int(v) for v in value)  # type: ignore[return-value]
        except Exception:
            return None
    return None


def cfg_from_profile_dict(d: dict[str, Any]) -> SimpleNamespace:
    """将 API 返回的 screen profile JSON 转为与参考 ``cfg`` 等价的属性对象。"""
    return SimpleNamespace(
        friend_list_box=_coerce_box4(d.get("friend_list_box")),
        user_name_box=_coerce_box4(d.get("user_name_box")),
        chat_window_box=_coerce_box4(d.get("chat_window_box")),
        input_box_pos=_coerce_box4(d.get("input_box_pos")),
    )


def clip_box_to_parent(box, parent_box):
    if not box or not parent_box:
        return box
    try:
        x1, y1, x2, y2 = [int(v) for v in box]
        px1, py1, px2, py2 = [int(v) for v in parent_box]
    except Exception:
        return None
    nx1 = max(px1, x1)
    ny1 = max(py1, y1)
    nx2 = min(px2, x2)
    ny2 = min(py2, y2)
    if nx2 <= nx1 or ny2 <= ny1:
        return None
    return (nx1, ny1, nx2, ny2)


def is_coordinate_valid(box, parent_box=None, tolerance_px: int = 3):
    if not box:
        return False, "坐标为空"
    try:
        x1, y1, x2, y2 = box
        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
    except Exception:
        return False, "坐标值无效"
    if x1 < 0 or y1 < 0 or x2 <= x1 or y2 <= y1:
        return False, "坐标值无效"
    if parent_box:
        parent_x1, parent_y1, parent_x2, parent_y2 = parent_box
        tol = int(tolerance_px or 0)
        if x1 < parent_x1 - tol or y1 < parent_y1 - tol or x2 > parent_x2 + tol or y2 > parent_y2 + tol:
            return False, "坐标超出父容器范围"
    return True, "坐标有效"


def _get_yolo_model(weights_path: str):
    global _yolo_model, _yolo_model_path_loaded
    path = _resolve_yolo_weights_path(weights_path)
    if not path:
        return None
    if not os.path.isfile(path):
        log.info("YOLO 权重文件不存在: %s", (weights_path or "").strip() or path)
        return None
    if _yolo_model is not None and _yolo_model_path_loaded == path:
        return _yolo_model
    try:
        try:
            from ultralytics import YOLO  # type: ignore[import-untyped]
        except ModuleNotFoundError:
            # 这里用 info 级别：很多开发环境日志默认只看 INFO，避免“静默回退”
            log.info("未安装 ultralytics，无法加载 YOLO；将回退到手动坐标。可 pip install ultralytics")
            return None

        _yolo_model = YOLO(path)
        _yolo_model_path_loaded = path
        log.info("已加载 YOLO 权重: %s", path)
    except Exception as e:
        log.info("加载 YOLO 失败，将回退到手动坐标: %s", e)
        _yolo_model = None
        _yolo_model_path_loaded = None
    return _yolo_model


def _model_can_detect_required_classes(model) -> bool:
    try:
        names = getattr(model, "names", {}) or {}
        name_set = set(names.values()) if isinstance(names, dict) else set(names)
        required = {"friend_list", "user_object", "chat_area", "input_box"}
        return required.issubset(name_set)
    except Exception:
        return False


def identify_message(img, model) -> dict[str, Any]:
    result_dict: dict[str, Any] = {
        "chat_software": None,
        "friend_list": None,
        "user_object": None,
        "chat_area": None,
        "input_box": None,
        "software_type": None,
    }
    best_conf = {k: -1.0 for k in ("chat_software", "friend_list", "user_object", "chat_area", "input_box")}
    software_best = {"name": None, "conf": -1.0}
    results = model(img)
    for result in results:
        boxes = result.boxes
        for box in boxes:
            coordinates = x1, y1, x2, y2 = box.xyxy[0]
            coordinates = int(x1), int(y1), int(x2), int(y2)
            class_id = box.cls[0]
            class_name = model.names[int(class_id)]
            conf = float(box.conf[0])
            if conf > 0.5:
                if class_name in _SOFTWARE_CLASSES:
                    if conf > best_conf.get("chat_software", -1.0):
                        best_conf["chat_software"] = conf
                        result_dict["chat_software"] = coordinates
                    if class_name in SOFTWARE_CLASS_TO_TYPE and conf > software_best["conf"]:
                        software_best = {"name": class_name, "conf": conf}
                else:
                    if class_name in best_conf:
                        if conf > best_conf.get(class_name, -1.0):
                            best_conf[class_name] = conf
                            result_dict[class_name] = coordinates
                    else:
                        result_dict[class_name] = coordinates
                    log.debug("识别到 %s: %s 置信度 %.2f", class_name, coordinates, conf)
    if software_best["name"]:
        result_dict["software_type"] = SOFTWARE_CLASS_TO_TYPE[software_best["name"]]
    return result_dict


def is_right(box_user_name, box_chat, box_input, box_friend, box_all, tolerance_px: int):
    if any(box is None for box in [box_user_name, box_chat, box_input, box_friend, box_all]):
        return False, "错误：存在未识别的区域"
    all_boxes = [
        (box_user_name, "用户名称区域"),
        (box_chat, "聊天区域"),
        (box_input, "输入框区域"),
        (box_friend, "好友列表区域"),
    ]
    for box, name in all_boxes:
        is_valid, message = is_coordinate_valid(box, box_all, tolerance_px=tolerance_px)
        if not is_valid:
            return False, f"错误：{name} {message}"
    return True, "所有坐标区域均合规"


def _fallback_from_cfg(cfg, tolerance_px: int):
    import pyautogui  # type: ignore[import-untyped]

    required_keys = ["chat_software", "friend_list", "user_object", "chat_area", "input_box"]
    sw, sh = pyautogui.size()
    fallback = {
        "chat_software": (0, 0, sw, sh),
        "friend_list": tuple(cfg.friend_list_box) if cfg.friend_list_box else None,
        "user_object": tuple(cfg.user_name_box) if cfg.user_name_box else None,
        "chat_area": tuple(cfg.chat_window_box) if cfg.chat_window_box else None,
        "input_box": tuple(cfg.input_box_pos) if cfg.input_box_pos else None,
        "software_type": None,
    }
    if all(fallback.get(k) for k in required_keys):
        ok, msg = is_right(
            fallback["user_object"],
            fallback["chat_area"],
            fallback["input_box"],
            fallback["friend_list"],
            fallback["chat_software"],
            tolerance_px,
        )
        if ok:
            return fallback, "使用手动/默认配置坐标"
        return None, f"回退坐标不合规：{msg}"
    return None, "手动/默认配置坐标不完整"


def get_chat_areas(
    cfg: SimpleNamespace,
    *,
    use_yolo: bool,
    yolo_weights_path: str,
    tolerance_px: int = 20,
) -> tuple[dict[str, Any] | None, str]:
    """
    与参考 ``get_chat_areas`` 等价：返回 (areas_dict, message)。
    areas 的键为 chat_software / friend_list / user_object / chat_area / input_box / software_type。
    """
    global _LAST_NO_MODEL_LOG_AT
    required_keys = ["chat_software", "friend_list", "user_object", "chat_area", "input_box"]
    if not use_yolo:
        try:
            return _fallback_from_cfg(cfg, tolerance_px)
        except Exception as e:
            return None, f"回退失败：{e}"

    model = _get_yolo_model(yolo_weights_path)
    if model is None or not _model_can_detect_required_classes(model):
        now = time.time()
        if now - _LAST_NO_MODEL_LOG_AT >= _NO_MODEL_LOG_INTERVAL_S:
            log.info("未加载到可用的区域检测模型，直接使用手动配置坐标")
            _LAST_NO_MODEL_LOG_AT = now
        try:
            return _fallback_from_cfg(cfg, tolerance_px)
        except Exception as e:
            return None, f"回退失败：{e}"

    import pyautogui  # type: ignore[import-untyped]

    img = pyautogui.screenshot()
    areas = identify_message(img, model)
    if not areas.get("chat_software"):
        try:
            sw, sh = getattr(img, "size", (None, None))
            if isinstance(sw, int) and isinstance(sh, int) and sw > 0 and sh > 0:
                areas["chat_software"] = (0, 0, int(sw), int(sh))
        except Exception:
            pass

    try:
        box_all = areas.get("chat_software")
        if isinstance(box_all, (list, tuple)) and len(box_all) == 4:
            for k in ("friend_list", "user_object", "chat_area", "input_box"):
                b = areas.get(k)
                if isinstance(b, (list, tuple)) and len(b) == 4:
                    ok, _ = is_coordinate_valid(b, box_all, tolerance_px=tolerance_px)
                    if ok:
                        cb = clip_box_to_parent(b, box_all)
                        if cb:
                            areas[k] = cb
    except Exception:
        pass

    missing = [k for k in required_keys if not areas.get(k)]
    if not missing:
        ok, msg = is_right(
            areas["user_object"],
            areas["chat_area"],
            areas["input_box"],
            areas["friend_list"],
            areas["chat_software"],
            tolerance_px,
        )
        if ok:
            # 高频循环下不刷屏：成功识别留给上层按“变化”节流打印
            log.debug("成功识别所有区域")
            return areas, "成功识别所有区域"
        log.warning("坐标合规性检查失败: %s", msg)
        return None, msg

    log.info("模型未识别到所有区域，回退到手动配置坐标")
    try:
        fb, m2 = _fallback_from_cfg(cfg, tolerance_px)
        if fb is not None:
            return fb, m2
    except Exception as e:
        return None, f"回退失败：{e}"
    return None, "未识别到所有区域"


def get_chat_areas_from_profile(
    profile: dict[str, Any],
    *,
    yolo_weights_path: str | None = None,
    tolerance_px: int | None = None,
) -> tuple[dict[str, Any] | None, str]:
    """``profile`` 为 ``GET /auto-reply/screen-profile`` 的 JSON。"""
    tol = int(tolerance_px if tolerance_px is not None else os.getenv("FLOWLY_SCREEN_YOLO_TOLERANCE_PX", "20"))
    dj_weights = ""
    try:
        from django.conf import settings

        dj_weights = str(getattr(settings, "FLOWLY_SCREEN_YOLO_WEIGHTS", "") or "").strip()
    except Exception:
        pass
    weights = (yolo_weights_path or os.getenv("FLOWLY_SCREEN_YOLO_WEIGHTS", "") or dj_weights or "").strip()
    cfg = cfg_from_profile_dict(profile)
    use_yolo = bool(profile.get("use_yolo", True))
    return get_chat_areas(cfg, use_yolo=use_yolo, yolo_weights_path=weights, tolerance_px=tol)


def areas_to_jsonable(areas: dict[str, Any] | None) -> dict[str, Any]:
    if not areas:
        return {}
    out: dict[str, Any] = {}
    for k, v in areas.items():
        if isinstance(v, (list, tuple)) and len(v) == 4:
            out[k] = [int(x) for x in v]
        else:
            out[k] = v
    return out
