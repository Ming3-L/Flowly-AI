# 本机屏幕代理（Windows）

与参考桌面项目一致：周期性截屏，可选 **Ultralytics YOLO** 识别聊天窗口子区域；将检测结果以 **heartbeat** 上报到 Flowly `POST /api/auto-reply/screen-events`。

可选：通过**子进程**调用仓库内参考快照里的 **`src/core/ocr.py`**（OpenOCR），在同一轮心跳的 payload 里附带 `ocr` 字段（用户名、聊天区预览、输入框预览等），失败时额外上报 **`ocr_error`** 事件。

## 依赖

**推荐（国内镜像 + GPU 版 PyTorch）**：在项目根目录执行 PowerShell：

```powershell
.\.venv\Scripts\powershell.exe -ExecutionPolicy Bypass -File Backend\scripts\install_desktop_agent_gpu_cn.ps1
# 若需 CUDA 12.4 轮子：加参数 -Cuda cu124
```

`torch` 需从 `https://download.pytorch.org/whl/cu118|cu121|cu124` 安装才能用 GPU；其余包走清华镜像。仅 CPU 时可自行 `pip install torch` 后 `pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r Backend/requirements-desktop-agent.txt`。

若启用 OCR 子进程，请再安装与参考实现一致的 OpenOCR（见 `desktop_screen_agent/ocr_reference_bundle/requirements.txt` 中的 `openocr-python`）。

## 环境变量

| 变量 | 说明 |
|------|------|
| `FLOWLY_API_BASE` | API 根，如 `http://127.0.0.1:8000/api` |
| `FLOWLY_ACCESS_TOKEN` | 登录后获得的 JWT |
| `FLOWLY_SCREEN_YOLO_WEIGHTS` | （可选）`best.pt` 等权重绝对路径；不填时默认使用 `Backend/ai_engine/desktop_screen_agent/weights/best.pt`（若存在） |
| `FLOWLY_SCREEN_YOLO_TOLERANCE_PX` | （可选）坐标容差，默认 20 |
| `FLOWLY_SCREEN_OCR_SUBPROCESS` | 设为 `1` / `true` 时，每轮在子进程中跑参考 OCR（需已安装 openocr，且参考根有效） |
| `FLOWLY_OCR_REFERENCE_ROOT` | 参考项目根（含 `src/`）。默认：`Backend/ai_engine/desktop_screen_agent/ocr_reference_bundle` |
| `FLOWLY_OCR_PYTHON` | 子进程 Python（默认当前解释器）；可为单独 venv 的 `python.exe` |
| `FLOWLY_OCR_SUBPROCESS_TIMEOUT` | OCR 子进程超时秒数，默认 120 |
| `FLOWLY_SCREEN_SEND_KEY` | （仅后端内置屏幕代理发送）发送快捷键：`enter`（默认）或 `ctrl_enter`（微信设置为 Ctrl+Enter 发送时用） |

## 启动

在仓库 **Backend** 目录（含 `manage.py` 的同级）执行：

**PowerShell（仅区域检测 + 心跳）**

```powershell
cd D:\project\Flowly-AI\Backend
$env:FLOWLY_API_BASE="http://127.0.0.1:8000/api"
$env:FLOWLY_ACCESS_TOKEN="你的JWT"
$env:FLOWLY_SCREEN_YOLO_WEIGHTS="D:\project\Flowly-AI\Backend\ai_engine\desktop_screen_agent\weights\best.pt"
# 建议使用项目根目录 .venv 的解释器运行（确保 ultralytics/torch 等已安装在正确环境）
D:\project\Flowly-AI\.venv\Scripts\python.exe -m ai_engine.desktop_screen_agent
```

**附加参考 OCR 子进程（同一解释器需能 import openocr，或设置 FLOWLY_OCR_PYTHON）**

```powershell
$env:FLOWLY_SCREEN_OCR_SUBPROCESS="1"
# 若参考目录不在仓库默认路径：
# $env:FLOWLY_OCR_REFERENCE_ROOT="E:\桌面\project\AI自动回复"
D:\project\Flowly-AI\.venv\Scripts\python.exe -m ai_engine.desktop_screen_agent
```

## 子进程协议

- 父进程：`ocr_subprocess.run_ocr_subprocess(op, image_path=..., box=(x1,y1,x2,y2))`
- 子进程入口：`ocr_reference_worker.py`（由父进程自动调用），通过临时 JSON 传参、写回结果 JSON。
- 支持 `op`：`user_area`、`chat_window`、`input_area`、`friend_list`、`all_area`（与参考模块函数一一对应）。

## 配置来源

在 Web 端「AI 自动回复」→ **屏幕监控配置** 保存后，代理下次轮询即可拉到最新坐标与选项。
