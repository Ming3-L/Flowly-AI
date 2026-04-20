"""
Unit tests for Workflow CRUD API endpoints.
Uses Django's TestClient with JWT Bearer tokens to test the full URL routing stack.

All protected endpoints require JWT authentication.
"""

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


def make_auth_header(user) -> dict:
    """Return HTTP_AUTHORIZATION header dict for the given user."""
    token = str(RefreshToken.for_user(user).access_token)
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}


@pytest.fixture
def django_client():
    return Client()


@pytest.fixture
def test_user(db):
    """Create a test user."""
    return User.objects.create_user(
        username="testuser", email="test@example.com", password="testpass123"
    )


@pytest.fixture
def auth_client(django_client, test_user):
    """Client pre-wired with a valid access token."""
    return django_client, make_auth_header(test_user)


# ── Workflow CRUD Tests ────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestWorkflowCRUD:
    """Test workflow list, create, retrieve, update, delete with JWT auth."""

    def test_list_workflows_empty(self, auth_client):
        """GET /api/workflows/ returns empty list."""
        client, auth = auth_client
        response = client.get("/api/workflows/", **auth)
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []

    def test_create_workflow(self, auth_client):
        """POST /api/workflows/ creates a workflow."""
        client, auth = auth_client
        response = client.post(
            "/api/workflows/",
            data={
                "name": "Test Workflow",
                "description": "A test workflow",
                "definition": {
                    "version": "1.0",
                    "nodes": [
                        {
                            "id": "node_1", "type": "chat", "label": "Chat Node",
                            "x": 100, "y": 100, "width": 200, "height": 80,
                            "ports": [
                                {"id": "n1_in", "label": "In", "type": "target", "position": "left"},
                                {"id": "n1_out", "label": "Out", "type": "source", "position": "right"},
                            ],
                            "config": {},
                            "style": {"color": "#409eff"},
                        }
                    ],
                    "edges": [],
                },
            },
            content_type="application/json",
            **auth,
        )
        assert response.status_code == 201, f"Got {response.status_code}: {response.content}"
        data = response.json()
        assert data["name"] == "Test Workflow"
        assert data["description"] == "A test workflow"
        assert data["is_active"] is True
        assert "id" in data
        assert "created_at" in data

    def test_get_workflow(self, auth_client):
        """GET /api/workflows/{id} retrieves a workflow."""
        client, auth = auth_client
        create_resp = client.post(
            "/api/workflows/",
            data={"name": "Get Test", "description": "Test retrieval", "definition": {}},
            content_type="application/json",
            **auth,
        )
        wf_id = create_resp.json()["id"]
        response = client.get(f"/api/workflows/{wf_id}", **auth)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == wf_id
        assert data["name"] == "Get Test"

    def test_update_workflow(self, auth_client):
        """PUT /api/workflows/{id} updates a workflow."""
        client, auth = auth_client
        create_resp = client.post(
            "/api/workflows/",
            data={"name": "Original Name", "description": "Original", "definition": {}},
            content_type="application/json",
            **auth,
        )
        wf_id = create_resp.json()["id"]
        response = client.put(
            f"/api/workflows/{wf_id}",
            data={"name": "Updated Name", "description": "Updated desc", "is_active": False},
            content_type="application/json",
            **auth,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["description"] == "Updated desc"
        assert data["is_active"] is False

    def test_delete_workflow_soft_delete(self, auth_client):
        """DELETE /api/workflows/{id} soft-deletes by setting is_active=False."""
        client, auth = auth_client
        create_resp = client.post(
            "/api/workflows/",
            data={"name": "To Delete", "description": "", "definition": {}},
            content_type="application/json",
            **auth,
        )
        wf_id = create_resp.json()["id"]
        response = client.delete(f"/api/workflows/{wf_id}", **auth)
        assert response.status_code == 200
        assert "deactivated" in response.json()["message"].lower()
        get_resp = client.get(f"/api/workflows/{wf_id}", **auth)
        assert get_resp.json()["is_active"] is False

    def test_list_workflows_search(self, auth_client):
        """GET /api/workflows/?search= filters by name/description."""
        client, auth = auth_client
        client.post("/api/workflows/", data={"name": "Alpha Workflow", "description": "", "definition": {}}, content_type="application/json", **auth)
        client.post("/api/workflows/", data={"name": "Beta Workflow", "description": "", "definition": {}}, content_type="application/json", **auth)
        client.post("/api/workflows/", data={"name": "Gamma Workflow", "description": "", "definition": {}}, content_type="application/json", **auth)
        response = client.get("/api/workflows/?search=alpha", **auth)
        assert response.status_code == 200
        names = [item["name"] for item in response.json()["items"]]
        assert "Alpha Workflow" in names

    def test_workflow_not_found(self, auth_client):
        """GET /api/workflows/99999 returns 404."""
        client, auth = auth_client
        response = client.get("/api/workflows/99999", **auth)
        assert response.status_code == 404

    def test_create_workflow_name_required(self, auth_client):
        """POST /api/workflows/ with empty name returns 422."""
        client, auth = auth_client
        response = client.post(
            "/api/workflows/",
            data={"name": "", "description": "", "definition": {}},
            content_type="application/json",
            **auth,
        )
        assert response.status_code == 422

    def test_workflow_execution_count(self, auth_client):
        """Workflow response includes execution_count field."""
        client, auth = auth_client
        create_resp = client.post(
            "/api/workflows/",
            data={"name": "Counter Test", "description": "", "definition": {}},
            content_type="application/json",
            **auth,
        )
        wf_id = create_resp.json()["id"]
        get_resp = client.get(f"/api/workflows/{wf_id}", **auth)
        assert get_resp.json()["execution_count"] == 0

    # ── Auth guard tests ────────────────────────────────────────────────────

    def test_unauthenticated_request_returns_401(self, django_client):
        """Requests without Authorization header return 401."""
        response = django_client.get("/api/workflows/")
        assert response.status_code == 401

    def test_invalid_token_returns_401(self, django_client):
        """Requests with an invalid token return 401."""
        response = django_client.get("/api/workflows/", HTTP_AUTHORIZATION="Bearer invalid")
        assert response.status_code == 401

    def test_workflow_isolation_between_users(self, db):
        """User A cannot see or modify User B's workflows."""
        user_a = User.objects.create_user(username="user_a", password="pass")
        user_b = User.objects.create_user(username="user_b", password="pass")
        client = Client()

        # User A creates a workflow
        resp = client.post(
            "/api/workflows/",
            data={"name": "User A Private", "description": "", "definition": {}},
            content_type="application/json",
            **make_auth_header(user_a),
        )
        assert resp.status_code == 201
        wf_id = resp.json()["id"]

        # User B cannot read it
        resp = client.get(f"/api/workflows/{wf_id}", **make_auth_header(user_b))
        assert resp.status_code == 404

        # User B cannot update it
        resp = client.put(
            f"/api/workflows/{wf_id}",
            data={"name": "Hijacked"},
            content_type="application/json",
            **make_auth_header(user_b),
        )
        assert resp.status_code == 404

        # User B cannot delete it
        resp = client.delete(f"/api/workflows/{wf_id}", **make_auth_header(user_b))
        assert resp.status_code == 404

        # User B's list is empty
        resp = client.get("/api/workflows/", **make_auth_header(user_b))
        assert resp.json()["total"] == 0

        # User A's list has the workflow
        resp = client.get("/api/workflows/", **make_auth_header(user_a))
        assert resp.json()["total"] == 1
        assert resp.json()["items"][0]["name"] == "User A Private"
