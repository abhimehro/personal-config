import ast
import sys

def calculate_complexity(node):
    if isinstance(node, (ast.If, ast.For, ast.While, ast.Try, ast.With, ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef, ast.AsyncFor, ast.AsyncWith)):
        return 1 + sum(calculate_complexity(child) for child in ast.iter_child_nodes(node))
    return sum(calculate_complexity(child) for child in ast.iter_child_nodes(node))

def get_max_nesting(node, current_depth=0):
    if isinstance(node, (ast.If, ast.For, ast.While, ast.Try, ast.With)):
        max_depth = current_depth + 1
        for child in ast.iter_child_nodes(node):
            max_depth = max(max_depth, get_max_nesting(child, current_depth + 1))
        return max_depth
    max_depth = current_depth
    for child in ast.iter_child_nodes(node):
        max_depth = max(max_depth, get_max_nesting(child, current_depth))
    return max_depth

with open(".github/scripts/repository_automation_tasks.py", "r") as f:
    tree = ast.parse(f.read())

for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef) and node.name == "discover_hotspots":
        print(f"Function: {node.name}")
        print(f"Complexity: {calculate_complexity(node)}")
        print(f"Max Nesting: {get_max_nesting(node)}")

        for n in ast.walk(node):
             if isinstance(n, ast.For):
                 print("For Loop Nesting:")
                 print(ast.dump(n))
