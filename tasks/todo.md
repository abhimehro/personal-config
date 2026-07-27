# Session plan — ABHI-1517: Pin GitHub Actions & Tighten Permissions

- [x] Audit all 17 active workflow files for unpinned actions, over-broad `permissions`, `pull_request_target`, PAT/App-token exposure, implicit `github.token`, and attacker-controlled interpolation
- [x] Independently re-resolve every floating tag to a verified 40-character commit SHA
- [x] Pin all remote `uses:` references to full SHAs and clean mismatched/duplicate version comments
- [x] Apply least-privilege, job-level `permissions` and top-level defaults where needed
- [x] Audit `persist-credentials` on checkout steps; set `false` unless the job pushes
- [x] Add fail-closed `.github/scripts/validate_workflow_pins.py` gate and wire it into CI
- [x] Validate with YAML parsing, `actionlint`, `pinact --no-fix`, `make test-quick`/`make test`/`make test-python`, and targeted `trunk check`
- [x] Resolve CI / CodeScene code-health failures on `validate_workflow_pins.py`
- [x] Open PR with ELIR handoff and post-merge repository default `GITHUB_TOKEN` guidance
- [x] Update Linear ABHI-1517 with implementation summary and status
