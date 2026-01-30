@echo off
REM Quick build script for Windows
echo ========================================
echo FreeQwenApi Executable Builder
echo ========================================
echo.

python build_exe.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo Build completed successfully!
    echo Check the releases/FreeQwenApi folder
    echo ========================================
) else (
    echo.
    echo ========================================
    echo Build failed! Check the error messages above.
    echo ========================================
)

pause
