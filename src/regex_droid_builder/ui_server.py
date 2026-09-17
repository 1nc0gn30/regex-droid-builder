"""
Regex Droid Studio UI & REST API Server (design influenced by Material 3 tokens).
Zero third-party runtime dependencies.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional

from regex_droid_builder.ast_engine import RegexASTParser, explain_regex, generate_test_samples
from regex_droid_builder.automaton_engine import (
    AutomatonBuilder,
    AutomatonGasMeter,
    to_mermaid_state_diagram,
)
from regex_droid_builder.catalog import PRESETS, get_preset, list_presets
from regex_droid_builder.codegen import generate_code_snippets
from regex_droid_builder.redos_detector import ReDoSAnalyzer

SERVER_START_TIME = time.time()

EMBEDDED_STUDIO_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Regex Droid Studio | Visual AST Builder & ReDoS Analyzer</title>
  <style>
    :root {
      --g-blue: #1a73e8;
      --g-blue-dark: #1557b0;
      --g-blue-light: #e8f0fe;
      --g-green: #1e8e3e;
      --g-green-light: #e6f4ea;
      --g-red: #d93025;
      --g-red-light: #fce8e6;
      --surface: #ffffff;
      --surface-variant: #f8f9fa;
      --border: #dadce0;
      --text: #202124;
      --text-secondary: #5f6368;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: -apple-system, BlinkMacSystemFont, "Google Sans", "Segoe UI", Roboto, sans-serif; background: var(--surface-variant); color: var(--text); height: 100vh; display: flex; flex-direction: column; }
    header { background: var(--surface); border-bottom: 1px solid var(--border); padding: 0.75rem 1.5rem; display: flex; justify-content: space-between; align-items: center; }
    .brand { font-size: 1.15rem; font-weight: 600; color: var(--g-blue); display: flex; align-items: center; gap: 0.5rem; }
    .container { display: grid; grid-template-columns: 320px 1fr; flex: 1; overflow: hidden; }
    aside { background: var(--surface); border-right: 1px solid var(--border); padding: 1.25rem; overflow-y: auto; display: flex; flex-direction: column; gap: 1rem; }
    main { padding: 1.5rem; overflow-y: auto; display: flex; flex-direction: column; gap: 1.25rem; }
    .card { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 1.25rem; }
    .btn { background: var(--g-blue); color: white; border: none; padding: 0.5rem 1rem; border-radius: 6px; font-weight: 600; cursor: pointer; }
    input, textarea { width: 100%; padding: 0.5rem 0.75rem; border: 1px solid var(--border); border-radius: 6px; font-family: monospace; font-size: 0.95rem; }
  </style>
</head>
<body>
  <header>
    <div class="brand"><span>🤖</span> Regex Droid Studio</div>
  </header>
  <div class="container">
    <aside>
      <h3>Presets</h3>
      <select id="preset-sel" onchange="loadPreset(this.value)">
        <option value="email">Email Address</option>
        <option value="url">HTTP/HTTPS URL</option>
        <option value="ipv4">IPv4 Address</option>
        <option value="uuid_v4">UUID v4</option>
        <option value="semver">Semantic Version</option>
        <option value="hex_color">Hex Color Code</option>
      </select>
    </aside>
    <main>
      <div class="card">
        <h3>Regex Pattern</h3>
        <input type="text" id="pattern-input" value="^[\\w.+-]+@[\\w-]+\\.[a-zA-Z]{2,}$" oninput="runAnalysis()">
      </div>
      <div class="card" id="redos-box">
        <h3>Security Audit (ReDoS)</h3>
        <p id="redos-status">Loading...</p>
      </div>
      <div class="card">
        <h3>Test Strings (One per line)</h3>
        <textarea id="test-input" rows="4" oninput="runTest()">test@example.com
invalid-address</textarea>
        <div id="test-results" style="margin-top:0.75rem;"></div>
      </div>
    </main>
  </div>
  <script>
    async function runAnalysis() {
      const pattern = document.getElementById('pattern-input').value;
      const resp = await fetch('/api/redos', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({pattern})
      });
      const data = await resp.json();
      document.getElementById('redos-status').innerText = `${data.severity}: ${data.description}`;
      runTest();
    }
    async function runTest() {
      const pattern = document.getElementById('pattern-input').value;
      const strings = document.getElementById('test-input').value.split('\\n').filter(Boolean);
      const resp = await fetch('/api/test', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({pattern, test_strings: strings})
      });
      const data = await resp.json();
      const div = document.getElementById('test-results');
      div.innerHTML = data.results.map(r => `<div style="color:${r.is_match ? '#1e8e3e' : '#d93025'}; font-family:monospace; margin-bottom:4px;">${r.is_match ? '✓' : '✗'} ${r.input}</div>`).join('');
    }
    function loadPreset(key) {
      fetch('/api/presets').then(r => r.json()).then(data => {
        const p = data.presets.find(x => x.id === key);
        if (p) {
          document.getElementById('pattern-input').value = p.pattern;
          runAnalysis();
        }
      });
    }
    runAnalysis();
  </script>
</body>
</html>"""


class RegexHTTPHandler(BaseHTTPRequestHandler):
    """HTTP Request Handler for Studio Web UI and REST API."""

    def _set_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _send_json(self, data: Any, status: int = 200) -> None:
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._set_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._set_cors_headers()
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/health":
            self._send_json({
                "status": "ok",
                "service": "regex-droid-builder",
                "uptime_seconds": round(time.time() - SERVER_START_TIME, 2),
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            })
            return

        elif path == "/api/presets":
            self._send_json({"presets": list_presets()})
            return

        elif path == "/api/diagnostics":
            self._send_json({
                "platform": sys.platform,
                "python": sys.version,
                "presets_catalog_size": len(PRESETS),
                "status": "HEALTHY"
            })
            return

        # Serve UI from public/index.html
        public_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "public"))
        index_file = os.path.join(public_dir, "index.html")

        if os.path.isfile(index_file) and path in ("/", "/index.html"):
            with open(index_file, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self._set_cors_headers()
            self.end_headers()
            self.wfile.write(content)
            return

        # Embedded UI fallback
        body = EMBEDDED_STUDIO_HTML.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._set_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(length) if length > 0 else b"{}"

        try:
            body = json.loads(raw_body.decode("utf-8"))
        except Exception:
            self._send_json({"error": "Invalid JSON"}, status=400)
            return

        pattern = body.get("pattern", "")
        flags = body.get("flags", "")

        if path == "/api/explain":
            parser = RegexASTParser(pattern, flags)
            ast = parser.parse()
            breakdown = explain_regex(pattern, flags)
            self._send_json({
                "pattern": pattern,
                "ast": ast.to_dict(),
                "explanation_steps": breakdown
            })
            return

        elif path == "/api/redos":
            analyzer = ReDoSAnalyzer()
            report = analyzer.analyze(pattern, flags)
            self._send_json(report.to_dict())
            return

        elif path == "/api/test":
            test_strings = body.get("test_strings", [])
            re_flags = 0
            if "i" in flags:
                re_flags |= re.IGNORECASE
            if "m" in flags:
                re_flags |= re.MULTILINE
            if "s" in flags:
                re_flags |= re.DOTALL

            try:
                compiled = re.compile(pattern, re_flags)
            except re.error as e:
                self._send_json({"error": f"Invalid regex: {str(e)}"}, status=400)
                return

            results = []
            for s in test_strings:
                m = compiled.search(s)
                if m:
                    results.append({
                        "input": s,
                        "is_match": True,
                        "span": m.span(),
                        "matched_text": m.group(0),
                        "groups": m.groups()
                    })
                else:
                    results.append({
                        "input": s,
                        "is_match": False,
                        "span": None,
                        "matched_text": None,
                        "groups": []
                    })

            self._send_json({
                "pattern": pattern,
                "total_tested": len(test_strings),
                "matches_count": sum(1 for r in results if r["is_match"]),
                "results": results
            })
            return

        elif path == "/api/samples":
            count = int(body.get("count", 4))
            samples = generate_test_samples(pattern, flags, count=count)
            self._send_json({
                "pattern": pattern,
                "flags": flags,
                "matching": samples.get("matching", []),
                "non_matching": samples.get("non_matching", [])
            })
            return

        elif path == "/api/codegen":
            snippets = generate_code_snippets(pattern, flags)
            self._send_json({
                "pattern": pattern,
                "flags": flags,
                "snippets": snippets
            })
            return

        elif path == "/api/automaton":
            builder = AutomatonBuilder()
            nfa = builder.build_nfa(pattern)
            dfa = builder.convert_to_dfa(nfa)
            mermaid_nfa = to_mermaid_state_diagram(nfa)
            mermaid_dfa = to_mermaid_state_diagram(dfa)
            self._send_json({
                "pattern": pattern,
                "nfa_states_count": nfa.total_states,
                "dfa_states_count": dfa.total_states,
                "state_explosion_ratio": dfa.state_explosion_ratio,
                "is_state_explosion": dfa.is_state_explosion,
                "mermaid_nfa": mermaid_nfa,
                "mermaid_dfa": mermaid_dfa,
            })
            return

        elif path == "/api/gas-meter":
            input_text = body.get("input_text", "")
            max_gas = int(body.get("max_gas", 50000))
            meter = AutomatonGasMeter(max_gas=max_gas)
            res = meter.trace_execution(pattern, input_text)
            self._send_json(res.to_dict())
            return

        self._send_json({"error": f"Endpoint not found: {path}"}, status=404)

    def log_message(self, format: str, *args: Any) -> None:
        pass


def run_ui_server(host: str = "0.0.0.0", port: int = 8097) -> ThreadingHTTPServer:
    """Launch UI HTTP Server."""
    server = ThreadingHTTPServer((host, port), RegexHTTPHandler)
    return server
