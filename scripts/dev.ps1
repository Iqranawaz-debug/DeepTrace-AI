param([ValidateSet('backend', 'frontend', 'migrate')][string]$Target = 'backend')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
if ($Target -eq 'frontend') {
    Push-Location (Join-Path $projectRoot 'frontend')
    try { & npm.cmd run dev; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
    finally { Pop-Location }
} else {
    Push-Location (Join-Path $projectRoot 'backend')
    try {
        $action = if ($Target -eq 'migrate') { 'migrate' } else { 'serve' }
        & .\.venv\Scripts\python.exe -m deeptrace $action
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    } finally { Pop-Location }
}
