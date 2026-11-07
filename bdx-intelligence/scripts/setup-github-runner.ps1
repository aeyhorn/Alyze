<#
.SYNOPSIS
    Installiert den GitHub Actions Self-Hosted Runner auf diesem Windows-Desktop.

.DESCRIPTION
    Das Skript:
      1. Laedt den neuesten GitHub Actions Runner fuer Windows x64 herunter.
      2. Konfiguriert ihn fuer das Repository aeyhorn/Alyze.
      3. Installiert ihn als Windows-Dienst (laeuft automatisch beim Systemstart).

    Der Runner benoetigt einen Registrierungstoken, den du einmalig unter
    GitHub -> Repository -> Settings -> Actions -> Runners -> "New self-hosted runner"
    -> Windows -> x64 siehst (Token ist 1 Stunde gueltig).

    Nach der Installation richtest du die 4 Deploy-Secrets in GitHub ein:
      DEV_SSH_HOST        = 192.168.82.33
      DEV_SSH_USER        = docadm
      DEV_SSH_KEY         = Inhalt deines privaten SSH-Schluessels (~/.ssh/id_ed25519)
      DEV_DEPLOY_PATH     = Pfad auf dem DEV-Host, z.B. /opt/bdx-intelligence

.PARAMETER Token
    Registrierungstoken von GitHub (einmalig, 1h gueltig).
    GitHub -> Settings -> Actions -> Runners -> New self-hosted runner -> Token kopieren.

.PARAMETER InstallDir
    Zielverzeichnis fuer den Runner. Standard: C:\actions-runner

.PARAMETER SshKeyPath
    Pfad zu deinem privaten SSH-Schluessel, der SSH-Zugriff auf 192.168.82.33 hat.
    Standard: $HOME\.ssh\id_ed25519

.PARAMETER SshHost
    DEV-Host-IP. Standard: 192.168.82.33

.PARAMETER SshUser
    SSH-Benutzername auf dem DEV-Host. Standard: docadm

.EXAMPLE
    # Token von GitHub holen, dann:
    .\setup-github-runner.ps1 -Token "AXXX..."

    .\setup-github-runner.ps1 -Token "AXXX..." -InstallDir "D:\actions-runner"
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Token,

    [string]$InstallDir = 'C:\actions-runner',

    [string]$SshKeyPath = (Join-Path $HOME '.ssh\id_ed25519'),

    [string]$SshHost = '192.168.82.33',

    [string]$SshUser = 'docadm'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$RepoUrl = 'https://github.com/aeyhorn/Alyze'
$RunnerVersion = '2.321.0'
$RunnerPackage = "actions-runner-win-x64-${RunnerVersion}.zip"
$RunnerUrl = "https://github.com/actions/runner/releases/download/v${RunnerVersion}/${RunnerPackage}"

function Write-Step($m) { Write-Host "`n==> $m" -ForegroundColor Cyan }
function Write-Ok($m)   { Write-Host "  OK  $m" -ForegroundColor Green }
function Write-Warn($m) { Write-Host "  !!  $m" -ForegroundColor Yellow }
function Write-Fail($m) { Write-Host "  XX  $m" -ForegroundColor Red; exit 1 }

# ── Vorauspruefungen ──────────────────────────────────────────────────────────
Write-Step "Vorauspruefungen"

if (-not (Get-Command ssh -ErrorAction SilentlyContinue)) {
    Write-Fail "ssh nicht gefunden. Installiere OpenSSH: Settings -> Apps -> Optional features -> OpenSSH Client"
}
Write-Ok "SSH-Client vorhanden"

if (-not (Test-Path $SshKeyPath)) {
    Write-Warn "SSH-Key nicht gefunden: $SshKeyPath"
    Write-Warn "Erstelle ihn mit:  ssh-keygen -t ed25519 -f $SshKeyPath"
    Write-Warn "Dann den oeffentlichen Key auf $SshHost hinzufuegen:  ssh-copy-id -i ${SshKeyPath}.pub ${SshUser}@${SshHost}"
    Write-Fail "Bitte SSH-Key bereitstellen und Skript erneut ausfuehren."
}
Write-Ok "SSH-Key gefunden: $SshKeyPath"

# ── SSH-Verbindung testen ─────────────────────────────────────────────────────
Write-Step "SSH-Verbindung zu ${SshUser}@${SshHost} testen"
$sshTest = & ssh -i $SshKeyPath -o ConnectTimeout=10 -o StrictHostKeyChecking=no `
    -o BatchMode=yes "${SshUser}@${SshHost}" "echo OK" 2>&1
if ($LASTEXITCODE -ne 0 -or $sshTest -notlike '*OK*') {
    Write-Warn "SSH-Test fehlgeschlagen: $sshTest"
    Write-Warn "Stelle sicher, dass der oeffentliche Key (~\.ssh\id_ed25519.pub) auf"
    Write-Warn "${SshHost} in ~/.ssh/authorized_keys von Benutzer '${SshUser}' eingetragen ist."
    Write-Fail "SSH-Verbindung konnte nicht hergestellt werden."
}
Write-Ok "SSH-Verbindung zu ${SshHost} erfolgreich"

# ── Runner herunterladen ──────────────────────────────────────────────────────
Write-Step "Runner v${RunnerVersion} herunterladen"

New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
$zipPath = Join-Path $InstallDir $RunnerPackage

if (Test-Path $zipPath) {
    Write-Ok "Paket bereits vorhanden, ueberspringe Download: $zipPath"
} else {
    Write-Host "  Lade herunter: $RunnerUrl"
    Invoke-WebRequest -Uri $RunnerUrl -OutFile $zipPath -UseBasicParsing
    Write-Ok "Heruntergeladen: $zipPath"
}

Write-Step "Runner entpacken nach $InstallDir"
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::ExtractToDirectory($zipPath, $InstallDir)
Write-Ok "Entpackt"

# ── Runner konfigurieren ──────────────────────────────────────────────────────
Write-Step "Runner konfigurieren (Repo: $RepoUrl)"
$configCmd = Join-Path $InstallDir 'config.cmd'
& $configCmd `
    --url $RepoUrl `
    --token $Token `
    --name "desktop-$(hostname)" `
    --labels "self-hosted,linux,windows-desktop" `
    --work "_work" `
    --unattended
if ($LASTEXITCODE -ne 0) { Write-Fail "config.cmd fehlgeschlagen." }
Write-Ok "Runner konfiguriert"

# ── Als Windows-Dienst installieren ──────────────────────────────────────────
Write-Step "Als Windows-Dienst installieren (automatischer Start)"
$svcCmd = Join-Path $InstallDir 'svc.cmd'
& $svcCmd install
if ($LASTEXITCODE -ne 0) { Write-Fail "svc.cmd install fehlgeschlagen." }
& $svcCmd start
if ($LASTEXITCODE -ne 0) { Write-Fail "svc.cmd start fehlgeschlagen." }
Write-Ok "Dienst gestartet"

# ── SSH-Key als Umgebungsvariable fuer den Dienst setzen ─────────────────────
Write-Step "SSH-Key-Pfad in Dienst-Umgebung eintragen"
$sshKeyContent = Get-Content $SshKeyPath -Raw
$svcName = "actions.runner.aeyhorn-Alyze.*"
$runner = Get-Service -Name $svcName -ErrorAction SilentlyContinue
if ($runner) {
    # Lege den Key als Datei ab, die der Runner-Prozess lesen kann
    $sshDir = Join-Path $InstallDir '.ssh'
    New-Item -ItemType Directory -Path $sshDir -Force | Out-Null
    $deployKey = Join-Path $sshDir 'deploy_key'
    Set-Content -Path $deployKey -Value $sshKeyContent -NoNewline
    # Berechtigungen einschraenken (nur aktueller User)
    $acl = Get-Acl $deployKey
    $acl.SetAccessRuleProtection($true, $false)
    $rule = New-Object System.Security.AccessControl.FileSystemAccessRule(
        [System.Security.Principal.WindowsIdentity]::GetCurrent().Name,
        'FullControl', 'Allow'
    )
    $acl.SetAccessRule($rule)
    Set-Acl -Path $deployKey -AclObject $acl
    Write-Ok "Deploy-Key abgelegt: $deployKey"
} else {
    Write-Warn "Dienst nicht gefunden, SSH-Key manuell ablegen unter: $InstallDir\.ssh\deploy_key"
}

# ── Naechste Schritte ausgeben ────────────────────────────────────────────────
Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host " Runner erfolgreich installiert!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host " Jetzt noch 4 GitHub-Secrets setzen:" -ForegroundColor Yellow
Write-Host " GitHub -> aeyhorn/Alyze -> Settings -> Secrets -> Actions -> New repository secret"
Write-Host ""
Write-Host "   DEV_SSH_HOST     = $SshHost"
Write-Host "   DEV_SSH_USER     = $SshUser"
Write-Host "   DEV_SSH_KEY      = (Inhalt von $SshKeyPath)"
Write-Host "   DEV_DEPLOY_PATH  = /opt/bdx-intelligence"
Write-Host ""
Write-Host " Dann den PR mergen - der Deploy laeuft automatisch." -ForegroundColor Cyan
Write-Host ""
Write-Host " Runner-Status pruefen:"
Write-Host "   Get-Service 'actions.runner.*' | Select Name, Status"
Write-Host ""
Write-Host " Dienst stoppen/starten:"
Write-Host "   cd $InstallDir"
Write-Host "   .\svc.cmd stop"
Write-Host "   .\svc.cmd start"
