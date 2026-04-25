"""
第三方登录 OAuth 核心逻辑。

支持 GitHub、Google、QQ 三个平台的 OAuth 2.0 流程。
"""

import hashlib
import logging
import secrets
import time
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from .models import SocialAccount

User = get_user_model()
logger = logging.getLogger(__name__)


# ── OAuth Provider 配置 ────────────────────────────────────────────────────────

@dataclass
class OAuthProvider:
    name: str
    client_id: str
    client_secret: str
    authorize_url: str
    token_url: str
    userinfo_url: str
    redirect_uri: str
    scopes: list[str]
    # QQ 特殊字段名映射
    qq_openid_url: str = ''


PROVIDERS: dict[str, OAuthProvider] = {}


def _build_providers() -> dict[str, OAuthProvider]:
    """从 settings 构建 OAuth Provider 配置"""
    redirect_uri = getattr(settings, 'OAUTH_REDIRECT_URI', 'http://localhost:5173/social-callback')

    providers = {}

    # GitHub
    github_client_id = getattr(settings, 'GITHUB_CLIENT_ID', '')
    github_client_secret = getattr(settings, 'GITHUB_CLIENT_SECRET', '')
    if github_client_id:
        providers['github'] = OAuthProvider(
            name='github',
            client_id=github_client_id,
            client_secret=github_client_secret,
            authorize_url='https://github.com/login/oauth/authorize',
            token_url='https://github.com/login/oauth/access_token',
            userinfo_url='https://api.github.com/user',
            redirect_uri=redirect_uri,
            scopes=['read:user', 'user:email'],
        )

    # Google
    google_client_id = getattr(settings, 'GOOGLE_CLIENT_ID', '')
    google_client_secret = getattr(settings, 'GOOGLE_CLIENT_SECRET', '')
    if google_client_id:
        providers['google'] = OAuthProvider(
            name='google',
            client_id=google_client_id,
            client_secret=google_client_secret,
            authorize_url='https://accounts.google.com/o/oauth2/v2/auth',
            token_url='https://oauth2.googleapis.com/token',
            userinfo_url='https://www.googleapis.com/oauth2/v2/userinfo',
            redirect_uri=redirect_uri,
            scopes=['openid', 'email', 'profile'],
        )

    # QQ
    qq_client_id = getattr(settings, 'QQ_CLIENT_ID', '')
    qq_client_secret = getattr(settings, 'QQ_CLIENT_SECRET', '')
    if qq_client_id:
        providers['qq'] = OAuthProvider(
            name='qq',
            client_id=qq_client_id,
            client_secret=qq_client_secret,
            authorize_url='https://graph.qq.com/oauth2.0/authorize',
            token_url='https://graph.qq.com/oauth2.0/token',
            userinfo_url='https://graph.qq.com/user/get_user_info',
            redirect_uri=redirect_uri,
            scopes=['get_user_info'],
            qq_openid_url='https://graph.qq.com/oauth2.0/me',
        )

    return providers


# 延迟初始化，在 Django settings 加载后使用
def get_provider(provider_name: str) -> Optional[OAuthProvider]:
    """获取指定 provider 的配置，如果未配置则返回 None"""
    if not PROVIDERS:
        PROVIDERS.update(_build_providers())
    return PROVIDERS.get(provider_name)


def get_enabled_providers() -> list[str]:
    """返回所有已配置且启用的 provider 列表"""
    if not PROVIDERS:
        PROVIDERS.update(_build_providers())
    return list(PROVIDERS.keys())


# ── State 管理（防止 CSRF）────────────────────────────────────────────────────

# 简单的内存存储，用于验证 state。生产环境建议使用 Redis。
_state_store: dict[str, dict] = {}


def generate_state(provider: str) -> str:
    """生成随机 state 并存储，返回 state 字符串"""
    state = secrets.token_urlsafe(32)
    _state_store[state] = {
        'provider': provider,
        'created_at': time.time(),
    }
    return state


def validate_state(state: str) -> Optional[str]:
    """
    验证 state 是否有效，返回 provider_name。
    超过 10 分钟的 state 视为无效。
    """
    data = _state_store.pop(state, None)
    if not data:
        return None

    # 检查是否过期（10 分钟）
    if time.time() - data['created_at'] > 600:
        return None

    return data['provider']


# ── 授权 URL 生成 ──────────────────────────────────────────────────────────────

def get_authorization_url(provider_name: str) -> tuple[str, str]:
    """
    获取指定 provider 的授权 URL。
    返回 (auth_url, state)
    """
    provider = get_provider(provider_name)
    if not provider:
        raise ValueError(f"未配置的 OAuth Provider: {provider_name}")

    state = generate_state(provider_name)

    params = {
        'client_id': provider.client_id,
        'redirect_uri': provider.redirect_uri,
        'scope': ' '.join(provider.scopes),
        'state': state,
        'response_type': 'code',
    }

    # QQ 使用 OAuth 1.0a，参数名不同
    if provider_name == 'qq':
        params.pop('scope', None)
        params['scope'] = 'get_user_info'
        # QQ OAuth 2.0 使用 display=pc
        params['display'] = 'pc'
        params.pop('response_type', None)
        params['response_type'] = 'code'

    # Google 使用 access_type=offline 获取 refresh_token
    if provider_name == 'google':
        params['access_type'] = 'offline'
        params['prompt'] = 'consent'

    auth_url = f"{provider.authorize_url}?{urlencode(params)}"
    return auth_url, state


# ── Token 交换 ────────────────────────────────────────────────────────────────

@dataclass
class OAuthToken:
    access_token: str
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None


def exchange_code_for_token(provider_name: str, code: str, state: str) -> OAuthToken:
    """
    用授权码换取 access_token。
    """
    provider = get_provider(provider_name)
    if not provider:
        raise ValueError(f"未配置的 OAuth Provider: {provider_name}")

    # 验证 state
    if validate_state(state) != provider_name:
        raise ValueError("无效的 state 参数，可能存在 CSRF 攻击")

    data = {
        'client_id': provider.client_id,
        'client_secret': provider.client_secret,
        'code': code,
        'redirect_uri': provider.redirect_uri,
        'grant_type': 'authorization_code',
    }

    response = requests.post(
        provider.token_url,
        data=data,
        headers={'Accept': 'application/json'},
        timeout=10,
    )
    response.raise_for_status()
    token_data = response.json()

    # GitHub 的 token 响应格式不是标准 JSON，是 "access_token=xxx&..."
    if provider_name == 'github':
        token_data = _parse_github_token(response.text)

    access_token = token_data.get('access_token')
    refresh_token = token_data.get('refresh_token')
    expires_in = token_data.get('expires_in')

    if not access_token:
        raise ValueError(f"Token 交换失败: {token_data}")

    return OAuthToken(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
    )


def _parse_github_token(text: str) -> dict:
    """解析 GitHub 的非标准 token 响应格式"""
    result = {}
    for pair in text.split('&'):
        if '=' in pair:
            key, value = pair.split('=', 1)
            result[key] = value
    return result


# ── 获取用户信息 ──────────────────────────────────────────────────────────────

@dataclass
class OAuthUserInfo:
    provider: str
    provider_user_id: str
    username: str
    email: str
    avatar_url: str


def get_user_info(provider_name: str, access_token: str) -> OAuthUserInfo:
    """
    从 provider 获取用户信息。
    """
    provider = get_provider(provider_name)
    if not provider:
        raise ValueError(f"未配置的 OAuth Provider: {provider_name}")

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/json',
    }

    if provider_name == 'github':
        # GitHub 可以一次请求获取用户信息和邮箱
        user_info = _get_github_user_info(access_token)
    elif provider_name == 'google':
        user_info = _get_google_user_info(provider, access_token)
    elif provider_name == 'qq':
        user_info = _get_qq_user_info(provider, access_token)
    else:
        raise ValueError(f"不支持的 Provider: {provider_name}")

    return OAuthUserInfo(
        provider=provider_name,
        provider_user_id=user_info['id'],
        username=user_info['username'],
        email=user_info.get('email', ''),
        avatar_url=user_info.get('avatar_url', ''),
    )


def _get_github_user_info(access_token: str) -> dict:
    """获取 GitHub 用户信息"""
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/json',
    }

    # 获取基本信息
    resp = requests.get('https://api.github.com/user', headers=headers, timeout=10)
    resp.raise_for_status()
    user_data = resp.json()

    result = {
        'id': str(user_data['id']),
        'username': user_data.get('login', ''),
        'avatar_url': user_data.get('avatar_url', ''),
        'email': '',
    }

    # 获取邮箱（可能有多个，取主要邮箱）
    email_resp = requests.get(
        'https://api.github.com/user/emails',
        headers=headers,
        timeout=10,
    )
    if email_resp.ok:
        emails = email_resp.json()
        for em in emails:
            if em.get('primary') and em.get('verified'):
                result['email'] = em.get('email', '')
                break
        # 如果没有主要邮箱，取第一个已验证的
        if not result['email']:
            for em in emails:
                if em.get('verified'):
                    result['email'] = em.get('email', '')
                    break

    return result


def _get_google_user_info(provider: OAuthProvider, access_token: str) -> dict:
    """获取 Google 用户信息"""
    headers = {
        'Authorization': f'Bearer {access_token}',
    }

    resp = requests.get(provider.userinfo_url, headers=headers, timeout=10)
    resp.raise_for_status()
    user_data = resp.json()

    return {
        'id': str(user_data.get('id', user_data.get('sub', ''))),
        'username': user_data.get('name', '') or user_data.get('email', '').split('@')[0],
        'email': user_data.get('email', ''),
        'avatar_url': user_data.get('picture', ''),
    }


def _get_qq_user_info(provider: OAuthProvider, access_token: str) -> dict:
    """获取 QQ 用户信息"""
    # QQ OAuth 2.0 需要先获取 OpenID
    openid_resp = requests.get(
        provider.qq_openid_url,
        params={'access_token': access_token},
        timeout=10,
    )
    openid_resp.raise_for_status()

    # QQ 返回 callback({"client_id":"...","openid":"..."});
    openid_text = openid_resp.text
    import json
    try:
        # 提取 JSON
        start = openid_text.find('(') + 1
        end = openid_text.rfind(')')
        openid_data = json.loads(openid_text[start:end])
    except (json.JSONDecodeError, ValueError):
        raise ValueError(f"无法解析 QQ OpenID 响应: {openid_text}")

    openid = openid_data.get('openid', '')
    if not openid:
        raise ValueError(f"QQ OpenID 获取失败: {openid_data}")

    # 获取用户基本信息
    user_resp = requests.get(
        provider.userinfo_url,
        params={
            'access_token': access_token,
            'oauth_consumer_key': provider.client_id,
            'openid': openid,
        },
        timeout=10,
    )
    user_resp.raise_for_status()
    user_data = user_resp.json()

    if user_data.get('ret') != 0:
        raise ValueError(f"QQ 用户信息获取失败: {user_data.get('msg')}")

    return {
        'id': openid,
        'username': user_data.get('nickname', ''),
        'email': '',  # QQ 不提供邮箱
        'avatar_url': user_data.get('figureurl_qq_2', user_data.get('figureurl_qq', '')),
    }


# ── 用户关联/创建 ─────────────────────────────────────────────────────────────

@dataclass
class OAuthResult:
    user: 'User'
    is_new_user: bool
    is_new_account: bool


def get_or_create_user(provider_name: str, user_info: OAuthUserInfo, token: OAuthToken) -> OAuthResult:
    """
    根据第三方账号信息获取或创建本地用户，并关联 SocialAccount。

    逻辑：
    1. 查找是否已存在该 provider + provider_user_id 的关联
    2. 如果存在，返回关联的用户
    3. 如果不存在，检查是否有相同邮箱的本地用户
       - 有：绑定到该用户
       - 无：创建新用户
    """
    from rest_framework_simplejwt.tokens import RefreshToken

    with transaction.atomic():
        # 1. 查找已有的第三方账号关联
        try:
            social_account = SocialAccount.objects.select_related('user').get(
                provider=provider_name,
                provider_user_id=user_info.provider_user_id,
            )
            # 更新 token 和用户信息
            social_account.access_token = token.access_token
            if token.refresh_token:
                social_account.refresh_token = token.refresh_token
            if token.expires_in:
                social_account.token_expires_at = timezone.now() + timezone.timedelta(seconds=token.expires_in)
            social_account.save()

            return OAuthResult(
                user=social_account.user,
                is_new_user=False,
                is_new_account=False,
            )
        except SocialAccount.DoesNotExist:
            pass

        # 2. 尝试通过邮箱查找本地用户
        user = None
        is_new_user = False

        if user_info.email:
            # 查找是否有相同邮箱的用户
            try:
                user = User.objects.get(email=user_info.email)
            except User.DoesNotExist:
                pass

        # 3. 如果没有找到用户，创建新用户
        if not user:
            is_new_user = True
            # 生成用户名：provider_id 格式
            base_username = f"{provider_name}_{user_info.provider_user_id}"
            username = base_username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}_{counter}"
                counter += 1

            # 创建用户（不设置密码，因为是第三方登录）
            user = User.objects.create_user(
                username=username,
                email=user_info.email or '',
            )

            # 如果有邮箱且需要激活
            if user_info.email and getattr(settings, 'ACCOUNT_EMAIL_VERIFICATION', False):
                user.is_active = True  # 第三方账号已验证，跳过邮箱验证
                user.save(update_fields=['is_active'])

        # 4. 创建第三方账号关联
        expires_at = None
        if token.expires_in:
            expires_at = timezone.now() + timezone.timedelta(seconds=token.expires_in)

        social_account = SocialAccount.objects.create(
            user=user,
            provider=provider_name,
            provider_user_id=user_info.provider_user_id,
            provider_username=user_info.username,
            provider_email=user_info.email,
            provider_avatar_url=user_info.avatar_url,
            access_token=token.access_token,
            refresh_token=token.refresh_token or '',
            token_expires_at=expires_at,
        )

        # 5. 如果是新用户且有昵称/头像，更新 UserProfile
        if is_new_user:
            try:
                profile = user.profile
            except Exception:
                from .models import UserProfile
                profile = UserProfile.objects.create(user=user)

            if user_info.username and not profile.nickname:
                profile.nickname = user_info.username
            if user_info.avatar_url:
                profile.avatar_path = user_info.avatar_url  # 存 URL，后续可下载
            profile.save()

        return OAuthResult(
            user=user,
            is_new_user=is_new_user,
            is_new_account=True,
        )


def generate_jwt_for_user(user: User) -> dict:
    """为用户生成 JWT token"""
    from rest_framework_simplejwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(user)
    return {
        'access': str(refresh.access_token),
        'refresh': str(refresh),
    }
