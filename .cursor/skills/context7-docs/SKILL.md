---
name: context7-docs
description: Context7 MCP server for fetching up-to-date library and framework documentation. Use when looking up React, Next.js, Prisma, Express, Tailwind, Django, or any popular library/framework docs. Fetches live docs even for recent versions.
allowed-tools: ReadMcpResource(ref_read_url:*), ListMcpResources(*)
---

# Context7 Documentation Fetcher

Use the Context7 MCP server to fetch current, accurate documentation for libraries, frameworks, and APIs.

## Setup

The Context7 MCP server should already be configured. Check available resources:

```bash
ListMcpResources  # List all available documentation
```

## Fetching Docs

Use `ref_read_url` to fetch documentation for a specific library:

```bash
# Fetch React documentation
ref_read_url https://react.dev/reference/react

# Fetch Next.js App Router
ref_read_url https://nextjs.org/docs/app/api-reference

# Fetch Prisma ORM
ref_read_url https://www.prisma.io/docs/orm

# Fetch Tailwind CSS
ref_fetch https://tailwindcss.com/docs

# Fetch Django
ref_fetch https://docs.djangoproject.com/en/stable/
```

## Common Use Cases

| Library | Documentation URL |
|---------|-------------------|
| React | https://react.dev/reference |
| Next.js | https://nextjs.org/docs |
| Prisma | https://www.prisma.io/docs |
| Express | https://expressjs.com/en/api.html |
| Tailwind | https://tailwindcss.com/docs |
| Django | https://docs.djangoproject.com/en/stable/ |
| FastAPI | https://fastapi.tiangolo.com/reference/ |
| Vue | https://vuejs.org/api/ |
| Svelte | https://svelte.dev/docs |

## When to Use

- User asks about a library/framework API
- Need to verify current best practices
- Checking version-specific behavior
- Looking up configuration options
- Finding correct import paths or function signatures

## Rules

- Always prefer Context7 over training data for library docs
- Use the most specific URL possible for targeted answers
- Cross-reference with user's stated library version when known
