---
name: tavily-search
description: Tavily AI search API integration for comprehensive web research, fact-checking, and content extraction. Use when user needs to search the web, research topics, extract content from URLs, or perform AI-powered search with context awareness.
---

# Tavily Search Integration

Tavily is an AI-powered search API designed for AI agents and LLM applications.

## Setup

```bash
pip install tavily-python
```

Get your API key from https://tavily.com

```python
import os
os.environ["TAVILY_API_KEY"] = "your-api-key"
```

## Basic Search

```python
from tavily import TavilyClient

client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

response = client.search(query="latest AI trends 2026")
for result in response["results"]:
    print(result["title"], result["url"])
```

## Search with Context

```python
response = client.search(
    query="Python async best practices",
    search_depth="advanced",      # "basic" or "advanced"
    max_results=10,
    include_answer=True,           # AI-generated answer
    include_raw_content=False,
    include_images=False,
    recency_days=30,               # Limit to recent results
)
print(response["answer"])
```

## Extract Content from URLs

```python
response = client.extract(urls=["https://example.com/article"])
for result in response["results"]:
    print(result["raw_content"][:500])
```

## Research Mode (Multi-source)

```python
response = client.research(
    query="compare Python vs JavaScript for backend",
    depth="deep",
    max_sources=5
)
for source in response["sources"]:
    print(source["url"], source["score"])
```

## JSON Output

```python
response = client.search(
    query="machine learning trends",
    include_answer=True
)
import json
print(json.dumps(response, indent=2))
```

## Common Patterns

| Use Case | Method | Key Params |
|----------|--------|-----------|
| Quick search | `search()` | `query`, `max_results` |
| Deep research | `research()` | `query`, `depth`, `max_sources` |
| URL extraction | `extract()` | `urls` (list) |
| News only | `search()` + `recency_days` | `recency_days=7` |

## Environment Variable

Always use environment variable for API key:

```python
import os
os.environ.setdefault("TAVILY_API_KEY", "your-key")
```
