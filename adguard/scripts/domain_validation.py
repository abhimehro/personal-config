"""Validate Control D PK values before writing AdGuard filter lines."""

import re


class InvalidDomainError(ValueError):
    """A source PK cannot be represented as one domain filter line."""


_LABEL = r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
_WILDCARD_LABEL = r"[A-Za-z0-9*](?:[A-Za-z0-9*-]{0,61}[A-Za-z0-9*])?"
_DOMAIN = re.compile(rf"{_LABEL}(?:\.{_LABEL})+")
_WILDCARD_DOMAIN = re.compile(rf"{_WILDCARD_LABEL}(?:\.{_WILDCARD_LABEL})+")


def validate_pk(pk, source, *, allow_wildcards=False):
    """Return a single domain pattern or reject the source value."""
    pattern = _WILDCARD_DOMAIN if allow_wildcards else _DOMAIN
    if (
        not isinstance(pk, str)
        or len(pk) > 253
        or not pattern.fullmatch(pk)
        or (allow_wildcards and all("*" in label for label in pk.split(".")))
    ):
        raise InvalidDomainError(f"Invalid PK in {source}: {pk!r}")
    return pk
