# Helper to load DATABASE_URL from .env and run backup_and_migrate.ps1
$envFile = Join-Path (Get-Location) '.env'
if (-not (Test-Path $envFile)) {
    Write-Error '.env not found in current directory. Please run this from the project root.'
    exit 1
}

# Find the first line that starts with DATABASE_URL=
$lines = Get-Content -Path $envFile
$lineObj = $lines | Where-Object { $_ -match '^\s*DATABASE_URL\s*=' } | Select-Object -First 1
if (-not $lineObj) {
    Write-Error 'DATABASE_URL not found in .env'
    exit 2
}

# Extract value and trim surrounding quotes
$db = $lineObj -replace '^\s*DATABASE_URL\s*=', ''
## Normalize: trim whitespace and remove surrounding matching quotes if present
$db = $db.Trim()
if (( $db.StartsWith("'") -and $db.EndsWith("'") ) -or ( $db.StartsWith('"') -and $db.EndsWith('"') )) {
    $db = $db.Substring(1, $db.Length - 2)
}

# Set environment variable (value is not printed)
$env:DATABASE_URL = $db
Write-Host 'DATABASE_URL loaded from .env (hidden)'

# Run the backup-and-migrate script
& .\scripts\backup_and_migrate.ps1

# End
