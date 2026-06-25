# ============================================================
#  매일 자동 갱신 작업 등록 (Windows 작업 스케줄러)
#  실행: PowerShell 에서  .\setup_schedule.ps1
#  - 관리자 권한 불필요 (현재 사용자 작업)
#  - 매일 오전 8시에 run_daily.bat 실행 = 수집(scrape.py) + 메일발송(email_digest.py)
# ============================================================
$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $ScriptDir) { $ScriptDir = (Get-Location).Path }
$Scraper  = Join-Path $ScriptDir 'scrape.py'
$Daily    = Join-Path $ScriptDir 'run_daily.bat'
$TaskName = 'PublicJobBoard_DailyUpdate'
$RunAt    = '08:00'

if (-not (Test-Path $Scraper)) { throw "scrape.py 를 찾을 수 없습니다: $Scraper" }
if (-not (Test-Path $Daily))   { throw "run_daily.bat 를 찾을 수 없습니다: $Daily" }

# Python 실행기 탐색 (프로젝트 venv 우선 → 실제 설치본 → Store stub 제외)
$py = $null
$venvPy = Join-Path $ScriptDir '.venv\Scripts\python.exe'
if (Test-Path $venvPy) { $py = $venvPy }
$cmd = if (-not $py) { Get-Command python -ErrorAction SilentlyContinue } else { $null }
if ($cmd -and $cmd.Source -and $cmd.Source -notmatch 'WindowsApps') { $py = $cmd.Source }
if (-not $py) {
  $found = Get-ChildItem (Join-Path $env:LOCALAPPDATA 'Programs\Python') -Filter python.exe -Recurse -ErrorAction SilentlyContinue |
           Select-Object -First 1
  if ($found) { $py = $found.FullName }
}
if (-not $py -or -not (Test-Path $py)) { throw "실제 Python 설치를 찾을 수 없습니다. 'python --version' 으로 확인하세요." }

# run_daily.bat 을 'auto' 인자로 직접 실행(멈춤 없이) → 수집 후 메일 발송
$action  = New-ScheduledTaskAction -Execute $Daily `
           -Argument 'auto' -WorkingDirectory $ScriptDir
$trigger = New-ScheduledTaskTrigger -Daily -At $RunAt
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd `
            -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
            -ExecutionTimeLimit (New-TimeSpan -Minutes 30)

try { Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue } catch {}

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings `
  -Description '공공/연구기관 석사급(이공계) 채용공고 매일 08시 수집+메일발송' | Out-Null

Write-Host "✅ 작업 등록 완료: '$TaskName' — 매일 $RunAt 수집+메일발송" -ForegroundColor Green
Write-Host "   Python: $py"
Write-Host "   즉시 실행:  Start-ScheduledTask -TaskName $TaskName"
Write-Host "   해제:      Unregister-ScheduledTask -TaskName $TaskName -Confirm:`$false"
