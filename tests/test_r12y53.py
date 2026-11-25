# ✦ Powered by LEENAI Automation System — v0.3.82 (R12Y53 · D-223 두 안 받는 쪽) 화면 시험 (가명 fixtures · 실제 호출 0)
"""D-223 (가) = 엔진 info INPUT_REBOOK 줄 → 줄 표 「IV変更 · Compass入力 再度必要」 + IV 머리줄 「… 再度必要 n」 (정보 · 막지 않음).
D-223 (나) = 「入力後の差異」 input_diff.slot.why = rebook → 이유 「IV変更 · 入力した枠が 新しいブッキングに無い（옛 IV → 새 IV）」.
데이터에 그 칸이 없으면 화면 변화 0 (지금 실전 그대로). 다른 why (record) 문구 그대로.
사용: python tests/test_r12y53.py [--engine C:\\LEENAI_C01_PROD\\code]  (먼저 python tools/make_test_data.py)"""
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
OLD_IV, NEW_IV = "TST2610-91", "TST2611-91"   # 가명


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
    return subprocess.Popen([sys.executable, str(TOOL / "tools" / "serve_local.py"), "--root", str(root), "--actions", str(tmp / ("la_" + root.name)),
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
    page.evaluate("() => { C01.state.filter = 'all'; C01.app.tick(); }")
    page.wait_for_timeout(500)
    return page


def card_text(page, qid):
    page.evaluate("q => { C01.state.view = 'input'; C01.state.qkind = 'all'; C01.state.qiv = null; C01.state.qsel = q; C01.app.render(); }", qid)
    page.wait_for_selector("#q-idtab", timeout=10000)
    return page.locator(".c01-idiff").inner_text()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", default=r"C:\LEENAI_C01_PROD\code")
    a = ap.parse_args()
    src = TOOL / "fixtures"
    if not (src / "_data" / "jikkyou.json").is_file():
        print("fixtures/_data 없음 — 먼저 python tools/make_test_data.py")
        sys.exit(2)
    sch = {}
    for nm in ("queue", "jikkyou"):
        p_ = Path(a.engine) / "engine" / "output" / "schema" / f"{nm}.schema.json"
        if p_.is_file():
            sch[nm] = json.loads(p_.read_text(encoding="utf-8"))
    sys.path.insert(0, a.engine)
    from engine.output import schema_check as SC  # noqa: E402
    tmp = Path(tempfile.mkdtemp(prefix="c01_r12y53_"))
    old, new = tmp / "old", tmp / "new"
    shutil.copytree(src, old)
    shutil.copytree(src, new)
    jp, qp = new / "_data" / "jikkyou.json", new / "_data" / "queue.json"
    j = json.loads(jp.read_text(encoding="utf-8"))
    q = json.loads(qp.read_text(encoding="utf-8"))
    qcid = {x.get("container_id") for x in q["items"]}
    iv1 = next(iv for iv in j["ivs"] if len([r for r in iv["rows"] if r.get("ct") and r.get("slot_guid") and r["container_id"] not in qcid]) >= 2
               and len(iv.get("slots") or []) >= 2)
    rs = [r for r in iv1["rows"] if r.get("ct") and r.get("slot_guid") and r["container_id"] not in qcid][:2]
    ra, rb = rs
    # (가): 줄 ra = INPUT_REBOOK (엔진 v0.5.182 s3_input_freeze_rebook_release 꼴 · 상태 自動OK 그대로)
    ra["info"] = list(ra.get("info") or []) + ["INPUT_REBOOK"]
    # (나): 줄 rb = 고정 · 「入力後の差異」 why rebook / 다른 IV 의 줄 = why record (그대로)
    other_slot = next(s["slot_guid"] for s in iv1["slots"] if s["slot_guid"] != rb["slot_guid"])
    rb.update({"status": "確認済", "engine_status": "自動OK", "reasons": [], "info": list(rb.get("info") or []) + ["INPUT_FROZEN"],
               "input_frozen": {"at": "2026-11-08T10:00:00+09:00", "done_at": "2026-11-08T09:58:00+09:00", "action_id": "r12y53cd0001", "src": "apply"}})
    base = {"kind": "入力後の差異", "iv_no": iv1["iv_no"], "field": None, "values": {}, "candidates": [], "files": [], "note": "slot", "resolved": None,
            "superseded": [], "cy_cut": iv1.get("cy_cut"), "cy_open": iv1.get("cy_open"), "issuer": None, "field_sources": {}, "field_source_text": {}}
    qr = dict(base, queue_id="5353535353535301", ct=rb["ct"], container_id=rb["container_id"],
              input_diff={"slot": {"input": "slot-gone-r12y53", "new": rb["slot_guid"], "why": "rebook", "old_iv": OLD_IV, "new_iv": NEW_IV}})
    iv2 = next(iv for iv in j["ivs"] if iv is not iv1 and any(r.get("ct") and r.get("slot_guid") and r["container_id"] not in qcid for r in iv["rows"]))
    rc = next(r for r in iv2["rows"] if r.get("ct") and r.get("slot_guid") and r["container_id"] not in qcid)
    rc.update({"status": "確認済", "engine_status": "自動OK", "reasons": [], "info": list(rc.get("info") or []) + ["INPUT_FROZEN"],
               "input_frozen": {"at": "2026-11-08T10:00:00+09:00", "done_at": "2026-11-08T09:58:00+09:00", "action_id": "r12y53cd0002", "src": "apply"}})
    qo = dict(base, queue_id="5353535353535302", iv_no=iv2["iv_no"], ct=rc["ct"], container_id=rc["container_id"], cy_cut=iv2.get("cy_cut"), cy_open=iv2.get("cy_open"),
              input_diff={"slot": {"input": "slot-other-r12y53", "new": rc["slot_guid"], "why": "record"}})
    q["items"] += [qr, qo]
    q["kinds"] = list(dict.fromkeys(list(q.get("kinds") or []) + ["入力後の差異"]))
    q.setdefault("count", {})["入力後の差異"] = 2
    jp.write_text(json.dumps(j, ensure_ascii=False, indent=1), encoding="utf-8")
    qp.write_text(json.dumps(q, ensure_ascii=False, indent=1), encoding="utf-8")
    if len(sch) == 2:
        er = SC.errors({**q, "items": [qr, qo]}, sch["queue"]) + SC.errors({**j, "ivs": [iv1, iv2]}, sch["jikkyou"])
        ok("시험 데이터 = 엔진 queue · jikkyou 스키마 (why rebook · old_iv · new_iv · info INPUT_REBOOK) 오류 0", not er, er[:4])
    else:
        ok("엔진 스키마 파일 있음", False, a.engine)
    p1, p2 = free_port(), free_port()
    s1, s2 = serve(old, p1, tmp), serve(new, p2, tmp)
    try:
        with sync_playwright() as p:
            br = p.chromium.launch()
            # ① 데이터 없음 (지금 실전) = 화면 변화 0
            page0 = open_page(br, p1)
            ok("(가) 없음 = 줄 표 0 · 머리줄 0", page0.locator("[data-info='input_rebook']").count() == 0 and page0.locator("[data-rebookhead]").count() == 0)
            ok("(나) 없음 = 「IV変更」 글 0 (실황표 · 머리줄)", "IV変更" not in page0.locator("#jikkyou-table").inner_text())
            # ② 데이터 있음
            page = open_page(br, p2)
            tb = f"tbody[data-iv='{iv1['iv_no']}']"
            bd = page.locator("[data-info='input_rebook']")
            ok("(가) 있음 = 줄 표 1 (그 IV 의 그 줄)", bd.count() == 1 and page.locator(tb + " [data-info='input_rebook']").count() == 1, bd.count())
            t = bd.first.get_attribute("title") if bd.count() else ""
            ok("(가) 줄 표 글 「IV変更 · Compass入力 再度必要」 · 마우스 = 새 枠 Compass 未入力 · 情報だけ",
               bd.count() == 1 and bd.first.inner_text() == "IV変更 · Compass入力 再度必要" and "Compass 未入力" in (t or "") and "情報だけ" in (t or ""), [bd.first.inner_text() if bd.count() else None, t])
            hd = page.locator("[data-rebookhead]")
            ok("(가) IV 머리줄 「IV変更 · Compass入力 再度必要 1」 · 그 IV 만", hd.count() == 1 and page.locator(tb + " [data-rebookhead]").count() == 1
               and hd.first.inner_text().strip() == "IV変更 · Compass入力 再度必要 1", hd.first.inner_text() if hd.count() else None)
            row = page.locator(tb + " tr.c01-row").filter(has=page.locator("[data-info='input_rebook']")).first
            ok("(가) 줄 상태 그대로 (정보만 · 막지 않음)", row.get_attribute("data-status") == ra.get("status"), [row.get_attribute("data-status"), ra.get("status")])
            shot = TOOL / "tests" / "_shots"
            shot.mkdir(exist_ok=True)
            page.screenshot(path=str(shot / "r12y53_rebook_info.png"))
            it = card_text(page, qr["queue_id"])
            ok("(나) why rebook = 이유 「IV変更 · 入力した枠が 新しいブッキングに無い（옛 IV → 새 IV）」",
               "IV変更 · 入力した枠が 新しいブッキングに無い" in it and f"（{OLD_IV} → {NEW_IV}）" in it and "rebook" not in it, it[:300])
            ok("(나) 枠 칸 빨강 1 (입력값 = 別の枠)", page.locator("#q-idtab tr.d[data-idf='slot']").count() == 1 and "別の枠" in it, it[:300])
            page.screenshot(path=str(shot / "r12y53_rebook_card.png"))
            it2 = card_text(page, qo["queue_id"])
            ok("다른 why (record) 문구 그대로 · 「IV変更」 0", "Compass入力の記録と、今の行の値・枠が違います" in it2 and "IV変更" not in it2, it2[:300])
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
