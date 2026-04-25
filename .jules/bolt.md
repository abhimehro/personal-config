## 2026-06-25 - [macOS BSD Find Limitations]

**Learning:** macOS uses BSD `find`, which does not support the GNU-specific `-quit` flag. Using `-quit` on macOS causes silent script failures if `stderr` is redirected, which can break conditional logic (e.g. `grep -q .` succeeding falsely or failing falsely).
**Action:** Do not use the `-quit` flag in `find` commands within macOS-specific scripts. If early exit behavior is needed on the first match, use `find ... | head -n 1` or `grep -q .`.

## 2024-05-18 - Fast String Searching for PR Exclusions

## 2026-06-28 - [Dictionary Key Checking Optimization]

**Learning:** In Python data parsing scripts, using direct dictionary lookups (`'key' in var and var['key'] == val`) avoids `.get()` function call overhead and is measurably faster (~15-20%). However, rewriting memory-efficient generator expressions into memory-heavy list comprehensions before passing them into aggregate functions like `.update()` can cause massive memory regressions, particularly inside scripts processing bulk lists.
**Action:** When filtering dictionaries based on key values inside loops, prefer explicit `in` checks over `.get()` for optimal performance. When passing large iterated structures into set functions, maintain the use of generator expressions to preserve memory.
