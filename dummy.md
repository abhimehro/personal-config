It appears that the CI failure was a spurious/flaky issue in `tests/test_controld_manager.sh` specifically related to:
`line 283: echo: write error: Broken pipe`
When ran locally it passes perfectly, and looking at the script it happens because `grep -q` exits immediately on the first match, and the echo command pipe gets broken. This flaky failure is unrelated to the `scratch_inventory.py` and `scratch_triage.py` changes. I will resubmit to kick off the CI checks again.
