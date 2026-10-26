@echo off
REM ProvaLivre - clique duas vezes neste arquivo para abrir o aplicativo.
REM Double-click this file to start the app. No terminal typing needed.
cd /d "%~dp0"
setlocal

REM Find Python (prefer the Windows launcher "py", else "python")
set PY=python
where py >nul 2>nul && set PY=py

echo ============================================================
echo  ProvaLivre
echo  Preparando o aplicativo. A primeira vez pode levar 1 a 2 minutos.
echo ============================================================
echo.

if not exist ".venv\Scripts\python.exe" (
  echo Criando o ambiente...
  %PY% -m venv .venv
  if errorlevel 1 (
    echo.
    echo Nao foi possivel criar o ambiente. O Python esta instalado?
    echo Baixe em https://www.python.org/downloads/ e marque "Add Python to PATH".
    pause
    exit /b 1
  )
)

call ".venv\Scripts\activate.bat"
echo Instalando componentes...
python -m pip install --quiet --disable-pip-version-check -r requirements.txt

echo.
echo Abrindo o ProvaLivre no seu navegador...
echo Para parar o aplicativo, feche esta janela.
echo.
python app.py

pause
