# ✦ Powered by LEENAI Automation System — v0.3.84 (R12Y59 · #404) 통관 송부 宛先 = COMPASS 乙仲 과 대조
"""Playwright · 가명 fixtures · 가짜 Graph · 가짜 D-03 · 가짜 COMPASS (실제 메일 · SharePoint · COMPASS 호출 0). 확인:
 U  matchBroker (이름 같음 · 株式会社 · 전각 · 「/」 별명 · 모르는 이름 · COMPASS 주소만)
 (v0.3.85 · R12Y60 · #407: 道 3 제안 없앰 — ① 없음 = 직접 입력 manual · 칸 비움)
 A  乙仲 ヴェリオス · 같은 港 최근 ① = LOTOS (NJJ 꼴) → 제안 0 · 빨강 「新規通関依頼メールが見つかりません」 + 乙仲 이름만 · ヴェリオス 입력 → 추가 서류
 A2 같은 港 송부 기록이 있어도 제안 0 · 다른 IV 기록의 宛名 안 씀
 B  乙仲 LOTOS → 제안 0 · C 표 주소 0 → manual · 막힘
 D  乙仲 빈칸 · E 이름 못 읽음 (403) · F 표에 없는 이름 → 노랑 한 줄 · manual
 G  道 1 · 宛先 テスト倉庫 · 乙仲 LOTOS → 빨강 「COMPASS の乙仲（LOTOS）と宛先（テスト倉庫）が違います」 + 확인 체크 전 막힘 · 체크 → 풀림 · 기록 broker_compass mismatch
 H  道 1 · 乙仲 = 宛先 → 회색 · 확인 체크 없음 · I 직접 입력 받는 사람 LOTOS (乙仲 ヴェリオス) → 빨강
사용: python tests/test_customs_r12y59.py [--shots 폴더]"""
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
VERI = "veri.x@veri.invalid"
LOT = "broker.l@lotos.invalid"
REQ = {"kind": "customs_broker_req", "version": "v1.0", "base": ["IV", "PL", "SI"], "unknown": "要確認",
       "brokers": [{"name": "LOTOS", "ports": ["KOBE"], "extra": []}, {"name": "ヴェリオス", "ports": ["KOBE"], "extra": ["PHOTO", "搬入票"]},
                   {"name": "テスト倉庫", "ports": ["TOKYO"], "extra": ["PHOTO", "搬入票"]}, {"name": "日本テスト通運 Eastカンパニー / 日本テスト通運 水島支店", "ports": [], "extra": ["PHOTO"]}],
       "domains": {"broker.invalid": {"broker": "テスト倉庫", "extra": ["PHOTO", "搬入票"]}, "lotos.invalid": {"broker": "LOTOS", "extra": []},
                   "nts.invalid": {"broker": "日本テスト通運 Eastカンパニー / 日本テスト通運 水島支店", "extra": ["PHOTO"]}},
       "addrs": {VERI: {"broker": "ヴェリオス", "extra": ["PHOTO", "搬入票"]}}}
BP = {"kind": "customs_s1", "built_at": "2026-11-08T09:00:00+09:00", "ivs": {}, "by_pol": {"KOBE": {"at": "2026-11-04T10:00:00", "staff": "staff.c@" + OURS, "n": 4,
      "to": [{"a": LOT, "n": "LOTOS L"}], "cc": [{"a": "staff.c@" + OURS, "n": "STAFF C"}]}}}


def ok(name, cond, detail=""):
    RES["checks"].append({"name": name, "ok": bool(cond), "detail": str(detail)[:300]})
    print(("OK  " if cond else "NG  ") + name + (f" — {detail}" if detail and not cond else ""), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shots")
    a = ap.parse_args()
    shots = Path(a.shots) if a.shots else Path(tempfile.mkdtemp(prefix="c01_r12y59_shots_"))
    shots.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="c01_r12y59_"))
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
    BC = {"mode": "veri"}
    BCQ = []

    def graph(route, request):
        if "/v1.0/me/" in request.url:
            return mail.handle(route, request)
        return sp(route, request)

    def actions(kind):
        return [x for x in (json.loads(f.read_text(encoding="utf-8")) for f in (root / "_actions").rglob("*.json")) if x.get("action") == kind]

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
            page.on("response", lambda rs: RES.setdefault("bad", []).append(f"{rs.status} {rs.request.method} {rs.url[:90]}") if rs.status == 400 else None)
            page.route("https://graph.microsoft.com/**", graph)
            page.route(f"http://127.0.0.1:{port}/__d03fake.html*", lambda r: r.fulfill(status=200, body=TC.fake_d03(pdf_b64, containers), headers={"Content-Type": "text/html; charset=utf-8"}))

            def J(r, b, st=200):
                return r.fulfill(status=st, body=json.dumps(b), headers={"Content-Type": "application/json"})

            def dvx(r):
                u = unquote(r.request.url)
                if "crcf9_container_informations" in u:
                    return J(r, {"value": [{"crcf9_container_no": f"TSTU{i:07d}", "crcf9_type": "45GP", "_crcf9_form_value": "64f45d9f-383c-f011-8c4e-6045bd62e122"} for i in range(3)]})
                if "cr49f_s_is" in u:
                    return r.fulfill(status=500, body="{}")
                if "_cr49f_fowarder_id_value" in u:          # v0.3.84: 乙仲 (가명)
                    BCQ.append(u)
                    m = BC["mode"]
                    if "$expand=cr49f_fowarder_id(" in u and m == "fail":
                        return r.fulfill(status=403, body="{}")
                    if m == "blank":
                        return J(r, {"value": [{"_cr49f_fowarder_id_value": None}]})
                    if "$expand" not in u:
                        return J(r, {"value": [{"_cr49f_fowarder_id_value": "G-BC"}]})
                    nm = {"veri": "株式会社ヴェリオス", "lotos": "ＬＯＴＯＳ", "test": "テスト倉庫", "unknown": "ABC通関"}[m]
                    return J(r, {"value": [{"_cr49f_fowarder_id_value": "G-BC", "cr49f_fowarder_id": {"crcf9_forwarder": nm, "crcf9_forwarder_to_email": None}}]})
                return J(r, {"value": [{"_cr49f_sale_contract_id_value": "SC1"}], "_cr49f_buyer_id_value": "BUYER-T"})
            page.route("https://orgde512c6f.crm7.dynamics.com/**", dvx)
            page.goto(f"http://127.0.0.1:{port}/")
            page.wait_for_selector("#ln-splash", timeout=20000)
            ok("탭 제목 v0.3.85", page.title() == "LEENAI C-01 搬入票 v0.3.87", page.title())
            page.evaluate(TGR.STUB, staff)
            page.evaluate(f"C01.CUSTOMS.d03Url = '/__d03fake.html'; C01.CUSTOMS.ourDomain = '{OURS}'; C01.CUSTOMS.shareLink = 'off'; localStorage.setItem('c01_ports', JSON.stringify({{port: 'all', ports: []}}));")
            page.evaluate("document.getElementById('ln-splash').style.display='none'; document.getElementById('app').style.display=''; C01.app.start(new C01.sources.Graph())")
            page.wait_for_selector("body[data-c01-ready='1']", timeout=20000)
            page.evaluate("(x) => { C01.app._api().S.customsReq = x; }", REQ)

            # U matchBroker
            U = [("ヴェリオス", None, ["ヴェリオス"]), ("株式会社ヴェリオス", None, ["ヴェリオス"]), ("ＬＯＴＯＳ", None, ["LOTOS"]), ("LOTOS (株)", None, ["LOTOS"]),
                 ("日本テスト通運", None, ["日本テスト通運 Eastカンパニー / 日本テスト通運 水島支店"]), ("ABC通関", None, []), ("", None, []),
                 ("ABC通関", "x@lotos.invalid; " + VERI, ["LOTOS", "ヴェリオス"])]
            for nm, em, want in U:
                got = page.evaluate("([rq, bc]) => C01.customs._matchBroker(rq, bc)", [REQ, {"state": "read", "name": nm, "email": em or ""}])
                ok(f"U matchBroker {nm!r} {'+주소' if em else ''} → {want}", got == want, got)
            ok("U 빈칸 · 못 읽음 = []", page.evaluate("([rq]) => C01.customs._matchBroker(rq, {state: 'blank'}).length + C01.customs._matchBroker(rq, {state: 'noname'}).length", [REQ]) == 0)

            def openw(s1=False, conv=None):
                mail.reset(s1=s1)
                mail.conv = conv
                BCQ.clear()
                page.locator(f'tbody[data-iv="{IV}"] [data-csend]').click()
                page.wait_for_function("() => document.querySelector('.c01-customs') && !document.querySelector('.c01-customs .c01-cstep')", timeout=20000)

            def close():
                if page.locator(".c01-customs [data-close]").count():
                    page.click(".c01-customs [data-close]")
                    page.wait_for_timeout(200)

            def bl():
                page.select_option("[data-cbl]", "waybill")
                page.wait_for_function("() => !document.querySelector('.c01-customs .c01-cstep')", timeout=15000)
                if page.locator("[data-cack]").count():
                    page.check("[data-cack]")

            def info():
                return page.evaluate("C01.customs._bc()")

            def why():
                return page.evaluate("C01.customs._blockers()") or []
            ACK = "宛先を確認しました"
            page.evaluate("(x) => { C01.app._api().S.customsS1 = x; }", BP)

            # A NJJ 꼴 (v0.3.85 · R12Y60 · #407): ① 없음 = 제안 0 → 빨강 「新規通関依頼メールが見つかりません」 + 칸 비움 · 乙仲 이름만
            BC["mode"] = "veri"
            openw()
            x = info()
            body = page.locator("[data-cbody]").input_value() if page.locator("[data-cbody]").count() else ""
            ok("A 乙仲 COMPASS GET = $expand cr49f_fowarder_id (crcf9_forwarder · crcf9_forwarder_to_email) · 1 번", len(BCQ) == 1 and "crcf9_forwarder,crcf9_forwarder_to_email" in BCQ[0], BCQ)
            ok("A 乙仲 = ヴェリオス (표 이름)", x["now"]["state"] == "read" and x["now"]["brokers"] == ["ヴェリオス"], x["now"])
            ok("A 같은 港 최근 ① (LOTOS) · 표 주소 제안 0 → 길 manual · To · CC 비움", x["prop"] and x["prop"]["src"] == "manual" and page.locator("[data-cedit='to']").input_value() == ""
               and page.locator("[data-cedit='cc']").input_value() == "", [x["prop"], page.locator("[data-cedit='to']").input_value()])
            ok("A 빨강 「新規通関依頼メールが見つかりません — 担当（宛先）が分かりません。宛先と宛名を入力してください」 + 乙仲 이름만", page.locator("[data-cmanual].c01-cr").count() == 1
               and "新規通関依頼メールが見つかりません — 担当（宛先）が分かりません。宛先と宛名を入力してください" in page.locator("[data-cmanual]").inner_text()
               and "ヴェリオス" in page.locator("[data-cmanual]").inner_text() and "@" not in page.locator("[data-cmanual]").inner_text(), page.locator("[data-cmanual]").all_inner_texts())
            ok("A 본문 · 宛名 에 LOTOS 0 · 宛名 = 입력 칸 표시 (（通関業者の会社名）)", "LOTOS" not in body and "（通関業者の会社名）" in body, body[:120])
            bl()
            ok("A 칸 비움 = 막힘 「宛先がありません」", any(w == "宛先がありません" for w in why()), why())
            page.screenshot(path=str(shots / "a_njj_manual.png"), full_page=False)
            # I 받는 사람을 LOTOS 로 넣음 → 빨강
            page.fill("[data-cedit='to']", LOT)
            page.locator("[data-cedit='to']").dispatch_event("change")
            ok("I 직접 입력 To 를 LOTOS 로 → 빨강 「COMPASS の乙仲（株式会社ヴェリオス）と宛先（LOTOS）が違います」", page.locator("[data-cbc='mismatch'].c01-cr").count() == 1
               and "COMPASS の乙仲（株式会社ヴェリオス）と宛先（LOTOS）が違います" in page.locator("[data-cbc]").inner_text(), page.locator("[data-cbc]").all_inner_texts())
            page.fill("[data-cedit='to']", VERI)
            page.locator("[data-cedit='to']").dispatch_event("change")
            rq = page.evaluate("C01.customs._req()")
            ok("A ヴェリオス 주소 입력 → 회색 일치 · 추가 서류 写真 · 搬入票", page.locator("[data-cbc='ok']").count() == 1 and rq["extra"] == ["PHOTO", "搬入票"] and rq["brokers"] == ["ヴェリオス"], rq)
            ok("A 확인 체크 전 막힘", any(ACK in w for w in why()), why())
            close()
            # A2 기록: 같은 港 · 같은 바이어 LOTOS · 다른 바이어 ヴェリオス 송부 기록이 있어도 제안 0
            page.evaluate('''([lot, veri]) => { const A = C01.app._api(); const o = A.S.jik.ivs.find(x => x.iv_no === 'TST2611-02'); o.pol = 'KOBE';
                const r = (id, at, b, to) => ({ action: { action_id: id, action: 'customs_sent', iv: 'TST2611-02', by: 'staff_a@fake', at: at,
                  value: { test: false, buyer_id: b, to: [to], cc: [], broker_dom: to.split('@')[1], broker_line: 'OTHER IV CO', broker_person: 'OTHERPERSON' } } });
                A.S.mine = (A.S.mine || []).concat([r('cs-l', '2026-11-07T10:00:00+09:00', 'BUYER-T', lot), r('cs-v', '2026-11-06T10:00:00+09:00', 'BUYER-X', veri)]); }''', [LOT, VERI])
            openw()
            x = info()
            ok("A2 같은 港 송부 기록 (같은 바이어 · 다른 바이어) 이 있어도 제안 0 · 칸 비움", x["prop"]["src"] == "manual" and page.locator("[data-cprop]").count() == 0
               and page.locator("[data-cedit='to']").input_value() == "", [x["prop"], page.locator("[data-cedit='to']").input_value()])
            page.fill("[data-cedit='to']", VERI)
            page.locator("[data-cedit='to']").dispatch_event("change")
            page.wait_for_timeout(200)
            body = page.locator("[data-cbody]").input_value() if page.locator("[data-cbody]").count() else ""
            ok("A2 宛名 = 다른 IV 의 송부 기록 안 씀 (OTHER IV CO · OTHERPERSON 0)", "OTHER IV CO" not in body and "OTHERPERSON" not in body, body[:120])
            close()
            # B 乙仲 LOTOS → 그래도 제안 0
            BC["mode"] = "lotos"
            openw()
            x = info()
            ok("B 乙仲 LOTOS (전각) · 같은 港 LOTOS 기록 있어도 제안 0 (manual · 칸 비움)", x["prop"]["src"] == "manual" and page.locator("[data-cedit='to']").input_value() == ""
               and "ＬＯＴＯＳ" in page.locator("[data-cmanual]").inner_text(), [x["prop"], page.locator("[data-cmanual]").all_inner_texts()])
            close()
            page.evaluate("() => { const A = C01.app._api(); A.S.mine = (A.S.mine || []).filter(m => ['cs-l', 'cs-v'].indexOf(m.action.action_id) < 0); }")
            # C 표 주소 0 → 같은 manual (막음 = 칸 비움)
            BC["mode"] = "veri"
            page.evaluate("(x) => { C01.app._api().S.customsReq = x; }", dict(REQ, addrs={}))
            openw()
            x = info()
            ok("C 乙仲 ヴェリオス · 표 주소 0 → manual · 「新規通関依頼メールが見つかりません」", x["prop"]["src"] == "manual" and page.locator("[data-cmanual]").count() == 1, page.locator(".c01-customs").inner_text()[:200])
            ok("C 送信 · 下書き 막힘 (宛先がありません)", page.locator("[data-csendgo]").is_disabled() and any("宛先がありません" in w for w in why()), why())
            close()
            page.evaluate("(x) => { C01.app._api().S.customsReq = x; }", REQ)
            # D · E · F
            for m, sel in (("blank", "blank"), ("fail", "noname"), ("unknown", "unknown")):
                BC["mode"] = m
                openw()
                x = info()
                ok(f"{ {'blank': 'D 乙仲 빈칸', 'fail': 'E 이름 못 읽음 (403 → 번호만)', 'unknown': 'F 표에 없는 이름'}[m]} → 노랑 한 줄 · manual (칸 비움) · 빨강 0",
                   page.locator(f"[data-cbc='{sel}'].c01-cy").count() == 1 and x["prop"]["src"] == "manual" and page.locator("[data-cbc='mismatch']").count() == 0
                   and page.locator("[data-cedit='to']").input_value() == "",
                   [x["now"], x["prop"] and x["prop"]["src"], page.locator("[data-cbc]").all_inner_texts()])
                if m == "fail":
                    ok("E 403 뒤 $expand 없이 다시 1 번", len(BCQ) == 2 and "$expand" not in BCQ[1], BCQ)
                close()
            page.evaluate("() => { C01.app._api().S.customsS1 = null; }")
            # G 道 1 · 宛先 テスト倉庫 · 乙仲 LOTOS
            BC["mode"] = "lotos"
            openw(s1=True)
            ok("G 道 1 (s1_reply)", page.evaluate("C01.customs._route()") == "s1_reply")
            ok("G 빨강 「COMPASS の乙仲（ＬＯＴＯＳ）と宛先（テスト倉庫）が違います」", page.locator("[data-cbc='mismatch'].c01-cr").count() == 1
               and "COMPASS の乙仲（ＬＯＴＯＳ）と宛先（テスト倉庫）が違います" in page.locator("[data-cbc]").inner_text(), page.locator("[data-cbc]").all_inner_texts())
            bl()
            TC.fill_body(page)
            page.fill("[data-cbody]", page.locator("[data-cbody]").input_value().replace("（担当者名）", "BROKERA"))
            page.wait_for_timeout(100)
            w = why()
            ok("G 「宛先を確認しました」 체크 전 막힘 (道 1 인데도)", page.locator("[data-cackto]").count() == 1 and any(ACK in x for x in w), w)
            page.screenshot(path=str(shots / "g_route1_mismatch.png"), full_page=False)
            page.check("[data-cackto]")
            w = [x for x in why() if ACK in x]
            ok("G 체크 → 그 막힘 풀림", not w, why())
            page.click("[data-cdraftgo]")
            page.wait_for_selector("[data-cdraftok]", timeout=30000)
            cd = actions("customs_draft")
            bcr = (cd[-1]["value"].get("broker_compass") if cd else None) or {}
            ok("G 下書き 기록 broker_compass = read · ＬＯＴＯＳ · [LOTOS] · mismatch · 宛先 [テスト倉庫]", bcr.get("state") == "read" and bcr.get("name") == "ＬＯＴＯＳ" and bcr.get("brokers") == ["LOTOS"]
               and bcr.get("mismatch") is True and bcr.get("to_brokers") == ["テスト倉庫"], bcr)
            close()
            page.evaluate("(iv) => { const A = C01.app._api(); A.S.mine = []; delete A.ivById(iv).customs_draft; A.render(); }", IV)
            for f in (root / "_actions").rglob("*.json"):
                f.unlink()
            # H 道 1 · 乙仲 = 宛先
            BC["mode"] = "test"
            openw(s1=True)
            bl()
            ok("H 乙仲 テスト倉庫 = 宛先 → 회색 일치 · 빨강 0 · 확인 체크 없음 · ACK 막힘 0", page.locator("[data-cbc='ok']").count() == 1 and page.locator("[data-cbc='mismatch']").count() == 0
               and page.locator("[data-cackto]").count() == 0 and not any(ACK in x for x in why()), [page.locator("[data-cbc]").all_inner_texts(), why()])
            close()
            errs = [e for e in RES["console_errors"] if "favicon" not in e and "404" not in e and not (("500" in e or "403" in e) and "Failed to load resource" in e)]
            ok("콘솔 오류 0", not errs, [errs[:3], RES.get("bad")])
            br.close()
    finally:
        srv.terminate()
    n_ng = sum(1 for c in RES["checks"] if not c["ok"])
    print(json.dumps({"checks": len(RES["checks"]), "ng": n_ng, "shots": str(shots)}, ensure_ascii=False))
    sys.exit(1 if n_ng else 0)


if __name__ == "__main__":
    main()
