## 2024-06-14 - Accessible Emojis in Text Headers
**Learning:** When text-containing elements like headers include decorative emojis, screen readers will audibly announce the emoji name, which disrupts reading flow. Wrapping only the emoji in `<span aria-hidden="true">` prevents this.
**Action:** Avoid duplicate `aria-label` on the parent text element; wrap just the emoji in `<span aria-hidden="true">` so the native inner text continues to be read naturally.
