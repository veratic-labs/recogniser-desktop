<#
.SYNOPSIS
    Builds, verifies, and (optionally) packages the recogniser Windows desktop app.

.DESCRIPTION
    Without switches, runs the tests, prepares the generated build inputs, and
    builds dist\recogniser with PyInstaller. It then verifies the bundle
    inventory, runs the frozen --self-test from two working directories, and
    writes build\bundle-manifest.json.

    With -Installer, nothing is rebuilt: the existing dist\recogniser must match
    build\bundle-manifest.json exactly, so the installer can only wrap the
    bundle that was built and reviewed earlier.

.PARAMETER Clean
    Pass --clean to PyInstaller, discarding its analysis cache.

.PARAMETER Installer
    Compile the Inno Setup installer for the reviewed bundle and stop.

.PARAMETER IsccPath
    Explicit path to ISCC.exe. When empty, the Inno Setup 7 default location and
    then PATH are tried.

.EXAMPLE
    .\packaging\build.ps1 -Clean

.EXAMPLE
    .\packaging\build.ps1 -Installer
#>

[CmdletBinding()]
param(
    [switch]$Clean,
    [switch]$Installer,
    [string]$IsccPath
)

$ErrorActionPreference = 'Stop'

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot 'venv\Scripts\python.exe'
$SpecPath = Join-Path $ProjectRoot 'packaging\recogniser.spec'
$InstallerScript = Join-Path $ProjectRoot 'packaging\recogniser.iss'
$VersionFile = Join-Path $ProjectRoot 'packaging\version.txt'
$BundleDir = Join-Path $ProjectRoot 'dist\recogniser'
$BundleExe = Join-Path $BundleDir 'recogniser.exe'
$ManifestPath = Join-Path $ProjectRoot 'build\bundle-manifest.json'
$InstallerDir = Join-Path $ProjectRoot 'dist\installer'
$TempRoot = Join-Path $ProjectRoot '.tmp'

# Every temporary file, cache, and log stays inside the project. Without this,
# PyInstaller would write its cache to %LOCALAPPDATA% and Python would write
# bytecode outside the repository.
$env:TEMP = $TempRoot
$env:TMP = $TempRoot
$env:PYTHONPYCACHEPREFIX = Join-Path $TempRoot 'pycache'
$env:PYINSTALLER_CONFIG_DIR = Join-Path $TempRoot 'pyinstaller-config'
foreach ($directory in @($TempRoot, $env:PYTHONPYCACHEPREFIX, $env:PYINSTALLER_CONFIG_DIR)) {
    New-Item -ItemType Directory -Force -Path $directory | Out-Null
}

function Write-Step {
    param([string]$Message)
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Write-Detail {
    param([string]$Message)
    Write-Host "    $Message"
}

function Invoke-Process {
    <# Runs a console process, logs both streams, and returns its exit code. #>
    param(
        [string]$FilePath,
        [string[]]$Arguments,
        [string]$LogPath
    )

    $previous = $ErrorActionPreference
    # A native command's stderr becomes error records in the pipeline; keep them
    # flowing into the log instead of terminating the script.
    $ErrorActionPreference = 'Continue'
    try {
        & $FilePath @Arguments 2>&1 | Out-File -LiteralPath $LogPath -Encoding utf8
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previous
    }

    Get-Content -LiteralPath $LogPath -Tail 15 | ForEach-Object { Write-Detail $_ }
    Write-Detail "exit code: $exitCode (log: $LogPath)"
    return $exitCode
}


function Get-AppVersion {
    <# Returns the validated version from packaging\version.txt. #>
    $version = (Get-Content -LiteralPath $VersionFile -Raw).Trim()
    if ($version -notmatch '^\d+\.\d+\.\d+$') {
        throw "$VersionFile must contain a three-part version such as 1.0.0, but contains '$version'."
    }
    return $version
}

function Get-BundleFiles {
    param([string]$Directory)
    Get-ChildItem -LiteralPath $Directory -Recurse -File | Sort-Object FullName
}

function Get-RelativeBundlePath {
    <# Windows PowerShell 5.1 has no Path.GetRelativePath. #>
    param([string]$Directory, [string]$FullName)
    $root = $Directory.TrimEnd('\') + '\'
    return $FullName.Substring($root.Length) -replace '\\', '/'
}

function Test-BundleInventory {
    <# Fails unless the expected executables and resources are in the bundle. #>
    if (-not (Test-Path -LiteralPath $BundleExe)) {
        throw "PyInstaller did not produce $BundleExe."
    }

    $required = @(
        'recogniser.exe',
        '_internal\frontend\index.html',
        '_internal\models\0-numbers\model_0_numbers.py',
        '_internal\models\0-numbers\model_0_numbers.onnx'
    )
    foreach ($relative in $required) {
        if (-not (Test-Path -LiteralPath (Join-Path $BundleDir $relative))) {
            throw "The bundle is missing $relative."
        }
        Write-Detail "present: $relative"
    }

    $files = Get-BundleFiles $BundleDir
    $total = ($files | Measure-Object -Property Length -Sum).Sum / 1MB
    Write-Detail ('files: {0}, size: {1:N1} MB' -f $files.Count, $total)

    $internal = Join-Path $BundleDir '_internal'
    $directories = @(Get-ChildItem -LiteralPath $internal -Directory | Select-Object -ExpandProperty Name)
    Write-Detail ("_internal directories ({0}): {1}" -f $directories.Count, ($directories -join ', '))
}

function Invoke-BundleSelfTest {
    <# Runs the frozen --self-test from one working directory and checks its report. #>
    param([string]$WorkingDirectory, [string]$DataDirectory)

    New-Item -ItemType Directory -Force -Path $DataDirectory | Out-Null
    $reportPath = Join-Path $DataDirectory 'logs\self-test.json'
    if (Test-Path -LiteralPath $reportPath) {
        Remove-Item -LiteralPath $reportPath -Force
    }

    $previousDataDirectory = $env:RECOGNISER_DATA_DIR
    $env:RECOGNISER_DATA_DIR = $DataDirectory
    try {
        # The executable uses the Windows GUI subsystem, so the call operator
        # would not wait for it. Start-Process -Wait does.
        $process = Start-Process -FilePath $BundleExe -ArgumentList '--self-test' `
            -WorkingDirectory $WorkingDirectory -WindowStyle Hidden -Wait -PassThru
    }
    finally {
        $env:RECOGNISER_DATA_DIR = $previousDataDirectory
    }

    if (-not (Test-Path -LiteralPath $reportPath)) {
        throw "The self-test wrote no report to $reportPath (exit code $($process.ExitCode))."
    }
    $report = Get-Content -LiteralPath $reportPath -Raw | ConvertFrom-Json
    if ($process.ExitCode -ne 0 -or -not $report.passed) {
        $problems = @($report.problems) -join '; '
        throw "The self-test failed from '$WorkingDirectory' (exit code $($process.ExitCode)): $problems"
    }
    Write-Detail "self-test ok from '$WorkingDirectory' (report: $reportPath)"
    Write-Detail ("renderer: {0}, frozen: {1}" -f $report.renderer, $report.frozen)
}

function Write-BundleManifest {
    <# Records every bundle file with its SHA-256, outside the bundle directory. #>
    param([string]$Directory, [string]$Path)

    $entries = @(
        foreach ($file in Get-BundleFiles $Directory) {
            [pscustomobject]@{
                path = Get-RelativeBundlePath $Directory $file.FullName
                size = $file.Length
                sha256 = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
            }
        }
    )

    $manifest = [ordered]@{
        bundle = 'dist/recogniser'
        executable = 'recogniser.exe'
        file_count = $entries.Count
        created = (Get-Date).ToUniversalTime().ToString('o')
        files = $entries
    }
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Path) | Out-Null
    # Windows PowerShell's Out-File -Encoding utf8 writes a BOM, which strict JSON
    # readers reject. The reviewed-bundle record must be plain UTF-8.
    $json = $manifest | ConvertTo-Json -Depth 5
    [System.IO.File]::WriteAllText($Path, $json, (New-Object System.Text.UTF8Encoding($false)))
    Write-Detail ("manifest: {0} ({1} files)" -f $Path, $entries.Count)
}

function Get-BundleManifestProblems {
    <# Returns the differences between the bundle and the reviewed manifest. #>
    param([string]$Directory, [string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        throw "The reviewed-bundle manifest is missing: $Path. Run .\packaging\build.ps1 first and review that bundle."
    }
    if (-not (Test-Path -LiteralPath $Directory)) {
        throw "The bundle directory is missing: $Directory."
    }

    $manifest = Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
    $expected = @{}
    foreach ($entry in @($manifest.files)) {
        $expected[$entry.path] = $entry.sha256
    }

    $actual = @{}
    foreach ($file in Get-BundleFiles $Directory) {
        $relative = Get-RelativeBundlePath $Directory $file.FullName
        $actual[$relative] = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    }

    $problems = @(
        foreach ($name in $expected.Keys) {
            if (-not $actual.ContainsKey($name)) {
                "missing since the reviewed build: $name"
            }
            elseif ($actual[$name] -ne $expected[$name]) {
                "modified since the reviewed build: $name"
            }
        }
        foreach ($name in $actual.Keys) {
            if (-not $expected.ContainsKey($name)) {
                "added since the reviewed build: $name"
            }
        }
    )
    return $problems
}

function Find-Iscc {
    <# Returns the ISCC.exe path: explicit, then Inno Setup 7, then PATH. #>
    param([string]$Explicit)

    if ($Explicit) {
        if (Test-Path -LiteralPath $Explicit) {
            return (Resolve-Path -LiteralPath $Explicit).Path
        }
        throw "ISCC.exe was not found at the supplied -IsccPath: $Explicit"
    }

    $default = 'C:\Program Files\Inno Setup 7\ISCC.exe'
    if (Test-Path -LiteralPath $default) {
        return $default
    }

    $command = Get-Command 'ISCC.exe' -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    throw "ISCC.exe was not found. Install Inno Setup 7, pass -IsccPath, or add ISCC.exe to PATH."
}

function Get-ProcessOutput {
    <# Returns all output lines of a console process. #>
    param([string]$FilePath, [string[]]$Arguments)

    $previous = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $output = & $FilePath @Arguments 2>&1
    }
    finally {
        $ErrorActionPreference = $previous
    }
    return @($output | ForEach-Object { $_.ToString() })
}

function Assert-ExitCode {
    param([int]$ExitCode, [string]$Action)
    if ($ExitCode -ne 0) {
        throw "$Action failed with exit code $ExitCode."
    }
}

# ---------------------------------------------------------------------------
# Installer path: package the reviewed bundle and never rebuild it.
# ---------------------------------------------------------------------------

if ($Installer) {
    $version = Get-AppVersion
    $fileVersion = "$version.0"
    Write-Step "Checking dist\recogniser against the reviewed manifest (version $version)"

    $differences = @(Get-BundleManifestProblems -Directory $BundleDir -Path $ManifestPath)
    if ($differences.Count -gt 0) {
        foreach ($difference in $differences) {
            Write-Detail $difference
        }
        throw "dist\recogniser differs from the reviewed bundle in $($differences.Count) file(s). Nothing was compiled: rebuild, verify, and review the bundle first."
    }
    Write-Detail 'bundle matches the reviewed manifest'

    if (-not (Test-Path -LiteralPath $InstallerScript)) {
        throw "The installer script is missing: $InstallerScript. The bundle was not packaged."
    }

    $builtVersion = (Get-Item -LiteralPath $BundleExe).VersionInfo.FileVersion
    if ($builtVersion -ne $fileVersion) {
        throw "The bundled executable version $builtVersion does not match packaging\version.txt ($fileVersion). Rebuild the bundle."
    }
    Write-Detail "executable file version: $builtVersion"

    $iscc = Find-Iscc -Explicit $IsccPath
    Write-Detail "ISCC: $iscc"

    New-Item -ItemType Directory -Force -Path $InstallerDir | Out-Null
    $code = Invoke-Process -FilePath $iscc `
        -Arguments @("/DAppVersion=$version", "/DAppVersion4=$fileVersion", $InstallerScript) `
        -LogPath (Join-Path $TempRoot 'iscc.log')
    Assert-ExitCode $code 'ISCC'

    $setup = Join-Path $InstallerDir "recogniser-$version-setup.exe"
    if (-not (Test-Path -LiteralPath $setup)) {
        throw "ISCC did not produce $setup."
    }
    $hash = (Get-FileHash -LiteralPath $setup -Algorithm SHA256).Hash.ToLowerInvariant()
    "$hash  $(Split-Path -Leaf $setup)" | Out-File -LiteralPath "$setup.sha256" -Encoding ascii
    Write-Step 'Installer compiled'
    Write-Detail "setup: $setup"
    Write-Detail "sha256: $hash"
    exit 0
}

# ---------------------------------------------------------------------------
# Build path: test, prepare, build, verify, and record the bundle.
# ---------------------------------------------------------------------------

if (-not (Test-Path -LiteralPath $Python)) {
    throw "The virtual environment interpreter is missing: $Python"
}

$version = Get-AppVersion
$fileVersion = "$version.0"
Write-Step "Preparing recogniser $version (file version $fileVersion)"
Write-Detail "project root: $ProjectRoot"
Write-Detail "temp root: $TempRoot"

$pyInstallerVersion = (Get-ProcessOutput -FilePath $Python -Arguments @('-m', 'PyInstaller', '--version') | Select-Object -Last 1)
if (-not $pyInstallerVersion) {
    throw "PyInstaller is not available in $Python. Install the build requirements into the virtual environment."
}
Write-Detail "PyInstaller: $pyInstallerVersion"

# packaging\ must not shadow the installed packaging library: PyInstaller imports
# it, and a name clash produces confusing analysis failures. Only a module that
# resolves inside <project>\packaging is a clash; the virtual environment also
# lives inside the project, so comparing against the project root would always
# match site-packages.
$packagingLibrary = (Get-ProcessOutput -FilePath $Python -Arguments @('-c', 'import packaging; print(packaging.__file__)') | Select-Object -Last 1)
$packagingDirectory = (Join-Path $ProjectRoot 'packaging').TrimEnd('\') + '\'
if ($packagingLibrary.StartsWith($packagingDirectory, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "The packaging\ directory shadows the installed packaging library ($packagingLibrary). Rename it or remove its __init__.py."
}
Write-Detail "packaging library: $packagingLibrary"

Write-Step 'Running the backend tests'
$code = Invoke-Process -FilePath $Python `
    -Arguments @('-m', 'unittest', 'discover', '-s', 'tests', '-v') `
    -LogPath (Join-Path $TempRoot 'build-tests.log')
Assert-ExitCode $code 'The backend test run'

Write-Step 'Generating version_info.txt and the application icon'
$code = Invoke-Process -FilePath $Python `
    -Arguments @((Join-Path $PSScriptRoot 'prepare_build.py')) `
    -LogPath (Join-Path $TempRoot 'prepare-build.log')
Assert-ExitCode $code 'packaging\prepare_build.py'

Write-Step 'Building dist\recogniser with PyInstaller'
$pyInstallerArguments = @(
    '-m', 'PyInstaller',
    '--noconfirm',
    '--distpath', (Join-Path $ProjectRoot 'dist'),
    '--workpath', (Join-Path $ProjectRoot 'build\pyinstaller')
)
if ($Clean) {
    $pyInstallerArguments += '--clean'
}
$pyInstallerArguments += $SpecPath
$code = Invoke-Process -FilePath $Python -Arguments $pyInstallerArguments -LogPath (Join-Path $TempRoot 'pyinstaller.log')
Assert-ExitCode $code 'PyInstaller'

Write-Step 'Verifying the bundle inventory'
Test-BundleInventory

Write-Step 'Running the frozen self-test from two working directories'
$selfTestCwd = Join-Path $TempRoot 'selftest-cwd'
New-Item -ItemType Directory -Force -Path $selfTestCwd | Out-Null
Invoke-BundleSelfTest -WorkingDirectory $ProjectRoot -DataDirectory (Join-Path $TempRoot 'selftest-project')
Invoke-BundleSelfTest -WorkingDirectory $selfTestCwd -DataDirectory (Join-Path $TempRoot 'selftest-cwd-data')

Write-Step 'Writing build\bundle-manifest.json'
Write-BundleManifest -Directory $BundleDir -Path $ManifestPath

Write-Step 'Re-verifying the bundle against the manifest it was just recorded from'
$differences = @(Get-BundleManifestProblems -Directory $BundleDir -Path $ManifestPath)
if ($differences.Count -gt 0) {
    foreach ($difference in $differences) {
        Write-Detail $difference
    }
    throw "The bundle changed while it was being recorded ($($differences.Count) file(s)). Rebuild before reviewing."
}
Write-Detail 'manifest matches the bundle exactly'

Write-Step 'Build complete; nothing has been committed or packaged'
Write-Detail "bundle: $BundleDir"
Write-Detail "manifest: $ManifestPath"
Write-Detail 'Review the bundle, then run .\packaging\build.ps1 -Installer once it is accepted.'
