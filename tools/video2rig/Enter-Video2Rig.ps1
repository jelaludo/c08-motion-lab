param([Parameter(Mandatory=$true)][string]$ExperimentRoot)
$ErrorActionPreference='Stop'
$video2rigRoot=(Resolve-Path -LiteralPath $ExperimentRoot).Path
$motionBricksWorkspace=Split-Path (Split-Path $video2rigRoot -Parent) -Parent
$env:UV_CACHE_DIR=(Join-Path $motionBricksWorkspace 'cache\uv')
$env:HF_HOME=Join-Path $video2rigRoot 'cache\huggingface'
$env:HF_HUB_CACHE=Join-Path $env:HF_HOME 'hub'
$env:HF_XET_CACHE=Join-Path $env:HF_HOME 'xet'
$env:CUDA_CACHE_PATH=Join-Path $video2rigRoot 'cache\cuda'
$env:TRITON_CACHE_DIR=Join-Path $video2rigRoot 'cache\triton'
$env:TORCHINDUCTOR_CACHE_DIR=Join-Path $video2rigRoot 'cache\torchinductor'
$env:TORCH_HOME=Join-Path $video2rigRoot 'cache\torch'
$env:LOCALAPPDATA=Join-Path $video2rigRoot 'cache\localappdata'
$env:TEMP=Join-Path $video2rigRoot 'cache\temp'
$env:TMP=$env:TEMP
$env:PYTHONPYCACHEPREFIX=Join-Path $video2rigRoot 'cache\pycache'
$env:PYTHONUTF8='1'
$env:V2R_BLENDER=(Join-Path $motionBricksWorkspace 'tools\blender-4.5.15-windows-x64\blender.exe')
$env:V2R_FFMPEG=(Join-Path $motionBricksWorkspace 'video-mocap\tools\ffmpeg.exe')
foreach($video2rigCache in @($env:CUDA_CACHE_PATH,$env:TRITON_CACHE_DIR,$env:TORCHINDUCTOR_CACHE_DIR,$env:HF_HOME,$env:HF_HUB_CACHE,$env:HF_XET_CACHE,$env:TORCH_HOME,$env:LOCALAPPDATA,$env:TEMP,$env:PYTHONPYCACHEPREFIX)){New-Item -ItemType Directory -Force -Path $video2rigCache | Out-Null}
Set-Location (Join-Path $video2rigRoot 'upstream')
