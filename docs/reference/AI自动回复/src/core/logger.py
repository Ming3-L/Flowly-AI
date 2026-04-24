import logging
import os
import time
import sys
import re

# 确保日志目录存在
LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# 创建日志文件路径
log_file = os.path.join(LOG_DIR, f"ai_auto_reply_{time.strftime('%Y-%m-%d')}.log")

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# 降噪：第三方库（OpenOCR/OpenRec/Ultralytics 等）默认会刷屏 INFO
# 这里统一降到 WARNING，需要排障时再手动调回 INFO
for noisy_name in (
    "openrec",
    "openocr",
    "openocr_unified",
    "ultralytics",
):
    try:
        logging.getLogger(noisy_name).setLevel(logging.WARNING)
    except Exception:
        pass

# 进一步降噪：部分第三方库会直接向 stdout 打印（不走 logging），导致控制台刷屏。
# 这里仅过滤 openrec/openocr 的重复 INFO 行，不影响我们的业务日志。
_NOISY_STDOUT_PATTERNS = [
    re.compile(r"^\[\d{4}/\d{2}/\d{2} .*\]\s+openrec\s+INFO:"),
    re.compile(r"^\[\d{4}/\d{2}/\d{2} .*\]\s+openocr_unified\s+INFO:"),
]


class _StdoutNoiseFilter:
    def __init__(self, wrapped):
        self._wrapped = wrapped
        self._buf = ""

    def write(self, s):
        try:
            self._buf += s
            while "\n" in self._buf:
                line, self._buf = self._buf.split("\n", 1)
                if any(p.match(line.strip()) for p in _NOISY_STDOUT_PATTERNS):
                    continue
                self._wrapped.write(line + "\n")
        except Exception:
            # 失败时不阻断输出
            self._wrapped.write(s)

    def flush(self):
        try:
            if self._buf:
                # flush 末尾残留
                line = self._buf
                self._buf = ""
                if not any(p.match(line.strip()) for p in _NOISY_STDOUT_PATTERNS):
                    self._wrapped.write(line)
            self._wrapped.flush()
        except Exception:
            pass


try:
    sys.stdout = _StdoutNoiseFilter(sys.stdout)
except Exception:
    pass

# 创建不同模块的logger
def get_logger(name):
    """获取指定名称的logger"""
    return logging.getLogger(name)

# 示例：不同模块的logger
core_logger = get_logger("core")
ocr_logger = get_logger("ocr")
ai_logger = get_logger("ai")
sender_logger = get_logger("sender")
monitor_logger = get_logger("monitor")
gui_logger = get_logger("gui")
