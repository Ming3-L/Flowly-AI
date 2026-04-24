from django.contrib.auth.models import User
from django.test import TestCase

from ai_engine.models import UserCustomNodeType
from ai_engine.workflow_graph.validator import validate_workflow_definition


class WorkflowDefinitionValidatorTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u1", password="pw")

    def test_empty_nodes_fails(self):
        ok, errors = validate_workflow_definition({"version": "1.0", "nodes": [], "edges": []}, user_id=self.user.id)
        self.assertFalse(ok)
        self.assertTrue(any(e["path"] == "nodes" for e in errors))

    def test_edge_dangling_ref_fails(self):
        ok, errors = validate_workflow_definition(
            {
                "version": "1.0",
                "nodes": [{"id": "n1", "type": "text", "label": "T", "x": 0, "y": 0, "width": 1, "height": 1, "ports": [], "config": {}}],
                "edges": [{"id": "e1", "sourceNodeId": "n1", "sourcePortId": "out", "targetNodeId": "missing", "targetPortId": "in"}],
            },
            user_id=self.user.id,
        )
        self.assertFalse(ok)
        self.assertTrue(any(e["code"] == "dangling_ref" for e in errors))

    def test_invalid_handles_for_condition(self):
        ok, errors = validate_workflow_definition(
            {
                "version": "1.0",
                "nodes": [
                    {"id": "c1", "type": "condition", "label": "C", "x": 0, "y": 0, "width": 1, "height": 1, "ports": [], "config": {}},
                    {"id": "t1", "type": "text", "label": "T", "x": 0, "y": 0, "width": 1, "height": 1, "ports": [], "config": {}},
                ],
                "edges": [{"id": "e1", "sourceNodeId": "c1", "sourcePortId": "out", "targetNodeId": "t1", "targetPortId": "in"}],
            },
            user_id=self.user.id,
        )
        self.assertFalse(ok)
        self.assertTrue(any(e["code"] == "invalid_handle" for e in errors))

    def test_ut_type_requires_ownership(self):
        other = User.objects.create_user(username="u2", password="pw")
        ut = UserCustomNodeType.objects.create(
            user=other,
            slug="x",
            display_name="X",
            provider_route=UserCustomNodeType.ProviderRoute.OPENAI,
            model_name="gpt-4o",
            default_config={},
            description="",
        )
        ok, errors = validate_workflow_definition(
            {
                "version": "1.0",
                "nodes": [{"id": "n1", "type": ut.type_key, "label": "X", "x": 0, "y": 0, "width": 1, "height": 1, "ports": [], "config": {}}],
                "edges": [],
            },
            user_id=self.user.id,
        )
        self.assertFalse(ok)
        self.assertTrue(any(e["code"] == "forbidden" for e in errors))

