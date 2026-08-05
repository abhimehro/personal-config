import urllib.request
import json
import os

token = os.environ.get("GH_TOKEN")
repo = os.environ.get("GITHUB_REPOSITORY", "unknown/repo")
branch = "test-improvement-write-text-files"

print(f"Token: {token[:4] if token else 'None'}... Repo: {repo}")
