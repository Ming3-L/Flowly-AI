from django.contrib.auth.models import User
from django.test import TestCase

from ai_engine.integrations import clear_local_secrets_cache
from ai_engine.models import Workflow


class PromptToolsApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u1", password="pw")
        self.workflow = Workflow.objects.create(
            user=self.user,
            name="wf1",
            description="",
            definition={"version": "1.0", "nodes": [{"id": "n1", "type": "text", "label": "T"}], "edges": []},
            is_active=True,
        )

    def test_models_endpoint_requires_auth(self):
        res = self.client.get("/api/ai/models")
        self.assertIn(res.status_code, (401, 403))

