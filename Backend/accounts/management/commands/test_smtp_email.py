from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "测试 SMTP（读取 FLOWLY_SMTP_*）并发送一封测试邮件。"

    def add_arguments(self, parser):
        parser.add_argument("--to", required=True, help="收件人邮箱")
        parser.add_argument(
            "--purpose",
            default="register",
            choices=["register", "password_reset"],
            help="邮件主题类型（仅影响主题/正文模板）",
        )

    def handle(self, *args, **options):
        to_email = str(options.get("to") or "").strip()
        purpose = str(options.get("purpose") or "register").strip()
        if not to_email:
            raise CommandError("--to 不能为空")

        from accounts.email_service import load_smtp_config_from_database, send_verification_email

        cfg = load_smtp_config_from_database()
        if not cfg:
            raise CommandError(
                "SMTP 未配置：请在后台「接入配置 (密钥)」写入 FLOWLY_SMTP_HOST/FLOWLY_SMTP_USER/FLOWLY_SMTP_PASSWORD"
            )

        # 不输出敏感信息：只输出可公开诊断字段
        self.stdout.write(
            self.style.NOTICE(
                "SMTP effective config:"
                f" host={cfg.get('host')!s}"
                f" port={cfg.get('port')!s}"
                f" use_ssl={cfg.get('use_ssl')!s}"
                f" use_tls={cfg.get('use_tls')!s}"
                f" from_email={cfg.get('from_email')!s}"
            )
        )

        # 使用固定 code，便于你在邮箱里肉眼确认链路
        code = "1234"
        try:
            send_verification_email(purpose=purpose, to_email=to_email, code=code)
        except Exception as exc:
            raise CommandError(f"SMTP send failed: {type(exc).__name__}: {exc}") from exc

        self.stdout.write(self.style.SUCCESS(f"已尝试发送测试邮件到 {to_email}（code={code}）"))

