# -*- coding: utf-8 -*-
"""
[로컬 PC 전용] 하이브리드 일일 파이프라인:
  1) scrape.py        — 채용공고 수집 (한국 IP라 안정적)
  2) build_secure.py  — 그날의 무작위 비번으로 jobs.enc.json 암호화
  3) git push         — 암호문 커밋·푸시 → GitHub Actions가 Pages 배포
  4) email_digest --link — 링크 + 오늘의 비밀번호 메일 발송

작업 스케줄러가 매일 08시에 이 스크립트를 실행한다(run_daily.bat 경유).
모든 단계 로그는 logs/daily.log 에 누적된다.
"""
import os, sys, subprocess, datetime

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable  # 현재 인터프리터(.venv) 그대로 사용


def run(args, **kw):
    print(f"$ {' '.join(args)}")
    return subprocess.run(args, cwd=ROOT, **kw)


def main():
    # 1) 수집
    r = run([PY, "scrape.py"])
    if r.returncode != 0:
        print("[중단] 수집 실패 — 기존 데이터/배포 유지.")
        sys.exit(1)

    # 2) 암호화 (DAILY_KEY= 한 줄을 stdout 으로 받는다)
    r = run([PY, "build_secure.py"], capture_output=True, text=True, encoding="utf-8")
    sys.stderr.write(r.stderr or "")
    daily_key = ""
    for line in (r.stdout or "").splitlines():
        if line.startswith("DAILY_KEY="):
            daily_key = line.split("=", 1)[1].strip()
    if r.returncode != 0 or not daily_key:
        print("[중단] 암호화 실패.")
        sys.exit(2)

    # 3) git 커밋·푸시 (→ Pages 배포 트리거). 변경 없으면 건너뜀.
    run(["git", "add", "-f", "data/jobs.enc.json"])
    diff = run(["git", "diff", "--cached", "--quiet"])
    if diff.returncode != 0:  # 변경 있음
        stamp = datetime.datetime.now().strftime("%Y-%m-%d")
        run(["git", "commit", "-m", f"chore(data): 암호화 채용공고 갱신 {stamp}"])
        push = run(["git", "push"])
        if push.returncode != 0:
            print("[경고] git push 실패 — 사이트는 직전 배포 유지. 메일은 계속 진행.")
    else:
        print("암호문 변경 없음 — 푸시 생략.")

    # 4) 링크 + 오늘의 비밀번호 메일
    env = dict(os.environ, DAILY_KEY=daily_key)
    r = run([PY, "email_digest.py", "--link"], env=env)
    if r.returncode != 0:
        print("[중단] 메일 발송 실패.")
        sys.exit(3)

    print("완료 ✅  배포 + 메일 발송")


if __name__ == "__main__":
    main()
