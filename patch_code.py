import re

with open('scratch_triage.py', 'r') as f:
    text = f.read()

search = '''def _fetch_all_prs_graphql(repo_list):
    all_prs = []
    # Process in batches of 50 to avoid GraphQL complexity limits
    batch_size = 50
    for i in range(0, len(repo_list), batch_size):
        batch = repo_list[i:i+batch_size]
        query_parts = []
        for j, repo in enumerate(batch):
            owner, name = repo.split("/")
            query_parts.append(f"""
            repo_{j}: repository(owner: "{owner}", name: "{name}") {{
                pullRequests(states: OPEN, first: 100) {{
                    nodes {{
                        number
                        title
                        author {{
                            login
                        }}
                        headRefName
                        mergeStateStatus
                        state
                        createdAt
                    }}
                }}
            }}
            """)
        query = "query {" + "".join(query_parts) + "}"
        success, stdout, _ = run_cmd(["gh", "api", "graphql", "-f", f"query={query}"])
        if success:
            data = json.loads(stdout)
            gh_data = data.get("data", {})
            for j, repo in enumerate(batch):
                repo_data = gh_data.get(f"repo_{j}")
                if not repo_data:
                    continue
                nodes = repo_data.get("pullRequests", {}).get("nodes", [])
                for pr in nodes:
                    if pr.get("author"):
                        pr["author"] = {"login": pr["author"]["login"]}
                    # ⚡ Bolt Optimization: Use rpartition() over split() to avoid intermediate list allocation overhead
                    pr["repo"] = repo.rpartition("/")[2]
                    pr["full_repo"] = repo
                    # ⚡ Bolt Optimization: Hoist title lowering out of filtering loops to prevent redundant C-level string allocations
                    pr["title_lower"] = pr["title"].lower()
                    all_prs.append(pr)
    return all_prs'''

replace = '''def _build_graphql_query(batch):
    query_parts = []
    for j, repo in enumerate(batch):
        owner, name = repo.split("/")
        query_parts.append(f"""
        repo_{j}: repository(owner: "{owner}", name: "{name}") {{
            pullRequests(states: OPEN, first: 100) {{
                nodes {{
                    number
                    title
                    author {{ login }}
                    headRefName
                    mergeStateStatus
                    state
                    createdAt
                }}
            }}
        }}
        """)
    return "query {" + "".join(query_parts) + "}"

def _parse_graphql_response(stdout, batch):
    parsed_prs = []
    data = json.loads(stdout)
    gh_data = data.get("data", {})
    for j, repo in enumerate(batch):
        repo_data = gh_data.get(f"repo_{j}")
        if not repo_data:
            continue
        nodes = repo_data.get("pullRequests", {}).get("nodes", [])
        for pr in nodes:
            if pr.get("author"):
                pr["author"] = {"login": pr["author"]["login"]}
            pr["repo"] = repo.rpartition("/")[2]
            pr["full_repo"] = repo
            pr["title_lower"] = pr["title"].lower()
            parsed_prs.append(pr)
    return parsed_prs

def _fetch_all_prs_graphql(repo_list):
    all_prs = []
    batch_size = 50
    for i in range(0, len(repo_list), batch_size):
        batch = repo_list[i:i+batch_size]
        query = _build_graphql_query(batch)
        success, stdout, _ = run_cmd(["gh", "api", "graphql", "-f", f"query={query}"])
        if success:
            all_prs.extend(_parse_graphql_response(stdout, batch))
    return all_prs'''

if search not in text:
    print('Search failed!')
else:
    text = text.replace(search, replace)
    with open('scratch_triage.py', 'w') as f:
        f.write(text)
    print('Replaced')
