## 2025-02-12 - HTML Template Accessibility
**Learning:** Simple HTML strings in Python scripts often miss crucial accessibility foundations like `lang`, `viewport` meta tags, focus outlines, and sufficient color contrast, hurting mobile users and keyboard navigators.
**Action:** When working with Python's `http.server` or generating ad-hoc HTML, always add responsive viewport tags, `:focus-visible` styles, and ensure text contrast passes WCAG AA.

## $(date +%Y-%m-%d) - HTML Template Accessibility (Bash scripts)
**Learning:** Shell scripts generating standalone HTML reports (like `performance_optimizer.sh`) often miss core accessibility attributes and use default color names (`green`, `orange`, `red`) that fail WCAG AA contrast ratios, particularly for alert states on white backgrounds.
**Action:** When generating HTML in bash, explicitly define `<html lang="en">`, include `<meta charset="UTF-8">` and a `viewport` tag, and replace default color names with WCAG AA compliant hex codes (e.g., `#057A55` for green, `#B45309` for orange/warning, `#DC2626` for red/critical).
