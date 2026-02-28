import json
import os
import timeit
import tempfile

def generate_test_data(num_rules):
    """Generate synthetic JSON data mirroring the expected structure."""
    rules = []
    for i in range(num_rules):
        rule = {}
        # 80% have PK
        if i % 10 < 8:
            rule['PK'] = f"domain{i}.com"
        # 30% have action.do = 1
        if i % 10 < 3:
            rule['action'] = {'do': 1}
        # 20% have action.do = 0
        elif i % 10 < 5:
            rule['action'] = {'do': 0}

        rules.append(rule)

    return {'rules': rules}

def main():
    num_rules = 500000
    iterations = 50
    print(f"Generating synthetic JSON data for benchmark ({num_rules} rules)...")
    test_data = generate_test_data(num_rules)

    # Save test data to file to benchmark the full end-to-end execution
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(test_data, f)
        temp_filepath = f.name

    try:
        # Full end-to-end setups (including JSON parsing)
        setup_e2e_old = f"""
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

        setup_e2e_new = f"""
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

        setup_e2e_allow_old = f"""
import json
def extract(filepath):
    domains = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if 'rules' in data:
                for rule in data['rules']:
                    if 'PK' in rule and rule.get('action', {{}}).get('do') == 1:
                        domains.append(rule['PK'])
    except Exception as e:
        pass
    return domains
"""

        # Using the optimized dictionary access rather than get().get()
        setup_e2e_allow_new = f"""
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

        print(f"\nBenchmarking end-to-end (including file read and JSON parsing)")
        print(f"Dataset size: {num_rules} rules. Iterations: {iterations}")

        globals_dict = {'temp_filepath': temp_filepath}

        # Test extract_domains
        old_time = timeit.timeit('extract(temp_filepath)', setup=setup_e2e_old, globals=globals_dict, number=iterations)
        new_time = timeit.timeit('extract(temp_filepath)', setup=setup_e2e_new, globals=globals_dict, number=iterations)

        print("\nextract_domains (end-to-end):")
        print(f"Old approach (for loop + append): {old_time:.4f} seconds")
        print(f"New approach (list comprehension): {new_time:.4f} seconds")
        print(f"Speedup: {old_time / new_time:.2f}x faster")
        print(f"Time saved: {old_time - new_time:.4f} seconds")

        # Test extract_allowlist_domains
        old_allow_time = timeit.timeit('extract(temp_filepath)', setup=setup_e2e_allow_old, globals=globals_dict, number=iterations)
        new_allow_time = timeit.timeit('extract(temp_filepath)', setup=setup_e2e_allow_new, globals=globals_dict, number=iterations)

        print("\nextract_allowlist_domains (end-to-end):")
        print(f"Old approach (for loop + append): {old_allow_time:.4f} seconds")
        print(f"New approach (list comprehension): {new_allow_time:.4f} seconds")
        print(f"Speedup: {old_allow_time / new_allow_time:.2f}x faster")
        print(f"Time saved: {old_allow_time - new_allow_time:.4f} seconds")

    finally:
        os.unlink(temp_filepath)

if __name__ == "__main__":
    main()
