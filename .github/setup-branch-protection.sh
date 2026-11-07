#!/usr/bin/env bash
# Setup branch protection for `main` on the BDX-Intelligence repo.
#
# Run once after the first push to GitHub:
#   gh auth login
#   bash .github/setup-branch-protection.sh
#
# Requires the GitHub CLI (gh) with admin scope on the repo.
# Idempotent: re-running updates the existing rule.
set -euo pipefail

REPO="${GITHUB_REPOSITORY:-aeyhorn/Alyze}"
BRANCH="main"

echo "Setting up branch protection on '$BRANCH' for $REPO..."

gh api \
  -X PUT \
  "repos/$REPO/branches/$BRANCH/protection" \
  -F "required_status_checks[strict]=true" \
  -F "required_status_checks[contexts][]=Lint & Format (ruff, advisory)" \
  -F "required_status_checks[contexts][]=Type Check (mypy, advisory)" \
  -F "required_status_checks[contexts][]=Tests (pytest + coverage)" \
  -F "required_status_checks[contexts][]=Docker Build Smoke Test" \
  -F "enforce_admins=false" \
  -F "required_pull_request_reviews[dismiss_stale_reviews]=true" \
  -F "required_pull_request_reviews[require_code_owner_reviews]=true" \
  -F "required_pull_request_reviews[required_approving_review_count]=1" \
  -F "restrictions=" \
  -F "required_linear_history=true" \
  -F "allow_force_pushes=false" \
  -F "allow_deletions=false" \
  --silent

echo "Branch protection configured:"
echo "  - 1 approving review (CODEOWNER for sap_sl/, db/, alembic/)"
echo "  - CI checks required: ruff, mypy, pytest+coverage, docker build"
echo "  - linear history, no force push, no branch deletion"
echo "  - strict status checks (PR must be up to date before merge)"
