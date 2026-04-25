"""
第三方登录 API。

提供 OAuth 授权 URL 获取、回调处理、账号绑定/解绑等功能。
"""

import logging

from django.http import HttpRequest, HttpResponse
from ninja import Router, Schema
from ninja.errors import AuthenticationError

from ai_engine.auth import JWTAuth
from .models import SocialAccount
from .social_auth import (
    OAuthResult,
    get_authorization_url,
    get_enabled_providers,
    get_or_create_user,
    generate_jwt_for_user,
    exchange_code_for_token,
    get_user_info,
    get_provider,
)
from django.contrib.auth import get_user_model

User = get_user_model()
router = Router(tags=["第三方登录"])
logger = logging.getLogger(__name__)


# ── Schemas ────────────────────────────────────────────────────────────────────

class OAuthProvidersSchema(Schema):
    providers: list[str]


class OAuthLoginSchema(Schema):
    auth_url: str
    state: str


class SocialConnectionSchema(Schema):
    id: int
    provider: str
    provider_username: str
    provider_email: str
    created_at: str


class SocialConnectionsSchema(Schema):
    connections: list[SocialConnectionSchema]


class BindRequestSchema(Schema):
    provider: str
    code: str
    state: str


class ErrorSchema(Schema):
    message: str
    detail: str | None = None


# ── 获取授权 URL ───────────────────────────────────────────────────────────────

@router.get(
    "/oauth/{provider}/login",
    response={
        200: OAuthLoginSchema,
        400: ErrorSchema,
    },
)
def oauth_login(request: HttpRequest, provider: str):
    """
    GET /api/auth/oauth/<provider>/login

    返回指定 Provider 的授权 URL。
    """
    enabled = get_enabled_providers()
    if provider not in enabled:
        return 400, ErrorSchema(
            message="不支持的 OAuth Provider",
            detail=f"当前支持: {', '.join(enabled) if enabled else '未配置任何 Provider'}",
        )

    try:
        auth_url, state = get_authorization_url(provider)
        return 200, OAuthLoginSchema(auth_url=auth_url, state=state)
    except ValueError as e:
        return 400, ErrorSchema(
            message="获取授权 URL 失败",
            detail=str(e),
        )
    except Exception as exc:
        logger.exception(f"oauth_login: {provider}")
        return 400, ErrorSchema(
            message="服务器配置错误",
            detail=str(exc) if request.resolver_match else "OAuth Provider 配置不完整",
        )


# ── OAuth 回调 ────────────────────────────────────────────────────────────────

@router.get("/oauth/{provider}/callback")
def oauth_callback(request: HttpRequest, provider: str, code: str = '', state: str = ''):
    """
    GET /api/auth/oauth/<provider>/callback

    OAuth 回调端点。由 OAuth Provider 重定向调用。
    验证 code，换取 token，获取用户信息，创建/关联用户，返回 JWT。
    返回一个简单的 HTML 页面，通过 postMessage 将 token 传递给 opener 窗口。
    """
    if not code:
        return _error_page("Missing authorization code")

    if not state:
        return _error_page("Missing state parameter")

    try:
        # 1. 交换 token
        token_obj = exchange_code_for_token(provider, code, state)

        # 2. 获取用户信息
        user_info = get_user_info(provider, token_obj.access_token)

        # 3. 获取或创建用户
        result: OAuthResult = get_or_create_user(provider, user_info, token_obj)

        # 4. 生成 JWT
        tokens = generate_jwt_for_user(result.user)

        # 5. 返回成功页面
        return _success_page(
            provider=provider,
            is_new_user=result.is_new_user,
            access_token=tokens['access'],
            refresh_token=tokens.get('refresh', ''),
        )

    except ValueError as e:
        logger.warning(f"oauth_callback {provider}: {e}")
        return _error_page(str(e))
    except Exception as exc:
        logger.exception(f"oauth_callback {provider}")
        return _error_page("登录失败，请稍后重试")


def _success_page(provider: str, is_new_user: bool, access_token: str, refresh_token: str) -> HttpResponse:
    """返回成功页面"""
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>登录成功 - Flowly</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-align: center;
            padding: 20px;
        }}
        .container {{
            background: rgba(255,255,255,0.15);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 40px 50px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.2);
            max-width: 400px;
        }}
        .icon {{
            font-size: 64px;
            margin-bottom: 20px;
        }}
        h1 {{
            font-size: 24px;
            margin-bottom: 10px;
        }}
        p {{
            font-size: 14px;
            opacity: 0.9;
            margin-bottom: 20px;
        }}
        .spinner {{
            width: 40px;
            height: 40px;
            border: 3px solid rgba(255,255,255,0.3);
            border-top-color: white;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 20px auto;
        }}
        @keyframes spin {{
            to {{ transform: rotate(360deg); }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="icon">🎉</div>
        <h1>登录成功</h1>
        <p>{'欢迎使用 Flowly，您的账号已创建' if is_new_user else '欢迎回来'}！</p>
        <div class="spinner"></div>
        <p>正在跳转...</p>
    </div>
    <script>
        try {{
            // 向 opener 窗口发送登录成功消息
            if (window.opener) {{
                window.opener.postMessage({{
                    type: 'OAUTH_SUCCESS',
                    provider: '{provider}',
                    isNewUser: {str(is_new_user).lower()},
                    access: '{access_token}',
                    refresh: '{refresh_token}',
                }}, '*');
            }}

            // 保存到 localStorage（作为备用，防止 postMessage 失败）
            localStorage.setItem('flowly_access_token', '{access_token}');
            localStorage.setItem('flowly_refresh_token', '{refresh_token}');
            localStorage.setItem('flowly_oauth_provider', '{provider}');

            // 3秒后关闭
            setTimeout(function() {{
                window.close();
            }}, 3000);
        }} catch(e) {{
            console.error('OAuth callback error:', e);
        }}
    </script>
</body>
</html>
"""
    return HttpResponse(html, content_type='text/html; charset=utf-8')


def _error_page(message: str) -> HttpResponse:
    """返回错误页面"""
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>登录失败 - Flowly</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
            text-align: center;
            padding: 20px;
        }}
        .container {{
            background: rgba(255,255,255,0.15);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 40px 50px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.2);
            max-width: 400px;
        }}
        .icon {{
            font-size: 64px;
            margin-bottom: 20px;
        }}
        h1 {{
            font-size: 24px;
            margin-bottom: 10px;
        }}
        p {{
            font-size: 14px;
            opacity: 0.9;
            margin-bottom: 20px;
        }}
        a {{
            display: inline-block;
            padding: 10px 24px;
            background: white;
            color: #f5576c;
            text-decoration: none;
            border-radius: 8px;
            font-weight: 600;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="icon">😢</div>
        <h1>登录失败</h1>
        <p>{message}</p>
        <a href="/login">返回登录页</a>
    </div>
    <script>
        // 发送错误消息给 opener
        if (window.opener) {{
            window.opener.postMessage({{
                type: 'OAUTH_ERROR',
                provider: '',
                error: '{message}',
            }}, '*');
        }}
    </script>
</body>
</html>
"""
    return HttpResponse(html, content_type='text/html; charset=utf-8', status=400)


# ── 获取已连接的第三方账号列表 ─────────────────────────────────────────────────

@router.get(
    "/oauth/connections",
    response={200: SocialConnectionsSchema},
    auth=JWTAuth(),
)
def get_oauth_connections(request: HttpRequest):
    """
    GET /api/auth/oauth/connections

    获取当前用户已绑定的第三方账号列表。
    """
    accounts = SocialAccount.objects.filter(user=request.user).order_by('-created_at')

    connections = [
        SocialConnectionSchema(
            id=acc.id,
            provider=acc.provider,
            provider_username=acc.provider_username,
            provider_email=acc.provider_email,
            created_at=acc.created_at.isoformat(),
        )
        for acc in accounts
    ]

    return 200, SocialConnectionsSchema(connections=connections)


# ── 解绑第三方账号 ─────────────────────────────────────────────────────────────

@router.delete(
    "/oauth/unbind",
    response={200: dict, 400: ErrorSchema},
    auth=JWTAuth(),
)
def oauth_unbind(request: HttpRequest, provider: str):
    """
    DELETE /api/auth/oauth/unbind?provider=<provider>

    解除当前用户与指定第三方账号的绑定。
    不允许解绑最后一个登录方式。
    """
    # 检查是否有密码设置
    has_password = request.user.has_usable_password()

    # 获取其他登录方式数量
    social_count = SocialAccount.objects.filter(user=request.user).exclude(provider=provider).count()

    if not has_password and social_count == 0:
        return 400, ErrorSchema(
            message="无法解绑",
            detail="这是您账号唯一的登录方式，解绑后将无法登录。请先设置密码。",
        )

    deleted, _ = SocialAccount.objects.filter(
        user=request.user,
        provider=provider,
    ).delete()

    if deleted == 0:
        return 400, ErrorSchema(
            message="未找到绑定的账号",
            detail=f"您尚未绑定 {provider} 账号",
        )

    return 200, {"message": "解绑成功"}


# ── 绑定第三方账号到已有用户 ───────────────────────────────────────────────────

@router.post(
    "/oauth/bind",
    response={200: dict, 400: ErrorSchema},
    auth=JWTAuth(),
)
def oauth_bind(request: HttpRequest, payload: BindRequestSchema):
    """
    POST /api/auth/oauth/bind

    将第三方账号绑定到当前已登录的用户。
    需要用户已通过其他方式登录（密码或其他第三方账号）。
    """
    # 检查是否已绑定
    if SocialAccount.objects.filter(
        user=request.user,
        provider=payload.provider,
    ).exists():
        return 400, ErrorSchema(
            message="绑定失败",
            detail=f"您的账号已绑定 {payload.provider}",
        )

    try:
        # 1. 交换 token
        token_obj = exchange_code_for_token(payload.provider, payload.code, payload.state)

        # 2. 获取用户信息
        user_info = get_user_info(payload.provider, token_obj.access_token)

        # 3. 检查是否已被其他用户绑定
        if SocialAccount.objects.filter(
            provider=payload.provider,
            provider_user_id=user_info.provider_user_id,
        ).exists():
            return 400, ErrorSchema(
                message="绑定失败",
                detail="该第三方账号已绑定到其他用户",
            )

        # 4. 创建绑定
        expires_at = None
        if token_obj.expires_in:
            from django.utils import timezone
            expires_at = timezone.now() + timezone.timedelta(seconds=token_obj.expires_in)

        SocialAccount.objects.create(
            user=request.user,
            provider=payload.provider,
            provider_user_id=user_info.provider_user_id,
            provider_username=user_info.username,
            provider_email=user_info.email,
            provider_avatar_url=user_info.avatar_url,
            access_token=token_obj.access_token,
            refresh_token=token_obj.refresh_token or '',
            token_expires_at=expires_at,
        )

        return 200, {"message": "绑定成功"}

    except ValueError as e:
        return 400, ErrorSchema(
            message="绑定失败",
            detail=str(e),
        )
    except Exception as exc:
        logger.exception(f"oauth_bind {payload.provider}")
        return 400, ErrorSchema(
            message="绑定失败",
            detail="服务器错误，请稍后重试",
        )
