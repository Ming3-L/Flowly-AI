from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_profile_default_doubao_model"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="nickname",
            field=models.CharField(blank=True, default="", help_text="展示在右上角与各页面的用户昵称；留空则回退 username。", max_length=64, verbose_name="昵称"),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="avatar_path",
            field=models.CharField(blank=True, default="", help_text="相对 MEDIA_ROOT 的路径（如 avatars/u1/xxx.png）；留空表示未设置。", max_length=512, verbose_name="头像路径"),
        ),
    ]

