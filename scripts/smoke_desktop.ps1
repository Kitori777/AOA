param(
    [string]$Executable
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
if ([string]::IsNullOrWhiteSpace($Executable)) {
    $Executable = Join-Path $projectRoot "dist\AOA\AOA.exe"
}
$resolvedExecutable = (Resolve-Path -LiteralPath $Executable).Path
$smokeDir = Join-Path $projectRoot "build\desktop-smoke"
New-Item -ItemType Directory -Path $smokeDir -Force | Out-Null
$marker = Join-Path $smokeDir "smoke-result.json"
$userData = Join-Path $smokeDir "user-data"
Remove-Item -LiteralPath $marker -Force -ErrorAction SilentlyContinue

$previousMarker = $env:AOA_SMOKE_MARKER
$previousUserData = $env:AOA_USER_DATA_DIR
$env:AOA_SMOKE_MARKER = $marker
$env:AOA_USER_DATA_DIR = $userData
try {
    $process = Start-Process -FilePath $resolvedExecutable -ArgumentList "--smoke-test" -Wait -PassThru -WindowStyle Hidden
    if ($process.ExitCode -ne 0) {
        throw "Test uruchomienia zakonczyl sie kodem $($process.ExitCode)."
    }
    if (-not (Test-Path -LiteralPath $marker)) {
        throw "Aplikacja nie zapisala znacznika testu uruchomienia."
    }
    $result = Get-Content -LiteralPath $marker -Raw | ConvertFrom-Json
    if (-not $result.frozen) {
        throw "Testowana aplikacja nie dziala jako paczka desktopowa."
    }
    foreach ($sampleName in @("sample_table.csv", "bom.csv", "inventory.csv", "schedule.csv")) {
        if (-not (Test-Path -LiteralPath (Join-Path $userData "data\sample\$sampleName"))) {
            throw "Pierwsze uruchomienie nie przygotowalo pliku $sampleName."
        }
    }
    Write-Output "DESKTOP_SMOKE_OK version=$($result.version)"
} finally {
    $env:AOA_SMOKE_MARKER = $previousMarker
    $env:AOA_USER_DATA_DIR = $previousUserData
}
