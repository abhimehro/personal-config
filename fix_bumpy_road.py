with open(".github/scripts/repository_automation_tasks.py", "r") as f:
    content = f.read()

import re

old_code = """def execute_configured_commands(
    section: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    setup_entries = []
    command_entries = []

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []
        for bucket_name, item in configured_commands(section):
            timeout = int(item.get("timeout_seconds", 1800))
            future = executor.submit(run_shell_command, item["run"], timeout)
            futures.append((bucket_name, item, future))

        for bucket_name, item, future in futures:
            result = future.result()
            entry = {
                "bucket": bucket_name,
                "name": item["name"],
                **result,
                "optional": bool(item.get("optional", False)),
            }
            if bucket_name == "setup":
                setup_entries.append(entry)
            else:
                command_entries.append(entry)

    return setup_entries, command_entries"""

new_code = """def _process_future_result(bucket_name: str, item: dict[str, Any], future: concurrent.futures.Future) -> dict[str, Any]:
    result = future.result()
    return {
        "bucket": bucket_name,
        "name": item["name"],
        **result,
        "optional": bool(item.get("optional", False)),
    }

def execute_configured_commands(
    section: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    setup_entries = []
    command_entries = []

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [
            (
                bucket_name,
                item,
                executor.submit(
                    run_shell_command, item["run"], int(item.get("timeout_seconds", 1800))
                ),
            )
            for bucket_name, item in configured_commands(section)
        ]

    for bucket_name, item, future in futures:
        entry = _process_future_result(bucket_name, item, future)
        if bucket_name == "setup":
            setup_entries.append(entry)
        else:
            command_entries.append(entry)

    return setup_entries, command_entries"""

content = content.replace(old_code, new_code)

with open(".github/scripts/repository_automation_tasks.py", "w") as f:
    f.write(content)
