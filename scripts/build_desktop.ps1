param(
    [switch]$SkipInstaller
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$version = (& $python -c "from AOA import __version__; print(__version__)").Trim()

Push-Location $projectRoot
try {
    & $python -m PyInstaller --noconfirm --clean "packaging\aoa.spec"
    if ($LASTEXITCODE -ne 0) {
        throw "Budowanie aplikacji PyInstaller nie powiodlo sie."
    }

    & (Join-Path $PSScriptRoot "smoke_desktop.ps1")

    if (-not $SkipInstaller) {
        $isccCommand = Get-Command iscc.exe -ErrorAction SilentlyContinue
        $isccPath = if ($null -ne $isccCommand) { $isccCommand.Source } else { $null }
        if ([string]::IsNullOrWhiteSpace($isccPath)) {
            $isccCandidates = @(
                (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 7\ISCC.exe"),
                "C:\Program Files\Inno Setup 7\ISCC.exe",
                "C:\Program Files (x86)\Inno Setup 7\ISCC.exe",
                "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
            )
            foreach ($candidate in $isccCandidates) {
                if (Test-Path -LiteralPath $candidate) {
                    $isccPath = $candidate
                    break
                }
            }
        }
        if ([string]::IsNullOrWhiteSpace($isccPath)) {
            throw "Nie znaleziono Inno Setup 6. Zbudowana aplikacja jest w dist\AOA, ale instalator nie powstal."
        }
        & $isccPath "/DMyAppVersion=$version" "packaging\installer.iss"
        if ($LASTEXITCODE -ne 0) {
            throw "Budowanie instalatora nie powiodlo sie."
        }
    }
} finally {
    Pop-Location
}
