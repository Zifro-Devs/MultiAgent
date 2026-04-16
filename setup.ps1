# -----------------------------------------------------------------
# DevTeam AI - Windows Setup Script
# -----------------------------------------------------------------

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  DevTeam AI - Project Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Create virtual environment
if (-not (Test-Path ".venv")) {
    Write-Host "[1/5] Creating virtual environment..." -ForegroundColor Yellow
    python -m venv .venv
} else {
    Write-Host "[1/5] Virtual environment already exists." -ForegroundColor Green
}

# 2. Activate
Write-Host "[2/5] Activating virtual environment..." -ForegroundColor Yellow
& .\.venv\Scripts\Activate.ps1

# 3. Install dependencies
Write-Host "[3/5] Installing dependencies..." -ForegroundColor Yellow
pip install -U pip | Out-Null
pip install -r requirements.txt

# 4. Create required directories
Write-Host "[4/5] Creating directories..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path artifacts | Out-Null
New-Item -ItemType Directory -Force -Path data | Out-Null

# 5. Copy env template
if (-not (Test-Path ".env")) {
    Write-Host "[5/5] Creating .env from template..." -ForegroundColor Yellow
    Copy-Item .env.example .env
    Write-Host ""
    Write-Host "  IMPORTANT: Edit .env and set your API keys!" -ForegroundColor Red
} else {
    Write-Host "[5/5] .env already exists." -ForegroundColor Green
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Setup complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Next steps:" -ForegroundColor White
Write-Host "    1. Start Ollama: ollama serve" -ForegroundColor White
Write-Host "    2. Pull model:   ollama pull qwen3:4b" -ForegroundColor White
Write-Host "    3. Activate:     .\.venv\Scripts\Activate.ps1" -ForegroundColor White
Write-Host "    4. Run:          streamlit run app.py" -ForegroundColor White
Write-Host ""
