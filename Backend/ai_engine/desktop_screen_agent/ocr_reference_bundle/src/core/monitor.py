import pyautogui
from ultralytics import YOLO
from src.config.constants import YOLO_MODEL_PATH, YOLO_BOX_TOLERANCE_PX
from src.core.logger import monitor_logger
from src.core.utils import clip_box_to_parent, is_coordinate_valid
from src.config import config_manager as cfg
import json as _json
import time as _time

# 加载 YOLO 模型（路径由 constants 解析，避免依赖进程当前工作目录）
model = YOLO(YOLO_MODEL_PATH)

SOFTWARE_CLASS_TO_TYPE = {
    "software_wechat": "wechat",
    "software_qq": "qq",
    "software_tim": "tim",
    "software_other": "other",
}

_SOFTWARE_CLASSES = set(SOFTWARE_CLASS_TO_TYPE.keys()) | {"chat_software"}

# 日志节流：避免监控线程每秒刷屏同一句话
_LAST_NO_MODEL_LOG_AT = 0.0
_NO_MODEL_LOG_INTERVAL_S = 20.0

# region agent debug log
def _dbg(hypothesisId: str, location: str, message: str, data: dict):
    try:
        payload = {
            "sessionId": "852d3a",
            "runId": "pre-fix",
            "hypothesisId": hypothesisId,
            "location": location,
            "message": message,
            "data": data,
            "timestamp": int(_time.time() * 1000),
        }
        with open("debug-852d3a.log", "a", encoding="utf-8") as f:
            f.write(_json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        pass
# endregion

def _model_can_detect_required_classes() -> bool:
    """
    判断当前加载的权重是否“看起来”是我们训练的区域检测模型。
    若不具备必需类别（至少 friend_list/user_object/chat_area/input_box 这些），则视为无模型可用。
    """
    try:
        names = getattr(model, "names", {}) or {}
        name_set = set(names.values()) if isinstance(names, dict) else set(names)
        required = {"friend_list", "user_object", "chat_area", "input_box"}
        ok = required.issubset(name_set)
        _dbg(
            "H1",
            "src/core/monitor.py:_model_can_detect_required_classes",
            "model class check",
            {"ok": ok, "required": sorted(list(required)), "available_sample": sorted(list(name_set))[:30]},
        )
        return bool(ok)
    except Exception as e:
        _dbg(
            "H1",
            "src/core/monitor.py:_model_can_detect_required_classes",
            "model class check error",
            {"error": str(e)},
        )
        return False


def identify_message(img):
    """识别聊天软件及其各区域"""
    result_dict = {
        "chat_software": None,
        "friend_list": None,
        "user_object": None,
        "chat_area": None,
        "input_box": None,
        # 额外信息：识别到的软件类型（wechat/qq/tim/other），若模型不支持则为 None
        "software_type": None,
    }
    # 同一类别可能会检测出多个框：这里用最高置信度的那个，避免偶发异常框覆盖正确结果
    best_conf = {k: -1.0 for k in ("chat_software", "friend_list", "user_object", "chat_area", "input_box")}
    software_best = {"name": None, "conf": -1.0}
    # 记录一次模型元信息（不含敏感信息）
    _dbg(
        "H1",
        "src/core/monitor.py:identify_message",
        "model meta",
        {
            "model_path": YOLO_MODEL_PATH,
            "names_count": len(getattr(model, "names", {}) or {}),
        },
    )
    
    # 开始检测
    results = model(img)
    
    # 遍历结果和获取信息
    for result in results:
        # 获取检测框
        boxes = result.boxes
        for box in boxes:
            # 提取坐标 x1，y1左上角
            coordinates = x1, y1, x2, y2 = box.xyxy[0]
            coordinates = int(x1), int(y1), int(x2), int(y2)
            
            # 提取目标名称
            class_id = box.cls[0]  # 类型编号
            class_name = model.names[int(class_id)]  # 类型名字
            
            # 提取置信度
            conf = float(box.conf[0])
            
            # 只保留置信度大于0.5的结果
            if conf > 0.5:
                _dbg(
                    "H2",
                    "src/core/monitor.py:identify_message",
                    "detection",
                    {"class_name": str(class_name), "conf": float(conf)},
                )
                # 兼容两种训练方式：
                # 1) 旧模型：只有 chat_software（无法区分微信/QQ）
                # 2) 新模型：software_wechat / software_qq / software_tim / software_other
                if class_name in _SOFTWARE_CLASSES:
                    # chat_software / software_xxx 都写到 chat_software 框（取最高置信度）
                    if conf > best_conf.get("chat_software", -1.0):
                        best_conf["chat_software"] = conf
                        result_dict["chat_software"] = coordinates
                    if class_name in SOFTWARE_CLASS_TO_TYPE and conf > software_best["conf"]:
                        software_best = {"name": class_name, "conf": conf}
                else:
                    # friend_list/user_object/chat_area/input_box 取最高置信度
                    if class_name in best_conf:
                        if conf > best_conf.get(class_name, -1.0):
                            best_conf[class_name] = conf
                            result_dict[class_name] = coordinates
                    else:
                        result_dict[class_name] = coordinates
                monitor_logger.debug(f"识别到{class_name}: {coordinates}, 置信度: {conf:.2f}")

    if software_best["name"]:
        result_dict["software_type"] = SOFTWARE_CLASS_TO_TYPE[software_best["name"]]
    return result_dict

# 检验 1.坐标是否合规


def is_right(box_user_name, box_chat, box_input, box_friend, box_all):
    """
    检查所有坐标区域是否完全在 box_all 范围内
    坐标格式：(x1, y1, x2, y2)
    返回：(是否合规, 错误/成功信息)
    """
    
    # 先检查参数是否为None
    if any(box is None for box in [box_user_name, box_chat, box_input, box_friend, box_all]):
        return False, "错误：存在未识别的区域"

    # 先把所有需要检查的区域放进列表，方便统一判断
    all_boxes = [
        (box_user_name, "用户名称区域"),
        (box_chat, "聊天区域"),
        (box_input, "输入框区域"),
        (box_friend, "好友列表区域")
    ]

    # 检查每个区域
    for box, name in all_boxes:
        is_valid, message = is_coordinate_valid(
            box,
            box_all,
            tolerance_px=YOLO_BOX_TOLERANCE_PX,
        )
        if not is_valid:
            return False, f"错误：{name} {message}"

    # 所有区域都合规
    return True, "所有坐标区域均合规"

def get_chat_areas():
    """获取聊天软件的所有区域"""
    required_keys = ["chat_software", "friend_list", "user_object", "chat_area", "input_box"]

    # 若当前权重不是区域检测模型（例如还没训练，只能识别 laptop/person 等），直接走手动/默认配置
    if not _model_can_detect_required_classes():
        global _LAST_NO_MODEL_LOG_AT
        now = _time.time()
        if now - _LAST_NO_MODEL_LOG_AT >= _NO_MODEL_LOG_INTERVAL_S:
            monitor_logger.info("未加载到可用的区域检测模型，直接使用手动/默认配置坐标")
            _LAST_NO_MODEL_LOG_AT = now
        try:
            sw, sh = pyautogui.size()
            fallback = {
                "chat_software": (0, 0, sw, sh),
                "friend_list": tuple(cfg.friend_list_box) if cfg.friend_list_box else None,
                "user_object": tuple(cfg.user_name_box) if cfg.user_name_box else None,
                "chat_area": tuple(cfg.chat_window_box) if cfg.chat_window_box else None,
                "input_box": tuple(cfg.input_box_pos) if cfg.input_box_pos else None,
                "software_type": None,
            }
            _dbg(
                "H4",
                "src/core/monitor.py:get_chat_areas",
                "direct-fallback snapshot (no model)",
                {
                    "friend_list": list(fallback["friend_list"]) if fallback["friend_list"] else None,
                    "user_object": list(fallback["user_object"]) if fallback["user_object"] else None,
                    "chat_area": list(fallback["chat_area"]) if fallback["chat_area"] else None,
                    "input_box": list(fallback["input_box"]) if fallback["input_box"] else None,
                },
            )
            if all(fallback.get(k) for k in required_keys):
                is_valid, message = is_right(
                    fallback["user_object"],
                    fallback["chat_area"],
                    fallback["input_box"],
                    fallback["friend_list"],
                    fallback["chat_software"],
                )
                _dbg(
                    "H5",
                    "src/core/monitor.py:get_chat_areas",
                    "direct-fallback validation (no model)",
                    {"is_valid": bool(is_valid), "message": str(message)},
                )
                if is_valid:
                    return fallback, "使用手动/默认配置坐标"
                return None, f"回退坐标不合规：{message}"
            return None, "手动/默认配置坐标不完整"
        except Exception as e:
            return None, f"回退失败：{e}"

    # 截取屏幕
    img = pyautogui.screenshot()

    # 使用模型识别区域
    areas = identify_message(img)
    # 父容器：按你的数据集定义，使用模型检测到的软件窗口框
    # （software_wechat/software_qq/software_tim/software_other 或旧模型 chat_software）
    # 若本轮未检测到父容器，才回退到整张截图范围，避免后续裁剪/校验崩溃。
    if not areas.get("chat_software"):
        try:
            sw, sh = getattr(img, "size", (None, None))
            if isinstance(sw, int) and isinstance(sh, int) and sw > 0 and sh > 0:
                areas["chat_software"] = (0, 0, int(sw), int(sh))
        except Exception:
            pass

    # 轻微越界是常见情况：这里先允许一定容差，并将各区域裁剪回 chat_software（父容器）范围内。
    try:
        box_all = areas.get("chat_software")
        if isinstance(box_all, (list, tuple)) and len(box_all) == 4:
            for k in ("friend_list", "user_object", "chat_area", "input_box"):
                b = areas.get(k)
                if isinstance(b, (list, tuple)) and len(b) == 4:
                    ok, _ = is_coordinate_valid(
                        b,
                        box_all,
                        tolerance_px=YOLO_BOX_TOLERANCE_PX,
                    )
                    if ok:
                        cb = clip_box_to_parent(b, box_all)
                        if cb:
                            areas[k] = cb
    except Exception:
        pass
    
    # 只要求关键框存在；software_type 允许为空
    missing = [k for k in required_keys if not areas.get(k)]
    _dbg(
        "H3",
        "src/core/monitor.py:get_chat_areas",
        "required keys check",
        {"missing": missing, "present": [k for k in required_keys if areas.get(k)]},
    )
    if not missing:
        # 检查坐标是否合规
        is_valid, message = is_right(
            areas["user_object"],
            areas["chat_area"],
            areas["input_box"],
            areas["friend_list"],
            areas["chat_software"]
        )
        
        if is_valid:
            monitor_logger.info("成功识别所有区域")
            return areas, "成功识别所有区域"
        else:
            monitor_logger.warning(f"坐标合规性检查失败: {message}")
            return None, message
    else:
        # 模型识别失败时，回退到配置/默认坐标
        monitor_logger.info("模型未识别到所有区域，回退到手动/默认配置坐标")
        try:
            sw, sh = pyautogui.size()
            _dbg(
                "H4",
                "src/core/monitor.py:get_chat_areas",
                "fallback cfg snapshot",
                {
                    "chat_window_box": list(cfg.chat_window_box) if cfg.chat_window_box else None,
                    "user_name_box": list(cfg.user_name_box) if cfg.user_name_box else None,
                    "friend_list_box": list(cfg.friend_list_box) if cfg.friend_list_box else None,
                    "input_box_pos": list(cfg.input_box_pos) if cfg.input_box_pos else None,
                    "screen": [sw, sh],
                },
            )
            fallback = {
                "chat_software": (0, 0, sw, sh),
                "friend_list": tuple(cfg.friend_list_box) if cfg.friend_list_box else None,
                "user_object": tuple(cfg.user_name_box) if cfg.user_name_box else None,
                "chat_area": tuple(cfg.chat_window_box) if cfg.chat_window_box else None,
                "input_box": tuple(cfg.input_box_pos) if cfg.input_box_pos else None,
                "software_type": None,
            }
            if all(fallback.get(k) for k in required_keys):
                is_valid, message = is_right(
                    fallback["user_object"],
                    fallback["chat_area"],
                    fallback["input_box"],
                    fallback["friend_list"],
                    fallback["chat_software"],
                )
                _dbg(
                    "H5",
                    "src/core/monitor.py:get_chat_areas",
                    "fallback validation",
                    {"is_valid": bool(is_valid), "message": str(message)},
                )
                if is_valid:
                    return fallback, "使用默认/手动配置坐标"
                return None, f"回退坐标不合规：{message}"
        except Exception as e:
            return None, f"回退失败：{e}"
        return None, "未识别到所有区域"

