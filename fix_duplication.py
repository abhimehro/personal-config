with open("scratch_inventory.py", "r") as f:
    content = f.read()

import re

# Remove the duplicate function definitions
new_content = re.sub(
    r'def _generate_markdown_header\(\):\n.*?(def _generate_markdown_header\(\):)',
    r'\1',
    content,
    flags=re.DOTALL
)

with open("scratch_inventory.py", "w") as f:
    f.write(new_content)
