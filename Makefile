.PHONY: help control-d-regression

help:  ## Show this help message
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

control-d-regression:  ## Run full Control D regression test suite
	./scripts/network-mode-regression.sh browsing
