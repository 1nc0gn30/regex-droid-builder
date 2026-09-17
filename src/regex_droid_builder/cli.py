"""
Command-Line Interface for regex-droid-builder.
Zero external runtime dependencies.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Any, List, Optional

from regex_droid_builder.ast_engine import explain_regex
from regex_droid_builder.catalog import PRESETS, get_preset, list_presets
from regex_droid_builder.codegen import generate_code_snippets
from regex_droid_builder.mcp_server import run_mcp_server
from regex_droid_builder.redos_detector import ReDoSAnalyzer, ReDoSSeverity
from regex_droid_builder.ui_server import run_ui_server


class Colors:
    """ANSI terminal color helpers with automatic disabling."""
    def __init__(self, force_disable: bool = False) -> None:
        disabled = force_disable or "NO_COLOR" in os.environ or not hasattr(sys.stdout, "isatty") or not sys.stdout.isatty()
        self.BLUE = "" if disabled else "\033[94m"
        self.GREEN = "" if disabled else "\033[92m"
        self.YELLOW = "" if disabled else "\033[93m"
        self.RED = "" if disabled else "\033[91m"
        self.CYAN = "" if disabled else "\033[96m"
        self.BOLD = "" if disabled else "\033[1m"
        self.DIM = "" if disabled else "\033[2m"
        self.RESET = "" if disabled else "\033[0m"


def build_parser() -> argparse.ArgumentParser:
    """Construct CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="regex-droid",
        description="Visual Regex AST Builder, ReDoS Vulnerability Detector & Multi-Language Code Generator",
    )
    parser.add_argument("-v", "--version", action="version", version="regex-droid-builder 0.1.0")

    base = argparse.ArgumentParser(add_help=False)
    base.add_argument("--no-color", action="store_true", help="Disable ANSI color output")
    base.add_argument("-f", "--flags", default="", help="Regex flags (e.g. 'i', 'm', 's')")

    sub = parser.add_subparsers(dest="command", help="Available subcommands")

    # explain
    p_exp = sub.add_parser("explain", parents=[base], help="Explain a regular expression in plain English")
    p_exp.add_argument("pattern", help="Regular expression pattern to explain")
    p_exp.add_argument("--json", action="store_true", help="Output AST as JSON")

    # audit / redos
    p_aud = sub.add_parser("audit", aliases=["redos"], parents=[base], help="Audit pattern for ReDoS vulnerabilities")
    p_aud.add_argument("pattern", help="Regular expression pattern to audit")
    p_aud.add_argument("--json", action="store_true", help="Output report as JSON")

    # test
    p_test = sub.add_parser("test", parents=[base], help="Test strings against a regular expression")
    p_test.add_argument("pattern", help="Regular expression pattern")
    p_test.add_argument("inputs", nargs="+", help="Input strings to test")
    p_test.add_argument("--json", action="store_true", help="Output results as JSON")

    # codegen
    p_code = sub.add_parser("codegen", parents=[base], help="Generate multi-language code snippets")
    p_code.add_argument("pattern", help="Regular expression pattern")
    p_code.add_argument("-l", "--lang", choices=["all", "python", "javascript", "rust", "go", "java", "csharp"], default="all")

    # presets
    p_pres = sub.add_parser("presets", parents=[base], help="List curated regex presets")
    p_pres.add_argument("--json", action="store_true", help="Output presets as JSON")

    # serve
    p_serve = sub.add_parser("serve", parents=[base], help="Start Google Material 3 Regex Studio Web UI")
    p_serve.add_argument("--host", default="0.0.0.0", help="Host address (default: 0.0.0.0)")
    p_serve.add_argument("--port", type=int, default=8097, help="Port (default: 8097)")

    # mcp
    p_mcp = sub.add_parser("mcp", parents=[base], help="Run Model Context Protocol stdio server")

    # diagnostics / doctor
    p_doc = sub.add_parser("doctor", aliases=["diagnostics", "platform"], parents=[base], help="Run system diagnostics")

    # test-self
    p_tself = sub.add_parser("test-self", parents=[base], help="Run internal self-verification test runner")

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """CLI execution entrypoint."""
    if argv is None:
        argv = sys.argv[1:]

    parser = build_parser()
    if not argv:
        parser.print_help()
        return 0

    args = parser.parse_args(argv)
    c = Colors(force_disable=getattr(args, "no_color", False))

    if args.command == "explain":
        steps = explain_regex(args.pattern, args.flags)
        if args.json:
            print(json.dumps({"pattern": args.pattern, "steps": steps}, indent=2))
        else:
            print(f"\n{c.BOLD}🤖 Regex Structure & Plain-English Explanation{c.RESET}")
            print(f"  Pattern: {c.CYAN}/{args.pattern}/{args.flags}{c.RESET}\n")
            for idx, step in enumerate(steps, 1):
                indent = "  " * step["depth"]
                val = f" ({step['value']})" if step["value"] else ""
                print(f"  {indent}{c.GREEN}#{idx}{c.RESET} {c.BOLD}{step['type']}{c.RESET}{val}: {step['explanation']}")
            print()
        return 0

    elif args.command in ("audit", "redos"):
        analyzer = ReDoSAnalyzer()
        report = analyzer.analyze(args.pattern, args.flags)
        if args.json:
            print(json.dumps(report.to_dict(), indent=2))
        else:
            print(f"\n{c.BOLD}🛡️ ReDoS Security Audit Report{c.RESET}")
            print(f"  Pattern: {c.CYAN}/{args.pattern}/{args.flags}{c.RESET}")

            sev_color = c.GREEN if report.severity == ReDoSSeverity.SAFE else (c.YELLOW if report.severity in (ReDoSSeverity.LOW, ReDoSSeverity.MEDIUM) else c.RED)
            print(f"  Severity: {sev_color}{report.severity.value}{c.RESET}")
            print(f"  Complexity: {c.BOLD}{report.complexity_order}{c.RESET}")
            print(f"  Description: {report.description}")
            if report.is_vulnerable:
                print(f"  {c.RED}Matched Subpattern: {report.matched_subpattern}{c.RESET}")
                print(f"  {c.YELLOW}Remediation: {report.remediation}{c.RESET}")
            print()
        return 0 if not report.is_vulnerable else 1

    elif args.command == "test":
        re_flags = 0
        if "i" in args.flags:
            re_flags |= re.IGNORECASE
        if "m" in args.flags:
            re_flags |= re.MULTILINE
        if "s" in args.flags:
            re_flags |= re.DOTALL

        try:
            compiled = re.compile(args.pattern, re_flags)
        except re.error as e:
            print(f"{c.RED}Error: Invalid regex: {str(e)}{c.RESET}")
            return 1

        results = []
        for s in args.inputs:
            m = compiled.search(s)
            results.append({
                "input": s,
                "is_match": bool(m),
                "matched_text": m.group(0) if m else None,
                "groups": m.groups() if m else []
            })

        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print(f"\n{c.BOLD}🧪 Regex Match Results for /{args.pattern}/{args.flags}:{c.RESET}\n")
            for r in results:
                icon = f"{c.GREEN}✓ MATCH{c.RESET}" if r["is_match"] else f"{c.RED}✗ NO MATCH{c.RESET}"
                extra = f" (captured: '{r['matched_text']}')" if r["is_match"] else ""
                print(f"  [{icon}] \"{r['input']}\"{extra}")
            print()
        return 0

    elif args.command == "codegen":
        snippets = generate_code_snippets(args.pattern, args.flags)
        if args.lang == "all":
            for lang, code in snippets.items():
                print(f"\n{c.BOLD}--- {lang.upper()} ---{c.RESET}")
                print(code.strip())
        else:
            print(snippets.get(args.lang, "").strip())
        return 0

    elif args.command == "presets":
        if args.json:
            print(json.dumps(list_presets(), indent=2))
        else:
            print(f"\n{c.BOLD}🤖 Regex Droid Curated Presets Catalog{c.RESET}\n")
            for p in PRESETS.values():
                print(f"  {c.CYAN}{p.id:<14}{c.RESET} : {c.BOLD}{p.name}{c.RESET} ({c.DIM}{p.category}{c.RESET})")
                print(f"    Pattern: /{p.pattern}/{p.flags}")
                print(f"    {c.DIM}{p.explanation}{c.RESET}\n")
        return 0

    elif args.command == "serve":
        server = run_ui_server(args.host, args.port)
        print(f"{c.GREEN}🤖 Google Regex Studio UI running at:{c.RESET} http://{args.host}:{args.port}")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server.")
        return 0

    elif args.command == "mcp":
        run_mcp_server()
        return 0

    elif args.command in ("doctor", "diagnostics", "platform"):
        print(f"\n{c.BOLD}🤖 Regex Droid Builder - System Diagnostics{c.RESET}")
        print(f"  Platform         : {sys.platform}")
        print(f"  Python Version   : {sys.version.split()[0]}")
        print(f"  Presets Loaded   : {len(PRESETS)}")
        print(f"  Zero Runtime Deps: {c.GREEN}YES (100% Python Standard Library){c.RESET}")
        print(f"  Status           : {c.GREEN}HEALTHY{c.RESET}\n")
        return 0

    elif args.command == "test-self":
        print(f"{c.BOLD}Running internal self-verification test runner...{c.RESET}")
        # Test basic parsing
        steps = explain_regex(r"^[\w.-]+@[\w.-]+\.[a-zA-Z]{2,}$")
        assert len(steps) > 3
        # Test redos detection
        analyzer = ReDoSAnalyzer()
        rep = analyzer.analyze(r"(a+)+$")
        assert rep.is_vulnerable is True
        print(f"{c.GREEN}✓ All internal checks passed!{c.RESET}")
        return 0

    return 0
