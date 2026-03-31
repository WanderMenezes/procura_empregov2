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

set "BACKUP_INPUT="
set "SKIP_CONFIRM="

:parse_args
if "%~1"=="" goto args_done
if /I "%~1"=="--help" goto usage
if /I "%~1"=="-h" goto usage
if /I "%~1"=="--yes" (
    set "SKIP_CONFIRM=1"
) else if /I "%~1"=="-y" (
    set "SKIP_CONFIRM=1"
) else if not defined BACKUP_INPUT (
    set "BACKUP_INPUT=%~1"
) else (
    echo Unexpected argument "%~1".
    goto usage_error
)
shift
goto parse_args

:args_done
if not defined BACKUP_INPUT goto usage_error

if exist "%BACKUP_INPUT%" (
    set "BACKUP_FILE=%BACKUP_INPUT%"
) else if exist "%PROJECT_DIR%\%BACKUP_INPUT%" (
    set "BACKUP_FILE=%PROJECT_DIR%\%BACKUP_INPUT%"
) else if exist "%BACKUP_DIR%\%BACKUP_INPUT%" (
    set "BACKUP_FILE=%BACKUP_DIR%\%BACKUP_INPUT%"
) else (
    echo Backup file was not found: "%BACKUP_INPUT%".
    exit /b 1
)

for %%I in ("%BACKUP_FILE%") do set "BACKUP_FILE=%%~fI"

if /I "%DB_ENGINE%"=="sqlite" goto restore_sqlite
if /I not "%DB_ENGINE%"=="mysql" (
    echo Unsupported DB_ENGINE "%DB_ENGINE%".
    exit /b 1
)

if "%DB_NAME%"=="" (
    echo DB_NAME is missing. Check "%ENV_FILE%".
    exit /b 1
)

set "MYSQL=C:\xampp\mysql\bin\mysql.exe"
if not exist "%MYSQL%" (
    echo mysql.exe was not found at "%MYSQL%".
    exit /b 1
)

echo Target database: %DB_NAME%
echo Backup file: "%BACKUP_FILE%"
echo.
echo This will overwrite data in the configured MySQL database.
if not defined SKIP_CONFIRM (
    set /p "CONFIRM=Type RESTORE to continue: "
    if /I not "!CONFIRM!"=="RESTORE" (
        echo Restore cancelled.
        exit /b 1
    )
)

echo Restoring MySQL backup...
if defined DB_PASSWORD (
    "%MYSQL%" --host=%DB_HOST% --port=%DB_PORT% --user=%DB_USER% --password=%DB_PASSWORD% < "%BACKUP_FILE%"
) else (
    "%MYSQL%" --host=%DB_HOST% --port=%DB_PORT% --user=%DB_USER% < "%BACKUP_FILE%"
)

if errorlevel 1 (
    echo Restore failed.
    exit /b 1
)

echo Restore completed successfully.
exit /b 0

:restore_sqlite
set "SQLITE_FILE=%PROJECT_DIR%\db.sqlite3"
if not exist "%BACKUP_FILE%" (
    echo Backup file was not found: "%BACKUP_FILE%".
    exit /b 1
)

echo Target SQLite file: "%SQLITE_FILE%"
echo Backup file: "%BACKUP_FILE%"
echo.
echo This will overwrite the current SQLite database file.
if not defined SKIP_CONFIRM (
    set /p "CONFIRM=Type RESTORE to continue: "
    if /I not "!CONFIRM!"=="RESTORE" (
        echo Restore cancelled.
        exit /b 1
    )
)

copy /Y "%BACKUP_FILE%" "%SQLITE_FILE%" >nul
if errorlevel 1 (
    echo Restore failed.
    exit /b 1
)

echo Restore completed successfully.
exit /b 0

:usage_error
echo.
:usage
echo Usage:
echo   restore_database.bat ^<backup-file^> [--yes]
echo.
echo Examples:
echo   restore_database.bat backups\base_nacional_jovens-20260330-115535.sql
echo   restore_database.bat base_nacional_jovens-20260330-115535.sql --yes
echo.
echo The script reads database settings from ".env".
exit /b 1
