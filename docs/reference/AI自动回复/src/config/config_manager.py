import json
import os
import logging
from src.config.constants import (
    CONFIG_FILE,
    DEFAULT_CHAT_WINDOW_BOX,
    DEFAULT_CHAT_SOFTWARE,
    DEFAULT_USER_NAME_AREA,
    DEFAULT_FRIENDS_LIST_AREA,
    DEFAULT_INPUT_BOX,
    MONITOR_LIST_FILE,
)

config_logger = logging.getLogger("config")


def _coerce_box4(value):
    """将输入规范化为 (x1, y1, x2, y2)，无效则返回 None。"""
    if value is None:
        return None
    if isinstance(value, (list, tuple)) and len(value) == 4:
        try:
            return tuple(int(v) for v in value)
        except Exception:
            return None
    return None

class UserConfig:
    """用户配置类"""
    def __init__(
        self,
        name,
        personality="gentle_healing",
        scene="daily_chat",
        custom_system_prompt="",
        knowledge_paths=None,
        knowledge_match_keywords=None,
    ):
        self.name = name
        self.personality = personality
        self.scene = scene
        self.custom_system_prompt = custom_system_prompt or ""
        # 相对项目根目录下 knowledge/ 的资料文件路径列表，如 ["shared/报价.txt"]
        self.knowledge_paths = list(knowledge_paths or [])
        # 仅当对方消息包含以下任一子串时才挂载资料；空列表表示不限制（总开关开启即挂载）
        self.knowledge_match_keywords = list(knowledge_match_keywords or [])

    def to_dict(self):
        """转换为字典"""
        return {
            "name": self.name,
            "personality": self.personality,
            "scene": self.scene,
            "custom_system_prompt": self.custom_system_prompt or "",
            "knowledge_paths": list(self.knowledge_paths or []),
            "knowledge_match_keywords": list(self.knowledge_match_keywords or []),
        }

    @classmethod
    def from_dict(cls, data):
        """从字典创建对象"""
        kp = data.get("knowledge_paths") or []
        if not isinstance(kp, list):
            kp = []
        kp = [str(p).strip() for p in kp if str(p).strip()]
        km = data.get("knowledge_match_keywords") or []
        if not isinstance(km, list):
            km = []
        km = [str(x).strip() for x in km if str(x).strip()]
        return cls(
            name=data.get("name", ""),
            personality=data.get("personality", "gentle_healing"),
            scene=data.get("scene", "daily_chat"),
            custom_system_prompt=data.get("custom_system_prompt") or "",
            knowledge_paths=kp,
            knowledge_match_keywords=km,
        )

class ConfigManager:
    """配置管理器"""
    def __init__(self):
        self.friends_config = {}  # 键为用户名，值为UserConfig对象
        self.current_chat_software = DEFAULT_CHAT_SOFTWARE
        self.chat_window_box = DEFAULT_CHAT_WINDOW_BOX
        # 区域：统一存储为 (x1, y1, x2, y2)
        self.input_box_pos = tuple(DEFAULT_INPUT_BOX)
        # 用户名区域 / 好友列表区域（手动填写 + 模型失效回退；允许为空 None）
        self.user_name_box = _coerce_box4(DEFAULT_USER_NAME_AREA)
        self.friend_list_box = _coerce_box4(DEFAULT_FRIENDS_LIST_AREA)
        self.monitored_friends = []
        # 是否在回复中合并资料库（仅当用户在「资料库」页点击「应用此设置」开启后为 True）
        self.knowledge_reply_enabled = False

    def load_config(self):
        """加载配置文件"""
        self.knowledge_reply_enabled = False
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.knowledge_reply_enabled = bool(
                        config.get("knowledge_reply_enabled", False)
                    )
                    # 加载好友配置，转换为UserConfig对象
                    friends_data = config.get('friends_config', {})
                    self.friends_config = {}
                    for name, data in friends_data.items():
                        self.friends_config[name] = UserConfig.from_dict(data)
                    self.current_chat_software = config.get('chat_software', DEFAULT_CHAT_SOFTWARE)
                    self.chat_window_box = tuple(config.get('chat_window_box', list(DEFAULT_CHAT_WINDOW_BOX)))
                    self.input_box_pos = tuple(_coerce_box4(config.get('input_box_pos')) or DEFAULT_INPUT_BOX)
                    self.user_name_box = _coerce_box4(config.get('user_name_box')) or self.user_name_box
                    self.friend_list_box = _coerce_box4(config.get('friend_list_box')) or self.friend_list_box
                    self.monitored_friends = config.get('monitored_friends', []) or []
            except Exception as e:
                config_logger.error(f"加载配置文件失败: {e}")

        # 兼容：若存在 monitor_list.json，则与 monitored_friends 合并
        try:
            if os.path.exists(MONITOR_LIST_FILE):
                with open(MONITOR_LIST_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    from_file = [str(x).strip() for x in data if str(x).strip()]
                    merged = list(dict.fromkeys(list(self.monitored_friends or []) + from_file))
                    self.monitored_friends = merged
        except Exception:
            pass

        # 确保：监听名单中的人，至少在 friends_config 里有一个默认配置（否则 UI 需要重复添加）
        try:
            for name in self.monitored_friends or []:
                if name and name not in self.friends_config:
                    self.friends_config[name] = UserConfig(name=name)
        except Exception:
            pass
        config_logger.info(
            "配置加载完成: friends=%s, monitored=%s",
            len(self.friends_config),
            len(self.monitored_friends or []),
        )
    
    def save_config(self):
        """保存配置文件"""
        # 转换UserConfig对象为字典
        friends_data = {}
        for name, user_config in self.friends_config.items():
            friends_data[name] = user_config.to_dict()
        
        config = {
            'friends_config': friends_data,
            'chat_software': self.current_chat_software,
            'chat_window_box': self.chat_window_box,
            'input_box_pos': self.input_box_pos,
            'user_name_box': self.user_name_box,
            'friend_list_box': self.friend_list_box,
            'monitored_friends': self.monitored_friends,
            'knowledge_reply_enabled': bool(self.knowledge_reply_enabled),
        }
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            # 兼容旧监控名单文件：同步输出一份（可被旧逻辑读取）
            try:
                with open(MONITOR_LIST_FILE, "w", encoding="utf-8") as f:
                    json.dump(self.monitored_friends or [], f, ensure_ascii=False, indent=2)
            except Exception as e:
                config_logger.warning(f"同步 monitor_list.json 失败: {e}")
            config_logger.info("配置保存成功")
            return True
        except Exception as e:
            config_logger.error(f"保存配置文件失败: {e}")
            return False

    # ===== 好友资料/监控名单 CRUD（统一入口）=====
    def list_profiles(self):
        """返回所有好友资料，附带监控状态，用于页面展示。"""
        result = []
        all_names = set(self.friends_config.keys())
        for n in self.monitored_friends or []:
            if n:
                all_names.add(n)
        for name in sorted(all_names):
            uc = self.friends_config.get(name) or UserConfig(name=name)
            result.append(
                {
                    "name": name,
                    "personality": uc.personality,
                    "scene": uc.scene,
                    "custom_system_prompt": uc.custom_system_prompt or "",
                    "knowledge_paths": list(getattr(uc, "knowledge_paths", []) or []),
                    "knowledge_match_keywords": list(
                        getattr(uc, "knowledge_match_keywords", []) or []
                    ),
                    "monitored": name in (self.monitored_friends or []),
                }
            )
        return result

    def upsert_profile(
        self,
        name,
        personality="gentle_healing",
        scene="daily_chat",
        custom_system_prompt="",
        knowledge_paths=None,
        knowledge_match_keywords=None,
    ):
        """新增或更新好友资料。"""
        if not name:
            return False
        old = self.friends_config.get(name)
        if knowledge_paths is None and old is not None:
            knowledge_paths = list(getattr(old, "knowledge_paths", []) or [])
        if knowledge_paths is None:
            knowledge_paths = []
        if knowledge_match_keywords is None and old is not None:
            knowledge_match_keywords = list(
                getattr(old, "knowledge_match_keywords", []) or []
            )
        if knowledge_match_keywords is None:
            knowledge_match_keywords = []
        kp = [str(p).strip().replace("\\", "/") for p in knowledge_paths if str(p).strip()]
        km = [
            str(x).strip()
            for x in knowledge_match_keywords
            if str(x).strip() and not str(x).strip().startswith("#")
        ]
        self.friends_config[name] = UserConfig(
            name=name,
            personality=personality,
            scene=scene,
            custom_system_prompt=custom_system_prompt or "",
            knowledge_paths=kp,
            knowledge_match_keywords=km,
        )
        return True

    def delete_profile(self, name):
        """删除好友资料，并从监控名单移除。"""
        if not name:
            return False
        self.friends_config.pop(name, None)
        if name in self.monitored_friends:
            self.monitored_friends.remove(name)
        return True

    def set_monitored(self, name, monitored: bool):
        """设置好友是否监控；若资料不存在则补默认资料。"""
        if not name:
            return False
        if name not in self.friends_config:
            self.friends_config[name] = UserConfig(name=name)
        if monitored:
            if name not in self.monitored_friends:
                self.monitored_friends.append(name)
        else:
            if name in self.monitored_friends:
                self.monitored_friends.remove(name)
        return True

# 创建配置管理器实例
config_manager = ConfigManager()

# 加载配置
config_manager.load_config()

# 为了保持向后兼容，创建全局变量
friends_config = config_manager.friends_config
current_chat_software = config_manager.current_chat_software
chat_window_box = config_manager.chat_window_box
input_box_pos = config_manager.input_box_pos
user_name_box = config_manager.user_name_box
friend_list_box = config_manager.friend_list_box
monitored_friends = config_manager.monitored_friends
knowledge_reply_enabled = getattr(
    config_manager, "knowledge_reply_enabled", False
)


def load_config():
    """加载配置文件"""
    global config_manager, friends_config, current_chat_software, chat_window_box, input_box_pos, user_name_box, friend_list_box, monitored_friends, knowledge_reply_enabled
    config_manager.load_config()
    # 更新全局变量
    friends_config = config_manager.friends_config
    current_chat_software = config_manager.current_chat_software
    chat_window_box = config_manager.chat_window_box
    input_box_pos = config_manager.input_box_pos
    user_name_box = config_manager.user_name_box
    friend_list_box = config_manager.friend_list_box
    monitored_friends = config_manager.monitored_friends
    knowledge_reply_enabled = config_manager.knowledge_reply_enabled


def save_config():
    """保存配置文件"""
    global config_manager, friends_config, current_chat_software, chat_window_box, input_box_pos, user_name_box, friend_list_box, monitored_friends, knowledge_reply_enabled
    # 更新配置管理器中的值
    config_manager.friends_config = friends_config
    config_manager.current_chat_software = current_chat_software
    config_manager.chat_window_box = chat_window_box
    config_manager.input_box_pos = input_box_pos
    config_manager.user_name_box = user_name_box
    config_manager.friend_list_box = friend_list_box
    config_manager.monitored_friends = monitored_friends
    config_manager.knowledge_reply_enabled = knowledge_reply_enabled
    # 保存配置
    return config_manager.save_config()


def list_profiles():
    """模块级封装：获取好友资料 + 监控状态列表。"""
    global config_manager
    return config_manager.list_profiles()


def upsert_profile(
    name,
    personality="gentle_healing",
    scene="daily_chat",
    custom_system_prompt="",
    knowledge_paths=None,
    knowledge_match_keywords=None,
):
    """模块级封装：新增或更新好友资料并持久化。"""
    global config_manager, friends_config
    ok = config_manager.upsert_profile(
        name,
        personality,
        scene,
        custom_system_prompt,
        knowledge_paths,
        knowledge_match_keywords,
    )
    friends_config = config_manager.friends_config
    if ok:
        return save_config()
    return False


def delete_profile(name):
    """模块级封装：删除好友资料并持久化。"""
    global config_manager, friends_config, monitored_friends
    ok = config_manager.delete_profile(name)
    friends_config = config_manager.friends_config
    monitored_friends = config_manager.monitored_friends
    if ok:
        return save_config()
    return False


def set_monitored(name, monitored: bool):
    """模块级封装：设置监控状态并持久化。"""
    global config_manager, friends_config, monitored_friends
    ok = config_manager.set_monitored(name, monitored)
    friends_config = config_manager.friends_config
    monitored_friends = config_manager.monitored_friends
    if ok:
        return save_config()
    return False
