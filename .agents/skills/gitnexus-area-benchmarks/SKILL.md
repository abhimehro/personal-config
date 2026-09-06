---
name: gitnexus-area-benchmarks
description: "Skill for the Benchmarks area of personal-config. 14 symbols across 2 files."
---

# Benchmarks

14 symbols | 2 files | Cohesion: 100%

## When to Use

- Working with code in `tests/`
- Understanding how run_benchmark, run_invalid_auth_benchmark,
  run_valid_auth_benchmark work
- Modifying benchmarks-related functionality

## Key Files

| File                                            | Symbols                                                                                         |
| ----------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| `tests/benchmarks/benchmark_infuse_auth.py`     | _execute_requests, _print_benchmark_results, _print_metrics, _run_benchmark, run_benchmark (+5) |
| `tests/benchmarks/benchmark_extract_domains.py` | generate_test_data, main, run_benchmark, setup_benchmark_data                                   |

## Entry Points

Start here when exploring this area:

- **`run_benchmark`** (Function) —
  `tests/benchmarks/benchmark_infuse_auth.py:176`
- **`run_invalid_auth_benchmark`** (Function) —
  `tests/benchmarks/benchmark_infuse_auth.py:95`
- **`run_valid_auth_benchmark`** (Function) —
  `tests/benchmarks/benchmark_infuse_auth.py:87`
- **`wait_for_port`** (Function) —
  `tests/benchmarks/benchmark_infuse_auth.py:12`
- **`generate_test_data`** (Function) —
  `tests/benchmarks/benchmark_extract_domains.py:7`

## Key Symbols

| Symbol                       | Type     | File                                            | Line |
| ---------------------------- | -------- | ----------------------------------------------- | ---- |
| `run_benchmark`              | Function | `tests/benchmarks/benchmark_infuse_auth.py`     | 176  |
| `run_invalid_auth_benchmark` | Function | `tests/benchmarks/benchmark_infuse_auth.py`     | 95   |
| `run_valid_auth_benchmark`   | Function | `tests/benchmarks/benchmark_infuse_auth.py`     | 87   |
| `wait_for_port`              | Function | `tests/benchmarks/benchmark_infuse_auth.py`     | 12   |
| `generate_test_data`         | Function | `tests/benchmarks/benchmark_extract_domains.py` | 7    |
| `main`                       | Function | `tests/benchmarks/benchmark_extract_domains.py` | 69   |
| `run_benchmark`              | Function | `tests/benchmarks/benchmark_extract_domains.py` | 27   |
| `setup_benchmark_data`       | Function | `tests/benchmarks/benchmark_extract_domains.py` | 54   |
| `start`                      | Method   | `tests/benchmarks/benchmark_infuse_auth.py`     | 47   |
| `stop`                       | Method   | `tests/benchmarks/benchmark_infuse_auth.py`     | 83   |
| `_execute_requests`          | Function | `tests/benchmarks/benchmark_infuse_auth.py`     | 103  |
| `_print_benchmark_results`   | Function | `tests/benchmarks/benchmark_infuse_auth.py`     | 116  |
| `_print_metrics`             | Function | `tests/benchmarks/benchmark_infuse_auth.py`     | 141  |
| `_run_benchmark`             | Function | `tests/benchmarks/benchmark_infuse_auth.py`     | 161  |

## Execution Flows

| Flow                                | Type            | Steps |
| ----------------------------------- | --------------- | ----- |
| `Run_benchmark → _print_metrics`    | intra_community | 5     |
| `Run_benchmark → _execute_requests` | intra_community | 4     |
| `Main → Generate_test_data`         | intra_community | 3     |
| `Run_benchmark → Wait_for_port`     | intra_community | 3     |

## How to Explore

1. `context({name: "run_benchmark"})` — see callers and callees
2. `query({search_query: "benchmarks"})` — find related execution flows
3. Read key files listed above for implementation details
4. `explain({target: "<file or symbol>"})` — persisted taint findings
   (source→sink data flows), when indexed with `--pdg`
