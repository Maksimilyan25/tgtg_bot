@echo off
echo Завершение всех процессов...

taskkill /f /im python.exe
taskkill /f /im cmd.exe
taskkill /f /im powershell.exe
taskkill /f /im node.exe
taskkill /f /im npm.exe
taskkill /f /im git.exe
taskkill /f /im code.exe

echo Все процессы завершены!
pause
