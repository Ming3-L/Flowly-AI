# Generated manually for WorkflowExecutionStep

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ai_engine", "0009_workflowgraphvalidation_promptenhancementrecord"),
    ]

    operations = [
        migrations.CreateModel(
            name="WorkflowExecutionStep",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("node_key", models.CharField(db_index=True, help_text="画布 client_node_id 或 LangGraph 逻辑节点名。", max_length=255, verbose_name="节点标识")),
                ("display_title", models.CharField(blank=True, help_text="画布节点 label 或可读标题。", max_length=512, verbose_name="展示标题")),
                ("node_kind", models.CharField(blank=True, help_text="如 chat、router、tool_executor。", max_length=64, verbose_name="节点类型")),
                ("activity", models.TextField(blank=True, help_text="面向用户的简短中文描述，如「使用 doubao 处理对话」。", verbose_name="当前在做什么")),
                ("model_route", models.CharField(blank=True, help_text="与 get_chat_model 一致，如 doubao、openai。", max_length=64, verbose_name="模型路由")),
                (
                    "status",
                    models.CharField(
                        choices=[("running", "运行中"), ("completed", "已完成"), ("failed", "失败")],
                        default="running",
                        max_length=16,
                        verbose_name="状态",
                    ),
                ),
                ("started_at", models.DateTimeField(auto_now_add=True, verbose_name="开始时间")),
                ("finished_at", models.DateTimeField(blank=True, null=True, verbose_name="结束时间")),
                ("detail", models.JSONField(blank=True, default=dict, verbose_name="附加信息")),
                (
                    "execution",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="steps",
                        to="ai_engine.workflowexecution",
                        verbose_name="所属执行",
                    ),
                ),
            ],
            options={
                "verbose_name": "工作流执行步骤",
                "verbose_name_plural": "工作流执行步骤",
                "ordering": ["execution_id", "id"],
            },
        ),
    ]
