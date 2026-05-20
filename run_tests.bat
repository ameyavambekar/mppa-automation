@echo off
setlocal enabledelayedexpansion

REM =============================================================================
REM  MPPA Automation — run_tests.bat
REM  Usage:
REM    run_tests.bat                                         -> full pre-registration suite
REM    run_tests.bat tests\test_pre_registration.py         -> same, explicit
REM    run_tests.bat tests\                                  -> every test in the project
REM    run_tests.bat tests\test_pre_registration.py -k tc05 -> one TC from a file
REM    run_tests.bat tests\ -m slow                         -> marked tests across all files
REM =============================================================================

REM ── Paths ─────────────────────────────────────────────────────────────────────
set RESULTS_DIR=reports\allure-results
set HTML_DIR=reports\allure-html
set DEST_DIR=reports
set COMBINED_FILE=reports\allure-report.html

REM ── Step 1: Clean previous results ───────────────────────────────────────────
echo.
echo [1/4] Cleaning previous Allure results...
if exist "%RESULTS_DIR%" rmdir /s /q "%RESULTS_DIR%"
if exist "%HTML_DIR%"    rmdir /s /q "%HTML_DIR%"
if exist "%COMBINED_FILE%" del /q "%COMBINED_FILE%"
mkdir "%RESULTS_DIR%"

REM ── Step 2: Resolve test target ───────────────────────────────────────────────
REM If no argument given, default to the pre-registration file.
REM Labels inside if blocks are unreliable in batch — args_loop must be at the
REM top level. We set TEST_TARGET first, then fall through to the loop.

set TEST_TARGET=tests\test_pre_registration.py
set EXTRA_ARGS=

if not "%~1"=="" (
    set TEST_TARGET=%~1
    shift
)

REM Collect all remaining arguments into EXTRA_ARGS (works correctly after shift)
:args_loop
if "%~1"=="" goto :args_done
set EXTRA_ARGS=!EXTRA_ARGS! %~1
shift
goto :args_loop
:args_done

REM ── Step 3: Run pytest ────────────────────────────────────────────────────────
echo.
echo [2/4] Running pytest on: %TEST_TARGET%
echo       Extra args: %EXTRA_ARGS%
echo.
pytest "%TEST_TARGET%" --alluredir="%RESULTS_DIR%" -v %EXTRA_ARGS%

REM Capture exit code — 0=all passed, 1=some failed, 2+=collection error
set PYTEST_EXIT=%ERRORLEVEL%

REM ── Step 4: Generate Allure HTML folder ───────────────────────────────────────
echo.
echo [3/4] Generating Allure HTML report...
allure generate "%RESULTS_DIR%" --clean -o "%HTML_DIR%"
if %ERRORLEVEL% neq 0 (
    echo ERROR: allure generate failed. Is Allure CLI installed and on PATH?
    goto :end
)

REM ── Step 5: Combine into single emailable file ────────────────────────────────
REM allure-combine names the output after the input folder name.
REM Input folder = allure-html, so output = reports\allure-html.html
echo.
echo [4/4] Combining into single HTML file...
allure-combine "%HTML_DIR%" --dest "%DEST_DIR%" --auto-create-folders
if %ERRORLEVEL% neq 0 (
    echo.
    echo WARNING: allure-combine failed. Falling back to zip...
    powershell -Command "Compress-Archive -Path '%HTML_DIR%' -DestinationPath 'reports\allure-report.zip' -Force"
    echo Zip created at: reports\allure-report.zip
    goto :end
)

REM Rename allure-html.html -> allure-report.html
if exist "%DEST_DIR%\allure-html.html" (
    move /y "%DEST_DIR%\allure-html.html" "%COMBINED_FILE%" >nul
)

echo.
echo ============================================================
echo  Report ready: %COMBINED_FILE%
echo ============================================================

:end
echo.
echo [Done] pytest exit code: %PYTEST_EXIT%
exit /b %PYTEST_EXIT%