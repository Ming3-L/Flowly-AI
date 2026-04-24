import tkinter as tk
from tkinter import ttk
from src.gui.config_frame import ConfigFrame
from src.gui.style_frame import StyleFrame
from src.gui.knowledge_frame import KnowledgeFrame
from src.gui.monitor_frame import MonitorFrame
from src.config.config_manager import load_config
from src.core.knowledge_loader import ensure_knowledge_dirs


class MainWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("AI自动回复")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # 加载配置
        load_config()
        ensure_knowledge_dirs()

        # 创建标签页
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 配置选项标签页
        self.config_frame = ConfigFrame(self.notebook)
        self.notebook.add(self.config_frame, text="配置选项")
        
        # 聊天风格设置标签页
        self.style_frame = StyleFrame(self.notebook)
        self.notebook.add(self.style_frame, text="聊天风格设置")

        self.knowledge_frame = KnowledgeFrame(self.notebook)
        self.notebook.add(self.knowledge_frame, text="资料库")
        
        # 监控界面标签页
        self.monitor_frame = MonitorFrame(self.notebook)
        self.notebook.add(self.monitor_frame, text="监控界面")
        
        # 绑定标签页切换事件，确保监控页面总是显示最新的好友列表
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)
    
    def on_tab_changed(self, event):
        """标签页切换事件处理"""
        # 切换标签时刷新关键页面数据，避免“保存后需重启才能看到”
        self.style_frame.refresh_style_list()
        try:
            self.knowledge_frame.refresh_state()
            self.knowledge_frame.refresh_files()
        except Exception:
            pass
        self.monitor_frame.refresh_monitor_list()
