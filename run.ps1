# Run from backend/ after: .\venv\Scripts\Activate.ps1
# Equivalent to: python -m app.main

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".\venv\Scripts\Activate.ps1")) {
    Write-Host "Creating virtual environment..."
    python -m venv venv
    .\venv\Scripts\Activate.ps1
    pip install -r requirements.txt
} else {
    .\venv\Scripts\Activate.ps1
}

python -m app.main
