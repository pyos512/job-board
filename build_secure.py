# -*- coding: utf-8 -*-
"""
data/jobs.json 을 '그날의 비밀번호'로 암호화해서 data/jobs.enc.json 을 만든다.
- 알고리즘: PBKDF2-HMAC-SHA256(200k) 로 키 유도 → AES-256-GCM (브라우저 Web Crypto 호환)
- 비밀번호: 환경변수 DAILY_KEY 가 있으면 사용, 없으면 무작위 생성.
- 표준출력 마지막 줄에  DAILY_KEY=<비번>  을 찍어 호출측(워크플로/배치)이 받아 쓰게 한다.

배포본에는 jobs.enc.json '만' 올린다. 평문 jobs.json/jobs.js 는 올리지 않는다.
"""
import os, sys, json, base64, secrets, hashlib

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "data", "jobs.json")
OUT = os.path.join(ROOT, "data", "jobs.enc.json")
ITER = 200_000


def b64(b):
    return base64.b64encode(b).decode("ascii")


def gen_password():
    # 사람이 복사·입력하기 쉬운 무작위 비번 (혼동 문자 제외, 4자리×4그룹)
    alphabet = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # I,L,O,0,1 제외
    groups = ["".join(secrets.choice(alphabet) for _ in range(4)) for _ in range(4)]
    return "-".join(groups)


def fixed_password():
    """고정 비밀번호: 환경변수 DAILY_KEY > email_config.json 의 site_password.
    둘 다 없으면 무작위 생성(권장 안 함 — 매번 바뀜)."""
    env = os.environ.get("DAILY_KEY")
    if env:
        return env
    cfg = os.path.join(ROOT, "email_config.json")
    if os.path.exists(cfg):
        try:
            with open(cfg, encoding="utf-8") as f:
                pw = (json.load(f).get("site_password") or "").strip()
            if pw:
                return pw
        except Exception:
            pass
    return gen_password()


def main():
    if not os.path.exists(SRC):
        print(f"[오류] {SRC} 없음. 먼저 scrape.py 실행.", file=sys.stderr)
        sys.exit(1)

    password = fixed_password()
    with open(SRC, "rb") as f:
        plaintext = f.read()

    salt = secrets.token_bytes(16)
    iv = secrets.token_bytes(12)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITER, dklen=32)
    ct = AESGCM(key).encrypt(iv, plaintext, None)  # ct = 암호문 + 16바이트 GCM 태그

    blob = {
        "v": 1,
        "kdf": "PBKDF2",
        "hash": "SHA-256",
        "iter": ITER,
        "salt": b64(salt),
        "iv": b64(iv),
        "ct": b64(ct),
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(blob, f, separators=(",", ":"))

    # 사람용 안내는 stderr, 기계용 결과는 stdout 마지막 줄
    print(f"[암호화 완료] {OUT}  ({len(plaintext)} bytes → {len(ct)} bytes)", file=sys.stderr)
    print(f"DAILY_KEY={password}")


if __name__ == "__main__":
    main()
