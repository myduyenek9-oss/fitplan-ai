$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$packageManager = if (Get-Command npm -ErrorAction SilentlyContinue) { "npm" } elseif (Get-Command pnpm -ErrorAction SilentlyContinue) { "pnpm" } else { throw "npm or pnpm is required" }

Push-Location $root
try {
    python -m pytest backend -q
    Push-Location frontend
    try {
        & $packageManager run test -- --run
        & $packageManager run build
    }
    finally {
        Pop-Location
    }
}
finally {
    Pop-Location
}
