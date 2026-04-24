# 工作流提示词加工 + 节点结构校验（方案 A）设计稿

**日期**：2026-04-22  
**范围**：Flowly-AI（Backend Django + Frontend Vue3）

## 背景与目标

在工作流编辑器中，用户在编辑节点提示词时，希望通过 AI 对提示词进行“加工/优化”，并可切换项目内已支持的模型。用户满意后确认回填，不满意可重试或取消。

同时，工作流保存时需要对节点/边结构进行严格校验（ID、类型、端口连线、输入输出等），校验失败需阻止保存；校验结果与提示词加工记录均需落库，便于审计与追踪。

## 现状（已存在能力）

- **工作流定义**：`ai_engine.models.Workflow.definition`（JSON）为权威快照；保存时同步写入规范化镜像表：
  - `ai_engine.models.WorkflowGraphNode`（节点行，含 `client_node_id/node_type/title/config`）
  - `ai_engine.models.WorkflowGraphEdge`（边行，含 source/target/handle）
  - 同步逻辑：`ai_engine.workflow_graph.definition_sync.sync_workflow_graph_from_definition`
- **节点执行**：`ai_engine.workflow_nodes.registry.resolve_node_executor` + `workflow_nodes/types/*`
- **节点配置中已包含 provider/model 字段**（例如 `AIChatNodeExecutor` 使用 `config.provider/config.model` 调用 `workflow.get_chat_model`）
- **模型工厂**：`ai_engine.workflow.get_chat_model(route, model=..., temperature=..., max_tokens=...)`，route 支持 `openai/doubao/claude/ollama/vectorengine`

## 用户交互设计（前端）

### 1) “提示词加工”入口

在 `WorkflowEditor.vue` 的节点属性面板中，对包含提示词编辑的字段（如 `systemPrompt/prompt/captionPrompt/...`）旁新增按钮：

- 按钮文案：`AI 加工`
- 点击打开悬浮窗（弹窗）

### 2) 悬浮窗能力

- **模型选择**：从后端动态拉取可用 provider/model（详见后端接口）
- **输入区**：
  - 原提示词（默认带入当前字段内容，可编辑）
  - 加工要求（可选）
- **生成**：请求后端生成候选（可多条）
- **结果区**：
  - 候选列表（可选中其一）
  - `重新生成`（可更改模型/原文/要求后再生成）
- **确认/取消**：
  - 确认：将选中候选回填到当前字段（本次编辑更改计入“未保存变更”）
  - 取消：不更改字段

## 后端设计

### 1) 模型目录查询（只读）

新增接口：

- `GET /api/ai/models`

目标：前端获取“当前项目可用的 provider/model 选择项”，来源为 `ai_engine.integrations.get_ai_provider_settings()`（环境变量 + `project_secrets_local`）。

响应建议结构（示意）：

```json
{
  "providers": [
    {
      "route": "openai",
      "default_model": "gpt-4o",
      "base_url": "https://api.openai.com/v1",
      "available_models": ["gpt-4o", "gpt-4o-mini"]
    },
    {
      "route": "doubao",
      "default_model": "ep-xxxxx",
      "base_url": "https://ark.cn-beijing.volces.com/api/v3",
      "available_models": ["ep-xxxxx"]
    }
  ]
}
```

注：`available_models` 初期允许只返回默认值，后续再扩展为更丰富的候选列表。

### 2) 提示词加工服务

新增接口：

- `POST /api/prompt-tools/enhance`

请求字段（建议）：
- `workflow_id?: number`
- `client_node_id?: string`（画布节点 id，用于审计）
- `node_type?: string`
- `field: string`（例如 `systemPrompt` / `prompt` / `captionPrompt`）
- `raw_prompt: string`
- `instruction?: string`（用户额外要求）
- `provider_route: string`（如 `openai/doubao/claude/ollama/vectorengine`）
- `model: string`
- `temperature?: number`
- `max_tokens?: number`

响应字段（建议）：
- `record_id: number`（本次加工记录主键）
- `candidates: string[]`
- `suggested: string`
- `used_provider_route: string`
- `used_model: string`

生成策略（最小闭环）：
- 固定生成 3 条候选（不同风格：简洁/结构化/更强约束），并标出 `suggested` 为第一条。
- 对超长输入做长度限制与错误提示。

安全约束：
- 不在任何 DB `config` 字段内存放密钥
- 请求只接受本项目支持的 route；`model` 为字符串透传给 `get_chat_model`（由各 provider 的 SDK/网关自行校验）

### 3) 落库（审计与追踪）

新增模型（建议）：

#### `PromptEnhancementRecord`
- `user`（外键）
- `workflow`（可空外键）
- `client_node_id`（可空）
- `node_type`（可空）
- `field`
- `raw_prompt`
- `instruction`（可空）
- `candidates`（JSON）
- `selected_text`（可空；前端若确认某条候选，可再调用一个“确认”接口回写）
- `provider_route`、`model`、`temperature`、`max_tokens`
- `created_at`

#### `WorkflowGraphValidation`
用于保存时记录校验结果（阻止保存时仍可写一条“失败记录”到该表，或仅在成功保存后写“成功记录”；本期建议：成功保存后写 success，失败则不写或写入独立日志表，二选一在实现计划中明确）。

字段建议：
- `workflow`（外键，建议一对一最新记录）
- `is_valid: bool`
- `errors: JSON`
- `validated_at`

### 4) 保存工作流时的严格结构校验

在 `ai_engine.workflows` 的 `create_workflow/update_workflow` 中，在写入 `Workflow.definition` 前执行校验：

- **节点**：
  - `nodes` 必须是数组且非空
  - `nodes[].id` 非空、长度合理、同一 workflow 内唯一
  - `nodes[].type` 必须是内置类型或 `ut_<id>`（并校验该 `UserCustomNodeType` 对当前用户可见）
  - `nodes[].label` 非空（严格模式）
- **边**：
  - `edges[].id` 唯一
  - `sourceNodeId/targetNodeId` 必须引用存在节点
  - 端口合法性（按节点类型定义允许的 source/target handle 集）
  - 禁止自环（可选；前端已防，但后端仍兜底）

校验失败：
- HTTP 返回 400（或 422），携带 `errors[]`（可定位到 node/edge）
- **阻止保存**（事务不写 Workflow、不写 graph 镜像）

校验成功：
- 继续现有事务：保存 `Workflow` + `sync_workflow_graph_from_definition`
- 可选：写 `WorkflowGraphValidation(is_valid=True, errors=[])`

## 非目标（本期不做）

- 模型目录完整管理后台（上下线、排序、别名、权限）
- 将“加工后的提示词”做为运行时优先字段（如 `promptEnhanced`）并改变执行逻辑（本期只回填原字段）
- 对提示词内容做敏感信息检测/脱敏（可后续扩展）

## 验收标准（Definition of Done）

- 编辑器内任一支持提示词字段可打开“AI 加工”弹窗，能切换模型、生成候选、反复生成、确认回填、取消不改。
- 模型列表来自后端接口，随配置变化而变化。
- 保存工作流时，后端对节点/边结构做严格校验，失败时阻止保存并返回可读错误。
- 每次提示词加工请求均落库可追踪（包含使用的模型与候选结果）。
