content = open('scripts/morning-brief/morning-brief.py').read()
search = 'LINEAR_GRAPHQL_URL = "https://api.linear.app/graphql"\n'
replace = """LINEAR_GRAPHQL_URL = "https://api.linear.app/graphql"

LINEAR_FOCUS_QUERY = \"\"\"
    query MorningBriefFocus {
      viewer {
        assignedIssues(first: 12, orderBy: updatedAt) {
          nodes {
            identifier
            title
            url
            priority
            dueDate
            updatedAt
            cycle { id }
            labels(first: 5) { nodes { name } }
            state { name type }
          }
        }
      }
    }
\"\"\"
"""
if search in content:
    open('scripts/morning-brief/morning-brief.py', 'w').write(content.replace(search, replace, 1))
    print("Patched 1")
else:
    print("Search string not found")
