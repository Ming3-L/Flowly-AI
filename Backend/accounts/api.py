from ninja import Field, ModelSchema, Router, Schema

from .models import UserProfile
from ai_engine.auth import JWTAuth

router = Router(tags=['用户设置'], auth=JWTAuth())


# ── Request / Response Schemas ──────────────────────────────────────────────

class UserProfileSchema(ModelSchema):
    openai_api_key: str = Field(default='', exclude=True)

    class Meta:
        model = UserProfile
        fields = ['ai_model', 'language', 'openai_base_url']


class UpdateProfileSchema(ModelSchema):
    class Meta:
        model = UserProfile
        fields = ['ai_model', 'language']


class ChangeApiKeySchema(Schema):
    openai_api_key: str = Field(default='', max_length=256)


# ── Profile Endpoints ───────────────────────────────────────────────────────

@router.get('/profile', response=UserProfileSchema)
def get_profile(request):
    """获取当前登录用户的资料（包含 AI 模型偏好）"""
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    return profile


@router.put('/profile', response=UserProfileSchema)
def update_profile(request, payload: UpdateProfileSchema):
    """更新 AI 模型偏好"""
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    for key, value in payload.model_dump().items():
        setattr(profile, key, value)
    profile.save()
    return profile


@router.post('/profile/api-key', response=UserProfileSchema)
def change_api_key(request, payload: ChangeApiKeySchema):
    """设置个人 OpenAI API Key（优先级高于系统全局 Key）"""
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    profile.openai_api_key = payload.openai_api_key.strip()
    profile.save()
    return profile


@router.delete('/profile/api-key')
def delete_api_key(request):
    """清除个人 API Key"""
    UserProfile.objects.filter(user=request.user).update(openai_api_key='')
    return {'detail': '已清除个人 API Key'}
