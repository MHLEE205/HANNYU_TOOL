# ✦ Powered by LEENAI Automation System — v0.3.65 (R12Y Part 1 · 구멍 6 · 형님 #354) 枠外 (A) / 枠未定 (B) 화면 시험 (가명 fixtures · 실제 호출 0)
"""엔진 engine/output/waku.py row_ab 로 가명 jikkyou 의 칸 없는 줄에 waku_ab 를 붙여 로컬 미리보기로 연다.
확인: 줄 표시 「COMPASS 枠外」 (A) / 「枠未定」 (B) · 머리줄 「枠外 n」 / 「枠未定 m」 = 엔진 ab_split 수 · 범례 · 통관 버튼 이유 · waku_ab 없는 엔진 = 예전 그대로.
사용: python tests/test_waku_ab.py [--engine C:\\LEENAI_C01_V2\\engine]"""
import argparse
import json
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

TOOL = Path(__file__).resolve().parent.parent
RES = {"ok": 0, "ng": 0, "console_errors": []}


def ok(name, cond, got=None):
    RES["ok" if cond else "ng"] += 1
    print(("OK  " if cond else "NG  ") + name + ("" if cond else f" — {got!r}"[:400]))


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def serve(root, port, tmp):
    return subprocess.Popen([sys.executable, str(TOOL / "tools" / "serve_local.py"), "--root", str(root), "--actions", str(tmp / "la"),
                             "--port", str(port), "--today", "2026-11-08"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def open_page(br, port):
    page = br.new_context(viewport={"width": 1600, "height": 1000}).new_page()
    page.on("console", lambda m: RES["console_errors"].append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: RES["console_errors"].append(f"pageerror {e}"))
    for _ in range(50):
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
            break
        except OSError:
            time.sleep(0.1)
    page.goto(f"http://127.0.0.1:{port}/")
    page.wait_for_selector("#c01-open-server", timeout=20000)
    page.click("#c01-open-server")
    page.wait_for_selector("body[data-c01-ready='1']", timeout=20000)
    page.evaluate("localStorage.setItem('c01_ports', JSON.stringify({port: 'all', ports: []}))")
    return page


def head(page, iv):
    return page.locator(f'tbody[data-iv="{iv}"] .c01-ivhead').first.inner_text()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", default=r"C:\LEENAI_C01_V2\engine")
    a = ap.parse_args()
    sys.path.insert(0, a.engine)
    from engine.output import waku as WK   # noqa: E402  (엔진 셈 = 화면 셈 · 한 함수)
    tmp = Path(tempfile.mkdtemp(prefix="c01_waku_"))
    old, new = tmp / "old", tmp / "new"
    shutil.copytree(TOOL / "fixtures", old)
    shutil.copytree(TOOL / "fixtures", new)
    jp = new / "_data" / "jikkyou.json"
    j = json.loads(jp.read_text(encoding="utf-8"))
    per, tot = WK.compute(j["ivs"], ab=True)
    for iv in j["ivs"]:
        if iv["iv_no"] in per:
            iv["waku"] = per[iv["iv_no"]]
            for r, k in WK.row_ab(iv):
                r["waku_ab"] = k
    jp.write_text(json.dumps(j, ensure_ascii=False), encoding="utf-8")
    ab = tot["ab"]
    ok("가명 자료: (A) · (B) 둘 다 있음 (엔진 row_ab)", ab["A"]["rows"] >= 1 and ab["B"]["rows"] >= 1, ab)
    p1, p2 = free_port(), free_port()
    s1, s2 = serve(old, p1, tmp), serve(new, p2, tmp)
    try:
        with sync_playwright() as p:
            br = p.chromium.launch()
            page = open_page(br, p2)
            tool_a = tool_b = 0
            for iv in j["ivs"]:
                w = per.get(iv["iv_no"])
                if not w:
                    continue
                h = head(page, iv["iv_no"])
                ha = int(h.split("枠外 ")[1].split()[0]) if "枠外 " in h else 0
                hb = int(h.split("枠未定 ")[1].split()[0]) if "枠未定 " in h else 0
                tool_a += ha
                tool_b += hb
                ok(f"머리줄 {iv['iv_no']}: 枠外 {w['a']} / 枠未定 {w['b']} = 엔진 줄 셈", (ha, hb) == (w["a"], w["b"]), h[:160])
                rows = page.locator(f'tbody[data-iv="{iv["iv_no"]}"] tr.c01-row')
                la = rows.locator(".c01-over").count()
                lb = rows.locator(".c01-wakumi").count()
                ok(f"줄 표시 {iv['iv_no']}: 「COMPASS 枠外」 {w['a']} · 「枠未定」 {w['b']}", (la, lb) == (w["a"], w["b"]), (la, lb))
            ok("화면 합계 = 엔진 ab_split (A 줄 · B 줄) — 매일 보고 · urgent_waku 와 같은 수", (tool_a, tool_b) == (ab["A"]["rows"], ab["B"]["rows"]), (tool_a, tool_b, ab["A"]["rows"], ab["B"]["rows"]))
            ok("枠未定 줄 = 옅은 색 (tr.wakumi) · 빨간 over 아님", page.locator("tr.c01-row.wakumi").count() == ab["B"]["rows"] and page.locator("tr.c01-row.wakumi.over").count() == 0)
            lg = page.locator(".c01-legend").first.inner_text() if page.locator(".c01-legend").count() else page.content()
            ok("범례: 「COMPASS 枠外（… 業者の空き枠なし）」 · 「枠未定（空き枠あり …）」", "業者の空き枠なし" in lg and "枠未定（空き枠あり" in lg)
            t = page.locator(".c01-wakumi").first.get_attribute("title") or ""
            ok("枠未定 마우스 글 = 빈 칸 있음 · 枠変更 안내", "空き枠" in t and "枠変更" in t, t)
            shot = TOOL / "tests" / "_shots"
            shot.mkdir(exist_ok=True)
            page.screenshot(path=str(shot / "r12y_waku_ab.png"), full_page=True)
            # waku_ab 없는 엔진 (예전) = 모두 「COMPASS 枠外」
            page2 = open_page(br, p1)
            n_over = page2.locator("tr.c01-row .c01-over").count()
            ok("waku_ab 없는 엔진 = 예전 그대로 (모두 「COMPASS 枠外」 · 「枠未定」 0)", n_over == ab["A"]["rows"] + ab["B"]["rows"] and page2.locator(".c01-wakumi").count() == 0, n_over)
            errs = [e for e in RES["console_errors"] if not ("Failed to load resource" in e and "404" in e)]
            ok("콘솔 오류 0", not errs, errs[:3])
            br.close()
    finally:
        s1.terminate()
        s2.terminate()
    print(json.dumps({"checks": RES["ok"] + RES["ng"], "ng": RES["ng"]}))
    sys.exit(1 if RES["ng"] else 0)


if __name__ == "__main__":
    main()
