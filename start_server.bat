@echo off
REM Codebeamer MCP Server - Windows Startup Script
REM Double-click this file to start the server for testing

echo ============================================
echo  Codebeamer MCP Server - Windows
echo ============================================
echo.

REM Set environment variables (EDIT THESE!)
set CODEBEAMER_URL=https://your-codebeamer-instance.com
set CODEBEAMER_API_KEY=your-api-key-here
set CODEBEAMER_MAX_CALLS=60
set CODEBEAMER_CACHE_TTL=300

echo Configuration:
echo   URL: %CODEBEAMER_URL%
echo   Max Calls/min: %CODEBEAMER_MAX_CALLS%
echo   Cache TTL: %CODEBEAMER_CACHE_TTL%s
echo.

REM Check if API key is set
if "%CODEBEAMER_API_KEY%"=="your-api-key-here" (
    echo [ERROR] Please edit this file and set your CODEBEAMER_API_KEY!
    echo.
    pause
    exit /b 1
)

echo Starting MCP Server...
echo (Press Ctrl+C to stop)
echo.

REM Try to run with python
python mcp_server.py

REM If python doesn't work, try py launcher
if errorlevel 1 (
    echo.
    echo [WARNING] 'python' command failed, trying 'py'...
    echo.
    py mcp_server.py
)

REM Keep window open if there's an error
if errorlevel 1 (
    echo.
    echo [ERROR] Failed to start server!
    echo.
    echo Troubleshooting:
    echo   1. Make sure Python 3.8+ is installed
    echo   2. Install dependencies: pip install -r requirements.txt
    echo   3. Check that API key is set correctly above
    echo.
    pause
)
