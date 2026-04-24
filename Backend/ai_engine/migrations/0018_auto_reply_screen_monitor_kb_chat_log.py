# Generated for screen monitor flags, knowledge/chat/log DB, job.friend_name.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("ai_engine", "0017_autoreplyscreenprofile_autoreplyscreenevent"),
    ]

    operations = [
        migrations.AddField(
            model_name="autoreplyscreenprofile",
            name="monitoring_active",
            field=models.BooleanField(
                default=False,
                help_text="Vue「开始监控」打开后，本机代理应持续轮询并执行识别/OCR；关闭则仅低频心跳或休眠。",
                verbose_name="监控运行中",
            ),
        ),
        migrations.AddField(
            model_name="autoreplyscreenprofile",
            name="region_detect_ack_nonce",
            field=models.PositiveIntegerField(default=0, verbose_name="区域识别已应用序号"),
        ),
        migrations.AddField(
            model_name="autoreplyscreenprofile",
            name="region_detect_nonce",
            field=models.PositiveIntegerField(
                default=0,
                help_text="前端「更新聊天窗口」自增；代理检测成功后回写坐标并同步 region_detect_ack_nonce。",
                verbose_name="区域识别请求序号",
            ),
        ),
        migrations.AddField(
            model_name="autoreplyscreenprofile",
            name="yolo_weights_path",
            field=models.CharField(
                blank=True,
                help_text="如 best.pt 绝对路径；写入数据库后代理可优先于此处配置，其次读环境变量。",
                max_length=512,
                verbose_name="YOLO 权重路径（本机）",
            ),
        ),
        migrations.AlterField(
            model_name="autoreplyscreenprofile",
            name="knowledge_reply_enabled",
            field=models.BooleanField(
                default=False,
                help_text="与参考项目一致：开启后生成回复时合并资料库条目（关键词规则见 AutoReplyKnowledgeEntry）。",
                verbose_name="资料库合并回复",
            ),
        ),
        migrations.AddField(
            model_name="autoreplyjob",
            name="friend_name",
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text="与监控/OCR 好友名一致；用于按好友筛选资料库条目。",
                max_length=128,
                verbose_name="对方显示名（可选）",
            ),
        ),
        migrations.CreateModel(
            name="AutoReplyKnowledgeEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("scope", models.CharField(choices=[("shared", "共享"), ("friend", "指定好友")], default="shared", max_length=16, verbose_name="范围")),
                ("friend_name", models.CharField(blank=True, db_index=True, help_text="scope=friend 时必填，与 OCR/监控名单一致。", max_length=128, verbose_name="好友显示名")),
                ("title", models.CharField(blank=True, max_length=256, verbose_name="标题")),
                ("body", models.TextField(help_text="纯文本，注入系统提示前的资料块。", verbose_name="正文")),
                ("trigger_keywords", models.JSONField(blank=True, default=list, help_text="子串列表；空列表表示在总开关开启时对每条消息都可挂载（与参考逻辑一致）。", verbose_name="触发关键词")),
                ("is_active", models.BooleanField(default=True, verbose_name="启用")),
                ("sort_order", models.SmallIntegerField(default=0, verbose_name="排序")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="auto_reply_knowledge_entries",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="所属用户",
                    ),
                ),
            ],
            options={
                "verbose_name": "自动回复资料条目",
                "verbose_name_plural": "自动回复资料条目",
                "ordering": ["sort_order", "id"],
            },
        ),
        migrations.CreateModel(
            name="AutoReplyChatHistoryEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("friend_name", models.CharField(blank=True, db_index=True, max_length=128, verbose_name="好友显示名")),
                ("role", models.CharField(choices=[("user", "对方/用户侧"), ("assistant", "模型/助手"), ("system", "系统")], default="user", max_length=16, verbose_name="角色")),
                ("content", models.TextField(verbose_name="内容")),
                ("meta", models.JSONField(blank=True, default=dict, verbose_name="元数据")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="auto_reply_chat_history",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="所属用户",
                    ),
                ),
            ],
            options={
                "verbose_name": "自动回复聊天记录",
                "verbose_name_plural": "自动回复聊天记录",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="AutoReplyMonitorLogLine",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("level", models.CharField(choices=[("info", "信息"), ("warn", "警告"), ("error", "错误")], default="info", max_length=8, verbose_name="级别")),
                ("line", models.TextField(verbose_name="日志行")),
                ("extra", models.JSONField(blank=True, default=dict, verbose_name="附加")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="auto_reply_monitor_logs",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="所属用户",
                    ),
                ),
            ],
            options={
                "verbose_name": "自动回复监控日志",
                "verbose_name_plural": "自动回复监控日志",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="autoreplyknowledgeentry",
            index=models.Index(fields=["user", "scope", "is_active"], name="ar_kb_usr_scope_act"),
        ),
        migrations.AddIndex(
            model_name="autoreplychathistoryentry",
            index=models.Index(fields=["user", "friend_name", "created_at"], name="ar_ch_usr_fn_crt"),
        ),
        migrations.AddIndex(
            model_name="autoreplymonitorlogline",
            index=models.Index(fields=["user", "created_at"], name="ar_ml_usr_crt"),
        ),
    ]
