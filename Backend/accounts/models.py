from django.contrib.auth.models import User
from django.db import models


class SocialAccount(models.Model):
    """第三方账号关联表，存储用户的 OAuth 账号绑定信息"""

    PROVIDER_CHOICES = [
        ('github', 'GitHub'),
        ('google', 'Google'),
        ('qq', 'QQ'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='social_accounts',
        verbose_name='关联用户',
    )
    provider = models.CharField(
        max_length=20,
        choices=PROVIDER_CHOICES,
        verbose_name='OAuth 提供商',
    )
    provider_user_id = models.CharField(
        max_length=255,
        verbose_name='第三方用户 ID',
    )
    provider_username = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name='第三方用户名',
    )
    provider_email = models.EmailField(
        blank=True,
        default='',
        verbose_name='第三方邮箱',
    )
    provider_avatar_url = models.URLField(
        blank=True,
        default='',
        verbose_name='第三方头像 URL',
    )
    access_token = models.TextField(
        blank=True,
        default='',
        verbose_name='Access Token（加密存储）',
    )
    refresh_token = models.TextField(
        blank=True,
        default='',
        verbose_name='Refresh Token（加密存储）',
    )
    token_expires_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Token 过期时间',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [['provider', 'provider_user_id']]
        verbose_name = '第三方账号'
        verbose_name_plural = '第三方账号'
        indexes = [
            models.Index(fields=['provider', 'provider_user_id']),
            models.Index(fields=['user', 'provider']),
        ]

    def __str__(self):
        return f'{self.user.username} - {self.get_provider_display()}'


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

    # 昵称与头像（存本地文件路径，实际文件在 MEDIA_ROOT 下）
    nickname = models.CharField(
        max_length=64,
        blank=True,
        default="",
        verbose_name="昵称",
        help_text="展示在右上角与各页面的用户昵称；留空则回退 username。",
    )
    avatar_path = models.CharField(
        max_length=512,
        blank=True,
        default="",
        verbose_name="头像路径",
        help_text="相对 MEDIA_ROOT 的路径（如 avatars/u1/xxx.png）；留空表示未设置。",
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
