@echo off
setlocal enabledelayedexpansion

REM =============================================================================
REM  MPPA Automation — run_tests.cmd
REM  Usage:
REM    run_tests                                              -> full pre-registration suite
REM    run_tests tests\test_pre_registration.py              -> same, explicit
REM    run_tests tests\                                       -> every test in the project
REM    run_tests tests\test_pre_registration.py -k tc05      -> one TC from a file
REM    run_tests tests\ -m slow                              -> marked tests across all files
REM =============================================================================

REM ── Switch to the drive and folder containing this script ─────────────────────
%~d0
cd /d "%~dp0"

REM ── Paths ─────────────────────────────────────────────────────────────────────
set RESULTS_DIR=reports\allure-results
set HTML_DIR=reports\allure-html
set DEST_DIR=reports
set COMBINED_FILE=reports\allure-report.html
set RAW_COMBINED=reports\complete.html
set ZIP_FILE=reports\allure-report.zip

REM ── Step 1: Clean previous results ───────────────────────────────────────────
echo.
echo [1/4] Cleaning previous results...
if exist "%RESULTS_DIR%" rmdir /s /q "%RESULTS_DIR%"
if exist "%HTML_DIR%"    rmdir /s /q "%HTML_DIR%"
if exist "%COMBINED_FILE%" del /q "%COMBINED_FILE%"
if exist "%ZIP_FILE%"    del /q "%ZIP_FILE%"
mkdir "%RESULTS_DIR%"

REM ── Step 2: Resolve test target and extra args ────────────────────────────────
set TEST_TARGET=tests\test_pre_registration.py
set EXTRA_ARGS=

if not "%~1"=="" (
    set TEST_TARGET=%~1
    shift
)

:args_loop
if "%~1"=="" goto :args_done
set EXTRA_ARGS=!EXTRA_ARGS! %~1
shift
goto :args_loop
:args_done

REM ── Step 3: Run pytest ────────────────────────────────────────────────────────
echo.
echo [2/4] Running pytest on: %TEST_TARGET%
if not "!EXTRA_ARGS!"=="" echo       Extra args:!EXTRA_ARGS!
echo.
pytest "%TEST_TARGET%" --alluredir="%RESULTS_DIR%" -v %EXTRA_ARGS%
set PYTEST_EXIT=%ERRORLEVEL%

REM ── Step 4: Generate Allure HTML ─────────────────────────────────────────────
REM cmd /c prevents allure's Java wrapper from calling exit and killing this shell
echo.
echo [3/4] Generating Allure HTML report...
cmd /c allure generate "%RESULTS_DIR%" --clean -o "%HTML_DIR%"

if not exist "%HTML_DIR%\index.html" (
    echo.
    echo ERROR: "%HTML_DIR%\index.html" not found after allure generate.
    echo        Make sure Allure CLI is installed: https://docs.qameta.io/allure/
    goto :end
)
echo        OK — HTML folder created.

REM ── Step 5: Combine into single emailable file ────────────────────────────────
REM cmd /c for the same reason; check output file existence rather than exit code
echo.
echo [4/4] Combining into single HTML file...
cmd /c allure-combine "%HTML_DIR%" --dest "%DEST_DIR%" --auto-create-folders

if exist "%RAW_COMBINED%" (
    move /y "%RAW_COMBINED%" "%COMBINED_FILE%" >nul
    echo.
    echo ============================================================
    echo  Report ready: %COMBINED_FILE%
    echo ============================================================
    goto :end
)

REM allure-combine failed — fall back to zip
echo.
echo allure-combine did not produce output. Falling back to zip...
powershell -NoProfile -Command "Compress-Archive -Path '%HTML_DIR%' -DestinationPath '%ZIP_FILE%' -Force"

if exist "%ZIP_FILE%" (
    echo.
    echo ============================================================
    echo  Report ready: %ZIP_FILE%
    echo  ^(Unzip and open index.html^)
    echo ============================================================
) else (
    echo ERROR: zip also failed. Open reports\allure-html\index.html directly.
)

:end
echo.
echo [Done] pytest exit code: %PYTEST_EXIT%
exit /b %PYTEST_EXIT%