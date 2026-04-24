import os
import subprocess
import sys
import tkinter as tk
from tkinter import ttk, messagebox

from src.config import config_manager as cfg
from src.config.constants import KNOWLEDGE_ROOT
from src.core.knowledge_loader import ensure_knowledge_dirs


class KnowledgeFrame(ttk.Frame):
    """本地资料库：默认不合并资料；在此页「应用」开启后，且对方消息命中关键词时才注入 AI。"""

    def __init__(self, parent):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        switch = ttk.LabelFrame(self, text="资料库与回复合并（默认关闭）")
        switch.pack(fill=tk.X, padx=10, pady=(8, 4))
        self.knowledge_reply_var = tk.BooleanVar(value=bool(cfg.knowledge_reply_enabled))
        srow = ttk.Frame(switch)
        srow.pack(fill=tk.X, padx=8, pady=6)
        ttk.Checkbutton(
            srow,
            text="启用后：合并「聊天风格」里挂载的资料；若填写了触发关键词则仅命中时挂载，关键词留空则每条消息都挂载",
            variable=self.knowledge_reply_var,
        ).pack(side=tk.LEFT, anchor=tk.W)
        ttk.Button(srow, text="应用此设置", command=self._apply_knowledge_reply_setting).pack(
            side=tk.RIGHT, padx=(8, 0)
        )
        self._switch_status_var = tk.StringVar()
        self._update_switch_status()
        ttk.Label(switch, textvariable=self._switch_status_var, foreground="gray", wraplength=760).pack(
            anchor=tk.W, padx=8, pady=(0, 6)
        )

        top = ttk.LabelFrame(self, text="资料目录")
        top.pack(fill=tk.X, padx=10, pady=8)

        path_row = ttk.Frame(top)
        path_row.pack(fill=tk.X, padx=8, pady=6)
        ttk.Label(path_row, text="路径：", width=5).pack(side=tk.LEFT)
        self.path_var = tk.StringVar(value=KNOWLEDGE_ROOT)
        ttk.Entry(path_row, textvariable=self.path_var, state="readonly").pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8)
        )
        ttk.Button(path_row, text="打开文件夹", command=self._open_knowledge_folder).pack(
            side=tk.LEFT
        )
        ttk.Button(path_row, text="刷新列表", command=self._refresh_file_list).pack(
            side=tk.LEFT, padx=(6, 0)
        )

        hint = (
            "使用方式：\n"
            "0）必须先在上方点击「应用此设置」并勾选启用，才会按规则合并资料；否则与原先纯 AI 一致。\n"
            "1）在 knowledge/shared/ 下放入 .txt；项目内已带演示包，索引见 shared/demo_index.txt。\n"
            "2）在「聊天风格设置」里填写「挂载资料路径」；在「资料触发关键词」里每行一条子串——"
            "仅当对方消息包含其中任一词时才挂载；关键词留空则对每条消息都尝试挂载。\n"
            "3）可选：knowledge/friends/<好友名>.txt 专属资料，同样受总开关与关键词规则约束。"
        )
        ttk.Label(top, text=hint, wraplength=760, justify=tk.LEFT).pack(
            anchor=tk.W, padx=8, pady=(0, 8)
        )

        list_fr = ttk.LabelFrame(self, text="knowledge/shared 下的文件")
        list_fr.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)
        self.file_list = tk.Listbox(list_fr, height=14, font=("Consolas", 9))
        sb = ttk.Scrollbar(list_fr, orient=tk.VERTICAL, command=self.file_list.yview)
        self.file_list.configure(yscrollcommand=sb.set)
        self.file_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=6, pady=6)
        sb.pack(side=tk.RIGHT, fill=tk.Y, pady=6)

        self.refresh_files()

    def _update_switch_status(self):
        on = bool(cfg.knowledge_reply_enabled)
        self._switch_status_var.set(
            "当前已保存：已启用（命中规则时合并资料库）"
            if on
            else "当前已保存：未启用（不读资料库，与原先一致）"
        )

    def _apply_knowledge_reply_setting(self):
        cfg.knowledge_reply_enabled = bool(self.knowledge_reply_var.get())
        if cfg.save_config():
            self._update_switch_status()
            messagebox.showinfo("已保存", "资料库合并开关已写入配置。")
        else:
            messagebox.showerror("失败", "保存配置失败。")

    def refresh_state(self):
        """切换到此标签时从磁盘同步开关显示。"""
        self.knowledge_reply_var.set(bool(cfg.knowledge_reply_enabled))
        self._update_switch_status()

    def refresh_files(self):
        """刷新 shared 下列表（供主窗口切换标签时调用）。"""
        self._refresh_file_list()

    def _open_knowledge_folder(self):
        ensure_knowledge_dirs()
        path = KNOWLEDGE_ROOT
        try:
            if sys.platform == "win32":
                os.startfile(path)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.run(["open", path], check=False)
            else:
                subprocess.run(["xdg-open", path], check=False)
        except Exception:
            pass

    def _refresh_file_list(self):
        ensure_knowledge_dirs()
        self.file_list.delete(0, tk.END)
        shared = os.path.join(KNOWLEDGE_ROOT, "shared")
        if not os.path.isdir(shared):
            return
        names = []
        try:
            for fn in sorted(os.listdir(shared)):
                if fn.startswith("."):
                    continue
                fp = os.path.join(shared, fn)
                if os.path.isfile(fp):
                    names.append(f"shared/{fn}")
        except OSError:
            return
        for n in names:
            self.file_list.insert(tk.END, n)
