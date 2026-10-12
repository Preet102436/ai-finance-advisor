# One-time local database setup for the AI Finance Advisor.
# Makes the "postgres" user's password match backend\api\.env (postgres),
# creates the finance_advisor database, and loads db\schema.sql.
# Normally run by INSTALL.bat. To run on its own (as Administrator):
#   powershell -ExecutionPolicy Bypass -File .\setup-db.ps1
# Also creates backend\api\.env from .env.example if it doesn't exist yet.

$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$psql = (Get-ChildItem "C:\Program Files\PostgreSQL\*\bin\psql.exe" | Select-Object -Last 1).FullName
if (-not $psql) {
    Write-Host "PostgreSQL not found in C:\Program Files\PostgreSQL. Install it first (see HOW-TO-RUN.txt)." -ForegroundColor Red
    exit 1
}
$env:PGPASSWORD = "postgres"

# Backend settings file - created from the template on first run, with the
# database password this script sets up and a fresh random login secret.
$envFile = Join-Path $root "backend\api\.env"
if (-not (Test-Path $envFile)) {
    $secret = [Convert]::ToBase64String((1..48 | ForEach-Object { Get-Random -Maximum 256 }))
    (Get-Content (Join-Path $root "backend\api\.env.example")) `
        -replace '^DB_PASSWORD=.*', 'DB_PASSWORD=postgres' `
        -replace '^JWT_SECRET_KEY=.*', "JWT_SECRET_KEY=$secret" |
        Set-Content $envFile
    Write-Host "Created backend\api\.env" -ForegroundColor Green
}

function Test-Login {
    & $psql -U postgres -h localhost -tAc "select 1" 2>$null | Out-Null
    return ($LASTEXITCODE -eq 0)
}

Write-Host "1) Checking the postgres password..."
if (Test-Login) {
    Write-Host "   Password already works." -ForegroundColor Green
} else {
    Write-Host "   Resetting the postgres password to 'postgres'..."
    $hba = (Get-ChildItem "C:\Program Files\PostgreSQL\*\data\pg_hba.conf" | Select-Object -Last 1).FullName
    Copy-Item $hba "$hba.bak" -Force
    try {
        (Get-Content $hba) -replace 'scram-sha-256|md5', 'trust' | Set-Content $hba
        Restart-Service postgresql* ; Start-Sleep -Seconds 3
        & $psql -U postgres -h localhost -c "ALTER USER postgres PASSWORD 'postgres';"
    } finally {
        Copy-Item "$hba.bak" $hba -Force
        Restart-Service postgresql* ; Start-Sleep -Seconds 3
    }
    if (-not (Test-Login)) {
        Write-Host "   Password reset failed - run INSTALL.bat with right-click > Run as administrator." -ForegroundColor Red
        exit 1
    }
    Write-Host "   Password set." -ForegroundColor Green
}

Write-Host "2) Checking the finance_advisor database..."
$exists = & $psql -U postgres -h localhost -tAc "SELECT 1 FROM pg_database WHERE datname='finance_advisor'"
if ($exists -ne "1") {
    & $psql -U postgres -h localhost -c "CREATE DATABASE finance_advisor;"
    Write-Host "   Database created." -ForegroundColor Green
} else {
    Write-Host "   Database already exists." -ForegroundColor Green
}

Write-Host "3) Checking tables..."
$hasUsers = & $psql -U postgres -h localhost -d finance_advisor -tAc "SELECT to_regclass('public.users') IS NOT NULL"
if ($hasUsers -ne "t") {
    & $psql -U postgres -h localhost -d finance_advisor -v ON_ERROR_STOP=1 -q -f (Join-Path $root "db\schema.sql")
    Write-Host "   Tables created." -ForegroundColor Green
} else {
    Write-Host "   Tables already exist." -ForegroundColor Green
}

Write-Host "4) Making sure the schema is up to date..."
$updates = Join-Path $root "db\schema_updates.sql"
if (Test-Path $updates) {
    & $psql -U postgres -h localhost -d finance_advisor -v ON_ERROR_STOP=1 -q -f $updates
    Write-Host "   Schema up to date." -ForegroundColor Green
}

Write-Host "`nDatabase ready." -ForegroundColor Cyan
