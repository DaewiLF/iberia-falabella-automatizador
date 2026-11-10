@echo off
if "%~1"=="" (
  echo Arrastra tu Excel de Precios de Falabella sobre este archivo BAT.
  echo Requiere Microsoft Excel instalado en Windows.
  pause
  exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0recalcular_precios_windows.ps1" -Archivo "%~1"
if errorlevel 1 echo Comprueba que Microsoft Excel este instalado y que el archivo no este bloqueado.
pause
