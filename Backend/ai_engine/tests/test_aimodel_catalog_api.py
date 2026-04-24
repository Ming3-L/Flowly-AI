"""项目模型目录 CRUD API（管理员）。"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase
from ninja.testing import TestClient  # pyright: ignore[reportMissingImports]
from rest_framework_simplejwt.tokens import RefreshToken  # pyright: ignore[reportMissingImports]

from ai_engine.models import AIModelCatalogEntry
from ai_engine.urls import api


class AIModelCatalogEntriesApiTests(TestCase):
    def setUp(self) -> None:
        User = get_user_model()
        self.staff = User.objects.create_user(
            username="cat_staff", password="TestPass123!", is_staff=True
        )
        self.user = User.objects.create_user(username="cat_norm", password="TestPass123!")
        self.ninja = TestClient(api)
        tok_s = RefreshToken.for_user(self.staff)
        self.staff_headers = {"Authorization": f"Bearer {str(tok_s.access_token)}"}
        tok_u = RefreshToken.for_user(self.user)
        self.user_headers = {"Authorization": f"Bearer {str(tok_u.access_token)}"}

    def test_non_staff_list_forbidden(self) -> None:
        res = self.ninja.get("/ai/catalog-entries", headers=self.user_headers)
        self.assertEqual(res.status_code, 403)

    def test_staff_crud(self) -> None:
        res = self.ninja.get("/ai/catalog-entries", headers=self.staff_headers)
        self.assertEqual(res.status_code, 200)
        self.assertGreaterEqual(len(res.json()), 1)

        res_c = self.ninja.post(
            "/ai/catalog-entries",
            json={
                "catalog_key": "test-api-seed-model",
                "label": "API 测试模型",
                "description": "仅测试",
                "route": "doubao",
                "model_id": "Doubao-Seed-2.0-lite",
                "category": "cat_test",
                "category_label": "测试",
                "category_order": 999,
                "api_kind": "ark_chat",
                "show_in_canvas_llm_nodes": True,
                "is_active": True,
            },
            headers=self.staff_headers,
        )
        self.assertEqual(res_c.status_code, 201, res_c.content)
        body = res_c.json()
        eid = int(body["id"])
        self.assertEqual(body["catalog_key"], "test-api-seed-model")

        res_p = self.ninja.patch(
            f"/ai/catalog-entries/{eid}",
            json={"label": "已改名"},
            headers=self.staff_headers,
        )
        self.assertEqual(res_p.status_code, 200)
        self.assertEqual(res_p.json()["label"], "已改名")

        res_d = self.ninja.delete(f"/ai/catalog-entries/{eid}", headers=self.staff_headers)
        self.assertEqual(res_d.status_code, 200)
        self.assertFalse(AIModelCatalogEntry.objects.filter(pk=eid).exists())
