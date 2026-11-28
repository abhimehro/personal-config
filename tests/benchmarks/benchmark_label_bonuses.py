import importlib.util
import sys
import timeit
from pathlib import Path

# Stub optional packages so morning-brief loads in minimal envs
import types
if "feedparser" not in sys.modules:
    fp = types.ModuleType("feedparser")
    fp.parse = lambda *a, **kw: types.SimpleNamespace(entries=[])
    sys.modules["feedparser"] = fp

if "dotenv" not in sys.modules:
    de = types.ModuleType("dotenv")
    de.load_dotenv = lambda *a, **kw: None
    sys.modules["dotenv"] = de

script_path = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "morning-brief"
    / "morning-brief.py"
)
spec = importlib.util.spec_from_file_location("morning_brief", script_path)
mb = importlib.util.module_from_spec(spec)
sys.modules["morning_brief"] = mb
spec.loader.exec_module(mb)

_calculate_label_bonuses = mb._calculate_label_bonuses

# Benchmark datasets representing common label configurations in Linear issues
DATASETS = {
    "empty": [[]] * 1000,
    "single_label": [["bug"], ["feature"], ["p0"], ["backend"]] * 250,
    "typical_linear (2-3 labels)": [["bug", "p0"], ["feature", "ui"], ["hotfix", "critical", "p1"]] * 333,
    "large_labels (10 labels)": [["bug", "feature", "improvement", "p0", "p1", "hotfix", "ui", "backend", "infra", "docs"]] * 1000,
}

def run_benchmark(iterations: int = 100) -> None:
    print(f"Running _calculate_label_bonuses benchmark ({iterations} iterations per dataset)...")
    for name, dataset in DATASETS.items():
        total_time = timeit.timeit(
            lambda: [_calculate_label_bonuses(labels) for labels in dataset],
            number=iterations,
        )
        avg_per_issue = (total_time / (iterations * len(dataset))) * 1e6
        print(f"  {name:30}: total={total_time:.5f}s, per-issue={avg_per_issue:.3f}µs")

if __name__ == "__main__":
    run_benchmark()
