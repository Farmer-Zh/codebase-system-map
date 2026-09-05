[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$RepositoryPath,
    [string]$OutputDirectory,
    [string]$Language = "zh",
    [switch]$ForceAnalysis
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$cli = Join-Path $projectRoot ".venv\Scripts\repo-atlas.exe"
if (-not (Test-Path -LiteralPath $cli -PathType Leaf)) {
    throw "RepoAtlas is not installed. Run .\scripts\setup.ps1 first."
}

$arguments = @(
    "build",
    $RepositoryPath,
    "--config", (Join-Path $projectRoot ".env"),
    "--work-dir", (Join-Path $projectRoot "data"),
    "--language", $Language
)
if (-not [string]::IsNullOrWhiteSpace($OutputDirectory)) {
    $arguments += @("--output", $OutputDirectory)
}
if ($ForceAnalysis) {
    $arguments += "--force-analysis"
}

& $cli @arguments
if ($LASTEXITCODE -ne 0) {
    throw "RepoAtlas build failed with exit code $LASTEXITCODE."
}
