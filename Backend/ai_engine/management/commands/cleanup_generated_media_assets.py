from __future__ import annotations

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "清理 90 天前的 generated 本地媒体资源（LocalMediaAsset + MEDIA_ROOT 文件）。"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=90,
            help="保留天数，默认 90（约 3 个月）",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="只统计不删除",
        )

    def handle(self, *args, **options):
        from ai_engine.tasks import cleanup_generated_media_assets

        days = int(options.get("days") or 90)
        dry_run = bool(options.get("dry_run") or False)
        res = cleanup_generated_media_assets(days=days, dry_run=dry_run)
        self.stdout.write(self.style.SUCCESS(f"done: {res}"))

