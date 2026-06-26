# -*- coding: utf-8 -*-
"""
공공·연구기관 「석사급(석사 이상·박사 미만) · 자연과학/이공계」 채용공고 수집기
소스: 잡알리오 + 하이브레인넷(연구원/정출연·국공립/지자체) + 워크넷 API(선택) + 나라일터(best-effort)

출력: data/jobs.json, data/jobs.js  (프론트엔드 index.html 이 읽음)
실행: python scrape.py
"""
import os, re, json, sys, time, html
from datetime import datetime

# 콘솔이 없는(작업 스케줄러/CI) 환경에서도 한글·이모지 출력이 죽지 않도록 UTF-8 강제
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import requests
from bs4 import BeautifulSoup

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
os.makedirs(DATA, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
UA_M = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15"}
TIMEOUT = 40


def GET(url, retries=3, backoff=3, **kw):
    """타임아웃/일시 오류에 재시도. 해외(GitHub Actions) IP에서 한국 사이트가 간헐적으로
    느리거나 막히는 경우를 완화한다."""
    kw.setdefault("timeout", TIMEOUT)
    last = None
    for i in range(retries):
        try:
            return requests.get(url, **kw)
        except Exception as ex:
            last = ex
            if i < retries - 1:
                time.sleep(backoff * (i + 1))
    raise last

# ----------------------------------------------------------------------------
# 자연과학/이공계 전공 필터 (기상·대기·환경·데이터·AI 등으로 정밀 축소)
#  - 한글 키워드(STEM_KO): 자연과학·공학 전공/분야어
#  - 영문 약어(STEM_EN): 단어경계 + 대소문자 구분 → "email/main"의 ai/it 오탐 차단
#  - 일반 행정어로 오인되기 쉬운 단어(안전·보건·정보)는 구체형으로만 인정
# ----------------------------------------------------------------------------
STEM_KO = re.compile(
    r"기상|대기환경|대기질|대기오염|대기과학|기후변화|기후|온실가스|탄소중립|탄소배출|미세먼지|오존|"
    r"환경|생태|생물다양성|수질|수자원|상하수도|하수|폐기물|자원순환|재활용|악취|토양|수문|"
    r"해양|수산|어업|양식|지질|지구과학|천문|우주|위성|원격탐사|"
    r"농업|농학|원예|임학|산림|축산|수의|식품|발효|종자|"
    r"화학|화공|소재|신소재|재료|금속|섬유|고분자|촉매|분광|반도체|디스플레이|배터리|"
    r"전기|전자|제어|계측|기계|로봇|자동차|항공|조선|에너지|신재생|태양광|풍력|수소|원자력|핵융합|전력|"
    r"물리|광학|레이저|음향|"
    r"생물|생명|바이오|유전체|유전|미생물|면역|세포|단백질|신경과학|뇌과학|"
    r"의생명|의료|보건의료|보건환경|공중보건|약학|간호|방사선|영상의학|진단|병리|역학|"
    r"데이터|빅데이터|통계|머신러닝|딥러닝|인공지능|알고리즘|"
    r"정보통신|정보보호|정보보안|사이버보안|소프트웨어|네트워크|클라우드|블록체인|컴퓨터공학|"
    r"토목|건설|건축|구조공학|지반|도시계획|교통공학|교통계획|교통정책|도로교통|방재|재난|산업안전|"
    r"공간정보|측량|수치모델|수치해석|모델링|시뮬레이션|시험분석|성분분석|실험|계량|"
    r"공학|이학|자연과학|과학기술|나노|디지털트윈"
)
STEM_EN = re.compile(r"\b(AI|ML|DL|IT|ICT|IoT|GIS|RS|R&?D|ESG|GHG|LCA|BIM|CFD|HVAC|EV|GHGs)\b")
def is_science(*texts) -> bool:
    blob = " ".join(t for t in texts if t)
    return bool(STEM_KO.search(blob) or STEM_EN.search(blob))

# ----------------------------------------------------------------------------
# 공통 유틸
# ----------------------------------------------------------------------------
def clean(s: str) -> str:
    if not s:
        return ""
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()

def fmt_qualifications(raw: str) -> str:
    """응시자격 텍스트를 항목 단위로 줄바꿈 정리(가독성)."""
    if not raw:
        return ""
    raw = html.unescape(raw)
    # 인라인 글머리표 앞에서 줄바꿈
    raw = re.sub(r"\s*(▶|■|□|●|○|◦|•|※|☞|▷|[①②③④⑤⑥⑦⑧⑨⑩⑪⑫]|(?<![\d.])\b\d{1,2}[).]\s|[-–]\s|[가나다라마바사][).]\s)",
                 lambda m: "\n" + m.group(1).strip() + " ", raw)
    lines, out = [l.strip(" \t·") for l in raw.split("\n")], []
    for l in lines:
        l = re.sub(r"[ \t]{2,}", " ", l).strip()
        if not l:
            continue
        if re.match(r"^(전형단계|전형일정|전형방법|채용절차|제출서류|첨부|우대조건|접수방법|채용 절차)", l):
            break
        out.append(l)
    text = "\n".join(out)
    return (text[:950] + "…") if len(text) > 950 else text

# ----------------------------------------------------------------------------
# 기관유형 분류 (네비게이션 탭)
# ----------------------------------------------------------------------------
JACHI = re.compile(
    r"(서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충북|충남|전북|전남|경북|경남|제주)\S{0,3}연구원|"
    r"보건환경연구원|농업기술원|산림환경연구원|해양수산연구원|지방.*연구원|시정연구원|발전연구원")
SCI_GOV = re.compile(
    r"기초과학연구원|한국과학기술연구원|KIST|선박해양|해양과학기술원|국방과학연구소|항공우주|전자통신연구원|ETRI|"
    r"생명공학|화학연구원|에너지기술|기계연구원|재료연구|표준과학|식품연구원|천문연구원|지질자원|핵융합|건설기술|"
    r"철도기술|전기연구원|원자력|나노|광기술|생산기술|과학기술기획평가원|KISTEP|한국과학창의재단|교육과정평가원|"
    r"한국환경연구원|국립환경과학원|국립생태원|국립기상과학원|한국해양과학기술원")
SOC_GOV = re.compile(
    r"한국개발연구원|KDI|한국노동연구원|정보통신정책연구원|산업연구원|에너지경제연구원|한국조세재정연구원|"
    r"한국보건사회연구원|한국직업능력연구원|한국형사|육아정책연구소|한국청소년정책연구원|건축공간연구원|한국해양수산개발원|"
    r"경제인문사회연구회|국토연구원|과학기술정책연구원|대외경제정책연구원|농촌경제연구원|교통연구원|여성정책연구원|"
    r"행정연구원|법제연구원|통일연구원|국방연구원")

def classify(org: str) -> str:
    if re.search(r"병원|의료원|의학원|암센터", org): return "대학·병원"
    if re.search(r"대학교|대학원|대학$", org): return "대학·병원"
    if JACHI.search(org): return "지자체·지방연구원"
    if SCI_GOV.search(org): return "정부출연(과학기술)"
    if SOC_GOV.search(org): return "정부출연(경제인문사회)"
    if re.search(r"연구원|연구소|연구회|진흥원", org): return "연구기관·진흥원"
    return "공공기관·공기업"

# ----------------------------------------------------------------------------
# 근로조건 점수 (가중치 조정판)
# ----------------------------------------------------------------------------
def score(emp, salary, pref, career, jtype, sci_strong=False):
    s, reasons = 0, []
    e = emp or ""
    if re.search(r"무기계약", e):           s += 34; reasons.append("무기계약직(고용안정)")
    elif re.search(r"비정규", e):            s += 10; reasons.append("계약직")
    elif re.search(r"청년인턴\(채용형\)", e): s += 18; reasons.append("채용형 인턴")
    elif re.search(r"청년인턴", e):          s += 4;  reasons.append("체험형 인턴")
    elif re.search(r"계약직", e):            s += 10; reasons.append("계약직")
    elif re.search(r"정규직", e):            s += 50; reasons.append("정규직(정년보장)")
    if salary and re.search(r"\d", salary):  s += 12; reasons.append("연봉 공개")
    if career and re.search(r"신입", career):s += 6;  reasons.append("신입 지원가능")
    if jtype and "정부출연" in jtype:        s += 8;  reasons.append("정부출연연")
    if jtype == "지자체·지방연구원":          s += 5;  reasons.append("지자체 연구원")
    if sci_strong:                           s += 5;  reasons.append("이공계 전문분야")
    if pref:                                 s += 4
    return s, reasons

RECO_CUTOFF = 48  # ⭐추천 기준

# ----------------------------------------------------------------------------
# 1) 잡알리오
# ----------------------------------------------------------------------------
def get_alio():
    url = ("https://job.alio.go.kr/recruit.do?pageSet=100&order=TERM_END&sort=ASC"
           "&ing=2&area=R8015&area=R8019&education=R7060")
    print("[잡알리오] 목록 수집...")
    r = GET(url, headers=UA); r.encoding = "utf-8"
    soup = BeautifulSoup(r.text, "html.parser")
    rows = []
    for tb in soup.select("table.tbl.type_03 tbody tr"):
        a = tb.select_one("a[href*='recruitview.do']")
        if not a:
            continue
        tds = tb.find_all("td")
        if len(tds) < 8:
            continue
        m = re.search(r"idx=(\d+)", a.get("href", ""))
        if not m:
            continue
        end_raw = clean(tds[7].get_text(" "))
        end = (re.search(r"\d{2}\.\d{2}\.\d{2}", end_raw) or [""])
        end = end.group(0) if hasattr(end, "group") else ""
        rows.append(dict(idx=m.group(1), title=clean(a.get_text()), org=clean(tds[3].get_text()),
                         loc=clean(tds[4].get_text()), emp=clean(tds[5].get_text()),
                         reg=clean(tds[6].get_text()), end=end))
    print(f"[잡알리오] 목록 {len(rows)}건 → 상세 수집...")

    jobs = []
    per_company = {}
    MAX_PER_COMPANY = 3
    for i, rr in enumerate(rows, 1):
        if per_company.get(rr["org"], 0) >= MAX_PER_COMPANY:   # 한 기관 과다 노출 방지
            continue
        durl = f"https://job.alio.go.kr/recruitview.do?idx={rr['idx']}"
        sal = pref = edu = field = career = period = head = elig = ""
        try:
            d = requests.get(durl, headers=UA, timeout=TIMEOUT); d.encoding = "utf-8"
            ds = BeautifulSoup(d.text, "html.parser")
            for br in ds.find_all("br"):
                br.replace_with("\n")
            for th in ds.find_all("th"):
                td = th.find_next_sibling("td")
                if not td:
                    continue
                k, v = clean(th.get_text()), clean(td.get_text())
                if   k == "급여정보": sal = v
                elif k == "우대조건": pref = v
                elif k == "채용기간": period = v
                elif k == "학력정보": edu = v
                elif k == "근무분야": field = v
                elif k == "채용구분": career = v
                elif k == "채용인원": head = v
            if not re.search(r"\d", sal):
                sal = ""
            # 응시자격 섹션
            head_tag = None
            for tag in ds.find_all(["h3", "h4", "h5", "strong", "b"]):
                if tag.get_text(strip=True).startswith("응시자격"):
                    head_tag = tag; break
            if head_tag:
                parts = []
                for sib in head_tag.next_elements:
                    nm = getattr(sib, "name", None)
                    if nm in ("h3", "h4", "h5") and sib is not head_tag:
                        break
                    if isinstance(sib, str):
                        parts.append(sib)
                    if sum(len(p) for p in parts) > 1600:
                        break
                elig = fmt_qualifications("".join(parts))
        except Exception as ex:
            print(f"   (상세 실패 {rr['org']}: {ex})")

        if edu and ("박사" in edu) and ("석사" not in edu):   # 박사 전용 제외
            continue
        if not is_science(rr["title"], field, edu, elig, pref, rr["org"]):  # 이공계만
            continue
        if not period:
            period = f"{rr['reg']} ~ {rr['end']}"
        jtype = classify(rr["org"])
        sci_strong = len(set(STEM_KO.findall(" ".join([rr["title"], field, elig])))) >= 3
        sc, rs = score(rr["emp"], sal, pref, career, jtype, sci_strong)
        jobs.append(dict(source="잡알리오", type=jtype, org=rr["org"], title=rr["title"],
                         location=rr["loc"], emp=rr["emp"], period=period, endDate=rr["end"],
                         dday="", salary=sal, edu=edu, field=field, career=career, headcount=head,
                         elig=elig, pref=pref, score=sc, reasons=rs, url=durl))
        per_company[rr["org"]] = per_company.get(rr["org"], 0) + 1
    print(f"[잡알리오] 이공계 석사급 확정 {len(jobs)}건")
    return jobs

# ----------------------------------------------------------------------------
# 2) 하이브레인넷 (연구원 / 정출연·국공립 / 지자체연구원 키워드)
# ----------------------------------------------------------------------------
def org_from_title(title, fallback):
    """하이브레인 제목에서 기관명 추출 (없으면 fallback)."""
    m = re.search(r"([가-힣A-Za-z·()]{2,}?(?:연구원|연구소|연구회|대학교|대학병원|병원|의료원|센터|재단|진흥원|공사|공단|연구단|대학원))", title)
    return m.group(1) if m else fallback

def get_hibrain_cat(url, label):
    out = []
    try:
        h = requests.get(url, headers=UA_M, timeout=30).text
    except Exception as ex:
        print(f"[하이브레인] {label} 실패: {ex}"); return out
    ids = list(re.finditer(r'data-hbn-recruitId="(\d+)"', h))
    seen = set()
    for k, mt in enumerate(ids):
        rid = mt.group(1)
        if rid in seen:
            continue
        seen.add(rid)
        block = h[mt.start(): ids[k + 1].start() if k + 1 < len(ids) else min(mt.start() + 2200, len(h))]
        hm = re.search(r'href="(/recruitment/[^"]+)"', block)
        href = html.unescape(hm.group(1)) if hm else f"/recruitment/recruits/{rid}"
        if not href.startswith("http"):
            href = "https://www.hibrain.net" + href
        tm = re.search(r"banner-title[^>]*>(.*?)</div>", block, re.S)
        title = clean(tm.group(1)) if tm else ""
        if not title:
            continue
        if re.search(r"박사후|Post-?Doc|박사급|연구교수", title, re.I):
            continue
        if not is_science(title, label):
            continue
        dd = re.search(r"(D-\d+|오늘마감|상시채용|상시)", block)
        org = org_from_title(title, "하이브레인넷 공고")
        jtype = classify(org if org != "하이브레인넷 공고" else title)
        if jtype == "공공기관·공기업":
            jtype = "하이브레인넷(연구실·기업)"
        sc, rs = score("연구직", "", "", "", jtype)
        out.append(dict(source="하이브레인넷", type=jtype, org=org, title=title,
                        location="", emp="연구직", period="", endDate="", dday=(dd.group(1) if dd else ""),
                        salary="", edu="석사 이상", field="연구", career="", headcount="",
                        elig="", pref="", score=sc + 12, reasons=rs + ["연구전문 채용"], url=href))
        if len(out) >= 14:
            break
    return out

def get_hibrain():
    print("[하이브레인넷] 수집...")
    res = []
    res += get_hibrain_cat("https://m.hibrain.net/recruitment/categories/JOB/categories/RES/recruits", "연구원")
    res += get_hibrain_cat("https://m.hibrain.net/recruitment/categories/COMP/categories/GOVLAB/recruits", "정출연·국공립연구소")
    res += get_hibrain_cat("https://m.hibrain.net/recruitment/categories/COMP/categories/GOVORG/recruits", "정부·공공·지자체")
    seen, uniq = set(), []
    for j in res:
        key = re.sub(r"\s+", "", j["title"])[:40]   # 제목 기준 중복 제거(카테고리 중복 방지)
        if key not in seen:
            seen.add(key); uniq.append(j)
    print(f"[하이브레인넷] {len(uniq)}건")
    return uniq

# ----------------------------------------------------------------------------
# 3) 워크넷 (공공데이터포털 공식 API, 선택) — 환경변수 WORKNET_KEY 필요
#    키 발급: https://www.data.go.kr  '한국고용정보원_워크넷 채용정보' 검색
# ----------------------------------------------------------------------------
def get_worknet():
    key = os.environ.get("WORKNET_KEY", "").strip()
    if not key:
        print("[워크넷] WORKNET_KEY 미설정 → 건너뜀 (README 참조)")
        return []
    out = []
    try:
        base = "https://apis.data.go.kr/1051000/recruitment/list"
        params = dict(serviceKey=key, numOfRows=100, pageNo=1, resultType="json")
        r = requests.get(base, params=params, headers=UA, timeout=30)
        data = r.json()
        items = (((data.get("result") or data).get("items")) or data.get("items") or [])
        if isinstance(items, dict):
            items = items.get("item", [])
        for it in items:
            title = clean(str(it.get("instNm", "")) + " " + str(it.get("recrutPbancTtl", it.get("title", ""))))
            org = clean(str(it.get("instNm", "")))
            if not is_science(title):
                continue
            url = it.get("srcUrl") or it.get("url") or "https://www.work24.go.kr"
            jtype = classify(org or title)
            sc, rs = score("", "", "", "", jtype)
            out.append(dict(source="워크넷", type=jtype, org=org or "워크넷 공고", title=title or "채용공고",
                            location=clean(str(it.get("workRgnNmLst", ""))), emp=clean(str(it.get("hireTypeNmLst", ""))),
                            period=clean(f"{it.get('pbancBgngYmd','')} ~ {it.get('pbancEndYmd','')}"),
                            endDate="", dday="", salary="", edu="석사 이상", field="연구", career="",
                            headcount="", elig="", pref="", score=sc, reasons=rs, url=url))
        print(f"[워크넷] {len(out)}건")
    except Exception as ex:
        print(f"[워크넷] 실패(건너뜀): {ex}")
    return out

# ----------------------------------------------------------------------------
# 4) 나라일터 (지자체 연구사/연구관) — best-effort
# ----------------------------------------------------------------------------
def get_narailteo():
    out = []
    try:
        s = requests.Session()
        s.get("https://www.gojobs.go.kr/apmList.do", headers=UA, timeout=20)
        r = s.post("https://www.gojobs.go.kr/apmList.do", headers=UA,
                   data={"pageIndex": "1", "searchKeyword": "연구사", "recordCountPerPage": "50"}, timeout=20)
        r.encoding = "utf-8"
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.select("a[onclick*='apmInfo'], a[href*='apmInfo']"):
            title = clean(a.get_text())
            if not title or not re.search(r"연구사|연구관|연구직|연구원", title):
                continue
            if not is_science(title):
                continue
            onclick = a.get("onclick", "") or a.get("href", "")
            idm = re.search(r"(\d{5,})", onclick)
            url = f"https://www.gojobs.go.kr/apmInfo.do?empmnSn={idm.group(1)}" if idm else "https://www.gojobs.go.kr/apmList.do"
            sc, rs = score("", "", "", "", "지자체·지방연구원")
            out.append(dict(source="나라일터", type="지자체·지방연구원", org="지자체(나라일터)", title=title,
                            location="", emp="공무원(연구사)", period="", endDate="", dday="", salary="",
                            edu="석사 이상", field="연구", career="", headcount="", elig="", pref="",
                            score=sc, reasons=rs, url=url))
            if len(out) >= 12:
                break
        print(f"[나라일터] {len(out)}건")
    except Exception as ex:
        print(f"[나라일터] 실패(건너뜀): {ex}")
    return out

# ----------------------------------------------------------------------------
# 실행
# ----------------------------------------------------------------------------
def _safe(fn, name):
    """한 소스가 실패(타임아웃·차단 등)해도 전체 수집을 멈추지 않는다."""
    try:
        return fn()
    except Exception as ex:
        print(f"[{name}] 실패(건너뜀): {ex}")
        return []


def main():
    allj = []
    allj += _safe(get_alio, "잡알리오")
    allj += _safe(get_hibrain, "하이브레인넷")
    allj += _safe(get_worknet, "워크넷")
    allj += _safe(get_narailteo, "나라일터")

    # 모든 소스가 실패해 0건이면 기존 데이터를 덮어쓰지 않고 실패 종료
    # (빈 보드 배포 방지 → 직전 배포·데이터 유지)
    if not allj:
        print("\n⚠️ 수집 0건 — 모든 소스 실패로 판단. 기존 데이터를 유지하고 종료합니다.")
        sys.exit(1)

    # 정렬: 점수↓, 마감 정보 있는 것 우선
    allj.sort(key=lambda j: (-j["score"], j["endDate"] or "9"))

    # 기관당 전역 상한(과다 노출 방지) — 점수 높은 공고 우선 유지
    capped, cnt = [], {}
    for j in allj:
        c = cnt.get(j["org"], 0)
        if c >= 4:
            continue
        cnt[j["org"]] = c + 1
        capped.append(j)
    allj = capped

    placeholders = {"하이브레인넷 공고", "지자체(나라일터)", "워크넷 공고"}
    companies = len({j["org"] for j in allj if j["org"] not in placeholders})
    reco = sum(1 for j in allj if j["score"] >= RECO_CUTOFF)
    payload = dict(
        updatedAt=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        updatedAtKr=datetime.now().strftime("%Y년 %m월 %d일 %H:%M"),
        count=len(allj), companies=companies, recommended=reco,
        target="석사급(석사 이상·박사 미만) · 자연과학/이공계 연구직",
        sources=["잡알리오", "하이브레인넷", "워크넷(API)", "나라일터"],
        jobs=allj,
    )
    js = json.dumps(payload, ensure_ascii=False, indent=2)
    with open(os.path.join(DATA, "jobs.json"), "w", encoding="utf-8") as f:
        f.write(js)
    with open(os.path.join(DATA, "jobs.js"), "w", encoding="utf-8") as f:
        f.write("/* 자동생성 — 직접 수정 금지. scrape.py 가 갱신합니다. */\nwindow.__JOBS__ = " + js + ";")
    print(f"\n완료 ✅  총 {len(allj)}건 / 기관 {companies}개사 / ⭐추천 {reco}건")
    print(f"갱신: {payload['updatedAtKr']}")


if __name__ == "__main__":
    main()
