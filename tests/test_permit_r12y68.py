# ✦ Powered by LEENAI Automation System — v0.3.89 (R12Y68 · #412 · #413 · #414) 許可 CUT 当日 · 許可書の内容 · 区分
"""Playwright · 가명 fixtures · serve_local (실제 메일 · SharePoint · COMPASS 호출 0). 확인:
 P0 CUT 当日 16:59 = 「許可待ち（本日CUT）」 橙 · 17:00 = 「許可なし」 赤 · 週末 CUT 도 같음 · 許可書 確認 + 17:00 = 赤い枠 · 送付前 = 없음 · 필터 許可待ち 에 本日CUT
 P1 許可書の内容 (meta.permit.check = shadow): 職員 = 안 보임 · 管理者 = 보임 · staff = true 면 직원 화면에도
 P2 ✓ 終結 · 許可済（区分2）— 確認 → 1 클릭 = _actions permit_ok (kubun) → ✓ 終結 · 元に戻す = undo → 다시 確認
 P3 許可書 相違 (赤) → 項目の表 (許可書 / 当社) · 表記確認 → 同じ意味（登録） = permit_ok same → ✓ 終結 · 違う = 相違
 P4 区分3 메일 (赤) · 写真未送付 (赤)   콘솔 오류 0
사용: python tests/test_permit_r12y68.py [--shots 폴더]"""
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
DECL = "100 2000 3000"                # 가명
CO = "FAKEPAPER TRADING CO., LTD."    # 가명
SENT = [{"at": "2026-11-06T10:00:00+09:00", "from": "staff_a@example.invalid", "test": False}]


def ok(name, cond, detail=""):
    RES["checks"].append({"name": name, "ok": bool(cond), "detail": str(detail)[:300]})
    print(("OK  " if cond else "NG  ") + name + (f" — {detail}" if detail and not cond else ""), flush=True)


def permit(kind="PERMIT", files=True, check=None):
    p = {"received_at": "2026-11-07T11:20:00+09:00", "kind": kind, "how": "text", "n": 1, "decl_no": DECL, "permit_date": "2026-11-07", "change": [], "need_human": [],
         "files": [{"kind": "PERMIT", "name": "x_ED.pdf", "path": "x/_通関書類/x_ED.pdf"}] if files else []}
    if check:
        p["check"] = check
    return p


def prep(root, staff=False):
    jp = root / "_data" / "jikkyou.json"
    jd = json.loads(jp.read_text(encoding="utf-8"))
    by = {x["iv_no"]: x for x in jd["ivs"]}
    for iv in (A, B, C, D):
        by[iv]["customs_mail"] = SENT
        by[iv]["cy_cut"] = "2026-11-10"
    by[A]["permit"] = permit(check={"st": "kubun", "kubun": "2", "fields": [], "main_ok": 10, "n_permit": 1, "n_change": 0})
    by[B]["permit"] = permit(check={"st": "diff", "kubun": "1", "main_ok": 9, "n_permit": 1, "n_change": 0,
                                    "fields": [{"f": "建値", "r": "相違", "p": "CFR", "o": "CIF"}]})
    by[C]["permit"] = permit(check={"st": "hyoki", "kubun": "1", "main_ok": 9, "n_permit": 1, "n_change": 0,
                                    "fields": [{"f": "仕向人", "r": "처음보는다름", "p": "FAKEPAPER TRADING SAMPLE CO LTD", "o": CO}]})
    by[D]["permit"] = {"received_at": None, "kind": None, "how": None, "n": 0, "decl_no": None, "permit_date": None, "change": [], "need_human": [], "files": [],
                       "check": {"st": "before", "kubun_mail": {"level": 3, "at": "2026-11-08T10:00:00+09:00", "photo": "missing", "photo_at": None}}}
    jp.write_text(json.dumps(jd, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    mp = root / "_data" / "meta.json"
    m = json.loads(mp.read_text(encoding="utf-8"))
    m["permit"] = {"on": True, "since": "2026-10-09", "check": "shadow", "kubun": "shadow", "staff": staff, "none_hour": "17:00"}
    mp.write_text(json.dumps(m, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for iv in (A, B, C):
        d = root / "x" / "_通関書類"
        d.mkdir(parents=True, exist_ok=True)
        TGR.make_pdf(d / "x_ED.pdf")


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


def open_page(br, port, hm="10:00"):
    ctx = br.new_context(viewport={"width": 1600, "height": 900})
    ctx.add_init_script("window.C01 = window.C01 || {}; window.__hm = '" + hm + "';")
    page = ctx.new_page()
    page.on("console", lambda m: RES["console_errors"].append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: RES["console_errors"].append(f"pageerror {e}"))
    page.goto(f"http://127.0.0.1:{port}/")
    page.wait_for_selector("#c01-open-server", timeout=20000)
    page.click("#c01-open-server")
    page.wait_for_selector("body[data-c01-ready='1']", timeout=20000)
    page.evaluate("() => { C01.PERMIT = { nowHm: function () { return window.__hm; } }; }")
    page.wait_for_timeout(300)
    return ctx, page


def set_admin(page, on):
    page.evaluate("(on) => { const S = C01.app._api().S; if (!S.me) S.me = { code: 'T1', name: 'T1', email: 'staff_a@fake' }; S.me.admin = on; C01.app.render(); }", on)
    page.wait_for_timeout(200)


def head(page, iv):
    return page.evaluate("""(iv) => { const t = document.querySelector("tbody[data-iv='" + iv + "'] .c01-ivhead"); if (!t) return null;
      return [...t.querySelectorAll('.c01-permit')].map(e => ({ t: e.textContent.trim(), c: e.className, title: e.title })); }""", iv)


def texts(h):
    return [x["t"] for x in (h or [])]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shots")
    a = ap.parse_args()
    if not (TOOL / "fixtures" / "_data" / "jikkyou.json").is_file():
        sys.exit("fixtures/_data 없음 — 먼저 python tools/make_test_data.py")
    shots = Path(a.shots) if a.shots else Path(tempfile.mkdtemp(prefix="c01_r12y68_shots_"))
    shots.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="c01_r12y68_"))
    root, root2 = tmp / "shadow", tmp / "staff"
    shutil.copytree(TOOL / "fixtures", root)
    shutil.copytree(TOOL / "fixtures", root2)
    prep(root, False)
    prep(root2, True)
    port, port2 = TGR.free_port(), TGR.free_port()
    s1, s2 = serve(root, port), serve(root2, port2)
    try:
        with sync_playwright() as p:
            br = p.chromium.launch()
            ctx, page = open_page(br, port)
            # ── P0 CUT 当日 (함수) ──
            st = page.evaluate("""() => { const f = C01.customs.permitState, sent = [{ at: '2026-11-01T10:00:00+09:00', from: 'x', test: false }], S = C01.app._api().S;
              const r = {};
              window.__hm = '16:59'; r.cut1659 = (f({ iv_no: 'TST2611-79', cy_cut: '2026-11-08', customs_mail: sent }) || {}).st;
              window.__hm = '17:00'; r.cut1700 = f({ iv_no: 'TST2611-79', cy_cut: '2026-11-08', customs_mail: sent }) || {};
              r.noSend = f({ iv_no: 'TST2611-78', cy_cut: '2026-11-08' });
              r.chk1700 = f({ iv_no: 'TST2611-77', cy_cut: '2026-11-08', customs_mail: sent, permit: { kind: null, need_human: [{ why: 'zip_password', received_at: '2026-11-08T09:00:00+09:00' }], change: [] } }) || {};
              window.__hm = '16:59'; r.chk1659 = f({ iv_no: 'TST2611-77', cy_cut: '2026-11-08', customs_mail: sent, permit: { kind: null, need_human: [{ why: 'zip_password' }], change: [] } }) || {};
              r.tomorrow = (f({ iv_no: 'TST2611-76', cy_cut: '2026-11-09', customs_mail: sent }) || {}).st;
              const t0 = S.info ? S.info.today : undefined; S.info = S.info || {}; S.info.today = '2026-11-28';      /* 土曜 */
              window.__hm = '17:30'; r.sat = (f({ iv_no: 'TST2611-75', cy_cut: '2026-11-28', customs_mail: sent }) || {}).st;
              window.__hm = '09:00'; r.sat9 = (f({ iv_no: 'TST2611-75', cy_cut: '2026-11-28', customs_mail: sent }) || {}).st;
              S.info.today = t0; window.__hm = '10:00'; return r; }""")
            ok("P0 CUT 当日 16:59 = 許可待ち（本日CUT）", st["cut1659"] == "wait_cut", st)
            ok("P0 CUT 当日 17:00 = 許可なし (today)", st["cut1700"].get("st") == "none" and st["cut1700"].get("today") is True, st)
            ok("P0 送付前 = 표시 없음 (CUT 当日 17:00 도)", st["noSend"] is None, st)
            ok("P0 許可書 確認 · 17:00 = late · 16:59 = late 아님", st["chk1700"].get("late") is True and not st["chk1659"].get("late"), st)
            ok("P0 내일 CUT = 許可待ち (회색)", st["tomorrow"] == "wait", st)
            ok("P0 週末 CUT (土) 도 같음 (09:00 本日CUT · 17:30 許可なし)", st["sat9"] == "wait_cut" and st["sat"] == "none", st)
            html = page.evaluate("""() => { window.__hm = '16:59'; const sent = [{ at: '2026-11-01T10:00:00+09:00', from: 'x', test: false }];
              const a = C01.customs.permitBadge({ iv: { iv_no: 'TST2611-79', cy_cut: '2026-11-08', customs_mail: sent } });
              window.__hm = '17:00'; const b = C01.customs.permitBadge({ iv: { iv_no: 'TST2611-79', cy_cut: '2026-11-08', customs_mail: sent } });
              const c = C01.customs.permitBadge({ iv: { iv_no: 'TST2611-77', cy_cut: '2026-11-08', customs_mail: sent, permit: { kind: null, need_human: [{ why: 'zip_password' }], change: [] } } });
              window.__hm = '10:00'; return [a, b, c]; }""")
            ok("P0 표시 글자 · 색", "許可待ち（本日CUT）" in html[0] and "c01-permit-cut" in html[0] and ">許可なし<" in html[1] and "data-permit-today" in html[1]
               and "c01-permit-late" in html[2], html)
            # 머리줄에 그려 캡처
            page.evaluate("""(iv) => { const h = document.querySelector("tbody[data-iv='" + iv + "'] .c01-ivhead"); const sent = [{ at: '2026-11-01T10:00:00+09:00', from: 'x', test: false }];
              window.__hm = '16:59'; h.insertAdjacentHTML('beforeend', C01.customs.permitBadge({ iv: { iv_no: 'TST2611-79', cy_cut: '2026-11-08', customs_mail: sent } }));
              window.__hm = '17:00'; h.insertAdjacentHTML('beforeend', C01.customs.permitBadge({ iv: { iv_no: 'TST2611-79', cy_cut: '2026-11-08', customs_mail: sent } }));
              h.insertAdjacentHTML('beforeend', C01.customs.permitBadge({ iv: { iv_no: 'TST2611-77', cy_cut: '2026-11-08', customs_mail: sent, permit: { kind: null, need_human: [{ why: 'zip_password' }], change: [] } } }));
              window.__hm = '10:00'; }""", A)
            page.locator(f"tbody[data-iv='{A}'] tr.c01-ivrow").screenshot(path=str(shots / "r12y68_cut_day.png"))
            set_admin(page, False)
            # ── P1 職員 = 안 보임 ──
            ha = head(page, A)
            ok("P1 職員 (shadow) = 内容 표시 없음", not any(t in ("✓ 終結", "許可書 相違", "表記確認") or t.startswith("許可済") or t.startswith("区分") for t in texts(ha)) and
               not page.locator("[data-permitck]").count(), texts(ha))
            set_admin(page, True)
            ha, hb, hc, hd = head(page, A), head(page, B), head(page, C), head(page, D)
            ok("P1 管理者 = 区分2 確認 (橙)", "許可済（区分2）— 確認" in texts(ha), texts(ha))
            ok("P1 管理者 = 許可書 相違 (赤)", any(x["t"] == "許可書 相違" and "c01-permit-none" in x["c"] for x in hb), hb)
            ok("P1 管理者 = 表記確認 (橙)", "表記確認" in texts(hc), texts(hc))
            ok("P4 区分3 (赤) · 区分3 の写真未送付 (赤)", any(x["t"] == "区分3" and "c01-permit-none" in x["c"] for x in hd) and "区分3 の写真未送付" in texts(hd), texts(hd))
            page.locator("#jikkyou-table").screenshot(path=str(shots / "r12y68_admin_badges.png"))
            # ── P2 区分 1 クリック ──
            page.click(f"tbody[data-iv='{A}'] [data-permit-kubun]")
            page.wait_for_selector("[data-ckkubun]", timeout=5000)
            page.screenshot(path=str(shots / "r12y68_kubun_modal.png"))
            page.click("[data-ckkubun]")
            page.wait_for_timeout(500)
            mine = page.evaluate("() => C01.app._api().S.mine.map(x => x.action).filter(a => a.action === 'permit_ok')")
            ok("P2 1 クリック = permit_ok kind kubun (iv · ct null)", len(mine) == 1 and mine[0]["value"]["kind"] == "kubun" and mine[0]["iv"] == A and mine[0]["ct"] is None, mine)
            page.evaluate("() => C01.app.closeModal ? C01.app.closeModal() : C01.app._api().closeModal()")
            page.evaluate("() => C01.app.render()")
            ha = head(page, A)
            ok("P2 → ✓ 終結 (緑)", any(x["t"] == "✓ 終結" and "c01-permit-ok" in x["c"] for x in ha), texts(ha))
            page.click(f"tbody[data-iv='{A}'] [data-permit-closed]")
            page.wait_for_selector("[data-ckundo]", timeout=5000)
            page.click("[data-ckundo]")
            page.wait_for_timeout(500)
            page.evaluate("() => C01.app._api().closeModal()")
            page.evaluate("() => C01.app.render()")
            ha = head(page, A)
            und = page.evaluate("() => C01.app._api().S.mine.map(x => x.action).filter(a => a.action === 'undo').length")
            ok("P2 元に戻す = undo → 다시 確認", und == 1 and "許可済（区分2）— 確認" in texts(ha), [und, texts(ha)])
            # ── P3 相違 표 · 表記確認 ──
            page.click(f"tbody[data-iv='{B}'] [data-permit-diff]")
            page.wait_for_selector("[data-ck-tbl]", timeout=5000)
            rows = page.evaluate("() => [...document.querySelectorAll('[data-ck-tbl] tr')].map(r => [...r.children].map(c => c.textContent.trim()))")
            ok("P3 相違 표: 建値 · CFR / CIF · 相違", any(r[:4] == ["建値", "CFR", "CIF", "相違"] for r in rows), rows)
            page.screenshot(path=str(shots / "r12y68_diff_modal.png"))
            page.evaluate("() => C01.app._api().closeModal()")
            page.click(f"tbody[data-iv='{C}'] [data-permit-hyoki]")
            page.wait_for_selector("[data-cksame]", timeout=5000)
            page.screenshot(path=str(shots / "r12y68_hyoki_modal.png"))
            page.click("[data-cksame]")
            page.wait_for_timeout(500)
            mine = page.evaluate("() => C01.app._api().S.mine.map(x => x.action).filter(a => a.action === 'permit_ok' && a.iv === '" + C + "')")
            ok("P3 同じ意味 = permit_ok same · field · 許可書 / 当社 값", len(mine) == 1 and mine[0]["value"]["kind"] == "same" and mine[0]["value"]["field"] == "仕向人"
               and mine[0]["value"]["o"] == CO, mine)
            page.evaluate("() => C01.app._api().closeModal()")
            page.evaluate("() => C01.app.render()")
            ok("P3 → ✓ 終結", "✓ 終結" in texts(head(page, C)), texts(head(page, C)))
            ctx.close()
            ctx2, page2 = open_page(br, port2)
            set_admin(page2, False)
            ok("P1 staff = true → 職員にも 表示", "許可書 相違" in texts(head(page2, B)), texts(head(page2, B)))
            ctx2.close()
            br.close()
    finally:
        s1.terminate()
        s2.terminate()
    ok("콘솔 오류 0", not RES["console_errors"], RES["console_errors"][:3])
    print(json.dumps({"ok": sum(c["ok"] for c in RES["checks"]), "ng": sum(not c["ok"] for c in RES["checks"]), "shots": str(shots)}, ensure_ascii=False))
    sys.exit(0 if all(c["ok"] for c in RES["checks"]) else 1)


if __name__ == "__main__":
    main()
