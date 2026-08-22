# Local dev launcher for Windows (API :8000 + Next.js :3000)
# Usage: .\scripts\start-local.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

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

Write-Host "== WhatIf Studio local dev ==" -ForegroundColor Cyan

# Git LFS models (inswapper + buffalo_l)
if (Get-Command git -ErrorAction SilentlyContinue) {
    Write-Host "Pulling Git LFS models..." -ForegroundColor Yellow
    git lfs pull 2>&1 | Out-Host
}

$Inswapper = Join-Path $Root "apps\api\engine\models\inswapper_128.onnx"
if (-not (Test-Path $Inswapper)) {
    Write-Error "Missing $Inswapper — run: git lfs pull"
}

# Node deps
if (-not (Test-Path "$Root\node_modules")) {
    Write-Host "Installing npm dependencies..." -ForegroundColor Yellow
    npm install
}

# Python venv
$Py = Find-Python
if (-not $Py) {
    Write-Host ""
    Write-Host "Python 3.11+ not found." -ForegroundColor Red
    Write-Host "Install: winget install Python.Python.3.12" -ForegroundColor Yellow
    Write-Host "Then re-run: .\scripts\start-local.ps1" -ForegroundColor Yellow
    exit 1
}

$VenvPy = Join-Path $Root "apps\api\.venv\Scripts\python.exe"
if (-not (Test-Path $VenvPy)) {
    Write-Host "Creating venv with $Py ..." -ForegroundColor Yellow
    & $Py -m venv "$Root\apps\api\.venv"
    & $VenvPy -m pip install --upgrade pip
    $req = if (Test-Path "$Root\apps\api\requirements-windows.txt") {
        "$Root\apps\api\requirements-windows.txt"
    } else {
        "$Root\apps\api\requirements.txt"
    }
    & $VenvPy -m pip install -r $req
}

$Gallery = (Resolve-Path "$Root\apps\web\public\gallery").Path
$Engine = (Resolve-Path "$Root\apps\api\engine").Path
$LanIp = (
    Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object {
        $_.IPAddress -notmatch '^127\.' -and
        $_.IPAddress -notmatch '^169\.254\.' -and
        $_.PrefixOrigin -eq 'Dhcp'
    } |
    Select-Object -First 1 -ExpandProperty IPAddress
)
if (-not $LanIp) { $LanIp = '127.0.0.1' }
$PublicUrl = "http://$LanIp`:3000"

Write-Host ""
Write-Host "Starting API  -> http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "Starting Web  -> http://127.0.0.1:3000" -ForegroundColor Green
Write-Host "Phone upload URL base -> $PublicUrl" -ForegroundColor Green
Write-Host "Press Ctrl+C in each terminal to stop." -ForegroundColor DarkGray
Write-Host ""

$ApiCmd = @"
Set-Location '$Root\apps\api'
`$env:GALLERY_DIR = '$Gallery'
`$env:WHATIF_ENGINE_DIR = '$Engine'
`$env:ALLOWED_ORIGIN = 'http://127.0.0.1:3000,http://localhost:3000,$PublicUrl'
`$env:PUBLIC_BASE_URL = '$PublicUrl'
`$env:WHATIF_SWAP_MODEL = 'inswapper_128'
`$env:WHATIF_SWAP_SOURCE_WEIGHT = '0.76'
`$env:WHATIF_PRESERVE_EXPRESSION = '0.82'
`$env:WHATIF_SWAP_SHARPNESS = '0.45'
& '$VenvPy' -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
"@

$WebCmd = @"
Set-Location '$Root'
`$env:NEXT_PUBLIC_API_URL = 'http://127.0.0.1:8000'
`$env:NEXT_PUBLIC_PUBLIC_URL = '$PublicUrl'
npm --workspace apps/web run dev -- -H 0.0.0.0 -p 3000
"@

Start-Process powershell -ArgumentList "-NoExit", "-Command", $ApiCmd
Start-Sleep -Seconds 2
Start-Process powershell -ArgumentList "-NoExit", "-Command", $WebCmd
