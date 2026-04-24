from django.db import migrations, models


def forwards(apps, schema_editor):
    UserProfile = apps.get_model("accounts", "UserProfile")
    UserProfile.objects.filter(ai_model__in=["gpt-4o", "gpt-4o-mini", ""]).update(ai_model="ark-doubao-smart-router")


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="userprofile",
            name="ai_model",
            field=models.CharField(
                default="ark-doubao-smart-router",
                help_text="模型目录键，如 ark-doubao-smart-router；对话与画布解析用",
                max_length=64,
                verbose_name="AI 模型",
            ),
        ),
        migrations.RunPython(forwards, noop_reverse),
    ]
