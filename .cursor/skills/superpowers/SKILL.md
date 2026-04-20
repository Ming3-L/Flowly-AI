---
name: superpowers
description: Core skills library for TDD, debugging, collaboration patterns, and proven development techniques. Use for brainstorming ideas, writing implementation plans, executing plans, code review, and finishing development branches.
---

# Superpowers - Development Workflow Skills

A comprehensive library of skills for professional software development workflows.

## Included Skills

### Core Workflow Skills
- **brainstorming** - Explore requirements and approaches through collaborative dialogue before writing code
- **writing-plans** - Create detailed implementation plans with bite-sized tasks
- **executing-plans** - Execute written implementation plans in a separate session with checkpoints
- **finishing-a-development-branch** - Complete development work with merge/PR options

### Collaboration Skills
- **receiving-code-review** - Handle code review feedback with technical rigor
- **dispatching-parallel-agents** - Delegate tasks to specialized agents for parallel execution
- **subagent-driven-development** - Execute plans using fresh subagent per task

### Utility Skills
- **using-git-worktrees** - Set up isolated workspaces using git worktrees
- **code-reviewer** - Review code against plan and coding standards

## Quick Start

### For New Features
1. Use **brainstorming** skill to explore and design
2. Get user approval on the design
3. Use **writing-plans** skill to create implementation plan
4. Use **subagent-driven-development** or **executing-plans** to implement
5. Use **finishing-a-development-branch** to complete

### For Code Reviews
- When **receiving** review: Use **receiving-code-review** skill
- When **conducting** review: Use **code-reviewer** skill

### For Parallel Work
- When facing multiple independent tasks: Use **dispatching-parallel-agents** skill

## Skill Descriptions

| Skill | When to Use |
|-------|-------------|
| brainstorming | Before any creative work - features, components, modifications |
| writing-plans | After brainstorming approval - create implementation plan |
| executing-plans | Execute plan in a separate session with checkpoints |
| subagent-driven-development | Execute plan in current session using subagents |
| finishing-a-development-branch | After implementation - merge, PR, or cleanup |
| receiving-code-review | When receiving feedback from reviewers |
| code-reviewer | When reviewing completed work |
| dispatching-parallel-agents | When 2+ independent tasks can run in parallel |
| using-git-worktrees | When starting isolated feature work |

## Key Principles

1. **Always design before implementing** - Use brainstorming first
2. **Write detailed plans** - Bite-sized tasks with exact steps
3. **Verify continuously** - Run tests after each task
4. **Commit frequently** - Small, focused commits
5. **Technical rigor** - Verify suggestions, don't blindly implement
6. **Isolate work** - Use git worktrees for feature work
