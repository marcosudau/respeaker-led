@echo off
setlocal

set "PROJECT_ROOT=%~dp0..\.."
set "PYTHON_EXE="

if exist "%PROJECT_ROOT%\.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%PROJECT_ROOT%\.venv\Scripts\python.exe"
)

if not defined PYTHON_EXE if exist "%PROJECT_ROOT%\..\.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%PROJECT_ROOT%\..\.venv\Scripts\python.exe"
)

if not defined PYTHON_EXE (
    set "PYTHON_EXE=python"
)

pushd "%PROJECT_ROOT%"
"%PYTHON_EXE%" "tools\PySide6TestApp\pyside6_effect_tester.py" %*
set "EXIT_CODE=%ERRORLEVEL%"
popd

exit /b %EXIT_CODE%
