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
12 (v0.3.66 · #366 ②) 받는 이름: ① 대화 우리 직원 메일 인사 줄 → TOOL 송부 기록 (시험 제외) → customs_broker.json (지금 받는 사람 우선) → 통관업자 서명 · 표시 이름 · 출처 한 줄
13 (v0.3.66 · #366 ③) 下書き 첨부: 인라인 그림 (isInline) 2 = 통과 · 일반 첨부가 끼어듦 = 송부 중지 + 파일 이름 · 빨간 글자 + 닫을 때까지 남는 알림
14 (v0.3.66 · #366 ①) POD = 고른 S/I (IV·PL) 의 COMPASS 값 · 값 없는 번호 흐리게 · B/L · Port of Discharge · 못 읽으면 노란 글자 (막지 않음)
15 (v0.3.68 · #367 Part 1) L 인보이스 = 「国内販売（通関書類は買い手側）」 회색 · 누르면 설명만 (창 0)
16 (v0.3.68 · #367 Part 2) ① 이 내 메일함에 없음 + 회사 메일함 ① (customs_s1) → 새 메일 (createReplyAll 0) · 같은 To · CC + 담당 직원 CC · ① 인용 · 기록 route s1_shared
17 본문 못 읽은 ① → 막힘 · 18 제안 (POL 만 = 붉은 「宛先を必ず確認」 · 고칠 수 있음 · 확인 체크 전 막힘 · 주소 꼴 검사) · 19 같은 POL · 바이어 송부 기록 = 노란 제안 · 회사 밖 도메인 2+ = 노란 경고
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
# v0.3.66 (R12Y3): 인사 줄 예 = 엔진 tests/test_v0157_r12y3.py GREET_CASES 와 똑같이 (JS greeting() = Python greeting())
GREET_CASES = [
    ("テスト海運株式会社\r\n山田 様\r\n\r\nいつもお世話になっております。", "テスト海運株式会社", "山田"),
    ("\u200b\r\nテスト通関\r\n佐藤様\r\nいつもお世話になっております。", "テスト通関", "佐藤"),
    ("株式会社テスト\r\n通関部\r\n鈴木 様\r\nいつも", "株式会社テスト\n通関部", "鈴木"),
    ("※至急\r\n株式会社テスト\r\n田中様\r\nいつも", "株式会社テスト", "田中"),
    ("TEST Co., Ltd. 高橋様\r\nいつも", "TEST Co., Ltd.", "高橋"),
    ("伊藤様\r\nいつもお世話になっております。", "", "伊藤"),
    ("いつもお世話になっております。\r\n株式会社テスト\r\n渡辺様", "", ""),
    ("お疲れ様です。\r\n書類を送ります。", "", ""),
    ("", "", ""),
]


def ok(name, cond, detail=""):
    RES["checks"].append({"name": name, "ok": bool(cond), "detail": str(detail)[:300]})
    print(("OK  " if cond else "NG  ") + name + (f" — {detail}" if detail and not cond else ""), flush=True)


class Mail:
    """가짜 Graph 메일함 (나 = ME). 기록: 부른 순서 · PATCH 내용 · 첨부 · send 횟수"""
    def __init__(self):
        self.reset()

    def reset(self, s1=True, sent=None, draft_override=None, greet=None, sig=None, extra_atts=None):
        self.greet = greet            # v0.3.66: ① (우리 메일) 본문 앞부분 = 인사 줄 (None = 인사 줄 없음)
        self.sig = sig                # v0.3.66: 통관업자 메일 본문 (uniqueBody · 서명)
        self.extra_atts = extra_atts or []   # v0.3.66: 全員に返信 下書き 에 따라온 첨부 (인라인 그림 등)
        self.urls = []
        self.calls = []
        self.patch = None
        self.atts = []
        self.sends = 0
        self.has_s1 = s1
        self.sent = sent or []
        self.draft_override = draft_override
        self.newdraft = None          # v0.3.68: 새 메일 下書き (POST me/messages)

    def msgs(self):
        def m(i, subj, frm, to, cc, at):
            r = lambda a: {"emailAddress": {"address": a, "name": a.split("@")[0].upper()}}
            return {"id": i, "subject": subj, "conversationId": "CONV1", "sentDateTime": at, "receivedDateTime": at, "isDraft": False,
                    "from": r(frm), "toRecipients": [r(x) for x in to], "ccRecipients": [r(x) for x in cc], "internetMessageId": "<" + i + ">",
                    "bodyPreview": (self.greet or "お疲れ様です。\r\n通関の依頼です。") if frm == ME else "いつもお世話になっております。"}
        s1 = m("M1", f"新規通関依頼:BKG#{BKG}, CUT11/10 (TOKYO TO TEST)", ME, ["broker.a@broker.invalid"], ["staff.b@" + OURS], "2026-11-05T01:00:00Z")
        r1 = m("M2", f"RE: 新規通関依頼:BKG#{BKG}, CUT11/10 (TOKYO TO TEST)", "broker.a@broker.invalid", [ME], ["broker.b@broker.invalid", "staff.b@" + OURS], "2026-11-05T03:00:00Z")
        return [s1, r1]

    def handle(self, route, request):
        u = urlparse(request.url)
        path = unquote(u.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        self.calls.append(request.method + " " + path.replace("/v1.0/", ""))
        self.urls.append(request.method + " " + unquote(request.url))
        J = lambda st, b: route.fulfill(status=st, body=json.dumps(b), headers={"Content-Type": "application/json"})
        if request.method == "GET" and path == "/v1.0/me/messages":
            if "$search" in q and "通関書類送付_" in q["$search"]:
                return J(200, {"value": self.sent})
            if "$search" in q:
                return J(200, {"value": self.msgs()[:1] if self.has_s1 else []})
            if "$filter" in q:
                return J(200, {"value": self.msgs()})
        if request.method == "GET" and path == "/v1.0/me/messages/M2" and "uniqueBody" in q.get("$select", ""):
            return J(200, {"uniqueBody": {"contentType": "text", "content": self.sig or ""}})
        if request.method == "POST" and path == "/v1.0/me/messages":       # v0.3.68 (R12Y7): 道 2 · 3 = 새 下書き
            self.newdraft = json.loads(request.post_data)
            return J(201, {"id": "D1", "subject": self.newdraft.get("subject")})
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
            p = self.draft_override or self.patch or self.newdraft or {}
            return J(200, {"subject": p.get("subject"), "toRecipients": p.get("toRecipients", []), "ccRecipients": p.get("ccRecipients", []),
                           "bccRecipients": [], "internetMessageId": "<D1@test>", "conversationId": "CONV1"})
        if request.method == "GET" and path == "/v1.0/me/messages/D1/attachments":
            return J(200, {"value": [{"name": a["name"], "size": 10, "isInline": False, "contentType": "application/pdf"} for a in self.atts] + self.extra_atts})
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
 var W=[{red:true,item:'D-03 未決項目',text:'タイ SHIPPING MARK'},{red:false,item:'D-03 未決項目',text:'INSURANCE 最低フロア (CIF)'}];
 if(!bl) W.unshift({red:true,item:'B/L',text:'B/L 形態を選んでください'});
 return Promise.resolve({ok:true,version:'4.13',iv:o.iv,file:o.iv+'_IV_PL_SI.pdf',pages:2,pdf_b64:'%s',bytes:900,sha256:'ab'.repeat(32),
  picks:{ivSino:{v:o.ivSino||2,why:'最終番号 (S/I②)'},siSino:{v:1,why:'S/I①'},pod:{v:[1],why:'候補 1 つ'},freight:{v:true,why:'CIF = 運賃あり'},bl:{v:bl,why:o.blWhy||''}},
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
            ft = {"mode": "ok"}
            SIQ = []          # v0.3.65 (R12Y · #361): 形態 · タイプ (가명 칸) — ok = 모두 있음 · blank = 1 칸 빈칸 · fail = GET 500

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
                if "cr49f_s_is" in r.request.url:        # v0.3.66 (R12Y3 · #366 ①): S/I 의 POD (가명)
                    if ft.get("si") == "fail":
                        return r.fulfill(status=500, body="{}")
                    si = [{"crcf9_sino": 1, "crcf9_place_of_delivery_1": "TESTPORT ONE", "crcf9_place_of_delivery_2": None, "crcf9_place_of_delivery_3": None,
                           "crcf9_pod_bl1": "TESTPORT ONE BL", "crcf9_pod_bl2": None, "crcf9_pod_bl3": None, "crcf9_port_of_discharge": "TESTPORT ONE"},
                          {"crcf9_sino": 2, "crcf9_place_of_delivery_1": "TESTPORT A", "crcf9_place_of_delivery_2": "TESTPORT B", "crcf9_place_of_delivery_3": None,
                           "crcf9_pod_bl1": "TESTPORT A BL", "crcf9_pod_bl2": None, "crcf9_pod_bl3": None, "crcf9_port_of_discharge": "TESTPORT DIS"}]
                    SIQ.append(unquote(r.request.url))
                    return r.fulfill(status=200, body=json.dumps({"value": si}), headers={"Content-Type": "application/json"})
                return r.fulfill(status=200, body=json.dumps({"value": [{"_cr49f_sale_contract_id_value": "SC1"}], "_cr49f_buyer_id_value": "BUYER-T"}),
                                 headers={"Content-Type": "application/json"})
            page.route("https://orgde512c6f.crm7.dynamics.com/**", dvx)
            page.goto(f"http://127.0.0.1:{port}/")
            page.wait_for_selector("#ln-splash", timeout=20000)
            ok("탭 제목 v0.3.70", page.title() == "LEENAI C-01 搬入票 v0.3.70", page.title())
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
            ok("2 본문 첫 줄 = 회사명 자리표시 (지난 기록 없음 · ① 인사 줄 없음 · 서명 없음)", bt.splitlines()[0] == "（通関業者の会社名）", bt.splitlines()[0])
            src_l = page.locator("[data-cnamesrc]").inner_text() if page.locator("[data-cnamesrc]").count() else ""
            ok("12 宛名の出どころ 한 줄 (회사명 = 見つかりません · 담당자 = 표시 이름)", "会社名 = 見つかりません" in src_l and "送信者名" in src_l, src_l)
            ok("12 서명 찾기 = 통관업자 메일 1통 GET (uniqueBody · 글자) · 쓰기 0", any("me/messages/M2" in u and "uniqueBody" in u for u in mail.urls), mail.urls[-6:])
            pod = page.locator("tr:has(th:text('POD'))").inner_text()
            ok("14 POD = 고른 S/I② 의 값 (1st POD TESTPORT A · 2nd POD TESTPORT B · 3rd = 값 없음)", "1st POD" in pod and "TESTPORT A" in pod and "2nd POD" in pod and "TESTPORT B" in pod and "TESTPORT ONE" not in pod, pod)
            ok("14 값 없는 3rd = 흐리게 · 못 누름", page.locator("[data-cpod='3']").is_disabled() and page.locator("[data-cpod='1']").is_enabled())
            ok("14 B/L · Port of Discharge 작게", "B/L: TESTPORT A BL" in pod and "Port of Discharge: TESTPORT DIS" in pod, pod)
            ok("14 S/I 읽기 = 販売契約 1번 (sino · POD 1/2/3 · pod_bl · port_of_discharge)", len(SIQ) == 1 and "_cr49f_sale_contract_id_value eq SC1" in SIQ[0] and "crcf9_place_of_delivery_3" in SIQ[0] and "crcf9_port_of_discharge" in SIQ[0], SIQ)
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
            ok("6 ① 없음 · 회사 메일함 ① 없음 · 제안 없음 → 「宛先がありません」 · 送信 막힘 · createReplyAll 0 (v0.3.68 道 0)", "宛先がありません" in body and page.locator("[data-csendgo]").is_disabled()
               and page.locator("[data-croute='none']").count() == 1 and not any("createReplyAll" in c for c in mail.calls), body[:200])
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
            ok("12 시험 송부 기록은 회사명 출처가 아님 (시험 제외 · v0.3.66) → 자리표시", bt8.splitlines()[0] == "（通関業者の会社名）", bt8.splitlines()[0])
            fill_body(page)
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
            ok("12 실전 송부 기록 (같은 도메인) = 회사명 미리 채움 · 출처 「TOOL の送付記録」", page.locator("[data-cbody]").input_value().splitlines()[0] == "TEST BROKER CORPORATION"
               and "TOOL の送付記録" in page.locator("[data-cnamesrc]").inner_text(), page.locator("[data-cnamesrc]").inner_text())
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
            page.evaluate("(b) => { const w = document.getElementById('c01-d03auto').contentWindow; const r0 = w.D03AUTO.run; w.__r0 = r0; w.D03AUTO.run = (o) => r0(o).then(r => Object.assign(r, {pdf_b64: b, bytes: Math.floor(b.length * 3 / 4)})); }", big)
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
            page.evaluate("() => { const w = document.getElementById('c01-d03auto').contentWindow; w.D03AUTO.run = w.__r0; }")   # 11 의 큰 PDF 흉내 끝
            # 12 (v0.3.66 · #366 ②) 받는 이름 — 인사 줄 규칙 = 엔진과 같음
            got = page.evaluate("(cs) => cs.map(c => C01.customs._greeting(c[0]))", [list(c) for c in GREET_CASES])
            ok("12 인사 줄 읽기 = 엔진 greeting() 과 같은 결과 (" + str(len(GREET_CASES)) + " 예)", [(g["company"], g["person"]) for g in got] == [(c[1], c[2]) for c in GREET_CASES], got)

            def open_iv(**kw):
                mail.reset(**kw)
                page.locator(f'tbody[data-iv="{IV}"] [data-csend]').click()
                page.wait_for_function("() => document.querySelector('.c01-customs') && !document.querySelector('.c01-customs .c01-cstep')", timeout=20000)
                return page.locator("[data-cbody]").input_value(), (page.locator("[data-cnamesrc]").inner_text() if page.locator("[data-cnamesrc]").count() else "")
            page.evaluate("() => { const A = C01.app._api(); A.S.mine = (A.S.mine || []).filter(m => !(m.action && m.action.action === 'customs_sent')); A.S.actions = (A.S.actions || []).filter(m => !((m.action || m).action === 'customs_sent')); A.render(); }")
            bt, sl = open_iv(greet="※ご確認ください\r\nテスト海運株式会社\r\nBROKERA 様\r\n\r\nいつもお世話になっております。")
            ok("12 ① 대화 우리 직원 메일 인사 줄 → 회사명 · 담당자 · 출처 「① の会話（あなたのメール m/d）」", bt.splitlines()[:2] == ["テスト海運株式会社", "BROKERA 様"] and "① の会話（あなたのメール 11/05）" in sl, [bt.splitlines()[:2], sl])
            ok("12 ① 에서 둘 다 찾음 = 서명 GET 0", not any("uniqueBody" in u for u in mail.urls), mail.urls[-4:])
            page.click(".c01-customs [data-close]")
            page.evaluate("""() => { C01.app._api().S.customsBroker = { domains: { 'broker.invalid': { company: 'テスト通関株式会社', company_n: 5, n: 7,
                persons: [{ name: '新人', n: 1, last_at: '2026-11-07T10:00:00' }, { name: 'BROKER.B', n: 6, last_at: '2026-10-01T10:00:00' }] },
                'other.invalid': { company: 'ちがう会社', company_n: 9, n: 9, persons: [{ name: 'X', n: 9, last_at: '2026-11-08T10:00:00' }] } } }; }""")
            bt, sl = open_iv()
            ok("12 customs_broker.json (같은 도메인) → 회사명 · 담당자 = 지금 받는 사람 (CC 의 BROKER.B) 우선 · 출처 「過去の 通関書類送付（7 通）」",
               bt.splitlines()[:2] == ["テスト通関株式会社", "BROKER.B 様"] and "過去の 通関書類送付（7 通）" in sl, [bt.splitlines()[:2], sl])
            page.click(".c01-customs [data-close]")
            page.evaluate("() => { C01.app._api().S.customsBroker = null; }")
            bt, sl = open_iv(sig="お世話になります。\r\n承知しました。\r\n\r\n--------\r\nテストシッピング株式会社\r\n通関課 BROKERA\r\nTEL 00-0000-0000")
            ok("12 서명의 회사명 줄 + 표시 이름 → 채움 · 출처 「通関業者のメールの署名」", bt.splitlines()[:2] == ["テストシッピング株式会社", "BROKER.A 様"] and "通関業者のメールの署名" in sl, [bt.splitlines()[:2], sl])
            page.click(".c01-customs [data-close]")
            ok("12 서명 줄 고르기 (회사명 낱말 · 60자 이하 · 맨 아래)", page.evaluate("C01.customs._sigCompany('本文 株式会社の件で\\nーー\\n■ テスト株式会社 ■\\nTEL')") == "テスト株式会社",
               page.evaluate("C01.customs._sigCompany('本文 株式会社の件で\\nーー\\n■ テスト株式会社 ■\\nTEL')"))
            # 13 (v0.3.66 · #366 ③) 下書き 첨부 = 인라인 그림 + 우리 PDF → 보냄 · 일반 첨부가 끼어듦 → 중지
            def send_once(**kw):
                open_iv(greet="テスト海運株式会社\r\nBROKERA 様\r\nいつも", **kw)
                page.select_option("[data-cbl]", "original")
                page.wait_for_function("() => !document.querySelector('.c01-customs .c01-cstep')", timeout=15000)
                if page.locator("[data-cack]").count():
                    page.check("[data-cack]")
                if page.locator("[data-cagain]").count():
                    page.check("[data-cagain]")
                why = page.locator("[data-cwhy]").inner_text()
                page.click("[data-csendgo]")
                return why
            inl = [{"name": "image001.png", "size": 5000, "isInline": True, "contentType": "image/png"}, {"name": "image002.jpg", "size": 8000, "isInline": True, "contentType": "image/jpeg"}]
            w13 = send_once(extra_atts=inl)
            try:
                page.wait_for_function("() => !document.querySelector('.c01-customs')", timeout=15000)
            except Exception:
                print("13 why:", w13, mail.calls[-6:], page.locator("[data-csenderr]").all_inner_texts())
            ok("13 인라인 그림 2 + PDF 1 → 송부 1번 (인라인 그림은 지우지 않음 · DELETE 0)", mail.sends == 1 and not any(c.startswith("DELETE") for c in mail.calls), mail.calls[-5:])
            ok("13 첨부 다시 읽기 = isInline · contentType 같이", any("/attachments?" in u and "isInline" in u and u.startswith("GET") for u in mail.urls), [u for u in mail.urls if "attachments" in u])
            send_once(extra_atts=inl[:1] + [{"name": "original_invoice.xlsx", "size": 9000, "isInline": False, "contentType": "application/vnd.ms-excel"}])
            page.wait_for_selector("#c01-cerr", timeout=15000)
            page.wait_for_timeout(300)
            er = page.locator("[data-csenderr]").inner_text() if page.locator("[data-csenderr]").count() else ""
            ok("13 일반 첨부가 끼어듦 → send 0 · 창 그대로 · 빨간 글자에 그 파일 이름", mail.sends == 0 and page.locator(".c01-customs").count() == 1 and "original_invoice.xlsx" in er and "image001.png" not in er, er)
            page.wait_for_timeout(6500)
            ok("13 실패 알림 = 6초 뒤에도 남음 (닫기 전까지) · 닫기 → 사라짐", page.locator("#c01-cerr").count() == 1 and "original_invoice.xlsx" in page.locator("#c01-cerr").inner_text())
            page.click("#c01-cerr [data-cerr-close]")
            ok("13 닫기 → 사라짐", page.locator("#c01-cerr").count() == 0)
            page.click(".c01-customs [data-close]")
            # 14 S/I 바꾸면 POD 표시도 그 S/I · 못 읽으면 노란 글자 (막지 않음)
            open_iv(greet="テスト海運株式会社\r\nBROKERA 様\r\nいつも")
            page.select_option("[data-cpick='ivSino']", "1")
            page.wait_for_function("() => !document.querySelector('.c01-customs .c01-cstep')", timeout=15000)
            pod1 = page.locator("tr:has(th:text('POD'))").inner_text()
            ok("14 S/I① 으로 바꿈 → POD 표시 = S/I① 값 (TESTPORT ONE · 2nd 흐리게)", "TESTPORT ONE" in pod1 and "TESTPORT A" not in pod1 and page.locator("[data-cpod='2']").is_disabled(), pod1)
            page.click(".c01-customs [data-close]")
            ft["si"] = "fail"
            open_iv(greet="テスト海運株式会社\r\nBROKERA 様\r\nいつも")
            page.select_option("[data-cbl]", "original")
            page.wait_for_function("() => !document.querySelector('.c01-customs .c01-cstep')", timeout=15000)
            page.check("[data-cack]")
            if page.locator("[data-cagain]").count():
                page.check("[data-cagain]")
            ok("14 S/I 못 읽음 → 번호만 + 노란 「COMPASS の POD を読めませんでした」 · 送信 은 막지 않음", page.locator("[data-cpodng]").count() == 1 and page.locator("[data-csendgo]").is_enabled(),
               page.locator("[data-cwhy]").inner_text())
            page.click(".c01-customs [data-close]")
            ft["si"] = None
            # 15 (v0.3.68 · #367 Part 1) L 인보이스 = 국내 판매
            ok("15 L 로 시작하는 IV = 국내 판매 (가명 번호)", page.evaluate("C01.customs._domestic({iv_no: 'LT02611-01'}) && !C01.customs._domestic({iv_no: 'NT02611-01'})"))
            page.evaluate("C01.CUSTOMS.domesticPrefix = 'TST2611-03'; C01.app._api().render()")
            b3 = page.locator('tbody[data-iv="TST2611-03"] [data-csend]')
            ok("15 버튼 = 회색 「国内販売（通関書類は買い手側）」 · 마우스 글 (S/I なし · 買い手側)", b3.count() == 1 and b3.inner_text() == "国内販売（通関書類は買い手側）"
               and "c01-csend-dom" in (b3.get_attribute("class") or "") and "S/I はなく" in (b3.get_attribute("title") or ""), [b3.inner_text() if b3.count() else "", b3.get_attribute("title") if b3.count() else ""])
            mail.reset()
            b3.click(); page.wait_for_timeout(400)
            ok("15 누름 = 설명 알림만 · 창 0 · 메일 GET 0", page.locator(".c01-customs").count() == 0 and not mail.calls and "国内販売" in page.locator("body").inner_text(), mail.calls)
            page.evaluate("C01.CUSTOMS.domesticPrefix = 'L'; C01.app._api().render()")
            ok("15 다른 IV 는 그대로 (TST2611-04 = 파랑)", "c01-btn-pri" in (page.locator(f'tbody[data-iv="{IV}"] [data-csend]').get_attribute("class") or ""))

            # 16 (v0.3.68 · #367 Part 2) 道 2 = 회사 메일함 ① (customs_s1.json 흉내)
            S1 = {"kind": "customs_s1", "built_at": "2026-11-08T09:00:00+09:00", "by_pol": {}, "ivs": {IV: {
                "s1": {"k": "k1", "subject": f"新規通関依頼:BKG#{BKG}, CUT11/10 (KOBE TO TEST)", "at": "2026-11-05T10:00:00", "from": "staff.c@" + OURS, "from_name": "STAFF C"},
                "last": {"k": "k2", "subject": f"RE: 新規通関依頼:BKG#{BKG}, CUT11/10 (KOBE TO TEST)", "at": "2026-11-06T12:00:00", "from": "broker.a@broker.invalid", "from_name": "BROKERA",
                         "to": [{"a": "staff.c@" + OURS, "n": "STAFF C"}], "cc": [{"a": "broker.b@broker.invalid", "n": "BROKERB"}, {"a": ME, "n": "ME"}],
                         "body": "承知しました。\n\nテスト通関株式会社\nBROKERA", "body_ok": True},
                "staff": "staff.c@" + OURS, "staff_name": "STAFF C", "n_conv": 3, "s1_count": 1}}}
            page.evaluate("(x) => { C01.app._api().S.customsS1 = x; }", S1)

            def open2(**kw):
                mail.reset(s1=False, **kw)
                page.locator(f'tbody[data-iv="{IV}"] [data-csend]').click()
                page.wait_for_function("() => document.querySelector('.c01-customs') && !document.querySelector('.c01-customs .c01-cstep')", timeout=20000)

            def ready_send():
                page.select_option("[data-cbl]", "original")
                page.wait_for_function("() => !document.querySelector('.c01-customs .c01-cstep')", timeout=15000)
                if page.locator("[data-cack]").count():
                    page.check("[data-cack]")
                if page.locator("[data-cagain]").count():
                    page.check("[data-cagain]")
                t = page.locator("[data-cbody]").input_value().replace("（通関業者の会社名）", "TEST BROKER CORPORATION").replace("（担当者名）", "BROKERA")
                page.fill("[data-cbody]", t)
                page.wait_for_timeout(100)
            open2()
            body = page.locator(".c01-customs").inner_text()
            ok("16 道 2 표시 = 「① は STAFF C のメールにあります — 新しいメールとして同じ宛先に送ります」", page.locator("[data-croute='s1_shared']").count() == 1
               and "① は STAFF C のメールにあります — 新しいメールとして同じ宛先に送ります" in body, body[:300])
            rc = page.evaluate("C01.customs._recips()")
            ok("16 받는 사람 = ① 최신 메일 (보낸 사람 + To) · CC (나 빼기) + 담당 직원 CC (기본)", [x["a"] for x in rc["to"]] == ["broker.a@broker.invalid", "staff.c@" + OURS]
               and [x["a"] for x in rc["cc"]] == ["broker.b@broker.invalid"], rc)
            page.uncheck("[data-cstaff]")
            rc2 = page.evaluate("C01.customs._recips()")
            page.check("[data-cstaff]")
            ok("16 담당 직원 CC = 끌 수 있음 (To 에 이미 있으면 그대로 1번)", [x["a"] for x in rc2["cc"]] == ["broker.b@broker.invalid"], rc2)
            ok("16 제목 = [test] 【通関書類送付_IV】RE: {① 제목}", page.locator(".c01-csubj").inner_text() == f"[test] 【通関書類送付_{IV}】RE: 新規通関依頼:BKG#{BKG}, CUT11/10 (KOBE TO TEST)",
               page.locator(".c01-csubj").inner_text())
            ok("16 창 열기만 = 메일 쓰기 0 (POST · PATCH 0)", not any(c.startswith(("POST", "PATCH")) for c in mail.calls), mail.calls)
            ready_send()
            ok("16 조건 다 맞으면 送信 가능", page.locator("[data-csendgo]").is_enabled(), page.locator("[data-cwhy]").inner_text())
            page.screenshot(path=str(shots / "customs_route2.png"), full_page=False)
            n_d = len(dlg)
            page.click("[data-csendgo]")
            page.wait_for_function("() => !document.querySelector('.c01-customs')", timeout=15000)
            page.wait_for_timeout(400)
            nd = mail.newdraft or {}
            ok("16 확인 창 = 宛先の道 (① と同じ宛先へ 新しいメール · 담당 이름)", len(dlg) >= n_d + 1 and "宛先の道: ① と同じ宛先へ 新しいメール（① は STAFF C のメール）" in dlg[n_d], dlg[n_d:])
            ok("16 새 下書き (POST me/messages) · createReplyAll 0 · PATCH 0", nd and not any("createReplyAll" in c for c in mail.calls) and mail.patch is None, mail.calls[-8:])
            ok("16 시험: 받는 사람 = 나 1명 · CC 0 · 제목 [test]", [x["emailAddress"]["address"] for x in nd.get("toRecipients", [])] == [ME] and nd.get("ccRecipients") == []
               and str(nd.get("subject", "")).startswith("[test] 【通関書類送付_" + IV + "】RE: "), nd.get("subject"))
            html = (nd.get("body") or {}).get("content", "")
            ok("16 본문 = 우리 글 → ① 최신 메일 인용 (Original Message · From · 본문)", html.find("通関用の書類") >= 0 and html.find("通関用の書類") < html.find("-----Original Message-----")
               and "承知しました。" in html and "From: BROKERA &lt;broker.a@broker.invalid&gt;" in html, html[:300])
            ok("16 첨부 1 · 다시 읽기 → send 1", len(mail.atts) == 1 and mail.sends == 1 and
               [c.split(" ")[0] + " " + c.split("/")[-1] for c in mail.calls if "D1" in c or c.endswith("me/messages")][-5:] == ["POST messages", "POST attachments", "GET D1", "GET attachments", "POST send"], mail.calls[-8:])
            cs = [json.loads(f.read_text(encoding="utf-8")) for f in (root / "_actions").rglob("*.json")]
            cs = sorted([x for x in cs if x.get("action") == "customs_sent" and (x.get("value") or {}).get("route") == "s1_shared"], key=lambda x: x["at"])
            v = cs[-1]["value"] if cs else {}
            ok("16 기록 route s1_shared · s1_k · 담당 직원", v.get("route") == "s1_shared" and v.get("s1_k") == "k2" and v.get("s1_staff") == "staff.c@" + OURS and v.get("test") is True, v)
            # 17 본문 못 읽음 → 막힘
            S1b = json.loads(json.dumps(S1)); S1b["ivs"][IV]["last"]["body_ok"] = False; S1b["ivs"][IV]["last"]["body"] = ""
            page.evaluate("(x) => { C01.app._api().S.customsS1 = x; }", S1b)
            open2()
            ready_send()
            why = page.evaluate("C01.customs._blockers()")
            ok("17 ① 본문 못 읽음 → 막힘 「① の本文をまだ読めていません」", page.locator("[data-csendgo]").is_disabled() and any("① の本文をまだ読めていません" in x for x in why), why)
            page.click(".c01-customs [data-close]")
            # 18 道 3 제안 (POL 만)
            BP = {"kind": "customs_s1", "built_at": "2026-11-08T09:00:00+09:00", "ivs": {}, "by_pol": {"KOBE": {"at": "2026-11-04T10:00:00", "staff": "staff.c@" + OURS, "n": 4,
                  "to": [{"a": "broker.k@kobe.invalid", "n": "BROKERK"}], "cc": [{"a": "staff.c@" + OURS, "n": "STAFF C"}, {"a": ME, "n": "ME"}]}}}
            page.evaluate("(x) => { C01.app._api().S.customsS1 = x; }", BP)
            open2()
            ok("18 道 3 = 붉은 「①がありません — 宛先を必ず確認」 (POL 만 · 바이어 모름)", page.locator("[data-croute='proposal']").count() == 1 and page.locator("[data-cprop='pol'].c01-cr").count() == 1
               and "宛先を必ず確認" in page.locator("[data-cprop]").inner_text(), page.locator(".c01-customs").inner_text()[:300])
            ok("18 미리 채움 = 그 POL 최신 ① 의 To · CC (나 빼기) · 고칠 수 있는 칸", page.locator("[data-cedit='to']").input_value() == "broker.k@kobe.invalid"
               and page.locator("[data-cedit='cc']").input_value() == "staff.c@" + OURS, [page.locator("[data-cedit='to']").input_value(), page.locator("[data-cedit='cc']").input_value()])
            ok("18 제목 = [test] 【通関書類送付_IV】BKG#… CUT m/d", page.locator(".c01-csubj").inner_text() == f"[test] 【通関書類送付_{IV}】BKG#{BKG} CUT 11/12", page.locator(".c01-csubj").inner_text())
            ready_send()
            why = page.evaluate("C01.customs._blockers()")
            ok("18 「宛先を確認しました」 체크 전 = 막힘", page.locator("[data-csendgo]").is_disabled() and any("宛先を確認しました" in x for x in why), why)
            page.fill("[data-cedit='cc']", "staff.c@" + OURS + ", not-an-address")
            page.locator("[data-cedit='cc']").dispatch_event("change")
            page.check("[data-cackto]")
            why = page.evaluate("C01.customs._blockers()")
            ok("18 주소 꼴이 틀림 → 막힘 (그 글자)", page.locator("[data-csendgo]").is_disabled() and any("not-an-address" in x for x in why), why)
            page.fill("[data-cedit='cc']", "staff.c@" + OURS + "\nextra.x@kobe.invalid")
            page.locator("[data-cedit='cc']").dispatch_event("change")
            ok("18 칸을 고치면 확인 체크가 풀림 (다시 확인)", not page.locator("[data-cackto]").is_checked())
            page.check("[data-cackto]")
            rc = page.evaluate("C01.customs._recips()")
            ok("18 고친 받는 사람 = 그대로 (To 1 · CC 2)", [x["a"] for x in rc["to"]] == ["broker.k@kobe.invalid"] and [x["a"] for x in rc["cc"]] == ["staff.c@" + OURS, "extra.x@kobe.invalid"], rc)
            ok("18 확인 + 조건 → 送信 가능", page.locator("[data-csendgo]").is_enabled(), page.locator("[data-cwhy]").inner_text())
            page.screenshot(path=str(shots / "customs_route3.png"), full_page=False)
            page.click("[data-csendgo]")
            page.wait_for_function("() => !document.querySelector('.c01-customs')", timeout=15000)
            page.wait_for_timeout(400)
            nd = mail.newdraft or {}
            cs = [json.loads(f.read_text(encoding="utf-8")) for f in (root / "_actions").rglob("*.json")]
            cs = [x for x in cs if x.get("action") == "customs_sent" and (x.get("value") or {}).get("route") == "proposal"]
            ok("18 새 下書き → send 1 · 기록 route proposal · prop_src pol", nd.get("subject", "").startswith("[test] 【通関書類送付_" + IV + "】BKG#") and mail.sends == 1
               and len(cs) == 1 and cs[0]["value"].get("prop_src") == "pol", [nd.get("subject"), mail.sends, len(cs)])
            # 19 같은 POL · 같은 바이어 송부 기록 (실전) = 노란 제안 · 회사 밖 도메인 2+ = 노란 경고
            page.evaluate('''(iv) => { const A = C01.app._api(); const o = A.S.jik.ivs.find(x => x.iv_no === 'TST2611-02'); o.pol = 'KOBE';
                A.S.mine = (A.S.mine || []).concat([{ action: { action_id: 'cs-other', action: 'customs_sent', iv: 'TST2611-02', by: 'staff_a@fake', at: '2026-11-07T10:00:00+09:00',
                value: { test: false, buyer_id: 'BUYER-T', to: ['broker.y@yoko.invalid'], cc: ['broker.z@other.invalid'] } } }]); }''', IV)
            open2()
            ok("19 같은 POL · 같은 바이어 실전 송부 기록 → 노란 「①がありません — 宛先を確認してください」 · 그 받는 사람", page.locator("[data-cprop='buyer'].c01-cy").count() == 1
               and page.locator("[data-cedit='to']").input_value() == "broker.y@yoko.invalid", page.locator(".c01-customs").inner_text()[:300])
            ok("19 회사 밖 도메인 2개 → 노란 경고", page.locator("[data-cdoms]").count() == 1 and "2 つ" in page.locator("[data-cdoms]").inner_text(), page.locator("[data-cdoms]").all_inner_texts())
            page.click(".c01-customs [data-close]")
            page.evaluate('''() => { const A = C01.app._api(); A.S.customsS1 = null; A.S.mine = (A.S.mine || []).filter(m => m.action.action_id !== 'cs-other');
                A.S.jik.ivs.find(x => x.iv_no === 'TST2611-02').pol = 'YOKOHAMA'; }''')
            # 20 (v0.3.70 · R12Y10) 道 2 · ① 대화 둘 · 받는 사람 다름 (ambiguous) → 노랑 「宛先を確認 — ① のメールが 2 件あります」 + 대화 고르기 (기본 = picked = 지금과 같음)
            def conv(k, at, frm, fname, to, picked, n, hit=False):
                return {"conv": "c" * 15 + k, "picked": picked, "iv_hit": hit, "n": n, "staff": "staff.c@" + OURS, "staff_name": "STAFF C", "ext_doms": 1,
                        "s1": {"k": "s" + k, "subject": f"新規通関依頼:BKG#{BKG}", "at": at, "from": "staff.c@" + OURS, "from_name": "STAFF C"},
                        "last": {"k": "l" + k, "subject": f"RE: 新規通関依頼:BKG#{BKG}", "at": at, "from": frm, "from_name": fname,
                                 "to": [{"a": a, "n": ""} for a in to], "cc": [], "body": "本文 " + k, "body_ok": True}}
            c1 = conv("1", "2026-11-06T12:00:00", "broker.a@broker.invalid", "BROKERA", ["staff.c@" + OURS], True, 3)
            c2 = conv("2", "2026-11-05T09:00:00", "broker.q@other.invalid", "BROKERQ", ["staff.c@" + OURS], False, 2)
            S1a = json.loads(json.dumps(S1)); x = S1a["ivs"][IV]
            x["last"] = dict(c1["last"]); x["s1"] = dict(c1["s1"]); x["n_conv"] = 3; x["n_s1_conv"] = 2; x["ambiguous"] = True; x["convs"] = [c1, c2]
            page.evaluate("(x) => { C01.app._api().S.customsS1 = x; }", S1a)
            open2()
            amb = page.locator("[data-camb='shared']")
            ok("20 노랑 「宛先を確認 — ① のメールが 2 件あります」 + 고르기 2", amb.count() == 1 and "宛先を確認 — ① のメールが 2 件あります" in amb.inner_text()
               and page.locator("[data-cconv] option").count() == 2 and page.locator("[data-cconv]").input_value() == "0", amb.all_inner_texts())
            rc = page.evaluate("C01.customs._recips()")
            ok("20 기본 = picked 대화 (가장 새 ① · 지금과 같음) 의 받는 사람", [y["a"] for y in rc["to"]][:1] == ["broker.a@broker.invalid"], rc)
            page.select_option("[data-cconv]", "1")
            page.wait_for_timeout(300)
            rc = page.evaluate("C01.customs._recips()")
            ok("20 다른 대화 고름 → 그 대화 가장 새 메일 받는 사람 (BROKERQ)", [y["a"] for y in rc["to"]][:1] == ["broker.q@other.invalid"] and page.locator("[data-cconv]").input_value() == "1", rc)
            ready_send()
            page.click("[data-csendgo]")
            page.wait_for_function("() => !document.querySelector('.c01-customs')", timeout=15000)
            page.wait_for_timeout(400)
            cs = [json.loads(f.read_text(encoding="utf-8")) for f in (root / "_actions").rglob("*.json")]
            cs = sorted([y for y in cs if y.get("action") == "customs_sent" and (y.get("value") or {}).get("route") == "s1_shared"], key=lambda y: y["at"])
            v = cs[-1]["value"] if cs else {}
            ok("20 기록 = 고른 대화 (s1_k · s1_conv sha · s1_amb 2) · 시험 = 나 1명", v.get("s1_k") == "l2" and v.get("s1_conv") == "c" * 15 + "2" and v.get("s1_amb") == 2 and v.get("test") is True, v)
            # 20b ambiguous 아님 (대화 하나) = 노랑 0
            page.evaluate("(x) => { C01.app._api().S.customsS1 = x; }", S1)
            open2()
            ok("20b 대화 하나 = 노랑 0 · 고르기 0 (지금과 같음)", page.locator("[data-camb]").count() == 0 and page.locator("[data-cconv]").count() == 0)
            page.click(".c01-customs [data-close]")
            # 20c 道 1 (내 메일함 ① 에 返信) + 엔진 ambiguous → 노랑 알림만 (고르기 0)
            page.evaluate("(x) => { C01.app._api().S.customsS1 = x; }", S1a)
            mail.reset(s1=True)
            page.locator(f'tbody[data-iv="{IV}"] [data-csend]').click()
            page.wait_for_function("() => document.querySelector('.c01-customs') && !document.querySelector('.c01-customs .c01-cstep')", timeout=20000)
            ok("20c 道 1 + 엔진 ambiguous → 노랑 알림 (data-camb=reply) · 고르기 0", page.locator("[data-croute='s1_reply']").count() == 1 and page.locator("[data-camb='reply']").count() == 1
               and page.locator("[data-cconv]").count() == 0, page.locator(".c01-customs").inner_text()[:200])
            page.click(".c01-customs [data-close]")
            page.evaluate("() => { C01.app._api().S.customsS1 = null; }")
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
