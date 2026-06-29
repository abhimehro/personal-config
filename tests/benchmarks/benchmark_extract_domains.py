import json
import os
import tempfile
import timeit


def generate_test_data(num_rules):
    """Generate synthetic JSON data mirroring the expected structure."""
    rules = []
    for i in range(num_rules):
        rule = {}
        # 80% have PK
        if i % 10 < 8:
            rule["PK"] = f"domain{i}.com"
        # 30% have action.do = 1
        if i % 10 < 3:
            rule["action"] = {"do": 1}
        # 20% have action.do = 0
        elif i % 10 < 5:
            rule["action"] = {"do": 0}

        rules.append(rule)

    return {"rules": rules}


# Full end-to-end setups (including JSON parsing)
SETUP_E2E_OLD = """
import json
def extract(filepath):
    domains = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if 'rules' in data:
                for rule in data['rules']:
                    if 'PK' in rule:
                        domains.append(rule['PK'])
    except Exception as e:
        pass
    return domains
"""

SETUP_E2E_NEW = """
import json
def extract(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if 'rules' in data:
                return [rule['PK'] for rule in data['rules'] if 'PK' in rule]
    except Exception as e:
        pass
    return []
"""

SETUP_E2E_ALLOW_OLD = """
import json
def extract(filepath):
    domains = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if 'rules' in data:
                for rule in data['rules']:
                    if 'PK' in rule and rule.get('action', {}).get('do') == 1:
                        domains.append(rule['PK'])
    except Exception as e:
        pass
    return domains
"""

# Using the optimized dictionary access rather than get().get()
SETUP_E2E_ALLOW_NEW = """
import json
def extract(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if 'rules' in data:
                return [
                    rule['PK']
                    for rule in data['rules']
                    if 'PK' in rule and 'action' in rule and rule['action'].get('do') == 1
                ]
    except Exception as e:
        pass
    return []
"""


def run_benchmark(name, setups, temp_filepath, iterations):
    """Run timing loops and print formatted output for a given setup."""
    setup_old, setup_new = setups
    globals_dict = {"temp_filepath": temp_filepath}

    old_time = timeit.timeit(
        "extract(temp_filepath)",
        setup=setup_old,
        globals=globals_dict,
        number=iterations,
    )
    new_time = timeit.timeit(
        "extract(temp_filepath)",
        setup=setup_new,
        globals=globals_dict,
        number=iterations,
    )

    print(f"\n{name} (end-to-end):")
    print(f"Old approach (for loop + append): {old_time:.4f} seconds")
    print(f"New approach (list comprehension): {new_time:.4f} seconds")
    print(f"Speedup: {old_time / new_time:.2f}x faster")
    print(f"Time saved: {old_time - new_time:.4f} seconds")


def main():
    num_rules = 500000
    iterations = 50
    print(f"Generating synthetic JSON data for benchmark ({num_rules} rules)...")
    test_data = generate_test_data(num_rules)

    # Save test data to file to benchmark the full end-to-end execution
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(test_data, f)
        temp_filepath = f.name

    try:
        print(f"\nBenchmarking end-to-end (including file read and JSON parsing)")
        print(f"Dataset size: {num_rules} rules. Iterations: {iterations}")

        run_benchmark(
            "extract_domains",
            (SETUP_E2E_OLD, SETUP_E2E_NEW),
            temp_filepath,
            iterations,
        )

        run_benchmark(
            "extract_allowlist_domains",
            (SETUP_E2E_ALLOW_OLD, SETUP_E2E_ALLOW_NEW),
            temp_filepath,
            iterations,
        )

    finally:
        os.unlink(temp_filepath)


if __name__ == "__main__":
    main()
