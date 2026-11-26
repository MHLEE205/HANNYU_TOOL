# ✦ Powered by LEENAI Automation System — v0.3.86 (R12Y63 · #408) 통관 B/L 형태 기본값 = 같은 販売契約 의 앞선 송부
"""Playwright · 가명 fixtures · 가짜 Graph · 가짜 D-03 · 가짜 COMPASS (실제 메일 · SharePoint · COMPASS 호출 0). 확인:
 U  pickBl (같은 계약 앞선 송부 있음 / 없음 / 둘 다름 · 바이어 같고 계약 다름 = 안 따라감 · 시험 기록 뺌 · IV 다시 보냄 = 새 기록 · 이 IV 기록 뺌 ·
    계약 못 읽음 · D-00 값 먼저 · 6개월 customs_bl.json 씨앗 안 씀)
 I1 창: COMPASS 販売契約 번호 · 같은 계약 IV GET → 앞선 IV WAY BILL → 기본값 waybill · 이유 「同じ販売契約（…）の前回 … と同じ」 · D-03 에 bl 전달
 I2 창: 같은 계약 기록 없음 (같은 바이어 다른 계약 기록만) → 빈칸 + 빨강 「B/L 形態を選んでください（同じ契約の送付記録がありません）」 · 「新しいバイヤー」 0
 I3 창: 같은 계약 둘 다름 → 빈칸 + 빨강 「同じ契約で B/L 形態が違います」 · 고르면 「担当者が選択」 (#305 · 이번만 바꿈 = 선택 칸 늘 보임)
사용: python tests/test_customs_r12y63.py [--shots 폴더]"""
import argparse
import base64
import json
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import unquote

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_graph as TGR   # noqa: E402
import test_customs as TC  # noqa: E402
import test_customs_r12y42 as T42  # noqa: E402

TOOL = Path(__file__).resolve().parent.parent
RES = {"checks": [], "console_errors": []}
OURS = TC.OURS
ME = TC.ME
IV = TC.IV
SCNO = "TST-SC0001"
P1, P2, P3 = "FAKEIV01", "FAKEIV02", "FAKEIV03"      # 같은 계약의 앞선 IV (가명)
OTHER = "FAKEIV09"                                   # 같은 바이어 · 다른 계약
NEWBUYER = "新しいバイヤー"


def ok(name, cond, detail=""):
    RES["checks"].append({"name": name, "ok": bool(cond), "detail": str(detail)[:300]})
    print(("OK  " if cond else "NG  ") + name + (f" — {detail}" if detail and not cond else ""), flush=True)


def rec(aid, iv, at, bl, test=False, buyer="BUYER-T"):
    return {"action": {"action_id": aid, "action": "customs_sent", "iv": iv, "by": "staff_a@fake", "at": at,
                       "value": {"test": test, "bl": bl, "buyer_id": buyer, "to": [], "cc": []}}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shots")
    a = ap.parse_args()
    shots = Path(a.shots) if a.shots else Path(tempfile.mkdtemp(prefix="c01_r12y63_shots_"))
    shots.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="c01_r12y63_"))
    root = tmp / "HANNYU_TOOL"
    shutil.copytree(TOOL / "fixtures", root)
    staff = json.loads((root / "_masters" / "pol_staff.json").read_text(encoding="utf-8"))
    jp = root / "_data" / "jikkyou.json"
    jd = json.loads(jp.read_text(encoding="utf-8"))
    t4 = next(x for x in jd["ivs"] if x["iv_no"] == IV)
    used = {r["slot_guid"] for r in t4["rows"] if r.get("slot_guid")}
    free = [x["slot_guid"] for x in t4["slots"] if x["slot_guid"] not in used]
    for r in t4["rows"]:
        if not r.get("slot_guid"):
            r["slot_guid"] = free.pop(0)
        r["status"] = "自動OK"; r["engine_status"] = "自動OK"; r["reasons"] = []; r["reason_text"] = ""
    t4["mail_missing"] = []
    t4["compass_input"] = [{"action_id": "acompasst4", "by": ME, "at": "2026-11-08T09:00:00+09:00", "value": {"cells": []}}]
    jp.write_text(json.dumps(jd, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    containers = [{"ct": r["ct"], "seal": r["seal"], "nw": r["n_w"], "tw": r["t_w"], "bales": r["bales"]} for r in t4["rows"]]
    pdfp = tmp / "x.pdf"
    TGR.make_pdf(pdfp)
    pdf_b64 = base64.b64encode(pdfp.read_bytes()).decode()
    port = TGR.free_port()
    srv = subprocess.Popen([sys.executable, str(TOOL / "tools" / "serve_local.py"), "--root", str(TOOL / "fixtures"), "--actions", str(tmp / "local_actions"),
                            "--port", str(port), "--today", "2026-11-08"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    mail = T42.Mail()
    sp = TGR.make_handler(root)
    DVQ = []

    def graph(route, request):
        if "/v1.0/me/" in request.url:
            return mail.handle(route, request)
        return sp(route, request)

    try:
        for _ in range(50):
            try:
                socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
                break
            except OSError:
                time.sleep(0.1)
        with sync_playwright() as p:
            br = p.chromium.launch()
            ctx = br.new_context(viewport={"width": 1440, "height": 1000})
            page = ctx.new_page()
            page.on("console", lambda m: RES["console_errors"].append(m.text) if m.type == "error" else None)
            page.on("pageerror", lambda e: RES["console_errors"].append(f"pageerror {e}"))
            page.on("dialog", lambda d: d.accept())
            page.route("https://graph.microsoft.com/**", graph)
            page.route(f"http://127.0.0.1:{port}/__d03fake.html*", lambda r: r.fulfill(status=200, body=TC.fake_d03(pdf_b64, containers), headers={"Content-Type": "text/html; charset=utf-8"}))

            def J(r, b, st=200):
                return r.fulfill(status=st, body=json.dumps(b), headers={"Content-Type": "application/json"})

            def dvx(r):
                u = unquote(r.request.url)
                DVQ.append(u)
                if "crcf9_container_informations" in u:
                    return J(r, {"value": [{"crcf9_container_no": f"TSTU{i:07d}", "crcf9_type": "45GP", "_crcf9_form_value": "64f45d9f-383c-f011-8c4e-6045bd62e122"} for i in range(3)]})
                if "cr49f_s_is" in u or "_cr49f_fowarder_id_value" in u:
                    return r.fulfill(status=500, body="{}")
                if "cr49f_sale_contracts(SC1)" in u:
                    return J(r, {"_cr49f_buyer_id_value": "BUYER-T", "cr49f_sale_contract_no": SCNO})
                if "cr49f_bookings" in u and "_cr49f_sale_contract_id_value eq SC1" in u:
                    return J(r, {"value": [{"cr49f_invoice_no": x} for x in (P1, P2, P3, IV)]})
                return J(r, {"value": [{"_cr49f_sale_contract_id_value": "SC1"}]})
            page.route("https://orgde512c6f.crm7.dynamics.com/**", dvx)
            page.goto(f"http://127.0.0.1:{port}/")
            page.wait_for_selector("#ln-splash", timeout=20000)
            ok("탭 제목 v0.3.86", page.title() == "LEENAI C-01 搬入票 v0.3.89", page.title())
            page.evaluate(TGR.STUB, staff)
            page.evaluate(f"C01.CUSTOMS.d03Url = '/__d03fake.html'; C01.CUSTOMS.ourDomain = '{OURS}'; C01.CUSTOMS.shareLink = 'off'; localStorage.setItem('c01_ports', JSON.stringify({{port: 'all', ports: []}}));")
            page.evaluate("document.getElementById('ln-splash').style.display='none'; document.getElementById('app').style.display=''; C01.app.start(new C01.sources.Graph())")
            page.wait_for_selector("body[data-c01-ready='1']", timeout=20000)

            def setrecs(xs, seed=None, d00=None):
                page.evaluate("([xs, seed, d00]) => { const A = C01.app._api(); A.S.mine = xs; A.S.actions = []; A.S.customsBl = seed; A.S.customsContractBl = d00; }", [xs, seed, d00])

            def pick(scivs=(P1, P2, P3, IV), sc="SC1", scno=SCNO):
                return page.evaluate("([ct, iv]) => C01.customs._pickBl(ct, iv)", [{"sc": sc, "scNo": scno, "scIvs": list(scivs) if scivs is not None else None}, IV])

            WAY_WHY = f"同じ販売契約（{SCNO}）の前回 {P2} と同じ"
            # U1 같은 계약 앞선 송부 있음 (둘 다 WAY) → 가장 최근 IV 이름
            setrecs([rec("u1a", P1, "2026-11-05T10:00:00+09:00", "WAY"), rec("u1b", P2, "2026-11-06T10:00:00+09:00", "waybill")])
            x = pick()
            ok("U1 같은 계약 앞선 송부 WAY 2 → waybill · 이유 「同じ販売契約（…）の前回 {가장 최근 IV} と同じ」", x["v"] == "waybill" and x["why"] == WAY_WHY and not x.get("red"), x)
            # U2 없음
            setrecs([])
            x = pick()
            ok("U2 같은 계약 기록 없음 → 빈칸 · 빨강 「B/L 形態を選んでください（同じ契約の送付記録がありません）」", x["v"] == "" and x["red"] == "B/L 形態を選んでください（同じ契約の送付記録がありません）"
               and NEWBUYER not in json.dumps(x, ensure_ascii=False), x)
            # U3 둘 다름
            setrecs([rec("u3a", P1, "2026-11-05T10:00:00+09:00", "WAY"), rec("u3b", P2, "2026-11-06T10:00:00+09:00", "ORIG")])
            x = pick()
            ok("U3 같은 계약 안 WAY · ORIG → 빈칸 · 빨강 「同じ契約で B/L 形態が違います」", x["v"] == "" and x["red"] == "同じ契約で B/L 形態が違います", x)
            # U4 바이어 같고 계약 다름 → 안 따라감
            setrecs([rec("u4a", OTHER, "2026-11-06T10:00:00+09:00", "WAY")])
            x = pick()
            ok("U4 같은 바이어 · 다른 계약 IV 의 WAY → 안 따라감 (빈칸 · 기록 없음)", x["v"] == "" and "同じ契約の送付記録がありません" in x["red"], x)
            # U5 시험 기록 뺌
            setrecs([rec("u5a", P1, "2026-11-06T10:00:00+09:00", "WAY", test=True)])
            x = pick()
            ok("U5 시험 송부 (test true) = 안 셈", x["v"] == "", x)
            # U6 같은 IV 다시 보냄 = 그 IV 의 새 기록만 (ORIG → WAY)
            setrecs([rec("u6a", P1, "2026-11-04T10:00:00+09:00", "ORIG"), rec("u6b", P1, "2026-11-06T10:00:00+09:00", "WAY")])
            x = pick()
            ok("U6 같은 IV 두 번 (ORIG → WAY) = 새 기록 WAY 만 → waybill (다름 아님)", x["v"] == "waybill" and P1 in x["why"], x)
            # U7 이 IV 자기 기록 뺌
            setrecs([rec("u7a", IV, "2026-11-06T10:00:00+09:00", "WAY")])
            x = pick()
            ok("U7 지금 IV 자기 송부 기록 = 안 셈", x["v"] == "", x)
            # U8 계약 못 읽음
            setrecs([rec("u8a", P1, "2026-11-06T10:00:00+09:00", "WAY")])
            x = pick(scivs=None)
            ok("U8 같은 계약 IV 를 못 읽음 → 빈칸 · 빨강 「…（販売契約を読めません）」", x["v"] == "" and x["red"] == "B/L 形態を選んでください（販売契約を読めません）", x)
            x = pick(sc="")
            ok("U8 販売契約 없음 → 빈칸", x["v"] == "", x)
            # U9 D-00 값 먼저
            setrecs([rec("u9a", P1, "2026-11-06T10:00:00+09:00", "WAY")], d00={"contracts": {SCNO: {"bl": "ORIG"}}})
            x = pick()
            ok("U9 D-00 계약별 값 (있으면) 먼저 → original · 이유 「D-00 の契約の値（…）」", x["v"] == "original" and x["why"] == f"D-00 の契約の値（{SCNO}）", x)
            setrecs([rec("u9b", P1, "2026-11-06T10:00:00+09:00", "WAY")], d00={"contracts": {"OTHER-SC": {"bl": "ORIG"}}})
            x = pick()
            ok("U9 D-00 에 이 계약 없음 → Part 1 (같은 계약 송부)", x["v"] == "waybill", x)
            # U10 6개월 씨앗 안 씀
            setrecs([], seed={"buyers": {"BUYER-T": [{"at": "2026-11-01", "iv": OTHER, "bl": "WAY", "cons": "X"}]}})
            x = pick()
            ok("U10 customs_bl.json (바이어 6개월 씨앗) 있어도 안 씀 → 빈칸", x["v"] == "", x)

            def openw():
                mail.reset(s1=True)
                DVQ.clear()
                page.evaluate("() => { const r = document.querySelector('.c01-d03auto, #c01-d03auto'); }")
                page.locator(f'tbody[data-iv="{IV}"] [data-csend]').click()
                page.wait_for_function("() => document.querySelector('.c01-customs') && !document.querySelector('.c01-customs .c01-cstep')", timeout=20000)

            def close():
                if page.locator(".c01-customs [data-close]").count():
                    page.click(".c01-customs [data-close]")
                    page.wait_for_timeout(200)

            def lastrun():
                return page.evaluate("() => { const f = document.getElementById('c01-d03auto'); const r = f && f.contentWindow.__runs; return r && r.length ? r[r.length - 1] : null; }")

            # I1 창 · 같은 계약 앞선 송부 WAY
            setrecs([rec("i1a", P2, "2026-11-06T10:00:00+09:00", "WAY"), rec("i1o", OTHER, "2026-11-07T10:00:00+09:00", "ORIG")])
            openw()
            s = page.evaluate("C01.customs._blState()")
            cell = page.locator("[data-cblwhy]").inner_text()
            ok("I1 COMPASS GET = 販売契約 번호 (cr49f_sale_contract_no) + 같은 계약 IV (bookings · sale_contract 거르기) · 모두 GET",
               any("cr49f_sale_contracts(SC1)" in u and "cr49f_sale_contract_no" in u for u in DVQ) and any("cr49f_bookings" in u and "_cr49f_sale_contract_id_value eq SC1" in u and "cr49f_invoice_no" in u for u in DVQ), DVQ)
            ok("I1 기본값 waybill · 칸 이유 「同じ販売契約（…）の前回 … と同じ」 · 빨강 아님", s["bl"] == "waybill" and page.locator("[data-cbl]").input_value() == "waybill"
               and cell == WAY_WHY and page.locator("[data-cblwhy].c01-cr").count() == 0, [s, cell])
            r = lastrun()
            ok("I1 D-03 에 bl waybill · blWhy 전달", r and r.get("bl") == "waybill" and r.get("blWhy") == WAY_WHY, r)
            ok("I1 「新しいバイヤー」 0", NEWBUYER not in page.locator(".c01-customs").inner_text())
            page.screenshot(path=str(shots / "i1_same_contract.png"), full_page=False)
            close()
            # I2 같은 바이어 다른 계약 기록만
            setrecs([rec("i2o", OTHER, "2026-11-07T10:00:00+09:00", "WAY")])
            openw()
            s = page.evaluate("C01.customs._blState()")
            cell = page.locator("[data-cblwhy]").inner_text()
            ok("I2 같은 계약 기록 없음 → 빈칸 · 빨강 「B/L 形態を選んでください（同じ契約の送付記録がありません）」", s["bl"] == "" and page.locator("[data-cbl]").input_value() == ""
               and cell == "B/L 形態を選んでください（同じ契約の送付記録がありません）" and page.locator("[data-cblwhy].c01-cr").count() == 1, [s, cell])
            ok("I2 「新しいバイヤー」 0 · 送信 막힘 「B/L 形態を選んでください」", NEWBUYER not in page.locator(".c01-customs").inner_text()
               and "B/L 形態を選んでください" in (page.evaluate("C01.customs._blockers()") or []), page.evaluate("C01.customs._blockers()"))
            page.screenshot(path=str(shots / "i2_no_record.png"), full_page=False)
            close()
            # I3 둘 다름 → 빈칸 · 빨강 → 고름 = 担当者が選択
            setrecs([rec("i3a", P1, "2026-11-05T10:00:00+09:00", "WAY"), rec("i3b", P3, "2026-11-06T10:00:00+09:00", "ORIG")])
            openw()
            cell = page.locator("[data-cblwhy]").inner_text()
            ok("I3 같은 계약 둘 다름 → 빈칸 · 빨강 「同じ契約で B/L 形態が違います」", page.locator("[data-cbl]").input_value() == "" and cell == "同じ契約で B/L 形態が違います"
               and page.locator("[data-cblwhy].c01-cr").count() == 1, cell)
            page.select_option("[data-cbl]", "original")
            page.wait_for_function("() => !document.querySelector('.c01-customs .c01-cstep')", timeout=15000)
            cell = page.locator("[data-cblwhy]").inner_text()
            r = lastrun()
            ok("I3 직원이 고름 → original · 「担当者が選択」 · D-03 다시 (bl original)", cell == "担当者が選択" and r and r.get("bl") == "original", [cell, r])
            close()
            # I4 앞선 WAY 인데 이번만 ORIG (#305) — 선택 칸 늘 보임 · 바꾸면 그대로
            setrecs([rec("i4a", P1, "2026-11-06T10:00:00+09:00", "WAY")])
            openw()
            vis = page.locator("[data-cbl]").is_visible() and page.locator("[data-cbl]").is_enabled()
            page.select_option("[data-cbl]", "original")
            page.wait_for_function("() => !document.querySelector('.c01-customs .c01-cstep')", timeout=15000)
            r = lastrun()
            ok("I4 (#305) 기본값 있어도 선택 칸 보임 · 바꿈 → original 로 D-03", vis and r and r.get("bl") == "original", [vis, r])
            close()
            src = (TOOL / "js" / "customs.js").read_text(encoding="utf-8")
            ok("S 송부 기록에 sc_id · sc_no · bl_why 남김 · 6개월 문구 0", "sc_no: st.scNo" in src and "sc_id: st.sc" in src and "bl_why:" in src
               and NEWBUYER not in src and "'6 か月の実績 = '" not in src and "customsBl." not in src)
            errs = [e for e in RES["console_errors"] if "favicon" not in e and "404" not in e and not (("500" in e or "403" in e) and "Failed to load resource" in e)]
            ok("콘솔 오류 0", not errs, errs[:3])
            br.close()
    finally:
        srv.terminate()
    n_ng = sum(1 for c in RES["checks"] if not c["ok"])
    print(json.dumps({"checks": len(RES["checks"]), "ng": n_ng, "shots": str(shots)}, ensure_ascii=False))
    sys.exit(1 if n_ng else 0)


if __name__ == "__main__":
    main()
