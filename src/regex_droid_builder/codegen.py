"""
Multi-Language Regex Code Generator.
Generates production snippets in Python, JavaScript/TypeScript, Rust, Go, Java, and C#.
Zero external runtime dependencies.
"""

from __future__ import annotations

from typing import Dict


def generate_code_snippets(pattern: str, flags: str = "") -> Dict[str, str]:
    """Generate production-ready code snippets across major programming languages."""
    # Clean pattern escaping for various languages
    py_pattern = pattern.replace('"', '\\"')
    js_pattern = pattern.replace("/", "\\/")
    rust_pattern = pattern.replace('"', '\\"')
    go_pattern = pattern

    # Python
    py_flags = []
    if "i" in flags:
        py_flags.append("re.IGNORECASE")
    if "m" in flags:
        py_flags.append("re.MULTILINE")
    if "s" in flags:
        py_flags.append("re.DOTALL")
    py_flag_str = f", { ' | '.join(py_flags) }" if py_flags else ""

    python_code = f"""import re

pattern = r"{py_pattern}"
regex = re.compile(pattern{py_flag_str})

# Test if string matches
def is_match(text: str) -> bool:
    return bool(regex.search(text))

# Extract matches
def extract_matches(text: str):
    return regex.findall(text)
"""

    # JavaScript / TypeScript
    js_code = f"""// ECMAScript RegExp
const regex = /{js_pattern}/{flags};

function isMatch(text) {{
  return regex.test(text);
}}

function extractMatches(text) {{
  return [...text.matchAll(new RegExp(regex.source, '{flags}' + (regex.flags.includes('g') ? '' : 'g')))];
}}
"""

    # Rust
    rust_code = f"""// Cargo.toml: regex = "1.10"
use regex::Regex;

fn is_match(text: &str) -> bool {{
    let re = Regex::new(r"{rust_pattern}").unwrap();
    re.is_match(text)
}}

fn extract_matches<'a>(text: &'a str) -> Vec<&'a str> {{
    let re = Regex::new(r"{rust_pattern}").unwrap();
    re.find_iter(text).map(|m| m.as_str()).collect()
}}
"""

    # Go
    go_code = f"""package main

import (
\t"fmt"
\t"regexp"
)

var re = regexp.MustCompile(`{go_pattern}`)

func isMatch(text string) bool {{
\treturn re.MatchString(text)
}}

func extractMatches(text string) []string {{
\treturn re.FindAllString(text, -1)
}}
"""

    # Java
    java_code = f"""import java.util.regex.Pattern;
import java.util.regex.Matcher;

public class RegexHelper {{
    private static final Pattern PATTERN = Pattern.compile("{pattern.replace('\\', '\\\\')}");

    public static boolean isMatch(String text) {{
        return PATTERN.matcher(text).find();
    }}
}}
"""

    # C#
    csharp_code = f"""using System;
using System.Text.RegularExpressions;

public static class RegexHelper {{
    private static readonly Regex Pattern = new Regex(@"{pattern.replace('"', '""')}", RegexOptions.Compiled);

    public static bool IsMatch(string text) => Pattern.IsMatch(text);
}}
"""

    return {
        "python": python_code,
        "javascript": js_code,
        "rust": rust_code,
        "go": go_code,
        "java": java_code,
        "csharp": csharp_code,
    }
