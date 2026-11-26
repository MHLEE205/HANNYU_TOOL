# ✦ Powered by LEENAI Automation System — v0.3.78 (R12Y38 · 결정 #381 · #382) 시험
"""Playwright · 가명 fixtures (tools/make_test_data.py) · serve_local (127.0.0.1) — 실제 SharePoint · Graph · COMPASS 호출 0. 확인:
 P2-1 CT 누름 = 사진 탭 · 오른쪽 그 CT 搬入票 (Blob · 원래 탭이 읽음) · 탭 이름 · 주소 = 해시만
 P2-2 搬入票 여러 장 = 위 탭 · 누르면 바뀜 · 「この書類の値」
 P2-3 搬入票 없음 = 「搬入票なし」 + 다른 서류 수 안내
 P2-4 「写真のみ」 = 오른쪽 숨김 · 기억 (다시 열어도) · 되돌림
 P2-5 폭 < 1200 = 위아래 · 접기 단추
 P2-6 엔진 구분이 搬入票 아님 / 없음 = 「区分: 種類不明」 노랑
 P3-1 엔진 각도 (rotation 180) 로 처음부터 바로 · ⟳ 90 · ⟲ 90 · 180 = 화면만 · localStorage c01_rotmem (sha16#쪽) · 다시 열어도 기억
 P3-2 📄 (doc.html) 같은 기억 · 단추 3
 P3-3 確認・入力 ⟲ · 180° 단추 (⟳ 와 같은 기억)
 P3-4 localStorage 쓰기 실패해도 화면은 돎
 P1   「人の枠変更から」 표시 (엔진 slot_from_human) · hover 문구 · 사람 枠変更 줄 자신은 안 나옴 · 엔진 schema 키 대조
사용: python tests/test_r12y38.py [--engine 엔진 레포] [--shots 폴더]"""
import argparse
import json
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

TOOL = Path(__file__).resolve().parent.parent
RES = {"checks": [], "console_errors": []}
IV = "TST2611-01"


def ok(name, cond, detail=""):
    RES["checks"].append({"name": name, "ok": bool(cond), "detail": str(detail)[:300]})
    print(("OK  " if cond else "NG  ") + name + (f" — {detail}" if detail and not cond else ""), flush=True)


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def watch(page, tag):
    page.on("console", lambda m: RES["console_errors"].append(f"{tag}: {m.text}") if m.type == "error" else None)
    page.on("pageerror", lambda e: RES["console_errors"].append(f"{tag}: pageerror {e}"))


def open_local(page, url):
    page.goto(url)
    page.wait_for_selector("#c01-open-server", timeout=20000)
    page.click("#c01-open-server")
    page.wait_for_selector("body[data-c01-ready='1']", timeout=20000)


def prep(root):
    jp = root / "_data" / "jikkyou.json"
    j = json.loads(jp.read_text(encoding="utf-8"))
    iv = next(x for x in j["ivs"] if x["iv_no"] == IV)
    docs = [p.relative_to(root).as_posix() for p in sorted((root / IV / "搬入票").glob("*.svg"))]
    r0, r1, r2, r3 = iv["rows"][:4]
    # r0: 搬入票 2 (엔진 각도 180 · 그리고 0) + EIR 1
    r0["docs"] = [{"path": docs[0], "name": "搬入票_A.svg", "page": None, "sha16": "a" * 16, "fields": ["n_w", "seal"], "doc_type": "hannyuhyo", "rotation": 180},
                  {"path": docs[1], "name": "搬入票_B.svg", "page": None, "sha16": "b" * 16, "fields": ["t_w"], "doc_type": "hannyuhyo"},
                  {"path": docs[2], "name": "EIR_C.svg", "page": None, "sha16": "c" * 16, "fields": ["t_w"], "doc_type": "eir"}]
    # r1: EIR 만 → 搬入票なし
    r1["docs"] = [{"path": docs[2], "name": "EIR_C.svg", "page": None, "sha16": "c" * 16, "fields": ["t_w"], "doc_type": "eir"}]
    # r3: 엔진 구분 없음 (doc_type 없음 · 파일 이름으로 搬入票) → 種類不明
    r3["docs"] = [{"path": docs[3], "name": "scan_0001.svg", "page": None, "sha16": "d" * 16, "fields": ["ct"]}]
    # P1: r3 = 사람 枠変更 에서 이어진 줄 · r2 = 사람 枠変更 줄 (slot_change) + slot_from_human (자기 줄은 안 나와야 함)
    r3["slot_from_human"] = {"by": "staff1@example.invalid", "ct": r0["ct"], "at": "2026-11-24T09:57:44+09:00"}
    r2["slot_change"] = {"action_id": "a-sc-1", "by": "staff1@example.invalid", "at": "2026-11-24T09:57:44+09:00", "before": None, "after": r2.get("slot_guid"), "swap_ct": None}
    r2["slot_from_human"] = {"by": "staff1@example.invalid", "ct": r0["ct"], "at": "2026-11-24T09:57:44+09:00"}
    jp.write_text(json.dumps(j, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return r0, r1, r2, r3


def open_photo_tab(page, ctx, ct):
    btn = page.locator(f"tbody[data-iv='{IV}'] tr.c01-row:has-text('{ct}') .c01-ctlink").first
    with ctx.expect_page(timeout=10000) as pi:
        btn.click()
    tab = pi.value
    watch(tab, "PHOTO")
    tab.wait_for_selector(".c01-pv-th", timeout=10000)
    return tab


def doc_rot(tab):
    tab.wait_for_function("() => { const i = document.querySelector('#pv-docstage .c01-sd-img'); return i && (i.tagName === 'CANVAS' || (i.complete && i.naturalWidth > 0)); }", timeout=10000)
    return tab.evaluate("document.querySelector('#pv-docstage .c01-sd-img').getAttribute('data-rot')")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", default=r"C:\LEENAI_C01_V2\engine")
    ap.add_argument("--shots")
    a = ap.parse_args()
    if not (TOOL / "fixtures" / "_data" / "jikkyou.json").is_file():
        sys.exit("fixtures/_data 없음 — 먼저 python tools/make_test_data.py")
    shots = Path(a.shots) if a.shots else Path(tempfile.mkdtemp(prefix="c01_r12y38_shots_"))
    shots.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="c01_r12y38_"))
    root = tmp / "data"
    shutil.copytree(TOOL / "fixtures", root)
    r0, r1, r2, r3 = prep(root)
    # 엔진 schema 대조 (받는 쪽 키)
    sp = Path(a.engine) / "engine" / "output" / "schema" / "jikkyou.schema.json"
    st = sp.read_text(encoding="utf-8") if sp.is_file() else ""
    ok("P1 엔진 jikkyou.schema 에 slot_from_human {by · ct · at} (TOOL 이 읽는 키)", '"slot_from_human"' in st and all(f'"{k}"' in st for k in ("by", "ct", "at")), sp)
    app = (TOOL / "js" / "app.js").read_text(encoding="utf-8")
    ok("P1 TOOL 이 읽는 키 = sfh.by · sfh.ct · sfh.at", all(("sfh." + k) in app for k in ("by", "ct", "at")))
    port = free_port()
    srv = subprocess.Popen([sys.executable, str(TOOL / "tools" / "serve_local.py"), "--root", str(root), "--port", str(port), "--today", "2026-11-08"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    url = f"http://127.0.0.1:{port}/"
    for _ in range(50):
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
            break
        except OSError:
            time.sleep(0.1)
    try:
        with sync_playwright() as p:
            br = p.chromium.launch()
            ctx = br.new_context(viewport={"width": 1440, "height": 1000})
            page = ctx.new_page()
            watch(page, "A")
            open_local(page, url)
            page.click("[data-port='all']") if page.locator("[data-port='all']").count() else None
            page.wait_for_timeout(300)
            ok("판 표시 0.3.77", page.title().endswith("v0.3.84"), page.title())

            # ── P1 표시 ──
            b3 = page.locator(f"tbody[data-iv='{IV}'] tr.c01-row:has-text('{r3['ct']}') [data-info='slot_from_human']")
            t3 = b3.get_attribute("title") if b3.count() else ""
            ok("P1 「人の枠変更から」 표시 + hover 「… が {CT} の枠を変更 → 残りの枠が一つに決まりました」",
               b3.count() == 1 and b3.inner_text() == "人の枠変更から" and r0["ct"] in t3 and "の枠を変更 → 残りの枠が一つに決まりました" in t3, t3)
            b2 = page.locator(f"tbody[data-iv='{IV}'] tr.c01-row:has-text('{r2['ct']}') [data-info='slot_from_human']")
            b2s = page.locator(f"tbody[data-iv='{IV}'] tr.c01-row:has-text('{r2['ct']}') [data-info='slot_change']")
            ok("P1 사람 枠変更 줄 자신 = 「⇄ 枠変更」 만 (「人の枠変更から」 없음)", b2.count() == 0 and b2s.count() == 1, [b2.count(), b2s.count()])
            nb = page.locator(f"tbody[data-iv='{IV}'] tr.c01-row:has-text('{r1['ct']}') [data-info='slot_from_human']")
            ok("P1 키 없는 줄 = 표시 없음", nb.count() == 0)

            # ── P2 · P3 사진 + 搬入票 ──
            tab = open_photo_tab(page, ctx, r0["ct"])
            ok("P2-1 사진 탭 주소 = 해시만 (CT 없음)", re.search(r"/photo\.html\?k=[0-9a-f]{8}$", tab.url) and r0["ct"] not in tab.url, tab.url)
            tab.wait_for_selector("#pv-doc:not([hidden]) .c01-pv-doch", timeout=10000)
            lay = tab.evaluate("""() => { const m = document.querySelector('#pv-main').getBoundingClientRect(), d = document.querySelector('#pv-doc').getBoundingClientRect();
                return {mr: m.right, dl: d.left, mt: m.top, dt: d.top, dw: d.width}; }""")
            ok("P2-1 넓은 화면 = 왼쪽 사진 · 오른쪽 搬入票 (나란히)", lay["dl"] >= lay["mr"] - 2 and abs(lay["dt"] - lay["mt"]) < 40 and lay["dw"] > 300, lay)
            r = doc_rot(tab)
            src = tab.evaluate("document.querySelector('#pv-docstage .c01-sd-img').src.slice(0,5)")
            ok("P2-1 오른쪽 = 그 CT 搬入票 (Blob · 원래 탭에서 받음 · 새 탭 로그인 0)", src == "blob:" and tab.evaluate("typeof window.LEENAI") == "undefined", src)
            ok("P3-1 엔진 각도 180 = 처음부터 돌려 보임 (data-rot 180)", r == "180", r)
            tabs = tab.eval_on_selector_all(".c01-pv-doctabs [data-dgo]", "els => els.map(e => e.textContent)")
            ok("P2-2 搬入票 2장 = 위 탭 2 (EIR 은 오른쪽에 안 나옴)", tabs == ["1. 搬入票", "2. 搬入票"], tabs)
            ok("P2-2 「この書類の値」 = 正味重量・シール番号", "この書類の値" in tab.locator(".c01-pv-docvals").inner_text(), tab.locator(".c01-pv-docvals").inner_text())
            tab.screenshot(path=str(shots / "r12y38_photo_doc.png"))
            # 회전
            tab.click("#pv-rot [data-rot='90']")
            r_a = doc_rot(tab)
            mem = tab.evaluate("JSON.parse(localStorage.getItem('c01_rotmem') || '{}')")
            ok("P3-1 ⟳ 90° = 270 (엔진 180 + 사람 90) · 기억 = sha16#1: 90", r_a == "270" and mem.get("a" * 16 + "#1") == 90, [r_a, mem])
            tab.click("#pv-rot [data-rot='-90']")
            tab.click("#pv-rot [data-rot='-90']")
            r_b = doc_rot(tab)
            mem = tab.evaluate("JSON.parse(localStorage.getItem('c01_rotmem') || '{}')")
            ok("P3-1 ⟲ 90° 두 번 = 90 · 기억 270", r_b == "90" and mem.get("a" * 16 + "#1") == 270, [r_b, mem])
            tab.click("#pv-rot [data-rot='180']")
            r_c = doc_rot(tab)
            ok("P3-1 180° = 270 (엔진 180 + 사람 90)", r_c == "270", r_c)
            # 다른 탭 (搬入票 B) → 각도 0 · 다시 A → 기억
            tab.click(".c01-pv-doctabs [data-dgo='1']")
            r_d = doc_rot(tab)
            tab.click(".c01-pv-doctabs [data-dgo='0']")
            r_e = doc_rot(tab)
            ok("P2-2 탭 바꿈 = 다른 搬入票 (각도 0) · 돌아오면 기억 각도", r_d == "0" and r_e == "270", [r_d, r_e])
            tab.screenshot(path=str(shots / "r12y38_photo_doc_rot.png"))
            # 원본은 그대로 (사본 파일 내용 바뀜 0)
            ok("P3-1 원본 파일 그대로 (화면만)", (root / r0["docs"][0]["path"]).read_bytes() == (TOOL / "fixtures" / r0["docs"][0]["path"]).read_bytes())
            # 사진 쪽은 그대로 동작
            tab.keyboard.press("ArrowRight")
            ok("P2-1 사진 ← → 그대로", tab.locator("#pv-pos").inner_text().startswith("2 / "), tab.locator("#pv-pos").inner_text())
            # 写真のみ
            tab.click("#pv-only")
            hid = tab.evaluate("document.querySelector('#pv-doc').hidden")
            ok("P2-4 「写真のみ」 = 오른쪽 숨김 · 단추 = 「写真 + 搬入票」 · 기억", hid and tab.locator("#pv-only").inner_text() == "写真 + 搬入票"
               and tab.evaluate("localStorage.getItem('c01_pv_photo_only')") == "1", hid)
            tab.reload()
            tab.wait_for_selector(".c01-pv-th", timeout=10000)
            tab.wait_for_timeout(300)
            ok("P2-4 다시 열어도 写真のみ", tab.evaluate("document.querySelector('#pv-doc').hidden") is True)
            tab.click("#pv-only")
            tab.wait_for_selector("#pv-doc:not([hidden]) .c01-pv-doch", timeout=10000)
            ok("P3-1 다시 열어도 각도 기억 (270)", doc_rot(tab) == "270")
            # 좁은 화면
            tab.set_viewport_size({"width": 1000, "height": 900})
            tab.wait_for_timeout(300)
            lay2 = tab.evaluate("""() => { const m = document.querySelector('#pv-main').getBoundingClientRect(), d = document.querySelector('#pv-doc').getBoundingClientRect();
                return {mb: m.bottom, dt: d.top, dir: getComputedStyle(document.querySelector('#pv-split')).flexDirection}; }""")
            ok("P2-5 폭 1000 = 위아래 (column · 搬入票 = 사진 아래)", lay2["dir"] == "column" and lay2["dt"] >= lay2["mb"] - 2, lay2)
            tab.click("#pv-fold")
            fold = tab.evaluate("document.querySelector('#pv-docstage') === null && document.querySelector('#pv-doc').classList.contains('fold')")
            ok("P2-5 접기 단추 = 搬入票 접힘 · 다시 누르면 펼침", fold and (tab.click("#pv-fold") or True) and tab.locator("#pv-docstage").count() == 1, fold)
            tab.screenshot(path=str(shots / "r12y38_photo_doc_narrow.png"))
            tab.close()
            # 搬入票なし
            tab = open_photo_tab(page, ctx, r1["ct"])
            tab.wait_for_selector("#pv-docnone", timeout=10000)
            tx = tab.locator("#pv-docnone").inner_text()
            ok("P2-3 搬入票 없음 = 「搬入票なし」 + 「ほかの書類 1 件は 実況表 の 📄」", tx.startswith("搬入票なし") and "ほかの書類 1 件" in tx, tx)
            tab.close()
            # 種類不明
            tab = open_photo_tab(page, ctx, r3["ct"])
            tab.wait_for_selector("#pv-doctype", timeout=10000)
            dt = tab.locator("#pv-doctype")
            ok("P2-6 엔진 구분 없음 = 「区分: 種類不明」 노랑 (그대로 보임)", dt.inner_text() == "区分: 種類不明" and "odd" in (dt.get_attribute("class") or ""), dt.inner_text())
            # localStorage 실패
            tab.evaluate("() => { Storage.prototype.setItem = function () { throw new Error('quota'); }; return 1; }")
            r0_ = doc_rot(tab)
            tab.click("#pv-rot [data-rot='90']")
            r1_ = doc_rot(tab)
            ok("P3-4 기억 저장 실패해도 화면은 돎 (0 → 90)", r0_ == "0" and r1_ == "90", [r0_, r1_])
            tab.close()

            # ── P3-2 📄 doc.html ──
            page.reload()
            page.wait_for_selector("#c01-open-server", timeout=20000)
            page.click("#c01-open-server")
            page.wait_for_selector("body[data-c01-ready='1']", timeout=20000)
            db = page.locator(f"tbody[data-iv='{IV}'] tr.c01-row:has-text('{r0['ct']}') .c01-docbtn").first
            with ctx.expect_page(timeout=10000) as pi:
                db.click()
            dtab = pi.value
            watch(dtab, "DOC")
            dtab.wait_for_selector("#dv-rot", timeout=10000)
            dtab.wait_for_function("() => { const i = document.querySelector('#dv-stage .c01-sd-img'); return i && i.complete && i.naturalWidth > 0; }", timeout=10000)
            g = lambda: dtab.evaluate("document.querySelector('#dv-stage .c01-sd-img').getAttribute('data-rot')")   # noqa: E731
            v0 = g()
            ok("P3-2 📄 = 회전 단추 3 (⟲ 90° · ⟳ 90° · 180°) · 사진 탭과 같은 기억 (270)", dtab.locator("#dv-rot [data-rot]").count() == 3 and v0 == "270", v0)
            dtab.click("#dv-rot [data-rot='-90']")
            dtab.wait_for_timeout(200)
            v1 = g()
            ok("P3-2 📄 ⟲ 90° = 180 · 기억 0 (지움)", v1 == "180" and "a" * 16 + "#1" not in dtab.evaluate("JSON.parse(localStorage.getItem('c01_rotmem') || '{}')"), v1)
            dtab.screenshot(path=str(shots / "r12y38_doc_tab.png"))
            dtab.close()

            # ── P3-3 確認・入力 ──
            page.evaluate("C01.state.view = 'input'; C01.app.render()")
            page.wait_for_timeout(300)
            items = page.locator(".c01-item")
            hit = False
            for i in range(min(items.count(), 12)):
                items.nth(i).click()
                page.wait_for_timeout(200)
                if page.locator("#rot").count():
                    hit = True
                    break
            if hit:
                r_before = page.evaluate("C01.state.rot")
                page.click("#rot-180")
                r_after = page.evaluate("C01.state.rot")
                page.click("#rot-l")
                r_after2 = page.evaluate("C01.state.rot")
                ok("P3-3 確認・入力 ⟲ · ⟳ · 180° 단추 (180° = +180 · ⟲ = −90)", page.locator("#rot-l").count() == 1 and page.locator("#rot-180").count() == 1
                   and r_after == (r_before + 180) % 360 and r_after2 == (r_after + 270) % 360, [r_before, r_after, r_after2])
                page.screenshot(path=str(shots / "r12y38_input_rot.png"))
            else:
                ok("P3-3 確認・入力 원본 서류가 있는 카드", False, "카드 없음")
            ctx.close()
            br.close()
    finally:
        srv.terminate()
    errs = [e for e in RES["console_errors"] if "favicon" not in e]
    ok("콘솔 오류 0", not errs, errs[:5])
    n_ok = sum(1 for c in RES["checks"] if c["ok"])
    print(json.dumps({"ok": n_ok, "total": len(RES["checks"]), "shots": str(shots)}, ensure_ascii=False))
    sys.exit(0 if n_ok == len(RES["checks"]) else 1)


if __name__ == "__main__":
    main()
