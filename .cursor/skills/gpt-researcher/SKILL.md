---
name: gpt-researcher
description: AI-powered research agent for comprehensive topic exploration, source gathering, and structured report generation. Use when user needs to research a topic, gather information from multiple sources, write research reports, or perform deep analysis.
---

# GPT Researcher

AI-powered autonomous research agent for comprehensive topic investigation.

## Research Workflow

### Phase 1: Define Research Scope

1. **Clarify the question**: What exactly needs to be researched?
2. **Set boundaries**: Time period, geographic scope, industry?
3. **Identify key aspects**: What sub-questions need answering?
4. **Determine output format**: Report, summary, comparison table?

### Phase 2: Gather Information

Use multiple sources:

```python
# Web search using Tavily
from tavily import TavilyClient

client = TavilyClient()
results = client.search(
    query="your research topic",
    search_depth="advanced",
    max_results=20,
    include_answer=True,
    recency_days=365  # Recent information
)
```

### Phase 3: Analyze and Synthesize

```python
# Structure findings
findings = {
    "main_themes": [],
    "key_facts": [],
    "contradictions": [],
    "sources": []
}

for result in results["results"]:
    findings["sources"].append({
        "title": result["title"],
        "url": result["url"],
        "relevance": result.get("score", 0)
    })
```

### Phase 4: Generate Report

Structure the final output:

```
1. Executive Summary (1-2 paragraphs)
2. Background/Context
3. Key Findings (numbered)
4. Analysis
5. Implications
6. Conclusions
7. References
```

## Research Methods

### Comparative Analysis

```python
# Compare multiple approaches/technologies
comparisons = {
    "Python": {
        "pros": ["Easy to learn", "Large ecosystem"],
        "cons": ["Slower than compiled languages"],
        "use_cases": ["Data science", "Web", "Automation"]
    },
    "JavaScript": {
        "pros": ["Universal (frontend+backend)", "Vast npm ecosystem"],
        "cons": ["Callback hell historically", "Type coercion issues"],
        "use_cases": ["Web apps", "Mobile", "Real-time"]
    }
}
```

### Trend Analysis

```python
# Identify trends from search results
trends = {
    "rising": [],    # Increasingly mentioned
    "declining": [],  # Less mentioned recently
    "stable": []      # Consistently referenced
}
```

### Source Evaluation

| Criteria | Question |
|----------|----------|
| Authority | Who wrote this? Expert or reputable source? |
| Currency | Is this up-to-date? |
| Objectivity | Is it biased or trying to sell something? |
| Coverage | Does it cover the topic comprehensively? |
| Evidence | Are claims backed by data? |

## Output Formats

### Research Brief (500-1000 words)

```markdown
# Research Brief: [Topic]

## Key Findings
1. Finding one
2. Finding two
3. Finding three

## Analysis
[Paragraphs explaining each finding]

## Implications
[What this means practically]

## Sources
- Source 1 (URL)
- Source 2 (URL)
```

### Comprehensive Report (2000+ words)

```markdown
# Research Report: [Topic]

## Executive Summary
[2-3 sentence overview]

## 1. Introduction
[Background and context]

## 2. Methodology
[How the research was conducted]

## 3. Findings
### 3.1 [Sub-topic 1]
### 3.2 [Sub-topic 2]

## 4. Analysis
[Deep dive into implications]

## 5. Recommendations
[Actionable steps]

## 6. Conclusion

## References
[All sources cited]
```

### Comparison Table

| Aspect | Option A | Option B | Option C |
|--------|----------|----------|----------|
| Cost | Low | Medium | High |
| Performance | Fast | Medium | Fastest |
| Ecosystem | Large | Medium | Growing |
| Learning Curve | Easy | Medium | Hard |

## Quality Checklist

- [ ] Multiple independent sources consulted
- [ ] Sources are current and authoritative
- [ ] Facts distinguished from opinions
- [ ] Contradicting viewpoints included
- [ ] Data and statistics cited
- [ ] Limitations acknowledged
- [ ] Conclusions follow from evidence

## Research Templates

### Initial Query Generator

```python
def expand_query(base_query):
    """Generate related queries for comprehensive research."""
    templates = [
        f"{base_query} best practices",
        f"{base_query} tutorial 2026",
        f"{base_query} comparison",
        f"{base_query} pros and cons",
        f"{base_query} case studies",
        f"latest {base_query} trends",
        f"{base_query} tools and software",
        f"{base_query} implementation guide"
    ]
    return templates
```

## Automation

### Scheduled Research Reports

```python
# Weekly research digest
import asyncio
from datetime import datetime

async def weekly_research():
    topics = ["AI developments", "tech industry news", "new tools"]
    for topic in topics:
        results = await search_async(topic)
        await generate_summary(results)
    await compile_digest()
```

## Best Practices

1. **Start broad, then narrow** - Get general understanding before diving deep
2. **Cross-reference sources** - Don't rely on single source
3. **Note publication dates** - Prioritize recent information
4. **Track all sources** - Document everything for citations
5. **Question everything** - Apply critical thinking
6. **Update regularly** - Research can become outdated
