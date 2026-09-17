"""Tests for UI Web Server and REST API."""

import json
import threading
import time
import urllib.request
import pytest
from regex_droid_builder.ui_server import run_ui_server


@pytest.fixture(scope="module")
def live_server():
    server = run_ui_server(host="127.0.0.1", port=8197)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.1)
    yield "http://127.0.0.1:8197"
    server.shutdown()
    server.server_close()


def test_api_health(live_server):
    req = urllib.request.Request(f"{live_server}/api/health")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["status"] == "ok"
        assert data["service"] == "regex-droid-builder"


def test_api_presets(live_server):
    req = urllib.request.Request(f"{live_server}/api/presets")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert len(data["presets"]) >= 8


def test_api_explain(live_server):
    payload = json.dumps({"pattern": r"^[\w.-]+@example\.com$"}).encode("utf-8")
    req = urllib.request.Request(f"{live_server}/api/explain", data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert "explanation_steps" in data


def test_api_redos(live_server):
    payload = json.dumps({"pattern": r"(a+)+$"}).encode("utf-8")
    req = urllib.request.Request(f"{live_server}/api/redos", data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["is_vulnerable"] is True


def test_api_test(live_server):
    payload = json.dumps({"pattern": r"^\d+$", "test_strings": ["123", "abc"]}).encode("utf-8")
    req = urllib.request.Request(f"{live_server}/api/test", data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["total_tested"] == 2
        assert data["matches_count"] == 1


def test_ui_index_html(live_server):
    req = urllib.request.Request(f"{live_server}/")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        content = resp.read().decode("utf-8")
        assert "<!DOCTYPE html>" in content
        assert "Regex Droid Studio" in content


def test_api_samples(live_server):
    payload = json.dumps({"pattern": r"^[\w.-]+@example\.com$", "count": 2}).encode("utf-8")
    req = urllib.request.Request(f"{live_server}/api/samples", data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert "matching" in data
        assert "non_matching" in data

