---
name: gitnexus-area-morning-brief
description: "Skill for the Morning-brief area of personal-config. 64 symbols across 3 files."
---

# Morning-brief

64 symbols | 3 files | Cohesion: 77%

## When to Use

- Working with code in `scripts/`
- Understanding how build_focus_meta_parts, build_focus_section,
  build_github_context_note work
- Modifying morning-brief-related functionality

## Key Files

| File                                     | Symbols                                                                                                          |
| ---------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| `scripts/morning-brief/morning-brief.py` | _calculate_base_score, _process_podcast_feed, _render_heading, build_focus_meta_parts, build_focus_section (+56) |
| `lib/safe_http.py`                       | _build_requests_session, build_safe_session                                                                      |
| `tests/test_morning_brief.py`            | test_build                                                                                                       |

## Entry Points

Start here when exploring this area:

- **`build_focus_meta_parts`** (Function) —
  `scripts/morning-brief/morning-brief.py:770`
- **`build_focus_section`** (Function) —
  `scripts/morning-brief/morning-brief.py:1516`
- **`build_github_context_note`** (Function) —
  `scripts/morning-brief/morning-brief.py:818`
- **`build_selection_reason`** (Function) —
  `scripts/morning-brief/morning-brief.py:788`
- **`derive_dynamic_tags`** (Function) —
  `scripts/morning-brief/morning-brief.py:854`

## Key Symbols

| Symbol                              | Type     | File                                     | Line |
| ----------------------------------- | -------- | ---------------------------------------- | ---- |
| `build_focus_meta_parts`            | Function | `scripts/morning-brief/morning-brief.py` | 770  |
| `build_focus_section`               | Function | `scripts/morning-brief/morning-brief.py` | 1516 |
| `build_github_context_note`         | Function | `scripts/morning-brief/morning-brief.py` | 818  |
| `build_selection_reason`            | Function | `scripts/morning-brief/morning-brief.py` | 788  |
| `derive_dynamic_tags`               | Function | `scripts/morning-brief/morning-brief.py` | 854  |
| `fetch_podcast_section`             | Function | `scripts/morning-brief/morning-brief.py` | 1326 |
| `get_time_aware_guidance`           | Function | `scripts/morning-brief/morning-brief.py` | 835  |
| `html_li`                           | Function | `scripts/morning-brief/morning-brief.py` | 613  |
| `html_section`                      | Function | `scripts/morning-brief/morning-brief.py` | 648  |
| `html_subsection`                   | Function | `scripts/morning-brief/morning-brief.py` | 655  |
| `html_ul`                           | Function | `scripts/morning-brief/morning-brief.py` | 617  |
| `is_due_today`                      | Function | `scripts/morning-brief/morning-brief.py` | 667  |
| `render_focus_item`                 | Function | `scripts/morning-brief/morning-brief.py` | 1361 |
| `render_focus_section`              | Function | `scripts/morning-brief/morning-brief.py` | 1433 |
| `render_linear_queue_focus_section` | Function | `scripts/morning-brief/morning-brief.py` | 1394 |
| `render_linear_queue_item`          | Function | `scripts/morning-brief/morning-brief.py` | 1383 |
| `sanitize_text`                     | Function | `scripts/morning-brief/morning-brief.py` | 600  |
| `select_focus_pair`                 | Function | `scripts/morning-brief/morning-brief.py` | 845  |
| `build_safe_session`                | Function | `lib/safe_http.py`                       | 663  |
| `build_greeting_section`            | Function | `scripts/morning-brief/morning-brief.py` | 1500 |

## Execution Flows

| Flow                                               | Type            | Steps |
| -------------------------------------------------- | --------------- | ----- |
| `Process_entry → _method_shortcut`                 | cross_community | 6     |
| `Process_entry → _build_requests_session`          | cross_community | 6     |
| `Build_focus_section → Is_due_today`               | cross_community | 6     |
| `Build_focus_section → _method_shortcut`           | cross_community | 6     |
| `Build_greeting_section → _build_requests_session` | intra_community | 6     |
| `Process_entry → _extract_safety_options`          | cross_community | 6     |
| `Process_entry → _validate_scheme`                 | cross_community | 6     |
| `Process_entry → _validate_url_string`             | cross_community | 6     |
| `Process_entry → _validate_userinfo`               | cross_community | 6     |
| `Build_greeting_section → _method_shortcut`        | cross_community | 6     |

## How to Explore

1. `context({name: "build_focus_meta_parts"})` — see callers and callees
2. `query({search_query: "morning-brief"})` — find related execution flows
3. Read key files listed above for implementation details
4. `explain({target: "<file or symbol>"})` — persisted taint findings
   (source→sink data flows), when indexed with `--pdg`
