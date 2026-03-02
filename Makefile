.DEFAULT_GOAL := help

.PHONY: help test test-quick lint lint-fix control-d-regression benchmark

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

lint-fix:  ## Auto-fix lint issues (requires Trunk; runs: trunk fmt)
	trunk fmt
