import tkinter as tk
from tkinter import ttk
import threading
import time
import pyautogui
import json as _json
import hashlib as _hashlib
from difflib import SequenceMatcher
from src.config import config_manager as cfg
from src.config.constants import ChatPersonalityCN, ChatScene
from src.core.ocr import (
    ocr_chat_window,
    ocr_user_area,
    parse_chat_content_by_position,
    get_last_chat_parse_debug,
    parse_friend_list_rows,
    add_monitor_friend,
    remove_monitor_friend,
    get_monitor_list,
    is_monitored,
)
from src.core.ai_api import call_ai_api
from src.core.sender import send_reply
from src.core.monitor import get_chat_areas
from src.core.logger import gui_logger
from src.core.chat_history import append_chat_history
from src.core.knowledge_loader import (
    load_knowledge_bundle,
    should_attach_knowledge_for_message,
)

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
            f.write(_json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _name_sig(name: str) -> dict:
    s = str(name or "")
    norm = "".join(s.split()).casefold()
    return {
        "raw_len": len(s),
        "norm_len": len(norm),
        "raw_hash8": _hashlib.md5(s.encode("utf-8")).hexdigest()[:8],
        "norm_hash8": _hashlib.md5(norm.encode("utf-8")).hexdigest()[:8],
    }
# endregion


def _best_name_match(target: str, candidates):
    """返回与 target 最接近的候选项及相似度。"""
    if not target or not candidates:
        return "", 0.0
    best_name = ""
    best_score = 0.0
    t = str(target)
    for c in candidates:
        c = str(c)
        score = SequenceMatcher(None, t, c).ratio()
        if score > best_score:
            best_name = c
            best_score = score
    return best_name, best_score


class MonitorFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.monitoring = False
        self.monitor_thread = None
        self.last_message_by_user = {}
        # 好友列表未读检测缓存（避免每秒重复提醒）
        self._friend_preview_cache = {}  # name -> last preview text
        self._friend_dot_cache = {}      # name -> last dot state
        self._friend_unread_cache = {}   # name -> last unread_count
        self._friend_last_alert_at = {}  # name -> last alert time
        self._friend_list_last_check_at = 0.0
        # 取消人为轮询延迟（如需降 CPU，可自行改回 >0）
        self.CHECK_INTERVAL = 0
        self.last_no_user_alert = 0  # 上次提示没有监控到用户的时间
        self._stop_requested_at = None
        self.init_ui()
    
    def init_ui(self):
        """初始化监控界面标签页"""
        # 监控状态
        status_frame = ttk.LabelFrame(self, text="监控状态")
        status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.status_var = tk.StringVar(value="未监控")
        ttk.Label(status_frame, text="当前状态：").pack(side=tk.LEFT, padx=10, pady=5)
        ttk.Label(status_frame, textvariable=self.status_var, foreground="red").pack(side=tk.LEFT, padx=10, pady=5)

        self.area_status_var = tk.StringVar(value="区域识别：—")
        ttk.Label(status_frame, textvariable=self.area_status_var, foreground="gray").pack(
            side=tk.LEFT, padx=16, pady=5
        )
        
        # 监控按钮
        button_frame = ttk.Frame(self)
        button_frame.pack(pady=10)
        
        self.start_btn = ttk.Button(button_frame, text="开始监控", command=self.start_monitoring)
        self.start_btn.pack(side=tk.LEFT, padx=10)
        
        self.stop_btn = ttk.Button(button_frame, text="停止监控", command=self.stop_monitoring, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=10)
        
        # 监听好友列表
        monitor_frame = ttk.LabelFrame(self, text="监听好友列表")
        monitor_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        columns = ("friend", "status", "style", "scene", "prompt", "action")
        self.monitor_tree = ttk.Treeview(monitor_frame, columns=columns, show="headings")
        self.monitor_tree.heading("friend", text="好友名称")
        self.monitor_tree.heading("status", text="状态")
        self.monitor_tree.heading("style", text="风格")
        self.monitor_tree.heading("scene", text="情景")
        self.monitor_tree.heading("prompt", text="提示词")
        self.monitor_tree.heading("action", text="操作")
        
        self.monitor_tree.column("friend", width=150)
        self.monitor_tree.column("status", width=70)
        self.monitor_tree.column("style", width=90)
        self.monitor_tree.column("scene", width=100)
        self.monitor_tree.column("prompt", width=120)
        self.monitor_tree.column("action", width=70)
        
        self.monitor_tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        
        scrollbar = ttk.Scrollbar(monitor_frame, orient=tk.VERTICAL, command=self.monitor_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.monitor_tree.configure(yscrollcommand=scrollbar.set)
        
        # 绑定点击事件
        self.monitor_tree.bind("<Double-1>", lambda e: self.on_monitor_tree_click(e))
        
        # 消息提醒列表
        alert_frame = ttk.LabelFrame(self, text="消息提醒")
        alert_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.alert_listbox = tk.Listbox(alert_frame, width=80, height=10)
        self.alert_listbox.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        
        scrollbar = ttk.Scrollbar(alert_frame, orient=tk.VERTICAL, command=self.alert_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.alert_listbox.configure(yscrollcommand=scrollbar.set)
        
        # 绑定点击事件
        self.alert_listbox.bind("<Double-1>", lambda e: self.on_alert_click(e))
        
        # 刷新监听好友列表
        self.refresh_monitor_list()
    
    def refresh_monitor_list(self):
        """刷新监听好友列表"""
        # 清空现有数据
        for item in self.monitor_tree.get_children():
            self.monitor_tree.delete(item)
        
        # 添加数据
        if not cfg.friends_config:
            gui_logger.warning("好友列表为空，请先在聊天风格设置中添加好友")

        # 显示 profile + 监控状态（包含持久化的提示词等信息）
        profiles = cfg.list_profiles()
        for item in profiles:
            friend = item["name"]
            status = "已监听" if is_monitored(friend) else "未监听"
            action = "监听" if not is_monitored(friend) else "取消监听"
            style_cn = ChatPersonalityCN.get(item.get("personality"), item.get("personality"))
            scene_cn = ChatScene.get(item.get("scene"), item.get("scene"))
            prompt_text = (item.get("custom_system_prompt") or "").strip()
            prompt_flag = "自定义" if prompt_text else "默认"
            self.monitor_tree.insert(
                "",
                tk.END,
                values=(friend, status, style_cn, scene_cn, prompt_flag, action),
            )
        gui_logger.info(f"刷新监听好友列表，共 {len(profiles)} 项")
    
    def add_monitored_friend(self, friend_name):
        """添加监控好友"""
        if not is_monitored(friend_name):
            add_monitor_friend(friend_name)
            self.refresh_monitor_list()
    
    def remove_monitored_friend(self, friend_name):
        """移除监控好友"""
        if is_monitored(friend_name):
            remove_monitor_friend(friend_name)
            self.refresh_monitor_list()
    
    def clear_monitored_friends(self):
        """清空监控好友"""
        monitor_list = get_monitor_list()
        for friend in monitor_list:
            remove_monitor_friend(friend)
        self.refresh_monitor_list()
    
    def on_monitor_tree_click(self, event):
        """处理监控列表点击事件"""
        item = self.monitor_tree.identify_row(event.y)
        if not item:
            return
        
        col = self.monitor_tree.identify_column(event.x)
        # region agent log
        _dbg(
            "H8",
            "src/gui/monitor_frame.py:on_monitor_tree_click",
            "tree click",
            {"col": col, "item": str(item)},
        )
        # endregion
        if col == "#6":  # 操作列
            values = self.monitor_tree.item(item, "values")
            if values and len(values) > 0:
                friend_name = values[0]
                # region agent log
                _dbg(
                    "H8",
                    "src/gui/monitor_frame.py:on_monitor_tree_click",
                    "before toggle",
                    {
                        "friend": str(friend_name),
                        "is_monitored_before": bool(is_monitored(friend_name)),
                        "monitor_count_before": len(get_monitor_list()),
                    },
                )
                # endregion
                if is_monitored(friend_name):
                    remove_monitor_friend(friend_name)
                else:
                    add_monitor_friend(friend_name)
                # region agent log
                _dbg(
                    "H8",
                    "src/gui/monitor_frame.py:on_monitor_tree_click",
                    "after toggle",
                    {
                        "friend": str(friend_name),
                        "is_monitored_after": bool(is_monitored(friend_name)),
                        "monitor_count_after": len(get_monitor_list()),
                        "monitor_names_after": get_monitor_list()[:20],
                    },
                )
                # endregion
                self.refresh_monitor_list()
    
    def on_alert_click(self, event):
        """处理消息提醒点击事件"""
        selected_index = self.alert_listbox.curselection()
        if selected_index:
            alert_text = self.alert_listbox.get(selected_index[0])
            # 这里可以添加切换到对应好友聊天窗口的逻辑
            gui_logger.info(f"点击了提醒：{alert_text}")
    
    def add_alert(self, friend_name, message):
        """添加消息提醒"""
        alert_text = f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {friend_name}: {message[:50]}..."
        self.alert_listbox.insert(0, alert_text)
        # 限制提醒数量
        if self.alert_listbox.size() > 50:
            self.alert_listbox.delete(50, tk.END)

    def _check_friend_list_updates(self, areas, screenshot):
        """
        检测好友列表中的未读（仅依赖红色未读圆圈 + 数字）。
        - 仅对监听名单中的用户生效
        - 节流：默认每 2 秒检测一次
        """
        try:
            now = time.time()
            if now - float(self._friend_list_last_check_at or 0.0) < 2.0:
                return
            self._friend_list_last_check_at = now

            if not areas or not areas.get("friend_list"):
                # region agent log
                _dbg(
                    "HFL1",
                    "src/gui/monitor_frame.py:_check_friend_list_updates",
                    "skip: no friend_list area",
                    {"areas_keys": sorted(list((areas or {}).keys())) if isinstance(areas, dict) else str(type(areas))},
                )
                # endregion
                return
            monitored = list(get_monitor_list() or [])
            if not monitored:
                # region agent log
                _dbg(
                    "HFL1",
                    "src/gui/monitor_frame.py:_check_friend_list_updates",
                    "skip: empty monitor list",
                    {"monitor_count": 0},
                )
                # endregion
                return

            # region agent log
            try:
                img_wh = tuple(getattr(screenshot, "size", (None, None)))
            except Exception:
                img_wh = (None, None)
            _dbg(
                "HFL1",
                "src/gui/monitor_frame.py:_check_friend_list_updates",
                "friend list check begin",
                {
                    "friend_list_box": list(areas.get("friend_list")) if isinstance(areas.get("friend_list"), (list, tuple)) else str(areas.get("friend_list")),
                    "monitor_count": len(monitored),
                    "monitor_names_head": [str(x) for x in monitored[:10]],
                    "cache_preview_size": len(self._friend_preview_cache),
                    "cache_dot_size": len(self._friend_dot_cache),
                    "screenshot_wh": list(img_wh) if isinstance(img_wh, tuple) else str(img_wh),
                },
            )
            # endregion

            rows = parse_friend_list_rows(areas["friend_list"], image=screenshot)
            # region agent log
            _dbg(
                "HFL2",
                "src/gui/monitor_frame.py:_check_friend_list_updates",
                "friend list rows parsed",
                {
                    "rows_count": len(rows or []),
                    "rows_head": [
                        {
                            "name": str((r or {}).get("name", "")).strip(),
                            "unread_count": int((r or {}).get("unread_count") or 0),
                            "has_unread_badge": bool((r or {}).get("has_unread_badge")),
                            "badge_bbox": (r or {}).get("badge_bbox"),
                            "row_bbox": (r or {}).get("row_bbox"),
                        }
                        for r in (rows or [])[:8]
                    ],
                },
            )
            # endregion
            if not rows:
                return

            # 若好友列表裁剪区域没覆盖到“昵称列”，OCR 往往只能读到时间/预览，导致监控名单永远命中不了。
            # 这里做一次自愈：当本轮 rows 中没有任何昵称命中监控名单时，自动向左扩展 friend_list_box 并重试一次。
            try:
                matched_any = False
                for r in rows:
                    nm = str((r or {}).get("name", "")).strip()
                    if nm and is_monitored(nm):
                        matched_any = True
                        break
                if not matched_any:
                    fl = areas.get("friend_list")
                    if isinstance(fl, (list, tuple)) and len(fl) == 4:
                        x1, y1, x2, y2 = [int(v) for v in fl]
                        sw, sh = (None, None)
                        try:
                            sw, sh = getattr(screenshot, "size", (None, None))
                        except Exception:
                            pass
                        # 默认向左扩 520 像素；并确保不越界
                        new_x1 = max(0, x1 - 520)
                        new_x2 = x2
                        if isinstance(sw, int) and sw:
                            new_x2 = min(int(sw), new_x2)
                        retry_box = (new_x1, y1, new_x2, y2)
                        # region agent log
                        _dbg(
                            "HFL4",
                            "src/gui/monitor_frame.py:_check_friend_list_updates",
                            "no monitored names matched; retry with expanded box",
                            {"orig_box": [x1, y1, x2, y2], "retry_box": [new_x1, y1, new_x2, y2], "screen_wh": [sw, sh]},
                        )
                        # endregion
                        rows2 = parse_friend_list_rows(retry_box, image=screenshot)
                        # region agent log
                        _dbg(
                            "HFL4",
                            "src/gui/monitor_frame.py:_check_friend_list_updates",
                            "retry rows parsed",
                            {
                                "rows2_count": len(rows2 or []),
                                "rows2_head": [
                                    {
                                        "name": str((rr or {}).get("name", "")).strip(),
                                        "preview": str((rr or {}).get("preview", "")).strip()[:40],
                                        "has_red_dot": bool((rr or {}).get("has_red_dot")),
                                    }
                                    for rr in (rows2 or [])[:8]
                                ],
                            },
                        )
                        # endregion
                        if rows2:
                            # 仅当重试结果里出现任何监控昵称命中，才采用重试结果
                            matched2 = False
                            try:
                                for rr in rows2:
                                    nm2 = str((rr or {}).get("name", "")).strip()
                                    if nm2 and is_monitored(nm2):
                                        matched2 = True
                                        break
                            except Exception:
                                matched2 = False
                            # region agent log
                            _dbg(
                                "HFL4",
                                "src/gui/monitor_frame.py:_check_friend_list_updates",
                                "retry adopt decision",
                                {"matched_any_monitored_in_retry": bool(matched2)},
                            )
                            # endregion
                            if matched2:
                                rows = rows2
            except Exception:
                pass

            unknown_dot_rows = 0
            for r in rows:
                name = str(r.get("name", "")).strip()
                unread_count = int(r.get("unread_count") or 0)
                has_badge = bool(r.get("has_unread_badge")) and unread_count > 0

                # 允许：未读角标检测到但昵称识别失败 -> 也提示（否则用户感觉“明明有未读但没反应”）
                if not name:
                    if has_badge:
                        unknown_dot_rows += 1
                    continue
                if not is_monitored(name):
                    continue

                last_unread = int(self._friend_unread_cache.get(name, 0) or 0)
                self._friend_unread_cache[name] = unread_count

                # 只看未读角标数字：从 0->N 或 N 变化都视为新消息
                if not has_badge:
                    continue
                if unread_count <= 0:
                    continue
                if unread_count == last_unread:
                    continue

                last_alert = float(self._friend_last_alert_at.get(name, 0.0) or 0.0)
                # 同一好友 5 秒内最多提醒一次，防抖
                if now - last_alert < 5.0:
                    continue
                self._friend_last_alert_at[name] = now

                msg = f"好友列表检测到新消息（未读 {unread_count} 条）"
                self.add_alert(name, msg)
                # region agent log
                _dbg(
                    "HFL3",
                    "src/gui/monitor_frame.py:_check_friend_list_updates",
                    "alert emitted",
                    {
                        "name": str(name),
                        "unread_count": int(unread_count),
                        "last_unread": int(last_unread),
                    },
                )
                # endregion

            # 若检测到“红点但昵称为空”的行，给一个汇总提醒（节流）
            if unknown_dot_rows > 0:
                last_alert = float(self._friend_last_alert_at.get("__unknown_dot__", 0.0) or 0.0)
                if now - last_alert >= 8.0:
                    self._friend_last_alert_at["__unknown_dot__"] = now
                    self.add_alert("好友列表", f"检测到 {unknown_dot_rows} 个未读角标，但昵称识别失败（请调整好友列表区域或分辨率）。")
        except Exception as e:
            gui_logger.debug(f"好友列表未读检测失败: {e}")
    
    def start_monitoring(self):
        """开始监控"""
        # 用户期望：点击“开始监控”后，直接对监控列表成员生效
        # 这里将当前资料列表中的好友自动加入监听名单（仅首次/缺失时补齐）
        profile_names = [p["name"] for p in cfg.list_profiles() if str(p.get("name", "")).strip()]
        before = get_monitor_list()
        # region agent log
        _dbg(
            "H10",
            "src/gui/monitor_frame.py:start_monitoring",
            "auto-monitor before",
            {"profile_count": len(profile_names), "monitor_count_before": len(before), "profiles": profile_names[:50]},
        )
        # endregion
        for name in profile_names:
            if not is_monitored(name):
                add_monitor_friend(name)
        after = get_monitor_list()
        # region agent log
        _dbg(
            "H10",
            "src/gui/monitor_frame.py:start_monitoring",
            "auto-monitor after",
            {"monitor_count_after": len(after), "monitor_names": after[:50]},
        )
        # endregion

        self.monitoring = True
        self._stop_requested_at = None
        self.status_var.set("监控中")
        self.area_status_var.set("区域识别：检测中…")
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.refresh_monitor_list()
        # region agent log
        _dbg(
            "H19",
            "src/gui/monitor_frame.py:start_monitoring",
            "monitor start requested",
            {"monitoring": bool(self.monitoring), "thread_alive_before": bool(self.monitor_thread and self.monitor_thread.is_alive())},
        )
        # endregion
        
        # 启动监控线程
        self.monitor_thread = threading.Thread(target=self.monitor_chat, daemon=True)
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """停止监控"""
        # region agent log
        _dbg(
            "H19",
            "src/gui/monitor_frame.py:stop_monitoring",
            "monitor stop requested",
            {
                "monitoring_before": bool(self.monitoring),
                "thread_alive_before": bool(self.monitor_thread and self.monitor_thread.is_alive()),
            },
        )
        # endregion
        self.monitoring = False
        self._stop_requested_at = time.time()
        self.status_var.set("未监控")
        self.area_status_var.set("区域识别：—")
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        # region agent log
        _dbg(
            "H19",
            "src/gui/monitor_frame.py:stop_monitoring",
            "monitor stop state updated",
            {
                "monitoring_after": bool(self.monitoring),
                "thread_alive_after": bool(self.monitor_thread and self.monitor_thread.is_alive()),
            },
        )
        # endregion

    def _set_area_status_ui(self, text):
        """监控线程里更新状态栏（主线程执行）"""
        def apply():
            if self.winfo_exists():
                self.area_status_var.set(text)

        try:
            self.after(0, apply)
        except tk.TclError:
            pass
    
    def monitor_chat(self):
        """监控聊天"""
        last_status = None  # 上次的状态
        last_user_name = ""
        while self.monitoring:
            try:
                # 获取聊天区域
                areas, message = get_chat_areas()

                if areas:
                    self._set_area_status_ui("区域识别：成功")
                    screenshot = pyautogui.screenshot()
                    # 先做好友列表未读检测（不依赖当前聊天对象）
                    self._check_friend_list_updates(areas, screenshot)
                    user_name = ocr_user_area(areas["user_object"], screenshot)
                    chat_lines = ocr_chat_window(areas["chat_area"], screenshot)

                    # region agent log
                    _dbg(
                        "H6",
                        "src/gui/monitor_frame.py:monitor_chat",
                        "ocr user and monitor-list signature",
                        {
                            "user": _name_sig(user_name),
                            "monitor_count": len(get_monitor_list()),
                            "monitor_sigs": [_name_sig(n) for n in get_monitor_list()[:20]],
                        },
                    )
                    # endregion

                    if is_monitored(user_name):
                        if last_status != "monitored" or str(user_name) != str(last_user_name):
                            gui_logger.info(f"监控到用户：{user_name}")
                            last_status = "monitored"
                            last_user_name = str(user_name)

                        other_messages, my_messages, message_sequence = parse_chat_content_by_position(chat_lines)
                        # region agent log
                        _dbg(
                            "H12",
                            "src/gui/monitor_frame.py:monitor_chat",
                            "parse summary",
                            {
                                "chat_lines_count": len(chat_lines),
                                "other_count": len(other_messages),
                                "my_count": len(my_messages),
                                "sequence_count": len(message_sequence),
                                "last_sender": message_sequence[-1][0] if message_sequence else None,
                                "last_text": (message_sequence[-1][1] if message_sequence else "")[:100],
                            },
                        )
                        # endregion

                        # 仅在“将触发回复”的情况下，打印本轮归属判定的关键参数（避免刷屏）
                        try:
                            if message_sequence and message_sequence[-1][0] == "other":
                                dbg = get_last_chat_parse_debug()
                                if dbg:
                                    gui_logger.info(
                                        "归属判定参数: "
                                        f"chat_w={dbg.get('chat_w')}, center={round(float(dbg.get('chat_center_x') or 0.0), 1)}, "
                                        f"block_bbox={dbg.get('block_bbox')}, block_center={round(float(dbg.get('block_center_x') or 0.0), 1)}, "
                                        f"rel_center={round(float(dbg.get('rel_center') or 0.0), 3)}, "
                                        f"left_margin={round(float(dbg.get('left_margin') or 0.0), 1)}, "
                                        f"right_margin={round(float(dbg.get('right_margin') or 0.0), 1)}, "
                                        f"bias={dbg.get('margin_bias_px')}, method={dbg.get('method')}, side={dbg.get('side')}"
                                    )
                        except Exception:
                            pass

                        if message_sequence and message_sequence[-1][0] == 'other':
                            # 仅以“最后一行”作为触发依据，避免旧行拼接导致误触发
                            latest_other_message = str(message_sequence[-1][1] or "").strip()
                            # region agent log
                            _dbg(
                                "H14",
                                "src/gui/monitor_frame.py:monitor_chat",
                                "latest other message",
                                {
                                    "user_ocr": str(user_name),
                                    "latest_len": len(latest_other_message or ""),
                                    "latest": (latest_other_message or "")[:120],
                                },
                            )
                            # endregion

                            from src.core.ocr import message_manager

                            is_dup = message_manager.is_message_duplicate(user_name, latest_other_message)
                            # region agent log
                            _dbg(
                                "H13",
                                "src/gui/monitor_frame.py:monitor_chat",
                                "duplicate check",
                                {
                                    "user_ocr": str(user_name),
                                    "is_duplicate": bool(is_dup),
                                    "latest_hash8": _hashlib.md5((latest_other_message or "").encode("utf-8")).hexdigest()[:8],
                                },
                            )
                            # endregion
                            if not is_dup:
                                last_for_user = self.last_message_by_user.get(user_name, "")
                                sim_ratio = (
                                    SequenceMatcher(
                                        None,
                                        "".join(str(latest_other_message or "").split()),
                                        "".join(str(last_for_user or "").split()),
                                    ).ratio()
                                    if last_for_user
                                    else 0.0
                                )
                                # region agent log
                                _dbg(
                                    "H17",
                                    "src/gui/monitor_frame.py:monitor_chat",
                                    "similarity gate",
                                    {
                                        "sim_ratio": round(float(sim_ratio), 4),
                                        "last_len": len(last_for_user or ""),
                                        "latest_len": len(latest_other_message or ""),
                                    },
                                )
                                # endregion
                                if latest_other_message != last_for_user and sim_ratio < 0.88:
                                    # 端到端时延预算：从“检测到需回复”到“发送成功确认”最多 10 秒
                                    detect_t0 = time.time()
                                    # region agent log
                                    _dbg(
                                        "H19",
                                        "src/gui/monitor_frame.py:monitor_chat",
                                        "before ai call monitor-state",
                                        {
                                            "monitoring": bool(self.monitoring),
                                            "stop_elapsed_ms": int((time.time() - self._stop_requested_at) * 1000)
                                            if self._stop_requested_at else None,
                                        },
                                    )
                                    # endregion
                                    gui_logger.info(f"收到消息：{latest_other_message[:50]}...")
                                    # 落盘：对方消息
                                    try:
                                        append_chat_history(user_name, "other", latest_other_message)
                                    except Exception as e:
                                        gui_logger.debug(f"写入聊天记录失败(other): {e}")
                                    user_config = cfg.friends_config.get(user_name)
                                    style = user_config.personality if user_config else "gentle_healing"
                                    scene = user_config.scene if user_config else "daily_chat"
                                    prior_history = message_manager.get_history(user_name)
                                    custom_prompt = (
                                        user_config.custom_system_prompt if user_config else ""
                                    )
                                    ref_materials = ""
                                    if getattr(cfg, "knowledge_reply_enabled", False):
                                        kws = (
                                            getattr(user_config, "knowledge_match_keywords", None)
                                            if user_config
                                            else None
                                        )
                                        if should_attach_knowledge_for_message(
                                            latest_other_message, kws
                                        ):
                                            ref_materials = load_knowledge_bundle(
                                                user_name,
                                                getattr(user_config, "knowledge_paths", None)
                                                if user_config
                                                else None,
                                            )
                                    use_ai = True
                                    # region agent log
                                    _dbg(
                                        "H13",
                                        "src/gui/monitor_frame.py:monitor_chat",
                                        "ai call gate",
                                        {
                                            "last_for_user_len": len(last_for_user or ""),
                                            "prior_history_len": len(prior_history or ""),
                                            "will_call_ai": bool(use_ai),
                                        },
                                    )
                                    # endregion
                                    # 给 AI 留出可控预算，避免单次请求把整体 SLA 撑爆
                                    total_budget_s = 10.0
                                    send_and_confirm_budget_s = 2.6  # 发送 + UI 刷新 + 一次确认 OCR
                                    remaining_s = total_budget_s - (time.time() - detect_t0)
                                    ai_timeout_s = max(0.2, min(6.0, remaining_s - send_and_confirm_budget_s))

                                    if ai_timeout_s <= 0.3:
                                        ai_reply = "收到，我马上看下。"
                                    else:
                                        ai_reply = call_ai_api(
                                            latest_other_message,
                                            style,
                                            scene,
                                            prior_history,
                                            custom_prompt,
                                            reference_materials=ref_materials,
                                            timeout_s=ai_timeout_s,
                                        )
                                    # region agent log
                                    _dbg(
                                        "H16",
                                        "src/gui/monitor_frame.py:monitor_chat",
                                        "ai reply generated",
                                        {
                                            "reply_len": len(str(ai_reply or "")),
                                            "reply_preview": str(ai_reply or "")[:80],
                                        },
                                    )
                                    # endregion
                                    # 发送（返回实际发送文本，避免“发送内容”和“落盘/确认内容”不一致）
                                    sent_text = send_reply(ai_reply, areas["input_box"])

                                    # 发送成功确认：在短时间内观察“最后一条消息归属”切到 me
                                    confirm_ok = False
                                    confirm_deadline = min(2.0, max(0.0, total_budget_s - (time.time() - detect_t0)))
                                    confirm_t_end = time.time() + confirm_deadline
                                    before_last = message_sequence[-1] if message_sequence else None
                                    expected = sent_text or str(ai_reply or "").strip()

                                    def _norm(s: str) -> str:
                                        return "".join(str(s or "").split())

                                    while time.time() < confirm_t_end:
                                        try:
                                            ss2 = pyautogui.screenshot()
                                            cl2 = ocr_chat_window(areas["chat_area"], ss2)
                                            _, _, seq2 = parse_chat_content_by_position(cl2)
                                            if seq2 and seq2[-1][0] == "me":
                                                last_txt = str(seq2[-1][1] or "").strip()
                                                sim = (
                                                    SequenceMatcher(None, _norm(last_txt), _norm(expected)).ratio()
                                                    if last_txt and expected
                                                    else 0.0
                                                )
                                                # 满足其一即可：
                                                # - 文本相似（OCR 可能缺字，但相似度应明显高于随机）
                                                # - 或者 last sender 已从 other -> me（至少 UI 已更新到我方气泡）
                                                if sim >= 0.35 or (before_last and before_last[0] == "other"):
                                                    confirm_ok = True
                                                    break
                                        except Exception:
                                            pass
                                        # 不引入人为延迟，交给 UI/系统调度
                                        time.sleep(0)

                                    if not confirm_ok:
                                        gui_logger.warning("发送确认超时：未在预算内观察到我方最后一条消息。")
                                    # 落盘：我方回复
                                    try:
                                        append_chat_history(user_name, "me", sent_text or ai_reply)
                                    except Exception as e:
                                        gui_logger.debug(f"写入聊天记录失败(me): {e}")
                                    # region agent log
                                    _dbg(
                                        "H16",
                                        "src/gui/monitor_frame.py:monitor_chat",
                                        "send reply invoked",
                                        {
                                            "input_box": areas.get("input_box"),
                                            "reply_len": len(str(ai_reply or "")),
                                        },
                                    )
                                    # endregion
                                    self.add_alert(user_name, latest_other_message)
                                    self.last_message_by_user[user_name] = latest_other_message
                                    message_manager.set_history(user_name, latest_other_message)
                                    message_manager.update_message_hash(user_name, latest_other_message)
                            else:
                                gui_logger.debug(f"消息重复，跳过处理: {latest_other_message[:50]}...")
                    else:
                        if last_status != "not_monitored":
                            monitor_names = get_monitor_list()
                            profile_names = [p["name"] for p in cfg.list_profiles()]
                            best_m, best_m_score = _best_name_match(user_name, monitor_names)
                            best_p, best_p_score = _best_name_match(user_name, profile_names)
                            cp = " ".join(f"U+{ord(ch):04X}" for ch in str(user_name or ""))
                            gui_logger.warning(
                                "当前对话对象不在监听列表中，跳过回复。"
                                f" OCR提取用户名='{user_name}'，OCR用户名码点={cp}，"
                                f"监听名单数量={len(monitor_names)}，"
                                f"监听名单最佳匹配='{best_m}'({best_m_score:.2f})，"
                                f"配置资料最佳匹配='{best_p}'({best_p_score:.2f})"
                            )
                            last_status = "not_monitored"
                            last_user_name = ""
                else:
                    short = (message or "")[:48] + ("…" if message and len(message) > 48 else "")
                    self._set_area_status_ui(f"区域识别：失败 {short}")
                    gui_logger.error(f"获取聊天区域失败：{message}")

                time.sleep(max(0, float(self.CHECK_INTERVAL or 0)))
            except Exception as e:
                gui_logger.error(f"监控出错：{e}")
                time.sleep(max(0, float(self.CHECK_INTERVAL or 0)))
        # region agent log
        _dbg(
            "H19",
            "src/gui/monitor_frame.py:monitor_chat",
            "monitor loop exited",
            {
                "monitoring": bool(self.monitoring),
                "thread_alive": bool(self.monitor_thread and self.monitor_thread.is_alive()),
            },
        )
        # endregion
