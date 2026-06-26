/* ============================================================
   비밀번호 게이트 (배포본 전용)
   - 배포본에는 data/jobs.enc.json (AES-256-GCM) 만 존재.
   - 사용자가 '오늘의 비밀번호'를 입력하면 브라우저에서 복호화 → window.__JOBS__ 주입.
   - 로컬(file:// 또는 평문 jobs.json 있는 서버)에서는 게이트가 뜨지 않음.
   - 인라인 스타일/스크립트 없음 (CSP script-src 'self' 준수). 스타일은 styles.css.
   ============================================================ */
(function () {
  "use strict";

  function b64ToBytes(s) {
    var bin = atob(s);
    var out = new Uint8Array(bin.length);
    for (var i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
    return out;
  }

  function elem(tag, attrs, kids) {
    var n = document.createElement(tag);
    if (attrs) for (var k in attrs) {
      if (k === "class") n.className = attrs[k];
      else if (k === "text") n.textContent = attrs[k];
      else n.setAttribute(k, attrs[k]);
    }
    (kids || []).forEach(function (c) { if (c != null) n.appendChild(c); });
    return n;
  }

  async function decrypt(blob, password) {
    var enc = new TextEncoder();
    var baseKey = await crypto.subtle.importKey(
      "raw", enc.encode(password), { name: "PBKDF2" }, false, ["deriveKey"]);
    var key = await crypto.subtle.deriveKey(
      { name: "PBKDF2", salt: b64ToBytes(blob.salt), iterations: blob.iter, hash: blob.hash || "SHA-256" },
      baseKey, { name: "AES-GCM", length: 256 }, false, ["decrypt"]);
    var ptBuf = await crypto.subtle.decrypt(
      { name: "AES-GCM", iv: b64ToBytes(blob.iv) }, key, b64ToBytes(blob.ct));
    return JSON.parse(new TextDecoder().decode(ptBuf));
  }

  // app.js 가 평문 데이터를 못 찾았을 때 호출한다. onData(data) 로 결과를 넘긴다.
  window.__decryptGate__ = function (onData) {
    var input, msg, btn, overlay;

    function setBusy(b) {
      btn.disabled = b; input.disabled = b;
      btn.textContent = b ? "여는 중…" : "열기";
    }
    function fail(text) {
      setBusy(false);
      msg.textContent = text;
      msg.className = "gate-msg err";
      input.focus(); input.select();
    }

    async function submit() {
      var pw = (input.value || "").trim();
      if (!pw) { fail("비밀번호를 입력하세요."); return; }
      setBusy(true);
      msg.textContent = ""; msg.className = "gate-msg";
      try {
        var res = await fetch("data/jobs.enc.json?t=" + Date.now(), { cache: "no-store" });
        if (!res.ok) throw new Error("blob " + res.status);
        var blob = await res.json();
        var data = await decrypt(blob, pw);
        try { sessionStorage.setItem("jb_key", pw); } catch (e) {}
        overlay.classList.add("hide");
        setTimeout(function () { overlay.remove(); }, 320);
        onData(data);
      } catch (e) {
        fail("비밀번호가 올바르지 않거나 데이터를 열 수 없습니다.");
      }
    }

    input = elem("input", { type: "password", class: "gate-input", placeholder: "오늘의 비밀번호",
                            autocomplete: "off", autocapitalize: "off", spellcheck: "false",
                            "aria-label": "비밀번호" });
    btn = elem("button", { type: "button", class: "gate-btn", text: "열기" });
    msg = elem("div", { class: "gate-msg" });
    btn.addEventListener("click", submit);
    input.addEventListener("keydown", function (e) { if (e.key === "Enter") submit(); });

    var card = elem("div", { class: "gate-card" }, [
      elem("div", { class: "gate-emoji", text: "🔒" }),
      elem("h2", { class: "gate-title", text: "공공·연구기관 채용보드" }),
      elem("p", { class: "gate-sub", text: "비밀번호를 입력하세요." }),
      elem("div", { class: "gate-row" }, [input, btn]),
      msg
    ]);
    overlay = elem("div", { class: "gate-overlay", role: "dialog", "aria-modal": "true" }, [card]);
    document.body.appendChild(overlay);

    // 세션 내 자동 재진입(같은 탭에서 새로고침 시 다시 안 묻기)
    var saved = null;
    try { saved = sessionStorage.getItem("jb_key"); } catch (e) {}
    if (saved) { input.value = saved; submit(); }
    else { setTimeout(function () { input.focus(); }, 60); }
  };
})();
