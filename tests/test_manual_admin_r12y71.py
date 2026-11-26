# ✦ Powered by LEENAI Automation System — v0.3.90 (R12Y71) 使い方 8 章 (許可書の内容確認 · admin) = 管理者だけ
"""Playwright · 가명 fixtures · serve_local (실제 메일 · SharePoint · COMPASS 호출 0). 확인:
 M1 엔진 manual.json (--engine · m19) = 스키마 통과 · admin 장 = 8 · 8-1~8-4 · 버튼 이름 = TOOL 화면 글자
 M2 職員 = 使い方 에 8 장 없음 (목차 · 본문) · 나머지 장 수 그대로 · AI 답 참고 (manual_refs) 8-1 = 버튼 안 냄 · 3-4 = 냄
 M3 管理者 = 8 장 보임 · 목차 「8. 許可書の内容確認（管理者）」 · 검색 「表記確認」 = 8-1 · 8-2   콘솔 오류 0
사용: python tests/test_manual_admin_r12y71.py [--engine C:\\LEENAI_C01_V2\\engine] [--shots 폴더]"""
import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_graph as TGR   # noqa: E402
import test_permit_r12y68 as TP   # noqa: E402

TOOL = Path(__file__).resolve().parent.parent
RES = TP.RES


def ok(name, cond, detail=""):
    TP.ok(name, cond, detail)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", default=r"C:\LEENAI_C01_V2\engine")
    ap.add_argument("--shots")
    a = ap.parse_args()
    sys.path.insert(0, a.engine)
    from engine.ask import manual as MAN  # noqa: E402
    from engine.output import schema_check as SC  # noqa: E402
    man = {"schema_version": 1, "kind": "manual", **MAN.output()}
    adm = [s["id"] for s in man["sections"] if s.get("admin")]
    ok("M1 엔진 manual.json = 스키마 통과 · admin 장 8 · 8-1~8-4", SC.errors(man, SC.load("manual")) == [] and adm == ["8", "8-1", "8-2", "8-3", "8-4"], adm)
    src = "".join((TOOL / f).read_text(encoding="utf-8") for f in ("index.html", "js/app.js", "js/photo.js", "js/zoompan.js", "js/compass.js", "js/doc.js",
                                                                   "js/customs.js", "js/linkab.js", "js/sidedoc.js", "photo.html"))
    miss = [b for b in man["buttons"] if b not in src]
    ok("M1 버튼 이름 = TOOL 화면 글자 (8 장 포함 · 없음 0)", not miss, miss)
    shots = Path(a.shots) if a.shots else Path(tempfile.mkdtemp(prefix="c01_r12y71_shots_"))
    shots.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="c01_r12y71_"))
    root = tmp / "root"
    shutil.copytree(TOOL / "fixtures", root)
    d = root / "_data"
    (d / "manual.json").write_text(json.dumps(man, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    mp = d / "meta.json"
    m = json.loads(mp.read_text(encoding="utf-8"))
    m["manual"] = "manual.json"
    mp.write_text(json.dumps(m, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    port = TGR.free_port()
    srv = TP.serve(root, port)
    try:
        with sync_playwright() as p:
            br = p.chromium.launch()
            ctx, page = TP.open_page(br, port)
            page.evaluate("() => { C01.state.manual = null; C01.state.manMiss = 0; C01.app.tick(); }")
            page.wait_for_timeout(800)

            def open_help():
                page.evaluate("() => { var m = document.getElementById('c01-modal'); if (m) { m.hidden = true; m.innerHTML = ''; } C01.state.modal = null; C01.app.render(); }")
                page.click("#help-open")
                page.wait_for_selector(".c01-man", timeout=5000)
                page.wait_for_timeout(300)
                return page.evaluate("() => [...document.querySelectorAll('.c01-man-sec')].map(e => e.dataset.mansec)"), \
                    page.evaluate("() => [...document.querySelectorAll('.c01-man-toc a')].map(e => e.textContent.trim())")
            TP.set_admin(page, False)
            secs, toc = open_help()
            n_staff = len(man["sections"]) - len(adm)
            ok("M2 職員 = 8 장 없음 (본문 · 목차) · 나머지 " + str(n_staff) + " 장 그대로",
               not any(s in adm for s in secs) and len(secs) == n_staff and len(toc) == n_staff and not any("許可書の内容確認" in t for t in toc), (len(secs), toc[-3:]))
            refs = page.evaluate("""() => { var el = document.createElement('div'); document.body.appendChild(el);
              el.innerHTML = C01.app._api().manRefs ? C01.app._api().manRefs({ manual_refs: [{ id: '8-1', title: 'x' }, { id: '3-4', title: 'まとめる' }] }) : '';
              var r = [...el.querySelectorAll('[data-man]')].map(b => b.dataset.man); el.remove(); return r; }""")
            ok("M2 職員 = AI 답 참고 8-1 버튼 안 냄 · 3-4 냄", refs == ["3-4"], refs)
            page.screenshot(path=str(shots / "r12y71_manual_staff.png"))
            TP.set_admin(page, True)
            secs, toc = open_help()
            ok("M3 管理者 = 8 장 보임 · 목차 「8. 許可書の内容確認（管理者）」", all(s in secs for s in adm) and len(secs) == len(man["sections"])
               and any(t.startswith("8. 許可書の内容確認（管理者）") for t in toc), toc[-6:])
            page.fill("#man-q", "表記確認")
            page.wait_for_timeout(200)
            vis = page.evaluate("() => [...document.querySelectorAll('.c01-man-sec')].filter(e => !e.hidden).map(e => e.dataset.mansec)")
            ok("M3 검색 「表記確認」 = 8-1 · 8-2", "8-1" in vis and "8-2" in vis, vis)
            page.fill("#man-q", "")
            page.locator("#man-8").scroll_into_view_if_needed()
            page.wait_for_timeout(200)
            page.screenshot(path=str(shots / "r12y71_manual_admin.png"))
            refs = page.evaluate("""() => { var el = document.createElement('div'); document.body.appendChild(el);
              el.innerHTML = C01.app._api().manRefs ? C01.app._api().manRefs({ manual_refs: [{ id: '8-1', title: 'x' }] }) : '';
              var r = [...el.querySelectorAll('[data-man]')].map(b => b.dataset.man); el.remove(); return r; }""")
            ok("M3 管理者 = AI 답 참고 8-1 버튼 냄", refs == ["8-1"], refs)
            ok("콘솔 오류 0", not RES["console_errors"], RES["console_errors"][:3])
            ctx.close()
            br.close()
    finally:
        srv.terminate()
    bad = [c for c in RES["checks"] if not c["ok"]]
    print(f"{len(RES['checks']) - len(bad)}/{len(RES['checks'])} ok · shots {shots}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
