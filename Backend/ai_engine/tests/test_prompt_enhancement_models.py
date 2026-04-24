from django.contrib.auth.models import User
from django.test import TestCase

from ai_engine.models import PromptEnhancementRecord, Workflow, WorkflowGraphValidation


class PromptEnhancementModelsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u1", password="pw")
        self.workflow = Workflow.objects.create(
            user=self.user,
            name="wf1",
            description="",
            definition={"version": "1.0", "nodes": [], "edges": []},
            is_active=True,
        )

    def test_prompt_enhancement_selected_text_nullable(self):
        rec = PromptEnhancementRecord.objects.create(
            user=self.user,
            workflow=self.workflow,
            client_node_id="node_x",
            node_type="text",
            field="prompt",
            raw_prompt="hello",
            instruction="make it better",
            candidates=["a", "b", "c"],
            suggested_text="a",
            provider_route="openai",
            model="gpt-4o",
            temperature=0.2,
            max_tokens=128,
        )
        self.assertIsNotNone(rec.created_at)
        self.assertIsNone(rec.selected_text)

    def test_workflow_graph_validation_one_to_one(self):
        v1 = WorkflowGraphValidation.objects.create(
            workflow=self.workflow,
            is_valid=True,
            errors=[],
        )
        self.assertTrue(v1.is_valid)
        v2 = WorkflowGraphValidation.objects.update_or_create(
            workflow=self.workflow,
            defaults={"is_valid": False, "errors": [{"code": "x"}]},
        )[0]
        self.assertEqual(v2.workflow_id, self.workflow.id)
        self.assertFalse(v2.is_valid)

