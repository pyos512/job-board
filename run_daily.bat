@echo off
chcp 65001 >nul
title 채용보드 일일 갱신+메일
cd /d "%~dp0"

rem ── Python 실행기: venv 우선 ─────────────────────────────
set "PYEXE=%~dp0.venv\Scripts\python.exe"
if not exist "%PYEXE%" set "PYEXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not exist "%PYEXE%" (
  where py >nul 2>nul && set "PYEXE=py" || set "PYEXE=python"
)

if not exist "%~dp0logs" mkdir "%~dp0logs"
set "LOG=%~dp0logs\daily.log"

echo ============================================ >>"%LOG%"
echo [%date% %time%] 시작 >>"%LOG%"

echo  수집 - 암호화 - 푸시(배포) - 메일 ...
"%PYEXE%" "%~dp0publish.py" >>"%LOG%" 2>&1
set "RC=%ERRORLEVEL%"

echo [%date% %time%] done rc=%RC% >>"%LOG%"
if "%RC%"=="0" goto OK
echo  실패(종료코드 %RC%) - logs\daily.log 를 확인하세요.
goto END
:OK
echo  완료. 배포 + 메일 발송됨.
:END

rem 스케줄러는 'auto' 인자로 호출 → 멈추지 않음. 더블클릭(인자 없음)이면 잠깐 멈춤.
if /i not "%~1"=="auto" pause
exit /b %RC%
