# ✦ Powered by LEENAI Automation System — C-01 TOOL v0.1 끝-끝 시험 (사본 DB + 사본 _data · local 모드 · Playwright)
r"""TOOL 로 値の違い 2 · 手入力 1 · 写真のCT 1 · 未分類FAX 1 · 先勝ち 1 · 체크디짓 확인 후 저장 1 (v0.2.2 #109 ③) · 슬롯 입れ替え 1 (#109 ②) 처리 → run_actions_tick.py (사본) →
사본 DB 반영 · _data 다시 쓰기 → TOOL 다시 읽어 상태 확인 → 되돌림 (apply.revert) → 판정 표 해시 = 처리 전.
이 스크립트에는 데이터가 없다 (대상은 실행 때 queue.json 에서 고름). 결과·스크린샷은 --out (레포 밖) 에만.
사용: python tests/e2e_local.py --db <사본 engine.db> --root <사본 photo_v2_local> --data <사본 C01_DATA> --out <폴더>
      [--engine C:\LEENAI_C01_V2\engine_r68] [--staff fixtures/_masters/pol_staff.json]"""
import argparse
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

TOOL = Path(__file__).resolve().parent.parent
MAIN_DB = Path(r"C:\LEENAI_C01_V2\data\engine.db").resolve()
MAIN_ROOT = Path(r"C:\LEENAI_C01_V2\data\photo_v2_local").resolve()
R = {"checks": [], "console_errors": [], "external": []}


def ok(name, cond, detail=""):
    R["checks"].append({"name": name, "ok": bool(cond), "detail": str(detail)[:400]})
    print(("OK  " if cond else "NG  ") + name + (f" — {detail}" if detail else ""), flush=True)


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def acts(root):
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted((root / "_actions").glob("20*/*.json"))]


def pick_item(page, kind, field=None, nth=0, avoid=()):
    page.click(f".c01-kinds [data-kind='{kind}']")
    page.wait_for_timeout(150)
    q = page.evaluate("(a) => { const it = (C01.state.queue.items||[]).filter(x => x.kind === a[0] && (!a[1] || x.field === a[1]) && !x.resolved && a[3].indexOf(x.queue_id) < 0); return it[a[2]] ? it[a[2]].queue_id : null; }",
                      [kind, field, nth, list(avoid)])
    if q:
        page.click(f"[data-q='{q}']")
        page.wait_for_timeout(150)
    return q


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--root", required=True)
    ap.add_argument("--data", required=True, help="사본 C01_DATA (run_actions_tick 의 잠금·정답 파일 위치)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--engine", default=r"C:\LEENAI_C01_V2\engine_r68")
    ap.add_argument("--staff", default=str(TOOL / "fixtures" / "_masters" / "pol_staff.json"))
    ap.add_argument("--today", default="2026-11-08")
    a = ap.parse_args()
    db, root, out = Path(a.db).resolve(), Path(a.root).resolve(), Path(a.out)
    if db == MAIN_DB or root == MAIN_ROOT:
        sys.exit("거부: 본 DB / 본 photo_v2_local 은 쓰지 않음 — 사본만")
    out.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, a.engine)
    sys.path.insert(0, str(Path(a.engine) / "tools"))
    os.environ["C01_DATA"] = a.data
    from run_actions_tick import judge_hash  # noqa: E402
    h0 = judge_hash(str(db))
    R["judge_hash_before"] = h0
    port = free_port()
    srv = subprocess.Popen([sys.executable, str(TOOL / "tools" / "serve_local.py"), "--root", str(root), "--port", str(port), "--staff", a.staff, "--today", a.today],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    url = f"http://127.0.0.1:{port}/"
    for _ in range(50):
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
            break
        except OSError:
            time.sleep(0.1)
    done = []
    try:
        with sync_playwright() as p:
            br = p.chromium.launch()

            def newpage(tag, staff):
                pg = br.new_context(viewport={"width": 1440, "height": 1000}).new_page()
                pg.on("console", lambda m: R["console_errors"].append(f"{tag}: {m.text}") if m.type == "error" else None)
                pg.on("pageerror", lambda e: R["console_errors"].append(f"{tag}: {e}"))
                pg.on("request", lambda r: R["external"].append(r.url) if not r.url.startswith(("http://127.0.0.1", "https://mhlee205.github.io/LEENAI_COMMON/", "data:", "blob:")) else None)
                pg.goto(url)
                pg.wait_for_selector("#c01-open-server", timeout=20000)
                pg.click("#c01-open-server")
                pg.wait_for_selector("body[data-c01-ready='1']", timeout=30000)
                pg.select_option("#me-select", staff)
                pg.wait_for_timeout(200)
                pg.click("[data-port='all']")
                return pg
            page = newpage("A", "STAFF_A")
            other = newpage("B", "STAFF_B")
            n_rows = page.locator("tr.c01-row").count()
            ok("実況表 (사본 실제 _data) 열림", n_rows > 0, n_rows)
            page.screenshot(path=str(out / "e2e_jikkyou.png"))
            # v0.2.0: Compass入力 DRY 窓 · 催促 プレビュー (実データ 사본 · 送信 無効)
            if page.locator(".c01-btn-pri[data-compass]").count():
                page.locator(".c01-btn-pri[data-compass]").first.click()
                page.wait_for_selector("#compass-table, .c01-modal .c01-err", timeout=5000)
                ok("Compass入力 DRY 窓 (전원 OK IV · 비교표 · 送信 비활성)", page.locator("#compass-table tbody tr").count() > 0 and page.locator("#compass-send").is_disabled())
                R["compass_modal_rows"] = page.locator("#compass-table tbody tr").count()
                page.screenshot(path=str(out / "e2e_compass.png"))
                page.click("[data-close]")
            if page.locator("[data-remind]").count():
                page.locator("[data-remind]").first.click()
                page.wait_for_selector(".c01-rmd", timeout=5000)
                body = page.locator(".c01-rbody").first.inner_text()
                ok("催促 プレビュー (본문 끝 Powered · 送信 비활성)", body.strip().endswith("✦ Powered by LEENAI Automation System") and page.locator("#remind-send").is_disabled())
                page.screenshot(path=str(out / "e2e_remind.png"))
                page.click("[data-close]")
            page.click("#tab-input")
            # 値の違い 2 (seal)
            for k in range(2):
                q = pick_item(page, "値の違い", "seal", 0, done)
                page.locator("[data-alt='0']").click()
                t0 = time.time()
                page.click("#q-submit")
                page.wait_for_timeout(200)
                R.setdefault("self_ms", []).append(round((time.time() - t0) * 1000))
                done.append(q)
            ok("値の違い 2 → confirm_value 2", sum(1 for x in acts(root) if x["action"] == "confirm_value") == 2)
            # 先勝ち: 내가 처리한 뒤, 다른 사람의 더 이른 at 기록을 둠 → 엔진은 at 순으로 다른 사람이 이김
            q3 = pick_item(page, "値の違い", "seal", 0, done)
            page.locator("[data-alt='0']").click()
            page.click("#q-submit")
            page.wait_for_timeout(200)
            mine3 = next(x for x in acts(root) if x["queue_id"] == q3)
            early = dict(mine3, action_id="zz-other-" + mine3["action_id"][-10:], by="staff.b@example.invalid", at=a.today + "T00:00:01+09:00")
            (root / "_actions" / a.today / f"{early['action_id']}.json").write_text(json.dumps(early, ensure_ascii=False), encoding="utf-8")
            done.append(q3)
            # 手入力 1 (n_w 또는 bales)
            q4 = pick_item(page, "手入力", "bales", 0, done) or pick_item(page, "手入力", "n_w", 0, done)
            page.fill("#q-in", "22")
            page.click("#q-submit")
            page.wait_for_timeout(200)
            ok("手入力 1 → manual_input", any(x["action"] == "manual_input" and x["queue_id"] == q4 for x in acts(root)))
            done.append(q4)
            # v0.2.2 (#109 ③) 체크디짓 틀림 → 확인창 · 취소 = 안 씀 · 확인 = 저장 (CT_CHECKDIGIT_OVERRIDE)
            q5 = pick_item(page, "手入力", "ct", 0, done)
            n_before = len(acts(root))
            if q5:
                msgs = []
                page.once("dialog", lambda dg: (msgs.append(dg.message), dg.dismiss()))
                page.fill("#q-in", "TSTU0000015")
                page.click("#q-submit")
                page.wait_for_timeout(300)
                ok("체크디짓 틀림 확인창 · 취소 = 파일 안 씀", msgs == ["チェックディジットが合いません。もう一度確認してください"] and len(acts(root)) == n_before, msgs)
                page.once("dialog", lambda dg: (msgs.append(dg.message), dg.accept()))
                page.click("#q-submit")
                page.wait_for_timeout(300)
                ok("체크디짓 확인 → manual_input (override CT_CHECKDIGIT_OVERRIDE)",
                   any(x["queue_id"] == q5 and x.get("override") == ["CT_CHECKDIGIT_OVERRIDE"] for x in acts(root)))
                done.append(q5)
            else:
                ok("체크디짓 확인 후 저장", False, "手入力 ct 항목 없음")
            q5_cid = next((x["container_id"] for x in page.evaluate("C01.state.queue.items") if x["queue_id"] == q5), None) if q5 else None
            # 写真のCT
            q6 = pick_item(page, "写真のCT")
            if q6 and page.locator("[data-choice='0']").count():
                page.locator("[data-choice='0']").click()
                page.click("#q-submit")
                page.wait_for_timeout(200)
            ok("写真のCT → assign_photos", any(x["action"] == "assign_photos" for x in acts(root)))
            # 未分類FAX → link_fax (IV = 実況表 첫 IV)
            q7 = pick_item(page, "未分類FAX")
            iv = page.evaluate("C01.state.jik.ivs[0].iv_no")
            page.fill("#q-iv", iv)
            page.click("#q-submit")
            page.wait_for_timeout(200)
            ok("未分類FAX → link_fax", any(x["action"] == "link_fax" and x["queue_id"] == q7 for x in acts(root)))
            page.screenshot(path=str(out / "e2e_input_after.png"))
            # v0.2.2 (#109 ②) 슬롯 입れ替え: 칸 있는 줄 2개 이상인 IV 에서 첫 줄을 둘째 줄 칸으로 (확인창 → 1건 swap_ct)
            page.click("#tab-main")
            page.wait_for_timeout(200)
            sw = page.evaluate("""() => { for (const iv of C01.state.jik.ivs) { const rs = iv.rows.filter(r => r.ct && r.slot_guid && iv.rows.filter(y => y.ct === r.ct).length === 1);
                 if (rs.length >= 2) return {iv: iv.iv_no, a: rs[0].ct, b: rs[1].ct, sa: rs[0].slot_guid, sb: rs[1].slot_guid}; } return null; }""")
            R["slot_swap"] = bool(sw)
            if sw:
                page.locator(f"tbody[data-iv='{sw['iv']}'] tr.c01-row[data-key*='{sw['a']}'] [data-slot]").click()
                page.wait_for_selector("[data-slotpick]")
                page.locator(f"[data-slotpick='{sw['sb']}']").click()
                dmsg = []
                page.once("dialog", lambda dg: (dmsg.append(dg.message), dg.accept()))
                page.click("#slot-apply")
                page.wait_for_timeout(400)
                sc = [x for x in acts(root) if x["action"] == "slot_change"]
                ok("슬롯 입れ替え 확인창 → slot_change 1 (swap_ct · 모든 직원)", dmsg == [f"{sw['b']} が入っています。入れ替えますか"] and len(sc) == 1
                   and sc[0]["value"]["swap_ct"] == sw["b"], dmsg)
                page.screenshot(path=str(out / "e2e_slot.png"))
            else:
                ok("슬롯 입れ替え 대상 IV", False, "칸 있는 줄 2개 IV 없음")
            page.click("#tab-input")
            page.wait_for_timeout(200)
            # 다른 창 30초 안
            t1 = time.time()
            first_q = done[0]
            try:
                other.click("#tab-input")
                other.wait_for_function("(q) => { const it=(C01.state.queue.items||[]).find(x=>x.queue_id===q); return document.querySelector(`[data-q='${q}'].done`) !== null; }", arg=first_q, timeout=33000)
                R["other_window_secs"] = round(time.time() - t1, 1)
                ok("다른 창 30초 안 반영", True, f"{R['other_window_secs']}s")
            except Exception as e:  # noqa: BLE001
                ok("다른 창 30초 안 반영", False, e)
            # 엔진 반영 (사본)
            env = dict(os.environ, PYTHONIOENCODING="utf-8", C01_DATA=a.data)
            t2 = time.time()
            pr = subprocess.run([sys.executable, str(Path(a.engine) / "tools" / "run_actions_tick.py"), "--db", str(db), "--root", str(root), "--today", a.today],
                                capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, cwd=a.engine)
            R["tick_secs"] = round(time.time() - t2, 1)
            try:
                tick = json.loads(pr.stdout)
            except ValueError:
                tick = {"raw": pr.stdout[-1500:], "err": pr.stderr[-1500:]}
            R["tick"] = {k: v for k, v in tick.items() if k in ("result", "files", "by_result", "outputs", "raw", "err")}
            ok("run_actions_tick (사본) 반영", pr.returncode == 0, json.dumps(R["tick"], ensure_ascii=False)[:400])
            # TOOL 다시 읽기
            page.evaluate("C01.app.tick()")
            page.wait_for_timeout(800)
            st = page.evaluate("(qs) => qs.map(q => { const it=(C01.state.queue.items||[]).find(x=>x.queue_id===q); return it ? {q, resolved: it.resolved && it.resolved.by, sup: (it.superseded||[]).map(s=>s.by)} : {q, gone: true}; })", done)
            R["after_tick_queue"] = st
            ok("엔진 반영 뒤 queue resolved (처리 항목)", all(x.get("resolved") or x.get("gone") for x in st), st)
            s3 = next(x for x in st if x["q"] == q3)
            ok("先勝ち: 더 이른 기록이 이김 · 내 것 superseded", s3.get("resolved") == "staff.b@example.invalid" and "staff.a@example.invalid" in (s3.get("sup") or []), s3)
            page.click("[data-kind='値の違い']")
            page.click(f"[data-q='{q3}']")
            page.wait_for_timeout(200)
            lost = page.locator(".c01-form .c01-lost").count() == 1
            ok("TOOL 「他の人が先に確認しました」 (엔진 superseded 결과)", lost)
            # v0.2.2: 엔진 반영 뒤 _data — 체크디짓 확인 줄 = 確認済 · info CT_CHECKDIGIT_OVERRIDE (自動OK 아님) · 슬롯 입れ替え 줄 정보
            jk = json.loads((root / "_data" / "jikkyou.json").read_text(encoding="utf-8"))
            rows = {r["container_id"]: r for iv in jk["ivs"] for r in iv["rows"]}
            if q5_cid and q5_cid in rows:
                r5 = rows[q5_cid]
                ok("엔진: 체크디짓 확인 CT = info CT_CHECKDIGIT_OVERRIDE · 自動OK 아님", "CT_CHECKDIGIT_OVERRIDE" in r5["info"] and r5["status"] != "自動OK"
                   and r5["ct"] == "TSTU0000015", {k: r5[k] for k in ("status", "info")})
            else:
                ok("엔진: 체크디짓 확인 CT 반영", False, "대상 줄이 実況表 창 밖")
            if sw:
                ra = next(r for iv in jk["ivs"] if iv["iv_no"] == sw["iv"] for r in iv["rows"] if r["ct"] == sw["a"])
                rb = next(r for iv in jk["ivs"] if iv["iv_no"] == sw["iv"] for r in iv["rows"] if r["ct"] == sw["b"])
                ok("엔진: 슬롯 입れ替え 반영 (칸 서로 바뀜 · 줄 정보 누가·전→후)", ra["slot_guid"] == sw["sb"] and rb["slot_guid"] == sw["sa"]
                   and ra.get("slot_change", {}).get("before") == sw["sa"] and ra["slot_change"]["by"] == "staff.a@example.invalid", ra.get("slot_change"))
            page.screenshot(path=str(out / "e2e_conflict.png"))
            page.click("#tab-main")
            page.wait_for_timeout(200)
            page.screenshot(path=str(out / "e2e_jikkyou_after.png"))
            ok("콘솔 오류 0", not R["console_errors"], R["console_errors"][:3])
            ok("네트워크 = LEENAI_COMMON · 127.0.0.1 만", not R["external"], sorted(set(R["external"]))[:3])
            br.close()
    finally:
        srv.terminate()
    # 되돌림
    from engine.actions import apply as AP  # noqa: E402
    import sqlite3
    c = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True)
    applied = [r[0] for r in c.execute("SELECT action_id FROM human_action WHERE result='applied'")]
    c.close()
    rv = [AP.revert(str(db), str(root), x, today=a.today) for x in applied]
    h1 = judge_hash(str(db))
    R["judge_hash_after_revert"] = h1
    R["reverted"] = sum(1 for x in rv if x.get("reverted"))
    ok("되돌림 뒤 판정 표 해시 = 처리 전", h1 == h0, f"{h0} / {h1} · 되돌림 {R['reverted']}")
    n_ng = sum(1 for x in R["checks"] if not x["ok"])
    (out / "e2e_result.json").write_text(json.dumps(R, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"== {len(R['checks']) - n_ng}/{len(R['checks'])} OK")
    return 1 if n_ng else 0


if __name__ == "__main__":
    sys.exit(main())
