<#
.SYNOPSIS
    Setzt die 4 GitHub-Secrets fuer den DEV-Deploy automatisch via gh CLI.

.DESCRIPTION
    Liest den SSH-Key aus einer lokalen Datei und setzt alle 4 erforderlichen
    Secrets in einem Zug. Benoetigt die GitHub CLI (gh) mit einem PAT, der
    den Scope "repo" oder "secrets" hat.

    Installation gh CLI: https://cli.github.com
    Authentifizierung:   gh auth login

.PARAMETER SshKeyPath
    Pfad zum privaten SSH-Schluessel fuer den Zugriff auf den DEV-Host.
    Standard: $HOME\.ssh\id_ed25519

.PARAMETER SshHost
    IP/Hostname des DEV-Hosts. Standard: 192.168.82.33

.PARAMETER SshUser
    SSH-Benutzername auf dem DEV-Host. Standard: docadm

.PARAMETER DeployPath
    Verzeichnis auf dem DEV-Host, das docker-compose.yml + .env enthaelt.
    Standard: /opt/bdx-intelligence

.EXAMPLE
    .\set-github-secrets.ps1

    .\set-github-secrets.ps1 -SshKeyPath "C:\Users\ich\.ssh\id_rsa" -DeployPath "/home/docadm/bdx"
#>
[CmdletBinding()]
param(
    [string]$SshKeyPath = (Join-Path $HOME '.ssh\id_ed25519'),
    [string]$SshHost = '192.168.82.33',
    [string]$SshUser = 'docadm',
    [string]$DeployPath = '/opt/bdx-intelligence'
)

$ErrorActionPreference = 'Stop'
$Repo = 'aeyhorn/Alyze'

function Write-Step($m) { Write-Host "`n==> $m" -ForegroundColor Cyan }
function Write-Ok($m)   { Write-Host "  OK  $m" -ForegroundColor Green }
function Write-Fail($m) { Write-Host "  XX  $m" -ForegroundColor Red; exit 1 }

# ── Vorauspruefungen ──────────────────────────────────────────────────────────
Write-Step "Vorauspruefungen"

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Fail "gh CLI nicht gefunden. Installieren: https://cli.github.com"
}
Write-Ok "gh CLI vorhanden"

$authStatus = & gh auth status 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Fail "Nicht eingeloggt. Ausfuehren: gh auth login"
}
Write-Ok "gh authentifiziert"

if (-not (Test-Path $SshKeyPath)) {
    Write-Fail "SSH-Key nicht gefunden: $SshKeyPath"
}
Write-Ok "SSH-Key gefunden: $SshKeyPath"

# ── Secrets setzen ───────────────────────────────────────────────────────────
Write-Step "Secrets setzen fuer $Repo"

$secrets = @{
    DEV_SSH_HOST    = $SshHost
    DEV_SSH_USER    = $SshUser
    DEV_SSH_KEY     = (Get-Content $SshKeyPath -Raw)
    DEV_DEPLOY_PATH = $DeployPath
}

foreach ($name in $secrets.Keys) {
    Write-Host "  Setze $name ..."
    $value = $secrets[$name]
    $value | & gh secret set $name --repo $Repo
    if ($LASTEXITCODE -ne 0) {
        Write-Fail "Konnte Secret '$name' nicht setzen. Pruefe gh-Berechtigungen (Scope: repo)."
    }
    Write-Ok "$name gesetzt"
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host " Alle 4 Secrets erfolgreich gesetzt!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host " Naechster Schritt: PR mergen unter"
Write-Host " https://github.com/aeyhorn/Alyze/pull/6" -ForegroundColor Cyan
Write-Host ""
Write-Host " Dann laeuft 'Deploy to DEV' automatisch durch."
