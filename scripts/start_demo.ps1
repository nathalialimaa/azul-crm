$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')
$python = Join-Path (Get-Location) '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) {
    py -3.12 -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Instale Python 3.12 e execute novamente.' }
}
& $python -m pip install -e '.[dev]'
if ($LASTEXITCODE -ne 0) { throw 'Instalação falhou.' }
if (-not (Test-Path '.env')) { Copy-Item '.env.example' '.env' }
$env:CRM_STORAGE='sqlite'
$env:CRM_UI_MODE='local'
& $python -m streamlit run streamlit_app.py
