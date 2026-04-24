# Generated manually for screen monitor profile + agent events.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("ai_engine", "0016_autoreplyrule_personality_scene_blank_prompt"),
    ]

    operations = [
        migrations.CreateModel(
            name="AutoReplyScreenProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("chat_software", models.CharField(blank=True, default="wechat", help_text="与参考项目一致，如 wechat、qq、tim。", max_length=32, verbose_name="当前聊天软件标识")),
                ("chat_window_box", models.JSONField(blank=True, help_text="手动标定或模型失效时的回退框。", null=True, verbose_name="聊天内容区 [x1,y1,x2,y2]")),
                ("input_box_pos", models.JSONField(blank=True, null=True, verbose_name="输入框区域")),
                ("user_name_box", models.JSONField(blank=True, null=True, verbose_name="对方用户名区域")),
                ("friend_list_box", models.JSONField(blank=True, null=True, verbose_name="好友列表区域")),
                ("monitored_friends", models.JSONField(blank=True, default=list, help_text="字符串列表，与参考 monitor_list 语义一致。", verbose_name="监控的好友显示名列表")),
                ("friends_overrides", models.JSONField(blank=True, default=dict, help_text="键为好友名，值为 {personality, scene, custom_system_prompt, ...} 结构，与参考 friends_config 对齐。", verbose_name="按好友名的策略覆盖")),
                ("check_interval_seconds", models.PositiveSmallIntegerField(default=3, verbose_name="检测间隔（秒）")),
                ("use_yolo", models.BooleanField(default=True, help_text="关闭时本机代理仅使用下方手动坐标。", verbose_name="启用 YOLO 区域检测")),
                ("knowledge_reply_enabled", models.BooleanField(default=False, help_text="与参考项目开关对齐；具体挂载逻辑可在代理侧实现。", verbose_name="资料库合并回复（占位）")),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "default_rule",
                    models.ForeignKey(
                        blank=True,
                        help_text="代理自动建任务时可选；须属于同一用户。",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="screen_profiles_default",
                        to="ai_engine.autoreplyrule",
                        verbose_name="屏幕任务默认规则",
                    ),
                ),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="auto_reply_screen_profile",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="所属用户",
                    ),
                ),
            ],
            options={
                "verbose_name": "自动回复屏幕配置",
                "verbose_name_plural": "自动回复屏幕配置",
            },
        ),
        migrations.CreateModel(
            name="AutoReplyScreenEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event_type", models.CharField(db_index=True, max_length=40, verbose_name="事件类型")),
                ("message", models.TextField(blank=True, verbose_name="简短说明")),
                ("payload", models.JSONField(blank=True, default=dict, verbose_name="附加数据")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="auto_reply_screen_events",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="所属用户",
                    ),
                ),
            ],
            options={
                "verbose_name": "屏幕代理事件",
                "verbose_name_plural": "屏幕代理事件",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="autoreplyscreenevent",
            index=models.Index(fields=["user", "created_at"], name="ar_scr_evt_usr_crt"),
        ),
    ]
