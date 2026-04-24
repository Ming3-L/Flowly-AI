"""用户自定义聊天模型预设 API 契约测试。"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase
from ninja.testing import TestClient  # pyright: ignore[reportMissingImports]
from rest_framework_simplejwt.tokens import RefreshToken  # pyright: ignore[reportMissingImports]

from ai_engine.models import UserChatModelPreset
from ai_engine.urls import api


class UserChatModelPresetsApiTests(TestCase):
    def setUp(self) -> None:
        User = get_user_model()
        self.user = User.objects.create_user(username="ucm_u1", password="TestPass123!")
        self.ninja = TestClient(api)
        token = RefreshToken.for_user(self.user)
        self.headers = {"Authorization": f"Bearer {str(token.access_token)}"}

    def test_crud_flow(self) -> None:
        res = self.ninja.post(
            "/ai/user-chat-model-presets",
            json={
                "display_name": "我的接入点",
                "description": "测试",
                "route": "doubao",
                "model_id": "ep-api-test-1",
                "is_active": True,
            },
            headers=self.headers,
        )
        self.assertEqual(res.status_code, 201, res.content)
        data = res.json()
        self.assertTrue(str(data.get("key", "")).startswith("user:"))
        self.assertIn("category", data)
        self.assertIn("scopes", data)
        self.assertFalse(data.get("has_custom_credentials"))
        pid = int(data["id"])

        res2 = self.ninja.get("/ai/user-chat-model-presets", headers=self.headers)
        self.assertEqual(res2.status_code, 200)
        arr = res2.json()
        self.assertTrue(any(x["id"] == pid for x in arr))

        res3 = self.ninja.patch(
            f"/ai/user-chat-model-presets/{pid}",
            json={"display_name": "改名后"},
            headers=self.headers,
        )
        self.assertEqual(res3.status_code, 200)
        self.assertEqual(res3.json()["display_name"], "改名后")

        res4 = self.ninja.get("/ai/models", headers=self.headers)
        self.assertEqual(res4.status_code, 200)
        models = res4.json().get("models") or []
        self.assertTrue(any(m.get("key") == data["key"] and m.get("source") == "user" for m in models))

        res5 = self.ninja.delete(f"/ai/user-chat-model-presets/{pid}", headers=self.headers)
        self.assertEqual(res5.status_code, 200)
        self.assertFalse(UserChatModelPreset.objects.filter(pk=pid).exists())
