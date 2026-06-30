#!/usr/bin/env python3
"""
Select one conservative, best Alldebrid WebDAV candidate from stdin.

Input: one filename per line.
Output: exactly one selected filename on stdout, or nothing if no candidate.
Logs: human-readable selection details on stderr.
State:
  ~/CloudMedia/approval_needed/.alldebrid_selected.tsv, completed selections
  ~/CloudMedia/approval_needed/.alldebrid_ignore, exact filenames or identities to skip
  ~/CloudMedia/approval_needed/.alldebrid_candidate_pending.tsv, latest pending selection
"""


import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

VIDEO_RE = re.compile(r"\.(mp4|mkv|avi|m4v|mov)$", re.IGNORECASE)
TV_RE = re.compile(
    r"(?i)(?:^|[ ._\-\(\[])(s\d{1,2})[ ._\-]*(e\d{1,2})(?:$|[ ._\-\)\]])"
)
YEAR_RE = re.compile(r"(?<!\d)(19\d{2}|20\d{2})(?!\d)")

BAD_MARKERS = {
    "cam": -100,
    "hdcam": -100,
    "ts": -80,
    "telesync": -80,
    "tc": -70,
    "telecine": -70,
    "scr": -60,
    "screener": -60,
    "xbet": -40,
}

RESOLUTION = {
    "4320p": 80,
    "2160p": 60,
    "4k": 55,
    "1080p": 35,
    "720p": 15,
    "480p": 0,
}

HDR = {
    "dolby vision": 20,
    "dovi": 20,
    "dv": 18,
    "hdr10plus": 18,
    "hdr10+": 18,
    "hdr10": 14,
    "hdr": 10,
}

AUDIO = {
    "truehd": 18,
    "atmos": 16,
    "dts-hd": 15,
    "dtshd": 15,
    "dts": 10,
    "ddp": 9,
    "eac3": 8,
    "aac": 3,
}

RELEASE = {
    "remux": 25,
    "bluray": 20,
    "blu-ray": 20,
    "web-dl": 16,
    "webdl": 16,
    "webrip": 10,
    "hdtv": 4,
}

CODEC = {
    "h.265": 10,
    "h265": 10,
    "x265": 10,
    "hevc": 10,
    "av1": 9,
    "h.264": 5,
    "h264": 5,
    "x264": 5,
}


@dataclass
class Candidate:
    filename: str
    identity: str
    score: int
    reasons: list[str]


def clean_title(value: str) -> str:
    value = VIDEO_RE.sub("", value)
    value = re.sub(r"&#0*39;", "'", value)
    value = re.sub(r"\[[^\]]*\]", " ", value)
    value = re.sub(r"\([^)]*\)", " ", value)
    value = re.sub(r"[._\-]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def slug(value: str) -> str:
    value = value.lower()
    value = value.replace("&", "and")
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def identity_for(filename: str) -> str:
    stem = VIDEO_RE.sub("", filename)
    tv = TV_RE.search(stem)
    if tv:
        prefix = stem[: tv.start()]
        show = clean_title(prefix)
        season = int(tv.group(1)[1:])
        episode = int(tv.group(2)[1:])
        return f"{slug(show)}-s{season:02d}e{episode:02d}"

    year_match = YEAR_RE.search(stem)
    if year_match:
        title = clean_title(stem[: year_match.start()])
        return f"{slug(title)}-{year_match.group(1)}"

    return slug(clean_title(stem))


def compact_token(value: str, keep_plus: bool = False) -> str:
    allowed = r"[^a-z0-9+]+" if keep_plus else r"[^a-z0-9]+"
    return re.sub(allowed, "", value.lower())


def apply_token_scores(
    text: str,
    compact: str,
    tokens: dict[str, int],
    reasons: list[str],
    *,
    stop_after_first: bool = False,
    keep_plus: bool = False,
    label_transform=lambda token: token,
) -> int:
    score = 0
    for token, points in tokens.items():
        token_compact = compact_token(token, keep_plus=keep_plus)
        if token in text or token_compact in compact:
            score += points
            reasons.append(label_transform(token))
            if stop_after_first:
                break
    return score


def score_candidate(filename: str) -> tuple[int, list[str]]:
    text = filename.lower()
    compact = compact_token(text, keep_plus=True)
    score = 0
    reasons: list[str] = []

    score += apply_token_scores(
        text, compact, RESOLUTION, reasons, stop_after_first=True
    )
    score += apply_token_scores(
        text,
        compact,
        HDR,
        reasons,
        keep_plus=True,
        label_transform=lambda token: token.upper() if len(token) <= 5 else token,
    )
    score += apply_token_scores(
        text, compact, AUDIO, reasons, label_transform=lambda token: token.upper()
    )
    score += apply_token_scores(text, compact, RELEASE, reasons, stop_after_first=True)
    score += apply_token_scores(text, compact, CODEC, reasons, stop_after_first=True)

    for token, points in BAD_MARKERS.items():
        if re.search(rf"(?i)(^|[^a-z0-9]){re.escape(token)}([^a-z0-9]|$)", filename):
            score += points
            reasons.append(f"bad:{token}")

    return score, reasons


def read_lines(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {
        line.strip()
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines()
        if line.strip()
    }


def read_processed_identities(selected_path: Path) -> set[str]:
    identities: set[str] = set()
    if not selected_path.exists():
        return identities
    for line in selected_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip() or line.startswith("identity\t"):
            continue
        identities.add(line.split("\t", 1)[0])
    return identities


def main() -> int:
    approval_dir = Path(
        os.environ.get(
            "APPROVAL_DIR", str(Path.home() / "CloudMedia" / "approval_needed")
        )
    )
    selected_path = approval_dir / ".alldebrid_selected.tsv"
    ignore_path = approval_dir / ".alldebrid_ignore"
    pending_path = approval_dir / ".alldebrid_candidate_pending.tsv"

    files = [
        line.strip()
        for line in sys.stdin
        if line.strip() and VIDEO_RE.search(line.strip())
    ]
    ignored = read_lines(ignore_path)
    processed = read_processed_identities(selected_path)

    candidates: list[Candidate] = []
    skipped_processed = 0
    skipped_ignored = 0

    for filename in files:
        identity = identity_for(filename)
        if filename in ignored or identity in ignored:
            skipped_ignored += 1
            continue
        if identity in processed:
            skipped_processed += 1
            continue
        score, reasons = score_candidate(filename)
        candidates.append(Candidate(filename, identity, score, reasons))

    if not candidates:
        print("Candidate selection: no eligible candidates", file=sys.stderr)
        print(f"skipped already selected: {skipped_processed}", file=sys.stderr)
        print(f"skipped ignored: {skipped_ignored}", file=sys.stderr)
        pending_path.unlink(missing_ok=True)
        return 0

    grouped: dict[str, list[Candidate]] = {}
    for candidate in candidates:
        grouped.setdefault(candidate.identity, []).append(candidate)

    winners = [
        max(group, key=lambda c: (c.score, c.filename)) for group in grouped.values()
    ]
    winner = max(winners, key=lambda c: (c.score, c.identity, c.filename))
    duplicate_count = max(0, len(grouped[winner.identity]) - 1)
    reason = " + ".join(dict.fromkeys(winner.reasons)) or "baseline"
    selected_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    pending_path.write_text(
        "identity\tfilename\tscore\treason\tselected_at\tduplicates_skipped\n"
        f"{winner.identity}\t{winner.filename}\t{winner.score}\t{reason}\t{selected_at}\t{duplicate_count}\n"
    )

    print("Candidate selection:", file=sys.stderr)
    print(f"identity: {winner.identity}", file=sys.stderr)
    print(f"selected: {winner.filename}", file=sys.stderr)
    print(f"reason: score={winner.score}, {reason}", file=sys.stderr)
    print(f"duplicates skipped: {duplicate_count}", file=sys.stderr)
    print(f"skipped already selected: {skipped_processed}", file=sys.stderr)
    print(f"skipped ignored: {skipped_ignored}", file=sys.stderr)
    print(winner.filename)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
