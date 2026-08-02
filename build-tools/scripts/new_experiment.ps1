[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern("^[A-Za-z0-9][A-Za-z0-9._-]*$")]
    [string]$Name,
    [string]$ExperimentsRoot = $(if ($env:LED_CONTROLLER_EXPERIMENTS_ROOT) {
        $env:LED_CONTROLLER_EXPERIMENTS_ROOT
    } else {
        Join-Path $HOME "source\experiments"
    }),
    [string]$SourceRoot = (Join-Path $PSScriptRoot "..\.."),
    [switch]$SkipEnvironmentSetup
)

$ErrorActionPreference = "Stop"

$sourceRoot = (Resolve-Path $SourceRoot).Path
$branch = (& git -C $sourceRoot branch --show-current).Trim()
if ($LASTEXITCODE -ne 0 -or $branch -ne "main") {
    throw "Experiments must be created from main. Current branch: $branch"
}

$dirty = @(& git -C $sourceRoot status --porcelain=v1)
if ($LASTEXITCODE -ne 0) {
    throw "Unable to inspect source repository"
}
if ($dirty.Count -gt 0) {
    throw "The source repository must be clean before creating an experiment."
}

$baseCommit = (& git -C $sourceRoot rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0) {
    throw "Unable to resolve source commit"
}

$experimentsRootPath = [System.IO.Path]::GetFullPath($ExperimentsRoot)
$targetPath = Join-Path $experimentsRootPath $Name
if (Test-Path -LiteralPath $targetPath) {
    throw "Experiment already exists: $targetPath"
}

New-Item -ItemType Directory -Path $experimentsRootPath -Force | Out-Null
& git clone --no-hardlinks --single-branch --branch main $sourceRoot $targetPath
if ($LASTEXITCODE -ne 0) {
    throw "git clone failed with exit code $LASTEXITCODE"
}

& git -C $targetPath config experiment.sourcePath $sourceRoot
& git -C $targetPath config experiment.baseCommit $baseCommit
& git -C $targetPath remote remove origin
if ($LASTEXITCODE -ne 0) {
    throw "Unable to detach experiment from its clone remote"
}

if (-not $SkipEnvironmentSetup) {
    & (Join-Path $PSScriptRoot "setup_experiment_environment.ps1") `
        -ExperimentsRoot $experimentsRootPath `
        -DependencyProjectRoot $sourceRoot
}

[pscustomobject]@{
    Name = $Name
    Path = $targetPath
    BaseCommit = $baseCommit
    Python = Join-Path $experimentsRootPath ".venv\Scripts\python.exe"
}
