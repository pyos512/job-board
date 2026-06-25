# ============================================================================
#  공공·연구기관 「석사급(석사이상·박사미만)」 채용공고 수집기
#  소스: 잡알리오(job.alio.go.kr) + 하이브레인넷(hibrain.net)
#  - 추가 설치 불필요 (Windows 기본 PowerShell / CI 환경 pwsh 동일 동작)
#  - data/jobs.js (window 할당, file:// 로컬에서 바로 열림) + data/jobs.json 생성
#  - 매일 자동 실행은 setup_schedule.ps1 로 등록 (또는 GitHub Actions)
# ============================================================================
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 } catch {}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if(-not $ScriptDir){ $ScriptDir = (Get-Location).Path }
$DataDir   = Join-Path $ScriptDir 'data'
New-Item -ItemType Directory -Force -Path $DataDir | Out-Null
$OutJson   = Join-Path $DataDir 'jobs.json'
$OutJs     = Join-Path $DataDir 'jobs.js'

function Clean([string]$s){
  if($null -eq $s){ return '' }
  $s = $s -replace '(?s)<[^>]+>',' '
  $s = [System.Net.WebUtility]::HtmlDecode($s)
  $s = $s -replace '\s+',' '
  return $s.Trim()
}

# ---- 기관유형 분류 (네비게이션 탭) -----------------------------------------
function Classify([string]$org){
  if($org -match '병원|의료원|의학원|암센터'){ return '대학·병원' }
  if($org -match '대학교|대학원|대학$'){ return '대학·병원' }
  if($org -match '기초과학연구원|한국과학기술연구원|KIST|선박해양|해양과학기술원|국방과학연구소|항공우주|전자통신연구원|ETRI|생명공학|화학연구원|에너지기술|기계연구원|재료연구|표준과학|식품연구원|천문연구원|지질자원|핵융합|건설기술|철도기술|전기연구원|원자력|나노|광기술|생산기술|과학기술기획평가원|KISTEP'){ return '정부출연(과학기술)' }
  if($org -match '한국개발연구원|KDI|한국노동연구원|정보통신정책연구원|산업연구원|에너지경제연구원|한국환경연구원|한국조세재정연구원|한국보건사회연구원|한국직업능력연구원|한국형사|육아정책연구소|한국청소년정책연구원|건축공간연구원|한국해양수산개발원|경제인문사회연구회|국토연구원|과학기술정책연구원|대외경제정책연구원|농촌경제연구원|교통연구원|여성정책연구원|행정연구원|법제연구원|통일연구원|국방연구원'){ return '정부출연(경제인문사회)' }
  if($org -match '연구원|연구소|연구회|진흥원'){ return '연구기관·진흥원' }
  return '공공기관·공기업'
}

# ---- 근로조건 점수 (높을수록 추천) ----------------------------------------
function Score($emp, $salary, $pref, $career, $type){
  $s = 0; $reasons = @()
  # '비정규직','무기계약직'이 '정규직'/'계약'을 부분 포함하므로 순서 주의
  if($emp -match '무기계약'){ $s += 32; $reasons += '무기계약직(고용안정)' }
  elseif($emp -match '비정규'){ $s += 10; $reasons += '계약직' }
  elseif($emp -match '청년인턴\(채용형\)'){ $s += 18; $reasons += '채용형 인턴' }
  elseif($emp -match '청년인턴'){ $s += 5; $reasons += '체험형 인턴' }
  elseif($emp -match '계약직'){ $s += 10; $reasons += '계약직' }
  elseif($emp -match '정규직'){ $s += 45; $reasons += '정규직(정년보장)' }
  if($salary -match '\d'){ $s += 15; $reasons += '연봉 공개' }
  if($pref){ $s += 5 }
  if($career -match '신입'){ $s += 6; $reasons += '신입 지원가능' }
  if($type -match '정부출연'){ $s += 8; $reasons += '정부출연연' }
  return [pscustomobject]@{ score=$s; reasons=$reasons }
}

# ---- 잡알리오: 진행중 / 연구직·교수직 / 석사 ------------------------------
function Get-AlioJobs {
  $listUrl = 'https://job.alio.go.kr/recruit.do?pageSet=100&order=TERM_END&sort=ASC&ing=2&area=R8015&area=R8019&education=R7060'
  Write-Host "[잡알리오] 목록 수집 중..."
  $resp = Invoke-WebRequest -Uri $listUrl -UseBasicParsing -TimeoutSec 40
  $html = $resp.Content
  $rowRe = '(?s)recruitview\.do\?idx=(\d+)"[^>]*>(.*?)</a>\s*</td>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>'
  $rmatches = [regex]::Matches($html, $rowRe)
  $rows = @()
  $seenIdx = @{}
  foreach($m in $rmatches){
    $idx = $m.Groups[1].Value
    if($seenIdx.ContainsKey($idx)){ continue }
    $seenIdx[$idx] = $true
    $endRaw = Clean $m.Groups[7].Value
    $endDate = ''; if($endRaw -match '(\d{2}\.\d{2}\.\d{2})'){ $endDate = $Matches[1] }
    $dday = ''
    if($endRaw -match '(D-\d+)'){ $dday = $Matches[1] } elseif($endRaw -match 'D-DAY|오늘마감'){ $dday='오늘마감' } elseif($endRaw -match '마감'){ $dday = '마감' }
    $rows += [pscustomobject]@{
      idx=$idx; title=(Clean $m.Groups[2].Value); org=(Clean $m.Groups[3].Value)
      loc=(Clean $m.Groups[4].Value); emp=(Clean $m.Groups[5].Value)
      regDate=(Clean $m.Groups[6].Value); endDate=$endDate; dday=$dday
    }
  }
  Write-Host "[잡알리오] 목록 $($rows.Count)건 → 상세 수집..."

  $jobs = @(); $i = 0
  foreach($r in $rows){
    $i++
    Write-Host ("  ({0}/{1}) {2}" -f $i, $rows.Count, $r.org)
    $detailUrl = "https://job.alio.go.kr/recruitview.do?idx=$($r.idx)"
    $sal=''; $elig=''; $pref=''; $edu=''; $field=''; $career=''; $period=''; $headcount=''
    try {
      $d = (Invoke-WebRequest -Uri $detailUrl -UseBasicParsing -TimeoutSec 40).Content
      $pairs = [regex]::Matches($d, '(?s)<th[^>]*>(.*?)</th>\s*<td[^>]*>(.*?)</td>')
      foreach($p in $pairs){
        $k = Clean $p.Groups[1].Value; $v = Clean $p.Groups[2].Value
        switch -Regex ($k){
          '급여정보' { $sal = $v }
          '우대조건' { $pref = $v }
          '채용기간' { $period = $v }
          '학력정보' { $edu = $v }
          '근무분야' { $field = $v }
          '채용구분' { $career = $v }
          '채용인원' { $headcount = $v }
        }
      }
      if($sal -notmatch '\d'){ $sal = '' }
      $ei = $d.IndexOf('응시자격')
      if($ei -ge 0){
        $chunk = $d.Substring($ei + 4, [Math]::Min(3000, $d.Length - $ei - 4))
        foreach($term in @('전형단계','채용절차','전형일정','전형 일정','첨부파일 전체보기','제출서류','우대조건','채용 절차')){
          $ti = $chunk.IndexOf($term); if($ti -gt 40){ $chunk = $chunk.Substring(0, $ti) }
        }
        $elig = Clean $chunk
        if($elig.Length -gt 750){ $elig = $elig.Substring(0,750) + '…' }
      }
    } catch { Write-Host "    (상세 수집 실패, 목록정보로 대체)" }

    # 박사 전용(석사 불가) 공고 제외 → 석사급만 유지
    if($edu -and ($edu -match '박사') -and ($edu -notmatch '석사')){ continue }

    if([string]::IsNullOrWhiteSpace($period)){ $period = ("{0} ~ {1}" -f $r.regDate, $r.endDate) }
    $type = Classify $r.org
    $sc = Score $r.emp $sal $pref $career $type
    $jobs += [pscustomobject]@{
      source='잡알리오'; type=$type; org=$r.org; title=$r.title; location=$r.loc; emp=$r.emp
      period=$period; endDate=$r.endDate; dday=$r.dday; salary=$sal; edu=$edu; field=$field
      career=$career; headcount=$headcount; elig=$elig; pref=$pref
      score=$sc.score; reasons=$sc.reasons; url=$detailUrl
    }
  }
  Write-Host "[잡알리오] 석사급 확정 $($jobs.Count)건"
  return $jobs
}

# ---- 하이브레인넷 (연구원 + 정출연/국공립연구소) ---------------------------
function Get-HibrainCategory($url, $label){
  $jobs = @()
  try {
    $h = (Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 30 -Headers @{ 'User-Agent'='Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15' }).Content
    $ids = [regex]::Matches($h, 'data-hbn-recruitId="(\d+)"')
    $seen = @{}
    for($k=0; $k -lt $ids.Count; $k++){
      $rid = $ids[$k].Groups[1].Value
      if($seen.ContainsKey($rid)){ continue }
      $seen[$rid] = $true
      $start = $ids[$k].Index
      $end = if($k -lt $ids.Count-1){ $ids[$k+1].Index } else { [Math]::Min($start+2200, $h.Length) }
      $block = $h.Substring($start, $end-$start)
      $hm = [regex]::Match($block, 'href="(/recruitment/[^"]+)"')
      $href = if($hm.Success){ [System.Net.WebUtility]::HtmlDecode($hm.Groups[1].Value) } else { '' }
      if($href -and $href -notmatch '^https?://'){ $href = 'https://www.hibrain.net' + $href }
      if(-not $href){ $href = "https://www.hibrain.net/recruitment/recruits/$rid" }
      $tm = [regex]::Match($block, '(?s)banner-title[^>]*>(.*?)</div>')
      $title = if($tm.Success){ Clean $tm.Groups[1].Value } else { '' }
      if([string]::IsNullOrWhiteSpace($title)){ continue }
      if($title -match '박사후|Post-?Doc|박사급|박사 채용|연구교수'){ continue }   # 박사전용 성격 제외
      $dday=''; $dm = [regex]::Match($block, '(D-\d+|오늘마감|상시채용|상시)'); if($dm.Success){ $dday=$dm.Groups[1].Value }
      $jobs += [pscustomobject]@{
        source='하이브레인넷'; type='하이브레인넷(연구실·기업)'; org=$label; title=$title
        location=''; emp='연구직'; period=''; endDate=''; dday=$dday; salary=''
        edu='석사 이상'; field='연구'; career=''; headcount=''; elig=''; pref=''
        score=12; reasons=@('연구전문 채용'); url=$href
      }
      if($jobs.Count -ge 12){ break }
    }
  } catch { Write-Host "[하이브레인넷] $label 수집 건너뜀: $($_.Exception.Message)" }
  return $jobs
}

function Get-HibrainJobs {
  Write-Host "[하이브레인넷] 수집 중..."
  $all = @()
  $all += Get-HibrainCategory 'https://m.hibrain.net/recruitment/categories/JOB/categories/RES/recruits' '연구원'
  $all += Get-HibrainCategory 'https://m.hibrain.net/recruitment/categories/COMP/categories/GOVLAB/recruits' '정출연·국공립연구소'
  # 링크 기준 중복 제거
  $seen=@{}; $uniq=@()
  foreach($j in $all){ if($j.url -and -not $seen.ContainsKey($j.url)){ $seen[$j.url]=$true; $uniq+=$j } }
  Write-Host "[하이브레인넷] $($uniq.Count)건"
  return $uniq
}

# ---- 실행 ------------------------------------------------------------------
$all = @()
$alio = Get-AlioJobs
$all += $alio
$all += Get-HibrainJobs

# 추천 정렬(점수↓, 마감 임박↑)
$all = $all | Sort-Object @{e={ -1 * $_.score }}, @{e={$_.endDate}}

$companyCount = ($alio | Select-Object -ExpandProperty org -Unique).Count
$recommended  = ($all | Where-Object { $_.score -ge 45 }).Count

$payload = [pscustomobject]@{
  updatedAt   = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
  updatedAtKr = (Get-Date).ToString('yyyy년 M월 d일 HH:mm')
  count       = $all.Count
  companies   = $companyCount
  recommended = $recommended
  target      = '석사급(석사 이상 · 박사 미만) · 공공/연구기관 연구직'
  sources     = @('잡알리오 (job.alio.go.kr)','하이브레인넷 (hibrain.net)')
  jobs        = $all
}

$json = $payload | ConvertTo-Json -Depth 6
$utf8 = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($OutJson, $json, $utf8)
# file:// 로컬에서 fetch 차단을 우회하기 위한 JS 데이터 (window 할당)
$jsContent = "/* 자동생성 파일 — 직접 수정 금지. update_jobs.ps1 가 갱신합니다. */" + [Environment]::NewLine + "window.__JOBS__ = " + $json + ";"
[System.IO.File]::WriteAllText($OutJs, $jsContent, $utf8)

Write-Host ""
Write-Host "완료 ✅  총 $($all.Count)건 / 공공·연구기관 $($companyCount)개사 / 추천 $($recommended)건"
Write-Host "갱신시각: $($payload.updatedAtKr)"
Write-Host "출력: $OutJson"
Write-Host "      $OutJs"
