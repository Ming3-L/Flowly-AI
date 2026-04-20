from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Checkpoint",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("composite_id", models.CharField(max_length=255, unique=True)),
                ("thread_id", models.CharField(max_length=255)),
                ("checkpoint_ns", models.CharField(max_length=255, default="")),
                ("checkpoint_id", models.CharField(max_length=255)),
                ("parent_checkpoint_id", models.CharField(max_length=255, blank=True, null=True)),
                ("type", models.CharField(max_length=100, blank=True, null=True)),
                ("checkpoint", models.BinaryField()),
                ("metadata", models.JSONField(default=dict)),
            ],
            options={
                "db_table": "checkpoint",
            },
        ),
        migrations.CreateModel(
            name="Write",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("task_id", models.CharField(max_length=255)),
                ("task_path", models.CharField(max_length=255)),
                ("idx", models.IntegerField()),
                ("channel", models.CharField(max_length=255)),
                ("type", models.CharField(max_length=100, blank=True, null=True)),
                ("value", models.BinaryField()),
                (
                    "checkpoint",
                    models.ForeignKey(
                        db_constraint=False,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="writes",
                        to="checkpoint.checkpoint",
                        to_field="composite_id",
                    ),
                ),
            ],
            options={
                "db_table": "write",
            },
        ),
        migrations.AddConstraint(
            model_name="checkpoint",
            constraint=models.UniqueConstraint(
                fields=("thread_id", "checkpoint_ns", "checkpoint_id"), name="unique_checkpoint"
            ),
        ),
        migrations.AddConstraint(
            model_name="write",
            constraint=models.UniqueConstraint(fields=("checkpoint", "task_id", "idx"), name="unique_write"),
        ),
    ]
