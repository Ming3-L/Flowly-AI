from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("ai_engine", "0019_aimodel_catalog_video_script_llm"),
    ]

    operations = [
        migrations.AddField(
            model_name="workflow",
            name="is_deleted",
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddField(
            model_name="workflow",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]

