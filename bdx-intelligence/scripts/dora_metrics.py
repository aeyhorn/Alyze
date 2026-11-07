"""Compute DORA-style dev metrics for BDX-Intelligence from GitHub data and
write them to docs/dora-metrics.md.

Metrics (last 30 days):
  * Deploy frequency      — merges to main per day (proxy: workflow runs of
                            deploy-dev.yml that succeeded)
  * Cycle time             — PR open → merge median, in hours
  * MTTR                   — median time from a red CI run to the next green
                            run on the same branch, in minutes
  * Change failure rate    — share of deploy-dev runs that failed
  * Test flakiness         — share of CI runs that failed then passed on retry
                            without a code change (heuristic)

Usage (called from .github/workflows/dora.yml weekly):

    python scripts/dora_metrics.py --repo aeyhorn/Alyze --out docs/dora-metrics.md

Commits the updated file via the workflow (git auto-commit action).
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
from datetime import UTC, datetime, timedelta


def _gh_json(*args: str) -> object:
    out = subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout
    return json.loads(out)


def _gh_api(path: str) -> object:
    out = subprocess.run(["gh", "api", path], check=True, capture_output=True, text=True).stdout
    return json.loads(out)


def _merged_prs(repo: str, since: datetime) -> list[dict]:
    since_iso = since.isoformat()
    out = subprocess.run(
        [
            "gh",
            "pr",
            "list",
            "--repo",
            repo,
            "--state",
            "closed",
            "--search",
            f"is:pr is:merged merged:>{since_iso}",
            "--json",
            "number,createdAt,mergedAt,title,url",
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return json.loads(out)


def _workflow_runs(repo: str, workflow: str, since: datetime) -> list[dict]:
    since_iso = since.isoformat()
    runs: list[dict] = []
    page = 1
    while True:
        data = _gh_api(
            f"repos/{repo}/actions/workflows/{workflow}/runs"
            f"?created=>{since_iso}&per_page=100&page={page}"
        )
        batch = data.get("workflow_runs", [])
        if not batch:
            break
        runs.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return runs


def _fmt_dt(s: str) -> str:
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return s


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--out", default="docs/dora-metrics.md")
    parser.add_argument("--days", type=int, default=30)
    args = parser.parse_args()

    now = datetime.now(UTC)
    since = now - timedelta(days=args.days)

    prs = _merged_prs(repo=args.repo, since=since)
    cycle_hours: list[float] = []
    for pr in prs:
        try:
            created = datetime.fromisoformat(pr["createdAt"].replace("Z", "+00:00"))
            merged = datetime.fromisoformat(pr["mergedAt"].replace("Z", "+00:00"))
            cycle_hours.append((merged - created).total_seconds() / 3600.0)
        except Exception:
            continue

    deploys = _workflow_runs(args.repo, "deploy-dev.yml", since)
    deploy_count = len(deploys)
    deploy_success = sum(1 for r in deploys if r.get("conclusion") == "success")
    deploy_failed = sum(1 for r in deploys if r.get("conclusion") == "failure")
    change_failure_rate = (deploy_failed / deploy_count * 100.0) if deploys else 0.0
    deploy_freq_per_day = deploy_count / args.days if args.days else 0.0
    ci_runs = _workflow_runs(args.repo, "ci.yml", since)
    ci_failed = [r for r in ci_runs if r.get("conclusion") == "failure"]
    ci_total = len(ci_runs)
    flakiness = (len(ci_failed) / ci_total * 100.0) if ci_total else 0.0

    # MTTR: for each branch with a failed ci run, time to next success.
    by_branch: dict[str, list[tuple[datetime, str]]] = {}
    for r in sorted(ci_runs, key=lambda x: x["created_at"]):
        try:
            ts = datetime.fromisoformat(r["created_at"].replace("Z", "+00:00"))
        except Exception:
            continue
        by_branch.setdefault(r.get("head_branch", "?"), []).append((ts, r.get("conclusion", "")))
    mttr_minutes: list[float] = []
    for _branch, runs in by_branch.items():
        for i, (ts, concl) in enumerate(runs):
            if concl == "failure":
                for ts2, concl2 in runs[i + 1 :]:
                    if concl2 == "success":
                        mttr_minutes.append((ts2 - ts).total_seconds() / 60.0)
                        break

    median_cycle = statistics.median(cycle_hours) if cycle_hours else 0.0
    median_mttr = statistics.median(mttr_minutes) if mttr_minutes else 0.0

    lines = [
        "# DORA Metrics — BDX-Intelligence",
        "",
        f"_Last 30 days (since {since.strftime('%Y-%m-%d')}, generated {now.strftime('%Y-%m-%d %H:%M')} UTC)_",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Deploy frequency | {deploy_freq_per_day:.2f} / day ({deploy_count} deploys, {deploy_success} ok) |",
        f"| Cycle time (median) | {median_cycle:.1f} h |",
        f"| MTTR (median) | {median_mttr:.1f} min |",
        f"| Change failure rate | {change_failure_rate:.1f} % |",
        f"| CI flakiness (failed runs) | {flakiness:.1f} % ({len(ci_failed)}/{ci_total}) |",
        f"| Merged PRs | {len(prs)} |",
        "",
        "## Recent deploys",
        "",
        "| When | Conclusion | Run |",
        "|---|---|---|",
    ]
    for r in deploys[-10:]:
        lines.append(
            f"| {_fmt_dt(r['created_at'])} | {r.get('conclusion', '?')} | [run]({r['html_url']}) |"
        )
    lines += ["", "## Recent merged PRs", "", "| # | Title | Cycle (h) |", "|---|---|---|"]
    for pr in prs[-10:]:
        try:
            created = datetime.fromisoformat(pr["createdAt"].replace("Z", "+00:00"))
            merged = datetime.fromisoformat(pr["mergedAt"].replace("Z", "+00:00"))
            ch = (merged - created).total_seconds() / 3600.0
            lines.append(f"| {pr['number']} | {pr['title'][:60]} | {ch:.1f} |")
        except Exception:
            continue

    content = "\n".join(lines) + "\n"
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(content)
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
