---
name: skill-creator
description: Create new Cursor Agent Skills by following the SKILL.md format standard. Use when user asks to create a new skill, add a skill, or author a skill for Cursor. Guides through skill structure, naming, description writing, and file creation.
---

# Skill Creator

Create new Cursor Agent Skills following the standard SKILL.md format.

## Skill Directory Structure

```
skill-name/
├── SKILL.md              # Required - main instructions
├── reference.md           # Optional - detailed documentation
├── examples.md           # Optional - usage examples
└── scripts/              # Optional - utility scripts
    ├── validate.py
    └── helper.sh
```

## Storage Locations

| Type | Path | Scope |
|------|------|-------|
| Personal | `~/.cursor/skills/skill-name/` | All projects |
| Project | `.cursor/skills/skill-name/` | Current project |

> **Note:** Never create skills in `~/.cursor/skills-cursor/` — that's for Cursor's built-in skills.

## SKILL.md Format

Every skill requires frontmatter and markdown body:

```markdown
---
name: skill-name
description: Brief description of what this skill does and when to use it
---

# Skill Name

## Instructions
Step-by-step guidance for the agent.

## Examples
Concrete usage examples.
```

## Required Frontmatter Fields

| Field | Rules | Purpose |
|-------|-------|---------|
| `name` | Max 64 chars, lowercase, letters/numbers/hyphens only | Unique identifier |
| `description` | Max 1024 chars, non-empty, third person | Triggers skill discovery |

## Writing Good Descriptions

Write in **third person** — this gets injected into system prompt:

```
Good:   "Processes PDF files, extracts text and tables."
Bad:    "I can help you process PDF files."
Bad:    "You can use this to process files."
```

Include **WHAT** and **WHEN**:

```
PDF Processing:
"Extract text and tables from PDF files, fill forms, merge documents.
 Use when working with PDF files or when the user mentions PDFs, forms,
 document extraction, PDF conversion, or merging/splitting PDFs."
```

## Skill Creation Workflow

### Phase 1: Discovery (Ask Questions)

If information is missing, gather:

1. Purpose and scope
2. Storage location (personal vs project)
3. Trigger scenarios
4. Specific requirements
5. Existing examples to follow

### Phase 2: Design

1. Draft skill name (lowercase, hyphens)
2. Write description (third person, specific)
3. Outline main sections
4. Identify if scripts are needed

### Phase 3: Implementation

```bash
# Create directory
New-Item -ItemType Directory -Path ".cursor\skills\skill-name" -Force

# Create SKILL.md
# Write content following this format
```

### Phase 4: Verification

- [ ] Description is specific and includes trigger terms
- [ ] Written in third person
- [ ] SKILL.md under 500 lines
- [ ] Consistent terminology
- [ ] Examples are concrete

## Common Patterns

### Template Pattern

```markdown
## Output Template

Use this structure:

\`\`\`markdown
# [Title]

## Summary
[One paragraph]

## Details
- Point 1
- Point 2
\`\`\`
```

### Checklist Pattern

```markdown
## Review Checklist

- [ ] Item 1
- [ ] Item 2
- [ ] Item 3
```

### Workflow Pattern

```markdown
## Workflow

**Step 1:** Do this
**Step 2:** Do that
**Step 3:** Verify result

\`\`\`bash
command to run
\`\`\`
```

## Anti-Patterns to Avoid

| Don't | Do |
|-------|-----|
| Windows paths (`scripts\helper.py`) | Unix paths (`scripts/helper.py`) |
| Too many library options | One default with escape hatch |
| Time-sensitive info | Versioned or stable info |
| Vague skill names (`helper`) | Specific names (`pdf-processing`) |

## Examples

### Minimal Skill

```markdown
---
name: hello-world
description: Prints a greeting message. Use when user asks to say hello or test the system.
---

# Hello World

\`\`\`python
print("Hello, World!")
\`\`\`
```

### Full Featured Skill

```markdown
---
name: code-review
description: Review code for quality, security, and maintainability. Use when reviewing pull requests, examining code changes, or when user asks for a code review.
---

# Code Review

## When to Use
...

## Review Checklist
...

## Providing Feedback
...
```
