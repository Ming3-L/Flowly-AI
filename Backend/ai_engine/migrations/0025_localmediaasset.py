from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("ai_engine", "0024_merge_0020_sync_vision_catalog_for_canvas_0023_remove_auto_reply_screen_events_and_logs"),
    ]

    operations = [
        migrations.CreateModel(
            name="LocalMediaAsset",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("kind", models.CharField(choices=[("image", "图片"), ("audio", "音频"), ("video", "视频"), ("file", "文件"), ("avatar", "头像")], db_index=True, default="file", max_length=16)),
                ("original_name", models.CharField(blank=True, default="", max_length=255)),
                ("mime", models.CharField(blank=True, default="", max_length=128)),
                ("size_bytes", models.BigIntegerField(default=0)),
                ("rel_path", models.CharField(db_index=True, help_text="相对 MEDIA_ROOT 的路径", max_length=512)),
                ("source_url", models.CharField(blank=True, default="", help_text="若由第三方生成/抓取，记录来源 URL（可空）", max_length=2048)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="local_media_assets", to="auth.user", verbose_name="所属用户")),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="localmediaasset",
            index=models.Index(fields=["user", "created_at"], name="ai_engine_lo_user_id_7d0c2b_idx"),
        ),
        migrations.AddIndex(
            model_name="localmediaasset",
            index=models.Index(fields=["user", "kind", "created_at"], name="ai_engine_lo_user_id_48bd0e_idx"),
        ),
    ]

