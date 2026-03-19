Param(
    [switch]$Clean
)

$ErrorActionPreference = "Stop"

Write-Host "[1/3] Installing dependencies..." -ForegroundColor Cyan
python -m pip install --upgrade pyinstaller playwright pystray pillow
if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed." }

if ($Clean) {
    Write-Host "[2/3] Cleaning old build artifacts..." -ForegroundColor Cyan
    if (Test-Path ".\build") { Remove-Item ".\build" -Recurse -Force }
    if (Test-Path ".\dist") { Remove-Item ".\dist" -Recurse -Force }
    if (Test-Path ".\auto_login_portal.spec") { Remove-Item ".\auto_login_portal.spec" -Force }
}

Write-Host "[3/3] Building exe (system Edge/Chrome)..." -ForegroundColor Cyan
pyinstaller --onefile --noconsole auto_login_portal.py --hidden-import=pystray --hidden-import=PIL --hidden-import=playwright.sync_api --exclude-module=numpy
if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed." }

if (-not (Test-Path ".\dist\auto_login_portal.exe")) {
    throw "Build completed but dist/auto_login_portal.exe was not found."
}

Write-Host "Done. Output: .\dist\auto_login_portal.exe" -ForegroundColor Green
Write-Host "Note: Target machine must have Microsoft Edge or Google Chrome installed." -ForegroundColor Yellow