# 📚 공공·연구기관 석사급(이공계) 채용보드

석사 이상·박사 미만, **자연과학/이공계**(기상·대기·환경·에너지·바이오·데이터·AI 등) 분야의
**공공기관·정부출연연·공기업·지자체 연구원** 채용공고를 여러 사이트에서 자동 수집해
지원기간·자격요건·우대사항·근무지·연봉·계약형태까지 정리하고, **근로조건이 좋은 순**으로 추천하는 정적 웹보드.

수집은 **Python**, 화면은 **순수 JS/HTML/CSS + Three.js 3D**. 외부 CDN 0개(완전 자체 호스팅).

---

## 🚀 가장 빠른 사용법

1. **`start.bat` 더블클릭** → 로컬 서버가 뜨고 브라우저에서 `http://localhost:8123` 열림.
2. 회사 유형 탭으로 분류해서 보고, 검색·정렬·새로고침·자격요건 펼치기 사용.

> 데이터 새로 받기: **`run_update.bat` 더블클릭** (수집 후 자동 반영).
> 매일 자동 갱신은 이미 **작업 스케줄러에 등록되어 매일 오전 8시** 실행됩니다(아래 참고).

---

## 🔁 매일 자동 갱신 + 📧 이메일 발송

작업 스케줄러에 등록되어 있습니다(`PublicJobBoard_DailyUpdate`, 매일 08:00).
매일 `run_daily.bat`이 **① 수집(`scrape.py`) → ② 다이제스트 메일 발송(`email_digest.py`)** 을 자동 수행합니다.

```powershell
# 재등록 / 시간 변경
.\setup_schedule.ps1
# 즉시 실행(테스트)
Start-ScheduledTask -TaskName PublicJobBoard_DailyUpdate
# 해제
Unregister-ScheduledTask -TaskName PublicJobBoard_DailyUpdate -Confirm:$false
```

### 📧 이메일 설정 (최초 1회)
이메일 클라이언트는 JS를 실행하지 않으므로, `jobs.json`을 읽어 **인라인 스타일 정적 HTML 다이제스트**
(⭐추천 공고 상단 + 전체 공고, D-day·근무지·고용형태)를 만들어 보냅니다.

1. **Gmail 앱 비밀번호 발급**: 구글 계정 → 보안 → 2단계 인증 켜기 → '앱 비밀번호' → 16자 발급.
   (일반 로그인 비밀번호로는 SMTP 발송이 차단됩니다.)
2. **`email_config.json`** 의 `"password"` 값에 그 16자(공백 제거)를 붙여넣기. 이 파일은 `.gitignore`로 커밋 제외됨.
3. **테스트 발송**:
   ```powershell
   .\.venv\Scripts\python email_digest.py            # 실제 발송
   .\.venv\Scripts\python email_digest.py --preview  # 발송 없이 digest_preview.html 생성
   ```
- 로그: `logs\daily.log`. 발송 실패 시 종료코드·원인이 여기에 남습니다.
- 다른 메일(네이버 등)은 `email_config.json`의 `smtp_host`/`smtp_port`만 바꾸면 됩니다.

---

## 🧰 기술 스택 / 환경

- **수집기**: Python + `requests` + `beautifulsoup4` — **프로젝트 전용 가상환경 `.venv\`** 에 설치(이 PC에 설치 완료).
  - 인터프리터: `.venv\Scripts\python.exe`. 배치/스케줄러는 이 venv를 최우선으로 씁니다.
  - 새 PC에서 재구축: `py -m venv .venv` → `.venv\Scripts\python -m pip install -r requirements.txt`
  - ⚠️ `python` 명령이 Microsoft Store 설치 안내창을 띄우는 PC라도, venv를 쓰므로 영향 없습니다.
- **화면**: 정적 HTML/CSS/JS. ES 모듈/`fetch` 미사용(파일도 그대로 열림). 배포 시엔 `jobs.json`을 `fetch`.
- **로컬 서버**: `tools/serve.ps1` (Windows 기본 PowerShell, 무설치, 보안헤더 포함).

---

## 📂 구성

```
job-board/
├─ index.html              # 메인 (3D 히어로 · 베이지 테마 · 반응형)
├─ assets/                 # styles.css · app.js(XSS방어) · hero3d.js · three.min.js(자체호스팅)
├─ data/                   # jobs.json(배포/서버용) · jobs.js(file:// 로컬 로드용)
├─ scrape.py               # ★ 수집기 (Python) — 잡알리오·하이브레인·워크넷·나라일터
├─ update_jobs.ps1         # (레거시) Python 없을 때용 PowerShell 수집기
├─ setup_schedule.ps1      # 매일 자동 갱신 작업 등록
├─ run_update.bat          # 지금 바로 수집
├─ start.bat               # 로컬 서버 + 브라우저 열기
├─ tools/serve.ps1         # 무설치 정적 서버(보안헤더)
├─ deploy/                 # 공개 배포용 보안설정(_headers · netlify.toml · nginx)
├─ .well-known/security.txt · robots.txt
└─ .github/workflows/update.yml   # 공개 배포 시 매일 자동 갱신(GitHub Actions, Python)
```

---

## 🔎 수집 대상 / 필터

- **잡알리오**: 진행중 · 근무분야 `연구직`/`교수직` · 학력 `석사` · **박사 전용(석사 불가) 공고 제외**.
- **하이브레인넷**: `연구원`(RES) · `정출연·국공립연구소`(GOVLAB) · **`정부·공공·지자체`(GOVORG)** 카테고리 (박사후/Post-Doc 제외).
  - 👉 **지자체 연구원**은 GOVORG 카테고리로 안정적으로 수집됩니다(경기연구원·보건환경연구원 등). 기관명이 지자체 패턴이면 `지자체·지방연구원` 탭으로 자동 분류.
- **워크넷**: 공공데이터포털 **공식 API**로 연동(선택). 환경변수 `WORKNET_KEY` 설정 시 활성화.
  - 키 발급: https://www.data.go.kr → ‘한국고용정보원_워크넷 채용정보’ 검색 → 활용신청(무료) → 인증키.
  - 로컬: `setx WORKNET_KEY "발급키"` 후 새 창에서 `run_update.bat`. CI: 저장소 Secrets에 `WORKNET_KEY`.
- **나라일터**: best-effort. 목록이 비공개 동적 호출(검색폼 셸만 반환)이라 현재 0건이며 실패 시 자동 건너뜁니다. 지자체 연구원은 위 하이브레인 GOVORG로 대체 커버합니다.
- **🧪 전공 필터(정밀판)**: 제목·전공·자격 텍스트에서 **자연과학/이공계 키워드**만 통과.
  - 한글: 기상·대기환경·대기질·환경·생태·수질·해양·지질·농학·화학·소재·전기전자·기계·에너지·물리·생명·바이오·보건의료·데이터·통계·정보통신·토목·건설 등.
  - 영문 약어(`AI·IT·ICT·IoT·GIS·R&D·ESG·BIM` 등)는 **단어경계+대소문자 구분**으로 매칭 → `email/main`의 `it/ai` 오탐 차단.
  - `대기`(→대기환경/대기질/대기과학으로 한정, ‘대기자’ 오탐 제거), `교통`(→교통공학/교통계획, ‘교통비’ 오탐 제거), `보건`(→보건의료/보건환경) 등 일반 행정어는 구체형만 인정.
  - 순수 경제·경영·법·행정·복지 공고는 제외.
- **기관당 최대 4건**으로 과다 노출 방지, 하이브레인 제목 기준 중복 제거.

### 네비게이션 탭(회사 유형)
정부출연(과학기술) / 정부출연(경제인문사회) / 지자체·지방연구원 / 공공기관·공기업 / 연구기관·진흥원 / 대학·병원 / 하이브레인넷 — 그리고 **⭐ 추천** 탭.

> 다른 사이트를 추가하려면 `scrape.py`에 `get_xxx()` 함수를 만들어 동일 스키마(dict)로 반환 후 `main()`의 `allj += get_xxx()` 한 줄만 추가.

---

## 🧮 근로조건 점수(가중치)

| 항목 | 가점 |
|---|---|
| 정규직(정년보장) | +50 |
| 무기계약직(고용안정) | +34 |
| 채용형 인턴 | +18 |
| 계약/비정규직 | +10 |
| 체험형 인턴 | +4 |
| 연봉(보수) 공개 | +12 |
| 신입 지원가능 | +6 |
| 정부출연연 | +8 |
| 지자체 연구원 | +5 |
| 이공계 전문분야(키워드 다수) | +5 |
| 우대사항 있음 | +4 |

- **48점 이상** → `⭐ 추천` 배지 + 추천 탭/추천순 상단.
- ⚠️ 추정치입니다. 지원 전 반드시 원문 공고·첨부 공고문에서 자격·연봉·접수기간을 확인하세요.

---

## 🛡️ 보안 (공개 배포 대비)

- **정적 사이트**(백엔드/DB 없음) → 공격면 최소.
- **XSS 차단** — 스크래핑 데이터는 전부 `textContent`로만 DOM 주입(HTML 미해석). 링크는 `http(s)`만 허용, `rel="noopener noreferrer"`.
- **CSP `default-src 'self'`** — 외부 CDN 0개(Three.js 자체 호스팅)라 `script-src 'self'`로 가장 엄격.
- **보안 헤더** — `nosniff`·`X-Frame-Options: DENY`·`Referrer-Policy: no-referrer`·`Permissions-Policy`·`HSTS`·COOP/CORP. (`deploy/` 및 `tools/serve.ps1`)

### 공개 배포 (택1)
- **Netlify / Cloudflare Pages**: 폴더 그대로 배포 + `deploy/_headers`(또는 `netlify.toml`)를 루트로.
- **GitHub Pages + Actions**: 푸시하면 `.github/workflows/update.yml`이 매일 Python으로 데이터 갱신·커밋.
- **자체 nginx**: `deploy/nginx-security.conf`를 `server {}`에 포함.

---

## ❓ 문제 해결

- **카드가 안 보임** → `run_update.bat` 먼저 실행해 `data/jobs.json`·`jobs.js` 생성.
- **`python`이 Store 창을 띄움** → 실제 설치본(`%LOCALAPPDATA%\Programs\Python\Python312\python.exe`) 사용. 배치/스케줄러는 자동 처리됨.
- **3D가 안 보임** → 하드웨어 가속/구형 브라우저 문제여도 페이지는 정상 동작(배경만 비활성).
