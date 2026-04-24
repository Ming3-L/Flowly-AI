"""契约测试：画布单步 API 持久化 client_node_id；占位节点错误信息；Celery 入口 input_data 字段。"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from ninja.testing import TestClient  # pyright: ignore[reportMissingImports]
from rest_framework_simplejwt.tokens import RefreshToken  # pyright: ignore[reportMissingImports]

from ai_engine.models import Workflow, WorkflowExecution
from ai_engine.urls import api
from ai_engine.workflow_nodes.registry import resolve_node_executor


class CanvasNodeRunContractTests(TestCase):
    def setUp(self) -> None:
        User = get_user_model()
        self.user = User.objects.create_user(username="contract_u1", password="TestPass123!")
        self.workflow = Workflow.objects.create(
            user=self.user,
            name="Contract WF",
            description="",
            definition={"version": "1.0", "nodes": [], "edges": []},
        )
        self.ninja = TestClient(api)
        token = RefreshToken.for_user(self.user)
        self.auth_headers = {"Authorization": f"Bearer {str(token.access_token)}"}

    @patch("ai_engine.api.execute_canvas_node", return_value={"text": "stub", "model": "stub-model"})
    def test_canvas_node_run_persists_client_node_id(self, _mock: MagicMock) -> None:
        payload = {
            "workflow_id": self.workflow.id,
            "client_node_id": "node_vueflow_123",
            "node_type": "chat",
            "config": {"model": "gpt-4o-mini"},
            "inputs": {"text": "hi"},
        }
        res = self.ninja.post(
            "/workflows/canvas-node/run",
            json=payload,
            headers=self.auth_headers,
        )
        self.assertEqual(res.status_code, 200, res.content)
        body = res.json()
        self.assertEqual(body.get("status"), "completed")
        self.assertEqual(body.get("output", {}).get("text"), "stub")
        ex = WorkflowExecution.objects.order_by("-id").first()
        assert ex is not None
        self.assertEqual(ex.input_data.get("client_node_id"), "node_vueflow_123")
        self.assertEqual(ex.input_data.get("node_type"), "chat")


class PlaceholderRegistryTests(TestCase):
    def test_tool_placeholder_message(self) -> None:
        ex = resolve_node_executor("tool", user_id=None)
        with self.assertRaises(NotImplementedError) as ar:
            ex.execute(config={}, inputs={})
        self.assertIn("tool", str(ar.exception))


class TaskApiInputDataTests(TestCase):
    def setUp(self) -> None:
        User = get_user_model()
        self.user = User.objects.create_user(username="task_u1", password="TestPass123!")
        self.workflow = Workflow.objects.create(
            user=self.user,
            name="Task WF",
            description="",
            definition={"nodes": []},
        )
        self.ninja = TestClient(api)
        token = RefreshToken.for_user(self.user)
        self.auth_headers = {"Authorization": f"Bearer {str(token.access_token)}"}

    @patch("ai_engine.tasks.run_workflow_task.delay")
    def test_async_run_stores_model_and_branches_in_input_data(self, delay_mock: MagicMock) -> None:
        from urllib.parse import quote

        q = quote("hello", safe="")
        res = self.ninja.post(
            f"/tasks/run/async?workflow_id={self.workflow.id}&query={q}"
            f"&model_name=claude&client_node_id=node_xyz",
            headers=self.auth_headers,
        )
        self.assertEqual(res.status_code, 200, res.content)
        delay_mock.assert_called_once()
        ex = WorkflowExecution.objects.order_by("-id").first()
        assert ex is not None
        self.assertEqual(ex.input_data.get("client_node_id"), "node_xyz")
        self.assertEqual(ex.input_data.get("model_name"), "claude")
        self.assertEqual(ex.input_data.get("parallel_branches"), [])
