from django.contrib.auth.models import User
from django.db import models


class UserProfile(models.Model):
    """扩展用户资料，存储 AI 模型偏好和 API Key"""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name='关联用户',
    )
    # AI 模型偏好
    ai_model = models.CharField(
        max_length=64,
        default="ark-doubao-smart-router",
        verbose_name="AI 模型",
        help_text="模型目录键，如 ark-doubao-smart-router（对话/画布与 ai_model_catalog 一致）",
    )
    # 自定义 API Key（优先于环境变量中的全局 Key）
    openai_api_key = models.CharField(
        max_length=256,
        blank=True,
        default='',
        verbose_name='OpenAI API Key',
        help_text='留空则使用系统默认 Key',
    )
    # 自定义 API Base URL
    openai_base_url = models.CharField(
        max_length=256,
        blank=True,
        default='',
        verbose_name='API Base URL',
        help_text='留空则使用默认的 https://api.openai.com/v1',
    )
    # 语言偏好
    language = models.CharField(
        max_length=16,
        default='zh',
        verbose_name='界面语言',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '用户资料'
        verbose_name_plural = '用户资料'

    def __str__(self):
        return f'{self.user.username} 的资料'

    @property
    def effective_api_key(self) -> str:
        return self.openai_api_key or ''

    @property
    def effective_base_url(self) -> str:
        return self.openai_base_url or ''
