## 2026-03-07 - Hide decorative emojis properly
**Learning:** When hiding decorative emojis within text-containing elements (e.g., `<h3>`), wrap only the emoji in `<span aria-hidden="true">`. Applying a duplicate `aria-label` to the parent text element unnecessarily overrides the native inner text for screen readers.
**Action:** Only wrap the emoji in `<span aria-hidden="true">` and remove redundant `aria-label` from parent if it duplicates the visible text.
