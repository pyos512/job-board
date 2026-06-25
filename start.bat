@echo off
chcp 65001 >nul
title 채용보드 (로컬 서버)
cd /d "%~dp0"
echo ============================================
echo  채용보드 로컬 서버를 시작합니다 (http://localhost:8123)
echo  이 창을 닫으면 서버가 종료됩니다.
echo ============================================
start "" http://localhost:8123/
powershell -NoProfile -Command "$Port=8123; $Root=(Get-Location).Path; Invoke-Expression ([IO.File]::ReadAllText('%~dp0tools\serve.ps1'))"
