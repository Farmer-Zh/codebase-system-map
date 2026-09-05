[CmdletBinding()]
param(
    [string]$Python = "python"
)

# Compatibility alias. The package now has one general setup entry point.
& (Join-Path $PSScriptRoot "setup.ps1") -Python $Python
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
