# 将 Seedream / Seedance 目录项同步为画布「图片」「视频」节点可选，并写入方舟 model_id

from django.db import migrations


def sync_rows(apps, schema_editor):
    AIModelCatalogEntry = apps.get_model("ai_engine", "AIModelCatalogEntry")
    from ai_engine.catalog_seed import CATALOG_SEED_ROWS

    keys = {
        "ark-seedream-5-0-lite",
        "ark-seedream-4-5",
        "ark-seedream-4-0",
        "ark-seededit-3-0-i2i",
        "ark-seedance-2-0",
        "ark-seedance-1-5-pro",
        "ark-seedance-1-0-pro-fast",
        "ark-seedance-1-0-pro",
    }
    for raw in CATALOG_SEED_ROWS:
        ck = raw.get("catalog_key")
        if ck not in keys:
            continue
        data = {k: v for k, v in raw.items() if k != "catalog_key"}
        AIModelCatalogEntry.objects.update_or_create(catalog_key=ck, defaults=data)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("ai_engine", "0019_aimodel_catalog_video_script_llm"),
    ]

    operations = [
        migrations.RunPython(sync_rows, noop_reverse),
    ]
