@echo off
cd /d "%~dp0"
where py >nul 2>&1
if %errorlevel% equ 0 (
  py -3 app.py
) else (
  where python >nul 2>&1
  if %errorlevel% equ 0 (
    python app.py
  ) else (
    echo No encuentro Python. Instala Python 3.11 o posterior desde https://python.org/downloads/
    echo Durante la instalacion activa la opcion Add python.exe to PATH.
    pause
    exit /b 1
  )
)
if errorlevel 1 pause
