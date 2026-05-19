import time
import os
import sys
from pathlib import Path

# Add the root to sys.path
sys.path.insert(0, os.path.abspath(os.getcwd()))

from adguard.scripts.create_consolidated_lists import main

if __name__ == "__main__":
    # Create a temporary directory for output to avoid polluting adguard/adblocking
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        # Copy source files to tmpdir
        import shutil
        src_dir = Path("adguard/adblocking")
        dst_dir = Path(tmpdir)
        for f in src_dir.glob("CD-*.json"):
            shutil.copy(f, dst_dir)

        os.environ["ADGUARD_LISTS_DIR"] = tmpdir

        start = time.perf_counter()
        main()
        end = time.perf_counter()
        print(f"\nBenchmark Result: {end - start:.4f} seconds")
