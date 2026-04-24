# Generated manually: UILabel + 默认 zh-CN 种子数据

from django.db import migrations, models


def seed_ui_labels(apps, schema_editor):
    UILabel = apps.get_model("ai_engine", "UILabel")
    locale = "zh-CN"
    rows: list[tuple[str, str, str, str]] = [
        # —— 应用壳层 app.* ——
        ("app.nav.home", "首页", "app", "主导航"),
        ("app.nav.chat", "AI 对话", "app", "主导航"),
        ("app.nav.workflows", "工作流", "app", "主导航"),
        ("app.nav.observability", "监控", "app", "主导航"),
        ("app.nav.newRun", "新建运行", "app", "顶栏按钮"),
        ("app.auth.login", "登录", "app", "访客按钮"),
        ("app.auth.register", "注册", "app", "访客按钮"),
        ("app.user.settings", "设置", "app", "用户菜单"),
        ("app.user.logout", "退出登录", "app", "用户菜单"),
        ("app.message.logoutSuccess", "已退出登录", "app", "退出成功提示"),
        ("app.brand.name", "Flowly", "app", "品牌名"),
        # —— 工作流运行页 wf.run.* ——
        ("wf.run.back", "返回", "workflow", "运行页顶栏"),
        ("wf.run.titleExec", "工作流执行", "workflow", "无名称时的标题"),
        ("wf.run.titleRun", "执行工作流", "workflow", "无路由 id 时标题"),
        ("wf.run.titleRunPrefix", "运行: ", "workflow", "带工作流名称前缀"),
        # —— 左侧表单 wf.runner.* ——
        ("wf.runner.header", "工作流执行", "workflow", "Runner 卡片标题"),
        ("wf.runner.workflowLabel", "工作流", "workflow", "表单项"),
        ("wf.runner.workflowPlaceholder", "选择工作流", "workflow", "下拉占位"),
        ("wf.runner.queryLabel", "查询", "workflow", "表单项"),
        ("wf.runner.queryPlaceholder", "描述任务或提出问题…", "workflow", "文本域占位"),
        ("wf.runner.contextLabel", "上下文（可选）", "workflow", "表单项"),
        (
            "wf.runner.contextPlaceholder",
            '以 JSON 格式提供额外上下文，如 {"key": "value"}',
            "workflow",
            "文本域占位",
        ),
        ("wf.runner.clientNodeLabel", "画布节点 ID（可选）", "workflow", "表单项"),
        ("wf.runner.clientNodePlaceholder", "与编辑器中节点 id 一致，便于按节点统计 token 费用", "workflow", "输入占位"),
        ("wf.runner.submit", "运行工作流", "workflow", "主按钮"),
        ("wf.runner.submitRunning", "运行中…", "workflow", "主按钮加载态"),
        ("wf.runner.reset", "重置", "workflow", "次按钮"),
        ("wf.runner.validation.workflowRequired", "请选择一个工作流", "workflow", "校验"),
        ("wf.runner.validation.queryRequired", "请输入查询内容", "workflow", "校验"),
        ("wf.runner.validation.queryLength", "查询内容长度为 2-2000 个字符", "workflow", "校验"),
        ("wf.common.descNone", "—", "workflow", "无描述占位"),
        # —— 监控区 wf.monitor.* ——
        ("wf.monitor.chatTitle", "执行对话", "monitor", "中栏标题"),
        ("wf.monitor.status.pending", "等待", "monitor", "总状态标签"),
        ("wf.monitor.status.running", "运行中", "monitor", "总状态标签"),
        ("wf.monitor.status.completed", "已完成", "monitor", "总状态标签"),
        ("wf.monitor.status.failed", "失败", "monitor", "总状态标签"),
        ("wf.monitor.emptyMessages", "暂无消息，运行工作流后将显示对话记录", "monitor", "空状态"),
        ("wf.monitor.statusPanelTitle", "节点状态", "monitor", "右栏标题"),
        ("wf.monitor.statusPanelTooltip", "实时显示工作流节点执行进度", "monitor", "右栏提示"),
        ("wf.monitor.emptyNodes", "暂无活跃节点", "monitor", "空状态"),
        ("wf.monitor.nodeModelPrefix", "模型：", "monitor", "节点模型前缀"),
        ("wf.monitor.progressLabel", "工作流进度", "monitor", "进度条说明"),
        ("wf.monitor.resultSuccessTitle", "工作流已完成", "monitor", "完成结果"),
        ("wf.monitor.resultFailTitle", "工作流失败", "monitor", "失败结果"),
        ("wf.monitor.resultSubtitleDefault", "执行结束", "monitor", "结果副标题"),
        ("wf.monitor.newRunAgain", "新运行", "monitor", "结果区按钮"),
        ("wf.monitor.approvalTitle", "需要审批", "monitor", "审批条"),
        ("wf.monitor.approve", "批准", "monitor", "审批按钮"),
        ("wf.monitor.reject", "拒绝", "monitor", "审批按钮"),
        ("wf.node.status.completed", "已完成", "monitor", "节点时间线"),
        ("wf.node.status.running", "运行中", "monitor", "节点时间线"),
        ("wf.node.status.failed", "失败", "monitor", "节点时间线"),
        ("wf.node.status.idle", "空闲", "monitor", "节点时间线"),
    ]
    for key, value, category, description in rows:
        UILabel.objects.update_or_create(
            locale=locale,
            key=key,
            defaults={
                "value": value,
                "category": category,
                "description": description,
                "is_active": True,
            },
        )


def unseed_ui_labels(apps, schema_editor):
    UILabel = apps.get_model("ai_engine", "UILabel")
    UILabel.objects.filter(locale="zh-CN").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("ai_engine", "0010_workflowexecutionstep"),
    ]

    operations = [
        migrations.CreateModel(
            name="UILabel",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key", models.CharField(db_index=True, help_text="稳定唯一键，与前端 useUiLabels().t() 参数一致。", max_length=160, verbose_name="文案键")),
                ("locale", models.CharField(db_index=True, default="zh-CN", help_text="BCP 47，如 zh-CN、en-US。", max_length=32, verbose_name="语言区域")),
                ("value", models.TextField(help_text="用户可见文案；支持换行（少数场景如多行提示）。", verbose_name="展示文本")),
                ("category", models.CharField(blank=True, db_index=True, default="general", help_text="仅用于后台筛选，如 app、workflow、monitor。", max_length=64, verbose_name="分组")),
                ("description", models.CharField(blank=True, help_text="说明该键出现在哪个页面，勿写用户可见内容。", max_length=255, verbose_name="管理员说明")),
                ("is_active", models.BooleanField(default=True, verbose_name="启用")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="更新时间")),
            ],
            options={
                "verbose_name": "界面文案",
                "verbose_name_plural": "界面文案",
                "ordering": ["locale", "category", "key"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("locale", "key"),
                        name="uniq_ai_engine_ui_label_locale_key",
                    ),
                ],
            },
        ),
        migrations.RunPython(seed_ui_labels, unseed_ui_labels),
    ]
