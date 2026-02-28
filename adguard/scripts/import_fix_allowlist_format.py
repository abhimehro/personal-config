import sys
from pathlib import Path

# Need to import a script with hyphens in the name
import importlib.util

# Get absolute path to fix-allowlist-format.py
current_dir = Path(__file__).resolve().parent
script_path = current_dir / "fix-allowlist-format.py"

# Load the module dynamically
spec = importlib.util.spec_from_file_location("fix_allowlist_format", script_path)
fix_allowlist_format = importlib.util.module_from_spec(spec)
sys.modules["fix_allowlist_format"] = fix_allowlist_format
spec.loader.exec_module(fix_allowlist_format)

extract_allowlist_domains_from_file = fix_allowlist_format.extract_allowlist_domains_from_file
