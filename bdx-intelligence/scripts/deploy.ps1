<#
.SYNOPSIS
    bdx-intelligence – Deployment auf remote-prod (DEV-Host 192.168.82.33).

    ./scripts/deploy.ps1 zielt immer auf den Docker-Context remote-prod
    (oder BDX_DOCKER_CONTEXT). Lokale Contexts (default, desktop-linux)
    werden abgelehnt.

.DESCRIPTION
    Services: collector, api (und migrate als one-shot).
    Compose-File: bdx-intelligence/docker-compose.yml.
    "up" baut zuerst das Image (docker compose build) und startet dann
    collector + api neu. migrate läuft via depends_on automatisch mit.
    Der Event-Store (PostgreSQL) bleibt unangetastet (läuft als separater
    Container bdx-intelligence-postgres auf dem Docker-Host).

    Der Docker-Context remote-prod zeigt per SSH auf docadm@192.168.82.33.
    Alle docker-Befehle laufen lokal, wirken aber auf den remote Docker-Daemon.

.PARAMETER Action
    up | down | restart | status | logs | migrate

.PARAMETER NoBuild
    Image-Build überspringen (nur bei up/relevant).

.PARAMETER Follow
    Bei logs: Ausgabe folgen (-f).

.PARAMETER SkipHealth
    HTTP-Prüfung von /health/live überspringen.

.PARAMETER Local
    Notausgang: lokalen Docker-Context erlauben. Normal ist remote-prod.

.PARAMETER DockerContext
    Docker-Context (Standard: BDX_DOCKER_CONTEXT oder remote-prod).

.PARAMETER Services
    Welche Services starten (Standard: collector api). Bei migrate ignoriert.

.EXAMPLE
    ./scripts/deploy.ps1
    ./scripts/deploy.ps1 up -NoBuild
    ./scripts/deploy.ps1 status
    ./scripts/deploy.ps1 logs -Follow
    ./scripts/deploy.ps1 down
    ./scripts/deploy.ps1 migrate
#>
[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet('up', 'down', 'restart', 'status', 'logs', 'migrate')]
    [string]$Action = 'up',

    [switch]$NoBuild,
    [switch]$Follow,
    [switch]$SkipHealth,
    [switch]$Local,
    [string]$DockerContext = '',
    [string[]]$Services = @('collector', 'api'),
    [ValidateRange(0, 10)]
    [int]$BuildRetryCount = 2,
    [ValidateRange(0, 10)]
    [int]$UpRetryCount = 2
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

# bdx-intelligence/scripts/deploy.ps1  ->  bdx-intelligence/
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$ComposeFile  = Join-Path $ProjectRoot 'docker-compose.yml'
$EnvFile      = Join-Path $ProjectRoot '.env'
$StateDir     = Join-Path $ProjectRoot '.runtime'
$LastDeployShaFile = Join-Path $StateDir 'last-deploy-sha'
$LastDeployAtFile  = Join-Path $StateDir 'last-deploy-at'
$ApiContainer = 'bdx-intelligence-api'
$PublishPort  = if ($env:API_PORT) { $env:API_PORT } else { '8085' }
$HealthPath   = '/health/live'

function Write-Step($m) { Write-Host "==> $m" -ForegroundColor Cyan }
function Write-Ok($m)    { Write-Host "  OK  $m" -ForegroundColor Green }
function Write-Warn2($m) { Write-Host "  !!  $m" -ForegroundColor Yellow }
function Write-Err($m)  { Write-Host "  XX  $m" -ForegroundColor Red }

function Get-DeployTimestamp { return (Get-Date).ToString('yyyy-MM-dd HH:mm:ss zzz') }

function Write-DeployCompleted {
    param(
        [Parameter(Mandatory = $true)][string]$Message,
        [switch]$Persist
    )
    $ts = Get-DeployTimestamp
    if ($Persist) {
        New-Item -ItemType Directory -Path $StateDir -Force | Out-Null
        [System.IO.File]::WriteAllText($LastDeployAtFile, "$ts`n")
        $headSha = ''
        $prev = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        try { $headSha = (& git -C $ProjectRoot rev-parse HEAD 2>$null).Trim() } finally { $ErrorActionPreference = $prev }
        if (-not [string]::IsNullOrWhiteSpace($headSha)) {
            [System.IO.File]::WriteAllText($LastDeployShaFile, "$headSha`n")
        }
    }
    Write-Ok ("{0} at {1}" -f $Message, $ts)
}

function Assert-RemoteDeployContext {
    $want = if (-not [string]::IsNullOrWhiteSpace($DockerContext)) {
        $DockerContext.Trim()
    } elseif ($env:BDX_DOCKER_CONTEXT) {
        $env:BDX_DOCKER_CONTEXT.Trim()
    } else {
        'remote-prod'
    }

    if (-not $Local -and $want -in @('default', 'desktop-linux')) {
        throw "Refusing local Docker context '$want'. Deploy targets remote-prod."
    }

    if ($Local) {
        if (-not [string]::IsNullOrWhiteSpace($DockerContext)) {
            Write-Step "Switching Docker context to '$DockerContext' (-Local)"
            & docker context use $DockerContext
            if ($LASTEXITCODE -ne 0) { throw "docker context use '$DockerContext' failed." }
        }
        Write-Warn2 'LOCAL ESCAPE HATCH (-Local): deploying to the active local Docker engine.'
    }
    else {
        $cur = (docker context show 2>$null).Trim()
        if ($cur -ne $want) {
            Write-Step "Switching Docker context to '$want'"
            & docker context use $want
            if ($LASTEXITCODE -ne 0) { throw "docker context use '$want' failed." }
        }
    }

    $active = (& docker context show).Trim()
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($active)) {
        throw 'Could not read active Docker context.'
    }
    Write-Step "Active Docker context: $active"
    if (-not $Local -and $active -in @('default', 'desktop-linux', '')) {
        throw "Active Docker context '$active' is local. Run: docker context use remote-prod"
    }
}

function Get-PublicHost {
    if ($env:BDX_REMOTE_HOST) { return $env:BDX_REMOTE_HOST.Trim().TrimEnd('/') }
    if ($Local) { return '127.0.0.1' }
    $ctxName = (docker context show 2>$null).Trim()
    $endpoint = (docker context inspect $ctxName --format '{{.Endpoints.docker.Host}}' 2>$null).Trim()
    if ($endpoint -match '@([^:/]+)$') { return $Matches[1] }
    if ($endpoint -match 'tcp://([^:/]+)') { return $Matches[1] }
    if ($endpoint -match '://([^:/]+)') { return $Matches[1] }
    throw "Cannot resolve public host from Docker context '$ctxName'. Set BDX_REMOTE_HOST."
}

function Invoke-Compose {
    param([string[]]$CommandArgs)
    $full = @('compose', '-f', $ComposeFile)
    if (Test-Path $EnvFile) { $full += @('--env-file', $EnvFile) }
    $full += $CommandArgs
    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        & docker @full
        $code = $LASTEXITCODE
    }
    finally { $ErrorActionPreference = $prev }
    if ($code -ne 0) { throw "compose command failed (exit $code): $($CommandArgs -join ' ')" }
}

function Invoke-WithRetry {
    param([scriptblock]$Command, [string]$Name, [int]$RetryCount)
    $maxAttempts = 1 + [Math]::Max(0, $RetryCount)
    for ($attempt = 1; $attempt -le $maxAttempts; $attempt++) {
        Write-Step "$Name (attempt $attempt/$maxAttempts)"
        try {
            & $Command
            return
        }
        catch {
            if ($attempt -ge $maxAttempts) { throw }
            Write-Warn2 "$Name failed on attempt $attempt. Retrying..."
            Start-Sleep -Seconds 3
        }
    }
}

function Test-ApiHealth {
    param([int]$TimeoutSeconds = 90)
    $base = Get-PublicHost
    $url = "http://${base}:$PublishPort$HealthPath"
    Write-Step "Health-check $url"
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        $prev = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        try {
            $running = (& docker inspect --format '{{.State.Running}}' $ApiContainer 2>$null).Trim()
            $r = Invoke-WebRequest -Uri $url -TimeoutSec 3 -UseBasicParsing
            if ($running -eq 'true' -and $r.StatusCode -eq 200) {
                Write-Ok "api antwortet auf ${base}:$PublishPort$HealthPath"
                return $true
            }
        }
        catch { }
        finally { $ErrorActionPreference = $prev }
        Start-Sleep -Seconds 3
    }
    Write-Warn2 "api hat innerhalb von ${TimeoutSeconds}s nicht geantwortet (docker logs $ApiContainer)."
    return $false
}

# ── Safety: refuse to deploy if DEV .env has SL_DRY_RUN=false ──────────────
function Assert-DevDryRun {
    if (-not (Test-Path $EnvFile)) { return }
    $dryRun = (Get-Content $EnvFile | Where-Object { $_ -match '^SL_DRY_RUN=' }) -replace '^SL_DRY_RUN=', ''
    if ($dryRun.Trim() -eq 'false') {
        throw "ABORT: $EnvFile has SL_DRY_RUN=false. DEV must keep SL_DRY_RUN=true. Use deploy-prod.yml for PROD."
    }
    Write-Ok "DEV SL_DRY_RUN=true confirmed"
}

Assert-RemoteDeployContext
& docker info | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Docker daemon is not reachable. docker context use remote-prod; docker info"
}

$doBuild = ($Action -in @('up', 'restart')) -and -not $NoBuild

switch ($Action) {
    'status' {
        Invoke-Compose -CommandArgs @('ps')
        exit 0
    }
    'logs' {
        $la = @('logs', '--tail', '200')
        if ($Follow) { $la += '-f' }
        $la += $Services
        Invoke-Compose -CommandArgs $la
        exit 0
    }
    'down' {
        Write-Step 'Container stoppen (Event-Store auf dem Server bleibt)'
        Invoke-Compose -CommandArgs @('down')
        Write-DeployCompleted -Message 'bdx-intelligence stopped'
        exit 0
    }
    'migrate' {
        Assert-DevDryRun
        Write-Step 'Alembic migrate (docker compose run --rm migrate)'
        Invoke-Compose -CommandArgs @('run', '--rm', 'migrate')
        Write-DeployCompleted -Message 'migrate completed'
        exit 0
    }
}

Assert-DevDryRun

if ($doBuild) {
    Invoke-WithRetry -RetryCount $BuildRetryCount -Name 'docker compose build' -Command {
        Invoke-Compose -CommandArgs (@('build') + $Services)
    }
}

Invoke-WithRetry -RetryCount $UpRetryCount -Name 'docker compose up -d' -Command {
    Invoke-Compose -CommandArgs (@('up', '-d') + $Services)
}

try {
    Invoke-Compose -CommandArgs (@('ps') + $Services)
}
catch {
    Write-Warn2 "compose ps failed after up: $($_.Exception.Message)"
}

if (-not $SkipHealth) {
    if (-not (Test-ApiHealth)) { throw 'Health-check failed.' }
}

Write-DeployCompleted -Message 'bdx-intelligence deploy completed' -Persist
