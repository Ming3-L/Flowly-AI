---
name: webapp-testing
description: Web application testing including Playwright, Selenium, unit tests, integration tests, and end-to-end testing. Use when user asks to test a web app, write tests, run automated tests, verify functionality, or check UI behavior.
---

# Web Application Testing

Comprehensive testing strategy for web applications using modern testing tools.

## Testing Pyramid

```
        /\
       /E2E\        ← Few, slow, expensive
      /------\
     /Integration\ ← Some, medium
    /--------------\
   /   Unit Tests   \ ← Many, fast, cheap
  /------------------\
```

## Unit Testing

### Python (pytest)

```python
# test_calculator.py
import pytest

def add(a, b):
    return a + b

def test_add():
    assert add(2, 3) == 5
    assert add(-1, 1) == 0

def test_add_strings():
    with pytest.raises(TypeError):
        add("2", 3)
```

### JavaScript (Jest/Vitest)

```javascript
// sum.test.js
export function sum(a, b) {
  return a + b;
}

test('adds two numbers', () => {
  expect(sum(2, 3)).toBe(5);
});
```

### Run Tests

```bash
# Python
pytest -v
pytest -x          # Stop on first failure
pytest --cov       # Coverage report

# JavaScript
npm test
npx vitest run     # Single run
npx vitest --coverage
```

## Component Testing

### React Testing Library

```javascript
// Button.test.jsx
import { render, screen, fireEvent } from '@testing-library/react';
import Button from './Button';

test('renders with text', () => {
  render(<Button>Click me</Button>);
  expect(screen.getByText('Click me')).toBeInTheDocument();
});

test('calls onClick when clicked', () => {
  const handleClick = jest.fn();
  render(<Button onClick={handleClick}>Click</Button>);
  fireEvent.click(screen.getByRole('button'));
  expect(handleClick).toHaveBeenCalledTimes(1);
});
```

### Vue Testing Library

```javascript
import { render, screen, fireEvent } from '@testing-library/vue';
import LoginForm from './LoginForm.vue';

test('submits form with values', async () => {
  const handleSubmit = jest.fn();
  render(LoginForm, { props: { onSubmit: handleSubmit } });

  await fireEvent.update(screen.getByLabelText('Email'), 'test@example.com');
  await fireEvent.submit(screen.getByRole('form'));

  expect(handleSubmit).toHaveBeenCalledWith({ email: 'test@example.com' });
});
```

## End-to-End Testing (Playwright)

### Installation

```bash
npm init playwright@latest
npx playwright install chromium
```

### Basic Test

```javascript
// tests/e2e/login.spec.js
const { test, expect } = require('@playwright/test');

test.describe('Login Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
  });

  test('successful login', async ({ page }) => {
    await page.fill('[data-testid="email"]', 'user@example.com');
    await page.fill('[data-testid="password"]', 'password123');
    await page.click('[data-testid="submit"]');

    await expect(page).toHaveURL('/dashboard');
    await expect(page.locator('.welcome-message')).toBeVisible();
  });

  test('invalid credentials show error', async ({ page }) => {
    await page.fill('[data-testid="email"]', 'wrong@example.com');
    await page.fill('[data-testid="password"]', 'wrongpass');
    await page.click('[data-testid="submit"]');

    await expect(page.locator('.error-message')).toContainText('Invalid credentials');
  });
});
```

### API Testing

```javascript
test('creates user via API', async ({ request }) => {
  const response = await request.post('/api/users', {
    data: {
      name: 'John Doe',
      email: 'john@example.com'
    }
  });

  expect(response.ok()).toBeTruthy();
  const user = await response.json();
  expect(user.name).toBe('John Doe');
});
```

### Visual Testing

```javascript
test('homepage visual', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveScreenshot('homepage.png');
});
```

## Integration Testing

### API Testing (Python + FastAPI)

```python
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_create_user():
    response = client.post("/api/users", json={
        "name": "John",
        "email": "john@example.com"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "John"
    assert "id" in data

def test_get_user():
    response = client.get("/api/users/1")
    assert response.status_code == 200
```

## Test Organization

```
tests/
├── unit/
│   ├── test_*.py
│   └── test_*.test.js
├── integration/
│   └── test_api.py
├── e2e/
│   └── *.spec.js
└── fixtures/
    └── conftest.py
```

## Test Best Practices

| Practice | Why |
|----------|-----|
| Test behavior, not implementation | Avoids brittle tests |
| One assertion per test (when practical) | Clearer failures |
| Descriptive test names | Self-documenting |
| Setup/teardown properly | Clean state |
| Mock external dependencies | Speed, reliability |
| Run tests in CI/CD | Catch issues early |

## CI/CD Integration

```yaml
# GitHub Actions example
name: Test
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - run: npm ci
      - run: npm test
      - run: npx playwright install --with-deps
      - run: npx playwright test
```

## Debugging Failed Tests

```bash
# Playwright
npx playwright test --debug
npx playwright show-trace trace.zip

# Python
pytest -xvs              # Verbose, stop on first
pytest --tb=long         # Full traceback
pytest --pdb             # Drop into debugger
```
