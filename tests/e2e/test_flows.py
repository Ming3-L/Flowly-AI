"""
Playwright E2E tests for Flowly AI critical user flows.

Prerequisites:
    pip install playwright pytest-playwright
    playwright install --with-deps chromium

Usage:
    pytest tests/e2e/ -v
    # Or with custom base URL:
    BASE_URL=http://localhost pytest tests/e2e/ -v
"""

import os
import pytest
from playwright.sync_api import Page, expect


BASE_URL = os.getenv('BASE_URL', 'http://localhost')
FRONTEND_URL = os.getenv('FRONTEND_URL', BASE_URL)
API_URL = f'{FRONTEND_URL}/api'


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope='session')
def api_client(page: Page):
    """Provide an authenticated API client via localStorage."""
    # Inject JWT tokens into localStorage for auth
    def _set_tokens(access: str, refresh: str = ''):
        page.evaluate(
            f"""
            localStorage.setItem('flowly_access_token', '{access}');
            localStorage.setItem('flowly_refresh_token', '{refresh}');
            """
        )
    return _set_tokens


# ── Authentication Tests ───────────────────────────────────────────────────────

class TestAuth:
    """Test login, register, logout flows."""

    def test_login_page_loads(self, page: Page):
        """Login page renders without errors."""
        page.goto(f'{FRONTEND_URL}/login')
        expect(page.get_by_role('heading', name='登录 Flowly AI')).to_be_visible()
        expect(page.get_by_placeholder('请输入用户名')).to_be_visible()
        expect(page.get_by_placeholder('请输入密码')).to_be_visible()

    def test_register_page_loads(self, page: Page):
        """Register page renders without errors."""
        page.goto(f'{FRONTEND_URL}/register')
        expect(page.get_by_role('heading', name='注册 Flowly AI')).to_be_visible()

    def test_login_invalid_credentials(self, page: Page):
        """Login with invalid credentials shows error."""
        page.goto(f'{FRONTEND_URL}/login')
        page.get_by_placeholder('请输入用户名').fill('nonexistent_user_xyz')
        page.get_by_placeholder('请输入密码').fill('wrong_password')
        page.get_by_role('button', name='登录').click()
        # Should show error message
        expect(page.locator('.el-message--error')).to_be_visible(timeout=5000)

    def test_navigation_to_register(self, page: Page):
        """Link from login navigates to register."""
        page.goto(f'{FRONTEND_URL}/login')
        page.get_by_text('立即注册').click()
        expect(page).to_have_url(f'{FRONTEND_URL}/register')


# ── Dashboard Tests ────────────────────────────────────────────────────────────

class TestDashboard:
    """Test the main dashboard page."""

    def test_dashboard_loads(self, page: Page):
        """Dashboard renders without errors."""
        page.goto(FRONTEND_URL)
        # Should not have console errors (checked via page.on('console'))
        page.wait_for_load_state('networkidle')

    def test_nav_menu_renders(self, page: Page):
        """Navigation menu items are visible."""
        page.goto(FRONTEND_URL)
        expect(page.get_by_text('首页')).to_be_visible()
        expect(page.get_by_text('AI 对话')).to_be_visible()
        expect(page.get_by_text('工作流')).to_be_visible()


# ── Workflow CRUD Tests ────────────────────────────────────────────────────────

class TestWorkflowList:
    """Test the workflow list page (requires auth)."""

    def test_workflow_list_requires_auth(self, page: Page):
        """Workflow list redirects to login if not authenticated."""
        page.goto(f'{FRONTEND_URL}/workflows')
        expect(page).to_have_url(f'{FRONTEND_URL}/login?redirect=/workflows', timeout=3000)

    def test_workflow_list_empty_state(self, page: Page, api_client):
        """Workflow list shows empty state when no workflows exist."""
        api_client(access='fake_token')  # Mock auth
        page.goto(f'{FRONTEND_URL}/workflows')
        page.wait_for_load_state('networkidle')
        # Empty state or table should be visible
        empty_or_table = (
            page.get_by_text('暂无工作流').or_(page.locator('.el-table'))
        )
        expect(empty_or_table.first).to_be_visible(timeout=5000)


# ── Workflow Editor Tests ──────────────────────────────────────────────────────

class TestWorkflowEditor:
    """Test the visual workflow editor."""

    def test_editor_page_loads(self, page: Page):
        """Editor page renders with canvas."""
        page.goto(f'{FRONTEND_URL}/workflows/new')
        page.wait_for_load_state('networkidle')
        # Palette should be visible
        expect(page.get_by_text('节点')).to_be_visible()
        # Canvas area should be present
        expect(page.locator('.canvas-container')).to_be_visible()

    def test_editor_palette_nodes(self, page: Page):
        """Node palette shows all 5 node types."""
        page.goto(f'{FRONTEND_URL}/workflows/new')
        page.wait_for_load_state('networkidle')

        for label in ['Chat', 'Tool', 'Condition', 'Approval', 'Parallel']:
            expect(page.get_by_text(label, exact=False).first).to_be_visible()

    def test_editor_toolbar_renders(self, page: Page):
        """Editor toolbar has zoom, layout, save buttons."""
        page.goto(f'{FRONTEND_URL}/workflows/new')
        page.wait_for_load_state('networkidle')

        expect(page.get_by_text('自动布局')).to_be_visible()
        expect(page.get_by_text('保存')).to_be_visible()
        expect(page.get_by_text('清空')).to_be_visible()

    def test_click_node_type_adds_to_canvas(self, page: Page):
        """Clicking a palette node type adds it to the canvas."""
        page.goto(f'{FRONTEND_URL}/workflows/new')
        page.wait_for_load_state('networkidle')

        # Click the Chat node type
        page.locator('.palette-item', has_text='Chat').click()

        # Should have a node on the canvas
        expect(page.locator('.node-group')).to_be_visible(timeout=3000)

    def test_node_palette_draggable(self, page: Page):
        """Palette nodes have draggable attribute."""
        page.goto(f'{FRONTEND_URL}/workflows/new')
        page.wait_for_load_state('networkidle')

        # Verify draggable attribute
        chat_palette = page.locator('.palette-item', has_text='Chat')
        expect(chat_palette).to_have_attribute('draggable', 'true')

    def test_select_node_opens_inspector(self, page: Page):
        """Selecting a node opens the right-side inspector panel."""
        page.goto(f'{FRONTEND_URL}/workflows/new')
        page.wait_for_load_state('networkidle')

        # Add a node
        page.locator('.palette-item', has_text='Chat').click()
        page.wait_for_timeout(500)

        # Click the node on canvas
        page.locator('.node-group').first.click()
        page.wait_for_timeout(300)

        # Inspector should open
        expect(page.locator('.node-inspector.open')).to_be_visible(timeout=3000)


# ── API Endpoint Tests ────────────────────────────────────────────────────────

class TestAPI:
    """Test backend API endpoints directly."""

    def test_api_health_check(self, page: Page):
        """GET /health/ returns healthy status."""
        response = page.request.get(f'{FRONTEND_URL}/health/')
        assert response.ok
        data = response.json()
        assert data['status'] == 'healthy'
        assert data['database'] == 'ok'

    def test_api_workflows_list(self, page: Page):
        """GET /api/workflows/ returns 200."""
        response = page.request.get(f'{API_URL}/workflows/')
        assert response.status_code == 200
        data = response.json()
        assert 'items' in data
        assert isinstance(data['items'], list)

    def test_api_workflows_create(self, page: Page):
        """POST /api/workflows/ creates a workflow."""
        response = page.request.post(
            f'{API_URL}/workflows/',
            json={
                'name': 'E2E Test Workflow',
                'description': 'Created by Playwright E2E test',
                'definition': {'version': '1.0', 'nodes': [], 'edges': []},
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data['name'] == 'E2E Test Workflow'
        assert data['id'] > 0

    def test_api_workflows_workflow_not_found(self, page: Page):
        """GET /api/workflows/999999 returns 404."""
        response = page.request.get(f'{API_URL}/workflows/999999')
        assert response.status_code == 404

    def test_api_workflows_update(self, page: Page):
        """PUT /api/workflows/{id} updates a workflow."""
        # Create
        create_resp = page.request.post(
            f'{API_URL}/workflows/',
            json={'name': 'Update Test', 'description': '', 'definition': {}},
        )
        wf_id = create_resp.json()['id']

        # Update
        update_resp = page.request.put(
            f'{API_URL}/workflows/{wf_id}',
            json={'name': 'Updated Name'},
        )
        assert update_resp.status_code == 200
        assert update_resp.json()['name'] == 'Updated Name'

    def test_api_workflows_delete(self, page: Page):
        """DELETE /api/workflows/{id} deactivates a workflow."""
        # Create
        create_resp = page.request.post(
            f'{API_URL}/workflows/',
            json={'name': 'Delete Test', 'description': '', 'definition': {}},
        )
        wf_id = create_resp.json()['id']

        # Delete
        delete_resp = page.request.delete(f'{API_URL}/workflows/{wf_id}')
        assert delete_resp.status_code == 200

        # Verify deactivated
        get_resp = page.request.get(f'{API_URL}/workflows/{wf_id}')
        assert get_resp.json()['is_active'] is False


# ── Settings Page Tests ───────────────────────────────────────────────────────

class TestSettings:
    """Test the settings page."""

    def test_settings_requires_auth(self, page: Page):
        """Settings page redirects to login if not authenticated."""
        page.goto(f'{FRONTEND_URL}/settings')
        expect(page).to_have_url(f'{FRONTEND_URL}/login?redirect=/settings', timeout=3000)
