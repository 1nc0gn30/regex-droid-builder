"""
Standard Regex Pattern Catalog & Curated Presets.
Zero external runtime dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class RegexPreset:
    """Represents a curated regular expression preset."""
    id: str
    name: str
    category: str
    pattern: str
    flags: str
    explanation: str
    test_cases: List[Dict[str, Any]] = field(default_factory=list)


PRESETS: Dict[str, RegexPreset] = {
    "email": RegexPreset(
        id="email",
        name="Email Address (RFC 5322 Pragmatic)",
        category="Web & Identifiers",
        pattern=r"^[\w.+-]+@(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}$",
        flags="",
        explanation="Matches typical email addresses with word characters, dots, pluses, or hyphens, an @ symbol, domain name, and a 2+ character TLD.",
        test_cases=[
            {"input": "user@example.com", "should_match": True},
            {"input": "alex.dev+test@domain.co.uk", "should_match": True},
            {"input": "plainaddress", "should_match": False},
            {"input": "@missinguser.com", "should_match": False},
        ]
    ),
    "url": RegexPreset(
        id="url",
        name="HTTP / HTTPS Web URL",
        category="Web & Identifiers",
        pattern=r"^https?:\/\/(?:localhost|(?:\d{1,3}\.){3}\d{1,3}|(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6})(?::[0-9]{1,5})?(?:[-a-zA-Z0-9()@:%_\+.~#?&//=]*)$",
        flags="",
        explanation="Matches standard HTTP and HTTPS web URLs including optional www, domains, ports, paths, query strings, and anchor hashes.",
        test_cases=[
            {"input": "https://google.com/search?q=regex", "should_match": True},
            {"input": "http://localhost:8080/api", "should_match": True},
            {"input": "ftp://files.example.com", "should_match": False},
        ]
    ),
    "ipv4": RegexPreset(
        id="ipv4",
        name="IPv4 Address (0-255 Octets)",
        category="Network",
        pattern=r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$",
        flags="",
        explanation="Matches valid IPv4 addresses where each of the 4 octets is strictly bounded between 0 and 255.",
        test_cases=[
            {"input": "192.168.1.1", "should_match": True},
            {"input": "255.255.255.255", "should_match": True},
            {"input": "256.100.0.1", "should_match": False},
            {"input": "192.168.1", "should_match": False},
        ]
    ),
    "uuid_v4": RegexPreset(
        id="uuid_v4",
        name="UUID v4 (Universally Unique Identifier)",
        category="Identifiers",
        pattern=r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-4[0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$",
        flags="",
        explanation="Matches RFC 4122 compliant version-4 UUID strings (e.g. `f47ac10b-58cc-4372-a567-0e02b2c3d479`).",
        test_cases=[
            {"input": "c9a646d3-9c61-4cd9-bc14-aa963f66ab60", "should_match": True},
            {"input": "00000000-0000-0000-0000-000000000000", "should_match": False},
        ]
    ),
    "semver": RegexPreset(
        id="semver",
        name="Semantic Version (SemVer 2.0)",
        category="Software Engineering",
        pattern=r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+(?P<buildmetadata>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$",
        flags="",
        explanation="Official SemVer 2.0 specification regex with major, minor, patch, prerelease, and build metadata capture groups.",
        test_cases=[
            {"input": "1.0.0", "should_match": True},
            {"input": "2.1.0-beta.1+20260916", "should_match": True},
            {"input": "v1.0.0", "should_match": False},
        ]
    ),
    "hex_color": RegexPreset(
        id="hex_color",
        name="Hexadecimal Color Code (#RGB / #RRGGBB / #RRGGBBAA)",
        category="Design & UI",
        pattern=r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$",
        flags="",
        explanation="Matches 3, 6, or 8 digit hexadecimal CSS color codes with a leading hashtag.",
        test_cases=[
            {"input": "#1a73e8", "should_match": True},
            {"input": "#FFF", "should_match": True},
            {"input": "#ff0000aa", "should_match": True},
            {"input": "#12", "should_match": False},
        ]
    ),
    "phone_na": RegexPreset(
        id="phone_na",
        name="North American Phone Number",
        category="Telecom",
        pattern=r"^(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})$",
        flags="",
        explanation="Matches 10-digit North American telephone numbers with optional country code, parentheses, dots, spaces, or hyphens.",
        test_cases=[
            {"input": "(555) 123-4567", "should_match": True},
            {"input": "+1-800-555-0199", "should_match": True},
            {"input": "555.867.5309", "should_match": True},
            {"input": "123-45", "should_match": False},
        ]
    ),
    "date_iso8601": RegexPreset(
        id="date_iso8601",
        name="ISO 8601 Date (YYYY-MM-DD)",
        category="Date & Time",
        pattern=r"^\d{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])$",
        flags="",
        explanation="Matches standard calendar dates in ISO 8601 format (YYYY-MM-DD) with valid month (01-12) and day (01-31) ranges.",
        test_cases=[
            {"input": "2026-09-16", "should_match": True},
            {"input": "1999-12-31", "should_match": True},
            {"input": "2026-02-35", "should_match": False},
            {"input": "09-16-2026", "should_match": False},
        ]
    ),
    "slug": RegexPreset(
        id="slug",
        name="URL Kebab-Case Slug",
        category="Web & Identifiers",
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
        flags="",
        explanation="Matches clean URL slugs consisting of lowercase alphanumeric words separated by single hyphens, without leading/trailing dashes.",
        test_cases=[
            {"input": "google-datamosh-studio", "should_match": True},
            {"input": "regex-droid-builder-2026", "should_match": True},
            {"input": "-leading-dash", "should_match": False},
            {"input": "double--dash", "should_match": False},
        ]
    ),
    "jwt": RegexPreset(
        id="jwt",
        name="JSON Web Token (JWT)",
        category="Security & Auth",
        pattern=r"^[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\.[A-Za-z0-9-_]*$",
        flags="",
        explanation="Matches standard 3-part base64url encoded JSON Web Tokens separated by periods (Header.Payload.Signature).",
        test_cases=[
            {"input": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c", "should_match": True},
            {"input": "invalid.jwt", "should_match": False},
        ]
    ),
}


def get_preset(preset_id: str) -> RegexPreset:
    """Get preset by ID or default to email."""
    return PRESETS.get(preset_id, PRESETS["email"])


def list_presets() -> List[Dict[str, Any]]:
    """Return list of all preset metadata."""
    return [
        {
            "id": p.id,
            "name": p.name,
            "category": p.category,
            "pattern": p.pattern,
            "flags": p.flags,
            "explanation": p.explanation,
            "test_cases": p.test_cases,
        }
        for p in PRESETS.values()
    ]
