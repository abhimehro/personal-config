
## 2026-12-08 - [Avoid slow manual string slicing with while loops]
**Learning:** Using a manual `while True` loop to parse out multi-line string content by constantly calling `str.find` and managing pointers is extremely inefficient, byte-code intensive, and hard to read.
**Action:** Replace manual string-parsing loops with a single `re.findall` call using a pre-compiled regular expression at the module level for a significant performance and readability boost.
## 2024-05-18 - Replacing file iteration with splitlines() for memory efficiency
**Learning:** The previous plan attempted to optimize file parsing by changing lazy iteration (`for line in handle:`) to loading the entire file into memory and splitting it into a list (`for line in handle.read().splitlines():`). While potentially faster for very small text files by avoiding the overhead of multiple I/O loops, it degraded memory efficiency because it required loading the entire file into memory at once. It also destroyed newline formatting. We learned that the standard `for line in handle:` is generally more memory-efficient and safer to use unless memory overhead is strictly not a concern and raw read speed is critical.
**Action:** When considering file reading performance optimizations, always weigh raw read speed against memory consumption and memory overhead. Prioritize lazy iteration (`for line in handle:`) for unknown file sizes or whenever memory optimization is prioritized over micro-optimizations in speed.

## 2026-03-10 - Optimizing Dictionary Updates with DefaultDict
**Learning:** Using `collections.defaultdict` inside loops (e.g., replacing manual checks like `if key not in dict: dict[key] = []`) significantly reduces overhead from Python's argument evaluation, conditional key checks, and redundant empty object allocations.
**Action:** When inserting into a dictionary of lists/sets inside a tight loop, prioritize `collections.defaultdict`. Make sure to cast back to `dict()` if a standard dictionary is expected by downstream consumers.
