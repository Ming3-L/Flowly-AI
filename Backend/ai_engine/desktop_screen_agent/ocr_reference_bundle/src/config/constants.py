import os

# 项目根目录（与 config.json 同级）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_FILE = os.path.join(PROJECT_ROOT, "config.json")
MONITOR_LIST_FILE = os.path.join(PROJECT_ROOT, "monitor_list.json")
# 可挂载到 AI 的本地资料目录（好友专属 / 共享文本等）
KNOWLEDGE_ROOT = os.path.join(PROJECT_ROOT, "knowledge")

# YOLO 权重：monitor 使用。Flowly 仅起 OCR 子进程时可能不放置 best.pt，故不强制抛错。
_default_yolo = os.path.join(PROJECT_ROOT, "best.pt")
if os.path.isfile(_default_yolo):
    YOLO_MODEL_PATH = _default_yolo
else:
    YOLO_MODEL_PATH = (os.environ.get("FLOWLY_REF_YOLO_WEIGHTS") or "").strip()

# YOLO 识别框容错：允许相对父容器轻微越界（像素）
YOLO_BOX_TOLERANCE_PX = 20

# 官方豆包 API：仅使用环境变量（本仓库副本已删除原参考项目中的硬编码密钥，请勿再写入密钥到文件）
API_KEY = (os.environ.get("DOUBAO_API_KEY") or os.environ.get("ARK_API_KEY") or "").strip()
ENDPOINT_ID = (os.environ.get("DOUBAO_ENDPOINT_ID") or os.environ.get("ARK_ENDPOINT_ID") or "").strip()
API_ENDPOINT = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
MODEL_NAME = "Doubao-1.5-pro-32k"

# OCR 引擎：已切换为 OpenOCR（不再需要本地 Tesseract 路径）

# 聊天软件配置
CHAT_SOFTWARE = {
    "wechat": "微信",
    "qq": "QQ",
    "tim": "TIM",
    "other": "其他"
}

# 聊天情景
ChatScene = {
    "daily_chat": "日常闲聊情景",
    "work_chat": "工作沟通情景",
    "study_chat": "学习交流情景",
    "friend_chat": "朋友聊天情景",
    "couple_chat": "情侣聊天情景",
    "family_chat": "家人沟通情景",
    "classmate_chat": "同学聊天情景",
    "customer_service": "客服沟通情景",
    "interview_chat": "面试沟通情景",
    "business_talk": "商务洽谈情景",
    "formal_talk": "正式沟通情景",
    "casual_talk": "轻松随意聊天情景",
    "encourage_chat": "鼓励安慰情景",
    "apology_chat": "道歉沟通情景",
    "greeting_chat": "问候寒暄情景",
    "date_chat": "约会聊天情景",
    "game_chat": "游戏开黑聊天情景",
    "party_chat": "聚会聊天情景",
    "conflict_chat": "矛盾沟通情景",
    "advice_chat": "寻求建议情景"
}

# AI提示词
ChatPersonality = {
    "gentle_healing": "温柔耐心，共情力强，说话轻声细语，温暖包容，不急躁不尖锐，让人安心舒服。",
    "energetic_cute": "活泼俏皮，热情阳光，爱接梗爱分享，元气真诚，聊天轻松有活力，像好朋友。",
    "cool_distant": "话少简洁，冷静克制，不主动不闲聊，保持距离，只说重点，情绪不外露。",
    "mature_stable": "成熟稳重，说话得体，逻辑清晰，客观靠谱，有分寸，情绪稳定让人信赖。",
    "humorous_funny": "风趣幽默，会玩梗，轻松搞笑不冷场，有趣有分寸，不冒犯他人。",
    "sharp_tongued_pride": "嘴硬心软，犀利傲娇，吐槽精准，有原则不软弱，关心不直白说。",
    "scheming_calm": "心思缜密，话少精准，表面温和内心清醒，冷静理智有底线。",
    "intellectual_artistic": "文雅细腻，有思想有质感，安静内敛，适合深度走心交流。",
    "dominant_strong": "果断强势，有主见气场足，主动主导，保护欲强，靠谱有安全感。",
    "lazy_buddha": "佛系慵懒，淡然随性，不争不吵，情绪平和，聊天无压力。",
    "puppy_clingy": "软萌粘人，热情主动，贴心依赖，直白真诚，让人感到被在意。",
    "queen_like_sister": "御姐温柔，成熟大气，会照顾人，从容有主见，安全感十足。",
}

# 聊天风格中文映射
ChatPersonalityCN = {
    "gentle_healing": "温柔治愈",
    "energetic_cute": "活泼可爱",
    "cool_distant": "高冷疏离",
    "mature_stable": "成熟稳重",
    "humorous_funny": "幽默风趣",
    "sharp_tongued_pride": "嘴硬傲娇",
    "scheming_calm": "沉稳心机",
    "intellectual_artistic": "文艺知性",
    "dominant_strong": "强势主导",
    "lazy_buddha": "佛系慵懒",
    "puppy_clingy": "软萌粘人",
    "queen_like_sister": "御姐温柔",
}

# 默认配置
# 总区域
DEFAULT_ALL_AREA = ()
# 用户名区域
DEFAULT_USER_NAME_AREA = None
# 用户列表区域
DEFAULT_FRIENDS_LIST_AREA = None
# 聊天区域（与 YOLO 检测一致：x1, y1, x2, y2，供裁剪与区域逻辑使用）
DEFAULT_CHAT_AREA = (481, 129, 839, 986)
DEFAULT_CHAT_WINDOW_BOX = DEFAULT_CHAT_AREA
# 输入框区域（统一：x1, y1, x2, y2）
# 这里给一个最小退化框，保证 x2>x1 且 y2>y1
DEFAULT_INPUT_BOX = (489, 1253, 490, 1254)
# 聊天软件类型
DEFAULT_CHAT_SOFTWARE = "wechat"
# 检查间隔
DEFAULT_CHECK_INTERVAL = 3
