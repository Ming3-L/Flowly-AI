from django.contrib import admin

from .models import (
    AIModelCatalogEntry,
    AutoReplyChatHistoryEntry,
    AutoReplyJob,
    AutoReplyKnowledgeEntry,
    AutoReplyMonitorLogLine,
    AutoReplyRule,
    AutoReplyScreenEvent,
    AutoReplyScreenProfile,
    ConversationMessage,
    ConversationSession,
    Thread,
    UILabel,
    UserChatModelPreset,
    UserCustomNodeType,
    Workflow,
    WorkflowExecution,
    WorkflowGraphEdge,
    WorkflowGraphNode,
)
from .rag_models import Document
from .analytics_models import CostRecord


@admin.register(UILabel)
class UILabelAdmin(admin.ModelAdmin):
    """界面文案：前端通过 GET /api/ui-labels 拉取；修改后前端刷新即可生效。"""

    list_display = ["key", "locale", "category", "value_preview", "is_active", "updated_at"]
    list_filter = ["locale", "category", "is_active"]
    search_fields = ["key", "value", "description"]
    list_editable = ["is_active"]
    ordering = ["locale", "category", "key"]

    fieldsets = [
        ("标识", {"fields": ["key", "locale", "category", "is_active"]}),
        ("内容", {"fields": ["value", "description"]}),
        ("时间", {"fields": ["updated_at"]}),
    ]
    readonly_fields = ["updated_at"]

    @admin.display(description="文案预览")
    def value_preview(self, obj: UILabel) -> str:
        v = (obj.value or "").replace("\n", " ")
        return (v[:80] + "…") if len(v) > 80 else v


@admin.register(Workflow)
class WorkflowAdmin(admin.ModelAdmin):
    """Admin configuration for Workflow model."""
    list_display = ["id", "name", "is_active", "created_at", "updated_at"]
    list_filter = ["is_active", "created_at"]
    search_fields = ["name", "description"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["-created_at"]

    fieldsets = [
        ("Basic Info", {"fields": ["name", "description", "is_active"]}),
        ("Definition", {"fields": ["definition"], "classes": ["collapse"]}),
        ("Timestamps", {"fields": ["created_at", "updated_at"]}),
    ]


@admin.register(Thread)
class ThreadAdmin(admin.ModelAdmin):
    """Admin configuration for Thread model."""
    list_display = ["id", "thread_id", "workflow", "user", "created_at", "updated_at"]
    list_filter = ["workflow", "created_at"]
    search_fields = ["thread_id"]
    readonly_fields = ["thread_id", "created_at", "updated_at"]
    ordering = ["-created_at"]
    raw_id_fields = ["user", "workflow"]


@admin.register(WorkflowExecution)
class WorkflowExecutionAdmin(admin.ModelAdmin):
    """Admin configuration for WorkflowExecution model."""
    list_display = [
        "id", "workflow", "status", "started_at", "completed_at"
    ]
    list_filter = ["status", "workflow", "started_at"]
    search_fields = ["thread__thread_id"]
    readonly_fields = ["started_at", "completed_at"]
    ordering = ["-started_at"]
    raw_id_fields = ["workflow", "thread"]

    fieldsets = [
        ("Execution Info", {"fields": ["workflow", "thread", "status"]}),
        ("Data", {"fields": ["input_data", "output_data", "error_message"]}),
        ("Timing", {"fields": ["started_at", "completed_at"]}),
    ]


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    """Admin for knowledge base documents (Phase 8: RAG)."""
    list_display = ["id", "filename", "workflow", "file_type", "processing_status", "chunk_count", "created_at"]
    list_filter = ["processing_status", "file_type", "workflow"]
    search_fields = ["filename", "title"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["-created_at"]


@admin.register(WorkflowGraphNode)
class WorkflowGraphNodeAdmin(admin.ModelAdmin):
    """后台维护：查看某工作流下规范化存储的节点，便于排查画布与 DB 是否一致。"""

    list_display = ["id", "workflow", "client_node_id", "node_type", "updated_at"]
    list_filter = ["node_type", "workflow"]
    search_fields = ["client_node_id", "title"]
    raw_id_fields = ["workflow"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(WorkflowGraphEdge)
class WorkflowGraphEdgeAdmin(admin.ModelAdmin):
    """后台维护：按边检索 source/target，辅助验证拓扑是否闭合、有无悬空边。"""

    list_display = ["id", "workflow", "client_edge_id", "source_node_id", "target_node_id", "updated_at"]
    list_filter = ["workflow"]
    search_fields = ["client_edge_id", "source_node_id", "target_node_id"]
    raw_id_fields = ["workflow"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(ConversationSession)
class ConversationSessionAdmin(admin.ModelAdmin):
    """后台维护：会话级列表；勿在 list_display 中展示 metadata 内可能较长的渠道原始报文。"""

    list_display = ["id", "user", "workflow", "topic", "created_at"]
    list_filter = ["workflow", "created_at"]
    search_fields = ["topic"]
    raw_id_fields = ["user", "workflow"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(ConversationMessage)
class ConversationMessageAdmin(admin.ModelAdmin):
    """后台维护：按角色与时间筛选消息；敏感内容仍须遵守公司审计与脱敏规范。"""

    list_display = ["id", "session", "role", "created_at"]
    list_filter = ["role", "created_at"]
    raw_id_fields = ["session"]
    readonly_fields = ["created_at"]


@admin.register(UserCustomNodeType)
class UserCustomNodeTypeAdmin(admin.ModelAdmin):
    """用户自定义节点类型（画布 type_key = ut_<id>）。"""

    list_display = ["id", "user", "slug", "type_key", "provider_route", "model_name", "updated_at"]
    list_filter = ["provider_route", "created_at"]
    search_fields = ["slug", "display_name", "model_name"]
    raw_id_fields = ["user"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(AIModelCatalogEntry)
class AIModelCatalogEntryAdmin(admin.ModelAdmin):
    """项目级模型目录：GET /api/ai/models 合并来源之一；画布仅 ark_chat 且 show_in_canvas_llm_nodes 可下拉里选。"""

    list_display = [
        "id",
        "catalog_key",
        "label",
        "api_kind",
        "route",
        "model_id",
        "category_label",
        "show_in_canvas_llm_nodes",
        "is_active",
        "updated_at",
    ]
    list_filter = ["api_kind", "is_active", "category", "show_in_canvas_llm_nodes"]
    search_fields = ["catalog_key", "label", "model_id", "description", "scope_summary"]
    ordering = ["category_order", "sort_order", "catalog_key"]


@admin.register(UserChatModelPreset)
class UserChatModelPresetAdmin(admin.ModelAdmin):
    """用户聊天模型预设（画布 modelKey = user:<id>）。"""

    list_display = [
        "id",
        "user",
        "display_name",
        "category_label",
        "route",
        "model_id",
        "has_encrypted_key",
        "is_active",
        "updated_at",
    ]
    list_filter = ["route", "is_active", "category", "created_at"]
    search_fields = ["display_name", "model_id", "description", "scope_summary"]
    raw_id_fields = ["user"]
    readonly_fields = ["created_at", "updated_at", "api_key_encrypted"]

    @admin.display(description="已存密钥", boolean=True)
    def has_encrypted_key(self, obj: UserChatModelPreset) -> bool:
        return bool((obj.api_key_encrypted or "").strip())


@admin.register(CostRecord)
class CostRecordAdmin(admin.ModelAdmin):
    """Admin for LLM cost tracking (Phase 10: Observability)."""
    list_display = [
        "id",
        "model",
        "provider",
        "node_name",
        "client_node_id",
        "conversation_session",
        "input_tokens",
        "output_tokens",
        "total_cost_usd",
        "created_at",
    ]
    list_filter = ["provider", "model", "created_at"]
    search_fields = ["model", "workflow__name"]
    readonly_fields = ["created_at"]
    ordering = ["-created_at"]


@admin.register(AutoReplyRule)
class AutoReplyRuleAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "user", "personality_key", "scene_key", "is_active", "model_key", "updated_at"]
    list_filter = ["is_active"]
    search_fields = ["name", "user__username"]
    raw_id_fields = ["user"]


@admin.register(AutoReplyJob)
class AutoReplyJobAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "status", "friend_name", "model_key_used", "created_at"]
    list_filter = ["status"]
    search_fields = ["input_text", "reply_text", "user__username"]
    raw_id_fields = ["user", "rule"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(AutoReplyScreenProfile)
class AutoReplyScreenProfileAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "user",
        "chat_software",
        "monitoring_active",
        "check_interval_seconds",
        "use_yolo",
        "region_detect_nonce",
        "updated_at",
    ]
    raw_id_fields = ["user", "default_rule"]
    readonly_fields = ["updated_at"]


@admin.register(AutoReplyKnowledgeEntry)
class AutoReplyKnowledgeEntryAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "scope", "friend_name", "title", "is_active", "sort_order", "updated_at"]
    list_filter = ["scope", "is_active"]
    search_fields = ["title", "body", "friend_name", "user__username"]
    raw_id_fields = ["user"]


@admin.register(AutoReplyChatHistoryEntry)
class AutoReplyChatHistoryEntryAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "friend_name", "role", "created_at"]
    list_filter = ["role"]
    search_fields = ["content", "user__username"]
    raw_id_fields = ["user"]


@admin.register(AutoReplyMonitorLogLine)
class AutoReplyMonitorLogLineAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "level", "line_preview", "created_at"]
    list_filter = ["level"]
    search_fields = ["line", "user__username"]
    raw_id_fields = ["user"]

    @admin.display(description="内容")
    def line_preview(self, obj: AutoReplyMonitorLogLine) -> str:
        return (obj.line or "")[:100]


@admin.register(AutoReplyScreenEvent)
class AutoReplyScreenEventAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "event_type", "message_preview", "created_at"]
    list_filter = ["event_type"]
    search_fields = ["message", "user__username"]
    raw_id_fields = ["user"]
    readonly_fields = ["created_at"]

    @admin.display(description="说明")
    def message_preview(self, obj: AutoReplyScreenEvent) -> str:
        t = (obj.message or "")[:80]
        return t + ("…" if len(obj.message or "") > 80 else "")

