from PIL import Image
import time
from src.core.logger import core_logger


def take_screenshot(region=None):
    """截取屏幕
    :param region: 区域坐标 (x1, y1, x2, y2)，None表示截取整个屏幕
    :return: 截图对象
    """
    try:
        import pyautogui
        if region:
            x1, y1, x2, y2 = region
            x1 = int(x1)
            y1 = int(y1)
            x2 = int(x2)
            y2 = int(y2)
            w = max(1, x2 - x1)
            h = max(1, y2 - y1)
            screenshot = pyautogui.screenshot(region=(x1, y1, w, h))
        else:
            screenshot = pyautogui.screenshot()
        core_logger.debug(f"截图成功，区域: {region}")
        return screenshot
    except Exception as e:
        core_logger.error(f"截图失败: {e}")
        return None


def crop_image(image, box):
    """裁剪图片
    :param image: 原始图片
    :param box: 裁剪区域 (x1, y1, x2, y2)
    :return: 裁剪后的图片
    """
    try:
        if image and box:
            x1, y1, x2, y2 = box
            width = x2 - x1
            height = y2 - y1
            cropped = image.crop((x1, y1, x2, y2))
            core_logger.debug(f"裁剪图片成功，区域: {box}")
            return cropped
        return None
    except Exception as e:
        core_logger.error(f"裁剪图片失败: {e}")
        return None


def clip_box_to_parent(box, parent_box):
    """
    将 box 裁剪到 parent_box 范围内（不做“容错判断”，只做裁剪）。
    若裁剪后不再是有效矩形，返回 None。
    """
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
    """检查坐标是否有效
    :param box: 要检查的坐标 (x1, y1, x2, y2)
    :param parent_box: 父容器坐标，None表示不检查边界
    :param tolerance_px: 允许超出父容器的像素容差（默认 3）
    :return: (是否有效, 错误信息)
    """
    if not box:
        return False, "坐标为空"
    
    x1, y1, x2, y2 = box
    if x1 < 0 or y1 < 0 or x2 <= x1 or y2 <= y1:
        return False, "坐标值无效"
    
    if parent_box:
        parent_x1, parent_y1, parent_x2, parent_y2 = parent_box
        tol = int(tolerance_px or 0)
        if x1 < parent_x1 - tol or y1 < parent_y1 - tol or x2 > parent_x2 + tol or y2 > parent_y2 + tol:
            return False, "坐标超出父容器范围"
    
    return True, "坐标有效"


def wait_with_timeout(seconds, condition=None):
    """等待指定时间，可选择等待条件
    :param seconds: 等待时间（秒）
    :param condition: 条件函数，返回True时停止等待
    :return: 是否在超时前满足条件
    """
    start_time = time.time()
    while time.time() - start_time < seconds:
        if condition and condition():
            return True
        time.sleep(0.1)
    return False


def format_time(timestamp=None):
    """格式化时间
    :param timestamp: 时间戳，None表示当前时间
    :return: 格式化后的时间字符串
    """
    if timestamp is None:
        timestamp = time.time()
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))
