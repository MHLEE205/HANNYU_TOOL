# ✦ Powered by LEENAI Automation System — v0.3.87 (R12Y64B) 통관 송부 기록에 S/I 기본값 · 후보 수 · 이유 칸 (기록만 · 화면 바꿈 0)
"""Playwright · 가명 fixtures · 가짜 Graph · 가짜 D-03 · 가짜 COMPASS (실제 메일 · SharePoint · COMPASS 호출 0). 확인:
 U  siRec / siWhyCode (기본값 그대로 = si_changed false · 직원이 바꿈 = true · staff_changed · 값 없음 = null · 후보 1 = only_one ·
    최종번호 = last_no · 三国間 = three_party · 残る S/I なし = no_rest · si_avail 없음 = si_avail_n null)
 I1 창 → 기본값 그대로 시험 송부 → 기록 si_default_iv 2 · si_default_si 1 · si_avail_n 2 · si_why last_no · si_changed false
 I2 창 → 직원이 S/I (IV·PL) ① 로 바꿈 → 송부 → 기록 si_default_iv 2 (처음 기본값) · picks.ivSino 1 · si_why staff_changed · si_changed true
 S  화면 · 메일 · 받는 사람 · 첨부 = 0.3.86 과 같음 (화면 글 · 송부 메일 PATCH 비교 · 기록 칸만 늘어남)
사용: python tests/test_customs_r12y64b.py [--shots 폴더]"""
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
P1 = "FAKEIV01"
NEWKEYS = ["si_default_iv", "si_default_si", "si_avail_n", "si_why", "si_changed"]


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
    shots = Path(a.shots) if a.shots else Path(tempfile.mkdtemp(prefix="c01_r12y64b_shots_"))
    shots.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="c01_r12y64b_"))
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
                if "crcf9_container_informations" in u:
                    return J(r, {"value": [{"crcf9_container_no": f"TSTU{i:07d}", "crcf9_type": "45GP", "_crcf9_form_value": "64f45d9f-383c-f011-8c4e-6045bd62e122"} for i in range(3)]})
                if "cr49f_s_is" in u or "_cr49f_fowarder_id_value" in u:
                    return r.fulfill(status=500, body="{}")
                if "cr49f_sale_contracts(SC1)" in u:
                    return J(r, {"_cr49f_buyer_id_value": "BUYER-T", "cr49f_sale_contract_no": SCNO})
                if "cr49f_bookings" in u and "_cr49f_sale_contract_id_value eq SC1" in u:
                    return J(r, {"value": [{"cr49f_invoice_no": x} for x in (P1, IV)]})
                return J(r, {"value": [{"_cr49f_sale_contract_id_value": "SC1"}]})
            page.route("https://orgde512c6f.crm7.dynamics.com/**", dvx)
            page.goto(f"http://127.0.0.1:{port}/")
            page.wait_for_selector("#ln-splash", timeout=20000)
            ok("탭 제목 v0.3.87", page.title() == "LEENAI C-01 搬入票 v0.3.92", page.title())
            page.evaluate(TGR.STUB, staff)
            page.evaluate(f"C01.CUSTOMS.d03Url = '/__d03fake.html'; C01.CUSTOMS.ourDomain = '{OURS}'; C01.CUSTOMS.shareLink = 'off'; localStorage.setItem('c01_ports', JSON.stringify({{port: 'all', ports: []}}));")
            page.evaluate("document.getElementById('ln-splash').style.display='none'; document.getElementById('app').style.display=''; C01.app.start(new C01.sources.Graph())")
            page.wait_for_selector("body[data-c01-ready='1']", timeout=20000)

            # ── U: siRec / siWhyCode ──
            def sr(r, s):
                return page.evaluate("([r, s]) => C01.customs._siRec(r, s)", [r, s])

            def R(iv, si, avail, ivwhy="最終番号 (S/I②)"):
                return {"ok": True, "picks": {"ivSino": {"v": iv, "why": ivwhy}, "siSino": {"v": si, "why": "S/I①"}}, "si_avail": avail}
            D = {"siDefIv": {"v": 2, "why": "最終番号 (S/I②)"}, "siDefSi": {"v": 1, "why": "S/I①"}}
            x = sr(R(2, 1, [1, 2]), D)
            ok("U1 기본값 그대로 → si_changed false · si_why last_no · si_avail_n 2 · 기본 2/1",
               x == {"si_default_iv": 2, "si_default_si": 1, "si_avail_n": 2, "si_why": "last_no", "si_changed": False}, x)
            x = sr(R(1, 1, [1, 2], "担当者が選択"), D)
            ok("U2 직원이 IV·PL S/I 바꿈 (2 → 1) → si_changed true · si_why staff_changed · 기본값은 처음 값 2",
               x["si_changed"] is True and x["si_why"] == "staff_changed" and x["si_default_iv"] == 2, x)
            x = sr(R(2, 2, [1, 2]), D)
            ok("U3 직원이 SI S/I 만 바꿈 (1 → 2) → si_changed true", x["si_changed"] is True and x["si_why"] == "staff_changed", x)
            x = sr(R(2, 1, [1, 2]), {})
            ok("U4 기본값 모름 (손에 없음) → si_default_* · si_why · si_changed = null (만들지 않음)",
               x["si_default_iv"] is None and x["si_default_si"] is None and x["si_why"] is None and x["si_changed"] is None and x["si_avail_n"] == 2, x)
            x = sr({"ok": True, "picks": {"ivSino": {"v": 1, "why": "最終番号 (S/I①)"}, "siSino": {"v": 1, "why": "S/I①"}}}, D)
            ok("U5 si_avail 없음 → si_avail_n null", x["si_avail_n"] is None, x)
            x = sr(None, None)
            ok("U6 D-03 결과 없음 → 모두 null", all(x[k] is None for k in NEWKEYS), x)
            D1 = {"siDefIv": {"v": 1, "why": "最終番号 (S/I①)"}, "siDefSi": {"v": 1, "why": "S/I①"}}
            x = sr(R(1, 1, [1], "最終番号 (S/I①)"), D1)
            ok("U7 후보 1 개 → only_one", x["si_why"] == "only_one" and x["si_avail_n"] == 1 and x["si_changed"] is False, x)
            wc = page.evaluate("""() => [C01.customs._siWhyCode('三国間貿易の疑い (S/I 3 つ以上 · 銀行以外の Consignee 2 社以上)', 3),
                C01.customs._siWhyCode('残る S/I がありません (XX · 仲介・物流の Notify を除くと 0)', 2), C01.customs._siWhyCode('S/I がありません', 0),
                C01.customs._siWhyCode('', 2), C01.customs._siWhyCode('最終番号 (S/I③)', 3), C01.customs._siWhyCode('ほか', 2)]""")
            ok("U8 이유 코드 = three_party · no_rest · none · none · last_no · other", wc == ["three_party", "no_rest", "none", "none", "last_no", "other"], wc)

            def setrecs(xs):
                page.evaluate("(xs) => { const A = C01.app._api(); A.S.mine = xs; A.S.actions = []; A.S.customsBl = null; A.S.customsContractBl = null; }", xs)

            def openw():
                mail.reset(s1=True)
                page.locator(f'tbody[data-iv="{IV}"] [data-csend]').click()
                page.wait_for_function("() => document.querySelector('.c01-customs') && !document.querySelector('.c01-customs .c01-cstep')", timeout=20000)

            def runs():
                return page.evaluate("() => { const f = document.getElementById('c01-d03auto'); return (f && f.contentWindow.__runs) || []; }")

            def send():
                if page.locator("[data-cack]").count() and not page.locator("[data-cack]").is_checked():
                    page.check("[data-cack]")
                TC.fill_body(page)
                ok("  送信 가능", page.locator("[data-csendgo]").is_enabled(), page.evaluate("C01.customs._blockers()"))
                page.click("[data-csendgo]")
                page.wait_for_function("() => !document.querySelector('.c01-customs')", timeout=15000)
                page.wait_for_timeout(500)

            def sent_recs():
                cs = [json.loads(f.read_text(encoding="utf-8")) for f in (root / "_actions").rglob("*.json")]
                cs = [x for x in cs if x.get("action") == "customs_sent"]
                return sorted(cs, key=lambda x: str(x.get("at", "")))

            # I1 기본값 그대로 송부 (B/L 은 같은 계약 앞선 송부 WAY 로 채워짐)
            setrecs([rec("i1a", P1, "2026-11-06T10:00:00+09:00", "WAY")])
            openw()
            d = page.evaluate("C01.customs._siDef()")
            ok("I1 창 열림 → D-03 기본값 기억 (IV·PL 2 · SI 1)", d and d["iv"]["v"] == 2 and d["si"]["v"] == 1, d)
            tab = page.locator(".c01-ctab:has(th:text('POD'))").inner_text()
            ok("I1 화면 = 0.3.86 과 같은 표 (S/I (IV·PL) · S/I (SI) · POD · FOB 運賃 · B/L 形態 · 이유 글 그대로 · 새 칸 글 0)",
               all(k in tab for k in ("S/I (IV·PL)", "S/I (SI)", "POD", "FOB 運賃", "B/L 形態", "最終番号 (S/I②)", "S/I①"))
               and not any(k in page.locator(".c01-customs").inner_text() for k in NEWKEYS + ["last_no", "staff_changed"]), tab)
            page.screenshot(path=str(shots / "i1_default.png"), full_page=False)
            n_r = len(runs())
            send()
            cs = sent_recs()
            v = cs[-1]["value"] if cs else {}
            ok("I1 기록 si_default_iv 2 · si_default_si 1 · si_avail_n 2 · si_why last_no · si_changed false",
               len(cs) == 1 and v.get("si_default_iv") == 2 and v.get("si_default_si") == 1 and v.get("si_avail_n") == 2 and v.get("si_why") == "last_no" and v.get("si_changed") is False, v)
            ok("I1 picks 그대로 (ivSino 2 · siSino 1) · bl waybill · D-03 다시 부름 0", v.get("picks", {}).get("ivSino") == 2 and v.get("picks", {}).get("siSino") == 1
               and v.get("bl") == "waybill" and len(runs()) == n_r, [v.get("picks"), v.get("bl")])
            P = mail.patch or {}
            to1 = [x["emailAddress"]["address"] for x in P.get("toRecipients", [])]
            cc1 = [x["emailAddress"]["address"] for x in P.get("ccRecipients", [])]
            ok("I1 메일 = 가짜 메일함 (fixtures 설정 그대로) · 받는 사람 = 기록 to 와 같음 · 첨부 1 (PDF) · send 1", to1 == v.get("to") and cc1 == v.get("cc")
               and len(mail.atts) == 1 and mail.atts[0]["name"] == f"{IV}_IV_PL_SI.pdf" and mail.sends == 1, [len(to1), len(mail.atts), mail.sends])
            subj1, html1 = P.get("subject"), P.get("body", {}).get("content", "")
            # I2 직원이 S/I (IV·PL) ① 로 바꿈
            openw()
            page.select_option("[data-cpick='ivSino']", "1")
            page.wait_for_function("() => !document.querySelector('.c01-customs .c01-cstep')", timeout=15000)
            d = page.evaluate("C01.customs._siDef()")
            ok("I2 직원이 바꾼 뒤에도 기억한 기본값 = 처음 값 (IV·PL 2)", d and d["iv"]["v"] == 2 and d["si"]["v"] == 1, d)
            ok("I2 D-03 다시 부를 때 ivSino 1 전달 (기본 고르는 규칙 = D-03 그대로)", runs()[-1].get("ivSino") == 1, runs()[-1])
            if page.locator("[data-cagain]").count():
                page.check("[data-cagain]")
            send()
            cs = sent_recs()
            v = cs[-1]["value"] if cs else {}
            ok("I2 기록 si_default_iv 2 · picks.ivSino 1 · si_why staff_changed · si_changed true · si_avail_n 2",
               len(cs) == 2 and v.get("si_default_iv") == 2 and v.get("picks", {}).get("ivSino") == 1 and v.get("si_why") == "staff_changed"
               and v.get("si_changed") is True and v.get("si_avail_n") == 2, v)
            P = mail.patch or {}
            ok("I2 메일 제목 · 본문 · 받는 사람 = I1 과 같음 (S/I 기록 칸이 메일에 안 들어감)", P.get("subject") == subj1 and P.get("body", {}).get("content", "") == html1
               and [x["emailAddress"]["address"] for x in P.get("toRecipients", [])] == to1 and not any(k in html1 for k in NEWKEYS), P.get("subject"))
            # S 정적: 새 칸은 기록 (customs_sent) 에만 · 다른 기록 · 메일 인자에 없음
            src = (TOOL / "js" / "customs.js").read_text(encoding="utf-8")
            body_send = src[src.index("function send()"):]
            ok("S 새 칸 = customs_sent 기록 안에만 (customs_draft · mailArgs 에 없음)",
               body_send.count("si_default_iv:") == 1 and "si_default_iv" not in src[src.index("function mailArgs"):src.index("function mailArgs") + 3000].split("function send()")[0]
               and "si_default_iv" not in src[src.index("mkAction('customs_draft'") - 1500:src.index("mkAction('customs_draft'")], "")
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
