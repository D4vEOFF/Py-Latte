<#
.SYNOPSIS
    Instalace nástroje latte (LaTeX Template To Editor) na Windows.

.DESCRIPTION
    Skript vytvoří izolované virtuální prostředí a do adresáře v PATH
    umístí spouštěč latte.cmd. Systémový Python zůstane nedotčený.

.PARAMETER Uninstall
    Odstraní latte.

.PARAMETER Purge
    Spolu s -Uninstall smaže i konfiguraci a uživatelské šablony.

.PARAMETER Prefix
    Adresář pro spouštěč. Výchozí %LOCALAPPDATA%\latte\bin.

.PARAMETER InstallDir
    Adresář instalace. Výchozí %LOCALAPPDATA%\latte.

.PARAMETER Python
    Interpret, ze kterého se vytvoří prostředí.

.EXAMPLE
    .\install.ps1

.EXAMPLE
    .\install.ps1 -Uninstall -Purge
#>

[CmdletBinding()]
param(
    [switch]$Uninstall,
    [switch]$Purge,
    [string]$Prefix,
    [string]$InstallDir,
    [string]$Python
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$MinPython = [Version]'3.9'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

$LatteHome = if ($InstallDir) { $InstallDir } else { Join-Path $env:LOCALAPPDATA 'latte' }
$BinDir    = if ($Prefix) { $Prefix } else { Join-Path $LatteHome 'bin' }
$VenvDir   = Join-Path $LatteHome 'venv'
$ConfigDir = Join-Path $env:APPDATA 'latte'
$Launcher  = Join-Path $BinDir 'latte.cmd'

# --- Výpis -----------------------------------------------------------

function Write-Info { param([string]$Message) Write-Host ":: $Message" }
function Write-Ok   { param([string]$Message) Write-Host "[ok] $Message" -ForegroundColor Green }
function Write-Warn { param([string]$Message) Write-Host "[!]  $Message" -ForegroundColor Yellow }
function Stop-WithError {
    param([string]$Message)
    Write-Host "[x]  $Message" -ForegroundColor Red
    exit 1
}

# --- Odinstalace -----------------------------------------------------

function Invoke-Uninstall {
    $removed = $false

    if (Test-Path $Launcher) {
        Remove-Item $Launcher -Force
        Write-Ok "odstraněno $Launcher"
        $removed = $true
    }
    if (Test-Path $VenvDir) {
        Remove-Item $VenvDir -Recurse -Force
        Write-Ok "odstraněno $VenvDir"
        $removed = $true
    }

    # Adresář instalace zmizí, jen pokud v něm nic dalšího nezůstalo.
    if ((Test-Path $LatteHome) -and -not (Get-ChildItem $LatteHome -Force)) {
        Remove-Item $LatteHome -Force
    }

    Remove-FromUserPath -Directory $BinDir

    if ($Purge) {
        if (Test-Path $ConfigDir) {
            Remove-Item $ConfigDir -Recurse -Force
            Write-Ok "odstraněna konfigurace $ConfigDir"
        }
    }
    elseif (Test-Path $ConfigDir) {
        Write-Info "Konfigurace v $ConfigDir zůstala zachována."
        Write-Host "   Smazat ji lze pomocí .\install.ps1 -Uninstall -Purge" -ForegroundColor DarkGray
    }

    if (-not $removed) { Write-Warn 'latte nebylo nainstalováno.' }
}

# --- PATH ------------------------------------------------------------

function Get-UserPath {
    $value = [Environment]::GetEnvironmentVariable('Path', 'User')
    if ($null -eq $value) { return @() }
    return $value.Split(';') | Where-Object { $_ -ne '' }
}

function Add-ToUserPath {
    param([string]$Directory)

    $entries = Get-UserPath
    if ($entries -contains $Directory) { return $false }

    $updated = (@($entries) + $Directory) -join ';'
    [Environment]::SetEnvironmentVariable('Path', $updated, 'User')
    # Aby příkaz fungoval i ve stávajícím okně.
    $env:Path = "$env:Path;$Directory"
    return $true
}

function Remove-FromUserPath {
    param([string]$Directory)

    $entries = Get-UserPath
    if ($entries -notcontains $Directory) { return }

    $updated = ($entries | Where-Object { $_ -ne $Directory }) -join ';'
    [Environment]::SetEnvironmentVariable('Path', $updated, 'User')
    Write-Ok "$Directory odebrán z PATH"
}

# --- Instalace -------------------------------------------------------

function Find-Python {
    if ($Python) {
        $found = Get-Command $Python -ErrorAction SilentlyContinue
        if (-not $found) { Stop-WithError "Interpret $Python neexistuje." }
        return $found.Source
    }

    # Launcher `py` umí vybrat nejnovější nainstalovanou verzi.
    $launcher = Get-Command 'py' -ErrorAction SilentlyContinue
    if ($launcher) {
        $resolved = & $launcher.Source '-3' '-c' 'import sys; print(sys.executable)' 2>$null
        if ($LASTEXITCODE -eq 0 -and $resolved) { return $resolved.Trim() }
    }

    foreach ($name in @('python3', 'python')) {
        $found = Get-Command $name -ErrorAction SilentlyContinue
        # Zástupce z Microsoft Store jen otevře obchod, není to interpret.
        if ($found -and $found.Source -notlike '*WindowsApps*') {
            return $found.Source
        }
    }

    Stop-WithError "Nenašel jsem Python. Nainstalujte Python $MinPython nebo novější z python.org."
}

function Test-PythonVersion {
    param([string]$Executable)

    $raw = & $Executable '-c' 'import platform; print(platform.python_version())'
    $version = [Version]($raw.Trim())
    if ($version -lt $MinPython) {
        Stop-WithError "Nalezen Python $version, je potřeba $MinPython nebo novější."
    }
    return $version
}

function Invoke-Install {
    $project = Join-Path $ScriptDir 'pyproject.toml'
    if (-not (Test-Path $project)) {
        Stop-WithError "V $ScriptDir není pyproject.toml -- spusťte skript z kořene projektu."
    }

    $python = Find-Python
    $version = Test-PythonVersion -Executable $python
    Write-Info "Python: $version -- $python"

    if (Test-Path $VenvDir) {
        Write-Info "Aktualizuji stávající instalaci v $VenvDir"
    }
    else {
        Write-Info "Vytvářím prostředí v $VenvDir"
        New-Item -ItemType Directory -Force -Path $LatteHome | Out-Null
        & $python '-m' 'venv' $VenvDir
        if ($LASTEXITCODE -ne 0) { Stop-WithError 'Vytvoření venv selhalo.' }
    }

    $venvPython = Join-Path $VenvDir 'Scripts\python.exe'
    & $venvPython '-m' 'pip' 'install' '--quiet' '--upgrade' 'pip'
    & $venvPython '-m' 'pip' 'install' '--quiet' '--upgrade' $ScriptDir
    if ($LASTEXITCODE -ne 0) { Stop-WithError 'Instalace balíčku selhala.' }

    New-Item -ItemType Directory -Force -Path $BinDir | Out-Null

    # Spouštěč místo symbolického odkazu: ten na Windows vyžaduje
    # vývojářský režim nebo práva správce.
    $exe = Join-Path $VenvDir 'Scripts\latte.exe'
    @(
        '@echo off',
        "`"$exe`" %*"
    ) | Set-Content -Path $Launcher -Encoding ASCII
    Write-Ok "latte nainstalováno do $Launcher"

    New-Item -ItemType Directory -Force -Path (Join-Path $ConfigDir 'templates') | Out-Null

    if (Add-ToUserPath -Directory $BinDir) {
        Write-Ok "$BinDir přidán do PATH"
        Write-Warn 'Nové okno terminálu změnu PATH uvidí, stávající nemusí.'
    }

    & $exe '--version'

    Write-Host ''
    Write-Host 'Začněte:'
    Write-Host '  latte muj-projekt          nový článek'
    Write-Host '  latte                      interaktivně'
    Write-Host '  latte templates            dostupné šablony'
    Write-Host '  latte config show          aktuální nastavení'
}

if ($Uninstall) { Invoke-Uninstall } else { Invoke-Install }
