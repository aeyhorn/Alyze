<#
.SYNOPSIS
    Stellt den SAP-SQL-Login bdx_readonly für DEV_SBO_LEISINGER wieder her
    und lässt den Collector einmal laufen (Dashboard-Stand aktualisieren).

.DESCRIPTION
    Läuft typischerweise auf einem Windows-Admin-PC im LAN (LEISINGER\…):

      1) sqlcmd mit Windows-Auth (-E) gegen LDSAP → reset_bdx_readonly.sql
         (Passwort kommt aus SAP_DB_PASSWORD in .env, nie aus dem Repo)
      2) docker compose (Context remote-prod → 192.168.82.33) →
         bdx-collect diagnose + collect --once

    Voraussetzungen:
      - sqlcmd (MSSQL Tools) im PATH
      - Windows-Konto mit Sysadmin auf LDSAP
      - Docker-Context remote-prod (wie scripts/deploy.ps1)
      - .env mit SAP_DB_* (gleiche Werte wie auf dem DEV-Host)

.PARAMETER EnvFile
    Pfad zur .env (Standard: bdx-intelligence/.env).

.PARAMETER SqlServer
    SQL-Server (Standard: SAP_DB_HOST aus .env, sonst ldsap.leisinger.local).

.PARAMETER SkipSql
    Nur Collector (wenn Login schon ok ist).

.PARAMETER SkipCollect
    Nur SQL-Reset (kein Docker-Lauf).

.PARAMETER Full
    collect --once --full statt inkrementell.

.PARAMETER Local
    Lokalen Docker-Context erlauben (wie deploy.ps1 -Local).

.EXAMPLE
    pwsh ./scripts/Fix-DevSapAccess.ps1
    pwsh ./scripts/Fix-DevSapAccess.ps1 -SkipSql
    pwsh ./scripts/Fix-DevSapAccess.ps1 -Full
#>
[CmdletBinding()]
param(
    [string]$EnvFile = '',
    [string]$SqlServer = '',
    [switch]$SkipSql,
    [switch]$SkipCollect,
    [switch]$Full,
    [switch]$Local,
    [string]$DockerContext = ''
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$ComposeFile = Join-Path $ProjectRoot 'docker-compose.yml'
$SqlTemplate = Join-Path $ProjectRoot 'docs/sql/reset_bdx_readonly.sql'
if ([string]::IsNullOrWhiteSpace($EnvFile)) {
    $EnvFile = Join-Path $ProjectRoot '.env'
}

function Write-Step($m) { Write-Host "==> $m" -ForegroundColor Cyan }
function Write-Ok($m)    { Write-Host "  OK  $m" -ForegroundColor Green }
function Write-Warn2($m) { Write-Host "  !!  $m" -ForegroundColor Yellow }
function Write-Err($m)  { Write-Host "  XX  $m" -ForegroundColor Red }

function Read-DotEnv {
    param([Parameter(Mandatory)][string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        throw ".env not found: $Path"
    }
    $map = @{}
    foreach ($line in Get-Content -LiteralPath $Path) {
        $t = $line.Trim()
        if ($t -eq '' -or $t.StartsWith('#')) { continue }
        $i = $t.IndexOf('=')
        if ($i -lt 1) { continue }
        $k = $t.Substring(0, $i).Trim()
        $v = $t.Substring($i + 1).Trim()
        if (($v.StartsWith('"') -and $v.EndsWith('"')) -or ($v.StartsWith("'") -and $v.EndsWith("'"))) {
            $v = $v.Substring(1, $v.Length - 2)
        }
        $map[$k] = $v
    }
    return $map
}

function Escape-SqlLiteral([string]$value) {
    return $value.Replace("'", "''")
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
        throw "Refusing local Docker context '$want'. Use remote-prod (or -Local)."
    }

    if ($Local) {
        if (-not [string]::IsNullOrWhiteSpace($DockerContext)) {
            Write-Step "Switching Docker context to '$DockerContext' (-Local)"
            & docker context use $DockerContext
            if ($LASTEXITCODE -ne 0) { throw "docker context use '$DockerContext' failed." }
        }
        Write-Warn2 'LOCAL ESCAPE HATCH (-Local): targeting the active local Docker engine.'
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
    Write-Step "Active Docker context: $active"
}

function Invoke-Compose {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$ComposeArgs)
    $args = @('compose', '--env-file', $EnvFile, '-f', $ComposeFile) + $ComposeArgs
    Write-Step ("docker " + ($args -join ' '))
    & docker @args
    if ($LASTEXITCODE -ne 0) { throw "docker compose failed (exit $LASTEXITCODE)." }
}

# ── load env ────────────────────────────────────────────────────────────────
$envMap = Read-DotEnv -Path $EnvFile
$password = $envMap['SAP_DB_PASSWORD']
if ([string]::IsNullOrWhiteSpace($password) -or $password -eq 'CHANGE_ME') {
    throw "SAP_DB_PASSWORD missing or still CHANGE_ME in $EnvFile"
}
if ([string]::IsNullOrWhiteSpace($SqlServer)) {
    $SqlServer = if ($envMap['SAP_DB_HOST']) { $envMap['SAP_DB_HOST'] } else { 'ldsap.leisinger.local' }
}
$dbName = if ($envMap['SAP_DB_NAME']) { $envMap['SAP_DB_NAME'] } else { 'DEV_SBO_LEISINGER' }

Write-Step "Env: $EnvFile"
Write-Step "SQL Server: $SqlServer  DB: $dbName"

# ── SQL reset (Windows integrated admin on LDSAP) ───────────────────────────
if (-not $SkipSql) {
    if (-not (Test-Path -LiteralPath $SqlTemplate)) {
        throw "SQL template missing: $SqlTemplate"
    }
    $sqlcmd = Get-Command sqlcmd -ErrorAction SilentlyContinue
    if (-not $sqlcmd) {
        throw "sqlcmd not found in PATH. Install MSSQL tools or run the SQL in SSMS, then re-run with -SkipSql."
    }

    $escaped = Escape-SqlLiteral $password
    $sqlText = Get-Content -LiteralPath $SqlTemplate -Raw
    if ($sqlText -notmatch '__SAP_DB_PASSWORD__') {
        throw "SQL template has no __SAP_DB_PASSWORD__ placeholder — refusing to run (avoid hardcoded secrets)."
    }
    $sqlText = $sqlText.Replace('__SAP_DB_PASSWORD__', $escaped)

    $tmp = Join-Path ([System.IO.Path]::GetTempPath()) ("bdx-reset-readonly-{0}.sql" -f [guid]::NewGuid().ToString('N'))
    try {
        # UTF-16 LE is what sqlcmd expects for Unicode passwords reliably
        [System.IO.File]::WriteAllText($tmp, $sqlText, [System.Text.UnicodeEncoding]::new($false, $true))
        Write-Step "Applying reset_bdx_readonly.sql on $SqlServer (Windows auth)"
        & sqlcmd -S $SqlServer -E -b -i $tmp
        if ($LASTEXITCODE -ne 0) { throw "sqlcmd failed (exit $LASTEXITCODE)." }
        Write-Ok "SQL login/grants applied for bdx_readonly → $dbName"
    }
    finally {
        if (Test-Path -LiteralPath $tmp) {
            Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue
        }
    }
}
else {
    Write-Warn2 'Skipping SQL reset (-SkipSql)'
}

# ── Collector once on DEV host ──────────────────────────────────────────────
if (-not $SkipCollect) {
    Assert-RemoteDeployContext
    if (-not (Test-Path -LiteralPath $ComposeFile)) {
        throw "compose file missing: $ComposeFile"
    }

    Write-Step 'diagnose'
    Invoke-Compose @('exec', '-T', 'collector', 'bdx-collect', 'diagnose')

    $collectArgs = @('exec', '-T', 'collector', 'bdx-collect', 'collect', '--once')
    if ($Full) { $collectArgs += '--full' }
    Write-Step ('collect ' + ($(if ($Full) { '--once --full' } else { '--once' })))
    Invoke-Compose @collectArgs

    Write-Ok 'Collector cycle finished. Check Dashboard Stand: http://192.168.82.33:8085/dashboard'
}
else {
    Write-Warn2 'Skipping collect (-SkipCollect)'
}

Write-Ok 'Done.'
