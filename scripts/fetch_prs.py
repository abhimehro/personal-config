#!/usr/bin/env python3
"""Refresh tasks/pr-inventory.md from GitHub (gh CLI). Run from any cwd; resolves repo root from this file."""

from __future__ import annotations

import json
import subprocess  # nosec B404
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = REPO_ROOT / "tasks" / "pr-inventory.md"

repos = [
    "abhimehro/personal-config",
    "abhimehro/ctrld-sync",
    "abhimehro/email-security-pipeline",
    "abhimehro/Seatek_Analysis",
    "abhimehro/Hydrograph_Versus_Seatek_Sensors_Project",
    "abhimehro/series_correction_project_updated",
]

bot_authors = [
    "dependabot[bot]",
    "renovate[bot]",
    "google-labs-jules[bot]",
    "cursor[bot]",
    "devin[bot]",
    "copilot[bot]",
    "app/copilot-swe-agent",
    "dependabot",
    "renovate",
    "google-labs-jules",
    "cursor",
    "devin",
    "copilot",
]


def check_automation_signals(pr: dict) -> str:
    author = pr.get("author", {}).get("login", "")
    if author in bot_authors:
        return f"Bot author ({author})"

    title = pr.get("title", "").lower()
    head = pr.get("headRefName", "").lower()
    body = pr.get("body", "").lower()

    signals = ["jules", "sentinel", "bolt", "palette", "qa", "automation-workflow"]

    for s in signals:
        if s in head:
            return f"Signal in branch ({s})"
        if s in title:
            return f"Signal in title ({s})"
        if s in body:
            return f"Signal in body ({s})"

    return "Human author (no obvious signal)"


def main() -> None:
    now = datetime.now(timezone.utc)

    out_md = "# PR Inventory\n\n"

    for i, repo in enumerate(repos):
        print(f"Fetching PRs for {repo}...")
        try:
            cmd = [
                "gh",
                "pr",
                "list",
                "--repo",
                repo,
                "--state",
                "open",
                "--json",
                "number,url,title,author,headRefName,baseRefName,createdAt,updatedAt,labels,isDraft,mergeable,statusCheckRollup,body",
                "--limit",
                "500",
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )  # nosec B603
            if result.returncode != 0:
                print(f"Warning: gh returned {result.returncode} for {repo}")
                print(f"Stderr: {result.stderr}")

            prs = json.loads(result.stdout or "[]")

            out_md += f"## {repo}\n\n"

            if not prs:
                out_md += "No open PRs found.\n\n"
                if i < len(repos) - 1:
                    time.sleep(2)
                continue

            out_md += (
                "| PR # | URL | Title | Author | Head/Base | Created/Updated | Stale? | "
                "Labels | Draft | Mergeable | Checks | Inclusion Reason |\n"
            )
            out_md += "|---|---|---|---|---|---|---|---|---|---|---|---|\n"

            for pr in prs:
                num = pr.get("number", "")
                url = pr.get("url", "")
                title = pr.get("title", "").replace("|", "\\|").replace("\n", " ")
                author = pr.get("author", {}).get("login", "Unknown")
                head = pr.get("headRefName", "")
                base = pr.get("baseRefName", "")
                created = pr.get("createdAt", "")
                updated = pr.get("updatedAt", "")

                stale = "No"
                if updated:
                    try:
                        updated_dt = datetime.strptime(
                            updated, "%Y-%m-%dT%H:%M:%SZ"
                        ).replace(tzinfo=timezone.utc)
                        days_ago = (now - updated_dt).days
                        if days_ago > 30:
                            stale = "Yes (>30d)"
                    except ValueError:
                        pass

                labels = ", ".join(
                    [lbl.get("name", "") for lbl in pr.get("labels", [])]
                )
                draft = "Yes" if pr.get("isDraft") else "No"
                mergeable = pr.get("mergeable", "")

                checks = "Unknown"
                rollup = pr.get("statusCheckRollup", [])
                if isinstance(rollup, list) and rollup:
                    checks = f"{len(rollup)} checks"

                reason = check_automation_signals(pr)

                out_md += (
                    f"| {num} | [Link]({url}) | {title} | {author} | {head} -> {base} | "
                    f"{created[:10]} / {updated[:10]} | {stale} | {labels} | {draft} | "
                    f"{mergeable} | {checks} | {reason} |\n"
                )

            out_md += "\n"

        except (json.JSONDecodeError, OSError, KeyError) as e:
            print(f"Error fetching {repo}: {e}")
            out_md += f"## {repo}\n\n*Error fetching: {e}*\n*MCP fallback needed?*\n\n"

        if i < len(repos) - 1:
            time.sleep(2)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(out_md, encoding="utf-8")

    print(f"Done. Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
