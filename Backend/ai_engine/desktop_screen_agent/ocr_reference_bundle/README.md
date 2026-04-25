# 屏幕 OCR 参考实现（随 Flowly 仓库提供）

本目录为原「AI 自动回复」桌面项目的 **Python 快照**（`src/**/*.py` 等），供 **本机屏幕代理** 在子进程中 `import src.core.ocr` 使用。**不是** Django 应用内可导入包；路径 `src.*` 仅由 `ocr_reference_worker.py` 在独立进程里加载。

## 位置

`Backend/ai_engine/desktop_screen_agent/ocr_reference_bundle/`

`FLOWLY_OCR_REFERENCE_ROOT` 未设置时，`ocr_subprocess.default_reference_root()` 指向此处。

## 复制范围（历史说明）

- 已纳入：`src/**/*.py`、`requirements.txt`、`config.example.json`。
- **未纳入**：`.venv/`、`__pycache__/`、**`yolo_moder/`**（训练工程）、个人化 `config.json` / `logs/` 等。

## 与 Flowly 主线的关系

- **Web 自动回复**：`/api/auto-reply/*`、`Frontend` 的「AI 自动回复」页、规则与任务入库等见 `ai_engine/auto_reply*`、`auto_reply_api.py`。
- **OCR 子进程**：`FLOWLY_SCREEN_OCR_SUBPROCESS=1` 时，由 `ocr_reference_worker.py` + `ocr_subprocess.py` 调用本目录下 **`constants.py`**（无 `best.pt` 时可不阻塞导入）、**`src/core/ocr.py`**（OpenOCR）。
- **本快照保留的桌面逻辑**（阅读 / 独立运行参考）：`ai_client.py`、`ai_decision.py`、`sender.py`、`monitor.py`（完整跑 `monitor.py` 仍可能需要 YOLO 权重）等。

## 安全说明

- `src/config/constants.py` 仅从环境变量读取密钥；勿将真实密钥提交仓库。
- 运行前按需配置：`DOUBAO_API_KEY` / `ARK_API_KEY`、`DOUBAO_ENDPOINT_ID`（或 `ARK_ENDPOINT_ID`）；OpenOCR 依赖见 `requirements.txt`。

## 目录结构

```
ocr_reference_bundle/
├── README.md
├── requirements.txt
├── config.example.json
└── src/
    ├── config/
    └── core/
```
