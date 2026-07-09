# Archived SecOps stubs

| File | Why archived |
| ---- | ------------ |
| `phase{1,2,3}-*.broken-python-stub` | Jul 2026 refactor replaced working shell logic with `uv run …/secops-autopilot/scripts/secops_agent.py`, but that skill was never added to `.agents/skills/`. LaunchAgents failed with exit 2 / `LastExitStatus=512`. Restored shell implementations from commit `6adacc8e`. |

Do not re-enable the Python stubs until `secops_agent.py` exists and is verified under launchd PATH.
