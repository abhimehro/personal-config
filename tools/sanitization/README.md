# Repo Sanitization

1. Copy `sensitive-paths.txt.sample` to `sensitive-paths.txt` and edit as needed.
2. Run `git-filter-repo` using that list to purge history.

Example `sensitive-paths.txt`:
```
configs/.gemini/
Python_System_Performance_Monitor.ipynb
```

Run:
```
pipx install git-filter-repo || python3 -m pip install --user git-filter-repo
python3 -m git_filter_repo --invert-paths --paths-from-file tools/sanitization/sensitive-paths.txt
```