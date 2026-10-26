param([Parameter(Mandatory=$true)][string]$Period, [string]$Url='')
$ErrorActionPreference='Stop'
Set-Location (Join-Path $PSScriptRoot '..')
$python = Join-Path (Get-Location) '.venv\Scripts\python.exe'
$argsList = @('-m','azul_crm.cli','fares','--period',$Period,'--max-mb','50')
if ($Url) { $argsList += @('--url',$Url) }
& $python @argsList
if ($LASTEXITCODE -ne 0) { throw 'Falha na ingestão. A Gold anterior foi preservada.' }
