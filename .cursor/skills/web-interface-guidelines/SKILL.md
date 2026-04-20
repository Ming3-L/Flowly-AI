---
name: web-interface-guidelines
description: Guidelines for web interface design, accessibility, and UI/UX standards. Use when building or refactoring frontend components to ensure consistency and accessibility compliance.
---

# Web Interface Guidelines

Comprehensive guidelines for web interface design, accessibility (WCAG), and UI/UX standards.

## When to Use

- Building or refactoring frontend components
- Ensuring consistency in UI/UX and accessibility
- Reviewing web interface implementations
- Creating accessible forms, navigation, and interactive elements

## Accessibility (WCAG) Guidelines

### Core Principles (POUR)

1. **Perceivable** - Information must be presentable in ways users can perceive
2. **Operable** - UI components must be operable
3. **Understandable** - Information and UI operation must be understandable
4. **Robust** - Content must be robust enough for various assistive technologies

### Color & Contrast

| Requirement | Standard |
|-------------|----------|
| Normal text | 4.5:1 contrast ratio minimum |
| Large text (18pt+) | 3:1 contrast ratio minimum |
| UI components & graphics | 3:1 contrast ratio minimum |

**Tools:** Use browser dev tools, WebAIM Contrast Checker, or axe DevTools

### Keyboard Navigation

- All interactive elements must be focusable via Tab key
- Logical tab order (follow visual order)
- Visible focus indicator on focused elements
- Skip links for main content
- Focus trap in modals/dialogs

### Screen Reader Support

- Semantic HTML elements (`<button>`, `<nav>`, `<main>`, `<article>`)
- ARIA labels when semantic HTML insufficient
- Meaningful alt text for images
- Form labels properly associated with inputs
- Heading hierarchy (h1 → h2 → h3)

## UI/UX Best Practices

### Typography

- Base font size: 16px minimum for body text
- Line height: 1.4-1.6 for body text
- Letter spacing: -0.01em to 0.01em for headings
- Responsive font sizes using rem or em units

### Spacing System

| Token | Value | Use |
|-------|-------|-----|
| xs | 4px | Tight spacing |
| sm | 8px | Component internal |
| md | 16px | Between components |
| lg | 24px | Section spacing |
| xl | 32px+ | Major sections |

### Interactive Elements

**Buttons:**
- Minimum touch target: 44x44px
- Distinct visual states (hover, active, disabled)
- Loading state indicator
- Disabled state: reduced opacity, not cursor: not-allowed

**Forms:**
- Clear labels (visible or associated)
- Error messages linked to inputs via aria-describedby
- Required field indicators
- Focus management on validation errors

### Responsive Design

| Breakpoint | Width | Target |
|------------|-------|--------|
| Mobile | < 576px | Phone |
| Tablet | 576-992px | Tablet |
| Desktop | > 992px | Desktop |

- Mobile-first approach
- Flexible layouts (flexbox, grid)
- Max-width containers
- No horizontal scroll on mobile

## Component Checklist

### Buttons
- [ ] Clear label or icon with aria-label
- [ ] Touch target minimum 44x44px
- [ ] Hover, focus, active states
- [ ] Loading indicator when applicable
- [ ] Disabled state properly styled

### Forms
- [ ] Labels associated with inputs
- [ ] Error messages linked to inputs
- [ ] Required field indicators
- [ ] Focus on first error field
- [ ] Success feedback after submission

### Navigation
- [ ] Skip link for main content
- [ ] Keyboard navigable
- [ ] Current page indicator
- [ ] Dropdown menus accessible
- [ ] Mobile menu with focus trap

### Images
- [ ] Alt text for informative images
- [ ] Empty alt for decorative images
- [ ] Text in images avoided
- [ ] High contrast text on images

### Modals/Dialogs
- [ ] Focus trap inside modal
- [ ] Focus returns to trigger on close
- [ ] Escape key closes modal
- [ ] aria-modal attribute
- [ ] aria-labelledby for title

## Testing Checklist

- [ ] Test with keyboard only
- [ ] Test with screen reader (NVDA, VoiceOver, JAWS)
- [ ] Test color contrast
- [ ] Test at various viewport sizes
- [ ] Test touch interactions on mobile
- [ ] Use automated tools (axe, Lighthouse)

## Resources

- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/)
- [ARIA Authoring Practices](https://www.w3.org/WAI/ARIA/apg/)
- [axe DevTools](https://www.deque.com/axe/devtools/)
