# Start API only (Windows). Run web separately: npm run dev:web:win
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location "$Root\apps\api"

function Find-Python {
    $candidates = @(
        "$Root\apps\api\.venv\Scripts\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe"
    )
    foreach ($p in $candidates) {
        if (Test-Path $p) { return $p }
    }
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd -and $cmd.Source -notmatch "WindowsApps") { return $cmd.Source }
    return $null
}

$Py = Find-Python
if (-not $Py) {
    Write-Host "Install Python 3.12: winget install Python.Python.3.12" -ForegroundColor Red
    exit 1
}

$VenvPy = "$Root\apps\api\.venv\Scripts\python.exe"
if (-not (Test-Path $VenvPy)) {
    & $Py -m venv "$Root\apps\api\.venv"
    & $VenvPy -m pip install --upgrade pip
    $req = if (Test-Path "$Root\apps\api\requirements-windows.txt") {
        "$Root\apps\api\requirements-windows.txt"
    } else {
        "$Root\apps\api\requirements.txt"
    }
    & $VenvPy -m pip install -r $req
}

$env:GALLERY_DIR = (Resolve-Path "$Root\apps\web\public\gallery").Path
$env:WHATIF_ENGINE_DIR = (Resolve-Path "$Root\apps\api\engine").Path
$env:ALLOWED_ORIGIN = "http://127.0.0.1:3000,http://localhost:3000"
$env:WHATIF_SWAP_MODEL = "inswapper_128"
$env:WHATIF_SWAP_SOURCE_WEIGHT = "0.76"
$env:WHATIF_PRESERVE_EXPRESSION = "0.82"
$env:WHATIF_SWAP_SHARPNESS = "0.45"

Write-Host "API -> http://127.0.0.1:8000" -ForegroundColor Green
& $VenvPy -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
