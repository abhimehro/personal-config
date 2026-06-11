# Palette's Notebook

## 2024-06-10 - Dashboard HTML Accessibility
**Learning:** Shell scripts generating HTML dashboard need better ARIA support. Visual health indicators are only conveyed through CSS classes or unicode characters, and metric cards lack screen reader context.
**Action:** Add explicit `aria-label` to dashboard metric cards and ensure ARIA grouping of values/labels. Add `aria-hidden="true"` to inner decorative text.
