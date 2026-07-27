$ErrorActionPreference = "Stop"

Push-Location $PSScriptRoot
try {
    $tectonic = Get-Command tectonic -ErrorAction SilentlyContinue
    if (-not $tectonic) {
        $localTectonic = Join-Path $PSScriptRoot "..\tools\tectonic\tectonic.exe"
        if (Test-Path -LiteralPath $localTectonic) {
            $tectonic = Get-Item -LiteralPath $localTectonic
        } else {
            throw "Tectonic was not found. Install it or add tectonic.exe to PATH."
        }
    }

    & $tectonic.Source "main.tex" "--keep-logs" "--keep-intermediates"
    if ($LASTEXITCODE -ne 0) {
        throw "LaTeX build failed with exit code $LASTEXITCODE."
    }
} finally {
    Pop-Location
}
