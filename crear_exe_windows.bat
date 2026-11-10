@echo off
cd /d "%~dp0"
echo Esta opcion crea un EXE en Windows. Requiere Internet solo durante la instalacion de PyInstaller.
py -3 -m pip install --user pyinstaller
if errorlevel 1 (
  echo PyInstaller no se pudo instalar. Usa iniciar_windows.bat con Python.
  pause
  exit /b 1
)
py -3 -m PyInstaller --clean --noconfirm --onedir --name IberiaFalabella --add-data "templates;templates" --add-data "static;static" app.py
if errorlevel 1 (
  echo Error al compilar el ejecutable.
  pause
  exit /b 1
)
echo EXE disponible en dist\IberiaFalabella\IberiaFalabella.exe
pause
