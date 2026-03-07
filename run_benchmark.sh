#!/bin/bash
kill $(lsof -t -i :8081) 2>/dev/null || true
kill $(lsof -t -i :8082) 2>/dev/null || true
sed -i 's/port = 8081/port = 8082/g' tests/benchmarks/benchmark_infuse_auth.py
python3 tests/benchmarks/benchmark_infuse_auth.py
