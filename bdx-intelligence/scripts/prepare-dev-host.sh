#!/usr/bin/env bash
# prepare-dev-host.sh — Provision the DEV host (192.168.82.33) as a GitHub Actions
# self-hosted runner for aeyhorn/Alyze, plus Docker + compose plugin.
#
# Usage (from your workstation):
#   ssh docadm@192.168.82.33 \
#     "RUNNER_TOKEN=<token> bash <(curl -fsSL https://raw.githubusercontent.com/aeyhorn/Alyze/main/bdx-intelligence/scripts/prepare-dev-host.sh)"
#
# Or locally on the host:
#   RUNNER_TOKEN=<token> bash prepare-dev-host.sh
#
# The RUNNER_TOKEN is a short-lived (~1h) registration token from
#   https://github.com/aeyhorn/Alyze/settings/actions/runners/new
# (Settings → Actions → Runners → "New self-hosted runner" → Linux x64 → copy the token)
#
# Idempotent: re-running with a fresh token re-registers; existing service is
# removed first. The runner runs as user "runner" (created if missing) and is
# installed as a systemd service that auto-starts on boot.
#
# Safety: refuses to run as root directly; uses sudo only when needed.

set -euo pipefail

REPO_FULL="aeyhorn/Alyze"
RUNNER_USER="runner"
RUNNER_HOME="/home/${RUNNER_USER}/actions-runner"
RUNNER_SERVICE="actions.runner.${REPO_FULL//\//.}.$(hostname)"
RUNNER_LABELS="self-hosted,linux,dev,lan"
RUNNER_ARCH="x64"  # 192.168.82.33 is x86_64

log()  { printf '\033[1;34m[prepare]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[warn]\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31m[err]\033[0m %s\n' "$*" >&2; exit 1; }

# --- preflight ---------------------------------------------------------------

[ "$(id -u)" -eq 0 ] && die "Run as a normal user (docadm), not root. The script uses sudo internally."
command -v sudo >/dev/null || die "sudo is required."

if [ -z "${RUNNER_TOKEN:-}" ]; then
  die "RUNNER_TOKEN env var is required. Get it from:
       https://github.com/${REPO_FULL}/settings/actions/runners/new"
fi

# --- 1. base packages --------------------------------------------------------

log "Installing base packages (curl, ca-certificates, jq, tar)..."
sudo apt-get update -qq
sudo apt-get install -y -qq curl ca-certificates jq tar gzip >/dev/null

# --- 2. Docker (if missing) --------------------------------------------------

if ! command -v docker >/dev/null 2>&1; then
  log "Docker not found — installing Docker Engine + compose plugin..."
  curl -fsSL https://get.docker.com | sudo sh
  sudo usermod -aG docker "$RUNNER_USER" 2>/dev/null || true
  sudo systemctl enable --now docker
else
  log "Docker already present: $(docker --version)"
fi

if ! docker compose version >/dev/null 2>&1; then
  warn "docker compose plugin missing — installing..."
  sudo apt-get install -y -qq docker-compose-plugin >/dev/null || \
    die "Failed to install docker-compose-plugin. Install manually."
fi

# --- 3. runner user ----------------------------------------------------------

if ! id "$RUNNER_USER" >/dev/null 2>&1; then
  log "Creating user '${RUNNER_USER}'..."
  sudo adduser --disabled-password --gecos "" "$RUNNER_USER"
  sudo usermod -aG docker "$RUNNER_USER"
else
  log "User '${RUNNER_USER}' already exists."
fi

# --- 4. download runner package (idempotent) --------------------------------

RUNNER_VERSION="$(curl -fsSL https://api.github.com/repos/actions/runner/releases/latest | jq -r .tag_name | sed 's/^v//')"
RUNNER_TARBALL="actions-runner-linux-${RUNNER_ARCH}-${RUNNER_VERSION}.tar.gz"

log "Downloading actions/runner v${RUNNER_VERSION} (${RUNNER_ARCH})..."

if [ ! -d "$RUNNER_HOME" ]; then
  sudo -u "$RUNNER_USER" mkdir -p "$RUNNER_HOME"
else
  log "Existing runner dir found — removing old install."
  # stop + unregister old service if present
  if sudo systemctl list-unit-files | grep -q "${RUNNER_SERVICE}.service"; then
    log "Stopping + removing old systemd service..."
    sudo systemctl stop "${RUNNER_SERVICE}.service" 2>/dev/null || true
    sudo systemctl disable "${RUNNER_SERVICE}.service" 2>/dev/null || true
    sudo rm -f "/etc/systemd/system/${RUNNER_SERVICE}.service"
    sudo systemctl daemon-reload
  fi
  sudo rm -rf "${RUNNER_HOME:?}/"*
fi

sudo -u "$RUNNER_USER" bash -c "
  cd '$RUNNER_HOME'
  curl -fsSL -o '$RUNNER_TARBALL' 'https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/${RUNNER_TARBALL}'
  tar xzf '$RUNNER_TARBALL'
  rm -f '$RUNNER_TARBALL'
"

# --- 5. configure + register ------------------------------------------------

log "Configuring runner (labels: ${RUNNER_LABELS})..."

sudo -u "$RUNNER_USER" bash -c "
  cd '$RUNNER_HOME'
  ./config.sh --url 'https://github.com/${REPO_FULL}' \
              --token '$RUNNER_TOKEN' \
              --name '$(hostname)-dev' \
              --labels '${RUNNER_LABELS}' \
              --work '_work' \
              --unattended \
              --replace
"

# --- 6. install + start systemd service --------------------------------------

log "Installing systemd service '${RUNNER_SERVICE}'..."
sudo -u "$RUNNER_USER" bash -c "cd '$RUNNER_HOME' && ./svc.sh install"
sudo systemctl daemon-reload
sudo systemctl enable --now "${RUNNER_SERVICE}.service"

# --- 7. verify --------------------------------------------------------------

sleep 3
if sudo systemctl is-active --quiet "${RUNNER_SERVICE}.service"; then
  log "✅ Runner service is ACTIVE."
else
  warn "Service not active yet — check:"
  warn "  sudo systemctl status ${RUNNER_SERVICE}.service"
  warn "  sudo journalctl -u ${RUNNER_SERVICE}.service -n 50 --no-pager"
fi

log "Verifying on GitHub..."
RUNNER_ID=$(curl -fsSL -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/${REPO_FULL}/actions/runners" \
  | jq -r '.runners[] | select(.name=="'"$(hostname)-dev"'") | .id' 2>/dev/null || echo "")

if [ -n "$RUNNER_ID" ]; then
  log "✅ Runner registered on GitHub (id: ${RUNNER_ID})"
else
  warn "Could not confirm registration via API (public read may be off)."
  warn "Check manually: https://github.com/${REPO_FULL}/settings/actions/runners"
fi

log "Done. Labels available to workflows: ${RUNNER_LABELS}"
log "Workflows can now target: runs-on: [self-hosted, linux]  (or [self-hosted, dev])"
