$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
  python -m venv .venv
  .\.venv\Scripts\pip install -r requirements.txt
}

if (-not (Test-Path ".\artifacts\itemknn_pipeline.pkl")) {
  Write-Host "Training the LensKit model (this can take a while)..."
  .\.venv\Scripts\python -m backend.train
}

if (-not (Test-Path ".\frontend\node_modules")) {
  Push-Location frontend
  npm install
  Pop-Location
}

Start-Process -FilePath ".\.venv\Scripts\python.exe" -ArgumentList "-m","uvicorn","backend.app:app","--host","127.0.0.1","--port","8000"
Push-Location frontend
npm run dev
Pop-Location
