<#
  Launch the FreightSight API for local development.

  Loads the repo-root .env (the app itself does NOT read .env), activates the
  venv, and starts uvicorn with --reload on :8000.

  Usage (from anywhere):
      pwsh backend/scripts/dev.ps1
      pwsh backend/scripts/dev.ps1 -NoDb      # ignore DATABASE_URL, run CSV-only

  With DATABASE_URL set in .env you get the Supabase-backed app (live vessels,
  freight-rate history). Without it, the app still runs from the bundled CSV.
#>
param([switch]$NoDb)

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$envFile = Join-Path $repo ".env"

if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#")) { return }
        $i = $line.IndexOf("=")
        if ($i -lt 1) { return }
        $name = $line.Substring(0, $i).Trim()
        $value = $line.Substring($i + 1).Trim()
        if ($NoDb -and $name -eq "DATABASE_URL") { return }
        Set-Item -Path "Env:$name" -Value $value
    }
    Write-Host "loaded .env ($envFile)" -ForegroundColor DarkGray
} else {
    Write-Host "no .env found - running CSV-only" -ForegroundColor Yellow
}

if ($NoDb) { $env:DATABASE_URL = "" }
if ($env:DATABASE_URL) {
    Write-Host "DATABASE_URL set -> Supabase-backed" -ForegroundColor Green
} else {
    Write-Host "no DATABASE_URL -> bundled CSV" -ForegroundColor Cyan
}

Set-Location (Join-Path $repo "backend")
& ".venv\Scripts\Activate.ps1"
python -m uvicorn app.main:app --port 8000 --reload
