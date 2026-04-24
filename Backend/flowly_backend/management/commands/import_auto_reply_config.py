"""将参考项目 config.json 导入当前用户的 AutoReplyScreenProfile（及 friends_overrides）。"""

import json
from pathlib import Path

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from ai_engine.models import AutoReplyScreenProfile


class Command(BaseCommand):
    help = "从 config.json 导入屏幕配置与好友覆盖到数据库（对应原 AI自动回复 配置选项 + 好友风格）"

    def add_arguments(self, parser):
        parser.add_argument("config_path", type=str, help="config.json 绝对或相对路径")
        parser.add_argument("--username", type=str, default="", help="Django 用户名，默认取首个超级用户")

    def handle(self, *args, **options):
        path = Path(options["config_path"]).expanduser().resolve()
        if not path.is_file():
            raise CommandError(f"文件不存在: {path}")
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise CommandError("config 根须为 JSON 对象")

        uname = (options.get("username") or "").strip()
        if uname:
            user = User.objects.filter(username=uname).first()
            if user is None:
                raise CommandError(f"用户不存在: {uname}")
        else:
            user = User.objects.filter(is_superuser=True).order_by("id").first()
            if user is None:
                user = User.objects.order_by("id").first()
            if user is None:
                raise CommandError("无可用用户，请先创建用户或指定 --username")

        p, _ = AutoReplyScreenProfile.objects.get_or_create(user=user)
        p.chat_software = str(data.get("chat_software") or "wechat").strip()[:32] or "wechat"
        for key in ("chat_window_box", "input_box_pos", "user_name_box", "friend_list_box"):
            v = data.get(key)
            if isinstance(v, (list, tuple)) and len(v) == 4:
                try:
                    setattr(p, key, [int(x) for x in v])
                except Exception:
                    setattr(p, key, None)
            else:
                setattr(p, key, None)

        mf = data.get("monitored_friends") or []
        if not isinstance(mf, list):
            mf = []
        p.monitored_friends = [str(x).strip() for x in mf if str(x).strip()]

        fc = data.get("friends_config") or {}
        if isinstance(fc, dict):
            out_fc: dict = {}
            for name, row in fc.items():
                if not isinstance(row, dict):
                    continue
                nm = str(name).strip()
                if not nm:
                    continue
                out_fc[nm] = {
                    "name": nm,
                    "personality": str(row.get("personality") or "gentle_healing")[:64],
                    "scene": str(row.get("scene") or "daily_chat")[:64],
                    "custom_system_prompt": str(row.get("custom_system_prompt") or "")[:50000],
                    "knowledge_paths": list(row.get("knowledge_paths") or []),
                    "knowledge_match_keywords": list(row.get("knowledge_match_keywords") or []),
                }
            p.friends_overrides = out_fc
        p.knowledge_reply_enabled = bool(data.get("knowledge_reply_enabled", False))
        p.save()
        self.stdout.write(self.style.SUCCESS(f"已导入到用户 {user.username} 的屏幕配置（id={p.pk}）"))
