param(
    [string]$BuildDirectory,
    [string]$InstalledDirectory = "$env:LOCALAPPDATA\Programs\AOA"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
if ([string]::IsNullOrWhiteSpace($BuildDirectory)) {
    $BuildDirectory = Join-Path $projectRoot "dist\AOA"
}
$buildRoot = (Resolve-Path -LiteralPath $BuildDirectory).Path
$installedRoot = (Resolve-Path -LiteralPath $InstalledDirectory).Path
$relativeFiles = @(
    "AOA.exe",
    "_internal\AOA\assets\assistant\model_pack.json",
    "_internal\docs\guide.md",
    "_internal\docs\theory.md",
    "_internal\data\esm\esm_jobs.csv",
    "_internal\data\esm\examples\esm_jobs_05_tight_deadlines.csv",
    "_internal\data\esm\examples\esm_jobs_06_component_wait.csv",
    "_internal\data\esm\examples\esm_jobs_07_parallel_balance.csv",
    "_internal\data\esm\examples\esm_jobs_08_changeovers.csv",
    "_internal\data\esm\examples\esm_jobs_09_urgent_mix.csv",
    "_internal\data\esm\examples\esm_jobs_10_mixed_constraints.csv",
    "_internal\AOA\assets\brand\aoa.ico",
    "_internal\AOA\assets\brand\aoa_logo.png"
)

$matched = 0
foreach ($relative in $relativeFiles) {
    $built = Join-Path $buildRoot $relative
    $installed = Join-Path $installedRoot $relative
    if (-not (Test-Path -LiteralPath $built) -or -not (Test-Path -LiteralPath $installed)) {
        throw "Brak pliku do porownania: $relative"
    }
    $builtHash = (Get-FileHash -LiteralPath $built -Algorithm SHA256).Hash
    $installedHash = (Get-FileHash -LiteralPath $installed -Algorithm SHA256).Hash
    if ($builtHash -ne $installedHash) {
        throw "Rozny skrot SHA256: $relative"
    }
    $matched += 1
}

Write-Output "INSTALL_OK HASH_MATCH=$matched/$($relativeFiles.Count)"
