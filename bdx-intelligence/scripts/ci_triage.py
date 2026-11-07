"""Triage a failed CI run: fetch failed job logs, run a Cursor agent to
produce a root-cause summary, and post it as a comment on the associated PR.

Called from .github/workflows/ci-triage.yml.

Exit codes:
    0  comment posted (or skipped: no PR, no CURSOR_API_KEY, no failures)
    1  startup error
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from typing import Optional


TRIAGE_PROMPT = """\
You triage failed CI runs for the BDX-Intelligence project (Python 3.11,
FastAPI, SQLAlchemy, pytest, ruff, mypy, Docker).

Given the failed job logs below, produce a concise root-cause comment with
these sections:
  ## Root cause
  One or two sentences naming the actual cause (not the symptom).
  ## Evidence
  The exact log line(s) that prove it, quoted.
  ## Likely fix
  One or two sentences naming the file + change to make. Do not write code.
  ## Confidence
  high / medium / low + one reason.

If the logs are ambiguous, say so and list the 2-3 most likely causes ranked.
Be concise. Do not invent file paths or line numbers not present in the logs.
"""


def _gh_json(*args: str) -> dict:
    out = subprocess.run(
        ["gh", *args], check=True, capture_output=True, text=True
    ).stdout
    return json.loads(out)


def _find_pr_for_run(repo: str, head_sha: str) -> Optional[int]:
    out = subprocess.run(
        ["gh", "pr", "list", "--repo", repo, "--state", "open",
         "--search", head_sha, "--json", "number,headRefOid"],
        check=True, capture_output=True, text=True
    ).stdout
    prs = json.loads(out)
    for pr in prs:
        if pr.get("headRefOid") == head_sha:
            return pr["number"]
    return None


def _failed_jobs(repo: str, run_id: str) -> list[dict]:
    jobs = _gh_json("run", "view", run_id, "--repo", repo, "--json", "jobs")
    return [j for j in jobs.get("jobs", []) if j.get("conclusion") == "failure"]


def _job_log(repo: str, job_id: int, max_bytes: int = 60000) -> str:
    out = subprocess.run(
        ["gh", "run", "view", "--repo", repo, "--job", str(job_id), "--log-failed"],
        check=False, capture_output=True, text=True
    ).stdout
    return out[-max_bytes:]


def _triage(logs: str) -> str:
    if not os.environ.get("CURSOR_API_KEY"):
        return (
            "_CURSOR_API_KEY not set — automated triage skipped. "
            "Inspect the failed job logs manually._"
        )
    try:
        from cursor_sdk import Agent, AgentOptions, CloudAgentOptions
    except ImportError:
        return "_cursor-sdk not installed — automated triage skipped._"
    prompt = f"{TRIAGE_PROMPT}\n\nFAILED JOB LOGS:\n```\n{logs[:120000]}\n```\n"
    try:
        result = Agent.prompt(
            prompt,
            AgentOptions(
                api_key=os.environ["CURSOR_API_KEY"],
                model="composer-2.5",
                cloud=CloudAgentOptions(repos=[]),
            ),
        )
        return result.result or "_no triage produced._"
    except Exception as exc:  # noqa: BLE001
        return f"_triage agent failed: {exc}_"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--repo", required=True)
    args = parser.parse_args()

    run = _gh_json("run", "view", args.run_id, "--repo", args.repo,
                   "--json", "headSha,displayTitle")
    head_sha = run["headSha"]
    pr_number = _find_pr_for_run(args.repo, head_sha)
    if not pr_number:
        print(f"No open PR for sha {head_sha} — nothing to triage.")
        return 0

    jobs = _failed_jobs(args.repo, args.run_id)
    if not jobs:
        print("No failed jobs — nothing to triage.")
        return 0

    logs = "\n\n--- JOB: {} ---\n{}".format(
        jobs[0]["name"], _job_log(args.repo, jobs[0]["databaseId"])
    )
    for j in jobs[1:5]:
        logs += "\n\n--- JOB: {} ---\n{}".format(
            j["name"], _job_log(args.repo, j["databaseId"])
        )

    print(f"Triaging {len(jobs)} failed job(s) for PR #{pr_number}...")
    triage = _triage(logs)
    body = (
        "## CI failure triage (automated)\n\n"
        f"{triage}\n\n"
        f"_Run: [{args.run_id}]({os.environ.get('GITHUB_SERVER_URL','')}/"
        f"{args.repo}/actions/runs/{args.run_id})_"
    )
    subprocess.run(
        ["gh", "pr", "comment", str(pr_number), "--repo", args.repo, "--body", body],
        check=True,
    )
    print("Triage comment posted.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
