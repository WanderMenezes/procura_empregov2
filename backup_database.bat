@echo off
setlocal EnableExtensions EnableDelayedExpansion

for %%I in ("%~dp0.") do set "PROJECT_DIR=%%~fI"
set "ENV_FILE=%PROJECT_DIR%\.env"
set "BACKUP_DIR=%PROJECT_DIR%\backups"

set "DB_ENGINE=mysql"
set "DB_NAME="
set "DB_USER=root"
set "DB_PASSWORD="
set "DB_HOST=127.0.0.1"
set "DB_PORT=3306"

if exist "%ENV_FILE%" (
    for /f "usebackq tokens=1,* delims==" %%A in ("%ENV_FILE%") do (
        set "KEY=%%~A"
        set "VALUE=%%~B"
        if not "!KEY!"=="" if not "!KEY:~0,1!"=="#" (
            if /I "!KEY!"=="DB_ENGINE" set "DB_ENGINE=!VALUE!"
            if /I "!KEY!"=="DB_NAME" set "DB_NAME=!VALUE!"
            if /I "!KEY!"=="DB_USER" set "DB_USER=!VALUE!"
            if /I "!KEY!"=="DB_PASSWORD" set "DB_PASSWORD=!VALUE!"
            if /I "!KEY!"=="DB_HOST" set "DB_HOST=!VALUE!"
            if /I "!KEY!"=="DB_PORT" set "DB_PORT=!VALUE!"
        )
    )
)

if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd-HHmmss"') do set "STAMP=%%I"

if not defined STAMP (
    echo Failed to build a backup timestamp.
    exit /b 1
)

if /I "%DB_ENGINE%"=="sqlite" goto backup_sqlite
if /I not "%DB_ENGINE%"=="mysql" (
    echo Unsupported DB_ENGINE "%DB_ENGINE%".
    exit /b 1
)

if "%DB_NAME%"=="" (
    echo DB_NAME is missing. Check "%ENV_FILE%".
    exit /b 1
)

set "MYSQLDUMP=C:\xampp\mysql\bin\mysqldump.exe"
if not exist "%MYSQLDUMP%" (
    echo mysqldump was not found at "%MYSQLDUMP%".
    exit /b 1
)

set "OUTPUT_FILE=%BACKUP_DIR%\%DB_NAME%-%STAMP%.sql"
echo Creating MySQL backup...

if defined DB_PASSWORD (
    "%MYSQLDUMP%" --host=%DB_HOST% --port=%DB_PORT% --user=%DB_USER% --password=%DB_PASSWORD% --single-transaction --routines --triggers --databases %DB_NAME% > "%OUTPUT_FILE%"
) else (
    "%MYSQLDUMP%" --host=%DB_HOST% --port=%DB_PORT% --user=%DB_USER% --single-transaction --routines --triggers --databases %DB_NAME% > "%OUTPUT_FILE%"
)

if errorlevel 1 (
    if exist "%OUTPUT_FILE%" del "%OUTPUT_FILE%"
    echo Backup failed.
    exit /b 1
)

echo Backup saved to "%OUTPUT_FILE%".
exit /b 0

:backup_sqlite
set "SQLITE_FILE=%PROJECT_DIR%\db.sqlite3"
if not exist "%SQLITE_FILE%" (
    echo SQLite database was not found at "%SQLITE_FILE%".
    exit /b 1
)

set "OUTPUT_FILE=%BACKUP_DIR%\db-%STAMP%.sqlite3"
echo Creating SQLite backup...
copy /Y "%SQLITE_FILE%" "%OUTPUT_FILE%" >nul

if errorlevel 1 (
    echo Backup failed.
    exit /b 1
)

echo Backup saved to "%OUTPUT_FILE%".
exit /b 0
