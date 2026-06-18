import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(".github/scripts").resolve()))

import repository_automation_tasks


def mock_run_shell_command(command, timeout=1800):
    time.sleep(0.1)
    return {"command": command, "exit_code": 0, "stdout": "ok", "stderr": ""}


repository_automation_tasks.run_shell_command = mock_run_shell_command

section = {
    "setup_commands": [{"name": f"s{i}", "run": f"echo s{i}"} for i in range(5)],
    "commands": [{"name": f"c{i}", "run": f"echo c{i}"} for i in range(5)],
    "security_commands": [{"name": f"sec{i}", "run": f"echo sec{i}"} for i in range(5)],
}

start = time.time()
repository_automation_tasks.execute_configured_commands(section)
duration = time.time() - start
print(f"Optimized execution time: {duration:.4f}s")
