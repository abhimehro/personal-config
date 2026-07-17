import os
import re

fpath = "scripts/morning-brief/morning-brief.py"
if os.path.exists(fpath):
    with open(fpath, "r") as f:
        content = f.read()

    content = content.replace(
        '    state_type = _state_type.lower().replace("_", "") if _state_type is not None else ""',
        '    state_type = ""\n    if _state_type is not None:\n        state_type = _state_type.lower().replace("_", "")'
    )
    content = content.replace(
        '    state_type = _state_type.lower() if _state_type is not None else ""',
        '    state_type = ""\n    if _state_type is not None:\n        state_type = _state_type.lower()'
    )
    content = content.replace(
        '    category = _category.lower() if _category is not None else ""',
        '    category = ""\n    if _category is not None:\n        category = _category.lower()'
    )

    with open(fpath, "w") as f:
        f.write(content)
