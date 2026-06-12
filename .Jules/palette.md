## 2024-06-12 - Initial Palette Setup
**Learning:** Set up the palette journal.
**Action:** Will start adding critical learnings.

## 2026-03-10 - Screen reader accessible emoji headings
**Learning:** When using emojis in headings as visual icons, they can cause screen readers to read the unicode description of the emoji, breaking the flow of the section title.
**Action:** Added a reusable helper that splits emojis from the text, applies an `aria-label` to the heading tag containing just the text, and wraps the emoji icon in `<span aria-hidden="true">` to hide it from screen readers.
