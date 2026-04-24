from django.contrib.auth.models import User
from django.db import models


# ─────────────────────────────────────────────────────────────────────────────
# AI 引擎模型
# ─────────────────────────────────────────────────────────────────────────────

class Workflow(models.Model):
    """表示一个 AI 工作流定义。"""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="flowly_workflows",
        null=True,
        blank=True,
        help_text="Owner of this workflow (null for system/global workflows)",
    )
    name = models.CharField(max_length=255, help_text="Workflow name")
    description = models.TextField(blank=True, help_text="Workflow description")
    definition = models.JSONField(help_text="Workflow definition in JSON format")
    is_active = models.BooleanField(default=True)
    # 软删除：被删除的工作流不应出现在列表中；
    # 但其执行记录/历史可按需保留，用于审计。
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class Thread(models.Model):
    """
    跟踪一次工作流会话（thread）。

    一个用户可拥有多个 thread；每个 thread 绑定且仅绑定一个工作流。
    thread_id（UUID）是 LangGraph checkpointer 用于持久化与恢复状态的主句柄。
    """

    thread_id = models.UUIDField(
        unique=True,
        editable=False,
        help_text="Unique thread ID used by LangGraph checkpointer",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="flowly_threads",
        null=True,
        blank=True,
        help_text="Owner of this thread (null for anonymous sessions)",
    )
    workflow = models.ForeignKey(
        Workflow,
        on_delete=models.SET_NULL,
        related_name="threads",
        null=True,
        blank=True,
        help_text="Workflow definition this thread uses",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Threads"

    def __str__(self):
        user_str = self.user.username if self.user else "anonymous"
        wf_name = self.workflow.name if self.workflow else "free-chat"
        return f"{wf_name} / {self.thread_id} ({user_str})"


class WorkflowExecution(models.Model):
    """表示一次工作流执行记录。"""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    workflow = models.ForeignKey(
        Workflow,
        on_delete=models.SET_NULL,
        related_name='executions',
        null=True,
        blank=True,
    )
    thread = models.ForeignKey(
        Thread,
        on_delete=models.CASCADE,
        related_name='executions',
        null=True,
        blank=True,
        help_text="Parent thread for this execution",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    input_data = models.JSONField(default=dict)
    output_data = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-started_at']
        verbose_name_plural = "Workflow executions"

    def __str__(self):
        wf_name = self.workflow.name if self.workflow else "free-chat"
        return f"{wf_name} - {self.thread_id}"

    @property
    def thread_id(self) -> str:
        """返回父 Thread 的 UUID 字符串（用于兼容旧字段/旧逻辑）。"""
        return str(self.thread.thread_id) if self.thread else ""


class WorkflowExecutionStep(models.Model):
    """
    单次执行中的节点级时间线：用于审计、前端「节点状态」回放与报表。

    与 ``WorkflowExecution.output_data.trace``（画布）互补：本表便于 SQL 查询与分页，
    不必解析 JSON。
    """

    class Status(models.TextChoices):
        RUNNING = "running", "运行中"
        COMPLETED = "completed", "已完成"
        FAILED = "failed", "失败"

    execution = models.ForeignKey(
        WorkflowExecution,
        on_delete=models.CASCADE,
        related_name="steps",
        verbose_name="所属执行",
    )
    node_key = models.CharField(
        "节点标识",
        max_length=255,
        db_index=True,
        help_text="画布 client_node_id 或 LangGraph 逻辑节点名。",
    )
    display_title = models.CharField(
        "展示标题",
        max_length=512,
        blank=True,
        help_text="画布节点 label 或可读标题。",
    )
    node_kind = models.CharField(
        "节点类型",
        max_length=64,
        blank=True,
        help_text="如 chat、router、tool_executor。",
    )
    activity = models.TextField(
        "当前在做什么",
        blank=True,
        help_text="面向用户的简短中文描述，如「使用 doubao 处理对话」。",
    )
    model_route = models.CharField(
        "模型路由",
        max_length=64,
        blank=True,
        help_text="与 get_chat_model 一致，如 doubao、openai。",
    )
    status = models.CharField(
        "状态",
        max_length=16,
        choices=Status.choices,
        default=Status.RUNNING,
    )
    started_at = models.DateTimeField("开始时间", auto_now_add=True)
    finished_at = models.DateTimeField("结束时间", null=True, blank=True)
    detail = models.JSONField("附加信息", default=dict, blank=True)

    class Meta:
        verbose_name = "工作流执行步骤"
        verbose_name_plural = "工作流执行步骤"
        ordering = ["execution_id", "id"]

    def __str__(self) -> str:
        return f"exec#{self.execution_id} {self.node_key} ({self.status})"


class UILabel(models.Model):
    """
    前后端分离场景下的界面文案：由管理员在后台维护，前端通过 ``GET /api/ui-labels`` 拉取。

    约定
    ----
    - ``key``：稳定英文点分路径，如 ``app.nav.home``、``wf.runner.submit``。
    - ``value``：面向最终用户的展示字符串（可为多行）。
    - ``locale``：如 ``zh-CN``；后续扩展多语言时同 key 多行记录。
    """

    key = models.CharField(
        "文案键",
        max_length=160,
        db_index=True,
        help_text="稳定唯一键，与前端 useUiLabels().t() 参数一致。",
    )
    locale = models.CharField(
        "语言区域",
        max_length=32,
        default="zh-CN",
        db_index=True,
        help_text="BCP 47，如 zh-CN、en-US。",
    )
    value = models.TextField(
        "展示文本",
        help_text="用户可见文案；支持换行（少数场景如多行提示）。",
    )
    category = models.CharField(
        "分组",
        max_length=64,
        default="general",
        blank=True,
        db_index=True,
        help_text="仅用于后台筛选，如 app、workflow、monitor。",
    )
    description = models.CharField(
        "管理员说明",
        max_length=255,
        blank=True,
        help_text="说明该键出现在哪个页面，勿写用户可见内容。",
    )
    is_active = models.BooleanField("启用", default=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        verbose_name = "界面文案"
        verbose_name_plural = "界面文案"
        ordering = ["locale", "category", "key"]
        constraints = [
            models.UniqueConstraint(
                fields=["locale", "key"],
                name="uniq_ai_engine_ui_label_locale_key",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.locale}:{self.key}"


# ─────────────────────────────────────────────────────────────────────────────
# 工作流画布规范化存储（与 DATABASE_URL 是否 mysql 无关；SQLite 亦可建相同表）
# 与 ``Workflow.definition`` JSON 双写时，注意 API 层事务与一致性策略。
# ─────────────────────────────────────────────────────────────────────────────


class WorkflowGraphNode(models.Model):
    """
    工作流编辑器中的「单个节点」在数据库中的一行记录。

    为何单独建表
    --------------
    ``Workflow.definition`` 适合整块读写与版本快照；本表便于按节点类型统计、
    SQL 过滤、与执行日志按 ``client_node_id`` 关联，而不必解析整棵 JSON。

    ``node_type`` 取值
    --------------------
    与前端 ``EditorNode.type`` 一致（如 ``chat``、``tool``），或用户自定义类型键
    ``ut_<UserCustomNodeType 主键>``（见 ``UserCustomNodeType``）。

    安全
    ----
    ``config`` 中**禁止**存放 API Key、refresh_token、用户身份证等敏感信息；
    密钥在运行时从 ``integrations.get_ai_provider_settings()`` 或密钥管理系统读取。
    """

    workflow = models.ForeignKey(
        Workflow,
        on_delete=models.CASCADE,
        related_name="graph_nodes",
        verbose_name="所属工作流",
        help_text="删除工作流时级联删除其下所有节点与边（见 WorkflowGraphEdge）。",
    )
    client_node_id = models.CharField(
        "前端节点 ID",
        max_length=128,
        help_text="与 Vue Flow 等编辑器中的 node.id 一致，在同一 workflow 内唯一。",
    )
    node_type = models.CharField(
        "节点类型",
        max_length=64,
        default="custom",
        db_index=True,
        help_text="内置类型或用户自定义 ut_<id>；由 ``workflow_nodes`` 注册表解析执行器。",
    )
    title = models.CharField(
        "显示标题",
        max_length=255,
        blank=True,
        help_text="画布上展示用，可不填；与业务主键无关。",
    )
    position_x = models.FloatField(
        "画布 X 坐标",
        default=0.0,
        help_text="编辑器坐标系下的水平位置，具体原点由前端约定。",
    )
    position_y = models.FloatField(
        "画布 Y 坐标",
        default=0.0,
        help_text="编辑器坐标系下的垂直位置。",
    )
    z_index = models.IntegerField(
        "叠放层级",
        default=0,
        help_text="节点重叠时的绘制顺序，数值越大越靠前。",
    )
    config = models.JSONField(
        "节点参数",
        default=dict,
        blank=True,
        help_text="非敏感配置 JSON：如 temperature、模板名、端口开关等；勿存密钥。",
    )
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        verbose_name = "工作流图节点"
        verbose_name_plural = "工作流图节点"
        ordering = ["workflow_id", "client_node_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["workflow", "client_node_id"],
                name="uniq_ai_engine_workflow_client_node",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.workflow_id}:{self.client_node_id} ({self.node_type})"


class WorkflowGraphEdge(models.Model):
    """
    有向边：描述「从哪个节点的哪个端口连到哪个节点」。

    与 JSON 定义的关系
    ------------------
    边的语义应与 ``Workflow.definition`` 中 edges 数组一致；若不一致，以业务规则
    约定准（例如「规范化表为准，JSON 为导出缓存」），并在保存 API 中单事务更新。
    """

    workflow = models.ForeignKey(
        Workflow,
        on_delete=models.CASCADE,
        related_name="graph_edges",
        verbose_name="所属工作流",
    )
    client_edge_id = models.CharField(
        "前端边 ID",
        max_length=128,
        help_text="与编辑器中 edge.id 一致，在同一 workflow 内唯一。",
    )
    source_node_id = models.CharField(
        "源节点前端 ID",
        max_length=128,
        help_text="等于某一 WorkflowGraphNode.client_node_id，否则图为脏数据。",
    )
    target_node_id = models.CharField(
        "目标节点前端 ID",
        max_length=128,
        help_text="等于某一 WorkflowGraphNode.client_node_id。",
    )
    source_handle = models.CharField(
        "源端口/句柄",
        max_length=64,
        blank=True,
        help_text="多输出端口时用字符串区分；无多端口时可留空。",
    )
    target_handle = models.CharField(
        "目标端口/句柄",
        max_length=64,
        blank=True,
        help_text="多输入端口时区分连接点；单输入可留空。",
    )
    metadata = models.JSONField(
        "边附加信息",
        default=dict,
        blank=True,
        help_text="如条件路由标签、权重、动画状态等；勿存密钥。",
    )
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        verbose_name = "工作流图边"
        verbose_name_plural = "工作流图边"
        ordering = ["workflow_id", "client_edge_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["workflow", "client_edge_id"],
                name="uniq_ai_engine_workflow_client_edge",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.workflow_id}:{self.source_node_id}->{self.target_node_id}"


# ─────────────────────────────────────────────────────────────────────────────
# AI 会话与消息（自动回复 / 多轮对话）；执行逻辑在 conversation.service 中扩展
# ─────────────────────────────────────────────────────────────────────────────


class ConversationSession(models.Model):
    """
    一次「对话上下文」的容器：可绑定用户、可选绑定用于生成回复的工作流。

    使用场景示例
    ------------
    - Web 聊天窗口：一个浏览器 tab 对应一个 session。
    - 自动回复：外部渠道 id 可编码进 ``metadata``（如 {"channel": "wecom", "room_id": "..."}）。

    workflow 为空时表示仅依赖通用模型或后续再绑定；设为 SET_NULL 以便工作流删除后
    会话仍可查看历史，只是失去自动图编排能力。
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="flowly_conversation_sessions",
        null=True,
        blank=True,
        verbose_name="所属用户",
        help_text="匿名访客可为空；登录后建议补上以便审计与配额统计。",
    )
    workflow = models.ForeignKey(
        Workflow,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="conversation_sessions",
        verbose_name="关联工作流",
        help_text="若设置，自动回复可优先按该工作流的 LangGraph 定义执行。",
    )
    topic = models.CharField(
        "会话主题/标题",
        max_length=255,
        blank=True,
        help_text="便于列表展示；可由首条用户消息摘要自动生成。",
    )
    metadata = models.JSONField(
        "扩展元数据",
        default=dict,
        blank=True,
        help_text="渠道、标签、优先级等业务字段；避免存放明文 PII。",
    )
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        verbose_name = "对话会话"
        verbose_name_plural = "对话会话"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"session#{self.pk} ({self.topic or 'untitled'})"


class ConversationMessage(models.Model):
    """
    会话中的一条消息（用户 / 助手 / 系统之一）。

    content 与 attachments 分工
    ----------------------------
    - ``content``：主文本（用户输入或模型输出）。
    - ``attachments``：结构化附件列表，如图片/音频 URL、文件 id；大文件本体应走
      对象存储，不在此存二进制 Base64。
    """

    class Role(models.TextChoices):
        """消息角色；与 OpenAI Chat API role 命名对齐，便于直接拼接 messages 数组。"""

        USER = "user", "用户"
        ASSISTANT = "assistant", "助手"
        SYSTEM = "system", "系统"

    session = models.ForeignKey(
        ConversationSession,
        on_delete=models.CASCADE,
        related_name="messages",
        verbose_name="所属会话",
        help_text="会话删除时级联删除其下所有消息。",
    )
    role = models.CharField(
        "角色",
        max_length=16,
        choices=Role.choices,
        help_text="决定该条在上下文拼接中的语义。",
    )
    content = models.TextField(
        "正文",
        blank=True,
        help_text="纯文本或多模态占位文本；结构化输出可用 JSON 字符串。",
    )
    attachments = models.JSONField(
        "附件列表",
        default=list,
        blank=True,
        help_text="每项建议为 dict，至少包含 type 与 url 或 storage_key。",
    )
    metadata = models.JSONField(
        "消息级元数据",
        default=dict,
        blank=True,
        help_text="如 token 用量、模型名、链路 trace_id；勿存密钥。",
    )
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        verbose_name = "对话消息"
        verbose_name_plural = "对话消息"
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.role}:{self.pk}"


# ─────────────────────────────────────────────────────────────────────────────
# 用户自定义节点类型（仅该用户可见；前端只传模型名与 provider 路由）
# ─────────────────────────────────────────────────────────────────────────────


class UserCustomNodeType(models.Model):
    """
    用户在平台中注册的「自定义节点类型」模板。

    画布上 ``node_type`` 建议使用 ``ut_<本记录主键>``，执行时由注册表加载本行，
    使用 ``provider_route`` + ``model_name`` 调用项目已封装的 ``get_chat_model``。
    密钥一律来自 ``get_ai_provider_settings()``，不得写入 ``default_config``。
    """

    class ProviderRoute(models.TextChoices):
        OPENAI = "openai", "OpenAI 兼容"
        DOUBAO = "doubao", "火山方舟 / 豆包"
        ARK = "ark", "方舟（同 doubao）"
        CLAUDE = "claude", "Anthropic Claude"
        OLLAMA = "ollama", "Ollama 本地"
        VECTORENGINE = "vectorengine", "VectorEngine 兼容网关"

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="custom_node_types",
        verbose_name="所属用户",
    )
    slug = models.SlugField(
        "类型标识",
        max_length=64,
        help_text="URL 安全短名，便于展示；与 user 组合唯一。",
    )
    display_name = models.CharField("显示名称", max_length=128)
    provider_route = models.CharField(
        "模型路由",
        max_length=32,
        choices=ProviderRoute.choices,
        help_text="与 ``workflow.get_chat_model`` 的 model_name 参数一致。",
    )
    model_name = models.CharField(
        "模型名",
        max_length=128,
        help_text="前端仅填写模型 id 字符串，如 gpt-4o、claude-3-5-sonnet-20241022。",
    )
    default_config = models.JSONField(
        "默认节点参数",
        default=dict,
        blank=True,
        help_text="temperature、max_tokens 等；勿存密钥。",
    )
    description = models.TextField("说明", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "用户自定义节点类型"
        verbose_name_plural = "用户自定义节点类型"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "slug"], name="uniq_user_custom_node_slug"),
        ]

    def __str__(self) -> str:
        return f"{self.user_id}:{self.slug}"

    @property
    def type_key(self) -> str:
        """写入画布 ``node_type`` 的推荐值。"""
        return f"ut_{self.pk}"


# ─────────────────────────────────────────────────────────────────────────────
# 项目级 AI 模型目录（方舟/语音等元数据，供 GET /api/ai/models 与画布 modelKey 解析）
# ─────────────────────────────────────────────────────────────────────────────


class AIModelCatalogEntry(models.Model):
    """
    项目维护的模型目录项（密钥仍只来自环境变量 / 用户自定义预设）。

    ``catalog_key`` 写入画布 ``config.modelKey``；仅 ``api_kind=ark_chat`` 且
    ``show_in_canvas_llm_nodes=True`` 的项会出现在画布 LLM 节点下拉中。
    """

    class ApiKind(models.TextChoices):
        ARK_CHAT = "ark_chat", "方舟对话/补全"
        ARK_EMBEDDING = "ark_embedding", "方舟向量嵌入"
        ARK_IMAGE_GEN = "ark_image_gen", "方舟图像生成/编辑"
        ARK_VIDEO_GEN = "ark_video_gen", "方舟视频生成"
        ARK_3D_GEN = "ark_3d_gen", "方舟 3D 生成"
        OPEN_SPEECH = "openspeech", "火山语音（独立接口）"

    catalog_key = models.SlugField("目录键", max_length=96, unique=True, db_index=True)
    label = models.CharField("展示名称", max_length=160)
    description = models.CharField("短说明", max_length=512, blank=True)
    route = models.CharField(
        "路由",
        max_length=32,
        default="doubao",
        help_text="与 get_chat_model 路由一致；语音独立接口可填 openspeech（仅元数据标记）。",
    )
    model_id = models.CharField(
        "模型 ID",
        max_length=256,
        blank=True,
        help_text="方舟 OpenAI 兼容调用时的 model；空则回退环境默认（一般仅用于占位）。",
    )
    category = models.CharField("分类 id", max_length=64, db_index=True)
    category_label = models.CharField("分类展示名", max_length=128)
    category_order = models.IntegerField("分类排序", default=500)
    sort_order = models.PositiveSmallIntegerField("同分类内排序", default=0)
    scopes = models.JSONField("标签", default=list, blank=True)
    scope_summary = models.TextField("详细说明", blank=True)
    canvas_node_kinds = models.JSONField(
        "画布 LLM 节点类型",
        default=list,
        blank=True,
        help_text='如 ["chat","text"]；空且非 canvas_universal 表示不限制（一般不用）。',
    )
    canvas_universal = models.BooleanField("全画布 LLM 节点可选", default=False)
    api_kind = models.CharField(
        "接口类型",
        max_length=32,
        choices=ApiKind.choices,
        default=ApiKind.ARK_CHAT,
        db_index=True,
    )
    show_in_canvas_llm_nodes = models.BooleanField(
        "在画布 LLM 节点展示",
        default=True,
        help_text="向量/文生图/语音等非对话补全能力选 False，仍出现在 GET /api/ai/models 供其它功能使用。",
    )
    is_active = models.BooleanField("启用", default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "AI 模型目录项"
        verbose_name_plural = "AI 模型目录"
        ordering = ["category_order", "sort_order", "catalog_key"]

    def __str__(self) -> str:
        return f"{self.catalog_key} ({self.label})"

    def normalized_route(self) -> str:
        r = (self.route or "").strip().lower()
        if r in ("ark", "byte", "volcengine"):
            return "doubao"
        return r


# ─────────────────────────────────────────────────────────────────────────────
# 本地媒体资源（用户上传/生成的图片、音频、视频等，路径存库）
# ─────────────────────────────────────────────────────────────────────────────
class LocalMediaAsset(models.Model):
    """用户在系统内产生/上传的资源：文件落在 MEDIA_ROOT 下，本表记录路径与元数据。"""

    class Kind(models.TextChoices):
        IMAGE = "image", "图片"
        AUDIO = "audio", "音频"
        VIDEO = "video", "视频"
        FILE = "file", "文件"
        AVATAR = "avatar", "头像"

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="local_media_assets",
        verbose_name="所属用户",
    )
    kind = models.CharField(max_length=16, choices=Kind.choices, default=Kind.FILE, db_index=True)
    original_name = models.CharField(max_length=255, blank=True, default="")
    mime = models.CharField(max_length=128, blank=True, default="")
    size_bytes = models.BigIntegerField(default=0)
    rel_path = models.CharField(max_length=512, db_index=True, help_text="相对 MEDIA_ROOT 的路径")
    source_url = models.CharField(max_length=2048, blank=True, default="", help_text="若由第三方生成/抓取，记录来源 URL（可空）")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["user", "kind", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.user_id}:{self.kind}:{self.rel_path}"


# ─────────────────────────────────────────────────────────────────────────────
# 用户自定义「聊天模型」预设（供标准画布节点 modelKey 使用，与项目内置 catalog 并列）
# ─────────────────────────────────────────────────────────────────────────────


class UserChatModelPreset(models.Model):
    """
    用户在平台保存的 LLM 选项，写入画布 ``config.modelKey`` 时使用 ``user:<本表主键>``。

    可选填写 ``api_key_encrypted`` / ``api_base_url``：调用 ``get_chat_model`` 时覆盖环境变量；
    未填写时仍使用项目全局密钥（与 route 匹配的环境配置）。
    """

    class ProviderRoute(models.TextChoices):
        OPENAI = "openai", "OpenAI 兼容"
        DOUBAO = "doubao", "火山方舟 / 豆包"
        ARK = "ark", "方舟（同 doubao）"
        CLAUDE = "claude", "Anthropic Claude"
        OLLAMA = "ollama", "Ollama 本地"
        VECTORENGINE = "vectorengine", "VectorEngine 兼容网关"

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="chat_model_presets",
        verbose_name="所属用户",
    )
    display_name = models.CharField("显示名称", max_length=128)
    description = models.TextField("说明", blank=True)
    route = models.CharField(
        "模型路由",
        max_length=32,
        choices=ProviderRoute.choices,
        help_text="与 ``workflow.get_chat_model`` 的路由名一致。",
    )
    model_id = models.CharField(
        "模型 ID",
        max_length=256,
        help_text="如方舟 ep-…、OpenAI 的 gpt-4o 等。",
    )
    category = models.CharField(
        "功能分类 id",
        max_length=32,
        default="user_custom",
        help_text="建议按「用途」命名（如 fn_high_volume），与内置 ``ai_model_catalog`` 的 category 同形，便于前端与内置项一起分组。",
    )
    category_label = models.CharField("功能分类展示名", max_length=128, default="我的模型")
    category_order = models.PositiveSmallIntegerField(
        "排序权重",
        default=100,
        help_text="在 GET /api/ai/models 中与内置项混排时越小越靠前。",
    )
    scopes = models.JSONField(
        "适用范围标签",
        default=list,
        blank=True,
        help_text='字符串数组，如 ["画布对话","文本"]，供前端展示芯片。',
    )
    scope_summary = models.TextField(
        "适用范围说明",
        blank=True,
        help_text="一段话说明该模型适合做什么；展示在模型选择器下方。",
    )
    api_key_encrypted = models.TextField(
        "API 密钥（加密）",
        blank=True,
        help_text="Fernet 密文；留空则调用时使用环境变量中的密钥。",
    )
    api_base_url = models.CharField(
        "API Base URL",
        max_length=512,
        blank=True,
        help_text="可选；OpenAI/方舟/VectorEngine 等兼容接口的 base，留空用环境默认。",
    )
    is_active = models.BooleanField("启用", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "用户聊天模型预设"
        verbose_name_plural = "用户聊天模型预设"
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return f"{self.user_id}:{self.display_name}"

    @property
    def api_model_key(self) -> str:
        """写入节点 ``modelKey`` 的值。"""
        return f"user:{self.pk}"

    def normalized_route(self) -> str:
        r = (self.route or "").strip().lower()
        if r in ("ark", "byte", "volcengine"):
            return "doubao"
        return r

    def set_api_key(self, raw: str | None) -> None:
        """写入前加密；传 ``None`` / 空串则清空已存密钥。"""
        from ai_engine.user_model_crypto import encrypt_user_secret

        t = (raw or "").strip()
        self.api_key_encrypted = encrypt_user_secret(t) if t else ""

    def get_api_key(self) -> str:
        from ai_engine.user_model_crypto import decrypt_user_secret

        return decrypt_user_secret(self.api_key_encrypted or "")


# ─────────────────────────────────────────────────────────────────────────────
# 提示词加工（Prompt Enhancement）审计与工作流校验结果
# ─────────────────────────────────────────────────────────────────────────────


class PromptEnhancementRecord(models.Model):
    """
    记录一次「提示词加工」的输入、模型参数、候选输出与最终选择（如有）。

    说明
    ----
    - 本表用于审计与复盘；不改变运行时节点行为（加工结果由前端回填到节点 config）。
    - user/workflow 可为空：为兼容系统任务/匿名场景；API 层通常要求登录用户。
    """

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="prompt_enhancement_records",
        help_text="触发本次加工的用户；匿名/系统任务可为空。",
    )
    workflow = models.ForeignKey(
        Workflow,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="prompt_enhancement_records",
        help_text="所属工作流上下文；不绑定工作流时可为空。",
    )

    client_node_id = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        help_text="画布节点 id（与 EditorNode.id 一致；可为空）。",
    )
    node_type = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        help_text="节点类型（如 chat/text/ut_<id>；可为空）。",
    )
    field = models.CharField(
        max_length=64,
        help_text="被加工的字段名（如 systemPrompt / prompt / captionPrompt）。",
    )

    raw_prompt = models.TextField(help_text="用户原始输入（待加工文本）。")
    instruction = models.TextField(
        null=True,
        blank=True,
        help_text="用户额外加工要求（可为空）。",
    )

    candidates = models.JSONField(
        default=list,
        blank=True,
        help_text="模型生成的候选列表（JSON）。",
    )
    suggested_text = models.TextField(
        blank=True,
        help_text="系统默认建议的候选（可为空）。",
    )
    selected_text = models.TextField(
        null=True,
        blank=True,
        help_text="用户最终确认的文本（确认前可为空）。",
    )

    provider_route = models.CharField(
        max_length=32,
        help_text="模型路由（openai/doubao/claude/ollama/vectorengine）。",
    )
    model = models.CharField(
        max_length=128,
        help_text="模型 id（如 gpt-4o 或 ep-xxxx）。",
    )
    temperature = models.FloatField(
        null=True,
        blank=True,
        help_text="采样温度（可为空）。",
    )
    max_tokens = models.IntegerField(
        null=True,
        blank=True,
        help_text="max_tokens（可为空）。",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["workflow", "created_at"]),
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return f"prompt_enhancement#{self.pk} ({self.provider_route}:{self.model})"


class WorkflowGraphValidation(models.Model):
    """每个工作流最近一次「definition 结构校验」结果（1 workflow ↔ 1 row）。"""

    workflow = models.OneToOneField(
        Workflow,
        on_delete=models.CASCADE,
        related_name="graph_validation",
        help_text="所属工作流（唯一）。",
    )
    is_valid = models.BooleanField(default=False, help_text="是否通过校验。")
    errors = models.JSONField(default=list, blank=True, help_text="校验错误列表（JSON）。")
    validated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"workflow#{self.workflow_id} valid={self.is_valid}"


# ─────────────────────────────────────────────────────────────────────────────
# AI 自动回复（规则 + 异步任务记录，与独立对话页数据分离）
# ─────────────────────────────────────────────────────────────────────────────


class AutoReplyRule(models.Model):
    """用户维度的自动回复策略（系统提示 + 可选模型键，走 ai_model_catalog）。"""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="auto_reply_rules",
        verbose_name="所属用户",
    )
    name = models.CharField("规则名称", max_length=128)
    personality_key = models.CharField(
        "人格预设键",
        max_length=64,
        blank=True,
        help_text="与参考项目 ChatPersonality 键一致；可与情景键组合，在系统提示为空时自动生成语气。",
    )
    scene_key = models.CharField(
        "情景预设键",
        max_length=64,
        blank=True,
        help_text="与参考项目 ChatScene 键一致。",
    )
    system_prompt = models.TextField(
        "系统提示",
        blank=True,
        help_text="可选。若填写则优先生效；若为空且填写人格/情景键，则按预设组合生成系统提示。",
    )
    model_key = models.CharField(
        "模型目录键",
        max_length=96,
        blank=True,
        help_text="与画布 modelKey 一致；留空则使用服务端 FLOWLY_AUTO_REPLY_MODEL_KEY。",
    )
    is_active = models.BooleanField("启用", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "自动回复规则"
        verbose_name_plural = "自动回复规则"

    def __str__(self) -> str:
        return f"{self.user_id}:{self.name}"


class AutoReplyJob(models.Model):
    """单次自动回复生成任务（由 Celery 或独立子进程执行，避免阻塞 HTTP）。"""

    class Status(models.TextChoices):
        PENDING = "pending", "排队中"
        PROCESSING = "processing", "生成中"
        COMPLETED = "completed", "已完成"
        FAILED = "failed", "失败"

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="auto_reply_jobs",
        verbose_name="所属用户",
    )
    rule = models.ForeignKey(
        AutoReplyRule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="jobs",
        verbose_name="使用的规则",
    )
    status = models.CharField(
        "状态",
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    input_text = models.TextField("用户/客户消息")
    friend_name = models.CharField(
        "对方显示名（可选）",
        max_length=128,
        blank=True,
        db_index=True,
        help_text="与监控/OCR 好友名一致；用于按好友筛选资料库条目。",
    )
    reply_text = models.TextField("模型回复", blank=True)
    error_message = models.TextField("错误信息", blank=True)
    model_key_used = models.CharField("实际使用的模型键", max_length=96, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "自动回复任务"
        verbose_name_plural = "自动回复任务"
        indexes = [
            models.Index(fields=["user", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"AutoReplyJob#{self.pk} ({self.status})"


class AutoReplyScreenProfile(models.Model):
    """
    屏幕监控布局与名单（原桌面端 config.json 中的区域与 monitored_friends 等），按用户一条。
    本机代理通过 API 拉取后执行截图 / YOLO /（后续可接 OCR）。
    """

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="auto_reply_screen_profile",
        verbose_name="所属用户",
    )
    chat_software = models.CharField(
        "当前聊天软件标识",
        max_length=32,
        blank=True,
        default="wechat",
        help_text="与参考项目一致，如 wechat、qq、tim。",
    )
    chat_window_box = models.JSONField(
        "聊天内容区 [x1,y1,x2,y2]",
        null=True,
        blank=True,
        help_text="手动标定或模型失效时的回退框。",
    )
    input_box_pos = models.JSONField("输入框区域", null=True, blank=True)
    user_name_box = models.JSONField("对方用户名区域", null=True, blank=True)
    friend_list_box = models.JSONField("好友列表区域", null=True, blank=True)
    monitored_friends = models.JSONField(
        "监控的好友显示名列表",
        default=list,
        blank=True,
        help_text="字符串列表，与参考 monitor_list 语义一致。",
    )
    friends_overrides = models.JSONField(
        "按好友名的策略覆盖",
        default=dict,
        blank=True,
        help_text="键为好友名，值为 {personality, scene, custom_system_prompt, ...} 结构，与参考 friends_config 对齐。",
    )
    check_interval_seconds = models.PositiveSmallIntegerField(
        "检测间隔（秒）",
        default=3,
    )
    use_yolo = models.BooleanField(
        "启用 YOLO 区域检测",
        default=True,
        help_text="关闭时本机代理仅使用下方手动坐标。",
    )
    knowledge_reply_enabled = models.BooleanField(
        "资料库合并回复",
        default=False,
        help_text="与参考项目一致：开启后生成回复时合并资料库条目（关键词规则见 AutoReplyKnowledgeEntry）。",
    )
    monitoring_active = models.BooleanField(
        "监控运行中",
        default=False,
        help_text="Vue「开始监控」打开后，本机代理应持续轮询并执行识别/OCR；关闭则仅低频心跳或休眠。",
    )
    yolo_weights_path = models.CharField(
        "YOLO 权重路径（本机）",
        max_length=512,
        blank=True,
        help_text="如 best.pt 绝对路径；写入数据库后代理可优先于此处配置，其次读环境变量。",
    )
    region_detect_nonce = models.PositiveIntegerField(
        "区域识别请求序号",
        default=0,
        help_text="前端「更新聊天窗口」自增；代理检测成功后回写坐标并同步 region_detect_ack_nonce。",
    )
    region_detect_ack_nonce = models.PositiveIntegerField(
        "区域识别已应用序号",
        default=0,
    )
    default_rule = models.ForeignKey(
        AutoReplyRule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="screen_profiles_default",
        verbose_name="屏幕任务默认规则",
        help_text="代理自动建任务时可选；须属于同一用户。",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "自动回复屏幕配置"
        verbose_name_plural = "自动回复屏幕配置"

    def __str__(self) -> str:
        return f"ScreenProfile(user={self.user_id})"


class AutoReplyKnowledgeEntry(models.Model):
    """替代原 knowledge/ 下文本文件：按用户存库，支持共享与按好友挂载、触发关键词。"""

    class Scope(models.TextChoices):
        SHARED = "shared", "共享"
        FRIEND = "friend", "指定好友"

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="auto_reply_knowledge_entries",
        verbose_name="所属用户",
    )
    scope = models.CharField(
        "范围",
        max_length=16,
        choices=Scope.choices,
        default=Scope.SHARED,
    )
    friend_name = models.CharField(
        "好友显示名",
        max_length=128,
        blank=True,
        db_index=True,
        help_text="scope=friend 时必填，与 OCR/监控名单一致。",
    )
    title = models.CharField("标题", max_length=256, blank=True)
    body = models.TextField("正文", help_text="纯文本，注入系统提示前的资料块。")
    trigger_keywords = models.JSONField(
        "触发关键词",
        default=list,
        blank=True,
        help_text="子串列表；空列表表示在总开关开启时对每条消息都可挂载（与参考逻辑一致）。",
    )
    is_active = models.BooleanField("启用", default=True)
    sort_order = models.SmallIntegerField("排序", default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "自动回复资料条目"
        verbose_name_plural = "自动回复资料条目"
        indexes = [
            models.Index(fields=["user", "scope", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"Kb#{self.pk} {self.scope}"


class AutoReplyChatHistoryEntry(models.Model):
    """替代原 chat_history 文件：监控/生成产生的对话片段。"""

    class Role(models.TextChoices):
        USER = "user", "对方/用户侧"
        ASSISTANT = "assistant", "模型/助手"
        SYSTEM = "system", "系统"

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="auto_reply_chat_history",
        verbose_name="所属用户",
    )
    friend_name = models.CharField("好友显示名", max_length=128, blank=True, db_index=True)
    role = models.CharField("角色", max_length=16, choices=Role.choices, default=Role.USER)
    content = models.TextField("内容")
    meta = models.JSONField("元数据", default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "自动回复聊天记录"
        verbose_name_plural = "自动回复聊天记录"
        indexes = [
            models.Index(fields=["user", "friend_name", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"ChatHist#{self.pk}"

