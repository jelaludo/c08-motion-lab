param([switch]$NoBrowser)
$ErrorActionPreference='Stop'
$predictiveWorkspace=$PSScriptRoot
$url='http://127.0.0.1:8791/mb-predictive/'
$env:PYTHONUTF8='1'
$env:WARP_CACHE_PATH=Join-Path $predictiveWorkspace 'cache\warp'
$env:CUDA_CACHE_PATH=Join-Path $predictiveWorkspace 'cache\cuda'
$env:PYTHONPYCACHEPREFIX=Join-Path $predictiveWorkspace 'cache\pycache'
$env:PATH="$(Join-Path $predictiveWorkspace 'upstream\.venv\Scripts');$env:PATH"
$listening=Get-NetTCPConnection -LocalPort 8791 -State Listen -ErrorAction SilentlyContinue
if(-not $listening){
 $server=Start-Process -FilePath (Join-Path $predictiveWorkspace 'upstream\.venv\Scripts\python.exe') -ArgumentList @('-X','utf8','-u',('"'+(Join-Path $predictiveWorkspace 'tools\mb_predictive_server.py')+'"')) -WorkingDirectory $predictiveWorkspace -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $predictiveWorkspace 'logs\mb-predictive-server.log') -RedirectStandardError (Join-Path $predictiveWorkspace 'logs\mb-predictive-server-error.log')
 $server.Id | Set-Content (Join-Path $predictiveWorkspace 'logs\mb-predictive-server.pid')
}
Write-Host $url
if(-not $NoBrowser){Start-Process $url}
