# ✦ Powered by LEENAI Automation System — v0.3.63 通関書類送付 시험 (결정 #359 · Playwright · 가명 fixtures · 가짜 Graph · 가짜 D-03 — 실제 메일 · SharePoint · COMPASS 호출 0)
"""확인:
 1 버튼 = 조건 다 맞는 IV 만 파랑 · 모자라면 회색 + 마우스 글 (무엇이 모자란지) · 회색을 눌러도 창 없음
 2 창 = ① 대화 가장 최근 메일 기준 To · CC (보낸 사람 포함 · 나 빼기) · 제목 [test] 【通関書類送付_IV】Re: {① 제목} · 본문 · PDF 미리보기 · 고른 값과 이유 · 경고 (붉게)
 3 B/L 빈칸 → 送信 막힘 → 고르면 D-03 다시 (bl 전달) · 빨간 경고 → 확인 체크 전 막힘
 4 送信 (시험 모드) = createReplyAll (가장 최근 메일) → PATCH 받는 사람 = 누른 본인 1명 · CC 0 · 제목 [test] → 첨부 1 → 다시 읽기 → send 1번 → _actions customs_sent (test true)
 5 누르기 전 send 0 · createReplyAll 0 · 창만 열고 닫으면 메일 쓰기 0
 6 ① 없음 → 「通関依頼メールが見つかりません」 · createReplyAll 0
 7 COMPASS ≠ 実況表 → 막힘 · 문구
 8 실전 모드 (sendTest false) = PATCH 받는 사람 = 창에 보인 To · CC 그대로 · 送付済 → 「もう一度送る」 체크 전 막힘
 9 下書き 받는 사람이 다르면 send 안 함 (下書き 남김)
10 머리줄 표시: 시험 뒤 「試験済」 · 실전 뒤 「✓ 通関書類 送付済 m/d · 이름」
사용: python tests/test_customs.py [--shots 폴더]"""
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
from urllib.parse import unquote, urlparse, parse_qs

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_graph as TGR   # noqa: E402  (가짜 SharePoint · 가명 PDF 함수 재사용)

TOOL = Path(__file__).resolve().parent.parent
RES = {"checks": [], "console_errors": []}
DRIVE = TGR.DRIVE
OURS = "example.invalid"            # 시험 = 우리 회사 도메인 대신 (C01.CUSTOMS.ourDomain)
ME = "staff.a@example.invalid"
IV = "TST2611-04"
BKG = "BKG-TEST-0004"


def ok(name, cond, detail=""):
    RES["checks"].append({"name": name, "ok": bool(cond), "detail": str(detail)[:300]})
    print(("OK  " if cond else "NG  ") + name + (f" — {detail}" if detail and not cond else ""), flush=True)


class Mail:
    """가짜 Graph 메일함 (나 = ME). 기록: 부른 순서 · PATCH 내용 · 첨부 · send 횟수"""
    def __init__(self):
        self.reset()

    def reset(self, s1=True, sent=None, draft_override=None):
        self.calls = []
        self.patch = None
        self.atts = []
        self.sends = 0
        self.has_s1 = s1
        self.sent = sent or []
        self.draft_override = draft_override

    def msgs(self):
        def m(i, subj, frm, to, cc, at):
            r = lambda a: {"emailAddress": {"address": a, "name": a.split("@")[0].upper()}}
            return {"id": i, "subject": subj, "conversationId": "CONV1", "sentDateTime": at, "receivedDateTime": at, "isDraft": False,
                    "from": r(frm), "toRecipients": [r(x) for x in to], "ccRecipients": [r(x) for x in cc], "internetMessageId": "<" + i + ">"}
        s1 = m("M1", f"新規通関依頼:BKG#{BKG}, CUT11/10 (TOKYO TO TEST)", ME, ["broker.a@broker.invalid"], ["staff.b@" + OURS], "2026-11-05T01:00:00Z")
        r1 = m("M2", f"RE: 新規通関依頼:BKG#{BKG}, CUT11/10 (TOKYO TO TEST)", "broker.a@broker.invalid", [ME], ["broker.b@broker.invalid", "staff.b@" + OURS], "2026-11-05T03:00:00Z")
        return [s1, r1]

    def handle(self, route, request):
        u = urlparse(request.url)
        path = unquote(u.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        self.calls.append(request.method + " " + path.replace("/v1.0/", ""))
        J = lambda st, b: route.fulfill(status=st, body=json.dumps(b), headers={"Content-Type": "application/json"})
        if request.method == "GET" and path == "/v1.0/me/messages":
            if "$search" in q and "通関書類送付_" in q["$search"]:
                return J(200, {"value": self.sent})
            if "$search" in q:
                return J(200, {"value": self.msgs()[:1] if self.has_s1 else []})
            if "$filter" in q:
                return J(200, {"value": self.msgs()})
        if request.method == "POST" and path.endswith("/createReplyAll"):
            self.reply_to = path.split("/")[-2]
            return J(201, {"id": "D1", "subject": "RE: x", "body": {"contentType": "html", "content": "<html><head></head><body><p>QUOTED</p></body></html>"},
                           "toRecipients": [], "ccRecipients": []})
        if request.method == "PATCH" and path == "/v1.0/me/messages/D1":
            self.patch = json.loads(request.post_data)
            return J(200, {"id": "D1"})
        if request.method == "POST" and path == "/v1.0/me/messages/D1/attachments/createUploadSession":
            self.upload = json.loads(request.post_data)
            return J(201, {"uploadUrl": "https://upload.example.invalid/up1"})
        if request.method == "POST" and path == "/v1.0/me/messages/D1/attachments":
            self.atts.append(json.loads(request.post_data))
            return J(201, {"id": "A1"})
        if request.method == "GET" and path == "/v1.0/me/messages/D1":
            p = self.draft_override or self.patch or {}
            return J(200, {"subject": p.get("subject"), "toRecipients": p.get("toRecipients", []), "ccRecipients": p.get("ccRecipients", []),
                           "bccRecipients": [], "internetMessageId": "<D1@test>", "conversationId": "CONV1"})
        if request.method == "GET" and path == "/v1.0/me/messages/D1/attachments":
            return J(200, {"value": [{"name": a["name"], "size": 10} for a in self.atts]})
        if request.method == "POST" and path == "/v1.0/me/messages/D1/send":
            self.sends += 1
            return route.fulfill(status=202, body="")
        return J(404, {"error": "unexpected " + request.method + " " + path})


def fake_d03(pdf_b64, containers):
    """가짜 D-03 자동 모드 (같은 출처) — run(o) = 받은 값 기록 + 고정 결과 (bl 이 오면 그대로)"""
    return """<!doctype html><meta charset="utf-8"><script>
window.__runs=[];
window.D03AUTO={version:'4.13',ready:Promise.resolve(true),run:function(o){window.__runs.push(o);
 var bl=o.bl||'';
 var W=[{red:true,item:'D-03 未確定項目',text:'タイ SHIPPING MARK'},{red:false,item:'D-03 未確定項目',text:'INSURANCE 最低フロア (CIF)'}];
 if(!bl) W.unshift({red:true,item:'B/L',text:'B/L 形態を選んでください'});
 return Promise.resolve({ok:true,version:'4.13',iv:o.iv,file:o.iv+'_IV_PL_SI.pdf',pages:2,pdf_b64:'%s',bytes:900,sha256:'ab'.repeat(32),
  picks:{ivSino:{v:2,why:'最終番号 (S/I②)'},siSino:{v:1,why:'S/I①'},pod:{v:[1],why:'候補 1 つ'},freight:{v:true,why:'CIF = 運賃あり'},bl:{v:bl,why:o.blWhy||''}},
  warnings:W,si_avail:[1,2],info:{buyer_id:'BUYER-T',consignee:'TESTCONS',terms:'CIF',containers:window.__ct||%s}});}};
</script>""" % (pdf_b64, json.dumps(containers))


def fill_body(page):
    t = page.locator("[data-cbody]").input_value().replace("（通関業者の会社名）", "TEST BROKER CORPORATION")
    page.fill("[data-cbody]", t)
    page.wait_for_timeout(100)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shots")
    a = ap.parse_args()
    shots = Path(a.shots) if a.shots else Path(tempfile.mkdtemp(prefix="c01_customs_shots_"))
    shots.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="c01_customs_"))
    root = tmp / "HANNYU_TOOL"
    shutil.copytree(TOOL / "fixtures", root)
    staff = json.loads((root / "_masters" / "pol_staff.json").read_text(encoding="utf-8"))
    # 시험 IV = TST2611-04 (칸 4 · 줄 4) → 전부 自動OK + Compass入力 기록 → 버튼 켜짐
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
    mail = Mail()
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
            dlg = []
            page.on("dialog", lambda d: (dlg.append(d.message), d.accept()))
            page.route("https://graph.microsoft.com/**", graph)
            page.route(f"http://127.0.0.1:{port}/__d03fake.html*", lambda r: r.fulfill(status=200, body=fake_d03(pdf_b64, containers), headers={"Content-Type": "text/html; charset=utf-8"}))
            ft = {"mode": "ok"}          # v0.3.65 (R12Y · #361): 形態 · タイプ (가명 칸) — ok = 모두 있음 · blank = 1 칸 빈칸 · fail = GET 500

            def dvx(r):
                if "crcf9_container_informations" in r.request.url:
                    if ft["mode"] == "fail":
                        return r.fulfill(status=500, body="{}")
                    cs = [{"crcf9_container_no": f"TSTU{i:07d}", "crcf9_type": "45GP", "_crcf9_form_value": "64f45d9f-383c-f011-8c4e-6045bd62e122"} for i in range(3)]
                    if ft["mode"] == "blank":
                        cs[1]["_crcf9_form_value"] = None
                        cs[2]["crcf9_type"] = None
                    cs.append({"crcf9_container_no": None, "crcf9_type": None, "_crcf9_form_value": None})     # CT 없는 칸 = 안 셈
                    return r.fulfill(status=200, body=json.dumps({"value": cs}), headers={"Content-Type": "application/json"})
                return r.fulfill(status=200, body=json.dumps({"value": [{"_cr49f_sale_contract_id_value": "SC1"}], "_cr49f_buyer_id_value": "BUYER-T"}),
                                 headers={"Content-Type": "application/json"})
            page.route("https://orgde512c6f.crm7.dynamics.com/**", dvx)
            page.goto(f"http://127.0.0.1:{port}/")
            page.wait_for_selector("#ln-splash", timeout=20000)
            ok("탭 제목 v0.3.65", page.title() == "LEENAI C-01 搬入票 v0.3.65", page.title())
            ok("설정: 통관서류 송부 켜짐 · 시험 모드 (sendTest true) · D-03 주소 = 같은 출처 github.io",
               page.evaluate("C01.CUSTOMS.enabled === true && C01.CUSTOMS.sendTest === true && C01.CUSTOMS.d03Url.indexOf('https://mhlee205.github.io/Shipping_Document/') === 0"))
            ok("본문 · 서명 · ✦ 설정 (본문 = #352 문구)", page.evaluate("C01.CUSTOMS.body.indexOf('通関用の書類を送付いたしますので、ご確認の程お願い致します。') > 0 && C01.CUSTOMS.footer === '✦ Powered by LEENAI Automation System'"))
            page.evaluate(TGR.STUB, staff)
            page.evaluate(f"C01.CUSTOMS.d03Url = '/__d03fake.html'; C01.CUSTOMS.ourDomain = '{OURS}'; localStorage.setItem('c01_ports', JSON.stringify({{port: 'all', ports: []}}));")
            page.evaluate("document.getElementById('ln-splash').style.display='none'; document.getElementById('app').style.display=''; C01.app.start(new C01.sources.Graph())")
            page.wait_for_selector("body[data-c01-ready='1']", timeout=20000)
            # 1 버튼
            b4 = page.locator(f'tbody[data-iv="{IV}"] [data-csend]')
            ok("1 조건 맞는 IV = 파란 「✉ 通関書類送付」 (Compass入力 옆)", b4.count() == 1 and "c01-btn-pri" in (b4.get_attribute("class") or "") and "通関書類送付" in b4.inner_text(),
               [b4.count(), b4.get_attribute("class") if b4.count() else "", b4.get_attribute("title") if b4.count() else ""])
            b1 = page.locator('tbody[data-iv="TST2611-01"] [data-csend]')
            t1 = b1.get_attribute("title") if b1.count() else ""
            ok("1 모자란 IV = 회색 + 마우스 글 (n/N台 · Compass入力未完了 n台)", b1.count() == 1 and "c01-blocked" in (b1.get_attribute("class") or "") and "4/5台" in t1 and "Compass入力未完了" in t1, t1)
            b1.click(); page.wait_for_timeout(300)
            ok("1 회색 누름 = 창 없음 (이유만 알림)", page.locator(".c01-customs").count() == 0)
            hdr = page.locator(f'tbody[data-iv="{IV}"] .c01-ivhead').inner_html()
            ok("1 버튼 위치 = Compass入力 버튼 바로 뒤", hdr.index("data-compass") < hdr.index("data-csend"))
            # 2 창
            mail.reset()
            b4.click()
            page.wait_for_selector(".c01-customs [data-csendgo]", timeout=20000)
            page.wait_for_function("() => !document.querySelector('.c01-customs .c01-cstep')", timeout=20000)
            body = page.locator(".c01-customs").inner_text()
            ok("2 받는 사람 = ① 대화 가장 최근 메일 (보낸 사람 To · CC · 나 빼기)", "broker.a@broker.invalid" in body.split("CC")[0] and "broker.b@broker.invalid" in body
               and ("staff.b@" + OURS) in body and body.count(ME) <= 2, body[:400])
            subj = page.locator(".c01-csubj").inner_text()
            ok("2 제목 = [test] 【通関書類送付_IV】Re: {① 제목}", subj == f"[test] 【通関書類送付_{IV}】Re: 新規通関依頼:BKG#{BKG}, CUT11/10 (TOKYO TO TEST)", subj)
            bt = page.locator("[data-cbody]").input_value()
            ok("2 본문 = 様 · 通関用の書類 · 서명 (이름 · 메일) · ✦", "様" in bt and "通関用の書類を送付いたしますので" in bt and ME in bt and bt.rstrip().endswith("✦ Powered by LEENAI Automation System"), bt[-120:])
            ok("2 본문 첫 줄 = 회사명 자리표시 (지난 기록 없음)", bt.splitlines()[0] == "（通関業者の会社名）", bt.splitlines()[0])
            ok("2 PDF 미리보기 · 첨부 이름 {IV}_IV_PL_SI.pdf", page.locator(".c01-cpdf").count() == 1 and f"{IV}_IV_PL_SI.pdf" in body)
            ok("2 고른 값과 이유 (S/I② 最終番号 · S/I① · 候補 1 つ · 운임)", "最終番号 (S/I②)" in body and "S/I①" in body and "候補 1 つ" in body and "CIF = 運賃あり" in body)
            ok("2 시험 모드 표시", page.locator("[data-ctrial]").count() == 1)
            ok("5 창 열기만 = createReplyAll 0 · send 0 · PATCH 0", mail.sends == 0 and not any("createReplyAll" in c for c in mail.calls) and mail.patch is None, mail.calls)
            # 3 B/L 빈칸 → 막힘
            go = page.locator("[data-csendgo]")
            why = page.locator("[data-cwhy]").inner_text()
            ok("3 B/L 빈칸 (새 바이어) → 送信 막힘 · 이유", go.is_disabled() and "B/L" in why, why)
            ok("3 빨간 경고 = 붉게 (c01-cr)", page.locator(".c01-cwarn .c01-cr").count() >= 1)
            page.select_option("[data-cbl]", "waybill")
            page.wait_for_function("() => (window.frames && document.getElementById('c01-d03auto').contentWindow.__runs.length) >= 2", timeout=15000)
            page.wait_for_function("() => !document.querySelector('.c01-customs .c01-cstep')", timeout=15000)
            runs = page.evaluate("document.getElementById('c01-d03auto').contentWindow.__runs")
            ok("3 B/L 고름 → D-03 다시 (bl = waybill)", runs[-1].get("bl") == "waybill" and runs[0].get("bl") == "", runs)
            why = page.evaluate("C01.customs._blockers()")
            ok("3 빨간 경고 확인 전 = 막힘", page.locator("[data-csendgo]").is_disabled() and any("赤の警告" in x for x in why), why)
            page.check("[data-cack]")
            why = page.locator("[data-cwhy]").inner_text()
            ok("3 회사명 자리표시가 남음 → 막힘", page.locator("[data-csendgo]").is_disabled() and "書き換えて" in why, why)
            fill_body(page)
            ok("3 확인 체크 + 회사명 → 送信 가능", page.locator("[data-csendgo]").is_enabled(), page.locator("[data-cwhy]").inner_text())
            page.screenshot(path=str(shots / "customs_window.png"), full_page=False)
            # 4 送信 (시험)
            n_d = len(dlg)
            page.click("[data-csendgo]")
            page.wait_for_function("() => !document.querySelector('.c01-customs')", timeout=15000)
            page.wait_for_timeout(500)
            P = mail.patch or {}
            to = [x["emailAddress"]["address"] for x in P.get("toRecipients", [])]
            cc = [x["emailAddress"]["address"] for x in P.get("ccRecipients", [])]
            ok("4 확인 창 (시험 · 자신에게만) 1번", len(dlg) == n_d + 1 and "【試験】" in dlg[-1] and ME in dlg[-1], dlg[n_d:])
            ok("4 createReplyAll = ① 대화 가장 최근 메일 (M2)", getattr(mail, "reply_to", "") == "M2", getattr(mail, "reply_to", ""))
            ok("4 시험: 받는 사람 = 누른 본인 1명 · CC 0 · BCC 0", to == [ME] and cc == [] and P.get("bccRecipients") == [], [to, cc])
            ok("4 시험: 제목 [test] 로 시작", str(P.get("subject", "")).startswith("[test] 【通関書類送付_" + IV + "】Re: "), P.get("subject"))
            html = P.get("body", {}).get("content", "")
            ok("4 본문 = 우리 글 (body 바로 뒤) + 답장 인용 (QUOTED)", html.index("通関用の書類") < html.index("QUOTED") and "✦ Powered by LEENAI Automation System" in html, html[:200])
            ok("4 첨부 1개 = {IV}_IV_PL_SI.pdf · application/pdf · PDF 바이트", len(mail.atts) == 1 and mail.atts[0]["name"] == f"{IV}_IV_PL_SI.pdf"
               and mail.atts[0]["contentType"] == "application/pdf" and base64.b64decode(mail.atts[0]["contentBytes"]).startswith(b"%PDF"), [x["name"] for x in mail.atts])
            ok("4 send 1번 · 순서 = createReplyAll → PATCH → 첨부 → 다시 읽기 → send", mail.sends == 1 and
               [c.split(" ")[0] + " " + c.split("/")[-1] for c in mail.calls if "D1" in c or "createReplyAll" in c][-6:] ==
               ["POST createReplyAll", "PATCH D1", "POST attachments", "GET D1", "GET attachments", "POST send"], mail.calls[-8:])
            acts = list((root / "_actions").rglob("*.json"))
            cs = [json.loads(f.read_text(encoding="utf-8")) for f in acts]
            cs = [x for x in cs if x.get("action") == "customs_sent"]
            v = cs[0]["value"] if cs else {}
            ok("4 _actions customs_sent (IV · 누가 · 시각 · 메일 ID · PDF sha · test true · 고른 값)", len(cs) == 1 and cs[0]["iv"] == IV and cs[0]["by"] == ME and v.get("test") is True
               and v.get("internet_message_id") == "<D1@test>" and len(v.get("pdf_sha256", "")) == 64 and v.get("bl") == "waybill" and v.get("picks", {}).get("ivSino") == 2, cs)
            hd = page.locator(f'tbody[data-iv="{IV}"] .c01-ivhead').inner_text()
            ok("10 시험 뒤 머리줄 = 「試験済」 · 버튼은 그대로 (실전 아님)", "試験済" in hd and "送付済" not in hd, hd)
            # 6 ① 없음
            mail.reset(s1=False)
            page.locator(f'tbody[data-iv="{IV}"] [data-csend]').click()
            page.wait_for_function("() => document.querySelector('.c01-customs') && !document.querySelector('.c01-customs .c01-cstep')", timeout=20000)
            body = page.locator(".c01-customs").inner_text()
            ok("6 ① 없음 → 「通関依頼メールが見つかりません」 · 送信 막힘 · createReplyAll 0", "通関依頼メールが見つかりません" in body and page.locator("[data-csendgo]").is_disabled()
               and not any("createReplyAll" in c for c in mail.calls), body[:200])
            page.click(".c01-customs [data-close]")
            # 7 COMPASS ≠ 実況表
            mail.reset()
            bad = json.loads(json.dumps(containers)); bad[0]["seal"] = "ZZ999999"
            page.evaluate("(c) => { const f = document.getElementById('c01-d03auto'); f.contentWindow.__ct = c; }", bad)
            page.locator(f'tbody[data-iv="{IV}"] [data-csend]').click()
            page.wait_for_function("() => document.querySelector('.c01-customs') && !document.querySelector('.c01-customs .c01-cstep')", timeout=20000)
            page.select_option("[data-cbl]", "original")
            page.wait_for_function("() => !document.querySelector('.c01-customs .c01-cstep')", timeout=15000)
            page.check("[data-cack]")
            fill_body(page)
            why = page.locator("[data-cwhy]").inner_text()
            ok("7 COMPASS 값 ≠ 実況表 → 막힘 (シール)", page.locator("[data-csendgo]").is_disabled() and "COMPASS ≠ 実況表" in why, why)
            page.click(".c01-customs [data-close]")
            page.evaluate("() => { document.getElementById('c01-d03auto').contentWindow.__ct = null; }")
            # 7b v0.3.65 (R12Y · #361): 形態 · タイプ 空欄 0 = 켜짐 조건 (확인 창 COMPASS GET · Compass入力 기록)
            for mode, word, name in (("blank", "形態・タイプ が空欄 2台", "7b 形態・タイプ 빈칸 2칸 (CT 있는 칸만 셈) → 送信 막힘 · 이유 한 줄"),
                                     ("fail", "形態・タイプ を COMPASS で確認できません", "7b 形態・タイプ GET 실패 → 막힘 (못 읽음 = 안 보냄)")):
                ft["mode"] = mode
                mail.reset()
                page.locator(f'tbody[data-iv="{IV}"] [data-csend]').click()
                page.wait_for_function("() => document.querySelector('.c01-customs') && !document.querySelector('.c01-customs .c01-cstep')", timeout=20000)
                page.select_option("[data-cbl]", "original")
                page.wait_for_function("() => !document.querySelector('.c01-customs .c01-cstep')", timeout=15000)
                page.check("[data-cack]")
                fill_body(page)
                why = page.locator("[data-cwhy]").inner_text()
                ok(name, page.locator("[data-csendgo]").is_disabled() and word in why, why)
                page.click(".c01-customs [data-close]")
            ft["mode"] = "ok"
            page.evaluate("""(iv) => { const A = C01.app._api(); A.S.mine = (A.S.mine || []).concat([{ action: { action_id: 'ft-test', action: 'compass_done', iv: iv, by: 'staff_a@fake',
                at: '2099-01-01T00:00:00+09:00', value: { cells: [{ ct_id: 'g', fields: ['crcf9_type'], before: {}, after: {} }], formtype_blank: 2 } } }]); A.render(); }""", IV)
            bft = page.locator(f'tbody[data-iv="{IV}"] [data-csend]')
            tft = bft.get_attribute("title") or ""
            ok("7b Compass入力 기록 formtype_blank 2 → 버튼 회색 + 「形態・タイプ 空欄 2台」", "c01-blocked" in (bft.get_attribute("class") or "") and "形態・タイプ 空欄 2台" in tft, tft)
            page.evaluate("() => { const A = C01.app._api(); A.S.mine = (A.S.mine || []).filter(m => m.action.action_id !== 'ft-test'); A.render(); }")
            ok("7b 기록 없앰 → 다시 파랑", "c01-btn-pri" in (page.locator(f'tbody[data-iv="{IV}"] [data-csend]').get_attribute("class") or ""))
            # 8 실전 모드
            mail.reset()
            page.evaluate("C01.CUSTOMS.sendTest = false")
            page.locator(f'tbody[data-iv="{IV}"] [data-csend]').click()
            page.wait_for_function("() => document.querySelector('.c01-customs') && !document.querySelector('.c01-customs .c01-cstep')", timeout=20000)
            page.select_option("[data-cbl]", "original")
            page.wait_for_function("() => !document.querySelector('.c01-customs .c01-cstep')", timeout=15000)
            page.check("[data-cack]")
            bt8 = page.locator("[data-cbody]").input_value()
            ok("4 지난 송부 기록의 회사명 (같은 통관업자 도메인) 을 미리 채움", bt8.splitlines()[0] == "TEST BROKER CORPORATION", bt8.splitlines()[0])
            subj = page.locator(".c01-csubj").inner_text()
            ok("8 실전 제목 = [test] 없음", subj.startswith("【通関書類送付_" + IV + "】Re: "), subj)
            n_d = len(dlg)
            page.click("[data-csendgo]")
            page.wait_for_function("() => !document.querySelector('.c01-customs')", timeout=15000)
            page.wait_for_timeout(400)
            P = mail.patch or {}
            to = sorted(x["emailAddress"]["address"] for x in P.get("toRecipients", []))
            cc = sorted(x["emailAddress"]["address"] for x in P.get("ccRecipients", []))
            ok("8 실전: 받는 사람 = 창에 보인 To (보낸 사람) · CC (나 빼기)", to == ["broker.a@broker.invalid"] and cc == sorted(["broker.b@broker.invalid", "staff.b@" + OURS]) and mail.sends == 1, [to, cc])
            hd = page.locator(f'tbody[data-iv="{IV}"] .c01-ivhead').inner_text()
            ok("10 실전 뒤 머리줄 = 「✓ 通関書類 送付済 m/d · 이름」", "通関書類 送付済 11/" in hd or "通関書類 送付済 " in hd, hd)
            # 8b 再送付
            mail.reset()
            page.locator(f'tbody[data-iv="{IV}"] [data-csend]').click()
            page.wait_for_function("() => document.querySelector('.c01-customs') && !document.querySelector('.c01-customs .c01-cstep')", timeout=20000)
            page.select_option("[data-cbl]", "original")
            page.wait_for_function("() => !document.querySelector('.c01-customs .c01-cstep')", timeout=15000)
            page.check("[data-cack]")
            fill_body(page)
            why = page.locator("[data-cwhy]").inner_text()
            ok("8 送付済 IV = 「もう一度送る」 체크 전 막힘", page.locator("[data-csendgo]").is_disabled() and "送付済み" in why, why)
            page.check("[data-cagain]")
            n_d = len(dlg)
            # 9 下書き 받는 사람 다름 → send 안 함
            mail.draft_override = {"subject": "x", "toRecipients": [{"emailAddress": {"address": "other@broker.invalid"}}]}
            page.click("[data-csendgo]")
            page.wait_for_timeout(1500)
            ok("8 再送付 = 확인 창 2번 (보통 + 「もう一度」)", len(dlg) == n_d + 2 and "もう一度" in dlg[-1], dlg[n_d:])
            ok("9 下書き 제목·받는 사람이 다름 → send 0 (下書き 남김 알림)", mail.sends == 0 and page.locator(".c01-customs").count() == 1, mail.calls[-4:])
            page.click(".c01-customs [data-close]")
            page.evaluate("C01.CUSTOMS.sendTest = true")
            # 11 3MB 넘는 PDF = 업로드 세션 (4MB 이하 조각 · 업로드 주소에는 인증 머리 없음) → 다시 읽기 → send
            mail.reset()
            puts = []
            def up(route, request):
                puts.append({"range": request.headers.get("content-range"), "auth": request.headers.get("authorization"), "n": len(request.post_data_buffer or b"")})
                mail.atts.append({"name": f"{IV}_IV_PL_SI.pdf"}) if len(puts) == 1 else None
                return route.fulfill(status=200 if len(puts) < 2 else 201, body="{}", headers={"Content-Type": "application/json"})
            page.route("https://upload.example.invalid/**", up)
            big = base64.b64encode(pdfp.read_bytes() + b"%" + b"0" * (3_400_000)).decode()
            page.evaluate("(b) => { const w = document.getElementById('c01-d03auto').contentWindow; const r0 = w.D03AUTO.run; w.D03AUTO.run = (o) => r0(o).then(r => Object.assign(r, {pdf_b64: b, bytes: Math.floor(b.length * 3 / 4)})); }", big)
            page.locator(f'tbody[data-iv="{IV}"] [data-csend]').click()
            page.wait_for_function("() => document.querySelector('.c01-customs') && !document.querySelector('.c01-customs .c01-cstep')", timeout=20000)
            page.select_option("[data-cbl]", "original")
            page.wait_for_function("() => !document.querySelector('.c01-customs .c01-cstep')", timeout=15000)
            page.check("[data-cack]")
            if page.locator("[data-cagain]").count():
                page.check("[data-cagain]")
            fill_body(page)
            page.click("[data-csendgo]")
            page.wait_for_function("() => !document.querySelector('.c01-customs')", timeout=20000)
            page.wait_for_timeout(300)
            ok("11 3MB 넘는 PDF = createUploadSession → PUT 조각 (4MB 이하 · 인증 머리 없음) → send 1",
               getattr(mail, "upload", {}).get("AttachmentItem", {}).get("name") == f"{IV}_IV_PL_SI.pdf" and len(puts) == 1 and puts[0]["auth"] is None
               and puts[0]["n"] <= 4 * 1024 * 1024 and puts[0]["range"].startswith("bytes 0-") and mail.sends == 1, [puts, getattr(mail, "upload", None), mail.sends])
            # 콘솔 오류
            errs = [e for e in RES["console_errors"] if "favicon" not in e and "404" not in e and not ("500" in e and "Failed to load resource" in e)]   # 500 = 7b 形態・タイプ GET 실패 흉내 (R12Y)
            ok("콘솔 오류 0", not errs, errs[:3])
            br.close()
    finally:
        srv.terminate()
    n_ng = sum(1 for c in RES["checks"] if not c["ok"])
    print(json.dumps({"checks": len(RES["checks"]), "ng": n_ng, "shots": str(shots)}, ensure_ascii=False))
    sys.exit(1 if n_ng else 0)


if __name__ == "__main__":
    main()
