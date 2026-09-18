"""
Cross-Flavor Regex Dialect Transpiler.

Transpiles regex patterns between:
- Python (`re`)
- PCRE2 / C++
- JavaScript (ECMAScript 2024)
- Go (`regexp` / RE2)
- Rust (`regex` crate)
- POSIX ERE (awk / grep -E)

Provides feature compatibility auditing, safe transformations, and native code snippets.
Zero external runtime dependencies (100% Python Standard Library).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple


SUPPORTED_DIALECTS = ["python", "pcre", "javascript", "go", "rust", "posix_ere"]


@dataclass
class TranspilationWarning:
    """A warning or incompatibility flagged during regex dialect transpilation."""
    feature: str
    severity: str  # "UNSUPPORTED_ERROR", "DEGRADED_SYNTAX", "SEMANTIC_DIFFERENCE", "INFO"
    message: str
    remediation: str


@dataclass
class TranspilationResult:
    """Result of transpiling a regex from source dialect to target dialect."""
    source_pattern: str
    source_dialect: str
    target_dialect: str
    target_pattern: str
    is_lossless: bool
    warnings: List[TranspilationWarning] = field(default_factory=list)
    code_snippet: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_pattern": self.source_pattern,
            "source_dialect": self.source_dialect,
            "target_dialect": self.target_dialect,
            "target_pattern": self.target_pattern,
            "is_lossless": self.is_lossless,
            "warnings": [
                {
                    "feature": w.feature,
                    "severity": w.severity,
                    "message": w.message,
                    "remediation": w.remediation,
                }
                for w in self.warnings
            ],
            "code_snippet": self.code_snippet,
        }


class RegexDialectTranspiler:
    """Transpiles regex patterns across programming language dialects and engines."""

    def transpile(
        self,
        pattern: str,
        source_dialect: str = "python",
        target_dialect: str = "javascript",
    ) -> TranspilationResult:
        src = source_dialect.lower().strip()
        tgt = target_dialect.lower().strip()

        if src not in SUPPORTED_DIALECTS:
            src = "python"
        if tgt not in SUPPORTED_DIALECTS:
            tgt = "javascript"

        warnings: List[TranspilationWarning] = []
        transformed = pattern

        # 1. Audit for Engine Incompatibilities (RE2 / Rust limitations)
        if tgt in ("go", "rust"):
            # Lookarounds check
            if re.search(r"\(\?[=!<=!]", transformed):
                warnings.append(
                    TranspilationWarning(
                        feature="Lookarounds (?=...), (?!...), (?<=...), (?<!...)",
                        severity="UNSUPPORTED_ERROR",
                        message=f"{tgt.upper()} engine (RE2/linear-time) strictly rejects lookahead and lookbehind assertions.",
                        remediation="Restructure pattern into prefix/suffix anchors or evaluate conditions in surrounding program logic.",
                    )
                )
            # Backreferences check (e.g. \1, \2)
            if re.search(r"(?<!\\)\\[1-9]", transformed):
                warnings.append(
                    TranspilationWarning(
                        feature="Backreferences (\\1, \\2, ...)",
                        severity="UNSUPPORTED_ERROR",
                        message=f"{tgt.upper()} linear-time automata do not support backreferences due to NP-hard complexity.",
                        remediation="Capture distinct groups separately and compare string values in host code.",
                    )
                )

        # 2. Possessive Quantifiers check (*+, ++, ?+, {m,n}+)
        if re.search(r"[*+?}]\+", transformed):
            if tgt in ("python", "javascript", "go", "rust", "posix_ere"):
                warnings.append(
                    TranspilationWarning(
                        feature="Possessive Quantifiers (*+, ++)",
                        severity="DEGRADED_SYNTAX",
                        message=f"{tgt.upper()} does not natively support possessive quantifiers (*+, ++).",
                        remediation="Converted to standard greedy quantifiers (*, +). Ensure no catastrophic backtracking.",
                    )
                )
                transformed = re.sub(r"([*+?}])\+", r"\1", transformed)

        # 3. Named Capture Groups Transpilation
        # Python: (?P<name>...)
        # PCRE/JS/Rust: (?<name>...)
        # Go: (?P<name>...)
        # POSIX ERE: Not supported -> downgrade to numbered capture group (...)
        if tgt == "javascript":
            # Convert (?P<name> to (?<name>
            transformed = re.sub(r"\(\?P<([a-zA-Z_][a-zA-Z0-9_]*)>", r"(?<\1>", transformed)
        elif tgt in ("python", "go"):
            # Convert (?<name> to (?P<name>
            transformed = re.sub(r"\(\?(?!P)<([a-zA-Z_][a-zA-Z0-9_]*)>", r"(?P<\1>", transformed)
        elif tgt == "posix_ere":
            # POSIX does not have named capture groups or non-capturing groups
            if "(?P<" in transformed or "(?<" in transformed:
                warnings.append(
                    TranspilationWarning(
                        feature="Named Capture Groups",
                        severity="DEGRADED_SYNTAX",
                        message="POSIX ERE standard does not support named capture groups.",
                        remediation="Downgrading to standard numbered capture group `(...)`.",
                    )
                )
                transformed = re.sub(r"\(\?P?<[a-zA-Z_][a-zA-Z0-9_]*>", "(", transformed)
            if "(?:" in transformed:
                warnings.append(
                    TranspilationWarning(
                        feature="Non-Capturing Groups (?:...)",
                        severity="DEGRADED_SYNTAX",
                        message="POSIX ERE standard does not support non-capturing groups `(?:...)`.",
                        remediation="Downgrading to standard capture group `(...)`.",
                    )
                )
                transformed = transformed.replace("(?:", "(")

        # 4. DotAll flag / newline matching
        if "(?s)" in transformed and tgt == "javascript":
            warnings.append(
                TranspilationWarning(
                    feature="Inline (?s) DotAll Flag",
                    severity="SEMANTIC_DIFFERENCE",
                    message="JavaScript regex does not support inline `(?s)` flag inside pattern.",
                    remediation="Removed inline `(?s)`: use `/s` flag on RegExp constructor or `[\\s\\S]`.",
                )
            )
            transformed = transformed.replace("(?s)", "")

        # 5. Atomic Groups (?>...)
        if "(?>" in transformed and tgt in ("javascript", "go", "rust", "python"):
            warnings.append(
                TranspilationWarning(
                    feature="Atomic Groups (?>...)",
                    severity="DEGRADED_SYNTAX",
                    message=f"{tgt.upper()} lacks native atomic groups.",
                    remediation="Converted `(?>...)` to non-capturing group `(?:...)`.",
                )
            )
            transformed = transformed.replace("(?>", "(?:")

        is_lossless = len([w for w in warnings if w.severity == "UNSUPPORTED_ERROR"]) == 0

        code_snippet = self._generate_native_snippet(transformed, tgt)

        return TranspilationResult(
            source_pattern=pattern,
            source_dialect=src,
            target_dialect=tgt,
            target_pattern=transformed,
            is_lossless=is_lossless,
            warnings=warnings,
            code_snippet=code_snippet,
        )

    def _generate_native_snippet(self, pattern: str, dialect: str) -> str:
        """Generate ready-to-run code snippet in target language."""
        if dialect == "python":
            return f"""import re

pattern = re.compile(r'{pattern}')
match = pattern.search(text)
if match:
    print(match.groupdict() if pattern.groupindex else match.group(0))"""

        elif dialect == "javascript":
            return f"""const regex = /{pattern}/g;
const match = regex.exec(text);
if (match) {{
    console.log(match.groups || match[0]);
}}"""

        elif dialect == "pcre":
            return f"""#include <pcre2.h>
// Compile pattern: "{pattern}"
pcre2_code *re = pcre2_compile((PCRE2_SPTR)"{pattern}", PCRE2_ZERO_TERMINATED, 0, &err_code, &err_offset, NULL);"""

        elif dialect == "go":
            return f"""package main

import (
    "fmt"
    "regexp"
)

func main() {{
    re := regexp.MustCompile(`{pattern}`)
    match := re.FindString(text)
    fmt.Println(match)
}}"""

        elif dialect == "rust":
            return f"""use regex::Regex;

fn main() {{
    let re = Regex::new(r"{pattern}").unwrap();
    if let Some(caps) = re.captures(text) {{
        println!("Match: {{:?}}", &caps[0]);
    }}
}}"""

        elif dialect == "posix_ere":
            return f"""# POSIX awk / grep -E
grep -E '{pattern}' input.txt

# Or in awk:
awk '/{pattern}/ {{ print $0 }}' input.txt"""

        return pattern


# Singleton instance
_transpiler = RegexDialectTranspiler()


def transpile_regex(
    pattern: str,
    source_dialect: str = "python",
    target_dialect: str = "javascript",
) -> TranspilationResult:
    """Convenience function to transpile a regex pattern across dialects."""
    return _transpiler.transpile(pattern, source_dialect=source_dialect, target_dialect=target_dialect)
