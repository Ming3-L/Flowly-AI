"""OAuth 第三方登录配置"""

from django.conf import settings

# OAuth 回调地址
OAUTH_REDIRECT_URI = getattr(
    settings,
    'OAUTH_REDIRECT_URI',
    'http://localhost:5173/social-callback'
)

# GitHub OAuth 配置
# 申请地址: https://github.com/settings/applications/new
GITHUB_CLIENT_ID = getattr(settings, 'GITHUB_CLIENT_ID', '')
GITHUB_CLIENT_SECRET = getattr(settings, 'GITHUB_CLIENT_SECRET', '')

# Google OAuth 配置
# 申请地址: https://console.cloud.google.com/apis/credentials/oauthclient
GOOGLE_CLIENT_ID = getattr(settings, 'GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = getattr(settings, 'GOOGLE_CLIENT_SECRET', '')

# QQ OAuth 配置
# 申请地址: https://connect.qq.com/
QQ_CLIENT_ID = getattr(settings, 'QQ_CLIENT_ID', '')
QQ_CLIENT_SECRET = getattr(settings, 'QQ_CLIENT_SECRET', '')
