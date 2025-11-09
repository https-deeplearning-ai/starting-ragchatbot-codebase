@echo off
REM Run all code quality checks

echo ===================================
echo Running Code Quality Checks
echo ===================================

set FAILED=0

REM Check Black formatting
echo.
echo Checking code formatting with Black...
uv run black --check backend/ main.py
if errorlevel 1 (
    echo Black check failed! Run 'format.bat' to fix formatting.
    set FAILED=1
) else (
    echo Black check passed!
)

REM Check isort
echo.
echo Checking import sorting with isort...
uv run isort --check-only backend/ main.py
if errorlevel 1 (
    echo Isort check failed! Run 'format.bat' to fix imports.
    set FAILED=1
) else (
    echo Isort check passed!
)

REM Run flake8
echo.
echo Running flake8 linter...
uv run flake8 backend/ main.py
if errorlevel 1 (
    echo Flake8 check failed!
    set FAILED=1
) else (
    echo Flake8 check passed!
)

REM Run mypy type checking
echo.
echo Running mypy type checker...
uv run mypy backend/ main.py
if errorlevel 1 (
    echo Mypy check failed!
    set FAILED=1
) else (
    echo Mypy check passed!
)

REM Summary
echo.
echo ===================================
if %FAILED%==0 (
    echo All quality checks passed!
    exit /b 0
) else (
    echo Some quality checks failed!
    exit /b 1
)
