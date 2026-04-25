# 第三方登录功能设计方案

**日期**: 2026-04-25
**版本**: 1.0
**状态**: 已批准实施

## 1. 概述

为 Flowly AI 平台增加 GitHub、Google、QQ 三个平台的第三方登录功能。用户可以通过已有的第三方账号快速注册/登录，无需单独注册新账号。

## 2. 技术方案

### 2.1 登录流程（混合方案 C）

```
1. 用户点击第三方登录按钮
2. 前端请求后端获取授权 URL
3. 前端新窗口打开授权 URL
4. 用户在 popup 中完成授权
5. Provider 重定向到后端回调
6. 后端处理：
   - 验证 authorization code
   - 获取/创建本地用户
   - 生成 JWT token
   - 将 token 写入 popup window 的 localStorage
   - 显示成功页面
7. 前端检测 popup 关闭，读取 token，完成登录
```

### 2.2 支持的 OAuth Provider

| Provider | OAuth 版本 | 授权 URL | Token 交换 | 用户信息 API |
|----------|-----------|---------|-----------|-------------|
| GitHub | OAuth 2.0 | `https://github.com/login/oauth/authorize` | `https://github.com/login/oauth/access_token` | `https://api.github.com/user` |
| Google | OAuth 2.0 | `https://accounts.google.com/o/oauth2/v2/auth` | `https://oauth2.googleapis.com/token` | `https://www.googleapis.com/oauth2/v2/userinfo` |
| QQ | OAuth 2.0 | `https://graph.qq.com/oauth2.0/authorize` | `https://graph.qq.com/oauth2.0/token` | `https://graph.qq.com/oauth2.0/me` + `https://graph.qq.com/user/get_user_info` |

## 3. 数据库设计

### 3.1 SocialAccount 模型

```python
class SocialAccount(models.Model):
    """第三方账号关联表"""
    
    PROVIDER_CHOICES = [
        ('github', 'GitHub'),
        ('google', 'Google'),
        ('qq', 'QQ'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='social_accounts')
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    provider_user_id = models.CharField(max_length=255)
    provider_username = models.CharField(max_length=255, blank=True)
    provider_email = models.EmailField(blank=True)
    provider_avatar_url = models.URLField(blank=True)
    access_token = models.TextField(blank=True)
    refresh_token = models.TextField(blank=True)
    token_expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = [['provider', 'provider_user_id']]
        verbose_name = '第三方账号'
        verbose_name_plural = '第三方账号'
```

### 3.2 UserProfile 扩展

如第三方账号提供了邮箱且用户本地账号无邮箱，自动填充邮箱。

## 4. 后端 API 设计

### 4.1 端点列表

| 端点 | 方法 | 认证 | 说明 |
|------|------|------|------|
| `/api/auth/oauth/<provider>/login` | GET | 否 | 返回指定 Provider 的授权 URL |
| `/api/auth/oauth/<provider>/callback` | GET | 否 | OAuth 回调（由 Provider 重定向调用） |
| `/api/auth/oauth/bind` | POST | 是 | 绑定已有账号与第三方账号 |
| `/api/auth/oauth/unbind` | DELETE | 是 | 解除第三方账号绑定 |
| `/api/auth/oauth/connections` | GET | 是 | 获取当前用户的第三方账号列表 |

### 4.2 响应格式

**OAuth Login 响应**:
```json
{
  "auth_url": "https://github.com/login/oauth/authorize?client_id=xxx&redirect_uri=xxx&state=xxx",
  "state": "随机 CSRF token"
}
```

**OAuth Callback 成功响应** (HTML 页面):
```html
<script>
  window.opener.postMessage({
    type: 'OAUTH_SUCCESS',
    provider: 'github',
    access: '<jwt_access_token>',
    refresh: '<jwt_refresh_token>',
  }, '*');
</script>
<h1>登录成功，窗口即将关闭...</h1>
```

## 5. 前端实现

### 5.1 新增文件

| 文件 | 职责 |
|------|------|
| `Frontend/src/stores/social.ts` | 第三方登录 Pinia store |
| `Frontend/src/components/SocialCallback.vue` | 回调页面（接收 JWT） |
| `Frontend/src/views/SettingsView.vue` | 用户设置页（绑定/解绑） |

### 5.2 Popup 流程

1. `oauthStore.loginWithPopup('github')` 打开新窗口
2. 监听 `message` 事件接收 token
3. 存储 token 到 localStorage
4. 刷新用户状态

## 6. 环境变量配置

```env
# GitHub OAuth
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret

# Google OAuth
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

# QQ OAuth
QQ_CLIENT_ID=your_qq_app_id
QQ_CLIENT_SECRET=your_qq_app_key

# OAuth 通用配置
OAUTH_REDIRECT_URI=http://localhost:5173/social-callback
```

## 7. 安全性设计

- **CSRF 保护**: OAuth 流程使用 `state` 参数防止 CSRF 攻击
- **Token 安全**: OAuth access_token/refresh_token 加密存储
- **用户关联**: 
  - 首次第三方登录：自动创建本地账号（用户名 = `{provider}_{provider_user_id}`）
  - 支持绑定到已有账号
- **解绑保护**: 不允许解绑最后一个登录方式

## 8. 文件清单

### 后端新增
- `Backend/accounts/social_auth.py` - OAuth 核心逻辑
- `Backend/accounts/social_views.py` - OAuth API 路由
- `Backend/flowly_backend/settings/social_auth.py` - OAuth 配置

### 后端修改
- `Backend/accounts/models.py` - 新增 SocialAccount 模型
- `Backend/ai_engine/urls.py` - 注册 social_views 路由

### 前端新增
- `Frontend/src/stores/social.ts` - 第三方登录 Store
- `Frontend/src/components/SocialCallback.vue` - 回调组件
- `Frontend/src/views/SettingsView.vue` - 设置页面

### 前端修改
- `Frontend/src/views/AuthPage.vue` - 接入第三方登录按钮
- `Frontend/src/router/index.ts` - 添加路由
