@echo off
rem Spare launcher: opens the projects window without a console, with whichever Python is installed.
rem Order: the Python launcher (pyw), then pythonw on PATH, then the old fixed path of Python 3.13.
set "APP=%~dp0XControlP.pyw"
where pyw >nul 2>nul && (start "" pyw "%APP%" & exit /b 0)
where pythonw >nul 2>nul && (start "" pythonw "%APP%" & exit /b 0)
if exist "%LOCALAPPDATA%\Programs\Python\Python313\pythonw.exe" (start "" "%LOCALAPPDATA%\Programs\Python\Python313\pythonw.exe" "%APP%" & exit /b 0)
echo Python 3 was not found. Install it from https://www.python.org/ and run this file again.
pause
exit /b 1
