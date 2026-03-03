.DEFAULT_GOAL := help

.PHONY: help test test-quick lint lint-errors lint-fix control-d-regression benchmark

help:  ## Show this help message
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

test:  ## Run all shell tests in parallel (ignoring known macOS-specific failures on Linux)
	./tests/run_all_tests.sh

test-quick:  ## Run smoke test subset (fast, cross-platform) for pre-commit verification
	@echo "Running smoke tests..."
	@bash tests/test_lib_common.sh
	@bash tests/test_lib_dns_utils.sh
	@python3 -m unittest tests.test_path_validation -v

control-d-regression:  ## Run full Control D regression test suite
	./scripts/network-mode-regression.sh browsing

benchmark:  ## Run performance benchmarks for core scripts (requires hyperfine)
	./tests/benchmarks/benchmark_scripts.sh all

lint:  ## Run all linters (requires Trunk; runs: trunk check --all)
	trunk check --all

lint-errors:  ## Fail on SC2155/SC2145 correctness violations (run without Trunk; regression gate)
	@echo "Checking for SC2155 (declare+assign) and SC2145 (arg mixing) violations..."
	@bash -c 'set -euo pipefail; \
		output=$$(find . \( -path "./.git" -o -path "./.trunk" -o -path "./configs/.config/mole" -o -path "*/archive" -o -path "./node_modules" \) -prune -o \
			-name "*.sh" -type f -exec shellcheck --include=SC2155,SC2145 --format=gcc {} \; || { \
				echo "❌ shellcheck failed to run correctly (missing, usage error, or parse error)"; \
				exit 1; \
			}); \
		if echo "$$output" | grep -E "SC2155|SC2145"; then \
			echo "❌ SC2155/SC2145 violations found — fix before merging"; \
			exit 1; \
		else \
			echo "✅ No SC2155/SC2145 violations found"; \
		fi'

lint-fix:  ## Auto-fix lint issues (requires Trunk; runs: trunk fmt)
	trunk fmt
