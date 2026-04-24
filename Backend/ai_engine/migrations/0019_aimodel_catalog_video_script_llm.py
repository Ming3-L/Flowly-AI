# Generated manually — 画布「视频」节点专用 LLM 目录项

from django.db import migrations


def upsert_video_script_row(apps, schema_editor):
    AIModelCatalogEntry = apps.get_model("ai_engine", "AIModelCatalogEntry")
    AIModelCatalogEntry.objects.update_or_create(
        catalog_key="ark-doubao-video-script-llm",
        defaults={
            "label": "视频脚本 / 分镜与旁白（LLM）",
            "description": "视频节点专用文案：分镜、旁白、镜头描述",
            "route": "doubao",
            "model_id": "",
            "category": "cat_language",
            "category_label": "语言模型（方舟）",
            "category_order": 0,
            "sort_order": 4,
            "scopes": ["分镜", "旁白", "镜头表", "动态描述"],
            "scope_summary": (
                "仅出现在「视频」节点：输出为文字分镜/旁白/镜头描述。说明：当前画布视频节点走方舟对话接口，"
                "不直接生成 mp4；文生视频请在火山控制台开通 Seedance 等后走专用视频 API。"
            ),
            "canvas_node_kinds": ["video"],
            "canvas_universal": False,
            "api_kind": "ark_chat",
            "show_in_canvas_llm_nodes": True,
            "is_active": True,
        },
    )


def remove_video_script_row(apps, schema_editor):
    AIModelCatalogEntry = apps.get_model("ai_engine", "AIModelCatalogEntry")
    AIModelCatalogEntry.objects.filter(catalog_key="ark-doubao-video-script-llm").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("ai_engine", "0018_auto_reply_screen_monitor_kb_chat_log"),
    ]

    operations = [
        migrations.RunPython(upsert_video_script_row, remove_video_script_row),
    ]
