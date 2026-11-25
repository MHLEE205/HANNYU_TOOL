# ✦ Powered by LEENAI Automation System — v0.3.80 (R12Y51 · 決定 #399) 「他の行とまとめる」 화면 시험 (가명 fixtures · 실제 호출 0)
"""확인: 엔진 meta.merge_pick 없음 = 단추 없음 (지금 그대로) · 있음 = 실황표 「⋯」 · 옆 창 · 確認・入力 카드에 단추 ·
짝 목록 추천 순서 (N/W · seal · CT 1~3글자) · 확인 창 값 나란히 · 自動OK / 再確認 / 確認済 짝 안내 · 무게 · seal 다름 = 빨간 경고 + 체크 뒤에만 ·
入力済 = 단추 없음 · 사진 줄끼리 = 막힘 · 보낸 action = merge_rows (엔진 action 스키마 통과) · 「まとめを元に戻す」 = undo · 2行→1行 값의 違い 정보.
사용: python tests/test_merge_pick.py [--engine C:\\LEENAI_C01_V2\\engine]"""
import argparse
import copy
import json
import shutil
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_link_ab import RES, ok, free_port, serve, open_page, actions  # noqa: E402

TOOL = Path(__file__).resolve().parent.parent
IV = "TST2611-01"
dump = lambda o: json.dumps(o, ensure_ascii=False, indent=1) + chr(10)   # noqa: E731


def prep(root, on, a_status="自動OK", d_frozen=False):
    jp, qp, mp = root / "_data" / "jikkyou.json", root / "_data" / "queue.json", root / "_data" / "meta.json"
    j, q, m = (json.loads(p.read_text(encoding="utf-8")) for p in (jp, qp, mp))
    iv = next(x for x in j["ivs"] if x["iv_no"] == IV)
    rows = [r for r in iv["rows"] if r.get("slot_guid") and r.get("ct")]
    a, x = rows[0], rows[1]
    pk = a.get("packer")
    a.update({"status": a_status, "engine_status": a_status, "reasons": [] if a_status != "再確認" else ["MIN_SOURCES"], "has_photos": True, "photos": 8,
              "has_docs": True, "human": None, "input_frozen": False})
    x.update({"packer": pk, "status": "自動OK", "engine_status": "自動OK", "reasons": [], "has_photos": True, "photos": 6, "human": None,
              "n_w": (a.get("n_w") or 20000) + 700, "seal": "QQ" + "9" * 6})
    d = copy.deepcopy(a)
    dct = a["ct"][:5] + ("7" if a["ct"][5] != "7" else "8") + a["ct"][6:]          # 1 글자 다른 CT (판독 오류)
    d.update({"container_id": "C-MPD-0001", "no": len(iv["rows"]) + 1, "ct": dct, "slot_guid": None, "status": "再確認", "engine_status": "再確認",
              "reasons": ["SLOT_CONFLICT"], "has_photos": False, "photos": 0, "has_docs": True, "human": None, "input_frozen": d_frozen,
              "seal": (a.get("seal") or "AB123456")[:2] + "-" + (a.get("seal") or "AB123456")[2:], "merge": None, "info": []})
    d.pop("merge", None)
    iv["rows"].append(d)
    jp.write_text(dump(j), encoding="utf-8")
    q0 = copy.deepcopy(next(it for it in q["items"] if it.get("kind") in ("値の違い", "値の確認", "手入力")))
    q0.update({"queue_id": "mpq0000000000001", "iv_no": IV, "ct": dct, "container_id": d["container_id"]})
    q["items"].append(q0)
    qp.write_text(dump(q), encoding="utf-8")
    if on:
        m["merge_pick"] = {"allow": {}}
    mp.write_text(dump(m), encoding="utf-8")
    return {"a": a, "x": x, "d": d, "qid": q0["queue_id"]}


def rules(page):
    page.evaluate("() => { C01.RULES.mergeRows = true; C01.RULES.otherCt = true; C01.app.tick(); }")
    page.click("#tab-main")
    page.click("[data-port='all']")
    page.wait_for_timeout(600)


def row_key(page, ct):
    return page.evaluate('ct => [...document.querySelectorAll("tbody[data-iv=\'' + IV + '\'] tr.c01-row")].map(t => t.getAttribute("data-key")).find(k => k && k.includes(ct))', ct)


def close_modal(page):
    if page.locator("#m-bg").count() and page.locator("#m-bg").is_visible():
        page.click("#m-bg", position={"x": 5, "y": 5})
        page.wait_for_timeout(150)


def open_menu(page, ct):
    close_modal(page)
    page.evaluate("() => { Object.assign(C01.state, {sel: null, editRow: null, view: 'main'}); C01.app.render(); }")
    page.wait_for_timeout(200)
    page.locator(f"[data-rowmenu='{row_key(page, ct)}']").click()
    page.wait_for_selector(".c01-modal-rowmenu")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", default=r"C:\LEENAI_C01_V2\engine")
    a_ = ap.parse_args()
    sys.path.insert(0, a_.engine)
    from engine.output import schema_check as SC   # noqa: E402
    if not (TOOL / "fixtures" / "_data" / "jikkyou.json").is_file():
        sys.exit("fixtures/_data 없음 — 먼저 python tools/make_test_data.py")
    tmp = Path(tempfile.mkdtemp(prefix="c01_mp_"))
    roots = {k: tmp / k for k in ("off", "on", "chk", "hum", "frz")}
    for r in roots.values():
        shutil.copytree(TOOL / "fixtures", r)
    prep(roots["off"], False)
    d = prep(roots["on"], True)
    prep(roots["chk"], True, "再確認")
    prep(roots["hum"], True, "確認済")
    prep(roots["frz"], True, d_frozen=True)
    ports = {k: free_port() for k in roots}
    srv = {k: serve(TOOL, roots[k], ports[k], tmp / ("a_" + k)) for k in roots}
    shots = TOOL / "tests" / "_shots"
    shots.mkdir(exist_ok=True)
    A, X, D = d["a"], d["x"], d["d"]
    try:
        with sync_playwright() as p:
            br = p.chromium.launch()
            # ① meta 없음 = 단추 없음
            p0 = open_page(br, ports["off"], "off")
            rules(p0)
            open_menu(p0, D["ct"])
            ok("meta.merge_pick 없음 = 「⋯」 에 「他の行とまとめる」 없음 (지금 그대로)", p0.locator("#rm-mergepick").count() == 0)
            # ② 켬
            pg = open_page(br, ports["on"], "on")
            rules(pg)
            open_menu(pg, A["ct"])
            ok("自動OK · 칸 있음 · 사진+서류 줄 = 단추 없음", pg.locator("#rm-mergepick").count() == 0)
            open_menu(pg, D["ct"])
            ok("서류만 · 枠外 · SLOT_CONFLICT 줄 = 「⋯」 에 단추", pg.locator("#rm-mergepick").count() == 1)
            pg.click("#rm-mergepick")
            pg.wait_for_selector(".c01-mplist")
            t = pg.locator(".c01-modal-merge").inner_text()
            first = pg.locator("input[name='mp-cand']").first.get_attribute("value")
            pg.screenshot(path=str(shots / "r12y51_pick_auto.png"))
            ok("짝 목록 = 같은 IV · 같은 업체 · 1번 추천 = N/W · seal 같고 CT 1글자 다른 줄", first == A["container_id"] and "N/W 同じ" in t and "CT 1 文字違い" in t, [t[:300]])
            ok("값 나란히 (CT 만 빨강 · seal 하이픈 = 같음) · 自動OK 안내 · 경고 없음 · 버튼 누를 수 있음",
               pg.locator(".c01-mtable td.c01-mdiff").count() == 2 and "自動OK のまま" in t and pg.locator(".c01-mpwarn").count() == 0
               and not pg.locator("#mp-go").is_disabled(), t[-300:])
            # 무게 · seal 다른 짝 고르기
            pg.locator(f"input[name='mp-cand'][value='{X['container_id']}']").check()
            pg.wait_for_timeout(300)
            dis0 = pg.locator("#mp-go").is_disabled()
            t2 = pg.locator(".c01-modal-merge").inner_text()
            pg.check("#mp-sure")
            dis1 = pg.locator("#mp-go").is_disabled()
            pg.screenshot(path=str(shots / "r12y51_pick_warn.png"))
            ok("무게 · seal 다름 = 「別のコンテナかもしれません」 · 체크 전 막힘 → 체크 뒤 누름", "別のコンテナかもしれません" in t2 and dis0 and not dis1, [dis0, dis1])
            # 다시 1번 짝으로 → まとめる
            pg.locator(f"input[name='mp-cand'][value='{A['container_id']}']").check()
            pg.wait_for_timeout(300)
            ids0 = {x.get("action_id") for x in actions(tmp / "a_on")}
            pg.click("#mp-go")
            pg.wait_for_timeout(600)
            new = [x for x in actions(tmp / "a_on") if x.get("action_id") not in ids0]
            ok("まとめる = merge_rows 1 (from = 서류만 줄 · into = 짝 · via pick) · 엔진 action 스키마 통과",
               len(new) == 1 and new[0]["action"] == "merge_rows" and new[0]["value"]["from_container_id"] == D["container_id"]
               and new[0]["value"]["into_container_id"] == A["container_id"] and new[0]["value"].get("via") == "pick" and new[0]["iv"] == IV
               and SC.check_obj(new[0], "action") == [], [new, SC.check_obj(new[0], "action") if new else None])
            mid = new[0]["action_id"] if new else None
            # 되돌리기 = 짝 줄 「⋯」 → 「まとめを元に戻す」
            pg.evaluate("() => { window.confirm = m => true; }")
            open_menu(pg, A["ct"])
            ids1 = {x.get("action_id") for x in actions(tmp / "a_on")}
            ok("짝 줄 「⋯」 에 「まとめを元に戻す」", pg.locator("#rm-mergeundo").count() == 1)
            pg.click("#rm-mergeundo")
            pg.wait_for_timeout(500)
            un = [x for x in actions(tmp / "a_on") if x.get("action_id") not in ids1]
            ok("元に戻す = undo 1 (merge_rows action_id) · 스키마", len(un) == 1 and un[0]["action"] == "undo" and un[0]["value"]["action_id"] == mid
               and SC.check_obj(un[0], "action") == [], un)
            # 옆 창 · 카드 단추
            close_modal(pg)
            pg.evaluate("k => { Object.assign(C01.state, {sel: k, editRow: null, view: 'main'}); C01.app.render(); }", row_key(pg, D["ct"]))
            pg.wait_for_timeout(400)
            ok("옆 창 = 「他の行とまとめる」", pg.locator("#panel-mergepick").count() == 1)
            pg.evaluate("q => { Object.assign(C01.state, {sel: null, view: 'input', qkind: 'all', qsel: q}); C01.app.render(); }", d["qid"])
            pg.wait_for_timeout(500)
            ok("確認・入力 카드 = 「他の行とまとめる」", pg.locator("#q-mergepick").count() == 1)
            pg.click("#q-mergepick")
            pg.wait_for_selector(".c01-mplist")
            ok("카드 단추 → 같은 확인 창", pg.locator("input[name='mp-cand']").count() >= 1)
            close_modal(pg)
            # 2行→1行 값의 違い 정보
            jp = roots["on"] / "_data" / "jikkyou.json"
            j = json.loads(jp.read_text(encoding="utf-8"))
            iv = next(x for x in j["ivs"] if x["iv_no"] == IV)
            ra = next(r for r in iv["rows"] if r["container_id"] == A["container_id"])
            ra["merge"] = {"kinds": ["行まとめ(人)"], "docs": ["fax_p1.pdf"], "differ": ["seal"]}
            ra["info"] = (ra.get("info") or []) + ["行まとめ(人)"]
            jp.write_text(dump(j), encoding="utf-8")
            pg.evaluate("() => { C01.state.view = 'main'; C01.app.tick(); }")
            pg.wait_for_timeout(700)
            bd = pg.locator(f"tbody[data-iv='{IV}'] tr.c01-row:has-text('{A['ct']}') .c01-mergebadge").first
            ok("2行→1行 배지 = 「値の違い 情報」 + 마우스 = 違う項目 シール番号", bd.count() == 1 and "値の違い" in bd.inner_text()
               and "シール番号" in (bd.get_attribute("title") or ""), bd.count())
            # ③ 再確認 · 確認済 짝 안내
            for k, want in (("chk", "1 枚で確認"), ("hum", "確認した値のまま")):
                pk = open_page(br, ports[k], k)
                rules(pk)
                open_menu(pk, D["ct"])
                pk.click("#rm-mergepick")
                pk.wait_for_selector(".c01-mplist")
                tk = pk.locator(".c01-modal-merge").inner_text()
                pk.screenshot(path=str(shots / f"r12y51_pick_{k}.png"))
                ok(f"짝 {'再確認' if k == 'chk' else '確認済'} = 안내 「{want}」", want in tk, tk[-250:])
            # ④ 入力済 = 단추 없음
            pf = open_page(br, ports["frz"], "frz")
            rules(pf)
            open_menu(pf, D["ct"])
            ok("入力済 줄 = 단추 없음 (#307)", pf.locator("#rm-mergepick").count() == 0)
            br.close()
    finally:
        for s in srv.values():
            s.terminate()
    errs = [e for e in RES["console_errors"] if not ("Failed to load resource" in e and "404" in e)]
    ok("콘솔 오류 0", not errs, errs[:3])
    print(json.dumps({"checks": RES["ok"] + RES["ng"], "ng": RES["ng"]}))
    sys.exit(1 if RES["ng"] else 0)


if __name__ == "__main__":
    main()
