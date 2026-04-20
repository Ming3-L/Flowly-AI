---
name: security-audit
description: Security auditing skill for identifying vulnerabilities, security risks, and dangerous code patterns. Use when reviewing code for security issues, before deploying, or when user asks for security audit.
---

# Security Audit

Perform comprehensive security audits to identify vulnerabilities and security risks in code.

## When to Use

- Before deploying applications
- When user asks for security review
- When adding authentication/authorization
- When handling sensitive data
- Regular security assessments

## Core Security Principles

### Defense in Depth
Layer multiple security controls so that if one fails, others provide protection.

### Principle of Least Privilege
Grant only the minimum permissions necessary for users and services to perform their tasks.

### Secure by Default
Design systems to be secure out of the box, not requiring additional configuration.

### Fail Securely
When errors occur, systems should fail in a way that does not compromise security.

## Common Vulnerability Categories

### Injection Attacks

**SQL Injection:**
```sql
-- Vulnerable
"SELECT * FROM users WHERE id = " + userId

-- Secure
"SELECT * FROM users WHERE id = ?"
```

**XSS (Cross-Site Scripting):**
```javascript
// Vulnerable
element.innerHTML = userInput;

// Secure
element.textContent = userInput;
// or
element.setAttribute('data-value', userInput);
```

**Command Injection:**
```bash
# Vulnerable
system("rm " + filename);

# Secure - validate input, use parameterized commands
```

### Authentication & Authorization

- Never store passwords in plain text (use bcrypt, Argon2)
- Implement proper session management
- Use secure token generation (crypto.randomBytes)
- Rate limit authentication attempts
- Implement MFA for sensitive operations

### Data Protection

- Encrypt sensitive data at rest
- Use HTTPS for all communications
- Validate and sanitize all input
- Escape output appropriately
- Protect against CSRF attacks

### Secure Coding Practices

| Practice | Description |
|----------|-------------|
| Input Validation | Validate all user input on server-side |
| Output Encoding | Encode data based on context (HTML, URL, JS) |
| Error Handling | Don't expose sensitive info in errors |
| Logging | Log security events without sensitive data |
| Dependencies | Keep libraries updated, audit for vulnerabilities |

## Audit Checklist

### Authentication
- [ ] Strong password policies enforced
- [ ] Passwords properly hashed (bcrypt, Argon2)
- [ ] Session tokens are cryptographically secure
- [ ] Sessions expire after inactivity
- [ ] MFA available for sensitive operations

### Authorization
- [ ] Role-based access control implemented
- [ ] Users can only access their own data
- [ ] API endpoints protected
- [ ] Admin functions require elevated privileges

### Data Protection
- [ ] Sensitive data encrypted at rest
- [ ] HTTPS used everywhere
- [ ] User input validated and sanitized
- [ ] Output properly encoded
- [ ] Secrets not in code (use env vars)

### Error Handling
- [ ] No stack traces in production
- [ ] No sensitive data in logs
- [ ] Generic error messages for users
- [ ] Errors don't reveal system details

### Dependencies
- [ ] Regular dependency audits
- [ ] Known vulnerabilities patched
- [ ] Minimal dependencies used
- [ ] Trusted sources only

## Vulnerability Scanning Tools

```bash
# Node.js
npm audit
npx auditjs

# Python
pip-audit
bandit

# General
npx retire
owasp-dependency-check
```

## Security Headers

Implement these HTTP security headers:

```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000
Content-Security-Policy: default-src 'self'
Referrer-Policy: strict-origin-when-cross-origin
```

## Secure Development Lifecycle

1. **Design** - Threat model during design phase
2. **Develop** - Follow secure coding practices
3. **Test** - Security testing and vulnerability scanning
4. **Deploy** - Secure configuration, environment separation
5. **Monitor** - Log security events, monitor for breaches

## Reporting Security Issues

For found vulnerabilities:
1. Document the issue clearly
2. Provide severity assessment (Critical/High/Medium/Low)
3. Show exploitation scenario
4. Suggest remediation
5. Do NOT expose publicly until fixed
