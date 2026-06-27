/* ============================================================
   채용보드 클라이언트 로직
   - 보안: 모든 외부(스크래핑) 데이터는 textContent 로만 주입 → XSS 차단
   - URL 은 http/https 만 허용 (javascript: 등 차단)
   - file:// 로컬: window.__JOBS__ 사용 / http 배포: jobs.json fetch
   ============================================================ */
(function () {
  "use strict";

  var TAB_ORDER = [
    "전체", "⭐ 추천",
    "정부출연(과학기술)",
    "지자체·지방연구원", "공공기관·공기업", "연구기관·진흥원", "대학·병원",
    "하이브레인넷(연구실·기업)",
    "🕒 최근 마감"
  ];
  var TAB_CLOSED = "🕒 최근 마감";

  var state = { data: null, tab: "전체", q: "", sort: "reco",
                fNew: false, fEntry: false, fSalary: false, fEmp: "", fRegion: "" };

  /* ---------- 안전 DOM 헬퍼 ---------- */
  function el(tag, attrs, kids) {
    var n = document.createElement(tag);
    if (attrs) for (var k in attrs) {
      if (k === "class") n.className = attrs[k];
      else if (k === "text") n.textContent = attrs[k];      // 항상 textContent
      else if (k === "html") { /* 의도적으로 미지원 */ }
      else n.setAttribute(k, attrs[k]);
    }
    if (kids) (Array.isArray(kids) ? kids : [kids]).forEach(function (c) {
      if (c == null) return;
      n.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
    });
    return n;
  }
  function safeUrl(u) {
    if (typeof u !== "string") return null;
    return /^https?:\/\//i.test(u.trim()) ? u.trim() : null;
  }

  /* ---------- 날짜 / D-day ---------- */
  function parseEnd(s) {              // "26.07.03" → Date
    if (!s) return null;
    var m = /(\d{2})\.(\d{2})\.(\d{2})/.exec(s);
    if (!m) return null;
    return new Date(2000 + (+m[1]), (+m[2]) - 1, (+m[3]));
  }
  function ddayInfo(job) {
    var d = parseEnd(job.endDate);
    if (!d) return { text: job.dday || "상시", n: 9999, urgent: false };
    var today = new Date(); today.setHours(0, 0, 0, 0);
    var diff = Math.round((d - today) / 86400000);
    if (diff < 0) return { text: "마감", n: -1, urgent: false };
    if (diff === 0) return { text: "오늘마감", n: 0, urgent: true };
    return { text: "D-" + diff, n: diff, urgent: diff <= 5 };
  }

  /* ---------- 고용형태 → 배지 클래스 ---------- */
  function empClass(emp) {
    if (!emp) return "emp-temp";
    if (/무기계약/.test(emp)) return "emp-perm";
    if (/비정규|계약/.test(emp)) return "emp-temp";
    if (/인턴/.test(emp)) return "emp-intern";
    if (/정규직/.test(emp)) return "emp-reg";
    return "emp-temp";
  }

  /* ---------- 카드 ---------- */
  function card(job) {
    var dd = ddayInfo(job);
    var reco = job.score >= 40;
    var c = el("article", { class: "card " + (job.score >= 40 ? "s-good" : job.score >= 25 ? "s-mid" : "") + (reco ? " reco" : "") + (job.closed ? " is-closed" : "") });

    c.appendChild(el("div", { class: "card-top" }, [
      el("span", { class: "org", text: job.org || "기관" }),
      el("span", { class: "src", text: job.source || "" })
    ]));
    c.appendChild(el("h3", { class: "title", text: job.title || "" }));

    /* 배지들 */
    var badges = el("div", { class: "badges" });
    if (job.isNew && !job.closed) badges.appendChild(el("span", { class: "badge new", text: "🆕 NEW" }));
    if (reco) badges.appendChild(el("span", { class: "badge reco", text: "⭐ 추천" }));
    if (job.emp) badges.appendChild(el("span", { class: "badge " + empClass(job.emp), text: job.emp }));
    if (job.edu) badges.appendChild(el("span", { class: "badge edu", text: "🎓 " + job.edu }));
    badges.appendChild(el("span", { class: "badge dday" + (dd.urgent ? "" : " safe"), text: dd.text }));
    c.appendChild(badges);

    /* 필드 정의목록 */
    var dl = el("dl", { class: "fields" });
    function row(label, val) {
      if (!val) return;
      dl.appendChild(el("dt", { text: label }));
      dl.appendChild(el("dd", { text: val }));
    }
    row("지원기간", job.period);
    row("근무지", job.location);
    row("계약형태", job.emp);
    row("연봉", job.salary ? job.salary : "공고문 참조(비공개)");
    if (job.headcount) row("채용인원", job.headcount);
    if (job.career) row("채용구분", job.career);
    if (job.field) row("근무분야", job.field);
    if (job.pref) row("우대사항", job.pref);
    c.appendChild(dl);

    /* 추천 사유 */
    if (job.reasons && job.reasons.length) {
      var rs = el("div", { class: "reasons" });
      job.reasons.forEach(function (r) { rs.appendChild(el("span", { class: "reason", text: r })); });
      c.appendChild(rs);
    }

    /* 응시자격 (접힘) — 문단 줄바꿈 보존(white-space:pre-line) */
    if (job.elig) {
      c.appendChild(el("div", { class: "elig-label", text: "📋 응시자격" }));
      var body = job.elig.replace(/^응시자격\s*/, "");   // 중복 라벨 제거
      var box = el("div", { class: "elig collapsed", text: body });
      var more = el("button", { class: "elig-more", type: "button", text: "자세히 보기 ▾" });
      more.addEventListener("click", function () {
        var col = box.classList.toggle("collapsed");
        box.style.maxHeight = col ? "" : "none";
        more.textContent = col ? "자세히 보기 ▾" : "접기 ▴";
      });
      c.appendChild(box); c.appendChild(more);
    }

    /* 하단: 점수 + 지원 */
    var foot = el("div", { class: "card-foot" });
    var bar = el("span", { class: "bar" }, el("i"));
    bar.firstChild.style.width = Math.min(100, Math.round(job.score / 70 * 100)) + "%";
    foot.appendChild(el("span", { class: "scorepill" }, [el("span", { text: "근로조건 " + (job.score || 0) }), bar]));
    var url = safeUrl(job.url);
    if (url) {
      var a = el("a", { class: "apply", href: url, target: "_blank", rel: "noopener noreferrer nofollow", text: "공고 보기 →" });
      foot.appendChild(a);
    }
    c.appendChild(foot);
    return c;
  }

  /* ---------- 필터/정렬 ---------- */
  function visibleJobs() {
    var jobs = (state.data.jobs || []).slice();
    if (state.tab === TAB_CLOSED) {
      jobs = jobs.filter(function (j) { return j.closed; });               // 마감 탭: 지난 공고만
    } else {
      jobs = jobs.filter(function (j) { return !j.closed; });              // 그 외 탭: 진행중만
      if (state.tab === "⭐ 추천") jobs = jobs.filter(function (j) { return j.score >= 40; });
      else if (state.tab !== "전체") jobs = jobs.filter(function (j) { return j.type === state.tab; });
    }
    if (state.q) {
      var q = state.q.toLowerCase();
      jobs = jobs.filter(function (j) {
        return [j.org, j.title, j.location, j.field, j.elig, j.pref].join(" ").toLowerCase().indexOf(q) >= 0;
      });
    }
    // 고급 필터
    if (state.fNew)    jobs = jobs.filter(function (j) { return j.isNew; });
    if (state.fEntry)  jobs = jobs.filter(function (j) { return /신입/.test(j.career || ""); });
    if (state.fSalary) jobs = jobs.filter(function (j) { return j.salary && /\d/.test(j.salary); });
    if (state.fEmp) {
      jobs = jobs.filter(function (j) {
        var e = j.emp || "";
        if (state.fEmp === "reg")    return /정규직|무기계약/.test(e);
        if (state.fEmp === "temp")   return /계약|기간제|비정규/.test(e) && !/무기계약/.test(e);
        if (state.fEmp === "intern") return /인턴/.test(e);
        return true;
      });
    }
    if (state.fRegion) jobs = jobs.filter(function (j) { return (j.location || "").indexOf(state.fRegion) >= 0; });
    jobs.sort(function (a, b) {
      if (state.sort === "deadline") return ddayInfo(a).n - ddayInfo(b).n;
      if (state.sort === "org") return (a.org || "").localeCompare(b.org || "", "ko");
      return (b.score - a.score) || (ddayInfo(a).n - ddayInfo(b).n);   // reco
    });
    return jobs;
  }

  /* ---------- 탭 ---------- */
  function buildTabs() {
    var counts = {}, all = state.data.jobs || [];
    var active = all.filter(function (j) { return !j.closed; });
    active.forEach(function (j) { counts[j.type] = (counts[j.type] || 0) + 1; });
    counts["전체"] = active.length;
    counts["⭐ 추천"] = active.filter(function (j) { return j.score >= 40; }).length;
    counts[TAB_CLOSED] = all.length - active.length;       // 최근 마감 건수
    var host = document.getElementById("tabs");
    host.textContent = "";
    TAB_ORDER.forEach(function (name) {
      if (name !== "전체" && name !== "⭐ 추천" && !counts[name]) return;   // 빈 탭 숨김(마감 0건이면 숨김)
      var cls = "tab" + (name === state.tab ? " active" : "") + (name === "⭐ 추천" ? " star" : "") + (name === TAB_CLOSED ? " closed" : "");
      var t = el("button", { class: cls, type: "button" }, [
        document.createTextNode(name + " "),
        el("span", { class: "cnt", text: String(counts[name] || 0) })
      ]);
      t.addEventListener("click", function () { state.tab = name; render(); });
      host.appendChild(t);
    });
  }

  /* ---------- 렌더 ---------- */
  function render() {
    buildTabs();
    var jobs = visibleJobs();
    var grid = document.getElementById("grid");
    grid.textContent = "";
    document.getElementById("resultMeta").textContent =
      "‘" + state.tab + "’ · " + jobs.length + "건" + (state.q ? " · 검색: " + state.q : "");
    if (!jobs.length) {
      grid.appendChild(el("div", { class: "empty" }, [
        el("div", { class: "big", text: "🔍" }),
        el("div", { text: "조건에 맞는 공고가 없습니다." })
      ]));
      return;
    }
    var frag = document.createDocumentFragment();
    jobs.forEach(function (j) { frag.appendChild(card(j)); });
    grid.appendChild(frag);
  }

  /* ---------- 헤더 통계 ---------- */
  function fillStats() {
    var d = state.data;
    document.getElementById("stCount").textContent = d.count || (d.jobs ? d.jobs.length : 0);
    document.getElementById("stCompanies").textContent = d.companies || "-";
    document.getElementById("stReco").textContent = d.recommended != null ? d.recommended :
      (d.jobs || []).filter(function (j) { return !j.closed && j.score >= 40; }).length;
    document.getElementById("updated").textContent = d.updatedAtKr || d.updatedAt || "-";
  }

  /* ---------- 데이터 로드 ---------- */
  function applyData(d) {
    state.data = d; fillStats(); fillRegions(); render();
  }
  function loadFresh() {
    // http(s) 환경에서만 fetch 시도 (file:// 은 차단됨)
    return fetch("data/jobs.json?t=" + Date.now(), { cache: "no-store" })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); });
  }
  function boot() {
    if (location.protocol === "http:" || location.protocol === "https:") {
      loadFresh().then(applyData).catch(function () {
        if (window.__JOBS__) applyData(window.__JOBS__);          // 로컬 서버(평문)
        else if (window.__decryptGate__) window.__decryptGate__(applyData); // 배포본(암호화)
        else showLoadError();
      });
    } else if (window.__JOBS__) {
      applyData(window.__JOBS__);                                  // file:// 로컬
    } else {
      showLoadError();
    }
  }
  function showLoadError() {
    document.getElementById("grid").appendChild(el("div", { class: "empty" }, [
      el("div", { class: "big", text: "⚠️" }),
      el("div", { text: "데이터를 불러오지 못했습니다. update_jobs.ps1 을 먼저 실행하세요." })
    ]));
  }

  /* ---------- 새로고침 버튼 ---------- */
  function bindRefresh() {
    var btn = document.getElementById("refreshBtn");
    btn.addEventListener("click", function () {
      btn.classList.add("loading");
      if (location.protocol === "http:" || location.protocol === "https:") {
        loadFresh().then(function (d) { applyData(d); flash("최신 데이터로 갱신했습니다 ✓"); })
          .catch(function () {
            if (window.__decryptGate__) { flash("최신 데이터를 다시 엽니다…"); setTimeout(function () { location.reload(); }, 350); }
            else flash("갱신 실패 — 잠시 후 다시 시도하세요");
          })
          .then(function () { btn.classList.remove("loading"); });
      } else {
        // file:// : 스크래퍼 결과(jobs.js)를 다시 읽도록 새로고침
        flash("로컬 파일을 다시 읽습니다…");
        setTimeout(function () { location.reload(); }, 350);
      }
    });
  }
  function flash(msg) {
    var f = document.getElementById("flash");
    f.textContent = msg; f.classList.add("show");
    setTimeout(function () { f.classList.remove("show"); }, 2600);
  }

  /* ---------- 근무지 옵션 채우기 ---------- */
  function fillRegions() {
    var sel = document.getElementById("fRegion");
    if (!sel || sel.options.length > 1) return;
    var counts = {};
    (state.data.jobs || []).forEach(function (j) {
      var loc = (j.location || "").trim();
      var m = loc.match(/(서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충북|충남|전북|전남|경북|경남|제주)/);
      if (m) counts[m[1]] = (counts[m[1]] || 0) + 1;
    });
    Object.keys(counts).sort(function (a, b) { return counts[b] - counts[a]; }).forEach(function (r) {
      sel.appendChild(el("option", { value: r, text: r + " (" + counts[r] + ")" }));
    });
  }

  /* ---------- 컨트롤 바인딩 ---------- */
  function bindControls() {
    var s = document.getElementById("search");
    var t;
    s.addEventListener("input", function () {
      clearTimeout(t); t = setTimeout(function () { state.q = s.value.trim(); render(); }, 160);
    });
    document.getElementById("sort").addEventListener("change", function (e) {
      state.sort = e.target.value; render();
    });
    function bindChk(id, key) {
      var el2 = document.getElementById(id);
      if (el2) el2.addEventListener("change", function () { state[key] = el2.checked; render(); });
    }
    function bindSel(id, key) {
      var el2 = document.getElementById(id);
      if (el2) el2.addEventListener("change", function () { state[key] = el2.value; render(); });
    }
    bindChk("fNew", "fNew"); bindChk("fEntry", "fEntry"); bindChk("fSalary", "fSalary");
    bindSel("fEmp", "fEmp"); bindSel("fRegion", "fRegion");
    var clr = document.getElementById("fClear");
    if (clr) clr.addEventListener("click", function () {
      state.fNew = state.fEntry = state.fSalary = false; state.fEmp = ""; state.fRegion = "";
      ["fNew", "fEntry", "fSalary"].forEach(function (id) { var e = document.getElementById(id); if (e) e.checked = false; });
      ["fEmp", "fRegion"].forEach(function (id) { var e = document.getElementById(id); if (e) e.value = ""; });
      render();
    });
  }

  /* ---------- 다크 모드 ---------- */
  function initTheme() {
    var saved = null;
    try { saved = localStorage.getItem("jb_theme"); } catch (e) {}
    if (saved === "dark") document.documentElement.setAttribute("data-theme", "dark");
    var btn = document.getElementById("themeBtn");
    function sync() { if (btn) btn.textContent = document.documentElement.getAttribute("data-theme") === "dark" ? "☀️" : "🌙"; }
    sync();
    if (btn) btn.addEventListener("click", function () {
      var dark = document.documentElement.getAttribute("data-theme") === "dark";
      if (dark) document.documentElement.removeAttribute("data-theme");
      else document.documentElement.setAttribute("data-theme", "dark");
      try { localStorage.setItem("jb_theme", dark ? "light" : "dark"); } catch (e) {}
      sync();
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    initTheme(); bindControls(); bindRefresh(); boot();
  });
})();
