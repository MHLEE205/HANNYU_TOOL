# ✦ Powered by LEENAI Automation System — v0.3.88 (R12Y67 · #411) 実況表 IV 見出し 「輸出許可書」 표시
"""Playwright · 가명 fixtures · serve_local (실제 메일 · SharePoint · COMPASS 호출 0). 확인:
 S1 ✓ 許可 MM/DD · 変更 MM/DD (초록 · 엔진 iv.permit) → 누르면 창 (受信 · 申告番号 · 許可年月日 · 変更通知) → 「開く」 = 새 탭 (_通関書類 사본)
 S2 許可書 確認 (주황 · need_human 만 — zip 비밀번호)   S3 許可待ち (회색 · 送付済 · 허가서 없음)   S4 許可なし (빨강 · CY CUT 지남 — 実況表 는 CUT 지난 IV 를 숨기므로 함수 + 그린 표시만)
 S5 L インボイス = 표시 없음 · 送付 전 = 표시 없음 · 필터 「許可待ち」 「許可書 確認」 (수 · 고르면 그 IV 만)
 S6 엔진 meta.permit 없음 = 표시 · 필터 0 (켜기 전 · 「許可なし」 잘못 빨강 0)   콘솔 오류 0
사용: python tests/test_permit_r12y67.py [--shots 폴더]"""
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_graph as TGR   # noqa: E402

TOOL = Path(__file__).resolve().parent.parent
RES = {"checks": [], "console_errors": []}
A, B, C, D = "TST2611-01", "TST2611-02", "TST2611-03", "TST2611-04"
L = "LTST2611-09"                     # 가명 L インボイス
DECL = "100 2000 3000"                # 가명


def ok(name, cond, detail=""):
    RES["checks"].append({"name": name, "ok": bool(cond), "detail": str(detail)[:300]})
    print(("OK  " if cond else "NG  ") + name + (f" — {detail}" if detail and not cond else ""), flush=True)


def prep(root, meta_on=True):
    jp = root / "_data" / "jikkyou.json"
    jd = json.loads(jp.read_text(encoding="utf-8"))
    by = {x["iv_no"]: x for x in jd["ivs"]}
    sent = [{"at": "2026-11-06T10:00:00+09:00", "from": "staff_a@example.invalid", "test": False}]
    by[A]["customs_mail"] = sent
    by[A]["permit"] = {"received_at": "2026-11-07T11:20:00+09:00", "kind": "PERMIT", "how": "text", "n": 1, "decl_no": DECL, "permit_date": "2026-11-07",
                       "change": [{"received_at": "2026-11-08T09:00:00+09:00", "how": "name"}], "need_human": [],
                       "files": [{"kind": "PERMIT", "name": f"{A}_ED.pdf", "path": f"{A}/_通関書類/{A}_ED.pdf"},
                                 {"kind": "CHANGE", "name": f"{A}_許可内容変更通知.pdf", "path": f"{A}/_通関書類/{A}_許可内容変更通知.pdf"}]}
    by[B]["customs_mail"] = sent
    by[B]["permit"] = {"received_at": None, "kind": None, "how": "human", "n": 0, "decl_no": None, "permit_date": None, "change": [],
                       "need_human": [{"why": "zip_password", "received_at": "2026-11-07T15:00:00+09:00", "kind": None}], "files": []}
    by[C]["customs_mail"] = sent
    lv = json.loads(json.dumps(by[D]))
    lv["iv_no"] = L
    for r in lv["rows"]:
        r["iv_no"] = L
    lv["customs_mail"] = sent
    jd["ivs"].append(lv)
    jp.write_text(json.dumps(jd, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    mp = root / "_data" / "meta.json"
    m = json.loads(mp.read_text(encoding="utf-8"))
    if meta_on:
        m["permit"] = {"on": True, "since": "2026-10-09"}
    else:
        m.pop("permit", None)
    mp.write_text(json.dumps(m, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    pj = root / "_data" / "photos"
    if (pj / f"{D}.json").exists():
        shutil.copy(pj / f"{D}.json", pj / f"{L}.json")
    d = root / A / "_通関書類"
    d.mkdir(parents=True, exist_ok=True)
    TGR.make_pdf(d / f"{A}_ED.pdf")
    TGR.make_pdf(d / f"{A}_許可内容変更通知.pdf")


def serve(root, port):
    p = subprocess.Popen([sys.executable, str(TOOL / "tools" / "serve_local.py"), "--root", str(root), "--port", str(port), "--today", "2026-11-08"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(50):
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
            break
        except OSError:
            time.sleep(0.1)
    return p


def open_page(br, port):
    ctx = br.new_context(viewport={"width": 1600, "height": 900})
    page = ctx.new_page()
    page.on("console", lambda m: RES["console_errors"].append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: RES["console_errors"].append(f"pageerror {e}"))
    page.on("response", lambda r: RES.setdefault("r404", []).append(r.url.split("/", 3)[-1]) if r.status == 404 else None)
    page.goto(f"http://127.0.0.1:{port}/")
    page.wait_for_selector("#c01-open-server", timeout=20000)
    page.click("#c01-open-server")
    page.wait_for_selector("body[data-c01-ready='1']", timeout=20000)
    page.wait_for_timeout(300)
    return ctx, page


def head(page, iv):
    return page.evaluate("""(iv) => { const t = document.querySelector("tbody[data-iv='" + iv + "'] .c01-ivhead"); if (!t) return null;
      return [...t.querySelectorAll('.c01-permit')].map(e => ({ t: e.textContent.trim(), c: e.className, title: e.title })); }""", iv)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shots")
    a = ap.parse_args()
    if not (TOOL / "fixtures" / "_data" / "jikkyou.json").is_file():
        sys.exit("fixtures/_data 없음 — 먼저 python tools/make_test_data.py")
    shots = Path(a.shots) if a.shots else Path(tempfile.mkdtemp(prefix="c01_r12y67_shots_"))
    shots.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="c01_r12y67_"))
    root, root2 = tmp / "on", tmp / "off"
    shutil.copytree(TOOL / "fixtures", root)
    shutil.copytree(TOOL / "fixtures", root2)
    prep(root, True)
    prep(root2, False)
    port, port2 = TGR.free_port(), TGR.free_port()
    s1, s2 = serve(root, port), serve(root2, port2)
    try:
        with sync_playwright() as p:
            br = p.chromium.launch()
            ctx, page = open_page(br, port)
            ha, hb, hc, hd, hl = head(page, A), head(page, B), head(page, C), head(page, D), head(page, L)
            ok("S1 ✓ 許可 11/07 · 変更 11/08 (초록)", ha and len(ha) == 1 and ha[0]["t"] == "✓ 許可 11/07 · 変更 11/08" and "c01-permit-ok" in ha[0]["c"] and DECL in ha[0]["title"], ha)
            ok("S2 許可書 確認 (주황 · zip 비밀번호)", hb and len(hb) == 1 and hb[0]["t"] == "許可書 確認" and "c01-permit-chk" in hb[0]["c"] and "zip" in hb[0]["title"], hb)
            ok("S3 許可待ち (회색 · 送付済)", hc and len(hc) == 1 and hc[0]["t"] == "許可待ち" and "c01-permit-wait" in hc[0]["c"], hc)
            ok("S5 送付 전 = 표시 없음", hd == [], hd)
            ok("S5 L インボイス = 표시 없음", hl == [], hl)
            st = page.evaluate("""() => { const f = C01.customs.permitState, sent = [{ at: '2026-11-01T10:00:00+09:00', from: 'x', test: false }];
              return { none: (f({ iv_no: 'TST2611-77', cy_cut: '2026-11-07', customs_mail: sent }) || {}).st,
                       noneNoSend: (f({ iv_no: 'TST2611-78', cy_cut: '2026-11-07' }) || {}).st,
                       cutToday: (f({ iv_no: 'TST2611-79', cy_cut: '2026-11-08', customs_mail: sent }) || {}).st,
                       okPast: (f({ iv_no: 'TST2611-80', cy_cut: '2026-11-01', permit: { kind: 'PERMIT', received_at: '2026-11-01T09:00:00+09:00', need_human: [], change: [] } }) || {}).st,
                       lPast: f({ iv_no: 'LTST2611-81', cy_cut: '2026-11-01' }) }; }""")
            ok("S4 許可なし = CUT 지남 · 허가서 없음 (送付 기록 없어도)", st["none"] == "none" and st["noneNoSend"] == "none", st)
            ok("S4 CUT 당일 = 許可待ち (빨강 아님)", st["cutToday"] == "wait", st)
            ok("S4 CUT 지남 + 허가서 = ✓ · L = 없음", st["okPast"] == "ok" and st["lPast"] is None, st)
            # 화면 캡처: 4가지 상태 (S4 = CUT 지난 IV 는 実況表 에 없으므로 D 머리줄에 그린 것)
            page.evaluate("""(iv) => { const h = document.querySelector("tbody[data-iv='" + iv + "'] .c01-ivhead");
              h.insertAdjacentHTML('beforeend', C01.customs.permitBadge({ iv: { iv_no: iv, cy_cut: '2026-11-07' } })); }""", D)
            hd2 = head(page, D)
            ok("S4 許可なし 표시 (빨강)", hd2 and hd2[0]["t"] == "許可なし" and "c01-permit-none" in hd2[0]["c"], hd2)
            page.locator("#jikkyou-table").screenshot(path=str(shots / "r12y67_permit_4states.png"))
            for iv, nm in ((A, "ok"), (B, "check"), (C, "wait"), (D, "none")):
                page.locator(f"tbody[data-iv='{iv}'] tr.c01-ivrow").screenshot(path=str(shots / f"r12y67_head_{nm}.png"))
            fl = page.evaluate("""() => [...document.querySelectorAll('[data-filter=pwait],[data-filter=pcheck]')].map(e => e.textContent.trim())""")
            ok("S5 필터 「許可待ち 1件」 「許可書 確認 1件」", fl == ["許可待ち 1件", "許可書 確認 1件"], fl)
            page.click("[data-filter=pwait]")
            page.wait_for_timeout(200)
            vis = page.evaluate("() => [...document.querySelectorAll('#jikkyou-table tbody[data-iv]')].map(t => t.getAttribute('data-iv'))")
            ok("S5 필터 許可待ち = 그 IV 만", vis == [C], vis)
            page.click("[data-filter=pcheck]")
            page.wait_for_timeout(200)
            vis = page.evaluate("() => [...document.querySelectorAll('#jikkyou-table tbody[data-iv]')].map(t => t.getAttribute('data-iv'))")
            ok("S5 필터 許可書 確認 = 그 IV 만", vis == [B], vis)
            page.click("[data-filter=pcheck]")
            page.wait_for_timeout(200)
            page.click(f"tbody[data-iv='{A}'] [data-permit-ok]")
            page.wait_for_selector("[data-permit-tbl]", timeout=5000)
            tbl = page.evaluate("() => [...document.querySelectorAll('[data-permit-tbl] tr')].map(r => r.textContent)")
            ok("S1 창: 受信 · 申告番号 · 許可年月日 · 見つけ方 · 変更通知",
               any(DECL in t for t in tbl) and any("許可年月日2026-11-07" in t for t in tbl) and any(t.startswith("変更通知") for t in tbl) and any("PDF の文字" in t for t in tbl), tbl)
            page.screenshot(path=str(shots / "r12y67_permit_modal.png"))
            page.evaluate("""() => { window.__opened = []; window.open = function () { const o = { opener: 1, document: { title: '', body: {} }, location: {}, close() {} };
              window.__opened.push(o); return o; }; }""")
            page.click("[data-permitopen='0']")
            page.wait_for_function("() => window.__opened.length && window.__opened[0].location.href", timeout=10000)
            u = page.evaluate("() => decodeURIComponent(window.__opened[0].location.href)")
            ok("S1 「開く」 = 새 탭 · _通関書類 의 허가서", u.endswith(f"{A}/_通関書類/{A}_ED.pdf"), u[-60:])
            ctx.close()
            ctx2, page2 = open_page(br, port2)
            n = page2.evaluate("() => document.querySelectorAll('.c01-permit, [data-filter=pwait], [data-filter=pcheck]').length")
            ok("S6 meta.permit 없음 = 표시 · 필터 0", n == 0, n)
            ctx2.close()
            br.close()
    finally:
        s1.terminate()
        s2.terminate()
    ok("콘솔 오류 0", not RES["console_errors"], [RES["console_errors"][:3], RES.get("r404")])
    print(json.dumps({"ok": sum(c["ok"] for c in RES["checks"]), "ng": sum(not c["ok"] for c in RES["checks"]), "shots": str(shots)}, ensure_ascii=False))
    sys.exit(0 if all(c["ok"] for c in RES["checks"]) else 1)


if __name__ == "__main__":
    main()
