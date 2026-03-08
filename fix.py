import sys

with open('maintenance/bin/node_maintenance.sh', 'r') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if line.strip() == "done":
        lines[i] = "\t\t\t\tdone < <(find \"$search_path\" -name \"node_modules\" -type d -mtime +\"${NODE_MODULES_MAX_AGE_DAYS:-90}\" -print0 2>/dev/null)\n"

with open('maintenance/bin/node_maintenance.sh', 'w') as f:
    f.writelines(lines)
