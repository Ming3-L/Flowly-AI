"""
验证码邮件的 SMTP **不在** Django 全局 ``EMAIL_*`` 中配置。

发信参数由管理员在「后台 → 接入配置 (密钥)」写入加密表
``PlatformAIProviderSecrets``，键名见 ``ai_engine.integrations.secrets_loader`` 中的
``FLOWLY_SMTP_*``。发送逻辑见 ``accounts.email_service``。
"""
