---
name: code-refactoring
description: Code refactoring techniques, patterns, and best practices for improving code quality without changing behavior. Use when user asks to refactor code, clean up legacy code, improve code structure, apply design patterns, or reduce technical debt.
---

# Code Refactoring

Improve existing code structure, readability, and maintainability without changing its external behavior.

## Core Principles

1. **Behavior preservation** - Refactored code must produce identical results
2. **Small steps** - Make incremental changes, test frequently
3. **Test coverage** - Ensure tests pass before and after
4. **Single responsibility** - Each function/method does one thing

## Refactoring Checklist

- [ ] Tests pass before refactoring
- [ ] Understand the current code's purpose
- [ ] Identify code smells
- [ ] Plan the refactor in small steps
- [ ] Refactor incrementally
- [ ] Run tests after each change
- [ ] Review the result

## Common Code Smells

| Smell | Problem | Solution |
|-------|---------|----------|
| Long method | Hard to understand/test | Extract smaller methods |
| Large class | Too many responsibilities | Split into smaller classes |
| Duplicate code | Maintenance nightmare | Extract common logic |
| Dead code | Confusion, bloat | Delete it |
| Magic numbers | Unclear meaning | Extract as constants |
| Deep nesting | Hard to follow | Extract conditions, early returns |

## Extract Method

```python
# Before
def process_order(order):
    # Validate
    if not order.get('items'):
        raise ValueError("Empty order")
    if order['total'] <= 0:
        raise ValueError("Invalid total")

    # Calculate discount
    discount = 0
    if order['total'] > 100:
        discount = order['total'] * 0.1
    final_total = order['total'] - discount

    # Save
    db.orders.insert(order)
    return final_total

# After
def process_order(order):
    validate_order(order)
    discount = calculate_discount(order)
    final_total = apply_discount(order, discount)
    save_order(order)
    return final_total

def validate_order(order):
    if not order.get('items'):
        raise ValueError("Empty order")
    if order['total'] <= 0:
        raise ValueError("Invalid total")

def calculate_discount(order):
    if order['total'] > 100:
        return order['total'] * 0.1
    return 0

def apply_discount(order, discount):
    return order['total'] - discount

def save_order(order):
    db.orders.insert(order)
```

## Replace Conditional with Polymorphism

```python
# Before
class PaymentProcessor:
    def process(self, payment):
        if payment.type == 'credit':
            # Credit card logic
            pass
        elif payment.type == 'debit':
            # Debit card logic
            pass
        elif payment.type == 'crypto':
            # Crypto logic
            pass

# After
from abc import ABC, abstractmethod

class PaymentMethod(ABC):
    @abstractmethod
    def process(self, payment):
        pass

class CreditCard(PaymentMethod):
    def process(self, payment):
        # Credit card logic
        pass

class DebitCard(PaymentMethod):
    def process(self, payment):
        # Debit card logic
        pass

class PaymentProcessor:
    def __init__(self):
        self.methods = {
            'credit': CreditCard(),
            'debit': DebitCard(),
        }

    def process(self, payment):
        method = self.methods.get(payment.type)
        if method:
            method.process(payment)
```

## Replace Magic Numbers

```python
# Before
def calculate_price(quantity):
    if quantity > 10:
        return quantity * 90
    return quantity * 100

# After
DISCOUNT_THRESHOLD = 10
REGULAR_PRICE = 100
DISCOUNT_PRICE = 90

def calculate_price(quantity):
    if quantity > DISCOUNT_THRESHOLD:
        return quantity * DISCOUNT_PRICE
    return quantity * REGULAR_PRICE
```

## Remove Dead Code

```python
# Before
def process():
    # Old implementation - 2024
    # data = fetch_old_data()
    # process_v1(data)
    pass

def process():
    data = fetch_new_data()
    process_v2(data)

# After - keep only the active implementation
def process():
    data = fetch_new_data()
    process_v2(data)
```

## Simplify Conditionals

```python
# Before
if is_valid and (age >= 18 or has_permission):
    do_something()

# After - extract complex condition
def can_access(age, has_permission):
    return is_valid and (age >= 18 or has_permission)

if can_access(user.age, user.has_permission):
    do_something()
```

## Replace Temporary with Query

```python
# Before
def get_price(item):
    discount = calculate_discount()  # expensive
    if discount > 10:
        return item.price - discount
    return item.price

# After - compute once, use throughout
class OrderCalculator:
    def __init__(self, items):
        self.items = items
        self._discount = None

    @property
    def discount(self):
        if self._discount is None:
            self._discount = self.calculate_discount()
        return self._discount

    def get_price(self, item):
        if self.discount > 10:
            return item.price - self.discount
        return item.price
```

## Rename Variables/Functions

```python
# Before
def fn(x, y):
    r = x * 3.14159
    return r * y

# After
PI = 3.14159

def calculate_circle_area(radius, height):
    base_area = radius * PI
    return base_area * height
```

## Introduce Parameter Object

```python
# Before
def create_user(name, email, age, city, country, phone):
    pass

create_user("John", "john@example.com", 30, "NYC", "USA", "123-456")

# After
from dataclasses import dataclass

@dataclass
class UserRegistration:
    name: str
    email: str
    age: int
    city: str
    country: str
    phone: str

def create_user(registration: UserRegistration):
    pass

create_user(UserRegistration(
    name="John",
    email="john@example.com",
    age=30,
    city="NYC",
    country="USA",
    phone="123-456"
))
```

## JavaScript/TypeScript Patterns

```typescript
// Before - callback hell
function getData(callback) {
    fetch('/api/user', (user) => {
        fetch(`/api/posts/${user.id}`, (posts) => {
            fetch(`/api/comments/${posts[0].id}`, (comments) => {
                callback(comments);
            });
        });
    });
}

// After - async/await
async function getData() {
    const user = await fetch('/api/user');
    const posts = await fetch(`/api/posts/${user.id}`);
    const comments = await fetch(`/api/comments/${posts[0].id}`);
    return comments;
}
```

## Refactoring Safety

```bash
# Always work on a clean git state
git status
git branch refactor/feature

# Run tests BEFORE starting
npm test  # or pytest, etc.

# Commit after each small refactor
git add -p  # Review each change
git commit -m "refactor: extract validate_order function"
```

## Test After Each Change

```python
# Python
pytest -xvs  # Run tests verbosely

# JavaScript
npm test -- --watch

# Verify behavior unchanged
# If test fails: revert, fix, re-test
```
