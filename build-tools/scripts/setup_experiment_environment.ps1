[CmdletBinding()]
param(
    [string]$ExperimentsRoot = $(if ($env:LED_CONTROLLER_EXPERIMENTS_ROOT) {
        $env:LED_CONTROLLER_EXPERIMENTS_ROOT
    } else {
        Join-Path $HOME "source\experiments"
    }),
    [string]$DependencyProjectRoot = (Join-Path $PSScriptRoot "..\.."),
    [string]$PythonVersion = "3.12"
)

$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path $DependencyProjectRoot).Path
$experimentsRootPath = [System.IO.Path]::GetFullPath($ExperimentsRoot)
$venvPath = Join-Path $experimentsRootPath ".venv"
$pythonPath = Join-Path $venvPath "Scripts\python.exe"

$null = Get-Command uv -ErrorAction Stop
New-Item -ItemType Directory -Path $experimentsRootPath -Force | Out-Null

if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) {
    & uv venv $venvPath --python $PythonVersion
    if ($LASTEXITCODE -ne 0) {
        throw "uv venv failed with exit code $LASTEXITCODE"
    }
}

$previousVirtualEnv = $env:VIRTUAL_ENV
try {
    $env:VIRTUAL_ENV = $venvPath
    & uv sync `
        --active `
        --project $projectRoot `
        --locked `
        --all-groups `
        --no-install-project
    if ($LASTEXITCODE -ne 0) {
        throw "uv sync failed with exit code $LASTEXITCODE"
    }
} finally {
    if ($null -eq $previousVirtualEnv) {
        Remove-Item Env:VIRTUAL_ENV -ErrorAction SilentlyContinue
    } else {
        $env:VIRTUAL_ENV = $previousVirtualEnv
    }
}

& $pythonPath -c "import fastapi, pytest, PySide6, usb, yaml; print('experiment environment verified')"
if ($LASTEXITCODE -ne 0) {
    throw "Experiment environment verification failed with exit code $LASTEXITCODE"
}

[pscustomobject]@{
    ExperimentsRoot = $experimentsRootPath
    VirtualEnv = $venvPath
    Python = $pythonPath
    DependencyProject = $projectRoot
}
