# ✦ Powered by LEENAI Automation System — C-01 搬入票 TOOL 시험 데이터 다시 만들기 (레포에 넣지 않는 가명 데이터)
r"""공개 레포에 넣지 않는 가명 시험 데이터 2가지를 같은 결과로 다시 만든다 (시험 전에 1번 실행).
  ① fixtures/_data/ · fixtures/_masters · 사진·서류 SVG  ← tools/make_fixtures.py (같은 --today · 같은 엔진이면 바이트 같음)
  ② tests/compass_cases.json                            ← 엔진 tests/make_compass_cases.py 의 사례 (CASES · CASES_V058) 를
                                                           엔진 Python 규칙 (engine/compass_input/rules.py) 으로 계산
엔진 폴더는 읽기만 한다 (import 만 · 엔진 쪽 파일을 쓰지 않음 · .pyc 도 만들지 않음).
사용: python tools/make_test_data.py [--engine C:\LEENAI_C01_V2\engine_r68] [--today 2026-11-08] [--check]
      --check = 만들지 않고 지금 파일이 다시 만든 것과 같은지만 확인 (다르면 종료 코드 1)"""
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
TOOL = Path(__file__).resolve().parent.parent
NOTE = ("가명 — Python engine/compass_input/rules.py 결과 (expected). TOOL js/compass.js 가 같아야 함 · "
        "cases_v058 = follow_same_cond_slot (input.opts)")


def compass_cases_text(engine):
    sys.path.insert(0, str(engine))
    sys.path.insert(0, str(engine / "tests"))
    import make_compass_cases as M  # noqa: E402  (엔진 사례 정의 · 엔진 규칙 그대로)
    return json.dumps({"schema_version": 1, "note": NOTE, "cases": M.build(), "cases_v058": M.build(M.CASES_V058)},
                      ensure_ascii=False, indent=1) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", default=r"C:\LEENAI_C01_V2\engine_r68")
    ap.add_argument("--today", default="2026-11-08")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    engine = Path(a.engine)
    if not (engine / "tests" / "make_compass_cases.py").is_file():
        sys.exit(f"엔진 폴더에 tests/make_compass_cases.py 가 없음: {engine}")
    text = compass_cases_text(engine)
    cases = TOOL / "tests" / "compass_cases.json"
    env_cmd = [sys.executable, "-B", str(TOOL / "tools" / "make_fixtures.py"), "--today", a.today, "--engine", str(engine)]
    if a.check:
        bad = []
        if not cases.is_file() or cases.read_text(encoding="utf-8") != text:
            bad.append("tests/compass_cases.json")
        with tempfile.TemporaryDirectory(prefix="c01fx_") as td:
            subprocess.run(env_cmd + ["--out", td], check=True, capture_output=True)
            base = TOOL / "fixtures"
            for p in sorted(Path(td).rglob("*")):
                if p.is_file():
                    rel = p.relative_to(td)
                    q = base / rel
                    if not q.is_file() or q.read_bytes() != p.read_bytes():
                        bad.append("fixtures/" + rel.as_posix())
        print(json.dumps({"same": not bad, "different": bad[:20], "different_n": len(bad)}, ensure_ascii=False))
        return 1 if bad else 0
    cases.write_text(text, encoding="utf-8")   # 줄 끝 = make_fixtures 와 같음 (OS 기본 · git 은 LF 로 저장)
    r = subprocess.run(env_cmd + ["--out", str(TOOL / "fixtures")], check=True, capture_output=True, text=True, encoding="utf-8")
    print(r.stdout.strip())
    print(json.dumps({"compass_cases": str(cases.relative_to(TOOL).as_posix()), "bytes": len(text.encode("utf-8"))}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
