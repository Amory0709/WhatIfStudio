# PROTOTYPE — clone official FaceFusion into vendor/ (optional)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Vendor = Join-Path $Root "vendor"
$FF = Join-Path $Vendor "facefusion"

if (Test-Path (Join-Path $FF "facefusion.py")) {
    Write-Host "FaceFusion already at $FF" -ForegroundColor Green
    exit 0
}

New-Item -ItemType Directory -Force -Path $Vendor | Out-Null
Write-Host "Cloning FaceFusion into $FF ..."
git clone --depth 1 https://github.com/facefusion/facefusion.git $FF
Set-Location $FF
$Py = "C:\Projects\MY\WhatIfStudio\apps\api\.venv\Scripts\python.exe"
if (-not (Test-Path $Py)) { $Py = "python" }
& $Py install.py --onnxruntime default --skip-conda
Write-Host "Done. Set FACEFUSION_HOME=$FF or run prototype/facefusion/run.py cli ..." -ForegroundColor Green
