# -*- coding: utf-8 -*-
"""
data/jobs.json 을 읽어 '이메일 클라이언트에서도 보이는' 인라인 스타일 HTML 다이제스트를
만들고, Gmail(또는 임의 SMTP)로 발송한다.

- 설정 우선순위: 환경변수  →  email_config.json (로컬, git 제외)
- 비밀번호(앱 비밀번호)는 채팅/저장소에 남기지 말 것. email_config.json 에만 보관.

사용법:
  python email_digest.py            # 메일 발송
  python email_digest.py --preview  # 발송 없이 digest_preview.html 만 저장(검증용)
"""
import os, sys, json, smtplib, ssl
from email.message import EmailMessage
from datetime import datetime

# 한글 콘솔(cp949)에서 — 같은 문자 출력 시 깨지지 않도록
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.abspath(__file__))
JOBS = os.path.join(ROOT, "data", "jobs.json")
CONFIG = os.path.join(ROOT, "email_config.json")
PREVIEW = os.path.join(ROOT, "digest_preview.html")


def load_config():
    cfg = {}
    if os.path.exists(CONFIG):
        try:
            with open(CONFIG, encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception as e:
            print(f"[경고] email_config.json 읽기 실패: {e}")
    # 환경변수가 있으면 우선
    out = {
        "smtp_host": os.environ.get("SMTP_HOST", cfg.get("smtp_host", "smtp.gmail.com")),
        "smtp_port": int(os.environ.get("SMTP_PORT", cfg.get("smtp_port", 587))),
        "user":      os.environ.get("GMAIL_USER", cfg.get("user", "")),
        # 앱 비밀번호는 화면에 4자리씩 공백으로 표시되므로 공백 제거
        "password":  os.environ.get("GMAIL_APP_PASSWORD", cfg.get("password", "")).replace(" ", ""),
        "to":        os.environ.get("MAIL_TO", cfg.get("to", "")) or cfg.get("user", ""),
        "from_name": cfg.get("from_name", "채용보드 봇"),
        "site_url":  os.environ.get("SITE_URL", cfg.get("site_url", "")),
    }
    return out


def esc(s):
    s = "" if s is None else str(s)
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;"))


def safe_url(u):
    u = (u or "").strip()
    return u if u.lower().startswith(("http://", "https://")) else ""


def job_title(j):
    t = (j.get("title") or "").strip()
    if t:
        return t
    # 제목이 비면 분야/기관으로 대체
    return (j.get("field") or j.get("org") or "(제목 없음)").strip()


def build_html(data):
    jobs = data.get("jobs", [])
    updated = data.get("updatedAtKr") or data.get("updatedAt") or ""
    count = data.get("count", len(jobs))
    companies = data.get("companies", "")
    rec_n = data.get("recommended", "")

    # 점수 내림차순, 추천(>=48) 우선
    jobs_sorted = sorted(jobs, key=lambda j: j.get("score", 0), reverse=True)
    recommended = [j for j in jobs_sorted if j.get("score", 0) >= 48]

    BEIGE = "#f7f3ea"; INK = "#2b2622"; SUB = "#6f655a"
    LINE = "#e4dccb"; GOLD = "#b8893a"; CARD = "#ffffff"

    def chip(text, bg="#efe7d6", fg=SUB):
        return (f'<span style="display:inline-block;background:{bg};color:{fg};'
                f'font-size:12px;padding:2px 8px;border-radius:10px;margin:0 6px 4px 0;'
                f'white-space:nowrap;">{esc(text)}</span>')

    def card(j, star=False):
        url = safe_url(j.get("url"))
        title = esc(job_title(j))
        org = esc(j.get("org", ""))
        dday = (j.get("dday") or "").strip()
        chips = []
        if star:
            chips.append(chip(f"⭐추천 {j.get('score','')}점", "#fbf1da", GOLD))
        if dday:
            chips.append(chip(dday, "#fde8e4", "#c0392b"))
        for key in ("emp", "location", "edu", "career", "headcount"):
            v = (j.get(key) or "").strip()
            if v:
                chips.append(chip(v))
        if (j.get("salary") or "").strip():
            chips.append(chip("연봉공개", "#e6f0e2", "#3b7a2e"))
        period = esc(j.get("period", ""))
        reasons = j.get("reasons") or []
        reason_html = ""
        if reasons:
            reason_html = (f'<div style="color:{SUB};font-size:12px;margin-top:6px;">'
                           f'· {esc("  ·  ".join(reasons))}</div>')
        title_html = (f'<a href="{esc(url)}" style="color:{INK};text-decoration:none;" '
                      f'target="_blank">{title}</a>') if url else title
        link_btn = (f'<a href="{esc(url)}" target="_blank" '
                    f'style="color:{GOLD};font-size:12px;text-decoration:none;'
                    f'border:1px solid {LINE};padding:4px 10px;border-radius:8px;'
                    f'white-space:nowrap;">원문 보기 →</a>') if url else ""
        return f"""
        <tr><td style="padding:0 0 12px 0;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
                 style="background:{CARD};border:1px solid {LINE};border-radius:12px;">
            <tr><td style="padding:14px 16px;">
              <div style="font-size:12px;color:{SUB};margin-bottom:4px;">{org}</div>
              <div style="font-size:16px;font-weight:700;color:{INK};line-height:1.35;">{title_html}</div>
              <div style="margin-top:8px;">{''.join(chips)}</div>
              <div style="color:{SUB};font-size:12px;margin-top:6px;">접수: {period}</div>
              {reason_html}
              <div style="margin-top:10px;">{link_btn}</div>
            </td></tr>
          </table>
        </td></tr>"""

    rec_section = ""
    if recommended:
        rec_cards = "".join(card(j, star=True) for j in recommended)
        rec_section = f"""
        <tr><td style="padding:6px 0 4px 0;font-size:14px;font-weight:700;color:{GOLD};">
          ⭐ 추천 공고 ({len(recommended)})</td></tr>
        <tr><td><table role="presentation" width="100%" cellpadding="0" cellspacing="0">{rec_cards}</table></td></tr>"""

    rest = [j for j in jobs_sorted if j.get("score", 0) < 48]
    rest_cards = "".join(card(j) for j in rest)
    rest_section = f"""
        <tr><td style="padding:14px 0 4px 0;font-size:14px;font-weight:700;color:{INK};">
          전체 공고 ({len(rest)})</td></tr>
        <tr><td><table role="presentation" width="100%" cellpadding="0" cellspacing="0">{rest_cards}</table></td></tr>"""

    return f"""<!doctype html><html><body style="margin:0;padding:0;background:{BEIGE};">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{BEIGE};">
    <tr><td align="center" style="padding:24px 12px;">
      <table role="presentation" width="640" cellpadding="0" cellspacing="0"
             style="max-width:640px;width:100%;font-family:'Malgun Gothic','Apple SD Gothic Neo',Arial,sans-serif;">
        <tr><td style="padding:0 0 4px 0;">
          <div style="font-size:20px;font-weight:800;color:{INK};">📚 공공·연구기관 석사급 채용보드</div>
          <div style="color:{SUB};font-size:13px;margin-top:4px;">
            총 <b style="color:{INK};">{count}</b>건 · 기관 {companies}개 · ⭐추천 {rec_n}건 &nbsp;|&nbsp; 갱신: {esc(updated)}</div>
          <div style="height:1px;background:{LINE};margin:14px 0;"></div>
        </td></tr>
        {rec_section}
        {rest_section}
        <tr><td style="padding:18px 0 0 0;color:{SUB};font-size:11px;line-height:1.6;">
          ⚠️ 점수·연봉·자격은 자동 추정치입니다. 지원 전 반드시 원문 공고를 확인하세요.<br>
          이 메일은 로컬 작업 스케줄러(매일 08:00)가 자동 발송했습니다.
        </td></tr>
      </table>
    </td></tr></table></body></html>"""


def build_link_html(data, url, password):
    """링크 + 오늘의 비밀번호 안내 메일 (전체 공고 내용은 싣지 않음 → 링크로만 열람)."""
    updated = data.get("updatedAtKr") or data.get("updatedAt") or ""
    count = data.get("count", len(data.get("jobs", [])))
    rec_n = data.get("recommended", "")
    BEIGE = "#f7f3ea"; INK = "#2b2622"; SUB = "#6f655a"; LINE = "#e4dccb"
    GREEN = "#1f6f5c"; CARD = "#ffffff"
    return f"""<!doctype html><html><body style="margin:0;padding:0;background:{BEIGE};">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{BEIGE};">
    <tr><td align="center" style="padding:28px 12px;">
      <table role="presentation" width="480" cellpadding="0" cellspacing="0"
             style="max-width:480px;width:100%;font-family:'Malgun Gothic','Apple SD Gothic Neo',Arial,sans-serif;
             background:{CARD};border:1px solid {LINE};border-radius:16px;">
        <tr><td style="padding:30px 28px 24px;text-align:center;">
          <div style="font-size:34px;line-height:1;">🔒📚</div>
          <div style="font-size:20px;font-weight:800;color:{INK};margin-top:10px;">오늘의 채용보드</div>
          <div style="color:{SUB};font-size:13px;margin-top:6px;">
            총 <b style="color:{INK};">{count}</b>건 · ⭐추천 {rec_n}건 · 갱신 {esc(updated)}</div>

          <a href="{esc(url)}" target="_blank"
             style="display:inline-block;margin:22px 0 18px;padding:13px 26px;background:{GREEN};
             color:#fff;font-size:15px;font-weight:700;text-decoration:none;border-radius:12px;">
             채용보드 열기 →</a>

          <div style="background:#f3efe4;border:1px solid {LINE};border-radius:12px;padding:14px 16px;margin-top:6px;">
            <div style="color:{SUB};font-size:12px;margin-bottom:6px;">오늘의 비밀번호 (매일 바뀝니다)</div>
            <div style="font-size:22px;font-weight:800;letter-spacing:3px;color:{INK};
                 font-family:Consolas,Menlo,monospace;">{esc(password)}</div>
          </div>

          <div style="color:{SUB};font-size:11px;line-height:1.6;margin-top:18px;text-align:left;">
            · 링크를 열고 위 비밀번호를 입력하면 오늘의 공고를 볼 수 있습니다.<br>
            · 이 메일을 받은 사람만 접속할 수 있도록 데이터는 매일 새 비밀번호로 암호화됩니다.<br>
            · 지원 전 반드시 원문 공고에서 자격·연봉·접수기간을 확인하세요.
          </div>
        </td></tr>
      </table>
    </td></tr></table></body></html>"""


def send(cfg, subject, html):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f'{cfg["from_name"]} <{cfg["user"]}>'
    msg["To"] = cfg["to"]
    msg.set_content("이 메일은 HTML 형식입니다. HTML을 지원하는 클라이언트에서 확인하세요.")
    msg.add_alternative(html, subtype="html")
    ctx = ssl.create_default_context()
    with smtplib.SMTP(cfg["smtp_host"], cfg["smtp_port"], timeout=30) as s:
        s.starttls(context=ctx)
        s.login(cfg["user"], cfg["password"])
        s.send_message(msg)


def main():
    preview = "--preview" in sys.argv
    link_mode = "--link" in sys.argv
    if not os.path.exists(JOBS):
        print(f"[오류] {JOBS} 가 없습니다. 먼저 scrape.py 를 실행하세요.")
        sys.exit(1)
    with open(JOBS, encoding="utf-8") as f:
        data = json.load(f)

    count = data.get("count", len(data.get("jobs", [])))
    rec_n = data.get("recommended", "")
    today = datetime.now().strftime("%m/%d")

    cfg = load_config()

    if link_mode:
        url = cfg.get("site_url", "")
        password = os.environ.get("DAILY_KEY", "")
        if not url or not password:
            print("[오류] --link 에는 SITE_URL 과 DAILY_KEY(환경변수)가 필요합니다.")
            sys.exit(3)
        html = build_link_html(data, url, password)
        subject = f"[채용보드] {today} — 링크와 오늘의 비밀번호"
        if preview:
            with open(PREVIEW, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"[미리보기] 발송 없이 저장: {PREVIEW}")
            return
        if not cfg["user"] or not cfg["password"]:
            print("[오류] 발신 계정/앱 비밀번호가 없습니다. email_config.json 또는 환경변수를 설정하세요.")
            sys.exit(2)
        send(cfg, subject, html)
        print(f"[발송 완료/링크] → {cfg['to']}  ({subject})")
        return

    # 기본: 전체 공고 다이제스트
    html = build_html(data)
    subject = f"[채용보드] {today} 자동갱신 — 총 {count}건·추천 {rec_n}건"
    if preview:
        with open(PREVIEW, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"[미리보기] 발송 없이 저장: {PREVIEW}")
        return
    if not cfg["user"] or not cfg["password"]:
        print("[오류] 발신 계정/앱 비밀번호가 없습니다. email_config.json 또는 환경변수를 설정하세요.")
        sys.exit(2)
    send(cfg, subject, html)
    print(f"[발송 완료] → {cfg['to']}  ({subject})")


if __name__ == "__main__":
    main()
