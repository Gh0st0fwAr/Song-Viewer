@echo off
chcp 65001 >nul
cd /d "%~dp0"

where py >nul 2>&1
if %ERRORLEVEL%==0 (
  py -3 main.py
  goto :done
)

where python >nul 2>&1
if %ERRORLEVEL%==0 (
  python main.py
  goto :done
)

if exist "%LocalAppData%\Programs\Python\Python312\python.exe" (
  "%LocalAppData%\Programs\Python\Python312\python.exe" main.py
  goto :done
)

if exist "%LocalAppData%\Programs\Python\Python313\python.exe" (
  "%LocalAppData%\Programs\Python\Python313\python.exe" main.py
  goto :done
)

if exist "%LocalAppData%\Programs\Python\Python311\python.exe" (
  "%LocalAppData%\Programs\Python\Python311\python.exe" main.py
  goto :done
)

echo Python was not found.
echo Install Python 3 and enable "Add python.exe to PATH",
echo or run:  py -3 main.py
echo.
pause
exit /b 1

:done
if errorlevel 1 (
  echo.
  echo Song Viewer exited with an error.
  pause
)
