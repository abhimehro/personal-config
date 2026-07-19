import re
with open(".cursor/hooks/snyk/snyk_secure_at_inception.py", "r") as f:
    content = f.read()

# Make sure all_vulns is correctly assigned as list since it's passed to _group_vulns_by_file which expects it, although it does `for vuln in vulns:` so tuple is fine. But lets be safe.
# Actually `scan_info.get("vulnerabilities", ())` is fine if we just iterate.
# Wait, are there other mutated tuples?
# `workspace_roots = data.get("workspace_roots", ())`
# `return workspace_roots[0]` -> fine
# `modified_ranges = file_info.get("modified_ranges", ())`
# `any(r["start"] <= v.get("start_line", 0) <= r["end"] for r in modified_ranges)` -> fine
# `existing = _cf.get("modified_ranges", ())`
# `_accumulate_ranges(existing, new_ranges)`
# inside `_accumulate_ranges`: `all_ranges = list(existing) + list(new)` -> fine
# `edits = data.get("edits", ())`
# `new_ranges = compute_modified_ranges(file_content, edits)`
# inside `compute_modified_ranges`: `for edit in edits:` -> fine
# `all_vulns = scan_info.get("vulnerabilities", ()) if scan_info else []`
# `_group_vulns_by_file(all_vulns)` -> `for vuln in vulns:` -> fine
# `manifest_files = state.get("manifest_files", ())`
# `message_parts.extend(f"- {Path(mf).name}" for mf in manifest_files)` -> fine
