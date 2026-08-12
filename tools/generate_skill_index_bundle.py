#!/usr/bin/env python3
"""Generate a non-executable JSON bundle for the Skill Index static directory."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "skill-index" / "directory-data.json"
SOURCE_ROOTS = (
    (".agents/skills", "Agents"),
    (".claude/skills", "Claude"),
    (".cursor/skills", "Cursor"),
    (".devin/skills", "Devin"),
    (".windsurf/skills", "Windsurf"),
)
TEXT_EXTENSIONS = {".md", ".txt", ".json", ".yaml", ".yml"}
MAX_REFERENCE_CHARS = 60000


def title_from_path(path: Path) -> str:
    words = path.parent.name.replace("-", " ").split()
    acronyms = {"ai", "api", "cli", "dart", "go", "js", "mcp", "pr", "rp", "sdk", "vpn"}
    return " ".join(word.upper() if word in acronyms else word.capitalize() for word in words)


def categorise(value: str) -> tuple[str, list[str]]:
    value = value.lower()
    if "firebase" in value:
        return "Firebase", ["firebase", "app-development"]
    if "genkit" in value:
        return "Genkit", ["ai-development", "genkit"]
    if "rp-" in value:
        return "RepoPrompt", ["repository-context", "agent-workflow"]
    if "gh-stack" in value:
        return "Git Workflows", ["github", "pull-requests"]
    if "hf-cli" in value:
        return "ML & Hugging Face", ["hugging-face", "machine-learning"]
    if "sonar" in value or "pplx" in value:
        return "Research APIs", ["perplexity", "research"]
    if "spotify" in value:
        return "Media Production", ["audio", "spotify"]
    if "windscribe" in value:
        return "System & Privacy", ["vpn", "networking"]
    if "xcode" in value:
        return "Apple Development", ["ios", "xcode"]
    if "context7" in value or "find-docs" in value:
        return "Documentation", ["developer-docs", "research"]
    if "review" in value:
        return "Code Quality", ["pull-requests", "review"]
    return "Agent Workflows", ["agentic-workflow", "personal-config"]


def extract_skill(path: Path) -> tuple[dict[str, Any], str]:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n?", text, re.DOTALL)
    if not match:
        raise ValueError(f"Missing YAML frontmatter: {path}")
    frontmatter = yaml.safe_load(match.group(1))
    if not isinstance(frontmatter, dict):
        raise ValueError(f"Invalid frontmatter: {path}")
    return frontmatter, text[match.end() :].strip()


def resource_kind(relative: Path) -> str:
    if relative.parts and relative.parts[0] == "references":
        return "Reference"
    if relative.parts and relative.parts[0] == "scripts":
        return "Script"
    if relative.parts and relative.parts[0] == "templates":
        return "Template"
    return "Resource"


def resource_record(path: Path, package_dir: Path) -> dict[str, Any]:
    relative = path.relative_to(package_dir)
    is_text = path.suffix.lower() in TEXT_EXTENSIONS
    content = ""
    truncated = False
    if is_text:
        content = path.read_text(encoding="utf-8", errors="replace")
        if len(content) > MAX_REFERENCE_CHARS:
            content, truncated = content[:MAX_REFERENCE_CHARS], True
    return {
        "path": relative.as_posix(),
        "name": path.name,
        "kind": resource_kind(relative),
        "isText": is_text,
        "content": content,
        "truncated": truncated,
        "bytes": path.stat().st_size,
    }


def source_revision(format_string: str) -> str:
    paths = [root for root, _ in SOURCE_ROOTS]
    return subprocess.run(
        ["git", "log", "-1", f"--format={format_string}", "--", *paths],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def source_commit() -> str:
    return source_revision("%h")


def source_timestamp() -> str:
    return source_revision("%cI")


def skill_updated_at(package_dir: Path) -> str:
    return subprocess.run(
        ["git", "log", "-1", "--format=%cI", "--", package_dir.relative_to(ROOT).as_posix()],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def stable_digest(skill_file: Path, resources: list[dict[str, Any]]) -> str:
    digest = hashlib.sha256(skill_file.read_bytes())
    for resource in resources:
        digest.update(resource["path"].encode("utf-8"))
        digest.update(str(resource["bytes"]).encode("utf-8"))
    return digest.hexdigest()[:16]


def build_bundle() -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    seen_skill_bodies: set[str] = set()
    for root_string, source in SOURCE_ROOTS:
        skills_dir = ROOT / root_string
        if not skills_dir.exists():
            continue
        for skill_file in sorted(skills_dir.glob("*/SKILL.md")):
            body_hash = hashlib.sha256(skill_file.read_bytes()).hexdigest()
            if body_hash in seen_skill_bodies:
                continue
            seen_skill_bodies.add(body_hash)
            package_dir = skill_file.parent
            frontmatter, instructions = extract_skill(skill_file)
            category, tags = categorise(package_dir.name)
            resources = [resource_record(path, package_dir) for path in sorted(package_dir.rglob("*")) if path.is_file() and path.name != "SKILL.md"]
            records.append({
                "id": f"personal-config-{source.lower()}-{package_dir.name}",
                "name": title_from_path(skill_file),
                "packageName": f"personal-config-{source.lower()}-{package_dir.name}",
                "description": str(frontmatter.get("description", "")),
                "source": source,
                "sourcePath": skill_file.relative_to(ROOT).as_posix(),
                "category": category,
                "tags": tags,
                "resources": len(resources) + 1,
                "frontmatter": frontmatter,
                "instructions": instructions,
                "resourceInventory": resources,
                "digest": stable_digest(skill_file, resources),
                "updatedAt": skill_updated_at(package_dir),
            })
    rank = {"Agents": 0, "Claude": 1, "Cursor": 2, "Devin": 3, "Windsurf": 4}
    records.sort(key=lambda record: (rank[record["source"]], record["category"], record["name"]))
    return {
        "schemaVersion": "1.0",
        "sourceRepository": "https://github.com/abhimehro/personal-config",
        "sourceCommit": source_commit(),
        "generatedAt": source_timestamp(),
        "packageCount": len(records),
        "skills": records,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Fail if the committed bundle differs from a fresh build.")
    args = parser.parse_args()
    payload = json.dumps(build_bundle(), ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != payload:
            raise SystemExit("Skill Index bundle is stale. Run tools/generate_skill_index_bundle.py.")
        print("Skill Index bundle is current.")
        return
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(payload, encoding="utf-8")
    print(f"Wrote {json.loads(payload)['packageCount']} skill records to {OUTPUT}")


if __name__ == "__main__":
    main()
