import tkinter as tk
from tkinter import ttk, messagebox
from src.config import config_manager as cfg
from src.config.constants import ChatPersonality, ChatPersonalityCN, ChatScene


class StyleFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self._loading_form = False
        self.init_ui()

    def init_ui(self):
        """初始化聊天风格设置标签页"""
        friend_frame = ttk.LabelFrame(self, text="好友与 AI 设定")
        friend_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        input_frame = ttk.Frame(friend_frame)
        input_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(input_frame, text="好友名称：").pack(side=tk.LEFT, padx=5, pady=5)
        self.friend_name_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.friend_name_var, width=14).pack(
            side=tk.LEFT, padx=5, pady=5
        )

        ttk.Label(input_frame, text="聊天风格：").pack(side=tk.LEFT, padx=5, pady=5)
        self.style_var = tk.StringVar(value="温柔治愈")
        style_options = list(ChatPersonalityCN.values())
        self.style_combo = ttk.Combobox(
            input_frame, textvariable=self.style_var, values=style_options, width=9, state="readonly"
        )
        self.style_combo.pack(side=tk.LEFT, padx=5, pady=5)
        self.style_combo.current(0)

        ttk.Label(input_frame, text="聊天情景：").pack(side=tk.LEFT, padx=5, pady=5)
        self.scene_var = tk.StringVar(value=ChatScene["daily_chat"])
        scene_options = list(ChatScene.values())
        self.scene_combo = ttk.Combobox(
            input_frame, textvariable=self.scene_var, values=scene_options, width=12, state="readonly"
        )
        self.scene_combo.pack(side=tk.LEFT, padx=5, pady=5)
        self.scene_combo.current(0)

        ttk.Button(input_frame, text="保存", command=self.save_friend_config).pack(
            side=tk.LEFT, padx=8, pady=5
        )

        prompt_frame = ttk.LabelFrame(friend_frame, text="自定义系统提示词（可选，非空时完全替代上方的风格+情景预设）")
        prompt_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        prompt_inner = ttk.Frame(prompt_frame)
        prompt_inner.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.prompt_text = tk.Text(prompt_inner, height=5, wrap=tk.WORD, font=("Microsoft YaHei UI", 9))
        p_scroll = ttk.Scrollbar(prompt_inner, orient=tk.VERTICAL, command=self.prompt_text.yview)
        self.prompt_text.configure(yscrollcommand=p_scroll.set)
        self.prompt_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        p_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        hint = (
            "提示：可描述身份、语气、禁忌、回复长度等；留空则使用「聊天风格 + 聊天情景」自动生成系统提示。"
        )
        ttk.Label(prompt_frame, text=hint, wraplength=720, foreground="gray").pack(
            anchor=tk.W, padx=5, pady=(0, 5)
        )

        kb_frame = ttk.LabelFrame(
            friend_frame,
            text="挂载的本地资料（每行一条路径，相对项目下 knowledge/，如 shared/说明.txt）",
        )
        kb_frame.pack(fill=tk.BOTH, expand=False, padx=10, pady=5)
        kb_inner = ttk.Frame(kb_frame)
        kb_inner.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.knowledge_paths_text = tk.Text(kb_inner, height=4, wrap=tk.NONE, font=("Consolas", 9))
        kb_scroll = ttk.Scrollbar(kb_inner, orient=tk.VERTICAL, command=self.knowledge_paths_text.yview)
        self.knowledge_paths_text.configure(yscrollcommand=kb_scroll.set)
        self.knowledge_paths_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        kb_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        kw_frame = ttk.LabelFrame(
            friend_frame,
            text="资料触发关键词（每行一条子串；留空=不筛选，启用资料库时对每条消息都挂载资料）",
        )
        kw_frame.pack(fill=tk.BOTH, expand=False, padx=10, pady=5)
        kw_inner = ttk.Frame(kw_frame)
        kw_inner.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.knowledge_keywords_text = tk.Text(kw_inner, height=3, wrap=tk.WORD, font=("Microsoft YaHei UI", 9))
        kw_scroll = ttk.Scrollbar(kw_inner, orient=tk.VERTICAL, command=self.knowledge_keywords_text.yview)
        self.knowledge_keywords_text.configure(yscrollcommand=kw_scroll.set)
        self.knowledge_keywords_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        kw_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        ttk.Label(
            kw_frame,
            text="示例：价格、报价、云程、合同、发票、售后（命中其一才挂载；可与 shared/demo_*.txt 搭配使用）",
            wraplength=720,
            foreground="gray",
        ).pack(anchor=tk.W, padx=5, pady=(0, 5))

        ttk.Label(
            kb_frame,
            text="另：knowledge/friends/<好友名>.txt 为专属资料；须先在「资料库」页启用合并才会注入。",
            wraplength=720,
            foreground="gray",
        ).pack(anchor=tk.W, padx=5, pady=(0, 5))

        list_frame = ttk.Frame(friend_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        columns = ("friend", "style", "scene", "prompt", "action")
        self.style_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=8)
        self.style_tree.heading("friend", text="好友名称")
        self.style_tree.heading("style", text="聊天风格")
        self.style_tree.heading("scene", text="情景")
        self.style_tree.heading("prompt", text="自定义提示")
        self.style_tree.heading("action", text="操作")

        self.style_tree.column("friend", width=120)
        self.style_tree.column("style", width=100)
        self.style_tree.column("scene", width=120)
        self.style_tree.column("prompt", width=70)
        self.style_tree.column("action", width=56)

        self.style_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.style_tree.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.style_tree.configure(yscrollcommand=sb.set)

        self.style_tree.bind("<Double-1>", self.on_style_tree_double_click)
        self.style_tree.bind("<<TreeviewSelect>>", self.on_friend_select)

        self.refresh_style_list()

    def get_style_key(self, style_name):
        for key, value in ChatPersonalityCN.items():
            if value == style_name:
                return key
        return "gentle_healing"

    def get_scene_key(self, scene_label):
        for key, value in ChatScene.items():
            if value == scene_label:
                return key
        return "daily_chat"

    def _set_prompt_widget(self, text):
        self._loading_form = True
        try:
            self.prompt_text.delete("1.0", tk.END)
            if text:
                self.prompt_text.insert("1.0", text)
        finally:
            self._loading_form = False

    def _set_knowledge_widget(self, lines):
        self._loading_form = True
        try:
            self.knowledge_paths_text.delete("1.0", tk.END)
            if lines:
                self.knowledge_paths_text.insert("1.0", lines)
        finally:
            self._loading_form = False

    def _set_keywords_widget(self, lines):
        self._loading_form = True
        try:
            self.knowledge_keywords_text.delete("1.0", tk.END)
            if lines:
                self.knowledge_keywords_text.insert("1.0", lines)
        finally:
            self._loading_form = False

    def on_friend_select(self, event):
        if self._loading_form:
            return
        sel = self.style_tree.selection()
        if not sel:
            return
        values = self.style_tree.item(sel[0], "values")
        if not values:
            return
        friend_name = values[0]
        uc = cfg.friends_config.get(friend_name)
        if not uc:
            # 允许从监听列表进入：自动补一个默认配置，避免“每次都要重新添加”
            cfg.upsert_profile(friend_name)
            uc = cfg.friends_config.get(friend_name)
        self.friend_name_var.set(friend_name)
        self.style_var.set(ChatPersonalityCN.get(uc.personality, list(ChatPersonalityCN.values())[0]))
        self.scene_var.set(ChatScene.get(uc.scene, ChatScene["daily_chat"]))
        self._set_prompt_widget(getattr(uc, "custom_system_prompt", "") or "")
        kp = getattr(uc, "knowledge_paths", None) or []
        self._set_knowledge_widget("\n".join(str(p) for p in kp if str(p).strip()))
        km = getattr(uc, "knowledge_match_keywords", None) or []
        self._set_keywords_widget("\n".join(str(x) for x in km if str(x).strip()))

    def save_friend_config(self):
        friend_name = self.friend_name_var.get().strip()
        if not friend_name:
            messagebox.showerror("错误", "请输入好友名称！")
            return

        style_key = self.get_style_key(self.style_var.get())
        scene_key = self.get_scene_key(self.scene_var.get())
        prompt_body = self.prompt_text.get("1.0", tk.END).strip()
        kb_raw = self.knowledge_paths_text.get("1.0", tk.END)
        knowledge_paths = [
            ln.strip().replace("\\", "/")
            for ln in kb_raw.splitlines()
            if ln.strip() and not ln.strip().startswith("#")
        ]
        kw_raw = self.knowledge_keywords_text.get("1.0", tk.END)
        knowledge_match_keywords = [
            ln.strip()
            for ln in kw_raw.splitlines()
            if ln.strip() and not ln.strip().startswith("#")
        ]

        cfg.upsert_profile(
            friend_name,
            personality=style_key,
            scene=scene_key,
            custom_system_prompt=prompt_body,
            knowledge_paths=knowledge_paths,
            knowledge_match_keywords=knowledge_match_keywords,
        )
        self.refresh_style_list()
        messagebox.showinfo("成功", "已保存该好友的聊天风格与提示词设置。")

    def delete_friend_style(self, friend_name):
        if cfg.delete_profile(friend_name):
            self.refresh_style_list()
            messagebox.showinfo("成功", "已删除该好友配置。")

    def refresh_style_list(self):
        for item in self.style_tree.get_children():
            self.style_tree.delete(item)

        for item in cfg.list_profiles():
            friend = item["name"]
            user_config = cfg.friends_config.get(friend)
            if user_config is None:
                # 防御：理论上 list_profiles 已补齐
                cfg.upsert_profile(friend)
                user_config = cfg.friends_config.get(friend)
            style_name = ChatPersonalityCN.get(user_config.personality, user_config.personality)
            scene_label = ChatScene.get(user_config.scene, user_config.scene)
            has_custom = "有" if (getattr(user_config, "custom_system_prompt", "") or "").strip() else "默认"
            self.style_tree.insert("", tk.END, values=(friend, style_name, scene_label, has_custom, "删除"))

    def on_style_tree_double_click(self, event):
        item = self.style_tree.identify_row(event.y)
        if not item:
            return
        col = self.style_tree.identify_column(event.x)
        if col != "#5":
            return
        values = self.style_tree.item(item, "values")
        if values:
            self.delete_friend_style(values[0])
