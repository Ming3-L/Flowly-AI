from django.contrib.auth.models import User
from django.test import TestCase

from ai_engine.models import Workflow


class WorkflowGuideApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="ug1", password="pw")
        self.workflow = Workflow.objects.create(
            user=self.user,
            name="引导测试",
            description="描述",
            definition={
                "version": "1.0",
                "nodes": [{"id": "a1", "type": "chat", "label": "开始"}],
                "edges": [],
            },
            is_active=True,
        )

    def test_workflow_guide_chat_requires_auth(self):
        res = self.client.post(
            "/api/ai/workflow-guide/chat",
            data={"messages": [{"role": "user", "content": "hi"}], "provider_route": "openai"},
            content_type="application/json",
        )
        self.assertIn(res.status_code, (401, 403))
