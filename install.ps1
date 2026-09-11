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
# Dokud nic nespustíme, proměnná neexistuje a přísný režim by na kontrole
# návratového kódu spadl.
$global:LASTEXITCODE = 0

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

# Oznámení o změně prostředí. Bez něj si Průzkumník drží starou PATH
# a předává ji každému programu, který z něj uživatel spustí -- včetně
# terminálů otevřených dlouho po instalaci.
function Publish-EnvironmentChange {
    if (-not ('Latte.NativeMethods' -as [type])) {
        $signature = @'
[DllImport("user32.dll", SetLastError = true, CharSet = CharSet.Auto)]
public static extern IntPtr SendMessageTimeout(IntPtr hWnd, uint Msg, UIntPtr wParam,
    string lParam, uint fuFlags, uint uTimeout, out UIntPtr lpdwResult);
'@
        try {
            Add-Type -MemberDefinition $signature -Name 'NativeMethods' `
                -Namespace 'Latte' -ErrorAction Stop | Out-Null
        }
        catch { return }
    }

    $HWND_BROADCAST   = [IntPtr]0xffff
    $WM_SETTINGCHANGE = 0x1a
    $SMTO_ABORTIFHUNG = 0x0002
    $answer = [UIntPtr]::Zero
    try {
        [void][Latte.NativeMethods]::SendMessageTimeout($HWND_BROADCAST, $WM_SETTINGCHANGE,
            [UIntPtr]::Zero, 'Environment', $SMTO_ABORTIFHUNG, 5000, [ref]$answer)
    }
    catch { }
}

# Porovnání cest bez ohledu na velikost písmen a koncové zpětné lomítko,
# aby se stejný adresář nepřidal dvakrát a odinstalace ho našla.
function Test-SamePath {
    param([string]$Left, [string]$Right)
    return $Left.TrimEnd('\') -eq $Right.TrimEnd('\')
}

function Get-UserPath {
    $key = [Microsoft.Win32.Registry]::CurrentUser.OpenSubKey('Environment')
    if (-not $key) { return @() }
    try {
        # Nerozvinutá podoba: jinak by se z %USERPROFILE%\bin při zápisu
        # stala napevno zapsaná cesta.
        $value = $key.GetValue('Path', '',
            [Microsoft.Win32.RegistryValueOptions]::DoNotExpandEnvironmentNames)
    }
    finally { $key.Close() }

    if (-not $value) { return @() }
    return @($value.Split(';') | Where-Object { $_ -ne '' })
}

function Set-UserPath {
    param([string[]]$Entries)

    $key = [Microsoft.Win32.Registry]::CurrentUser.OpenSubKey('Environment', $true)
    if (-not $key) { Stop-WithError 'Nepodařilo se otevřít uživatelské proměnné prostředí.' }
    try {
        # REG_EXPAND_SZ, ne REG_SZ: [Environment]::SetEnvironmentVariable
        # zapisuje prostý text a tím zruší rozvíjení %PROMĚNNÝCH%
        # u všech ostatních položek PATH.
        $key.SetValue('Path', ($Entries -join ';'),
            [Microsoft.Win32.RegistryValueKind]::ExpandString)
    }
    finally { $key.Close() }

    Publish-EnvironmentChange
}

function Add-ToUserPath {
    param([string]$Directory)

    $entries = Get-UserPath
    foreach ($entry in $entries) {
        if (Test-SamePath -Left $entry -Right $Directory) { return $false }
    }

    Set-UserPath -Entries (@($entries) + $Directory)
    # Aby příkaz fungoval i ve stávajícím okně.
    $env:Path = "$env:Path;$Directory"
    return $true
}

function Remove-FromUserPath {
    param([string]$Directory)

    $entries = Get-UserPath
    $kept = @($entries | Where-Object { -not (Test-SamePath -Left $_ -Right $Directory) })
    if ($kept.Count -eq $entries.Count) { return }

    Set-UserPath -Entries $kept
    Write-Ok "$Directory odebrán z PATH"
}

# Změnu PATH si nový proces přečte z registru, ale prostředí dědí po tom,
# kdo ho spustil. Windows Terminal ani VS Code si prostředí po oznámení
# neobnovují, takže nová karta v nich stále běží se starou PATH; pomůže
# až restart celého programu.
function Show-PathHint {
    Write-Warn 'Změnu PATH uvidí až nově spuštěné programy.'
    Write-Host '   Windows Terminal a VS Code si prostředí drží od svého startu,' -ForegroundColor DarkGray
    Write-Host '   takže nová karta nestačí -- ukončete celý program a spusťte ho' -ForegroundColor DarkGray
    Write-Host '   znovu. Ve stávajícím okně cestu doplní:' -ForegroundColor DarkGray
    Write-Host ''
    Write-Host "     `$env:Path += ';$BinDir'"
    Write-Host ''
}

# --- Instalace -------------------------------------------------------

# Přesměrování chybového výstupu nativního programu se v PowerShellu 5.1
# zabalí do chybového záznamu; při $ErrorActionPreference = 'Stop' by
# takové volání shodilo celý skript, proto se nastavení na okamžik vrátí.
function Invoke-Quiet {
    param(
        [string]$Executable,
        [string[]]$Arguments
    )

    $previous = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $output = & $Executable @Arguments 2>$null
        $code = $LASTEXITCODE
    }
    catch { return $null }
    finally { $ErrorActionPreference = $previous }

    if ($code -ne 0) { return $null }
    return $output
}

# Vrátí verzi a skutečnou cestu interpretu, nebo $null, pokud kandidát
# neexistuje nebo se nespustí.
function Get-PythonInfo {
    param([string]$Executable)

    if (-not $Executable) { return $null }
    if (-not (Test-Path -LiteralPath $Executable -PathType Leaf)) { return $null }

    $probe = 'import sys, platform; print(platform.python_version()); print(sys.executable)'
    $lines = @(Invoke-Quiet -Executable $Executable -Arguments @('-c', $probe))
    if ($lines.Count -lt 2) { return $null }

    try { $version = [Version]($lines[0].Trim()) } catch { return $null }

    $path = $lines[1].Trim()
    if (-not $path) { $path = $Executable }

    return [pscustomobject]@{ Version = $version; Path = $path }
}

# Kandidáti na interpret, od nejpravděpodobnějšího. Samotné PATH nestačí:
# Python z python.org se do něj nemusí zapsat a Python z Microsoft Store
# je v PATH jen jako zástupce.
function Get-PythonCandidate {
    $candidates = New-Object System.Collections.Generic.List[string]

    # Launcher `py` umí vybrat nejnovější nainstalovanou verzi.
    $launcher = @(Get-Command 'py' -CommandType Application -ErrorAction SilentlyContinue)
    if ($launcher.Count -gt 0) {
        $resolved = @(Invoke-Quiet -Executable $launcher[0].Source `
            -Arguments @('-3', '-c', 'import sys; print(sys.executable)'))
        if ($resolved.Count -gt 0) { $candidates.Add($resolved[0].Trim()) }
    }

    # Interprety v PATH. Zástupce WindowsApps\python.exe se přeskakuje:
    # bez nainstalovaného balíčku jen otevře obchod a nikdy se nevrátí.
    foreach ($name in @('python3', 'python')) {
        foreach ($found in @(Get-Command $name -CommandType Application -ErrorAction SilentlyContinue)) {
            if ($found.Source -notlike '*\WindowsApps\*') { $candidates.Add($found.Source) }
        }
    }

    # Python z Microsoft Store. Cesta s názvem balíčku je na rozdíl od
    # zástupce skutečný interpret, takže se spustí bezpečně.
    $store = Join-Path $env:LOCALAPPDATA 'Microsoft\WindowsApps\PythonSoftwareFoundation.Python.*\python.exe'
    foreach ($item in @(Get-Item $store -ErrorAction SilentlyContinue)) {
        $candidates.Add($item.FullName)
    }

    # Registr zachytí instalace z python.org, které v PATH nejsou.
    foreach ($hive in @('HKCU:\SOFTWARE\Python', 'HKLM:\SOFTWARE\Python',
                        'HKLM:\SOFTWARE\WOW6432Node\Python')) {
        foreach ($key in @(Get-ChildItem "$hive\*\*\InstallPath" -ErrorAction SilentlyContinue)) {
            $props = Get-ItemProperty -Path $key.PSPath
            $exe = $null
            if ($props.PSObject.Properties['ExecutablePath']) { $exe = $props.ExecutablePath }
            if (-not $exe -and $props.PSObject.Properties['(default)']) {
                $root = $props.'(default)'
                if ($root) { $exe = Join-Path $root 'python.exe' }
            }
            # Balíčky v Program Files\WindowsApps uživatel spustit nesmí.
            if ($exe -and $exe -notlike '*\Program Files\WindowsApps\*') { $candidates.Add($exe) }
        }
    }

    # Obvyklá místa instalace z python.org bez zápisu do PATH i registru.
    foreach ($pattern in @((Join-Path $env:LOCALAPPDATA 'Programs\Python\Python3*\python.exe'),
                           (Join-Path $env:ProgramFiles 'Python3*\python.exe'),
                           'C:\Python3*\python.exe')) {
        foreach ($item in @(Get-Item $pattern -ErrorAction SilentlyContinue)) {
            $candidates.Add($item.FullName)
        }
    }

    return $candidates | Select-Object -Unique
}

function Find-Python {
    if ($Python) {
        $explicit = $Python
        $found = @(Get-Command $Python -CommandType Application -ErrorAction SilentlyContinue)
        if ($found.Count -gt 0) { $explicit = $found[0].Source }
        elseif (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
            Stop-WithError "Interpret $Python neexistuje."
        }

        $info = Get-PythonInfo -Executable $explicit
        if (-not $info) { Stop-WithError "Interpret $Python se nepodařilo spustit." }
        if ($info.Version -lt $MinPython) {
            Stop-WithError "Nalezen Python $($info.Version), je potřeba $MinPython nebo novější."
        }
        return $info
    }

    $tooOld = $null
    foreach ($candidate in Get-PythonCandidate) {
        $info = Get-PythonInfo -Executable $candidate
        if (-not $info) { continue }
        if ($info.Version -lt $MinPython) {
            if (-not $tooOld) { $tooOld = $info.Version }
            continue
        }
        return $info
    }

    if ($tooOld) {
        Stop-WithError "Nalezen jen Python $tooOld, je potřeba $MinPython nebo novější."
    }
    Write-Warn 'Prohledány PATH, launcher py, registr, Microsoft Store i obvyklé adresáře.'
    Stop-WithError ("Nenašel jsem Python. Nainstalujte Python $MinPython nebo novější " +
        'z python.org, nebo zadejte cestu: .\install.ps1 -Python C:\cesta\python.exe')
}

function Invoke-Install {
    $project = Join-Path $ScriptDir 'pyproject.toml'
    if (-not (Test-Path $project)) {
        Stop-WithError "V $ScriptDir není pyproject.toml -- spusťte skript z kořene projektu."
    }

    $info = Find-Python
    $python = $info.Path
    Write-Info "Python: $($info.Version) -- $python"

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
        Show-PathHint
    }
    elseif (-not (Get-Command 'latte' -CommandType Application -ErrorAction SilentlyContinue)) {
        # Adresář v PATH už zapsaný je, ale tento proces ho nevidí --
        # uživatel narazí na totéž i v terminálu, který nové prostředí
        # nedostal.
        Publish-EnvironmentChange
        Show-PathHint
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
