$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$venvPython = Join-Path $root ".venv\Scripts\python.exe"
$python = if (Test-Path -LiteralPath $venvPython) { $venvPython } else { "python" }

function Get-NodeVersion {
    $node = Get-Command node -ErrorAction SilentlyContinue
    if (-not $node) {
        return $null
    }

    $versionText = (& $node.Source --version).Trim()
    if ($LASTEXITCODE -ne 0) {
        return $null
    }

    try {
        return [version]($versionText.TrimStart("v"))
    }
    catch {
        return $null
    }
}

function Test-ViteNodeVersion {
    param([version]$Version)

    return $null -ne $Version -and (
        ($Version.Major -eq 20 -and $Version -ge [version]"20.19.0") -or
        ($Version.Major -ge 22 -and $Version -ge [version]"22.12.0")
    )
}

function Assert-NodeVersion {
    $version = Get-NodeVersion
    if (-not (Test-ViteNodeVersion $version)) {
        $codexNodeBin = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin"
        $codexNode = Join-Path $codexNodeBin "node.exe"
        if (Test-Path -LiteralPath $codexNode) {
            $env:Path = "$codexNodeBin$([IO.Path]::PathSeparator)$env:Path"
            $version = Get-NodeVersion
        }
    }

    if (-not (Test-ViteNodeVersion $version)) {
        throw "Vite 7 requires Node.js ^20.19.0 or >=22.12.0; found '$version'."
    }
}

Assert-NodeVersion
$packageManager = if (Get-Command pnpm -ErrorAction SilentlyContinue) {
    "pnpm"
} elseif (Get-Command npm -ErrorAction SilentlyContinue) {
    "npm"
} else {
    throw "pnpm is the primary package manager; npm is the fallback. Neither command is available."
}

Start-Process -FilePath "powershell.exe" -WorkingDirectory $root -ArgumentList @(
    "-NoProfile",
    "-NoExit",
    "-Command",
    "& '$python' -m uvicorn app.main:app --app-dir backend --reload"
)

Start-Process -FilePath "powershell.exe" -WorkingDirectory (Join-Path $root "frontend") -ArgumentList @(
    "-NoProfile",
    "-NoExit",
    "-Command",
    "$packageManager run dev"
)
