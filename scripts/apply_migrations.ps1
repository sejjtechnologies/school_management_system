<#
PowerShell helper to apply Alembic migrations for this project.

Usage:
  ./scripts/apply_migrations.ps1            # Uses current environment (ensure DATABASE_URL is set)
  ./scripts/apply_migrations.ps1 -UseEnvFile # Loads variables from .env into process env then runs alembic

#>

param(
    [switch]$UseEnvFile
)

Set-StrictMode -Version Latest

function Load-EnvFile {
    param([string]$Path = '.env')
    if (-Not (Test-Path $Path)) { return }
    Get-Content $Path | ForEach-Object {
        if ($_ -match '^[ \t]*#') { return }
        if ($_ -match '^\s*([^=]+)=(.*)$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim().Trim('"')
            Write-Host "Setting env: $name"
            $env:$name = $value
        }
    }
}

if ($UseEnvFile) {
    Write-Host "Loading .env into environment..."
    Load-EnvFile -Path '.env'
}

if (-not $env:DATABASE_URL) {
    Write-Host "ERROR: DATABASE_URL not set in the environment. Set it or run with -UseEnvFile if you have a .env file." -ForegroundColor Red
    exit 1
}

Write-Host "DATABASE_URL is set. Running alembic upgrade head..."

& python -m alembic upgrade head

if ($LASTEXITCODE -ne 0) {
    Write-Host "alembic failed with exit code $LASTEXITCODE" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "Migrations applied successfully." -ForegroundColor Green
