from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from ai_engine.ai_model_catalog import (
    list_models_merged_for_api,
    list_presets_for_api,
    resolve_route_and_model_id,
)
from ai_engine.models import UserChatModelPreset


class AiModelCatalogTests(TestCase):
    def _mock_settings(self):
        s = MagicMock()
        s.language.openai_model = "env-openai-default"
        s.language.anthropic_model = "env-claude"
        s.language.ollama_model = "env-ollama"
        s.language.vectorengine_model = "env-ve"
        s.language.doubao_ark_model = "ep-from-env"
        return s

    @patch("ai_engine.ai_model_catalog.get_ai_provider_settings")
    def test_model_key_openai_preset(self, mock_gs):
        mock_gs.return_value = self._mock_settings()
        route, mid, key = resolve_route_and_model_id({"modelKey": "openai-gpt-4o"})
        self.assertEqual(route, "openai")
        self.assertEqual(mid, "gpt-4o")
        self.assertEqual(key, "openai-gpt-4o")

    @patch("ai_engine.ai_model_catalog.get_ai_provider_settings")
    def test_model_key_doubao_uses_env(self, mock_gs):
        mock_gs.return_value = self._mock_settings()
        route, mid, key = resolve_route_and_model_id({"modelKey": "doubao-default"})
        self.assertEqual(route, "doubao")
        self.assertEqual(mid, "ep-from-env")
        self.assertEqual(key, "doubao-default")

    @patch("ai_engine.ai_model_catalog.get_ai_provider_settings")
    def test_model_key_doubao_smart_router(self, mock_gs):
        mock_gs.return_value = self._mock_settings()
        route, mid, key = resolve_route_and_model_id({"modelKey": "ark-doubao-smart-router"})
        self.assertEqual(route, "doubao")
        self.assertEqual(mid, "Doubao-Smart-Router")
        self.assertEqual(key, "ark-doubao-smart-router")

    @patch("ai_engine.ai_model_catalog.get_ai_provider_settings")
    def test_model_key_plain_gpt4o_resolves_openai_preset(self, mock_gs):
        mock_gs.return_value = self._mock_settings()
        route, mid, key = resolve_route_and_model_id({"modelKey": "gpt-4o"})
        self.assertEqual(route, "openai")
        self.assertEqual(mid, "gpt-4o")
        self.assertEqual(key, "openai-gpt-4o")

    @patch("ai_engine.ai_model_catalog.get_ai_provider_settings")
    def test_doubao_seed_mini_maps_to_ep_when_env_is_endpoint(self, mock_gs):
        mock_gs.return_value = self._mock_settings()
        route, mid, key = resolve_route_and_model_id({"modelKey": "ark-doubao-seed-2-0-mini"})
        self.assertEqual(route, "doubao")
        self.assertEqual(mid, "ep-from-env")
        self.assertEqual(key, "ark-doubao-seed-2-0-mini")

    @patch("ai_engine.ai_model_catalog.get_ai_provider_settings")
    def test_legacy_ep_prefix(self, mock_gs):
        mock_gs.return_value = self._mock_settings()
        route, mid, key = resolve_route_and_model_id(
            {"provider": "doubao", "model": "ep-custom-123"}
        )
        self.assertEqual(route, "doubao")
        self.assertEqual(mid, "ep-custom-123")
        self.assertEqual(key, "")

    def test_list_for_api_shape(self):
        rows = list_presets_for_api()
        self.assertTrue(rows)
        for row in rows:
            self.assertIn("key", row)
            self.assertIn("label", row)
            self.assertIn("description", row)
            self.assertIn("route", row)


class AiModelCatalogMergeTests(TestCase):
    def test_list_merge_anonymous_only_project_sources(self):
        rows = list_models_merged_for_api(None)
        self.assertTrue(
            all(r.get("source") in ("catalog", "project") for r in rows if r.get("source") != "user")
        )
        first = rows[0]
        self.assertIn("category", first)
        self.assertIn("scopes", first)
        self.assertIn("scope_summary", first)
        self.assertIn("canvas_node_kinds", first)
        self.assertIn("canvas_universal", first)
        keys = [r["key"] for r in rows]
        self.assertIn("ark-doubao-smart-router", keys)
        smart = next(r for r in rows if r["key"] == "ark-doubao-smart-router")
        self.assertTrue(smart.get("canvas_universal"))
        mini = next(r for r in rows if r["key"] == "openai-gpt-4o-mini")
        self.assertEqual(set(mini.get("canvas_node_kinds") or []), {"chat", "text", "audio", "video"})
        emb = next(r for r in rows if r.get("key") == "ark-doubao-embedding")
        self.assertEqual(emb.get("api_kind"), "ark_embedding")
        self.assertFalse(emb.get("show_in_canvas_llm_nodes"))

    @patch("ai_engine.ai_model_catalog.get_ai_provider_settings")
    def test_resolve_embedding_catalog_key_raises(self, mock_gs):
        mock_gs.return_value = self._mock_settings()
        with self.assertRaises(ValueError):
            resolve_route_and_model_id({"modelKey": "ark-doubao-embedding"})

    def test_list_merge_includes_user_presets(self):
        User = get_user_model()
        u = User.objects.create_user(username="catalog_u1", password="pw")
        p = UserChatModelPreset.objects.create(
            user=u,
            display_name="我的豆包",
            description="",
            route="doubao",
            model_id="ep-test-123",
        )
        rows = list_models_merged_for_api(u)
        keys = [r["key"] for r in rows]
        self.assertIn(p.api_model_key, keys)
        user_rows = [r for r in rows if r.get("source") == "user"]
        self.assertTrue(any(r["key"] == p.api_model_key for r in user_rows))

    @patch("ai_engine.ai_model_catalog.get_ai_provider_settings")
    def test_resolve_user_model_key(self, mock_gs):
        mock_gs.return_value = self._mock_settings()
        User = get_user_model()
        u = User.objects.create_user(username="catalog_u2", password="pw")
        p = UserChatModelPreset.objects.create(
            user=u,
            display_name="X",
            description="",
            route="doubao",
            model_id="ep-xyz",
        )
        route, mid, key = resolve_route_and_model_id(
            {"modelKey": p.api_model_key},
            user_id=u.pk,
        )
        self.assertEqual(route, "doubao")
        self.assertEqual(mid, "ep-xyz")
        self.assertEqual(key, p.api_model_key)

    @patch("ai_engine.ai_model_catalog.get_ai_provider_settings")
    def test_resolve_user_key_wrong_owner_raises(self, mock_gs):
        mock_gs.return_value = self._mock_settings()
        User = get_user_model()
        u1 = User.objects.create_user(username="catalog_u3", password="pw")
        u2 = User.objects.create_user(username="catalog_u4", password="pw")
        p = UserChatModelPreset.objects.create(
            user=u1,
            display_name="A",
            description="",
            route="doubao",
            model_id="ep-a",
        )
        with self.assertRaises(ValueError):
            resolve_route_and_model_id({"modelKey": p.api_model_key}, user_id=u2.pk)

    def _mock_settings(self):
        s = MagicMock()
        s.language.openai_model = "env-openai-default"
        s.language.anthropic_model = "env-claude"
        s.language.ollama_model = "env-ollama"
        s.language.vectorengine_model = "env-ve"
        s.language.doubao_ark_model = "ep-from-env"
        return s
