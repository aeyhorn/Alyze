"""Tests for the quality-gate agents (docs / tests / quality / runner).

These tests exercise the agents against a small on-disk fixture project so
they don't depend on the real bdx-intelligence tree, the dev database, SAP,
or any external system.
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from bdx.agents.base import CheckResult, Finding, Severity, Status
from bdx.agents.docs import DocumentationAgent, DocumentationConfig
from bdx.agents.quality import QualityAgent, QualityConfig
from bdx.agents.runner import AgentRunner, RunnerConfig, RunnerReport

# ── fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture
def sample_project(tmp_path: Path) -> Path:
    """A minimal but well-behaved project tree for the agents to scan."""
    (tmp_path / "README.md").write_text(
        "# sample\n\nA sample project for the quality-gate agents.\n" * 5,
        encoding="utf-8",
    )
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "ARCHITECTURE.md").write_text(
        "# Architecture\n\nRoutes: `/api/v1/orders`, `/api/v1/machines`.\n"
        "Env: `SAP_DB_HOST`, `POSTGRES_DSN`.\n",
        encoding="utf-8",
    )
    (docs / "PROJECT_STATUS.md").write_text("# Status\n\nAll green.\n", encoding="utf-8")
    (docs / "PROJECT_GOALS.md").write_text("# Goals\n\nG1 done.\n", encoding="utf-8")
    (docs / "REQUIREMENTS.md").write_text(
        "# Requirements\n\n| ID | Text |\n|---|---|\n", encoding="utf-8"
    )
    (docs / "SAP_MAPPING.md").write_text("# SAP mapping\n\n…\n", encoding="utf-8")

    src = tmp_path / "src" / "bdx"
    src.mkdir(parents=True)
    (src / "__init__.py").write_text('"""bdx package."""\n', encoding="utf-8")
    (src / "config.py").write_text(
        textwrap.dedent(
            '''
            """Configuration."""
            from pydantic_settings import BaseSettings, SettingsConfigDict


            class SAPSettings(BaseSettings):
                """SAP settings."""

                model_config = SettingsConfigDict(env_prefix="SAP_DB_")

                host: str = "localhost"
            '''
        ).strip(),
        encoding="utf-8",
    )
    routes = src / "api" / "routes"
    routes.mkdir(parents=True)
    (routes / "__init__.py").write_text("", encoding="utf-8")
    (routes / "orders.py").write_text(
        textwrap.dedent(
            '''
            """Orders routes."""
            from fastapi import APIRouter

            router = APIRouter()


            @router.get("/orders")
            def list_orders():
                """List orders."""
                return []
            '''
        ).strip(),
        encoding="utf-8",
    )
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_smoke.py").write_text(
        "def test_smoke():\n    assert 1 + 1 == 2\n", encoding="utf-8"
    )
    return tmp_path


@pytest.fixture
def bad_project(tmp_path: Path) -> Path:
    """A project with several deliberate quality issues."""
    (tmp_path / "README.md").write_text("x", encoding="utf-8")  # tiny stub
    docs = tmp_path / "docs"
    docs.mkdir()
    # PROJECT_STATUS.md missing on purpose
    (docs / "ARCHITECTURE.md").write_text("# Arch\n\nnothing here\n", encoding="utf-8")
    (docs / "SAP_MAPPING.md").write_text("# SAP\n", encoding="utf-8")

    src = tmp_path / "src" / "bdx"
    src.mkdir(parents=True)
    (src / "__init__.py").write_text("", encoding="utf-8")
    (src / "config.py").write_text(
        '"""Config."""\nimport os\n\nX = os.environ.get("BDX_SECRET")\n',
        encoding="utf-8",
    )
    (src / "smelly.py").write_text(
        textwrap.dedent(
            '''
            """Smelly module."""

            def public_fn():
                # TODO fix this later
                print("debug")
                try:
                    pass
                except Exception:
                    pass
            '''
        ).strip(),
        encoding="utf-8",
    )
    return tmp_path


# ── base types ──────────────────────────────────────────────────────────────


def test_status_from_findings():
    assert Status.from_findings([]) is Status.PASSED
    assert Status.from_findings([Finding("X", "m", severity=Severity.INFO)]) is Status.PASSED
    assert Status.from_findings([Finding("X", "m", severity=Severity.WARNING)]) is Status.WARNED
    assert Status.from_findings([Finding("X", "m", severity=Severity.ERROR)]) is Status.FAILED
    # error wins over warning
    both = [Finding("X", "m", severity=Severity.WARNING),
            Finding("Y", "m", severity=Severity.ERROR)]
    assert Status.from_findings(both) is Status.FAILED


def test_check_result_counts():
    r = CheckResult(agent="x")
    r.add("A", "info", severity=Severity.INFO)
    r.add("B", "warn", severity=Severity.WARNING)
    r.add("C", "err", severity=Severity.ERROR)
    assert r.error_count == 1
    assert r.warning_count == 1
    assert r.info_count == 1
    assert r.status is Status.FAILED
    assert not r.passed


def test_finding_render():
    f = Finding("CODE", "msg", location="f.py:3", severity=Severity.WARNING)
    assert "WARNING" in f.render()
    assert "CODE" in f.render()
    assert "[f.py:3]" in f.render()


# ── documentation agent ────────────────────────────────────────────────────


def test_docs_agent_clean_project(sample_project: Path):
    result = DocumentationAgent(DocumentationConfig(root=sample_project)).run()
    # the sample project is well-behaved; no ERROR findings expected
    assert result.status in (Status.PASSED, Status.WARNED)
    assert all(f.severity is not Severity.ERROR for f in result.findings)


def test_docs_agent_missing_status(bad_project: Path):
    result = DocumentationAgent(DocumentationConfig(root=bad_project)).run()
    codes = [f.code for f in result.findings]
    assert "DOC.MISSING_REQUIRED" in codes  # PROJECT_STATUS.md missing
    assert result.status is Status.FAILED


def test_docs_agent_detects_undocumented_routes(bad_project: Path):
    # add a route that is not in ARCHITECTURE.md
    routes = bad_project / "src" / "bdx" / "api" / "routes"
    routes.mkdir(parents=True)
    (routes / "machines.py").write_text(
        '"""Machines."""\nfrom fastapi import APIRouter\n'
        'router = APIRouter()\n\n@router.get("/machines")\ndef list_machines():\n    return []\n',
        encoding="utf-8",
    )
    result = DocumentationAgent(DocumentationConfig(root=bad_project)).run()
    codes = [f.code for f in result.findings]
    assert "DOC.ROUTE_UNDOCUMENTED" in codes


def test_docs_agent_collects_env_vars(sample_project: Path):
    cfg = DocumentationConfig(root=sample_project)
    agent = DocumentationAgent(cfg)
    env = agent._collect_env_vars()
    # SAPSettings has prefix SAP_DB_ and field host -> SAP_DB_HOST
    assert "SAP_DB_HOST" in env
    # must NOT cross-pollinate prefixes from other classes
    assert "BDE_HOST" not in env
    assert "MQTT_HOST" not in env


def test_docs_agent_env_vars_per_class(tmp_path: Path):
    """Two settings classes with different prefixes stay separate."""
    src = tmp_path / "src" / "bdx"
    src.mkdir(parents=True)
    (src / "config.py").write_text(
        textwrap.dedent(
            '''
            """Config."""
            from pydantic_settings import BaseSettings, SettingsConfigDict


            class ASettings(BaseSettings):
                """A."""

                model_config = SettingsConfigDict(env_prefix="A_")

                host: str = "x"


            class BSettings(BaseSettings):
                """B."""

                model_config = SettingsConfigDict(env_prefix="B_")

                port: int = 1
            '''
        ).strip(),
        encoding="utf-8",
    )
    agent = DocumentationAgent(DocumentationConfig(root=tmp_path))
    env = agent._collect_env_vars()
    assert "A_HOST" in env
    assert "B_PORT" in env
    assert "A_PORT" not in env
    assert "B_HOST" not in env


# ── quality agent ──────────────────────────────────────────────────────────


def test_quality_agent_detects_smells(bad_project: Path):
    cfg = QualityConfig(root=bad_project, enable_ruff=False, enable_mypy=False)
    result = QualityAgent(cfg).run()
    codes = {f.code for f in result.findings}
    assert "SMELL.TODO_NO_OWNER" in codes
    assert "SMELL.PRINT_STATEMENT" in codes
    assert "SMELL.EMPTY_EXCEPT" in codes


def test_quality_agent_clean_smells(sample_project: Path):
    cfg = QualityConfig(root=sample_project, enable_ruff=False, enable_mypy=False)
    result = QualityAgent(cfg).run()
    codes = {f.code for f in result.findings}
    assert "SMELL.TODO_NO_OWNER" not in codes
    assert "SMELL.PRINT_STATEMENT" not in codes


def test_quality_agent_print_method_not_flagged(tmp_path: Path):
    """`console.print()` (a method call) must not be flagged as a smell."""
    src = tmp_path / "src" / "bdx"
    src.mkdir(parents=True)
    (src / "__init__.py").write_text('"""pkg."""\n', encoding="utf-8")
    (src / "cli.py").write_text(
        textwrap.dedent(
            '''
            """CLI."""
            from rich.console import Console

            console = Console()


            def show():
                """Show something."""
                console.print("hello")
                console.print("world")
            '''
        ).strip(),
        encoding="utf-8",
    )
    cfg = QualityConfig(root=tmp_path, enable_ruff=False, enable_mypy=False)
    result = QualityAgent(cfg).run()
    prints = [f for f in result.findings if f.code == "SMELL.PRINT_STATEMENT"]
    assert prints == [], f"console.print() should not be flagged: {prints}"


def test_quality_agent_handles_missing_tools(tmp_path: Path):
    # ruff/mypy not installed → INFO/WARNING, never crash
    cfg = QualityConfig(root=tmp_path, enable_ruff=True, enable_mypy=True, enable_smells=False)
    result = QualityAgent(cfg).run()
    # should not raise; agent reports gracefully
    assert result.agent == "quality"


# ── runner ─────────────────────────────────────────────────────────────────


def test_runner_runs_all_agents(sample_project: Path):
    cfg = RunnerConfig(
        root=sample_project,
        run_tests=False,  # avoid shelling out to pytest in unit tests
        enable_mypy=False,
        enable_ruff=False,
    )
    report = AgentRunner(cfg).run()
    agent_names = {r.agent for r in report.results}
    assert agent_names == {"documentation", "quality"}
    # exit code 0 (passed) or 1 (warned) but never 2 (failed) on the clean fixture
    assert report.exit_code in (0, 1)


def test_runner_crash_is_caught(tmp_path: Path):
    """A crashing agent must not take the runner down."""
    from bdx.agents.runner import RunnerReport

    class BoomAgent:
        name = "boom"

        def run(self) -> CheckResult:
            raise RuntimeError("kaboom")

    report = RunnerReport()
    AgentRunner(RunnerConfig(root=tmp_path, run_docs=False, run_tests=False, run_quality=False))._timed(
        report, BoomAgent()
    )
    assert report.results[0].agent == "boom"
    assert report.results[0].error_count == 1
    assert report.status is Status.FAILED


def test_runner_report_json_serialisable(sample_project: Path):
    cfg = RunnerConfig(
        root=sample_project, run_tests=False, enable_mypy=False, enable_ruff=False
    )
    report = AgentRunner(cfg).run()
    data = report.to_dict()
    assert data["status"] in ("passed", "warned", "failed")
    assert "agents" in data and isinstance(data["agents"], list)
    for a in data["agents"]:
        assert "name" in a and "findings" in a


def test_runner_exit_codes():
    r = RunnerReport()
    assert r.exit_code == 0  # empty -> passed
    r.results.append(CheckResult(agent="x"))
    assert r.exit_code == 0
    r.results[0].add("X", "w", severity=Severity.WARNING)
    assert r.exit_code == 1
    r.results[0].add("Y", "e", severity=Severity.ERROR)
    assert r.exit_code == 2
