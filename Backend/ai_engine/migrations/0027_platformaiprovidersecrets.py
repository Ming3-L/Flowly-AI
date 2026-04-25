# Generated manually for PlatformAIProviderSecrets

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ai_engine", "0026_autoreplyscreenprofile_agent_runtime_snapshot"),
    ]

    operations = [
        migrations.CreateModel(
            name="PlatformAIProviderSecrets",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("encrypted_payload", models.TextField(blank=True, default="", verbose_name="加密配置包")),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "平台 AI 接入配置",
                "verbose_name_plural": "平台 AI 接入配置",
            },
        ),
    ]
