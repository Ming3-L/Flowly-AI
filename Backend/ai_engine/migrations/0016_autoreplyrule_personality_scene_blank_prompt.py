from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ai_engine", "0015_autoreplyrule_autoreplyjob_uilabel_autoreply_nav"),
    ]

    operations = [
        migrations.AddField(
            model_name="autoreplyrule",
            name="personality_key",
            field=models.CharField(
                blank=True,
                help_text="与参考项目 ChatPersonality 键一致；可与情景键组合，在系统提示为空时自动生成语气。",
                max_length=64,
                verbose_name="人格预设键",
            ),
        ),
        migrations.AddField(
            model_name="autoreplyrule",
            name="scene_key",
            field=models.CharField(
                blank=True,
                help_text="与参考项目 ChatScene 键一致。",
                max_length=64,
                verbose_name="情景预设键",
            ),
        ),
        migrations.AlterField(
            model_name="autoreplyrule",
            name="system_prompt",
            field=models.TextField(
                blank=True,
                help_text="可选。若填写则优先生效；若为空且填写人格/情景键，则按预设组合生成系统提示。",
                verbose_name="系统提示",
            ),
        ),
    ]
