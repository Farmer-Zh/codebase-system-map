[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$RepositoryPath,
    [string]$OutputDirectory,
    [string]$Language = "zh",
    [switch]$ForceAnalysis
)

$arguments = @{
    RepositoryPath = $RepositoryPath
    Language = $Language
    ForceAnalysis = $ForceAnalysis
}
if (-not [string]::IsNullOrWhiteSpace($OutputDirectory)) {
    $arguments.OutputDirectory = $OutputDirectory
}

Write-Warning "build-wiki.ps1 is retained as a compatibility alias; use build-system-map.ps1."
& (Join-Path $PSScriptRoot "build-system-map.ps1") @arguments
