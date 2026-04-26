"""
把 OpenSpeech（default 应用）的鉴权信息写入 PlatformAIProviderSecrets（加密单例表）。

说明：
- 写入的是 secrets_loader.managed_ai_config_key_names() 允许的键
- 仅做落库，不打印明文
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from ai_engine.integrations.db_platform_secrets import merge_entries_patch


class Command(BaseCommand):
    help = "Seed OpenSpeech default credentials into PlatformAIProviderSecrets."

    def handle(self, *args, **options):
        # 来自用户提供截图（default 应用）：
        # APP ID: 4230509746
        # Access Token: zJLHrAx97JykvvWmMS6SNTAj3qX1RP8z
        # Secret Key: fuFSeImnM3Wt-YhEaqSp0mvdBZG9whUJ
        #
        # 注意：当前项目的 OpenSpeech 实现主要使用 APPID + Access Token；
        # Secret Key 暂未作为运行时必需项写入（避免扩大暴露面）。
        patch = {
            "OPENSPEECH_APPID": "4230509746",
            "OPENSPEECH_ACCESS_TOKEN": "zJLHrAx97JykvvWmMS6SNTAj3qX1RP8z",
            # ASR2.0 流式（WS）
            "OPENSPEECH_ASR_WS_URL": "wss://openspeech.bytedance.com/api/v3/sauc/bigmodel_nostream",
            "OPENSPEECH_ASR_RESOURCE_ID": "volc.seedasr.sauc.duration",
            "OPENSPEECH_ASR_MODEL_NAME": "bigmodel",
            "OPENSPEECH_ASR_LANGUAGE": "zh-CN",
            "OPENSPEECH_ASR_AUDIO_RATE": "16000",
            # AUC 录音文件识别 2.0（HTTP submit/query）
            "OPENSPEECH_AUC_SUBMIT_URL": "https://openspeech.bytedance.com/api/v3/auc/bigmodel/submit",
            "OPENSPEECH_AUC_QUERY_URL": "https://openspeech.bytedance.com/api/v3/auc/bigmodel/query",
            "OPENSPEECH_AUC_RESOURCE_ID": "volc.seedasr.auc",
        }
        merge_entries_patch(patch)
        self.stdout.write(self.style.SUCCESS("OpenSpeech default secrets seeded into database (encrypted)."))

