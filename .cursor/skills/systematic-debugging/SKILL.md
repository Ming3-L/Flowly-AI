---
name: systematic-debugging
description: Systematic debugging methodology using divide-and-conquer, hypothesis testing, and root cause analysis. Use when debugging bugs, errors, crashes, unexpected behavior, performance issues, or when asked to troubleshoot any code problem.
---

# Systematic Debugging

A methodical approach to finding and fixing bugs, errors, and unexpected behavior.

## Core Principle: Divide and Conquer

```
Isolate → Hypothesize → Test → Narrow → Repeat
```

## Step 1: Reproduce the Bug

Before anything else, reproduce the issue reliably.

- Find the exact input that triggers the bug
- Note the expected vs actual behavior
- Identify if it's deterministic or intermittent
- Check if it occurs on specific environments

## Step 2: Gather Evidence

Read all available diagnostic output:

- **Frontend**: Browser Console, Network tab, Vue DevTools/React DevTools
- **Backend**: Server logs, error traces, request/response bodies
- **Build**: Compiler errors, bundler warnings, linter output

Write down the exact error message. Do NOT guess.

## Step 3: Form a Hypothesis

Based on evidence, form a specific hypothesis:

- "The bug is caused by X because Y"
- Not: "Something is broken"

## Step 4: Test the Hypothesis

Isolate the problem:

- Add logging to narrow down the code path
- Comment out code to isolate
- Use breakpoints or step-through debugging
- Create a minimal reproduction case

## Step 5: Fix and Verify

- Apply the fix
- Confirm the bug is gone
- Run tests
- Check for regressions

## Debugging Patterns

### Null/Undefined Errors

```python
# Check chain
result = data.get("key", {}).get("nested")
# Instead of
result = data["key"]["nested"]  # Will crash

# Use Optional chaining
value = obj?.prop1?.prop2
```

### Race Conditions

```python
# Use locks for shared state
import threading
lock = threading.Lock()

with lock:
    shared_resource += 1
```

### Async/Await Issues

```python
# Always await async calls
async def main():
    result = await fetch_data()  # Not: fetch_data()

# Check for missing awaits
import asyncio
asyncio.get_event_loop().run_until_complete(main())
```

### Memory Leaks

```javascript
// Clean up subscriptions
const subscription = data$.subscribe(handle);
// Later:
subscription.unsubscribe();

// Or use takeUntil
data$.pipe(takeUntil(destroy$)).subscribe(handle);
```

### API/Network Errors

```python
import requests

try:
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data = response.json()
except requests.exceptions.Timeout:
    logger.error("Request timed out")
except requests.exceptions.HTTPError as e:
    logger.error(f"HTTP error: {e.response.status_code}")
except requests.exceptions.RequestException as e:
    logger.error(f"Request failed: {e}")
```

## Debugging Checklist

- [ ] Can you reliably reproduce the issue?
- [ ] What is the exact error message?
- [ ] What is the expected behavior?
- [ ] What have you changed since it last worked?
- [ ] Does it work in isolation (minimal case)?
- [ ] Have you checked logs on both frontend and backend?
- [ ] Is it a network, data, or logic issue?

## Common Root Causes

| Symptom | Common Cause |
|---------|-------------|
| "Cannot read property of null" | Missing null check, wrong data shape |
| Race condition | Missing async/await, shared state |
| Memory leak | Unclosed connections, event listeners |
| 500 error | Backend exception, missing env var |
| 404 error | Wrong URL, missing route |
| Slow performance | N+1 query, missing index, unoptimized loop |
| Works on my machine | Environment difference, cached state |

## Tools

| Tool | Use For |
|------|---------|
| Console.log | JS runtime values |
| pdb / breakpoint() | Python debugging |
| Browser DevTools | Network, DOM, JS execution |
| Postman/curl | API testing |
| pytest -xvs | Python test debugging |
