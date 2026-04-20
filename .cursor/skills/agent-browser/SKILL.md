---
name: agent-browser
description: Browser automation CLI for AI agents. Use when the user needs to interact with websites, including navigating pages, filling forms, clicking buttons, taking screenshots, extracting data, testing web apps, or automating any browser task. Triggers include requests to "open a website", "fill out a form", "click a button", "take a screenshot", "scrape data from a page", "test this web app", "login to a site", "automate browser actions", or any task requiring programmatic web interaction.
allowed-tools: Bash(npx agent-browser:*), Bash(agent-browser:*)
---

# Browser Automation with agent-browser

The CLI uses Chrome/Chromium via CDP directly. Install via `npm i -g agent-browser`, `brew install agent-browser`, or `cargo install agent-browser`. Run `agent-browser install` to download Chrome. Run `agent-browser upgrade` to update to the latest version.

## Core Workflow

Every browser automation follows this pattern:

1. **Navigate**: `agent-browser open <url>`
2. **Snapshot**: `agent-browser snapshot -i` (get element refs like `@e1`, `@e2`)
3. **Interact**: Use refs to click, fill, select
4. **Re-snapshot**: After navigation or DOM changes, get fresh refs

```bash
agent-browser open https://example.com/form
agent-browser snapshot -i
# Output: @e1 [input type="email"], @e2 [input type="password"], @e3 [button] "Submit"

agent-browser fill @e1 "user@example.com"
agent-browser fill @e2 "password123"
agent-browser click @e3
agent-browser wait --load networkidle
agent-browser snapshot -i  # Check result
```

## Command Chaining

Commands can be chained with `&&` in a single shell invocation. The browser persists between commands via a background daemon.

```bash
# Chain open + wait + snapshot in one call
agent-browser open https://example.com && agent-browser wait --load networkidle && agent-browser snapshot -i

# Chain multiple interactions
agent-browser fill @e1 "user@example.com" && agent-browser fill @e2 "password123" && agent-browser click @e3
```

## Essential Commands

```bash
# Navigation
agent-browser open <url>              # Navigate
agent-browser close                   # Close browser

# Snapshot
agent-browser snapshot -i             # Interactive elements with refs

# Interaction
agent-browser click @e1              # Click element
agent-browser fill @e2 "text"        # Clear and type text
agent-browser select @e1 "option"     # Select dropdown option
agent-browser check @e1              # Check checkbox
agent-browser press Enter            # Press key
agent-browser scroll down 500        # Scroll page

# Get information
agent-browser get text @e1           # Get element text
agent-browser get url                # Get current URL
agent-browser get title              # Get page title

# Wait
agent-browser wait @e1               # Wait for element
agent-browser wait --load networkidle # Wait for network idle
agent-browser wait --url "**/page"   # Wait for URL pattern

# Capture
agent-browser screenshot             # Screenshot to temp dir
agent-browser screenshot --full      # Full page screenshot
agent-browser screenshot --annotate   # Annotated screenshot
```

## Handling Authentication

**Option 1: Import auth from browser (fastest)**
```bash
agent-browser --auto-connect state save ./auth.json
agent-browser --state ./auth.json open https://app.example.com/dashboard
```

**Option 2: Session name (auto-save/restore)**
```bash
agent-browser --session-name myapp open https://app.example.com/login
# ... login flow ...
agent-browser close  # State auto-saved
agent-browser --session-name myapp open https://app.example.com/dashboard
```

## Common Patterns

### Form Submission
```bash
agent-browser open https://example.com/signup
agent-browser snapshot -i
agent-browser fill @e1 "Jane Doe"
agent-browser fill @e2 "jane@example.com"
agent-browser click @e3
agent-browser wait --load networkidle
```

### Data Extraction
```bash
agent-browser open https://example.com/products
agent-browser snapshot -i
agent-browser get text @e5
agent-browser get text body > page.txt
```

### Parallel Sessions
```bash
agent-browser --session site1 open https://site-a.com
agent-browser --session site2 open https://site-b.com
agent-browser --session site1 snapshot -i
```

## Security Features

**Domain Allowlist:**
```bash
export AGENT_BROWSER_ALLOWED_DOMAINS="example.com,*.example.com"
```

**Content Boundaries:**
```bash
export AGENT_BROWSER_CONTENT_BOUNDARIES=1
```

## Ref Lifecycle

Refs (`@e1`, `@e2`, etc.) are invalidated when the page changes. Always re-snapshot after clicking navigation elements or form submissions.

```bash
agent-browser click @e5              # Navigates to new page
agent-browser snapshot -i            # MUST re-snapshot
agent-browser click @e1              # Use new refs
```

## Diffing (Verifying Changes)

Use `diff snapshot` after performing an action to verify it had the intended effect.

```bash
agent-browser snapshot -i          # Take baseline snapshot
agent-browser click @e2            # Perform action
agent-browser diff snapshot        # See what changed
```

## Timeouts

The default timeout is 25 seconds. Use explicit waits for slow websites:

```bash
agent-browser wait --load networkidle  # Wait for network idle
agent-browser wait "#content"          # Wait for element
agent-browser wait 5000                # Wait milliseconds
```

## Session Management

Always close your browser session when done:
```bash
agent-browser close                    # Close default session
agent-browser --session agent1 close   # Close specific session
```

For more commands and patterns, see the full documentation.
