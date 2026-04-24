# Prompt Enhancement + Graph Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a prompt-enhancement (“AI 加工”) feature with model switching, and enforce strict workflow graph validation on save, persisting both enhancement records and validation results to the database.

**Architecture:** Implement a small “prompt-tools” API surface in the Django backend that (1) exposes configured model routes/default models and (2) generates enhancement candidates using the existing `get_chat_model` factory. Add a backend validator for `Workflow.definition` and enforce it in workflow create/update endpoints before writing to DB. Extend the Vue workflow editor inspector to open a modal for enhancement and apply results back into the node config field being edited.

**Tech Stack:** Django + Django Ninja, Django ORM migrations, Vue 3 + Element Plus, Pinia, existing `ai_engine.workflow.get_chat_model`.

---

## File map (what changes where)

### Backend (Django)
- Create: `Backend/ai_engine/prompt_tools_api.py`
- Modify: `Backend/ai_engine/urls.py` (register router)
- Modify: `Backend/ai_engine/models.py` (new models: `PromptEnhancementRecord`, `WorkflowGraphValidation`)
- Create: `Backend/ai_engine/migrations/00xx_prompt_enhancement_and_validation.py`
- Create: `Backend/ai_engine/workflow_graph/validator.py` (strict definition validator)
- Modify: `Backend/ai_engine/workflows.py` (validate before save; persist validation result)
- (Optional) Create/Modify: `Backend/ai_engine/tests/test_workflow_definition_validation.py`
- (Optional) Modify: `Backend/ai_engine/tests/test_canvas_and_registry.py` (add coverage for ut_* ownership checks if needed)

### Frontend (Vue)
- Modify: `Frontend/src/components/WorkflowEditor.vue` (add “AI 加工” button + modal wiring)
- Create: `Frontend/src/components/prompt/PromptEnhanceModal.vue`
- Modify: `Frontend/src/utils/api.ts` or existing API wrapper usage (add typed calls if project has a typed layer)
- Modify: `Frontend/src/types/workflow-editor.ts` (optional: type the enhancement field names)

---

### Task 1: Add backend models + migrations (DB persistence)

**Files:**
- Modify: `Backend/ai_engine/models.py`
- Create: `Backend/ai_engine/migrations/00xx_prompt_enhancement_and_validation.py`

- [ ] **Step 1: Write failing tests for new models (optional but recommended)**

Create a test file and assert the models can be created and store JSON fields.

- [ ] **Step 2: Implement `PromptEnhancementRecord` model**

Fields:
- user (FK)
- workflow (FK nullable)
- client_node_id (nullable, len 128)
- node_type (nullable, len 64)
- field (len 64)
- raw_prompt (Text)
- instruction (Text blank)
- candidates (JSON list)
- suggested_text (Text blank)
- selected_text (Text blank)
- provider_route (len 32)
- model (len 128)
- temperature (Float null)
- max_tokens (Int null)
- created_at (auto)

- [ ] **Step 3: Implement `WorkflowGraphValidation` model**

Fields:
- workflow (FK, unique=True for “latest record” semantics)
- is_valid (Bool)
- errors (JSON list)
- validated_at (auto_now)

- [ ] **Step 4: Create and run migrations**

Run: `python manage.py makemigrations ai_engine`  
Run: `python manage.py migrate`

- [ ] **Step 5: Commit**

```bash
git add Backend/ai_engine/models.py Backend/ai_engine/migrations
git commit -m "feat: persist prompt enhancement and graph validation records"
```

---

### Task 2: Implement strict workflow definition validator

**Files:**
- Create: `Backend/ai_engine/workflow_graph/validator.py`
- Modify: `Backend/ai_engine/workflows.py`
- Test: `Backend/ai_engine/tests/test_workflow_definition_validation.py`

- [ ] **Step 1: Write failing tests for invalid definitions**

Test cases:
- empty nodes
- duplicate node ids
- edge references missing node
- invalid port handle for condition/human_approval
- invalid node type (unknown)

- [ ] **Step 2: Implement `validate_workflow_definition(definition, *, user_id)`**

Return shape (example):
```python
{
  "ok": False,
  "errors": [
    {"path": "nodes[0].id", "code": "required", "message": "..."},
    {"path": "edges[1].sourceNodeId", "code": "dangling_ref", "message": "..."},
  ],
}
```

Validation rules:
- `definition.nodes` is non-empty list of dicts with `id`, `type`, `label`
- Node id uniqueness and length
- Node type allowed:
  - builtin: `chat/tool/condition/human_approval/parallel/text/image/audio/video`
  - or `ut_<digits>` where the referenced `UserCustomNodeType` exists and belongs to the user
- `definition.edges` list of dicts with `id`, `sourceNodeId`, `targetNodeId`, `sourcePortId`, `targetPortId`
- Edge id uniqueness
- All node references exist
- Handle rules:
  - default: target handle must be `"in"`; source must be `"out"`
  - `condition` source may be `"true"`/`"false"`; target must be `"in"`
  - `human_approval` source may be `"approved"`/`"rejected"`; target must be `"in"`

- [ ] **Step 3: Enforce validation in `create_workflow` and `update_workflow`**

Before saving:
- run validator
- if invalid: raise/return 400 with errors
- if valid: proceed with existing atomic transaction and `sync_workflow_graph_from_definition`
- upsert `WorkflowGraphValidation` to `is_valid=True, errors=[]`

- [ ] **Step 4: Commit**

```bash
git add Backend/ai_engine/workflow_graph/validator.py Backend/ai_engine/workflows.py Backend/ai_engine/tests
git commit -m "feat: validate workflow definition strictly on save"
```

---

### Task 3: Add backend APIs: model listing + prompt enhance

**Files:**
- Create: `Backend/ai_engine/prompt_tools_api.py`
- Modify: `Backend/ai_engine/urls.py`
- Test: `Backend/ai_engine/tests/test_prompt_tools_api.py`

- [ ] **Step 1: Implement `GET /api/ai/models`**

Implementation:
- call `get_ai_provider_settings()`
- assemble routes present + default model/base_url
- return JSON

- [ ] **Step 2: Implement `POST /api/prompt-tools/enhance`**

Implementation:
- auth required
- validate payload (raw_prompt min length, max length)
- build a system prompt that instructs the model to output 3 candidates as JSON array
- call `get_chat_model(provider_route, model=model, temperature=..., max_tokens=...)`
- parse response robustly (fallback: treat as single candidate)
- create `PromptEnhancementRecord`
- return `record_id`, candidates, suggested, used provider/model

- [ ] **Step 3: Wire router into `ai_engine/urls.py`**

- [ ] **Step 4: Commit**

```bash
git add Backend/ai_engine/prompt_tools_api.py Backend/ai_engine/urls.py Backend/ai_engine/tests
git commit -m "feat: add prompt enhancement and model catalog APIs"
```

---

### Task 4: Frontend “AI 加工” modal + apply-back to node config

**Files:**
- Create: `Frontend/src/components/prompt/PromptEnhanceModal.vue`
- Modify: `Frontend/src/components/WorkflowEditor.vue`

- [ ] **Step 1: Build modal UI**

Modal controls:
- model route select + model select (populated from `GET /api/ai/models`)
- textarea raw prompt (pre-filled from current field)
- textarea instruction
- generate button
- candidates list (radio)
- confirm/cancel

- [ ] **Step 2: Wire API calls**

On open:
- fetch models once (cache in component)

On generate:
- call `POST /api/prompt-tools/enhance`
- show candidates and preselect suggested

On confirm:
- update `inspectorConfig` for the correct field and call existing `updateNodeConfig()`

- [ ] **Step 3: Add “AI 加工” buttons next to prompt fields**

At least:
- chat.systemPrompt
- text.prompt
- image.captionPrompt
- audio.systemPrompt
- video.systemPrompt

The button should open the modal with `(nodeId, fieldName, currentValue, nodeType)` context.

- [ ] **Step 4: Commit**

```bash
git add Frontend/src/components/WorkflowEditor.vue Frontend/src/components/prompt/PromptEnhanceModal.vue
git commit -m "feat: add AI prompt enhancement modal in workflow editor"
```

---

### Task 5: End-to-end verification (manual + targeted automated)

**Files:**
- Test: backend tests already added

- [ ] **Step 1: Backend unit tests**

Run: `pytest Backend/ai_engine/tests -q` (or project’s test runner)

- [ ] **Step 2: Manual smoke**

Steps:
- open editor, edit a node prompt, click AI 加工, switch model, generate, re-generate, confirm, save workflow
- try saving with a broken edge payload (e.g. invalid handle) using devtools / request replay; confirm server blocks with errors

- [ ] **Step 3: Commit (if any fixes)**

```bash
git add -A
git commit -m "test: cover prompt tools and validation" || true
```

---

## Self-review (plan)

- Spec coverage:
  - prompt enhancement UI + model switching: Task 3 + Task 4
  - node-level model switching: already in node configs; editor uses backend-provided list (Task 4 + Task 3)
  - strict graph validation + block save: Task 2
  - persistence: Task 1
- Placeholder scan: none
- Type consistency: backend returns provider_route/model; frontend uses same keys

---

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-22-prompt-enhancement-and-graph-validation.md`. Two execution options:

**1. Subagent-Driven (recommended)** - Dispatch a fresh subagent per task  
**2. Inline Execution** - Execute tasks in this session using executing-plans

Which approach?
