$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location (Join-Path $projectRoot 'backend')
try {
    & .\.venv\Scripts\ruff.exe check src tests
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & .\.venv\Scripts\ruff.exe format --check src tests
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & .\.venv\Scripts\mypy.exe src
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    $testDirectory = '.cache/test-' + [guid]::NewGuid().ToString('N')
    & .\.venv\Scripts\python.exe -m pytest -q "--basetemp=$testDirectory"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} finally { Pop-Location }
Push-Location (Join-Path $projectRoot 'frontend')
try {
    foreach ($command in @('lint', 'typecheck', 'test', 'build', 'test:browser')) {
        & npm.cmd run $command
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
} finally { Pop-Location }
