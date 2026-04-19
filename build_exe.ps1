$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$Python = Join-Path $Root "venv\Scripts\python.exe"
if (!(Test-Path $Python)) {
    $Python = "python"
}

Write-Host "[1/4] Installing Python requirements..."
& $Python -m pip install -r requirements.txt

Write-Host "[2/4] Installing Playwright Chromium..."
& $Python -m playwright install chromium

Write-Host "[3/4] Building EXE with PyInstaller..."
& $Python -m PyInstaller `
    --noconfirm `
    --clean `
    --name BlogAutomation `
    --onedir `
    --collect-all playwright `
    --hidden-import=google.generativeai `
    --hidden-import=bs4 `
    app.py

Write-Host "[4/4] Preparing writable data folders..."
$DistApp = Join-Path $Root "dist\BlogAutomation"
New-Item -ItemType Directory -Force -Path (Join-Path $DistApp "source_data") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $DistApp "text_generated") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $DistApp "tistory_user_data") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $DistApp "tistory_debug") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $DistApp "blog_prompts") | Out-Null

if (Test-Path (Join-Path $Root ".env")) {
    Copy-Item (Join-Path $Root ".env") (Join-Path $DistApp ".env") -Force
}

if (Test-Path (Join-Path $Root "blog_prompts")) {
    Copy-Item (Join-Path $Root "blog_prompts\*.md") (Join-Path $DistApp "blog_prompts") -Force -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "Build complete:"
Write-Host "  $DistApp\BlogAutomation.exe"
Write-Host ""
Write-Host "Run BlogAutomation.exe. It will open http://127.0.0.1:5000 automatically."
