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

## 🔁 매일 자동 갱신 (하이브리드) + 📧 링크·비밀번호 메일

> ⚠️ **왜 하이브리드?** 한국 정부 채용사이트(잡알리오·나라일터 등)가 **GitHub 해외 러너 IP를 차단**해
> 클라우드(Actions) 수집은 불가능합니다. 그래서 **수집·암호화·푸시·메일은 한국에 있는 이 PC**가 맡고,
> **GitHub는 푸시받은 암호문을 Pages로 배포만** 합니다.

작업 스케줄러(`PublicJobBoard_DailyUpdate`, 매일 08:00)가 `run_daily.bat` → **`publish.py`** 를 실행:
**① 수집(`scrape.py`) → ② 그날 비번으로 암호화(`build_secure.py`) → ③ `git push`(=Pages 배포) → ④ 링크+비번 메일(`email_digest.py --link`)**

```powershell
# 재등록 / 시간 변경
.\setup_schedule.ps1
# 즉시 실행(테스트) — 수집·암호화·푸시·메일 전부
Start-ScheduledTask -TaskName PublicJobBoard_DailyUpdate
# 해제
Unregister-ScheduledTask -TaskName PublicJobBoard_DailyUpdate -Confirm:$false
```
- 로그: `logs\daily.log`.
- 📌 PC가 08시에 꺼져 있어도 `StartWhenAvailable` 옵션으로 **켜지면 곧 따라잡아 실행**됩니다.

### 📧 이메일 설정 (최초 1회)
1. **Gmail 앱 비밀번호 발급**: 구글 계정 → 보안 → 2단계 인증 → '앱 비밀번호' 16자.
2. **`email_config.json`** 의 `"password"`(16자)와 `"site_url"`(예: `https://<id>.github.io/job-board/`) 설정. 이 파일은 `.gitignore`로 커밋 제외.
3. **테스트**:
   ```powershell
   .\.venv\Scripts\python publish.py                       # 전체 파이프라인(수집·암호화·푸시·메일)
   .\.venv\Scripts\python email_digest.py --link --preview # 메일 발송 없이 미리보기만
   ```
- 메일엔 **링크 + 그날의 비밀번호**가 담깁니다. 링크를 열고 비번을 넣어야 공고가 보입니다(데이터는 매일 새 키로 암호화).
- 전체 공고를 본문에 담는 다이제스트가 필요하면 인자 없이 `email_digest.py`.

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

- **잡알리오**: 진행중 · 근무분야 `연구직`/`교수직` · **학사·석사**(학력 무관 포함, **박사 전용 공고 제외**). 기관당 최대 4건.
- **하이브레인넷**: `연구원`(RES) · `정출연·국공립연구소`(GOVLAB) · **`정부·공공·지자체`(GOVORG)** 카테고리 (박사후/Post-Doc 제외).
- **고용24**(work24.go.kr 공식 OpenAPI, 선택): 환경변수 `WORK24_KEY` 설정 시 활성화. **정부·지자체·민간 채용을 폭넓게 커버**(국가 고용포털).
  - 키 발급: work24.go.kr → 고객센터 → OPEN-API → 회원가입 후 인증키 신청(무료). 엔드포인트 `callOpenApiSvcInfo210L01.do`.
  - 로컬: `setx WORK24_KEY "발급키"` 후 새 창에서 `publish.py` 실행.
  - 분야 키워드(기상·대기환경·환경·해양기상·농림기상·데이터분석·인공지능·대기측정 등)로 다중 조회.
- **워크넷**(공공데이터포털 API, 선택): `WORKNET_KEY` 설정 시. 키 발급: https://www.data.go.kr → ‘한국고용정보원_워크넷 채용정보’.
- **나라일터**: best-effort. 목록을 AJAX로 동적 로딩해 정적 파싱으론 0건 → 정부·지자체 채용은 **고용24 API로 대체 커버**.
- **사람인·잡플래닛·캐치**: 자동수집 미지원 — 이들은 ToS상 스크래핑 금지 + 봇 차단(로그인·캡차)이라 안정적 자동수집 불가. 대신 **고용24 API가 민간 공고도 상당수 포함**하므로 그쪽으로 커버 권장.
- **🎯 전공 필터(내 분야 한정)**: 제목·기관·전공·자격 텍스트가 다음에 해당할 때만 통과.
  - **기상학·대기환경·환경·농림기상·해양기상·데이터분석·AI·환경컨설팅·대기측정** 및 인접어(기후·미세먼지·오존·온실가스·환경영향평가·환경모니터링·수질·생태·통계·머신러닝·원격탐사·수치모델 등).
  - 영문 약어 `AI·ML·DL·ESG·GHG·LCA·GIS·RS·AQI·PM2.5·PM10·CEMS·TMS` 매칭(단어경계).
  - `환경미화·시설관리·경비·방역` 등 비기술 ‘환경’ 공고는 제외(NEG 필터). 전기전자·기계·화학·바이오·의료·토목 등 타 이공계도 제외.

### 네비게이션 탭(회사 유형)
정부출연(과학기술) / 정부출연(경제인문사회) / 지자체·지방연구원 / 공공기관·공기업 / 연구기관·진흥원 / 대학·병원 / 하이브레인넷 — 그리고 **⭐ 추천** 탭.

> 다른 사이트를 추가하려면 `scrape.py`에 `get_xxx()` 함수를 만들어 동일 스키마(dict)로 반환 후 `main()`의 `allj += get_xxx()` 한 줄만 추가.

---

## 🧮 근로조건 점수(가중치)

| 항목 | 가점 |
|---|---|
| 정규직(정년보장) | +50 |
| 무기계약직(고용안정) | +34 |
| 계약/비정규직 | **+5** (하향) |
| 인턴 | +3 |
| 연봉(보수) 공개 | +12 |
| 신입 지원가능 | +6 |
| 정부출연연 | +8 |
| 지자체 연구원 | +5 |
| 전문분야 적합(키워드 다수) | +5 |
| 우대사항 있음 | +4 |

> 변경: **채용형 인턴(+18) 항목 삭제**, **계약직 +10 → +5 하향**.

- **40점 이상** → `⭐ 추천` 배지 + 추천 탭/추천순 상단. (가중치 하향에 맞춰 48→40)
- ⚠️ 추정치입니다. 지원 전 반드시 원문 공고·첨부 공고문에서 자격·연봉·접수기간을 확인하세요.

---

## 🛡️ 보안 (공개 배포 대비)

- **정적 사이트**(백엔드/DB 없음) → 공격면 최소.
- **XSS 차단** — 스크래핑 데이터는 전부 `textContent`로만 DOM 주입(HTML 미해석). 링크는 `http(s)`만 허용, `rel="noopener noreferrer"`.
- **CSP `default-src 'self'`** — 외부 CDN 0개(Three.js 자체 호스팅)라 `script-src 'self'`로 가장 엄격.
- **보안 헤더** — `nosniff`·`X-Frame-Options: DENY`·`Referrer-Policy: no-referrer`·`Permissions-Policy`·`HSTS`·COOP/CORP. (`deploy/` 및 `tools/serve.ps1`)

### 🔐 비공개 배포 (GitHub Pages + 매일 비밀번호) — 현재 구성
"링크 하나로 어디서든 보되, 나만 접속"을 위해 **데이터를 매일 새 비밀번호로 암호화**합니다. (하이브리드: 위 _매일 자동 갱신_ 참고)

- **암호화**: `build_secure.py` 가 `jobs.json` → `data/jobs.enc.json`(AES-256-GCM, PBKDF2-SHA256 200k). 배포본엔 **암호문만** 올라가고 평문 `jobs.json`/`jobs.js`는 `.gitignore`로 제외.
- **게이트**: `assets/gate.js` 가 비밀번호 입력 → 브라우저 Web Crypto로 복호화 후 렌더. 틀리면 안 열림.
- **수집·암호화·푸시·메일**: 로컬 `publish.py`(작업 스케줄러). 한국 PC라 정부사이트 수집이 안정적.
- **배포**: `.github/workflows/update.yml` 은 **푸시 트리거 배포 전용**(수집 안 함). `data/jobs.enc.json` 이 푸시되면 Pages로 자동 배포.
- **Pages 설정**: 저장소 Settings → Pages → **Build and deployment: GitHub Actions**.
- **로컬 설정**: `email_config.json` 에 `password`(Gmail 앱 비번)·`site_url`. git 자격증명은 `gh auth login` 으로 1회 설정(푸시용).

> 보안 근거: 비밀번호는 4자리×4그룹(혼동문자 제외) 무작위 + PBKDF2 200k → 공개 저장소의 암호문이라도 브루트포스 비현실적.

### 그 외 공개 배포 (택1)
- **Netlify / Cloudflare Pages**: 폴더 그대로 배포 + `deploy/_headers`(또는 `netlify.toml`)를 루트로.
- **자체 nginx**: `deploy/nginx-security.conf`를 `server {}`에 포함.

---

## ❓ 문제 해결

- **카드가 안 보임** → `run_update.bat` 먼저 실행해 `data/jobs.json`·`jobs.js` 생성.
- **`python`이 Store 창을 띄움** → 실제 설치본(`%LOCALAPPDATA%\Programs\Python\Python312\python.exe`) 사용. 배치/스케줄러는 자동 처리됨.
- **3D가 안 보임** → 하드웨어 가속/구형 브라우저 문제여도 페이지는 정상 동작(배경만 비활성).
