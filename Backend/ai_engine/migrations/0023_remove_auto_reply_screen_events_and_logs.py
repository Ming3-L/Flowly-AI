from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("ai_engine", "0022_merge_0020_workflow_soft_delete_0021_seedance_model_id_fix"),
    ]

    operations = [
        migrations.DeleteModel(name="AutoReplyScreenEvent"),
        migrations.DeleteModel(name="AutoReplyMonitorLogLine"),
    ]

