---
name: frontend-design
description: Build web interfaces with genuine design quality, not AI slop. Use for any frontend work - landing pages, web apps, dashboards, admin panels, components, interactive experiences. Activates for both greenfield builds and modifications to existing applications. Detects existing design systems and respects them. Covers composition, typography, color, motion, and copy.
---

# Frontend Design

Build production-grade interfaces using genuine design principles, not AI slop.

## When to Use

- Any frontend work (landing pages, web apps, dashboards, admin panels, components)
- Both new builds and modifications to existing applications
- When user requests UI/UX work (design, build, create, implement, review, fix, improve)
- When you need to create visually appealing and professional interfaces

## Core Design Principles

### 1. No Emoji as Icons
Use SVG icons (Heroicons, Lucide, Simple Icons) instead of emojis as UI icons.

### 2. Stable Hover States
Use color/opacity transitions on hover, NOT scale transforms that shift layout.

### 3. Consistent Brand Logos
Research official SVG from Simple Icons, don't guess or use incorrect logo paths.

### 4. Consistent Icon Sizing
Use fixed viewBox (24x24) with consistent w-6 h-6 sizing.

### 5. Cursor Pointer
Add `cursor-pointer` to all clickable/hoverable interactive elements.

### 6. Hover Feedback
Provide visual feedback (color, shadow, border) on hover.

### 7. Smooth Transitions
Use `transition-colors duration-200` (150-300ms), not instant changes or too slow (>500ms).

## Design System Checklist

### Visual Quality
- [ ] No emojis used as icons (use SVG instead)
- [ ] All icons from consistent icon set (Heroicons/Lucide)
- [ ] Brand logos are correct (verified from Simple Icons)
- [ ] Hover states don't cause layout shift
- [ ] Use theme colors directly (bg-primary) not var() wrapper

### Interaction
- [ ] All clickable elements have `cursor-pointer`
- [ ] Hover states provide clear visual feedback
- [ ] Transitions are smooth (150-300ms)
- [ ] Focus states visible for keyboard navigation

### Light/Dark Mode
- [ ] Light mode text has sufficient contrast (4.5:1 minimum)
- [ ] Glass/transparent elements visible in light mode
- [ ] Borders visible in both modes
- [ ] Test both modes before delivery

### Layout
- [ ] Floating elements have proper spacing from edges
- [ ] No content hidden behind fixed navbars
- [ ] Responsive at 375px, 768px, 1024px, 1440px
- [ ] No horizontal scroll on mobile

### Accessibility
- [ ] All images have alt text
- [ ] Form inputs have labels
- [ ] Color is not the only indicator
- [ ] `prefers-reduced-motion` respected

## Design System Generation

When starting a UI project, generate a design system using the ui-ux-pro-max skill:

```bash
python3 skills/ui-ux-pro-max/scripts/search.py "<product_type> <industry> <keywords>" --design-system -p "Project Name"
```

This provides:
1. Complete design system: pattern, style, colors, typography, effects
2. Anti-patterns to avoid
3. Implementation guidelines

## UI/UX Best Practices

### Typography
- Choose font pairings appropriate for the industry
- Use readable font sizes (base 16px minimum for body text)
- Maintain consistent heading hierarchy

### Color
- Use accessible color contrast ratios (4.5:1 for normal text)
- Create cohesive color palettes
- Test in both light and dark modes

### Spacing
- Use consistent spacing scales (4px, 8px, 16px, 24px, 32px, 48px)
- Account for fixed navbar height in content padding
- Use max-width containers consistently

### Component Design
- Keep components small and focused
- Use consistent border radius
- Apply subtle shadows for depth
- Maintain visual hierarchy

## Verification

Always verify UI changes by:
1. Taking screenshots to check visual output
2. Verifying responsive behavior
3. Testing both light and dark modes
4. Checking accessibility with keyboard navigation
