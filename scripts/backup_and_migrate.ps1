<#
PowerShell backup_and_migrate.ps1

Usage: run this from PowerShell in the project root (where alembic.ini lives).
Prereqs:
 - pg_dump, pg_restore, psql available on PATH (Postgres client tools)
 - alembic available in the same Python environment (or in PATH)
 - If using a virtualenv, activate it first (e.g. .\.venv\Scripts\Activate.ps1)

This script will:
 1. Ask or read DATABASE_URL
 2. Run a parallel directory-format pg_dump (-Fd -j) suitable for large DBs
 3. Also create a compressed custom-format dump (-Fc)
 4. Run a validation query to find malformed timetable start_time/end_time rows
 5. If validation passes, prompt to run `alembic upgrade head`

Note: This script does NOT run as superuser; if your managed provider restricts connections, use provider snapshots instead (Neon dashboard/CLI).
#>

Param(
    [string]$DatabaseUrl = $env:DATABASE_URL,
    [int]$ParallelJobs = 8
)

function ExitWithError([string]$msg, [int]$code=1) {
    Write-Error $msg
    exit $code
}

# Prompt for DATABASE_URL if not provided
if (-not $DatabaseUrl -or $DatabaseUrl -eq '') {
    $DatabaseUrl = Read-Host "Enter DATABASE_URL (postgresql://user:pass@host:5432/dbname)"
    if (-not $DatabaseUrl) { ExitWithError "No DATABASE_URL provided. Aborting." }
}

Write-Host "Using DATABASE_URL: $DatabaseUrl"

# Quick connectivity test
Write-Host "Testing connection (psql -c '\l' )..."
try {
    psql $DatabaseUrl -c "SELECT 1;" | Out-Null
} catch {
    ExitWithError "psql failed to connect. Ensure pg client tools can reach the host and DATABASE_URL is correct. Error: $_"
}

$ts = Get-Date -Format 'yyyyMMdd_HHmmss'
$backupDir = "db_backup_$ts"
$dirPath = Join-Path -Path (Get-Location) -ChildPath $backupDir
New-Item -ItemType Directory -Path $dirPath | Out-Null

# 1) Directory-format dump (good for large DBs)
Write-Host "Starting directory-format parallel dump to $dirPath (this may take some time)..."
$pgDumpCmd = "pg_dump -Fd -j $ParallelJobs -f `"$dirPath`" `"$DatabaseUrl`""
Write-Host $pgDumpCmd
$rc = & pg_dump -Fd -j $ParallelJobs -f $dirPath $DatabaseUrl
if ($LASTEXITCODE -ne 0) { ExitWithError "pg_dump (directory format) failed with exit code $LASTEXITCODE" }
Write-Host "Directory dump completed."

# 2) Create compressed custom-format dump as a single file as well
$compressedFile = "${backupDir}.dump"
Write-Host "Creating compressed custom-format dump $compressedFile ..."
& pg_dump -Fc --no-acl --no-owner -f $compressedFile $DatabaseUrl
if ($LASTEXITCODE -ne 0) { ExitWithError "pg_dump (custom) failed with exit code $LASTEXITCODE" }
Write-Host "Custom-format dump created: $compressedFile"

# 3) Validate timetable time formats
Write-Host "Validating timetable_slots start_time/end_time formatting..."
$validationSql = "SELECT id, start_time, end_time FROM timetable_slots WHERE start_time IS NULL OR end_time IS NULL OR start_time !~ '^(?:[01][0-9]|2[0-3]):[0-5][0-9]$' OR end_time !~ '^(?:[01][0-9]|2[0-3]):[0-5][0-9]$';"
$badRows = psql $DatabaseUrl -t -A -c $validationSql
if ($badRows -and $badRows.Trim() -ne '') {
    Write-Host "Found rows with NULL or invalid start_time/end_time. Listing up to 50 rows:" -ForegroundColor Yellow
    psql $DatabaseUrl -c "$validationSql LIMIT 50;"
    Write-Host "You must fix or clean these rows before applying the migration. The migration will fail otherwise." -ForegroundColor Red
    Write-Host "Backup completed and stored in $dirPath and $compressedFile. Exiting without running migration."
    exit 2
}
Write-Host "No invalid timetable rows found. Safe to proceed."

# 4) Verify custom dump (list contents)
Write-Host "Verifying custom dump contents (pg_restore --list)..."
pg_restore --list $compressedFile | Select-Object -First 30 | ForEach-Object { Write-Host $_ }

# 5) Prompt to run migration
$confirm = Read-Host "Backups completed. Do you want to run 'alembic upgrade head' now against $DatabaseUrl ? (yes/no)"
if ($confirm -ne 'yes') {
    Write-Host "Skipped running alembic upgrade. You can run it later with: alembic upgrade head"; exit 0
}

# Run alembic upgrade head using environment variable
Write-Host "Running alembic upgrade head..."
# Ensure alembic reads DATABASE_URL from environment
$env:DATABASE_URL = $DatabaseUrl
& alembic upgrade head
if ($LASTEXITCODE -ne 0) { ExitWithError "alembic upgrade head failed (exit code $LASTEXITCODE). See output above for details." }

Write-Host "Migration finished successfully. Keep your backups at: $dirPath and $compressedFile" -ForegroundColor Green
Write-Host "Recommended: copy the backup files off this machine to secure storage (S3 / external drive / Neon snapshot)."

# End

