@echo off
chcp 65001 >nul
title 채용공고 수집 갱신
cd /d "%~dp0"
rem 1) 프로젝트 가상환경 우선  2) Python312 설치본  3) py 런처  4) python
set "PYEXE=%~dp0.venv\Scripts\python.exe"
if not exist "%PYEXE%" set "PYEXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not exist "%PYEXE%" (
  where py >nul 2>nul && set "PYEXE=py" || set "PYEXE=python"
)
echo ============================================
echo  공공/연구기관 석사급(이공계) 채용공고 수집 시작...
echo ============================================
"%PYEXE%" "%~dp0scrape.py"
echo.
echo 완료되었습니다. 창을 닫으셔도 됩니다.
pause
