# 参考项目「AI 自动回复」快照（只读归档）

本目录由仓库根目录下的 **`AI自动回复/`** 参考项目复制而来，便于在删除原文件夹后仍能对照业务逻辑。**不是** Django 可导入包，路径 `src.*` 仅作阅读参考。

## 复制范围

- 已复制：`src/**/*.py`、`requirements.txt`。
- **未复制**：`.venv/`、`__pycache__/`、`.idea/`、**`yolo_moder/`**（训练工程，按约定不纳入）。
- **未复制**：根目录 `config.json` / `monitor_list.json` / `chat_history/` / `logs/`（含个人化配置与记录；若需结构请见下方 `config.example.json`）。

## 与 Flowly 主线的关系

- **Flowly 已实现**：**Vue** 单页「AI 自动回复」（**不使用**原参考项目里的 Tkinter 桌面 UI）、`/api/auto-reply/*`、规则与任务**入库**、人格/情景键与 `presets` 对齐、Celery/子进程执行等（见 `Backend/ai_engine/auto_reply*`、`Frontend/src/views/AutoReplyView.vue`）。
- **屏幕监控配置**：区域坐标与 `monitored_friends` 等由 **`GET/PUT /api/auto-reply/screen-profile`** 存库；本机代理 **`python -m ai_engine.desktop_screen_agent`**（`Backend/ai_engine/desktop_screen_agent/`）拉配置、可选 YOLO 检测、**`POST /api/auto-reply/screen-events`** 上报心跳；详细见该目录下 `README.md`。
- **OCR 子进程**：设置 **`FLOWLY_SCREEN_OCR_SUBPROCESS=1`** 后，代理在子进程中 **`import src.core.ocr`** 并调用 `ocr_user_area` / `ocr_chat_window` / `ocr_input_area`（见 Flowly 包内 `ocr_reference_worker.py` + `ocr_subprocess.py`）。参考快照内 **`constants.py`** 已改为：无 `best.pt` 时不阻塞导入（便于仅跑 OCR）；若仍要跑参考里的 `monitor.py`，请放置权重或设置环境变量 **`FLOWLY_REF_YOLO_WEIGHTS`**。
- **Django 配置**：已收敛为模块化包 **`Backend/flowly_backend/settings/`**（入口仍为 `flowly_backend.settings`）；前端开发代理集中在 **`Frontend/src/config/vite-dev-proxy.ts`**。
- **本快照保留**：原桌面端逻辑，例如：
  - `src/core/api/ai_client.py`：豆包 OpenAPI 风格 `chat/completions`、人格/情景 `ChatPersonality` / `ChatScene`、参考资料拼进 system。
  - `src/core/logic/ai_decision.py`：是否触发 AI（消息变化 + 非空 + 计数阈值）。
  - `src/core/sender.py`：`pyautogui` + 剪贴板发消息（仅桌面自动化场景）。
  - `src/core/monitor.py`：**依赖 YOLO 权重 `best.pt`** 做区域检测；与 `yolo_moder` 训练代码分离，但运行监控仍需要权重文件。

## 安全说明

- `src/config/constants.py` 在入库时已**删除原硬编码 API Key**，改为仅从环境变量读取；若你本地仍保留旧目录，请**轮换已泄露的密钥**。
- 运行本参考代码前请自行配置：`DOUBAO_API_KEY` / `ARK_API_KEY`、`DOUBAO_ENDPOINT_ID`（或 `ARK_ENDPOINT_ID`）。**`best.pt`**：跑参考 `monitor.py` 时仍需要权重；仅被 Flowly 以子进程方式 import `ocr.py` 时，可在参考根不放置 `best.pt`（见上方「OCR 子进程」说明）。

## 目录结构（快照）

```
docs/reference/AI自动回复/
├── README.md                 # 本说明
├── requirements.txt          # 原项目顶层依赖（极简；实际还依赖 torch/ultralytics/pyautogui 等，以你原环境为准）
├── config.example.json       # 配置结构示例（无真实数据）
└── src/
    ├── config/
    ├── core/
    └── gui/
```

删除仓库根目录 **`AI自动回复/`** 前，请确认本 `docs/reference/AI自动回复/` 已提交或已备份你仍需要的文件。
