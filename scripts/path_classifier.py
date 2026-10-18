"""Path classification logic for guardrail evaluation."""

import re
from typing import Any, Set

_STICKY_EXEMPT = {"generated_output"}
_DEPENDABOT_EXEMPT = {
    "workflows_and_permissions",
    "lockfiles_and_major_dependencies",
}
_PATH_RULES: tuple[tuple[str, str], ...] = (
    (
        "workflows_and_permissions",
        r"(^|/)\.github/(workflows|actions|rulesets|scripts|hooks|agents|commands|copilot|jules|CODEOWNERS|github-app\.ya?ml|repository-automation\.ya?ml|dependabot\.ya?ml|pull_request_template)|(^|/)(\.claude/|\.agents/|\.windsurf/|\.codeium/|\.mcp\.json$|AGENTS\.md$|CLAUDE\.md$|\.cursorrules$|docs/cursor-automations/(prompts|exports)/)",
    ),
    (
        "secrets",
        r"(^|/)(\.env($|\.)|[^/]*\.env$|secrets?/|credentials?[^/]*|[^/]*\.(pem|key|p12|pfx|keystore)$|id_(rsa|ed25519|ecdsa|dsa)|\.ssh/|[^/]*netrc)",
    ),
    (
        "authentication_and_authorization",
        r"[^/]*(authentication|authorization|oauth|rbac|permission|sso|login)[^/]*\.(py|sh|js|ts|ya?ml|json|toml|rb|go|fish)$",
    ),
    (
        "deployment_and_infrastructure",
        r"(^|/)(Dockerfile[^/]*|docker-compose[^/]*|\.devcontainer/|deploy[^/]*/|infrastructure/|terraform[^/]*|[^/]*\.tf$|fly\.toml|vercel\.json|launchd[^/]*|launch-agents/|[^/]*\.plist$|systemd[^/]*|[^/]*\.service$)",
    ),
    (
        "lockfiles_and_major_dependencies",
        r"(^|/)(package-lock\.json|yarn\.lock|pnpm-lock\.ya?ml|uv\.lock|poetry\.lock|Pipfile\.lock|Gemfile\.lock|go\.(mod|sum)|Cargo\.(toml|lock)|composer\.(json|lock)|requirements[^/]*\.txt|requirements/|pyproject\.toml|setup\.(py|cfg)|package\.json|Brewfile[^/]*|[^/]*\.gemspec|renv\.lock)",
    ),
    (
        "security_configuration",
        r"(^|/)(\.trunk/|\.github/gitleaks\.toml|[^/]*gitleaks[^/]*|[^/]*codeql[^/]*|[^/]*semgrep[^/]*|[^/]*trufflehog[^/]*|[^/]*trivy[^/]*|[^/]*snyk[^/]*|\.codacy\.ya?ml|[^/]*sonar[^/]*\.(ya?ml|properties)|[^/]*zizmor[^/]*|SECURITY\.md|\.github/SECURITY[^/]*|security\.py$)",
    ),
    (
        "database_migrations",
        r"(^|/)(migrations?/|alembic[^/]*|[^/]*\.sql$|schema\.prisma|prisma/migrations)",
    ),
    (
        "network_and_browser_origins",
        r"[^/]*(dns|network|cors|proxy|origin)[^/]*\.(ya?ml|toml|json|conf|cfg|sh|py|js|ts|fish)$|(^|/)(hosts|resolv\.conf|pf\.conf|ctrld[^/]*\.toml|nginx[^/]*|[^/]*\.zone$",
    ),
    (
        "shell_execution",
        r"[^/]*\.(sh|bash|zsh|fish|command|bat|ps1)$|(^|/)(Makefile|[^/]*\.mk$|bin/)",
    ),
    (
        "file_read_write_boundaries",
        r"(^|/)(\.gitignore|\.gitattributes|\.cursorignore|[^/]*ignore$|\.cursor/|\.devin/|\.idea/|\.vscode/)",
    ),
    (
        "generated_output",
        r"(^|/)(\.jules/|jules/|generated/|dist/|build/|coverage/|\.snapshot[^/]*|[^/]*\.generated\.[^/]*$)",
    ),
    (
        "public_api_contracts",
        r"(^|/)(openapi[^/]*|swagger[^/]*|schemas?/|apis?/|api[^/]*\.(json|ya?ml)|[^/]*\.proto$|[^/]*\.graphql|[^/]*\.schema\.json)",
    ),
    (
        "destructive_data_actions",
        r"[^/]*(delete|purge|wipe|destroy|truncate|drop|erase)[^/]*\.(sh|py|sql|js|ts|rb|fish)$",
    ),
)
_COMPILED_RULES: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (name, re.compile(pattern, re.IGNORECASE)) for name, pattern in _PATH_RULES
)
_JULES_JOURNAL_RE = re.compile(r"(^|/)\.jules/.+\.md$", re.IGNORECASE)
_TEST_PATH_RE = re.compile(
    r"(^|/)(tests?|specs?)/|(^|/)test_[^/]+$|[^/]+_test\.[^/]+$|Tests\.swift$",
    re.IGNORECASE,
)


def is_jules_journal(path: str) -> bool:
    """Return whether `path` is a `.jules` markdown journal."""
    return _JULES_JOURNAL_RE.search(path) is not None


def _is_test_path(path: str) -> bool:
    """Return whether `path` is a test file whose fixtures should not trigger diff holds."""
    return _TEST_PATH_RE.search(path) is not None


def classify_path(path: Any) -> Set[str]:
    """Return the taxonomy classes a changed path matches (empty when clean)."""
    if not isinstance(path, str) or not path.strip():
        return set()
    text = path.strip()
    if is_jules_journal(text):
        return set()
    return {name for name, pattern in _COMPILED_RULES if pattern.search(text)}


def classify_item_paths(changed_paths: Any) -> Set[str]:
    """Union the taxonomy classes across one item's changed paths."""
    if not isinstance(changed_paths, list):
        return set()
    classes: Set[str] = set()
    for path in changed_paths:
        classes.update(classify_path(path))
    return classes


def calculate_path_sticky(
    item: dict[str, Any], evidence: Any, dependabot_routine_eligible: Any
) -> Set[str]:
    """Return sticky paths after applying Dependabot exemptions."""
    classes = classify_item_paths(item["changed_paths"])
    path_sticky = classes - _STICKY_EXEMPT
    if dependabot_routine_eligible(item, evidence):
        path_sticky -= _DEPENDABOT_EXEMPT
    return path_sticky