## 2025-06-05 - Added ARIA labels to directory listing links
**Learning:** Screen readers reading generated HTML directory structures (like from `infuse-media-server.py`) can encounter redundant emoji announcements (📁, 🎬, 📄) without context of whether the link represents a directory or a specific file type.
**Action:** Always add descriptive `aria-label` attributes to anchor tags in generated HTML listings to clarify the file type and avoid redundant emoji reading. When doing so, ensure `html.escape()` is used correctly to prevent XSS vectors. Ensure unit tests checking these generated strings are updated simultaneously.

## 2025-06-05 - Grouped screen reader announcements for metric cards
**Learning:** When displaying a value and a label together (like "85" and "Health Score"), screen readers will read them as disconnected elements.
**Action:** Apply `aria-label` to the parent container with a cohesive sentence (e.g., "Health Score: 85") and `aria-hidden="true"` to the inner value and label elements. This creates a single, understandable announcement.
