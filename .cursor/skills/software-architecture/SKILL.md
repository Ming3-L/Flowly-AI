---
name: software-architecture
description: Software architecture skill for designing, reviewing, and implementing robust system architectures. Use when designing new systems, refactoring existing code, or making architectural decisions.
---

# Software Architecture

Design and review robust software architectures with clear separation of concerns and well-defined boundaries.

## When to Use

- Designing new systems or features
- Refactoring existing codebases
- Making architectural decisions
- Reviewing system designs
- Choosing between technology options

## Core Architectural Principles

### Separation of Concerns
Each module should have a single, well-defined responsibility.

```
Good: UserService handles user operations, OrderService handles orders
Bad: One service handles users, orders, payments, and notifications
```

### Single Responsibility Principle
A class or module should have only one reason to change.

### Dependency Inversion
Depend on abstractions, not concretions.

```
Good: service.use(repositoryInterface)
Bad: service.use(concreteMysqlRepository)
```

### Law of Demeter (Principle of Least Knowledge)
Each component should only know about its direct collaborators.

## Architecture Patterns

### Layered Architecture

```
┌─────────────────────┐
│    Presentation     │  UI, Controllers
├─────────────────────┤
│    Application      │  Use Cases, Commands
├─────────────────────┤
│      Domain         │  Entities, Business Rules
├─────────────────────┤
│   Infrastructure    │  Database, External Services
└─────────────────────┘
```

### Clean Architecture

```
┌────────────────────────────────────────┐
│              Presentation              │
├────────────────────────────────────────┤
│              Application               │
├────────────────────────────────────────┤
│                 Domain                  │
├────────────────────────────────────────┤
│              Infrastructure             │
└────────────────────────────────────────┘

Dependencies point inward only
```

### Microservices Architecture

- Single Responsibility per service
- Each service owns its data
- Services communicate via APIs
- Independent deployment

## API Design Principles

### RESTful Best Practices

| Principle | Description |
|-----------|-------------|
| Resources | Use nouns, not verbs (/users not /getUsers) |
| HTTP Methods | GET (read), POST (create), PUT/PATCH (update), DELETE (delete) |
| Status Codes | Use appropriate codes (200, 201, 400, 401, 404, 500) |
| Pagination | Use limit/offset or cursor-based |
| Versioning | Version APIs (/v1/users, /v2/users) |

### Error Handling

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input",
    "details": [
      { "field": "email", "message": "Invalid email format" }
    ]
  }
}
```

## Database Design

### Normalization Guidelines

| Level | Description | Use When |
|-------|-------------|----------|
| 1NF | Atomic values, no repeating groups | Always |
| 2NF | 1NF + no partial dependencies | When you have composite keys |
| 3NF | 2NF + no transitive dependencies | When you want to reduce redundancy |

### Indexing Strategy

- Index frequently queried columns
- Index foreign keys
- Consider composite indexes for multi-column queries
- Don't over-index (slows writes)

## Scalability Patterns

### Horizontal vs Vertical Scaling

| Type | Pros | Cons |
|------|------|------|
| Horizontal | More capacity, fault tolerance | Complexity, coordination |
| Vertical | Simple | Hardware limits, no fault tolerance |

### Caching Strategies

```
┌──────────┐     ┌──────────┐     ┌──────────┐
│ Client   │────▶│   CDN    │────▶│  Origin  │
└──────────┘     └──────────┘     └──────────┘
                        │
                        ▼
                  ┌──────────┐
                  │  Cache   │
                  │ (Redis)  │
                  └──────────┘
```

### Load Balancing

- Round Robin
- Least Connections
- IP Hash
- Session Affinity

## Architecture Decision Record (ADR)

When making significant architectural decisions, document:

```markdown
# ADR-001: Use PostgreSQL for Primary Database

## Status
Accepted

## Context
We need a primary database that supports:
- ACID transactions
- Complex queries
- JSON storage
- High availability

## Decision
We will use PostgreSQL 14+

## Consequences
### Positive
- ACID compliance
- Rich feature set
- Strong community

### Negative
- Requires operational expertise
- License considerations
```

## Code Organization

### Good Structure

```
src/
├── domain/           # Business entities, rules
│   ├── entities/
│   └── value-objects/
├── application/      # Use cases, commands
│   ├── commands/
│   └── queries/
├── infrastructure/  # External concerns
│   ├── repositories/
│   └── services/
└── presentation/    # UI, API
    ├── controllers/
    └── dto/
```

### Module Communication

```
Domain Layer
    │
    ▼
Application Layer (orchestrates domain)
    │
    ▼
Infrastructure Layer (implements interfaces)
    │
    ▼
Presentation Layer (UI/API)
```

## Review Checklist

- [ ] Clear separation of concerns
- [ ] Dependencies point inward
- [ ] Well-defined module boundaries
- [ ] Appropriate abstraction levels
- [ ] Error handling strategy
- [ ] Scalability considerations
- [ ] Security implications
- [ ] Testability

## Technology Selection

When choosing technologies:

1. **Fit for Purpose** - Does it solve the problem?
2. **Team Expertise** - Can the team use it effectively?
3. **Community & Support** - Is it actively maintained?
4. **Performance** - Does it meet requirements?
5. **Security** - Is it secure and maintained?
6. **Licensing** - Are there legal considerations?
