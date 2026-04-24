# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ai_engine", "0012_userchatmodelpreset"),
    ]

    operations = [
        migrations.AddField(
            model_name="userchatmodelpreset",
            name="api_base_url",
            field=models.CharField(
                blank=True,
                default="",
                help_text="可选；OpenAI/方舟/VectorEngine 等兼容接口的 base，留空用环境默认。",
                max_length=512,
                verbose_name="API Base URL",
            ),
        ),
        migrations.AddField(
            model_name="userchatmodelpreset",
            name="api_key_encrypted",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Fernet 密文；留空则调用时使用环境变量中的密钥。",
                verbose_name="API 密钥（加密）",
            ),
        ),
        migrations.AddField(
            model_name="userchatmodelpreset",
            name="category",
            field=models.CharField(
                default="user_custom",
                help_text="与内置 catalog 的 category 同形，便于前端分组；可自定义。",
                max_length=32,
                verbose_name="分类 id",
            ),
        ),
        migrations.AddField(
            model_name="userchatmodelpreset",
            name="category_label",
            field=models.CharField(default="我的模型", max_length=128, verbose_name="分类展示名"),
        ),
        migrations.AddField(
            model_name="userchatmodelpreset",
            name="category_order",
            field=models.PositiveSmallIntegerField(
                default=100,
                help_text="在 GET /api/ai/models 中与内置项混排时越小越靠前。",
                verbose_name="排序权重",
            ),
        ),
        migrations.AddField(
            model_name="userchatmodelpreset",
            name="scope_summary",
            field=models.TextField(
                blank=True,
                default="",
                help_text="一段话说明该模型适合做什么；展示在模型选择器下方。",
                verbose_name="适用范围说明",
            ),
        ),
        migrations.AddField(
            model_name="userchatmodelpreset",
            name="scopes",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='字符串数组，如 ["画布对话","文本"]，供前端展示芯片。',
                verbose_name="适用范围标签",
            ),
        ),
    ]
