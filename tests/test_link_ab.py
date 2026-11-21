# ✦ Powered by LEENAI Automation System — v0.3.67 (R12Y5 · 決定 #356 穴 3 · #365) 「IVに連結」 (a)/(b) 화면 시험 (가명 fixtures · 실제 호출 0)
"""확인: 엔진 meta.link_iv_ab 없음 = 지금 화면 그대로 · 있음 = 「この書類は どれ？」 먼저 · (a) 줄 추천 순서 (CT 오독이어도 seal · 무게) → link_iv mode attach ·
(b) 쓰인 칸 = 옮길 빈 칸 필수 (move_to_slot) · 入力済 = 막힘 · 빈 칸 없음 = 막힘 · 조건 다른 점 · 元に戻す · 入力後の差異 merge_undo 문구 ·
보낸 action = 엔진 action 스키마 통과 · 옛 TOOL (0.3.66) 이 meta.link_iv_ab 를 받아도 깨지지 않음 (--old-tool).
사용: python tests/test_link_ab.py [--engine C:\\LEENAI_C01_V2\\engine] [--old-tool <0.3.66 내보낸 폴더>]"""
import argparse
import copy
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
IV = "TST2611-01"
dump = lambda o: json.dumps(o, ensure_ascii=False, indent=1) + chr(10)   # noqa: E731


def ok(name, cond, got=None):
    RES["ok" if cond else "ng"] += 1
    print(("OK  " if cond else "NG  ") + name + ("" if cond else f" — {got!r}"[:500]))


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def serve(tool, root, port, tmp):
    return subprocess.Popen([sys.executable, str(tool / "tools" / "serve_local.py"), "--root", str(root), "--actions", str(tmp / "la"),
                             "--port", str(port), "--today", "2026-11-08"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def open_page(br, port, tag):
    page = br.new_context(viewport={"width": 1600, "height": 1000}).new_page()
    page.on("console", lambda m: RES["console_errors"].append(f"{tag}: {m.text}") if m.type == "error" else None)
    page.on("pageerror", lambda e: RES["console_errors"].append(f"{tag}: pageerror {e}"))
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
    page.evaluate("() => { C01.state.me = {name: 'staff_a', email: 'staff_a@fake'}; }")
    return page


def actions(tmp):
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted((tmp / "la" / "_actions").rglob("*.json")) if "_rejected" not in p.parts]


def prep(root, ab_on):
    """가명 자료: TST2611-01 (5칸 · 4줄 · 빈 칸 1) 의 業者・IV未定 카드에 판독 2줄 — ① CT 4글자 오독 + seal 앞 글자 다름 = 3번 줄 · ② CT 같음 = 1번 줄."""
    jp, qp, mp = root / "_data" / "jikkyou.json", root / "_data" / "queue.json", root / "_data" / "meta.json"
    j, q, m = (json.loads(p.read_text(encoding="utf-8")) for p in (jp, qp, mp))
    iv = next(x for x in j["ivs"] if x["iv_no"] == IV)
    rows = [r for r in iv["rows"] if r.get("slot_guid")]
    r1, r3 = rows[0], rows[2]
    hq = next(x for x in q["items"] if x["kind"] == "業者・IV未定")
    ct3 = "XYW" + r3["ct"][3:7] + "9" + r3["ct"][8:]
    hq["fax_read"] = {"ct": [ct3, r1["ct"]], "pages": [
        {"page": 1, "doc_type": "other", "rows": [{"ct": ct3, "seal": "X" + r3["seal"][1:], "n_w": r3["n_w"], "t_w": r3["t_w"]}]},
        {"page": 2, "doc_type": "other", "rows": [{"ct": r1["ct"], "seal": "X" + r1["seal"][1:], "n_w": r1["n_w"], "t_w": r1["t_w"]}]}]}
    if ab_on:
        m["link_iv_ab"] = ["attach", "move_to_slot"]
    m["link_iv_scopes"] = ["one", "packer_all"]
    for p, o in ((jp, j), (qp, q), (mp, m)):
        p.write_text(dump(o), encoding="utf-8")
    return {"hq": hq["queue_id"], "r1": r1, "r3": r3, "rows": rows, "free": [s["slot_guid"] for s in iv["slots"] if s["slot_guid"] not in {r["slot_guid"] for r in rows}]}


def open_card(page, qid):
    page.evaluate("q => { C01.state.view = 'input'; C01.state.qkind = 'all'; C01.state.qsel = q; C01.app.render(); }", qid)
    page.wait_for_selector("#link-iv")
    page.click(f".c01-linkiv [data-linkiv='{IV}']")
    page.wait_for_timeout(250)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", default=r"C:\LEENAI_C01_V2\engine")
    ap.add_argument("--old-tool", default=None, help="TOOL 0.3.66 (git archive hannyu-main) 폴더 — 있으면 옛 화면이 meta.link_iv_ab 에 깨지지 않는지")
    a = ap.parse_args()
    sys.path.insert(0, a.engine)
    from engine.output import schema_check as SC   # noqa: E402  (받는 쪽 대조)
    if not (TOOL / "fixtures" / "_data" / "jikkyou.json").is_file():
        sys.exit("fixtures/_data 없음 — 먼저 python tools/make_test_data.py")
    tmp = Path(tempfile.mkdtemp(prefix="c01_linkab_"))
    off, on = tmp / "off", tmp / "on"
    shutil.copytree(TOOL / "fixtures", off)
    shutil.copytree(TOOL / "fixtures", on)
    prep(off, False)
    d = prep(on, True)
    r1, r3 = d["r1"], d["r3"]
    p1, p2 = free_port(), free_port()
    s1, s2 = serve(TOOL, off, p1, tmp / "off_a"), serve(TOOL, on, p2, tmp)
    s3 = None
    shots = TOOL / "tests" / "_shots"
    shots.mkdir(exist_ok=True)
    try:
        with sync_playwright() as p:
            br = p.chromium.launch()
            # ① 엔진 meta 없음 = 지금 화면 그대로
            pg0 = open_page(br, p1, "off")
            open_card(pg0, d["hq"])
            pg0.locator(f"input[name='link-slot'][value='{r1['slot_guid']}']").check()
            pg0.wait_for_timeout(200)
            t0 = pg0.locator(".c01-linkiv").inner_text()
            ok("meta.link_iv_ab 없음 = 「この書類は どれ？」 없음 · 칸 목록 · 「もう行があります」 경고 (지금 그대로)",
               pg0.locator("#link-ab").count() == 0 and pg0.locator("input[name='link-slot']").count() == 5 and "もう行があります" in t0 and not pg0.locator("#q-submit").is_disabled(), t0[-200:])
            # ② 켬 = 먼저 묻기
            page = open_page(br, p2, "on")
            open_card(page, d["hq"])
            t = page.locator(".c01-linkiv").inner_text()
            ok("켬: IV 고른 뒤 「この書類は どれ？」 (a) 既にある行の追加書類 / (b) 新しいコンテナ · 칸 목록은 아직 없음 · 버튼 막힘",
               page.locator("#link-ab").count() == 1 and "既にある行の追加書類" in t and "新しいコンテナ" in t and page.locator("input[name='link-slot']").count() == 0
               and page.locator("#q-submit").is_disabled() and "この書類は どれ？" in page.locator("#q-submit").inner_text(), [t[:200], page.locator("#q-submit").inner_text()])
            # ③ (a) 추천
            page.locator("input[name='link-ab'][value='a']").check()
            page.wait_for_timeout(250)
            order = page.evaluate("() => [...document.querySelectorAll('#link-rows input[name=\"link-row\"]')].map(x => x.value)")
            rec = page.locator("#link-rows .c01-slotopt.match").count()
            ok("(a) 줄 목록 = CT 있는 줄 전부 · 추천 상위 2 = 판독 2줄의 줄 (CT 오독 줄은 seal · 무게로) · ★ おすすめ 2",
               len(order) == len(d["rows"]) and sorted(order[:2]) == sorted([r1["container_id"], r3["container_id"]]) and rec == 2, [order, rec])
            ok("(a) 안내 = 参考の書類 · 새 줄 없음 · 값 · 판정 그대로 · 버튼 = 줄 고르기 전 막힘",
               "参考の書類" in page.locator("#link-rows").inner_text() and page.locator("#q-submit").is_disabled(), page.locator("#q-submit").inner_text())
            page.locator(f"input[name='link-row'][value='{r3['container_id']}']").check()
            page.wait_for_timeout(200)
            ok("(a) 줄 고름 = 버튼 「確認して次へ」", not page.locator("#q-submit").is_disabled(), page.locator("#q-submit").inner_text())
            page.screenshot(path=str(shots / "r12y5_link_a.png"))
            ids0 = {x.get("action_id") for x in actions(tmp)}
            dl = []

            def acc(dg):
                dl.append(dg.message)
                dg.accept()
            page.on("dialog", acc)
            page.click("#q-submit")
            page.wait_for_timeout(700)
            new = [x for x in actions(tmp) if x.get("action_id") not in ids0]
            v = new[0]["value"] if new else {}
            ok("(a) 저장 = link_iv mode attach · container_id = 고른 줄 · slot_guid = 그 줄 칸 · move_to_slot 없음 · 확인창 0 · 엔진 action 스키마 통과",
               len(new) == 1 and new[0]["action"] == "link_iv" and v.get("mode") == "attach" and v.get("container_id") == r3["container_id"]
               and v.get("slot_guid") == r3["slot_guid"] and "move_to_slot" not in v and dl == [] and SC.check_obj(new[0], "action") == [],
               [new, dl, new and SC.check_obj(new[0], "action")])
            page.evaluate("q => { C01.state.qkind = 'done'; C01.state.qsel = q; C01.app.render(); }", d["hq"])
            page.wait_for_timeout(300)
            page.click("#q-undo")
            page.wait_for_timeout(500)
            un = [x for x in actions(tmp) if x.get("action_id") not in ids0 and x["action"] == "undo"]
            ok("(a) 元に戻す = undo 1 (value.action_id = link_iv)", len(un) == 1 and new and un[0]["value"]["action_id"] == new[0]["action_id"], un)
            # ④ (b) 쓰인 칸 → 옮길 빈 칸 필수
            page.evaluate("q => { C01.state.qkind = 'all'; C01.state.qsel = q; C01.state.qvals[q] = {}; C01.app.render(); }", d["hq"])
            open_card(page, d["hq"])
            page.locator("input[name='link-ab'][value='b']").check()
            page.wait_for_timeout(200)
            st = page.evaluate("() => [...document.querySelectorAll('.c01-linkslots .c01-slotopt')].map(x => x.innerText)")
            ok("(b) 칸 목록 줄 상태 = 「空き」 1 · 「使用中 CT · 自動OK」 · 「使用中 CT · 確認済」",
               sum("空き" in x for x in st) == 1 and any("使用中 " + r1["ct"] + " · 自動OK" in x for x in st) and any("· 確認済" in x for x in st), st)
            page.locator(f"input[name='link-slot'][value='{r1['slot_guid']}']").check()
            page.wait_for_timeout(200)
            mt = page.locator("#link-move").inner_text() if page.locator("#link-move").count() else ""
            ok("(b) 쓰인 칸 고름 = 「この枠には (CT) が入っています。… どの枠に移しますか？（必須）」 · 후보 = 빈 칸 · 버튼 막힘 · 「もう行があります」 확인창 문구 없음",
               f"この枠には {r1['ct']} が入っています" in mt and "（必須）" in mt and page.locator("input[name='link-move']").count() == len(d["free"])
               and page.locator("#q-submit").is_disabled() and "移す空き枠" in page.locator("#q-submit").inner_text()
               and "もう行があります" not in page.locator(".c01-linkiv").inner_text(), [mt[:200], page.locator("#q-submit").inner_text()])
            page.locator(f"input[name='link-move'][value='{d['free'][0]}']").check()
            page.wait_for_timeout(200)
            page.screenshot(path=str(shots / "r12y5_link_b_move.png"))
            ids1 = {x.get("action_id") for x in actions(tmp)}
            page.click("#q-submit")
            page.wait_for_timeout(700)
            nb = [x for x in actions(tmp) if x.get("action_id") not in ids1]
            vb = nb[0]["value"] if nb else {}
            ok("(b) 저장 = link_iv mode new · slot_guid = 쓰인 칸 · move_to_slot = 고른 빈 칸 · 확인창 0 · 엔진 스키마 통과 (한 기록)",
               len(nb) == 1 and vb.get("mode") == "new" and vb.get("slot_guid") == r1["slot_guid"] and vb.get("move_to_slot") == d["free"][0]
               and "container_id" not in vb and dl == [] and SC.check_obj(nb[0], "action") == [], [nb, dl])
            page.remove_listener("dialog", acc)
            page.evaluate("q => { C01.state.qkind = 'done'; C01.state.qsel = q; C01.app.render(); }", d["hq"])
            page.wait_for_timeout(300)
            page.click("#q-undo")
            page.wait_for_timeout(500)
            ub = [x for x in actions(tmp) if x.get("action_id") not in ids1 and x["action"] == "undo"]
            ok("(b) 元に戻す = undo 1 (연결 + 옮김 한 기록 → 한 번에)", len(ub) == 1 and nb and ub[0]["value"]["action_id"] == nb[0]["action_id"], ub)
            page.evaluate("() => { C01.state.qkind = 'all'; }")
            # ⑤ 入力済 막힘 · 빈 칸 없음 막힘 · 조건 다른 점
            jp, qp = on / "_data" / "jikkyou.json", on / "_data" / "queue.json"
            j0 = jp.read_text(encoding="utf-8")
            j = json.loads(j0)
            iv = next(x for x in j["ivs"] if x["iv_no"] == IV)
            rr = next(r for r in iv["rows"] if r["container_id"] == r3["container_id"] and r["slot_guid"] == r3["slot_guid"])
            rr["input_frozen"] = {"at": "2026-11-08T10:00:00+09:00", "done_at": "2026-11-08T09:58:00+09:00", "action_id": "r12y5frz0001", "src": "apply"}
            fs = next(s for s in iv["slots"] if s["slot_guid"] == d["free"][0])
            fs["work_date"] = "2026-11-12"
            jp.write_text(dump(j), encoding="utf-8")
            page.evaluate("q => { C01.state.qsel = q; C01.state.qvals[q] = {}; C01.app.tick(); }", d["hq"])
            page.wait_for_timeout(700)
            open_card(page, d["hq"])
            page.locator("input[name='link-ab'][value='b']").check()
            page.wait_for_timeout(150)
            st2 = page.evaluate("() => [...document.querySelectorAll('.c01-linkslots .c01-slotopt')].map(x => x.innerText)")
            ok("(b) 줄 상태 「使用中 CT · 入力済」 (row.input_frozen)", any("使用中 " + r3["ct"] + " · 入力済" in x for x in st2), st2)
            page.locator(f"input[name='link-slot'][value='{r3['slot_guid']}']").check()
            page.wait_for_timeout(200)
            bt = page.locator("#link-block").inner_text() if page.locator("#link-block").count() else ""
            ok("(b) 入力済 줄 칸 = 「入力済みの行は動かせません — 追加書類なら (a) を選んでください」 · 버튼 막힘",
               "入力済みの行は動かせません — 追加書類なら (a) を選んでください" in bt and page.locator("#q-submit").is_disabled()
               and page.locator("input[name='link-move']").count() == 0, [bt, page.locator("#q-submit").inner_text()])
            page.locator(f"input[name='link-slot'][value='{r1['slot_guid']}']").check()
            page.wait_for_timeout(200)
            cd = page.evaluate("() => [...document.querySelectorAll('.c01-linkslots .c01-conddiff')].map(x => x.innerText)")
            page.locator(f"input[name='link-move'][value='{d['free'][0]}']").check()
            page.wait_for_timeout(200)
            ok("조건 다른 칸 = 「違い: 作業予定日」 한 줄 · 옮길 칸으로 고르면 「作業予定日の違う枠です」 안내",
               cd == ["違い: 作業予定日"] and "作業予定日の違う枠です" in page.locator("#link-move").inner_text(), [cd, page.locator("#link-move").inner_text()[-120:]])
            j2 = json.loads(j0)
            iv2 = next(x for x in j2["ivs"] if x["iv_no"] == IV)
            extra = copy.deepcopy(r1)
            extra.update({"container_id": "C-G-r12y5full", "ct": "TSTU0019990", "slot_guid": d["free"][0], "no": 99})
            iv2["rows"].append(extra)
            jp.write_text(dump(j2), encoding="utf-8")
            page.evaluate("q => { C01.state.qsel = q; C01.state.qvals[q] = {}; C01.app.tick(); }", d["hq"])
            page.wait_for_timeout(700)
            open_card(page, d["hq"])
            page.locator("input[name='link-ab'][value='b']").check()
            page.wait_for_timeout(150)
            page.locator(f"input[name='link-slot'][value='{r1['slot_guid']}']").check()
            page.wait_for_timeout(200)
            bt2 = page.locator("#link-block").inner_text() if page.locator("#link-block").count() else ""
            ok("(b) 5칸 모두 사용 = 「空き枠がありません — … 枠外 … (a) を選んでください」 · 버튼 막힘 (강행 없음)",
               "空き枠がありません" in bt2 and "(a) を選んでください" in bt2 and page.locator("#q-submit").is_disabled(), bt2)
            page.screenshot(path=str(shots / "r12y5_link_b_full.png"))
            page.locator("input[name='link-ab'][value='a']").check()
            page.wait_for_timeout(200)
            ok("같은 IV 에서 (a) 로 바꾸면 = 줄 고르기 (막힘 없음)", page.locator("#link-rows").count() == 1 and page.locator("#link-block").count() == 0, "")
            jp.write_text(j0, encoding="utf-8")
            # ⑥ 入力後の差異 merge_undo 문구 (#365)
            q = json.loads(qp.read_text(encoding="utf-8"))
            qa = {"queue_id": "7e7e7e7e7e7e7ed5", "kind": "入力後の差異", "iv_no": IV, "ct": r1["ct"], "field": None, "container_id": r1["container_id"], "values": {},
                  "candidates": [], "files": [], "note": "n_w", "resolved": None, "superseded": [], "cy_cut": None, "cy_open": None, "issuer": None,
                  "field_sources": {}, "field_source_text": {}, "input_diff": {"n_w": {"input": r1["n_w"], "new": 20500, "why": "merge_undo"}}}
            q["items"].append(qa)
            q["kinds"] = list(q.get("kinds") or []) + ["入力後の差異"]
            q.setdefault("count", {})["入力後の差異"] = 1
            qp.write_text(dump(q), encoding="utf-8")
            page.evaluate("() => C01.app.tick()")
            page.wait_for_timeout(700)
            page.evaluate("q => { C01.state.view = 'input'; C01.state.qkind = 'all'; C01.state.qsel = q; C01.app.render(); }", qa["queue_id"])
            page.wait_for_selector("#q-idtab")
            it = page.locator(".c01-idiff").inner_text()
            ok("入力後の差異 why merge_undo = 「まとめを元に戻しました — Compass 入力値は そのまま（入力済）」 (낱말 merge_undo 그대로 안 보임)",
               "まとめを元に戻しました — Compass 入力値は そのまま（入力済）" in it and "merge_undo" not in it, it[:300])
            errs = [e for e in RES["console_errors"] if not ("Failed to load resource" in e and "404" in e)]
            ok("콘솔 오류 0 (새 화면)", not errs, errs[:3])
            # ⑦ 옛 TOOL 0.3.66 + meta.link_iv_ab = 깨지지 않음 (지금 화면 그대로)
            if a.old_tool:
                p3 = free_port()
                s3 = serve(Path(a.old_tool), on, p3, tmp / "old_a")
                n0 = len(RES["console_errors"])
                po = open_page(br, p3, "old")
                ver = po.locator(".ln-hdr-ver").inner_text()
                open_card(po, d["hq"])
                po.locator(f"input[name='link-slot'][value='{r1['slot_guid']}']").check()
                po.wait_for_timeout(200)
                to = po.locator(".c01-linkiv").inner_text()
                oe = [e for e in RES["console_errors"][n0:] if not ("Failed to load resource" in e and "404" in e)]
                ok("옛 TOOL 0.3.66 + meta.link_iv_ab = 화면 깨지지 않음 (지금 칸 목록 · 경고 그대로 · 콘솔 오류 0)",
                   "0.3.66" in ver and po.locator("#link-ab").count() == 0 and "もう行があります" in to and not oe, [ver, oe[:2]])
            br.close()
    finally:
        for s in (s1, s2, s3):
            if s:
                s.terminate()
    print(json.dumps({"checks": RES["ok"] + RES["ng"], "ng": RES["ng"]}))
    sys.exit(1 if RES["ng"] else 0)


if __name__ == "__main__":
    main()
