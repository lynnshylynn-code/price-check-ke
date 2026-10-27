$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python -m uvicorn price_check_api.main:app --app-dir src --reload --host 127.0.0.1 --port 8000
