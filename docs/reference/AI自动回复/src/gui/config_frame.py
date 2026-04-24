import tkinter as tk
from tkinter import ttk, messagebox
from src.config import config_manager as cfg
from src.config.constants import CHAT_SOFTWARE


class ConfigFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        """初始化配置选项标签页"""
        # 聊天软件选择
        software_frame = ttk.LabelFrame(self, text="聊天软件")
        software_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(software_frame, text="选择聊天软件：").pack(side=tk.LEFT, padx=10, pady=5)
        self.software_var = tk.StringVar(
            value=CHAT_SOFTWARE.get(cfg.current_chat_software, cfg.current_chat_software)
        )
        software_combo = ttk.Combobox(
            software_frame,
            textvariable=self.software_var,
            values=list(CHAT_SOFTWARE.values()),
            width=10,
            state="readonly",
        )
        software_combo.pack(side=tk.LEFT, padx=10, pady=5)
        
        # 聊天窗口坐标设置
        window_frame = ttk.LabelFrame(self, text="聊天窗口坐标")
        window_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(
            window_frame,
            text="聊天区域 (x1, y1, x2, y2，与「更新聊天窗口」识别结果一致)：",
        ).grid(row=0, column=0, padx=10, pady=5, sticky=tk.W)
        # 直接读取 cfg.chat_window_box
        self.window_x_var = tk.StringVar(value=str(cfg.chat_window_box[0]))
        self.window_y_var = tk.StringVar(value=str(cfg.chat_window_box[1]))
        self.window_width_var = tk.StringVar(value=str(cfg.chat_window_box[2]))
        self.window_height_var = tk.StringVar(value=str(cfg.chat_window_box[3]))
        
        ttk.Entry(window_frame, textvariable=self.window_x_var, width=10).grid(row=0, column=1, padx=5, pady=5)
        ttk.Entry(window_frame, textvariable=self.window_y_var, width=10).grid(row=0, column=2, padx=5, pady=5)
        ttk.Entry(window_frame, textvariable=self.window_width_var, width=10).grid(row=0, column=3, padx=5, pady=5)
        ttk.Entry(window_frame, textvariable=self.window_height_var, width=10).grid(row=0, column=4, padx=5, pady=5)

        # 用户名区域坐标
        user_frame = ttk.LabelFrame(self, text="用户名区域坐标（手动填写，模型失效时用于回退）")
        user_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(user_frame, text="用户名区域 (x1, y1, x2, y2)：").grid(row=0, column=0, padx=10, pady=5, sticky=tk.W)
        ub = cfg.user_name_box
        self.user_x1_var = tk.StringVar(value=str(ub[0]) if ub else "")
        self.user_y1_var = tk.StringVar(value=str(ub[1]) if ub else "")
        self.user_x2_var = tk.StringVar(value=str(ub[2]) if ub else "")
        self.user_y2_var = tk.StringVar(value=str(ub[3]) if ub else "")
        ttk.Entry(user_frame, textvariable=self.user_x1_var, width=10).grid(row=0, column=1, padx=5, pady=5)
        ttk.Entry(user_frame, textvariable=self.user_y1_var, width=10).grid(row=0, column=2, padx=5, pady=5)
        ttk.Entry(user_frame, textvariable=self.user_x2_var, width=10).grid(row=0, column=3, padx=5, pady=5)
        ttk.Entry(user_frame, textvariable=self.user_y2_var, width=10).grid(row=0, column=4, padx=5, pady=5)

        # 好友列表区域坐标
        friend_frame = ttk.LabelFrame(self, text="好友列表区域坐标（手动填写，模型失效时用于回退）")
        friend_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(friend_frame, text="好友列表区域 (x1, y1, x2, y2)：").grid(row=0, column=0, padx=10, pady=5, sticky=tk.W)
        fb = cfg.friend_list_box
        self.friend_x1_var = tk.StringVar(value=str(fb[0]) if fb else "")
        self.friend_y1_var = tk.StringVar(value=str(fb[1]) if fb else "")
        self.friend_x2_var = tk.StringVar(value=str(fb[2]) if fb else "")
        self.friend_y2_var = tk.StringVar(value=str(fb[3]) if fb else "")
        ttk.Entry(friend_frame, textvariable=self.friend_x1_var, width=10).grid(row=0, column=1, padx=5, pady=5)
        ttk.Entry(friend_frame, textvariable=self.friend_y1_var, width=10).grid(row=0, column=2, padx=5, pady=5)
        ttk.Entry(friend_frame, textvariable=self.friend_x2_var, width=10).grid(row=0, column=3, padx=5, pady=5)
        ttk.Entry(friend_frame, textvariable=self.friend_y2_var, width=10).grid(row=0, column=4, padx=5, pady=5)
        
        # 输入框坐标设置
        input_frame = ttk.LabelFrame(self, text="输入框坐标")
        input_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(input_frame, text="输入框区域 (x1, y1, x2, y2)：").grid(row=0, column=0, padx=10, pady=5, sticky=tk.W)
        ib = cfg.input_box_pos
        self.input_x_var = tk.StringVar(value=str(ib[0]))
        self.input_y_var = tk.StringVar(value=str(ib[1]))
        self.input_x2_var = tk.StringVar(value=str(ib[2]))
        self.input_y2_var = tk.StringVar(value=str(ib[3]))
        
        ttk.Entry(input_frame, textvariable=self.input_x_var, width=10).grid(row=0, column=1, padx=5, pady=5)
        ttk.Entry(input_frame, textvariable=self.input_y_var, width=10).grid(row=0, column=2, padx=5, pady=5)
        ttk.Entry(input_frame, textvariable=self.input_x2_var, width=10).grid(row=0, column=3, padx=5, pady=5)
        ttk.Entry(input_frame, textvariable=self.input_y2_var, width=10).grid(row=0, column=4, padx=5, pady=5)
        
        # 保存按钮
        save_btn = ttk.Button(self, text="保存配置", command=self.save_config)
        save_btn.pack(pady=10)
        
        # 更新聊天窗口按钮
        update_window_btn = ttk.Button(self, text="更新聊天窗口", command=self.update_chat_window)
        update_window_btn.pack(pady=5)
    
    def _software_key_from_var(self):
        label = self.software_var.get().strip()
        for key, name in CHAT_SOFTWARE.items():
            if name == label or key == label:
                return key
        return "wechat"

    def save_config(self):
        """保存配置"""
        cfg.current_chat_software = self._software_key_from_var()
        
        try:
            window_x = int(self.window_x_var.get())
            window_y = int(self.window_y_var.get())
            window_width = int(self.window_width_var.get())
            window_height = int(self.window_height_var.get())
            cfg.chat_window_box = (window_x, window_y, window_width, window_height)

            # 手动区域（允许为空则不写）
            ux1 = self.user_x1_var.get().strip()
            uy1 = self.user_y1_var.get().strip()
            ux2 = self.user_x2_var.get().strip()
            uy2 = self.user_y2_var.get().strip()
            if ux1 and uy1 and ux2 and uy2:
                cfg.user_name_box = (int(ux1), int(uy1), int(ux2), int(uy2))
            else:
                cfg.user_name_box = None

            fx1 = self.friend_x1_var.get().strip()
            fy1 = self.friend_y1_var.get().strip()
            fx2 = self.friend_x2_var.get().strip()
            fy2 = self.friend_y2_var.get().strip()
            if fx1 and fy1 and fx2 and fy2:
                cfg.friend_list_box = (int(fx1), int(fy1), int(fx2), int(fy2))
            else:
                cfg.friend_list_box = None

            input_x1 = int(self.input_x_var.get())
            input_y1 = int(self.input_y_var.get())
            input_x2 = int(self.input_x2_var.get())
            input_y2 = int(self.input_y2_var.get())
            cfg.input_box_pos = (input_x1, input_y1, input_x2, input_y2)
            
            if cfg.save_config():
                messagebox.showinfo("成功", "配置保存成功！")
            else:
                messagebox.showerror("错误", "配置保存失败！")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字！")
    
    def update_chat_window(self):
        """更新聊天窗口坐标"""
        # 识别聊天窗口
        from src.core.monitor import get_chat_areas
        areas, message = get_chat_areas()
        if areas:
            # 更新全局变量
            cfg.chat_window_box = areas["chat_area"]
            cfg.input_box_pos = areas["input_box"]
            cfg.user_name_box = areas["user_object"]
            cfg.friend_list_box = areas["friend_list"]
        else:
            messagebox.showerror("错误", f"识别聊天窗口失败：{message}")
            return
        # 更新UI
        self.window_x_var.set(str(cfg.chat_window_box[0]))
        self.window_y_var.set(str(cfg.chat_window_box[1]))
        self.window_width_var.set(str(cfg.chat_window_box[2]))
        self.window_height_var.set(str(cfg.chat_window_box[3]))
        self.input_x_var.set(str(cfg.input_box_pos[0]))
        self.input_y_var.set(str(cfg.input_box_pos[1]))
        self.input_x2_var.set(str(cfg.input_box_pos[2]))
        self.input_y2_var.set(str(cfg.input_box_pos[3]))
        self.user_x1_var.set(str(cfg.user_name_box[0]))
        self.user_y1_var.set(str(cfg.user_name_box[1]))
        self.user_x2_var.set(str(cfg.user_name_box[2]))
        self.user_y2_var.set(str(cfg.user_name_box[3]))
        self.friend_x1_var.set(str(cfg.friend_list_box[0]))
        self.friend_y1_var.set(str(cfg.friend_list_box[1]))
        self.friend_x2_var.set(str(cfg.friend_list_box[2]))
        self.friend_y2_var.set(str(cfg.friend_list_box[3]))
        # 保存配置
        cfg.save_config()
        messagebox.showinfo("成功", "聊天窗口更新成功！")
