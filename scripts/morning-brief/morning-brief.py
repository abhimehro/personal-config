#!/Users/speedybee/dev/personal-config/scripts/morning-brief/venv/bin/python3.15
"""
Morning Brief Generator for Raycast.

Builds a daily HTML briefing from weather, horoscope, Linear tasks,
Google Calendar events, Louisiana RSS feeds, and podcast episodes,
then saves it to Readwise Reader.

Usage:
    python3.15 morning-brief.py              # Normal run → saves to Readwise
    python3.15 morning-brief.py --dry-run    # Writes HTML to stdout / temp file

Required env vars:
    READWISE_TOKEN

Optional env vars:
    PERPLEXITY_API_KEY
    LINEAR_API_KEY  or  LINEAR_TOKEN
    GOOGLE_CALENDAR_API_KEY
    GOOGLE_CALENDAR_EMAIL
    GOOGLE_CALENDAR_TIMEZONE          (default: America/Chicago)
    MORNING_BRIEF_TZ_OFFSET           (default: -05:00)
    MORNING_BRIEF_FOCUS_MAX_ITEMS     (default: 3)
    MORNING_BRIEF_LOG_LEVEL           (default: INFO)

Section toggles (set to "0" or "false" to disable):
    MORNING_BRIEF_ENABLE_GREETING     (default: 1)
    MORNING_BRIEF_ENABLE_FOCUS        (default: 1)
    MORNING_BRIEF_ENABLE_NEWS         (default: 1)
    MORNING_BRIEF_ENABLE_PODCAST      (default: 1)

Cache control:
    MORNING_BRIEF_CACHE_DIR           (default: ~/.cache/morning-brief)
    MORNING_BRIEF_WEATHER_CACHE_TTL   (default: 1800, seconds)
    MORNING_BRIEF_FEED_CACHE_TTL      (default: 900, seconds)
"""

# Required parameters:
# @raycast.schemaVersion 1
# @raycast.title Generate Morning Brief
# @raycast.mode compact
# @raycast.needsConfirmation false

# Optional parameters:
# @raycast.icon ☕
# @raycast.packageName Daily Optimization

from __future__ import annotations

import concurrent.futures
import datetime as dt
import hashlib
import html
import json
import logging
import os
import sys
import tempfile
import time
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable

import feedparser
import requests
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ============================================================
# Constants
# ============================================================

APP_NAME = "morning-brief"
APP_VERSION = "3.0"

READWISE_SAVE_URL = "https://readwise.io/api/v3/save"
PERPLEXITY_CHAT_URL = "https://api.perplexity.ai/chat/completions"
LINEAR_GRAPHQL_URL = "https://api.linear.app/graphql"
AMERICA_ADAPTS_RSS_URL = "https://americaadapts.libsyn.com/rss"

DEFAULT_TIMEOUT = 10
HOROSCOPE_TIMEOUT = 8
LLM_MAX_TOKENS_SUMMARY = 100
LLM_MAX_TOKENS_GREETING = 150
MAX_LLM_INPUT_CHARS = 3000
SUMMARY_TRUNCATE_LEN = 150
DEFAULT_FOCUS_MAX_ITEMS = 3

DEFAULT_LAT = 30.4515
DEFAULT_LON = -91.1871
DEFAULT_ZODIAC_SIGN = "cancer"

DEFAULT_WEATHER_CACHE_TTL = 1800
DEFAULT_FEED_CACHE_TTL = 900

FEEDS: dict[str, str] = {
    "🔍 The Lens": "https://thelensnola.org/feed/",
    "🏛️ LA Illuminator": "https://lailluminator.com/feed/",
    "🎙️ WRKF (NPR)": "https://www.wrkf.org/news.rss",
    "⚖️ Verite News": "https://veritenews.org/feed/",
    "🌊 The Current": "https://thecurrentla.com/feed/",
}

TARGET_PODCAST_KEYWORDS = (
    "coastal",
    "freshwater",
    "sponge",
    "river",
    "drone",
    "biodiversity",
    "ecology",
    "wetland",
    "sea level",
    "marsh",
)

# Linear state-type weights (higher = more urgent to work on today)
LINEAR_STATE_WEIGHTS: dict[str, int] = {
    "started": 40,
    "inprogress": 40,
    "unstarted": 10,
    "backlog": 0,
    "triage": 5,
}

# Linear label bonuses
LINEAR_LABEL_BONUSES: dict[str, int] = {
    "bug": 25,
    "hotfix": 30,
    "feature": 10,
    "improvement": 5,
    "p0": 40,
    "p1": 20,
}

HOROSCOPE_ENDPOINTS_TEMPLATE = [
    {
        "name": "horoscope-app-api.vercel.app",
        "url": "https://horoscope-app-api.vercel.app/api/v1/get-horoscope/daily",
        "params_fn": lambda sign: {"sign": sign, "day": "today"},
    },
    {
        "name": "ohmanda.com",
        "url_fn": lambda sign: f"https://ohmanda.com/api/horoscope/{sign}",
        "params_fn": lambda _sign: {},
    },
]


# ============================================================
# Logging
# ============================================================


def configure_logging() -> logging.Logger:
    """Configure application logger → stderr."""
    level_name = os.getenv("MORNING_BRIEF_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(levelname)s [%(name)s] %(message)s",
        stream=sys.stderr,
    )
    return logging.getLogger(APP_NAME)


logger = configure_logging()


# ============================================================
# Data Models
# ============================================================


@dataclass(frozen=True)
class SectionToggles:
    """Which briefing sections are enabled."""

    greeting: bool = True
    focus: bool = True
    news: bool = True
    podcast: bool = True

    @property
    def any_enabled(self) -> bool:
        return self.greeting or self.focus or self.news or self.podcast


@dataclass(frozen=True)
class AppConfig:
    """Immutable runtime configuration loaded from environment."""

    readwise_token: str
    perplexity_api_key: str = ""
    linear_api_key: str = ""
    google_calendar_api_key: str = ""
    google_calendar_email: str = ""
    google_calendar_timezone: str = "America/Chicago"
    timezone_offset: str = "-05:00"
    focus_max_items: int = DEFAULT_FOCUS_MAX_ITEMS
    lat: float = DEFAULT_LAT
    lon: float = DEFAULT_LON
    zodiac_sign: str = DEFAULT_ZODIAC_SIGN
    env_source: str = ""
    feeds: dict[str, str] = field(default_factory=lambda: dict(FEEDS))
    toggles: SectionToggles = field(default_factory=SectionToggles)
    cache_dir: str = ""
    weather_cache_ttl: int = DEFAULT_WEATHER_CACHE_TTL
    feed_cache_ttl: int = DEFAULT_FEED_CACHE_TTL
    dry_run: bool = False

    @classmethod
    def load(cls, argv: list[str] | None = None) -> "AppConfig":
        """Build config from env files, env vars, and CLI flags."""
        preferred = Path.home() / ".config" / "morning-brief.env"
        fallback = Path(__file__).with_name(".env")
        env_source = preferred if preferred.exists() else fallback
        load_dotenv(env_source)

        readwise_token = os.getenv("READWISE_TOKEN", "").strip()
        dry_run = "--dry-run" in (argv or sys.argv[1:])

        if not readwise_token and not dry_run:
            print("Error: READWISE_TOKEN is not set.", file=sys.stderr)
            sys.exit(1)

        config = cls(
            readwise_token=readwise_token,
            perplexity_api_key=os.getenv("PERPLEXITY_API_KEY", "").strip(),
            linear_api_key=(
                os.getenv("LINEAR_API_KEY", "").strip()
                or os.getenv("LINEAR_TOKEN", "").strip()
            ),
            google_calendar_api_key=os.getenv("GOOGLE_CALENDAR_API_KEY", "").strip(),
            google_calendar_email=os.getenv("GOOGLE_CALENDAR_EMAIL", "").strip(),
            google_calendar_timezone=os.getenv(
                "GOOGLE_CALENDAR_TIMEZONE", "America/Chicago"
            ).strip(),
            timezone_offset=os.getenv("MORNING_BRIEF_TZ_OFFSET", "-05:00").strip(),
            focus_max_items=_safe_int(
                "MORNING_BRIEF_FOCUS_MAX_ITEMS", DEFAULT_FOCUS_MAX_ITEMS
            ),
            env_source=str(env_source),
            toggles=SectionToggles(
                greeting=_env_bool("MORNING_BRIEF_ENABLE_GREETING", True),
                focus=_env_bool("MORNING_BRIEF_ENABLE_FOCUS", True),
                news=_env_bool("MORNING_BRIEF_ENABLE_NEWS", True),
                podcast=_env_bool("MORNING_BRIEF_ENABLE_PODCAST", True),
            ),
            cache_dir=os.getenv(
                "MORNING_BRIEF_CACHE_DIR",
                str(Path.home() / ".cache" / "morning-brief"),
            ),
            weather_cache_ttl=_safe_int(
                "MORNING_BRIEF_WEATHER_CACHE_TTL", DEFAULT_WEATHER_CACHE_TTL
            ),
            feed_cache_ttl=_safe_int(
                "MORNING_BRIEF_FEED_CACHE_TTL", DEFAULT_FEED_CACHE_TTL
            ),
            dry_run=dry_run,
        )

        logger.debug("Loaded env from: %s", config.env_source)
        if not config.perplexity_api_key:
            logger.warning("PERPLEXITY_API_KEY not set; LLM features disabled.")
        if config.dry_run:
            logger.info(
                "Running in --dry-run mode; output will not be sent to Readwise."
            )
        if not config.toggles.any_enabled:
            logger.warning("All sections are disabled; the brief will be nearly empty.")

        return config


@dataclass(frozen=True)
class WeatherSnapshot:
    current_temp: str
    high_temp: str
    rain_probability: str
    narrative: str


@dataclass(frozen=True)
class FocusItem:
    kind: str
    identifier: str
    title: str
    url: str
    state: str = ""
    state_type: str = ""
    due_date: str = ""
    time_label: str = ""
    badge: str = ""
    score: int = 0
    labels: tuple[str, ...] = ()
    updated_at: str = ""
    description: str = ""


@dataclass(frozen=True)
class SectionResult:
    html: str
    tags: list[str]


@dataclass(frozen=True)
class LinearQueueSnapshot:
    unread_count: int = 0
    review_items: tuple[FocusItem, ...] = ()
    notification_items: tuple[FocusItem, ...] = ()


@dataclass(frozen=True)
class DailyContext:
    today: dt.date
    today_iso: str
    calendar_time_min: str
    calendar_time_max: str

    @classmethod
    def build(cls, timezone_offset: str) -> "DailyContext":
        today = dt.date.today()
        today_iso = today.isoformat()
        return cls(
            today=today,
            today_iso=today_iso,
            calendar_time_min=f"{today_iso}T00:00:00{timezone_offset}",
            calendar_time_max=f"{today_iso}T23:59:59{timezone_offset}",
        )


# ============================================================
# Env-parsing helpers
# ============================================================


def _env_bool(key: str, default: bool) -> bool:
    """Read an env var as a boolean toggle."""
    raw = os.getenv(key, "").strip().lower()
    if not raw:
        return default
    return raw not in ("0", "false", "no", "off", "disabled")


def _safe_int(key: str, default: int) -> int:
    """Read an env var as int, falling back to default."""
    raw = os.getenv(key, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        logger.warning("Invalid %s=%r, using %s", key, raw, default)
        return default


# ============================================================
# Cache
# ============================================================


class FileCache:
    """Lightweight JSON file cache with TTL."""

    def __init__(self, cache_dir: str) -> None:
        self.root = Path(cache_dir)

    def _key_path(self, key: str) -> Path:
        safe = hashlib.sha256(key.encode()).hexdigest()[:16]
        return self.root / f"{safe}.json"

    def get(self, key: str, ttl: int) -> Any | None:
        """Return cached value if fresh, else None."""
        path = self._key_path(key)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if time.time() - data.get("ts", 0) > ttl:
                return None
            return data.get("value")
        except (json.JSONDecodeError, OSError, KeyError) as exc:
            logger.debug("Cache read error for %s: %s", key, exc)
            return None

    def set(self, key: str, value: Any) -> None:
        """Write a value into the cache."""
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            path = self._key_path(key)
            payload = {"ts": time.time(), "value": value}
            path.write_text(json.dumps(payload, default=str), encoding="utf-8")
        except OSError as exc:
            logger.debug("Cache write error for %s: %s", key, exc)


# ============================================================
# HTTP + LLM
# ============================================================


def build_retry_session(
    total: int = 3,
    backoff_factor: float = 1.0,
) -> requests.Session:
    """Create a requests session with retry logic."""
    session = requests.Session()
    retry = Retry(
        total=total,
        connect=total,
        read=total,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=frozenset(["GET", "POST"]),
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update(
        {
            "User-Agent": f"MorningBrief/{APP_VERSION} (+https://internal-brief.local)",
            "Accept": "application/json, text/html;q=0.9, */*;q=0.8",
        }
    )
    return session


class PerplexityClient:
    """Thin wrapper around Perplexity chat completions."""

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key.strip()

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def chat(
        self,
        system_prompt: str,
        user_content: str,
        *,
        max_tokens: int,
        temperature: float,
        session: requests.Session | None = None,
    ) -> str:
        if not self.enabled or not user_content.strip():
            return ""

        working = session or build_retry_session(total=2, backoff_factor=0.5)
        payload = {
            "model": "sonar",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content[:MAX_LLM_INPUT_CHARS]},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        try:
            response = working.post(
                PERPLEXITY_CHAT_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=DEFAULT_TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()
            return (
                data.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
                .strip()
            )
        except Exception as exc:
            logger.error("Perplexity API error: %s", exc)
            return ""

    def summarize_podcast(
        self, text: str, session: requests.Session | None = None
    ) -> str:
        return self.chat(
            (
                "You are a highly efficient assistant. Summarize the provided "
                "podcast show notes in exactly two concise sentences. Focus on "
                "the core environmental or scientific takeaways."
            ),
            text,
            max_tokens=LLM_MAX_TOKENS_SUMMARY,
            temperature=0.5,
            session=session,
        )

    def generate_greeting(
        self,
        weather_narrative: str,
        horoscope_text: str,
        session: requests.Session | None = None,
    ) -> str:
        return self.chat(
            (
                "You are a witty, warm, and approachable assistant. Address the user "
                "as Abhi. Write a cohesive 2-3 sentence morning greeting that blends "
                "the local weather and daily horoscope. Keep it encouraging and "
                "casually tailored to a coastal environmental science student. "
                "Do not use long dashes, use a comma and a space instead. Use "
                "standard hyphens for ranges, use straight quotes, and avoid double spaces."
            ),
            f"Weather in Baton Rouge: {weather_narrative}\nCancer Horoscope: {horoscope_text}",
            max_tokens=LLM_MAX_TOKENS_GREETING,
            temperature=0.6,
            session=session,
        )


# ============================================================
# Text + HTML Helpers (Pure)
# ============================================================


class HTMLTextExtractor(HTMLParser):
    """Extract plain text from HTML fragments."""

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def get_text(self) -> str:
        return "".join(self.parts).strip()


def strip_html_tags(text: str) -> str:
    parser = HTMLTextExtractor()
    parser.feed(text or "")
    parser.close()
    return parser.get_text()


def sanitize_text(value: Any) -> str:
    if value is None:
        return ""
    return html.escape(str(value).strip(), quote=True)


def truncate_text(text: str, max_len: int = SUMMARY_TRUNCATE_LEN) -> str:
    cleaned = (text or "").strip()
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[: max_len - 3].rstrip() + "..."


def html_li(content: str) -> str:
    return f"<li>{content}</li>"


def html_ul(items: Iterable[str]) -> str:
    return f"<ul>{''.join(items)}</ul>"


def html_section(title: str, body: str) -> str:
    return f"<h3>{sanitize_text(title)}</h3>{body}"


def html_subsection(title: str, body: str) -> str:
    return f"<h4>{sanitize_text(title)}</h4>{body}"


# ============================================================
# Pure Business Logic
# ============================================================


def is_due_today(date_str: str, today_iso: str) -> bool:
    return bool(date_str) and date_str == today_iso


def format_time_label(start_raw: str) -> str:
    if not start_raw:
        return "Anytime"
    return start_raw[11:16] if "T" in start_raw else "All day"


def extract_horoscope_text(data: dict[str, Any]) -> str | None:
    if not isinstance(data, dict):
        return None
    nested = data.get("data")
    candidates = [
        nested.get("horoscope_data") if isinstance(nested, dict) else None,
        data.get("horoscope_data"),
        data.get("horoscope"),
        data.get("description"),
    ]
    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    return None


def staleness_days(updated_at: str, today: dt.date) -> int:
    """Return days since last update, or 0 on parse failure."""
    if not updated_at:
        return 0
    try:
        updated_date = dt.date.fromisoformat(updated_at[:10])
        return max((today - updated_date).days, 0)
    except (ValueError, TypeError):
        return 0


def score_linear_issue(issue: dict[str, Any], today_iso: str, daily_today: dt.date) -> int:
    """Score a Linear issue with priority, due date, state, labels, and staleness."""
    priority = issue.get("priority") or 0
    due_date = issue.get("dueDate") or ""
    state_type = (issue.get("state", {}).get("type") or "").lower().replace("_", "")
    labels_raw = issue.get("labels", {}).get("nodes", [])
    label_names = [
        (lbl.get("name") or "").lower() for lbl in labels_raw if isinstance(lbl, dict)
    ]
    updated_at = issue.get("updatedAt") or ""

    score = 0

    # Due-date contribution
    if is_due_today(due_date, today_iso):
        score += 100
    elif due_date:
        score += 20

    # Priority contribution
    priority_scores = {1: 80, 2: 60, 3: 30, 4: 10}
    score += priority_scores.get(priority, 0)

    # State-type contribution
    score += LINEAR_STATE_WEIGHTS.get(state_type, 0)

    # Label bonuses
    for label in label_names:
        for keyword, bonus in LINEAR_LABEL_BONUSES.items():
            if keyword in label:
                score += bonus

    # Staleness penalty (issues untouched > 14 days get penalized)
    stale = staleness_days(updated_at, daily_today)
    if stale > 14:
        score -= min(stale - 14, 30)

    # Cycle membership bonus
    if issue.get("cycle"):
        score += 15

    return max(score, 0)


def calendar_admin_score(title: str, description: str = "") -> int:
    text = f"{title} {description}".lower()
    keyword_weights = {
        "maintenance": 6,
        "cleanup": 6,
        "health check": 5,
        "report": 5,
        "review": 4,
        "admin": 4,
        "system": 3,
        "monitor": 3,
        "schedule": 3,
        "planning": 3,
        "homebrew": 3,
        "deals": 1,
    }
    return sum(weight for kw, weight in keyword_weights.items() if kw in text)


def build_focus_meta_parts(item: FocusItem, today_iso: str) -> list[str]:
    parts: list[str] = []
    if item.badge:
        parts.append(item.badge)
    if item.state:
        parts.append(item.state)
    if item.due_date:
        label = (
            "due today"
            if is_due_today(item.due_date, today_iso)
            else f"due {item.due_date}"
        )
        parts.append(label)
    if item.time_label:
        parts.append(item.time_label)
    return parts


def build_selection_reason(role: str, item: FocusItem | None, today_iso: str) -> str:
    if not item:
        if role == "admin":
            return "No live admin source was available, so the brief falls back to a lightweight housekeeping prompt."
        return "No live work item was available, so the brief falls back to a general planning prompt."

    reasons: list[str] = []
    if item.kind == "linear":
        if is_due_today(item.due_date, today_iso):
            reasons.append("it is due today")
        elif item.due_date:
            reasons.append(f"it already has a due date ({item.due_date})")
        if item.badge in {"urgent", "high priority"}:
            reasons.append(f"it is marked {item.badge}")
        elif item.state:
            reasons.append(f"it is currently in {item.state}")
        if item.labels:
            reasons.append(f"labels: {', '.join(item.labels)}")
        if not reasons:
            reasons.append("it is your highest-ranked active Linear issue")
    elif item.kind == "calendar":
        if item.time_label:
            reasons.append(f"it has a clear time block at {item.time_label}")
        reasons.append("it looks like routine maintenance or operational admin")
    else:
        reasons.append("it best matches the current fallback rules")

    return f"{role.capitalize()} was chosen because " + ", ".join(reasons) + "."


def build_github_context_note(
    deep_item: FocusItem | None,
    admin_item: FocusItem | None,
) -> str:
    if deep_item and deep_item.kind == "linear":
        return (
            "Use the admin block to check related pull requests, review requests, "
            "and GitHub notifications after the main work block."
        )
    if admin_item and admin_item.kind == "calendar":
        return (
            "Pair the admin item with a quick GitHub sweep: review open PRs, "
            "triage notifications, and clear lightweight repository follow-ups."
        )
    return "Use the admin slot for PR reviews, notification triage, and small repository maintenance tasks."


def get_time_aware_guidance(now: dt.datetime | None = None) -> str:
    current = now or dt.datetime.now()
    hour = current.hour
    if hour < 12:
        return "Morning favors deep work: tackle the hardest task first and defer inbox, PRs, and light cleanup until later."
    if hour < 16:
        return "Midday is a good handoff point: finish a focused block, then clear one admin task before context-switching."
    return "Late-day energy is usually better for lighter admin work, PR reviews, and cleanup than for new deep work."


def select_focus_pair(
    linear_items: list[FocusItem],
    calendar_items: list[FocusItem],
) -> tuple[FocusItem | None, FocusItem | None]:
    deep_item = linear_items[0] if linear_items else None
    admin_item = calendar_items[0] if calendar_items else None
    return deep_item, admin_item


def derive_dynamic_tags(summary: str) -> list[str]:
    lowered = summary.lower()
    tags: list[str] = []
    if any(kw in lowered for kw in TARGET_PODCAST_KEYWORDS):
        tags.append("coastal-science")
    return tags


# ============================================================
# Data Fetching
# ============================================================


def fetch_weather(
    session: requests.Session,
    config: AppConfig,
    cache: FileCache,
) -> WeatherSnapshot:
    cache_key = f"weather:{config.lat}:{config.lon}"
    cached = cache.get(cache_key, config.weather_cache_ttl)
    if cached:
        logger.debug("Weather cache hit")
        return WeatherSnapshot(**cached)

    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast?latitude={config.lat}&longitude={config.lon}"
            "&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max"
            "&current_weather=true&temperature_unit=fahrenheit&timezone=auto"
        )
        response = session.get(url, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        current = data.get("current_weather", {})
        daily = data.get("daily", {})

        snap = WeatherSnapshot(
            current_temp=str(current.get("temperature", "N/A")),
            high_temp=str(daily.get("temperature_2m_max", ["N/A"])[0]),
            rain_probability=str(
                daily.get("precipitation_probability_max", ["N/A"])[0]
            ),
            narrative=(
                f"Current temp is {current.get('temperature', 'N/A')}F, "
                f"high today is {daily.get('temperature_2m_max', ['N/A'])[0]}F, "
                f"rain chance is {daily.get('precipitation_probability_max', ['N/A'])[0]}%."
            ),
        )
        cache.set(
            cache_key,
            {
                "current_temp": snap.current_temp,
                "high_temp": snap.high_temp,
                "rain_probability": snap.rain_probability,
                "narrative": snap.narrative,
            },
        )
        return snap
    except Exception as exc:
        logger.error("Weather fetch error: %s", exc)
        return WeatherSnapshot("N/A", "N/A", "N/A", "Weather data unavailable.")


def fetch_horoscope(session: requests.Session, zodiac_sign: str) -> str:
    default_text = (
        "Trust your instincts and prioritize tasks that reduce future stress."
    )
    for tmpl in HOROSCOPE_ENDPOINTS_TEMPLATE:
        url = tmpl.get("url") or tmpl["url_fn"](zodiac_sign)
        params = tmpl["params_fn"](zodiac_sign)
        try:
            response = session.get(url, params=params, timeout=HOROSCOPE_TIMEOUT)
            response.raise_for_status()
            extracted = extract_horoscope_text(response.json())
            if extracted:
                return extracted
        except Exception as exc:
            logger.warning("Horoscope failed from %s: %s", tmpl["name"], exc)
    return default_text


def fetch_linear_focus_items(
    session: requests.Session,
    config: AppConfig,
    daily: DailyContext,
) -> list[FocusItem]:
    if not config.linear_api_key:
        return []

    query = """
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
    """

    priority_labels = {
        1: "urgent",
        2: "high priority",
        3: "medium priority",
        4: "low priority",
    }

    try:
        response = session.post(
            LINEAR_GRAPHQL_URL,
            headers={
                "Authorization": config.linear_api_key,
                "Content-Type": "application/json",
            },
            json={"query": query},
            timeout=DEFAULT_TIMEOUT,
        )
        response.raise_for_status()
        nodes = (
            response.json()
            .get("data", {})
            .get("viewer", {})
            .get("assignedIssues", {})
            .get("nodes", [])
        )

        items: list[FocusItem] = []
        for issue in nodes:
            state = issue.get("state", {})
            state_type = (state.get("type") or "").lower()
            if state_type in {"completed", "canceled", "cancelled"}:
                continue

            label_nodes = issue.get("labels", {}).get("nodes", [])
            label_names = tuple(
                (lbl.get("name") or "").strip()
                for lbl in label_nodes
                if isinstance(lbl, dict) and lbl.get("name")
            )

            items.append(
                FocusItem(
                    kind="linear",
                    identifier=issue.get("identifier", "Linear"),
                    title=issue.get("title", "Untitled issue"),
                    url=issue.get("url", "#"),
                    state=state.get("name", "Open"),
                    state_type=state.get("type", ""),
                    due_date=issue.get("dueDate") or "",
                    badge=priority_labels.get(issue.get("priority") or 0, ""),
                    score=score_linear_issue(issue, daily.today_iso, daily.today),
                    labels=label_names,
                    updated_at=issue.get("updatedAt") or "",
                )
            )

        items.sort(key=lambda i: (-i.score, i.due_date or "9999-12-31", i.title))
        filtered = items[: config.focus_max_items]
        if not filtered:
            logger.info("No active Linear issues found for the current assignee.")
        return filtered
    except Exception as exc:
        logger.error("Linear focus error: %s", exc)
        return []


def fetch_linear_queue_snapshot(
    session: requests.Session,
    config: AppConfig,
) -> LinearQueueSnapshot:
    if not config.linear_api_key:
        return LinearQueueSnapshot()

    query = """
    query MorningBriefLinearQueue {
      notificationsUnreadCount
      notifications(first: 25, orderBy: updatedAt) {
        nodes {
          __typename
          id
          type
          category
          title
          subtitle
          url
          inboxUrl
          readAt
          updatedAt
        }
      }
    }
    """

    try:
        response = session.post(
            LINEAR_GRAPHQL_URL,
            headers={
                "Authorization": config.linear_api_key,
                "Content-Type": "application/json",
            },
            json={"query": query},
            timeout=DEFAULT_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json().get("data", {})
        unread_count = payload.get("notificationsUnreadCount", 0)
        nodes = payload.get("notifications", {}).get("nodes", [])
        unread_nodes = [node for node in nodes if not node.get("readAt")]

        review_items: list[FocusItem] = []
        seen_reviews: set[str] = set()
        notification_items: list[FocusItem] = []
        seen_notifications: set[str] = set()

        for node in unread_nodes:
            category = (node.get("category") or "").lower()
            title = node.get("title") or "Untitled notification"
            subtitle = truncate_text(node.get("subtitle") or "", 140)
            url = node.get("inboxUrl") or node.get("url") or "#"
            dedupe_key = url or title

            item = FocusItem(
                kind="linear-notification",
                identifier="Review" if category == "reviews" else "Inbox",
                title=title,
                url=url,
                badge=category or "notification",
                score=0,
                updated_at=node.get("updatedAt") or "",
                description=subtitle,
            )

            if category == "reviews":
                if dedupe_key in seen_reviews:
                    continue
                seen_reviews.add(dedupe_key)
                review_items.append(item)
                continue

            if dedupe_key in seen_notifications:
                continue
            seen_notifications.add(dedupe_key)
            notification_items.append(item)

        return LinearQueueSnapshot(
            unread_count=unread_count,
            review_items=tuple(review_items[:3]),
            notification_items=tuple(notification_items[:5]),
        )
    except Exception as exc:
        logger.error("Linear queue snapshot error: %s", exc)
        return LinearQueueSnapshot()


def fetch_calendar_focus_items(
    session: requests.Session,
    config: AppConfig,
    daily: DailyContext,
) -> list[FocusItem]:
    if not config.google_calendar_api_key or not config.google_calendar_email:
        return []
    if config.google_calendar_api_key.startswith("GOCSPX-"):
        logger.warning("GOOGLE_CALENDAR_API_KEY is an OAuth secret; skipping calendar.")
        return []

    encoded = requests.utils.quote(config.google_calendar_email, safe="")
    url = f"https://www.googleapis.com/calendar/v3/calendars/{encoded}/events"
    params = {
        "key": config.google_calendar_api_key,
        "timeMin": daily.calendar_time_min,
        "timeMax": daily.calendar_time_max,
        "singleEvents": "true",
        "orderBy": "startTime",
        "maxResults": "10",
        "timeZone": config.google_calendar_timezone,
    }

    try:
        response = session.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        events = response.json().get("items", [])

        items: list[FocusItem] = []
        for event in events:
            title = event.get("summary", "Calendar event")
            desc = event.get("description", "")
            start_raw = (
                event.get("start", {}).get("dateTime")
                or event.get("start", {}).get("date")
                or ""
            )

            items.append(
                FocusItem(
                    kind="calendar",
                    identifier="Calendar",
                    title=title,
                    url=event.get("htmlLink", "#"),
                    time_label=format_time_label(start_raw),
                    badge="admin",
                    score=calendar_admin_score(title, desc),
                    description=desc,
                )
            )

        items.sort(key=lambda i: (-i.score, i.time_label or "99:99", i.title))
        return items[: config.focus_max_items]
    except Exception as exc:
        logger.error("Calendar focus error: %s", exc)
        return []


def fetch_single_feed(
    name: str,
    url: str,
    *,
    limit: int = 3,
    cache: FileCache | None = None,
    cache_ttl: int = DEFAULT_FEED_CACHE_TTL,
) -> str:
    cache_key = f"feed:{url}"

    if cache:
        cached = cache.get(cache_key, cache_ttl)
        if cached:
            logger.debug("Feed cache hit: %s", name)
            return cached

    session = build_retry_session(total=2, backoff_factor=0.5)

    try:
        response = session.get(url, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        feed = feedparser.parse(response.content)

        if not feed.entries:
            return ""

        items: list[str] = []
        for entry in feed.entries[:limit]:
            title = sanitize_text(entry.get("title", "No Title"))
            link = entry.get("link", "#")
            summary_raw = entry.get("summary", entry.get("description", ""))
            summary = sanitize_text(
                truncate_text(strip_html_tags(html.unescape(summary_raw)))
            )

            items.append(
                f'<li style="margin-bottom: 8px;">'
                f'<a href="{link}" style="text-decoration: none; font-weight: bold; color: #2c3e50;">{title}</a><br>'
                f'<span style="color: #666; font-size: 0.9em;">{summary}</span>'
                f"</li>"
            )

        result = html_section(name, html_ul(items))
        if cache:
            cache.set(cache_key, result)
        return result
    except Exception as exc:
        logger.error("RSS error [%s]: %s", name, exc)
        return ""


def fetch_news_sections(feeds: dict[str, str], cache: FileCache) -> str:
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=min(16, len(feeds) or 1)
    ) as executor:
        futures = [
            executor.submit(fetch_single_feed, name, url, cache=cache)
            for name, url in feeds.items()
        ]
        sections = [f.result() for f in futures]
    return "".join(s for s in sections if s)


def fetch_podcast_section(llm: PerplexityClient, *, limit: int = 3) -> SectionResult:
    session = build_retry_session(total=2, backoff_factor=0.5)

    try:
        response = session.get(AMERICA_ADAPTS_RSS_URL, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        feed = feedparser.parse(response.content)

        if not feed.entries:
            return SectionResult("", [])

        detected_tags: set[str] = set()
        items: list[str] = []

        for entry in feed.entries[:limit]:
            title = sanitize_text(entry.get("title", "No Title"))
            link = entry.get("link", "#")
            pub_date = sanitize_text(entry.get("published", ""))
            summary_raw = entry.get("summary", entry.get("description", ""))
            llm_summary = llm.summarize_podcast(
                strip_html_tags(html.unescape(summary_raw)), session=session
            )

            for tag in derive_dynamic_tags(llm_summary):
                detected_tags.add(tag)

            summary_block = (
                f'<br><span style="color: #444; font-size: 0.9em;"><em>{sanitize_text(llm_summary)}</em></span>'
                if llm_summary
                else ""
            )

            items.append(
                f'<li style="margin-bottom: 12px;">'
                f'<a href="{link}" style="text-decoration: none; font-weight: bold; color: #2c3e50;">{title}</a><br>'
                f'<span style="color: #666; font-size: 0.8em;">Published: {pub_date}</span>{summary_block}'
                f"</li>"
            )

        return SectionResult(
            html=html_section("🎧 Latest from America Adapts", html_ul(items)),
            tags=sorted(detected_tags),
        )
    except Exception as exc:
        logger.error("Podcast error: %s", exc)
        return SectionResult(
            "<h3>🎧 Latest from America Adapts</h3><p><em>Could not fetch episodes today.</em></p>",
            [],
        )


# ============================================================
# Rendering
# ============================================================


def render_focus_item(label: str, item: FocusItem, today_iso: str) -> str:
    meta = " · ".join(build_focus_meta_parts(item, today_iso))
    body = f'<a href="{item.url}">'
    if item.identifier:
        body += f"<strong>{sanitize_text(item.identifier)}</strong>: "
    body += f"{sanitize_text(item.title)}</a>"
    if meta:
        body += f' <span style="color: #666;">({sanitize_text(meta)})</span>'
    return html_li(f"<strong>{sanitize_text(label)}:</strong> {body}")


def render_greeting_section(weather: WeatherSnapshot, greeting_paragraph: str) -> str:
    body = (
        f"<p>{sanitize_text(greeting_paragraph)}</p>"
        f"<ul>"
        f"<li><strong>Baton Rouge Weather:</strong> "
        f"{sanitize_text(weather.high_temp)}°F High / "
        f"{sanitize_text(weather.current_temp)}°F Current "
        f"(Rain: {sanitize_text(weather.rain_probability)}%)</li>"
        f"</ul>"
    )
    return html_section("🌅 Good Morning, Abhi", body)


def render_linear_queue_item(item: FocusItem) -> str:
    subtitle = (
        f'<br><span style="color: #666; font-size: 0.9em;">{sanitize_text(item.description)}</span>'
        if item.description
        else ""
    )
    return html_li(
        f'<a href="{item.url}"><strong>{sanitize_text(item.title)}</strong></a>{subtitle}'
    )


def render_linear_queue_focus_section(
    queue: LinearQueueSnapshot,
    daily: DailyContext,
) -> str:
    review_body = html_ul([render_linear_queue_item(item) for item in queue.review_items]) if queue.review_items else '<p><em>No review items were surfaced from Linear.</em></p>'
    notification_body = html_ul([render_linear_queue_item(item) for item in queue.notification_items]) if queue.notification_items else '<p><em>No unread notifications were surfaced from Linear.</em></p>'

    subsections = [
        html_subsection("Pending reviews", review_body),
        html_subsection("Unread notifications", notification_body),
        html_subsection(
            "Why this was chosen",
            html_ul(
                [
                    html_li(
                        sanitize_text(
                            f"No active Linear issues were available, so the brief surfaced your current queue instead: {queue.unread_count} unread notifications and {len(queue.review_items)} highlighted reviews."
                        )
                    )
                ]
            ),
        ),
        html_subsection(
            "PR / GitHub Context",
            html_ul(
                [
                    html_li(
                        sanitize_text(
                            "Start with pending reviews first, then clear the highest-signal unread notifications. This keeps merge and feedback loops moving even when no active issue is assigned."
                        )
                    )
                ]
            ),
        ),
        html_subsection(
            "Time-aware selection",
            html_ul([html_li(sanitize_text(get_time_aware_guidance()))]),
        ),
    ]

    body = (
        f"<p><strong>Linear queue snapshot:</strong> {queue.unread_count} unread notifications, {len(queue.review_items)} highlighted reviews</p>"
        + "".join(subsections)
    )
    return html_section("🚀 Focus", body)


def render_focus_section(
    deep_item: FocusItem | None, admin_item: FocusItem | None, daily: DailyContext
) -> str:
    bullets: list[str] = []
    if deep_item:
        bullets.append(render_focus_item("Deep work", deep_item, daily.today_iso))
    else:
        bullets.append(
            html_li(
                "<strong>Deep work:</strong> Choose the highest-leverage task that meaningfully moves a project forward."
            )
        )
    if admin_item:
        bullets.append(render_focus_item("Admin", admin_item, daily.today_iso))
    else:
        bullets.append(
            html_li(
                "<strong>Admin:</strong> Clear one small obligation that reduces background stress."
            )
        )

    subsections = [
        html_subsection(
            "Why this was chosen",
            html_ul(
                [
                    html_li(
                        sanitize_text(
                            build_selection_reason(
                                "deep work", deep_item, daily.today_iso
                            )
                        )
                    ),
                    html_li(
                        sanitize_text(
                            build_selection_reason("admin", admin_item, daily.today_iso)
                        )
                    ),
                ]
            ),
        ),
        html_subsection(
            "PR / GitHub Context",
            html_ul(
                [
                    html_li(
                        sanitize_text(build_github_context_note(deep_item, admin_item))
                    ),
                ]
            ),
        ),
        html_subsection(
            "Time-aware selection",
            html_ul(
                [
                    html_li(sanitize_text(get_time_aware_guidance())),
                ]
            ),
        ),
    ]

    body = (
        "<p><strong>Today's structure:</strong> one deep work item + one admin item</p>"
        + html_ul(bullets)
        + "".join(subsections)
    )
    return html_section("🚀 Focus", body)


def render_full_brief(
    *,
    daily: DailyContext,
    greeting_html: str,
    focus_html: str,
    news_html: str,
    podcast_html: str,
) -> str:
    sections = [
        f"<h1>Morning Briefing</h1><p><em>{sanitize_text(daily.today.strftime('%A, %B %d'))}</em></p>",
    ]
    for section in (greeting_html, focus_html, news_html, podcast_html):
        if section:
            sections.append("<hr>")
            sections.append(section)
    return "".join(sections)


# ============================================================
# Orchestration
# ============================================================


def build_greeting_section(
    config: AppConfig, llm: PerplexityClient, cache: FileCache
) -> str:
    session = build_retry_session(total=2, backoff_factor=0.5)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future_w = executor.submit(fetch_weather, session, config, cache)
        future_h = executor.submit(fetch_horoscope, session, config.zodiac_sign)
        weather = future_w.result()
        horoscope = future_h.result()

    greeting = llm.generate_greeting(weather.narrative, horoscope, session=session)
    if not greeting:
        greeting = "Good morning! Let's tackle today's highest-leverage tasks."
    return render_greeting_section(weather, greeting)


def build_focus_section(config: AppConfig, daily: DailyContext) -> str:
    session = build_retry_session(total=2, backoff_factor=0.5)
    linear_items = fetch_linear_focus_items(session, config, daily)
    if linear_items:
        calendar_items: list[FocusItem] = []
        deep_item, admin_item = select_focus_pair(linear_items, calendar_items)
        return render_focus_section(deep_item, admin_item, daily)

    queue = fetch_linear_queue_snapshot(session, config)
    if queue.review_items or queue.notification_items or queue.unread_count:
        return render_linear_queue_focus_section(queue, daily)

    return render_focus_section(None, None, daily)


def save_to_reader(
    config: AppConfig, html_content: str, *, extra_tags: list[str] | None = None
) -> None:
    session = build_retry_session(total=2, backoff_factor=0.5)
    unique_id = dt.datetime.now().strftime("%Y%m%d-%H%M")
    tags = sorted(set(["morning-routine", "dashboard"] + (extra_tags or [])))

    try:
        response = session.post(
            READWISE_SAVE_URL,
            headers={"Authorization": f"Token {config.readwise_token}"},
            json={
                "url": f"https://internal-brief.local/daily-{unique_id}",
                "html": html_content,
                "title": f"Morning Brief: {dt.date.today().strftime('%B %d, %Y')}",
                "author": "Raycast Assistant",
                "tags": tags,
                "should_clean_html": False,
            },
            timeout=DEFAULT_TIMEOUT,
        )
        response.raise_for_status()
        print(f"✅ Brief sent to Reader with tags: {', '.join(tags)}")
    except Exception as exc:
        print(f"❌ Error sending to Reader: {exc}", file=sys.stderr)
        sys.exit(1)


def handle_dry_run(html_content: str) -> None:
    """Write briefing HTML to stdout or a temp file."""
    if sys.stdout.isatty():
        print(html_content)
    else:
        tmp = (
            Path(tempfile.gettempdir())
            / f"morning-brief-{dt.date.today().isoformat()}.html"
        )
        tmp.write_text(html_content, encoding="utf-8")
        print(f"✅ Dry-run output written to {tmp}", file=sys.stderr)


def main() -> None:
    """Main application entrypoint."""
    config = AppConfig.load()
    daily = DailyContext.build(config.timezone_offset)
    llm = PerplexityClient(config.perplexity_api_key)
    cache = FileCache(config.cache_dir)
    toggles = config.toggles

    logger.info("Gathering local intel...")

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=min(32, 3 + len(config.feeds))
    ) as executor:
        future_greeting = (
            executor.submit(build_greeting_section, config, llm, cache)
            if toggles.greeting
            else None
        )
        future_focus = (
            executor.submit(build_focus_section, config, daily)
            if toggles.focus
            else None
        )
        future_podcast = (
            executor.submit(fetch_podcast_section, llm) if toggles.podcast else None
        )
        future_news = (
            executor.submit(fetch_news_sections, config.feeds, cache)
            if toggles.news
            else None
        )

        greeting_html = future_greeting.result() if future_greeting else ""
        focus_html = future_focus.result() if future_focus else ""
        podcast_result = (
            future_podcast.result() if future_podcast else SectionResult("", [])
        )
        news_html = future_news.result() if future_news else ""

    full_content = render_full_brief(
        daily=daily,
        greeting_html=greeting_html,
        focus_html=focus_html,
        news_html=news_html,
        podcast_html=podcast_result.html,
    )

    if config.dry_run:
        handle_dry_run(full_content)
    else:
        save_to_reader(config, full_content, extra_tags=podcast_result.tags)


if __name__ == "__main__":
    main()
