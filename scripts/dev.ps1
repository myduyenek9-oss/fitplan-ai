$root = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $root ".venv\Scripts\python.exe"
$python = if (Test-Path $venvPython) { $venvPython } else { "python" }

if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    $codexNodeBin = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin"
    if (Test-Path (Join-Path $codexNodeBin "node.exe")) {
        $env:Path = "$codexNodeBin;$env:Path"
    }
}

$packageManager = if (Get-Command npm -ErrorAction SilentlyContinue) {
    "npm"
} elseif (Get-Command pnpm -ErrorAction SilentlyContinue) {
    "pnpm"
} else {
    throw "npm or pnpm is required"
}

Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location -LiteralPath '$root'; & '$python' -m uvicorn app.main:app --app-dir backend --reload"
)

Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location -LiteralPath '$root\frontend'; $packageManager run dev"
)
