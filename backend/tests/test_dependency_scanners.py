import json
from pathlib import Path

from app.scanners.npm_audit_scanner import parse_npm_audit_json
from app.scanners.pip_audit_scanner import (
    collect_pins,
    parse_pip_audit_json,
    parse_requirements,
)


def test_parse_requirements_only_collects_exact_pins() -> None:
    result = parse_requirements(
        "Flask==2.0.0\nrequests>=2\n# comment\nurllib3[secure]==1.26.0 ; python_version >= '3.8'\n",
        "requirements.txt",
    )

    assert [(pin.name, pin.version, pin.line) for pin in result.pins] == [
        ("Flask", "2.0.0", 1),
        ("urllib3", "1.26.0", 4),
    ]
    assert result.unpinned == 1


def test_collect_pins_deduplicates_and_reports_unpinned(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text("flask==2.0.0\nrequests>=2\n", encoding="utf-8")
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "requirements.txt").write_text("Flask==2.0.0\n", encoding="utf-8")

    result = collect_pins(tmp_path)

    assert result.files == 2
    assert len(result.pins) == 1
    assert result.unpinned == 1


def test_parse_pip_audit_json_creates_finding(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text("flask==2.0.0\n", encoding="utf-8")
    pins = collect_pins(tmp_path).pins
    output = json.dumps(
        {
            "dependencies": [
                {
                    "name": "Flask",
                    "version": "2.0.0",
                    "vulns": [
                        {
                            "id": "PYSEC-2022-01",
                            "fix_versions": ["2.2.0"],
                            "description": "A vulnerability.",
                        }
                    ],
                }
            ]
        }
    )

    report = parse_pip_audit_json(output, pins, tmp_path, "s" * 32)

    assert len(report.findings) == 1
    assert report.findings[0].rule_id == "PYSEC-2022-01"
    assert report.findings[0].severity == "medium"
    assert report.findings[0].file_path == "requirements.txt"


def test_parse_npm_audit_json_creates_finding(tmp_path: Path) -> None:
    lock = tmp_path / "package-lock.json"
    lock.write_text('{\n  "packages": {\n    "node_modules/demo": {}\n  }\n}\n', encoding="utf-8")
    output = json.dumps(
        {
            "vulnerabilities": {
                "demo": {
                    "severity": "moderate",
                    "range": "<1.2.0",
                    "nodes": ["node_modules/demo"],
                    "via": [
                        {
                            "source": 123,
                            "title": "Demo vulnerability",
                            "severity": "moderate",
                            "url": "https://example.invalid/advisories/123",
                            "cwe": ["CWE-79"],
                        }
                    ],
                    "fixAvailable": True,
                }
            }
        }
    )

    findings, dropped = parse_npm_audit_json(
        output, "package-lock.json", lock.read_text().splitlines(), tmp_path, "s" * 32
    )

    assert dropped == 0
    assert len(findings) == 1
    assert findings[0].rule_id == "123"
    assert findings[0].severity == "medium"
    assert findings[0].cwe == "CWE-79"
