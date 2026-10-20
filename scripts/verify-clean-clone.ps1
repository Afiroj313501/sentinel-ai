<#
Verifies that the published repository works for a new visitor.

Clones the repository into a temporary folder, installs everything from scratch, runs the
backend tests and the frontend build, then starts the backend on a spare port and scans the
sample repository end to end.

Usage, from the repository root:
  .\scripts\verify-clean-clone.ps1
  .\scripts\verify-clean-clone.ps1 -KeepFiles
#>
param(
    [string]$RepoUrl = "https://github.com/Afiroj313501/sentinel-ai.git",
    [string]$Target = (Join-Path $env:TEMP "sentinel-ai-clean-check"),
    [int]$Port = 8765,
    [switch]$KeepFiles
)

# Native tools write progress to stderr, so failures are detected through exit codes instead.
$ErrorActionPreference = "Continue"

function Invoke-Step {
    param([string]$Name, [scriptblock]$Action)
    Write-Host "==> $Name" -ForegroundColor Cyan
    $global:LASTEXITCODE = 0
    & $Action
    if ($LASTEXITCODE -ne 0) { throw "Step failed: $Name (exit code $LASTEXITCODE)" }
}

if (Test-Path $Target) { Remove-Item -Recurse -Force $Target }

$server = $null
$succeeded = $false
try {
    Invoke-Step "Clone $RepoUrl" { git clone --depth 1 $RepoUrl $Target }

    $backend = Join-Path $Target "backend"
    $frontend = Join-Path $Target "frontend"
    $python = Join-Path $backend ".venv\Scripts\python.exe"

    Invoke-Step "Create the backend virtual environment" { python -m venv (Join-Path $backend ".venv") }
    Invoke-Step "Install backend dependencies" {
        & $python -m pip install --quiet -r (Join-Path $backend "requirements-dev.txt")
    }

    Push-Location $backend
    try { Invoke-Step "Run the backend tests" { & $python -m pytest -q } } finally { Pop-Location }

    Push-Location $frontend
    try {
        Invoke-Step "Install frontend dependencies (npm ci)" { npm ci --no-audit --no-fund }
        Invoke-Step "Build the frontend (type-check and bundle)" { npm run build }
        Invoke-Step "Lint the frontend" { npm run lint }
    } finally { Pop-Location }

    Write-Host "==> Start the backend on port $Port" -ForegroundColor Cyan
    $out = Join-Path $Target "uvicorn.out.log"
    $err = Join-Path $Target "uvicorn.err.log"
    $server = Start-Process -FilePath $python `
        -ArgumentList @("-m", "uvicorn", "app.main:app", "--port", "$Port") `
        -WorkingDirectory $backend -PassThru -WindowStyle Hidden `
        -RedirectStandardOutput $out -RedirectStandardError $err

    $base = "http://127.0.0.1:$Port"
    $ready = $false
    for ($i = 0; $i -lt 30; $i++) {
        try {
            Invoke-RestMethod "$base/api/health" -TimeoutSec 2 -ErrorAction Stop | Out-Null
            $ready = $true
            break
        } catch { Start-Sleep -Seconds 1 }
    }
    if (-not $ready) { throw "The backend did not become healthy. See $err" }

    Write-Host "==> Scan the sample repository" -ForegroundColor Cyan
    $zip = Join-Path $Target "vulnerable.zip"
    Compress-Archive -Path (Join-Path $Target "sample-repos\vulnerable-python\*") -DestinationPath $zip -Force -ErrorAction Stop
    $response = curl.exe -s -F "file=@$zip" "$base/api/scans/upload"
    $result = ($response -join "") | ConvertFrom-Json -ErrorAction Stop

    $bandit = $result.scanner_runs | Where-Object { $_.scanner -eq "bandit" }
    if ($bandit.status -ne "completed") { throw "Bandit status was '$($bandit.status)': $($bandit.message)" }
    if ($result.findings.Count -lt 1) { throw "The sample repository produced no findings." }
    $coverage = ($result.scanner_runs | ForEach-Object { "$($_.scanner)=$($_.status)" }) -join ", "
    Write-Host "    $($result.findings.Count) findings. Scanners: $coverage"

    Write-Host "==> Download a Markdown report" -ForegroundColor Cyan
    $report = Invoke-WebRequest "$base/api/scans/$($result.metadata.scan_id)/report?format=markdown" -UseBasicParsing -ErrorAction Stop
    if ($report.StatusCode -ne 200 -or $report.Content -notmatch "Sentinel AI security report") {
        throw "The report download did not return the expected content."
    }

    $succeeded = $true
}
catch {
    Write-Host "FAILED: $($_.Exception.Message)" -ForegroundColor Red
}
finally {
    if ($server -and -not $server.HasExited) { Stop-Process -Id $server.Id -Force }
}

if ($succeeded) {
    Write-Host "All checks passed: a fresh clone installs, tests, builds, and scans." -ForegroundColor Green
    if (-not $KeepFiles) { Remove-Item -Recurse -Force $Target -ErrorAction SilentlyContinue }
} else {
    Write-Host "Files kept for inspection: $Target" -ForegroundColor Yellow
    exit 1
}
