"""
将当前进程环境变量中的 AI 接入配置写入数据库（与后台「从环境变量导入」相同逻辑）。

用法:
  python manage.py import_ai_secrets_from_env
  python manage.py import_ai_secrets_from_env --replace
"""

from django.core.management.base import BaseCommand

from ai_engine.integrations.db_platform_secrets import seed_from_process_environ


class Command(BaseCommand):
    help = "把已加载的非空环境变量中的 AI 配置写入 PlatformAIProviderSecrets（加密）。"

    def add_arguments(self, parser):
        parser.add_argument(
            "--replace",
            action="store_true",
            help="先清空库内已有项，再仅写入当前环境中存在的键",
        )

    def handle(self, *args, **options):
        n = seed_from_process_environ(replace=bool(options.get("replace")))
        self.stdout.write(self.style.SUCCESS(f"已写入 {n} 个键（replace={bool(options.get('replace'))}）。"))

