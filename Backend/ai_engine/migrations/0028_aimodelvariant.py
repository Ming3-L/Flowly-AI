from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("ai_engine", "0027_platformaiprovidersecrets"),
    ]

    operations = [
        migrations.CreateModel(
            name="AIModelVariant",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "kind",
                    models.CharField(
                        choices=[("voice", "音色"), ("capability", "能力/模式")],
                        db_index=True,
                        default="voice",
                        max_length=24,
                    ),
                ),
                (
                    "variant_id",
                    models.CharField(
                        help_text="前端二级下拉保存的值（稳定 id）。如 voice_001 / zh_female_vv_uranus_bigtts。",
                        max_length=96,
                        verbose_name="二级选项 ID",
                    ),
                ),
                ("label", models.CharField(blank=True, default="", max_length=160, verbose_name="展示名")),
                (
                    "value",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text="实际传给下游接口的值。如 speaker / voice_type / resource_id 等（按 config 约定）。",
                        max_length=256,
                        verbose_name="值",
                    ),
                ),
                ("sort_order", models.IntegerField(default=0, verbose_name="排序")),
                (
                    "config",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="用于存放额外参数，如 resource_id、sample_rate、explicit_language 等。",
                        verbose_name="扩展配置",
                    ),
                ),
                ("is_active", models.BooleanField(db_index=True, default=True, verbose_name="启用")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "model_entry",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="variants",
                        to="ai_engine.aimodelcatalogentry",
                        verbose_name="所属模型目录项",
                    ),
                ),
            ],
            options={
                "verbose_name": "AI 模型二级选项",
                "verbose_name_plural": "AI 模型二级选项",
                "ordering": ["model_entry_id", "sort_order", "id"],
            },
        ),
        migrations.AddConstraint(
            model_name="aimodelvariant",
            constraint=models.UniqueConstraint(
                fields=("model_entry", "variant_id"),
                name="uniq_aimodel_variant_model_entry_and_variant_id",
            ),
        ),
    ]

