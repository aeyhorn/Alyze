"""PR review runner for BDX-Intelligence CI.

Runs two Cursor cloud agents on a pull-request diff and posts the verdicts as
a single PR comment:

  1. Bug review       – finds correctness / regression risks in the diff.
  2. Security review  – finds secrets, injection, auth issues in the diff.

Usage (called from .github/workflows/pr-review.yml):

    python scripts/pr_review.py \\
        --pr-number "$PR_NUMBER" \\
        --repo "$GITHUB_REPOSITORY" \\
        --diff-file pr.diff

Requires:
    * CURSOR_API_KEY env var (Cursor cloud agent key).
    * `gh` CLI authenticated (to post the comment).
    * `cursor-sdk` installed (`pip install cursor-sdk`).

If CURSOR_API_KEY is missing, the script exits 0 with a skip notice so the
workflow stays green — review is opt-in via the repo secret.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from typing import Optional


BUG_PROMPT = """\
You are a code reviewer focused on correctness and regressions.

Review the following pull-request diff for the BDX-Intelligence project.
The project is a SAP Business One read-only collector with a Service-Layer
write channel guarded by SL_DRY_RUN. Hard rules (flag any violation):
  * MSSQL channel is read-only (no INSERT/UPDATE/DELETE/DDL).
  * SL writes go through sap_sl/operations.py::_exec and audit to sl_operations.
  * SQL must be parameterized (text() with :param binds), no string interpolation.
  * No secrets in code; SL_DRY_RUN=false must never appear in committed files.
  * order_state is fingerprint-upsert, one row per order; order_snapshots is
    history-on-change only.
  * Events are idempotent by event_id UUID; never reuse IDs.
  * SAP status codes: P=Planned, R=Released, L=Closed, C=Cancelled.

Find: logic errors, off-by-one, wrong status mapping, missing idempotency,
broken fingerprint upsert, missing audit, unhandled exceptions, race conditions,
and any violation of the hard rules.

Output a concise bullet list. For each finding: file:line, severity (blocker/
major/minor/nit), one-sentence problem, one-sentence fix. If nothing material,
say "No blocker-level issues." Do not refactor; do not write code.
"""

SECURITY_PROMPT = """\
You are a security reviewer.

Review the following pull-request diff for the BDX-Intelligence project.
Focus on: leaked secrets/credentials, SQL injection, command injection,
SSRF, missing auth on endpoints, unsafe deserialization, path traversal,
TLS verification disabled without justification, and any change that weakens
the SL_DRY_RUN guard or the MSSQL read-only guard.

Output a concise bullet list. For each finding: file:line, severity
(critical/high/medium/low), one-sentence problem, one-sentence remediation.
If nothing material, say "No critical/high issues."
"""


def _run_review(prompt: str, diff: str) -> str:
    """Run one Cursor cloud review agent on the diff and return its text."""
    try:
        from cursor_sdk import Agent, AgentOptions, CloudAgentOptions
    except ImportError:
        return "[cursor-sdk not installed — skipping SDK review]"

    full_prompt = f"{prompt}\n\nDIFF:\n```diff\n{diff[:200000]}\n```\n"
    try:
        result = Agent.prompt(
            full_prompt,
            AgentOptions(
                api_key=os.environ["CURSOR_API_KEY"],
                model="composer-2.5",
                cloud=CloudAgentOptions(repos=[]),
            ),
        )
    except Exception as exc:  # noqa: BLE001
        return f"[review agent failed: {exc}]"
    return result.result or "[no text returned]"


def _post_comment(repo: str, pr_number: int, body: str) -> None:
    subprocess.run(
        [
            "gh", "pr", "comment", str(pr_number),
            "--repo", repo,
            "--body", body,
        ],
        check=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pr-number", type=int, required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--diff-file", required=True)
    args = parser.parse_args()

    if not os.environ.get("CURSOR_API_KEY"):
        print("CURSOR_API_KEY not set — skipping SDK review (opt-in).")
        _post_comment(
            args.repo, args.pr_number,
            "## Automated review\n\n_skipped — set `CURSOR_API_KEY` repo secret "
            "to enable Cursor bug + security review._",
        )
        return 0

    with open(args.diff_file, encoding="utf-8") as fh:
        diff = fh.read()
    if not diff.strip():
        print("Empty diff — nothing to review.")
        return 0

    print(f"Running bug review on PR #{args.pr_number} ({len(diff)} bytes)...")
    bug = _run_review(BUG_PROMPT, diff)
    print("Running security review...")
    security = _run_review(SECURITY_PROMPT, diff)

    body = (
        "## Automated review (Cursor SDK)\n\n"
        "### Bug review\n\n"
        f"{bug}\n\n"
        "### Security review\n\n"
        f"{security}\n"
    )
    _post_comment(args.repo, args.pr_number, body)
    print("Review comment posted.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
