from ninja import Field, ModelSchema, Router, Schema  # pyright: ignore[reportMissingImports]

from .models import UserProfile
from ai_engine.auth import JWTAuth

router = Router(tags=['用户设置'], auth=JWTAuth())


# ── Request / Response Schemas ──────────────────────────────────────────────

class UserProfileSchema(ModelSchema):
    openai_api_key: str = Field(default='', exclude=True)

    class Meta:
        model = UserProfile
        fields = ['ai_model', 'language', 'openai_base_url', 'nickname', 'avatar_path']


class UpdateProfileSchema(ModelSchema):
    class Meta:
        model = UserProfile
        fields = ['ai_model', 'language', 'nickname']


class ChangeApiKeySchema(Schema):
    openai_api_key: str = Field(default='', max_length=256)


class AvatarUploadOut(Schema):
    avatar_path: str
    avatar_public_url: str


class AvatarHistoryItem(Schema):
    asset_id: int
    created_at: str
    avatar_path: str
    avatar_public_url: str


class AvatarHistoryOut(Schema):
    current_avatar_path: str
    items: list[AvatarHistoryItem]


class AvatarSelectIn(Schema):
    asset_id: int


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


@router.post("/profile/avatar", response=AvatarUploadOut)
def upload_avatar(request):
    """
    POST /api/auth/profile/avatar (multipart/form-data)
    字段：file
    """
    from django.utils.text import get_valid_filename
    from django.core.files.uploadedfile import UploadedFile
    import os, uuid
    from ai_engine.local_media_store import build_public_url
    from ai_engine.models import LocalMediaAsset
    from ai_engine.media_storage import oss_enabled, put_fileobj, media_root

    # Django Ninja 文件上传需要从 request.FILES 获取
    files = getattr(request, 'FILES', {})
    uploaded_file = files.get('file') if hasattr(request, 'FILES') else None
    
    # 兼容 Ninja 1.x 的 Form 解析方式
    if uploaded_file is None:
        try:
            uploaded_file = request.resolve_param(UploadedFile, 'file', None)
        except Exception:
            uploaded_file = None
    
    if uploaded_file is None:
        from ninja.errors import HttpError  # pyright: ignore[reportMissingImports]

        raise HttpError(400, "file required")
    
    file = uploaded_file
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    orig = get_valid_filename(getattr(file, "name", "") or "avatar.png")
    ext = os.path.splitext(orig)[1][:16] or ".png"
    rel_path = f"avatars/u{int(request.user.id)}/{uuid.uuid4().hex}{ext}"
    if oss_enabled():
        fp = getattr(file, "file", None)
        if fp is not None:
            put_fileobj(key=rel_path, fp=fp, content_type=str(getattr(file, "content_type", "") or ""))
        else:
            put_fileobj(
                key=rel_path,
                fp=__import__("io").BytesIO(b"".join(list(file.chunks()))),
                content_type=str(getattr(file, "content_type", "") or ""),
            )
    else:
        mr = media_root()
        abs_path = os.path.join(mr, rel_path.replace("/", os.sep))
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "wb") as f:
            for chunk in file.chunks():
                f.write(chunk)
    profile.avatar_path = rel_path
    profile.save(update_fields=["avatar_path"])

    # 同步记录到资源表（方便统一管理）
    try:
        LocalMediaAsset.objects.create(
            user_id=int(request.user.id),
            kind=LocalMediaAsset.Kind.AVATAR,
            original_name=orig,
            mime=str(getattr(file, "content_type", "") or ""),
            size_bytes=int(getattr(file, "size", 0) or 0),
            rel_path=rel_path,
            source_url="",
        )
    except Exception:
        pass

    return AvatarUploadOut(
        avatar_path=rel_path,
        avatar_public_url=build_public_url(rel_path),
    )


@router.get("/profile/avatars", response=AvatarHistoryOut)
def list_avatar_history(request):
    """GET /api/auth/profile/avatars — 历史头像列表（来自 LocalMediaAsset(kind=avatar)）。"""
    from ai_engine.local_media_store import build_public_url
    from ai_engine.models import LocalMediaAsset

    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    qs = LocalMediaAsset.objects.filter(user_id=request.user.id, kind=LocalMediaAsset.Kind.AVATAR).order_by("-created_at")[:40]
    items = [
        AvatarHistoryItem(
            asset_id=int(x.pk),
            created_at=x.created_at.isoformat() if x.created_at else "",
            avatar_path=x.rel_path,
            avatar_public_url=build_public_url(x.rel_path),
        )
        for x in qs
        if (x.rel_path or "").strip()
    ]
    return AvatarHistoryOut(current_avatar_path=(profile.avatar_path or "").strip(), items=items)


@router.post("/profile/avatars/select", response=AvatarUploadOut)
def select_avatar_from_history(request, payload: AvatarSelectIn):
    """POST /api/auth/profile/avatars/select — 选择历史头像为当前头像。"""
    from ai_engine.local_media_store import build_public_url
    from ai_engine.models import LocalMediaAsset
    from ninja.errors import HttpError  # pyright: ignore[reportMissingImports]

    asset = LocalMediaAsset.objects.filter(pk=int(payload.asset_id), user_id=request.user.id, kind=LocalMediaAsset.Kind.AVATAR).first()
    if asset is None or not (asset.rel_path or "").strip():
        raise HttpError(404, "历史头像不存在")
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    profile.avatar_path = asset.rel_path
    profile.save(update_fields=["avatar_path"])
    return AvatarUploadOut(avatar_path=asset.rel_path, avatar_public_url=build_public_url(asset.rel_path))


@router.delete("/profile/avatars/{asset_id}", response={200: dict})
def delete_avatar_from_history(request, asset_id: int):
    """DELETE /api/auth/profile/avatars/{asset_id} — 删除历史头像（若是当前头像则仅清空引用，不强制删除文件）。"""
    from ai_engine.models import LocalMediaAsset

    row = LocalMediaAsset.objects.filter(pk=int(asset_id), user_id=request.user.id, kind=LocalMediaAsset.Kind.AVATAR).first()
    if row is None:
        return 200, {"ok": True}
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if (profile.avatar_path or "").strip() and (profile.avatar_path or "").strip() == (row.rel_path or "").strip():
        profile.avatar_path = ""
        profile.save(update_fields=["avatar_path"])
    row.delete()
    return 200, {"ok": True}
