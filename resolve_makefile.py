with open('Makefile', 'r') as f:
    content = f.read()

import re

# We will just accept the origin/main version since they both added .cursor
new_content = re.sub(
    r"<<<<<<< HEAD\n.*?\n=======\n(.*?)\n>>>>>>> origin/main",
    r"\1",
    content,
    flags=re.DOTALL
)

with open('Makefile', 'w') as f:
    f.write(new_content)
