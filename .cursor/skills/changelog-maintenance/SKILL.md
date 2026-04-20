---
name: changelog-maintenance
description: Maintain and update CHANGELOG files following Keep a Changelog standard. Use when user asks to update changelog, document changes, track version history, or generate release notes.
---

# Changelog Maintenance

Maintain organized, standardized changelog files following the Keep a Changelog convention.

## Changelog Format (Keep a Changelog)

```markdown
# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- New feature descriptions

### Changed
- Changes in existing functionality

### Deprecated
- Soon-to-be removed features

### Removed
- Removed features

### Fixed
- Bug fixes

### Security
- Security improvements

## [1.2.0] - 2026-04-15

### Added
- User authentication with JWT tokens
- Password reset functionality

### Fixed
- Resolved memory leak in WebSocket handler
- Fixed race condition in concurrent requests

## [1.1.0] - 2026-01-01

### Changed
- Updated API response format
- Migrated database to PostgreSQL
```

## Adding New Entries

When adding a change, insert it under the `[Unreleased]` section in the appropriate subsection:

```markdown
## [Unreleased]

### Added
- **2026-04-15**: User authentication with JWT (#123)
- Real-time notifications via WebSocket

### Fixed
- **2026-04-10**: Memory leak in cache handler
```

## Semantic Versioning

| Version | Meaning | Example |
|---------|---------|---------|
| Major (X.0.0) | Breaking changes | Removed API v1, changed auth |
| Minor (0.X.0) | New features (backward compatible) | Added export feature |
| Patch (0.0.X) | Bug fixes (backward compatible) | Fixed login bug |

## Commit Message Convention

Use conventional commits to auto-generate changelog:

```
feat(auth): add JWT authentication
fix(api): resolve timeout issue in user endpoint
docs: update README installation instructions
refactor(core): simplify request handling
test(payment): add unit tests for checkout flow
```

### Commit Types

| Type | Section |
|------|---------|
| feat | Added |
| fix | Fixed |
| docs | Changed |
| refactor | Changed |
| perf | Changed |
| test | (internal) |
| chore | (internal) |

## Auto-generate with Git Logs

```python
import subprocess
from datetime import datetime

def generate_changelog():
    # Get commits since last release tag
    result = subprocess.run(
        ['git', 'log', '--pretty=format:%s|%b', '--no-merges'],
        capture_output=True, text=True
    )

    changes = {'added': [], 'fixed': [], 'changed': []}

    for line in result.stdout.split('\n'):
        if line.startswith('feat:'):
            changes['added'].append(line[5:])
        elif line.startswith('fix:'):
            changes['fixed'].append(line[5:])
        elif any(line.startswith(t) for t in ['refactor:', 'perf:', 'docs:']):
            changes['changed'].append(line.split(':')[1] if ':' in line else line)

    return changes
```

## Release Process

1. **Update Unreleased section**: Move unreleased changes to new version
2. **Add date**: Use `YYYY-MM-DD` format
3. **Create Git tag**: `git tag -a v1.2.0 -m "Release version 1.2.0"`
4. **Push tags**: `git push origin --tags`
5. **GitHub Release**: Create release with changelog entry

## Workflow

```
1. Merge feature branch
   ↓
2. Write changelog entry under [Unreleased]
   ↓
3. When ready to release:
   - Move [Unreleased] to new version section
   - Add release date
   - Commit
   - Create git tag
   - Push
   ↓
4. Generate GitHub release notes
```

## GitHub Actions Auto-Changelog

```yaml
# .github/workflows/changelog.yml
name: Changelog
on:
  release:
    types: [published]

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - name: Generate release notes
        run: |
          git tag --sort=-v:refname -l 'v*' | head -n 20 > tags.txt
          # Use conventional-changelog-cli to generate
```

## Tools

| Tool | Purpose |
|------|---------|
| [conventional-changelog](https://github.com/conventional-changelog/conventional-changelog) | Auto-generate from commits |
| [release-please](https://github.com/googleapis/release-please) | Automated releases |
| [Keep a Changelog](https://keepachangelog.com) | Format standard |

## Checklist

- [ ] New features documented in Added section
- [ ] Bug fixes documented in Fixed section
- [ ] Breaking changes clearly marked
- [ ] Version numbers follow semver
- [ ] Dates in YYYY-MM-DD format
- [ ] Links to issues/PRs when applicable
- [ ] Internal changes (tests, chores) excluded from changelog
