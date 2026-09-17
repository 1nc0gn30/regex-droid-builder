"""Tests for CLI subcommands."""

import pytest
from regex_droid_builder.cli import main


def test_cli_help(capsys):
    ret = main([])
    assert ret == 0
    out = capsys.readouterr().out
    assert "regex-droid" in out

    with pytest.raises(SystemExit):
        main(["--help"])


def test_cli_explain(capsys):
    ret = main(["explain", r"^[\w.-]+@example\.com$"])
    assert ret == 0
    out = capsys.readouterr().out
    assert "Regex Structure & Plain-English Explanation" in out


def test_cli_explain_json(capsys):
    ret = main(["explain", r"^\d+$", "--json"])
    assert ret == 0
    out = capsys.readouterr().out
    assert '"steps"' in out


def test_cli_audit_safe(capsys):
    ret = main(["audit", r"^[a-zA-Z0-9]+$"])
    assert ret == 0
    out = capsys.readouterr().out
    assert "SAFE" in out


def test_cli_audit_redos(capsys):
    ret = main(["audit", r"(a+)+$"])
    assert ret == 1
    out = capsys.readouterr().out
    assert "CRITICAL" in out or "HIGH" in out


def test_cli_test(capsys):
    ret = main(["test", r"^\d{3}$", "123", "abc", "999"])
    assert ret == 0
    out = capsys.readouterr().out
    assert "MATCH" in out


def test_cli_codegen(capsys):
    ret = main(["codegen", r"^[a-z]+$", "-l", "python"])
    assert ret == 0
    out = capsys.readouterr().out
    assert "import re" in out


def test_cli_presets(capsys):
    ret = main(["presets"])
    assert ret == 0
    out = capsys.readouterr().out
    assert "Email Address" in out


def test_cli_doctor(capsys):
    ret = main(["doctor"])
    assert ret == 0
    out = capsys.readouterr().out
    assert "HEALTHY" in out


def test_cli_test_self(capsys):
    ret = main(["test-self"])
    assert ret == 0
    out = capsys.readouterr().out
    assert "All internal checks passed" in out
