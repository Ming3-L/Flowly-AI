from django.db import models


class Checkpoint(models.Model):
    composite_id = models.CharField(max_length=255, unique=True)
    thread_id = models.CharField(max_length=255)
    checkpoint_ns = models.CharField(max_length=255, default="")
    checkpoint_id = models.CharField(max_length=255)
    parent_checkpoint_id = models.CharField(max_length=255, blank=True, null=True)
    type = models.CharField(max_length=100, blank=True, null=True)
    checkpoint = models.BinaryField()
    metadata = models.JSONField(default=dict)

    class Meta:
        db_table = "checkpoint"


class Write(models.Model):
    checkpoint = models.ForeignKey(
        Checkpoint,
        to_field="composite_id",
        on_delete=models.CASCADE,
        related_name="writes",
        db_constraint=False,
    )
    task_id = models.CharField(max_length=255)
    task_path = models.CharField(max_length=255)
    idx = models.IntegerField()
    channel = models.CharField(max_length=255)
    type = models.CharField(max_length=100, blank=True, null=True)
    value = models.BinaryField()

    class Meta:
        db_table = "write"
        constraints = [
            models.UniqueConstraint(fields=("checkpoint", "task_id", "idx"), name="unique_write"),
        ]
