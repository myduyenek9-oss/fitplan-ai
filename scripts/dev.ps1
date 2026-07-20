$root = Split-Path -Parent $PSScriptRoot
$packageManager = if (Get-Command npm -ErrorAction SilentlyContinue) { "npm" } elseif (Get-Command pnpm -ErrorAction SilentlyContinue) { "pnpm" } else { throw "npm or pnpm is required" }

Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location -LiteralPath '$root'; python -m uvicorn app.main:app --app-dir backend --reload"
)

Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location -LiteralPath '$root\frontend'; $packageManager run dev"
)
