---
name: subagent-driven-development
description: Use when executing implementation plans with independent tasks in the current session
---

# Subagent-Driven Development

Execute plan by dispatching fresh subagent per task, with two-stage review after each: spec compliance review first, then code quality review.

**Why subagents:** You delegate tasks to specialized agents with isolated context. By precisely crafting their instructions and context, you ensure they stay focused and succeed at their task.

**Core principle:** Fresh subagent per task + two-stage review = high quality, fast iteration

## When to Use

**vs. Executing Plans (parallel session):**
- Same session (no context switch)
- Fresh subagent per task (no context pollution)
- Two-stage review after each task: spec compliance first, then code quality
- Faster iteration (no human-in-loop between tasks)

## The Process

### Per Task:

1. **Dispatch implementer subagent** with full task text + context
2. **If implementer asks questions:** Answer clearly and completely
3. **Implementer implements, tests, commits, self-reviews**
4. **Dispatch spec reviewer subagent** to confirm code matches spec
5. **If spec reviewer finds issues:** Implementer fixes them, re-review
6. **Dispatch code quality reviewer subagent**
7. **If quality reviewer finds issues:** Implementer fixes them, re-review
8. **Mark task complete in TodoWrite**

### After All Tasks:

1. **Dispatch final code reviewer** for entire implementation
2. **Use finishing-a-development-branch skill**

## Model Selection

Use the least powerful model that can handle each role:

- **Mechanical implementation tasks** (isolated functions, clear specs): use fast model
- **Integration and judgment tasks** (multi-file coordination): use standard model
- **Architecture, design, and review tasks**: use most capable model

## Handling Implementer Status

Implementer subagents report one of four statuses:

- **DONE:** Proceed to spec compliance review
- **DONE_WITH_CONCERNS:** Read concerns, address if needed before review
- **NEEDS_CONTEXT:** Provide missing context and re-dispatch
- **BLOCKED:** Assess blocker and adjust approach

## Red Flags

**Never:**
- Start implementation on main/master branch without explicit user consent
- Skip reviews (spec compliance OR code quality)
- Proceed with unfixed issues
- Dispatch multiple implementation subagents in parallel
- Make subagent read plan file (provide full text instead)
- Skip scene-setting context
- Ignore subagent questions
- Accept "close enough" on spec compliance
- Move to next task while either review has open issues

## Integration

**Required workflow skills:**
- **superpowers:using-git-worktrees** - REQUIRED: Set up isolated workspace before starting
- **superpowers:writing-plans** - Creates the plan this skill executes
- **superpowers:finishing-a-development-branch** - Complete development after all tasks
