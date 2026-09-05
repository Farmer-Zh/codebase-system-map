[CmdletBinding()]
param(
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $true
$projectRoot = Split-Path -Parent $PSScriptRoot
$virtualEnvironment = Join-Path $projectRoot ".venv"
$virtualPython = Join-Path $virtualEnvironment "Scripts\python.exe"

function Assert-NativeCommandSucceeded {
    param([string]$Stage)
    if ($LASTEXITCODE -ne 0) { throw "$Stage failed with exit code $LASTEXITCODE." }
}

$pythonCommand = Get-Command $Python -ErrorAction SilentlyContinue
if (-not $pythonCommand) {
    throw "Python executable not found: $Python. Pass -Python with a Python 3.12+ executable."
}
$pythonExecutable = $pythonCommand.Source

if (-not (Test-Path -LiteralPath $virtualPython)) {
    & $pythonExecutable -m venv $virtualEnvironment
    Assert-NativeCommandSucceeded "Virtual environment creation"
}

& $virtualPython -m pip install --upgrade pip setuptools
Assert-NativeCommandSucceeded "Python packaging tool installation"
& $virtualPython -m pip install --editable $projectRoot --no-build-isolation
Assert-NativeCommandSucceeded "Codebase System Map installation"

if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    throw "Node.js 18+ is required for the bundled SVG renderer."
}

Write-Host "Codebase System Map installed. Run: .venv\Scripts\codebase-map.exe <repository>"
