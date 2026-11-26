# ✦ Powered by LEENAI Automation System — v0.3.76 (R12Y37 · 결정 #380) 통관 송부 「下書きで保存」 · 통관업자별 추가 서류 · 사진 · 搬入票 링크 (관리자 시험) 시험
"""Playwright · 가명 fixtures · 가짜 Graph · 가짜 D-03 · 가짜 SharePoint (실제 메일 · SharePoint · COMPASS 호출 0). 확인:
 R1 req 없음 (엔진 키 없음) = 노랑 0 · 「送信」 파랑 · 「下書きで保存」 회색 (지금과 같음)
 R2 LOTOS 꼴 (추가 없음) = 노랑 0 · 送信 그대로
 R3 추가 필요 (PHOTO · 搬入票) = 노랑 문구 · 필요한 것만 · 기본 = 下書きで保存 (파랑) · 送信 = 「追加書類は別に送ります」 체크 뒤
 R4 要確認 (표에 없는 도메인) = 「必要書類を確認してください」
 R5 下書きで保存 (道 1 s1_reply) = createReplyAll → PATCH → 첨부 → 다시 읽기 → webLink GET · send 0 · _actions customs_draft · 「Outlook で開く」 · 머리줄 「下書き作成済」
 R6 두 번 누름 = 「もう一つ作りますか」 확인 · 취소 = 下書き 0
 R7 下書きで保存 (道 2 s1_shared) = 새 下書き (POST me/messages) · send 0
 R8 엔진이 본 메일 (iv.customs_mail · test 아님) = 머리줄 「✓ 通関書類 送付済」 · [test] 메일 = 아님
 R9 링크 (관리자 시험): 관리자 아님 = 체크 없음 · 관리자 = 체크 → 시험 모드 · zip 2 (PHOTO · 搬入票) → _customs_share/{IV}/{時刻}/ · createLink anonymous · view · 7 일 →
    본문 링크 + 「まで有効」 · 받는 사람 = 나 1명 · [test] · 기록 share (item id · 경로 · 크기 · 장수) · zip 안 = CT 폴더 + 사진 수 = 목록 · 写真なしCT 표시
 R10 링크 범위가 anonymous 아님 = 보내지 않음 (send 0) · v0.3.78: 노랑 「リンクを作れませんでした」 (0.3.76 동작으로)
 R11 shareLink 'off' = 관리자 체크 없음
 R12 (v0.3.81 · R12Y52) 리부킹 옛 IV 송부 (iv.customs_prev_iv) = 머리줄 · 창 노랑 · 送付済 경고 아님 · 새 IV 송부 있으면 노랑 0
사용: python tests/test_customs_r12y37.py [--shots 폴더]"""
import argparse
import base64
import io
import json
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path
from urllib.parse import unquote, urlparse, parse_qs

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_graph as TGR   # noqa: E402
import test_customs as TC  # noqa: E402

TOOL = Path(__file__).resolve().parent.parent
RES = {"checks": [], "console_errors": []}
DRIVE = TGR.DRIVE
OURS = TC.OURS
ME = TC.ME
IV = TC.IV
BKG = TC.BKG
REQ = {"kind": "customs_broker_req", "version": "v1.0", "base": ["IV", "PL", "SI"], "unknown": "要確認",
       "domains": {"broker.invalid": {"broker": "テスト倉庫", "extra": ["PHOTO", "搬入票"]}, "lotos.invalid": {"broker": "LOTOS", "extra": []}},
       "addrs": {}}


def ok(name, cond, detail=""):
    RES["checks"].append({"name": name, "ok": bool(cond), "detail": str(detail)[:300]})
    print(("OK  " if cond else "NG  ") + name + (f" — {detail}" if detail and not cond else ""), flush=True)


class Mail(TC.Mail):
    def handle(self, route, request):
        u = urlparse(request.url)
        path = unquote(u.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        if request.method == "GET" and path == "/v1.0/me/messages/D1" and q.get("$select") == "webLink":
            self.calls.append("GET webLink")
            return route.fulfill(status=200, body=json.dumps({"webLink": "https://outlook.example.invalid/owa/?ItemID=D1"}), headers={"Content-Type": "application/json"})
        return super().handle(route, request)


class Share:
    """가짜 SharePoint 링크 송부 (_customs_share 올리기 · createLink)"""
    def __init__(self):
        self.reset()

    def reset(self, scope="anonymous"):
        self.scope = scope
        self.sessions = []      # rel
        self.files = {}         # rel → bytes
        self.links = []         # (item_id, body)
        self.n = 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shots")
    a = ap.parse_args()
    shots = Path(a.shots) if a.shots else Path(tempfile.mkdtemp(prefix="c01_r12y37_shots_"))
    shots.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="c01_r12y37_"))
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
    # 사진 목록: 한 CT 사진 0 (写真なしCT)
    pj = root / "_data" / "photos" / f"{IV}.json"
    ph = json.loads(pj.read_text(encoding="utf-8"))
    cid_rows = {r.get("container_id") for r in t4["rows"]}
    ph_cs = [c for c in ph["containers"] if c["container_id"] in cid_rows]
    nophoto_ct = ph_cs[-1]["ct"]
    ph_cs[-1]["photos"] = []
    pj.write_text(json.dumps(ph, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    n_photos = sum(len(c["photos"]) for c in ph_cs)
    n_docs = len(ph.get("docs") or [])
    pdfp = tmp / "x.pdf"
    TGR.make_pdf(pdfp)
    pdf_b64 = base64.b64encode(pdfp.read_bytes()).decode()
    port = TGR.free_port()
    srv = subprocess.Popen([sys.executable, str(TOOL / "tools" / "serve_local.py"), "--root", str(TOOL / "fixtures"), "--actions", str(tmp / "local_actions"),
                            "--port", str(port), "--today", "2026-11-08"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    mail = Mail()
    share = Share()
    sp = TGR.make_handler(root)
    pre = f"/v1.0/drives/{DRIVE}/root:/{TGR.SP}/"

    def graph(route, request):
        if "/v1.0/me/" in request.url:
            return mail.handle(route, request)
        path = unquote(urlparse(request.url).path)
        J = lambda st, b: route.fulfill(status=st, body=json.dumps(b), headers={"Content-Type": "application/json"})
        if request.method == "POST" and path.startswith(pre + "_customs_share/") and path.endswith(":/createUploadSession"):
            rel = path[len(pre):-len(":/createUploadSession")]
            body = json.loads(request.post_data or "{}")
            if (body.get("item") or {}).get("@microsoft.graph.conflictBehavior") != "fail":
                return J(400, {"error": {"code": "noConflictFail"}})
            share.sessions.append(rel)
            return J(200, {"uploadUrl": "https://upload.example.invalid/s/" + str(len(share.sessions))})
        if request.method == "POST" and path.startswith(f"/v1.0/drives/{DRIVE}/items/") and path.endswith("/createLink"):
            iid = path.split("/")[-2]
            b = json.loads(request.post_data or "{}")
            share.links.append((iid, b))
            return J(200, {"id": "perm-" + iid, "link": {"scope": share.scope, "type": b.get("type"), "webUrl": "https://share.example.invalid/" + iid},
                           "expirationDateTime": b.get("expirationDateTime")})
        return sp(route, request)

    up_buf = {}

    def upload(route, request):
        i = int(request.url.rsplit("/", 1)[-1])
        rel = share.sessions[i - 1]
        rng = request.headers.get("content-range", "")
        a0, rest = rng.replace("bytes ", "").split("-")
        b1, total = rest.split("/")
        buf = up_buf.setdefault(rel, bytearray())
        if int(a0) != len(buf):
            return route.fulfill(status=416, body="{}")
        buf += request.post_data_buffer or b""
        if len(buf) < int(total):
            return route.fulfill(status=202, body=json.dumps({"nextExpectedRanges": [f"{len(buf)}-"]}), headers={"Content-Type": "application/json"})
        share.files[rel] = bytes(buf)
        share.n += 1
        return route.fulfill(status=201, body=json.dumps({"id": f"ITEM{share.n}", "name": rel.split("/")[-1], "size": len(buf)}), headers={"Content-Type": "application/json"})

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
            ans = {"v": True}

            def on_dlg(d):
                dlg.append(d.message)
                if ans["v"] or "もう一つ" not in d.message:
                    d.accept()
                else:
                    d.dismiss()
            page.on("dialog", on_dlg)
            page.route("https://graph.microsoft.com/**", graph)
            page.route("https://upload.example.invalid/**", upload)
            page.route(f"http://127.0.0.1:{port}/__d03fake.html*", lambda r: r.fulfill(status=200, body=TC.fake_d03(pdf_b64, containers), headers={"Content-Type": "text/html; charset=utf-8"}))

            def dvx(r):
                if "crcf9_container_informations" in r.request.url:
                    cs = [{"crcf9_container_no": f"TSTU{i:07d}", "crcf9_type": "45GP", "_crcf9_form_value": "64f45d9f-383c-f011-8c4e-6045bd62e122"} for i in range(3)]
                    return r.fulfill(status=200, body=json.dumps({"value": cs}), headers={"Content-Type": "application/json"})
                if "cr49f_s_is" in r.request.url:
                    return r.fulfill(status=500, body="{}")
                return r.fulfill(status=200, body=json.dumps({"value": [{"_cr49f_sale_contract_id_value": "SC1"}], "_cr49f_buyer_id_value": "BUYER-T"}),
                                 headers={"Content-Type": "application/json"})
            page.route("https://orgde512c6f.crm7.dynamics.com/**", dvx)
            page.goto(f"http://127.0.0.1:{port}/")
            page.wait_for_selector("#ln-splash", timeout=20000)
            ok("탭 제목 v0.3.79", page.title() == "LEENAI C-01 搬入票 v0.3.90", page.title())
            ok("설정: shareLink = on (v0.3.78 · #384) · shareDays 7 · zipStore 있음", page.evaluate("C01.CUSTOMS.shareLink === 'on' && C01.CUSTOMS.shareDays === 7 && typeof C01.zipStore === 'function'"))
            page.evaluate("C01.CUSTOMS.shareLink = 'admin_test'")     # 아래 R1~R11 = 0.3.76 의 관리자 시험 길 그대로 (on 은 tests/test_customs_r12y40.py)
            page.evaluate("C01.CUSTOMS.sendTest = true")
            page.evaluate(TGR.STUB, staff)
            page.evaluate(f"C01.CUSTOMS.d03Url = '/__d03fake.html'; C01.CUSTOMS.ourDomain = '{OURS}'; localStorage.setItem('c01_ports', JSON.stringify({{port: 'all', ports: []}}));")
            page.evaluate("document.getElementById('ln-splash').style.display='none'; document.getElementById('app').style.display=''; C01.app.start(new C01.sources.Graph())")
            page.wait_for_selector("body[data-c01-ready='1']", timeout=20000)

            def openw(s1=True):
                mail.reset(s1=s1)
                page.locator(f'tbody[data-iv="{IV}"] [data-csend]').click()
                page.wait_for_function("() => document.querySelector('.c01-customs') && !document.querySelector('.c01-customs .c01-cstep')", timeout=20000)

            def ready():
                page.select_option("[data-cbl]", "waybill")
                page.wait_for_function("() => !document.querySelector('.c01-customs .c01-cstep')", timeout=15000)
                if page.locator("[data-cack]").count():
                    page.check("[data-cack]")
                if page.locator("[data-cagain]").count():
                    page.check("[data-cagain]")
                t = page.locator("[data-cbody]").input_value().replace("（通関業者の会社名）", "TEST BROKER CORPORATION").replace("（担当者名）", "BROKERA")
                page.fill("[data-cbody]", t)
                page.wait_for_timeout(100)

            def close():
                if page.locator(".c01-customs [data-close]").count():
                    page.click(".c01-customs [data-close]")
                    page.wait_for_timeout(200)

            def setreq(x):
                page.evaluate("(x) => { C01.app._api().S.customsReq = x; }", x)

            # R1 req 없음
            setreq(None)
            openw(); ready()
            ok("R1 req 없음 = 노랑 0 · 送信 파랑 · 下書きで保存 회색", page.locator("[data-creq]").count() == 0 and "c01-btn-pri" in (page.get_attribute("[data-csendgo]", "class") or "")
               and "c01-btn-ghost2" in (page.get_attribute("[data-cdraftgo]", "class") or "") and page.locator("[data-csendgo]").is_enabled(), page.locator("[data-cwhy]").inner_text())
            ok("R1 관리자 아님 = 링크 시험 체크 없음", page.locator("[data-csharetest]").count() == 0)
            close()
            # R2 LOTOS 꼴
            setreq(dict(REQ, domains={"broker.invalid": {"broker": "LOTOS", "extra": []}}))
            openw(); ready()
            ok("R2 LOTOS 꼴 (추가 없음) = 노랑 0 · 送信 그대로 파랑 · 가능", page.locator("[data-creq]").count() == 0 and "c01-btn-pri" in (page.get_attribute("[data-csendgo]", "class") or "")
               and page.locator("[data-csendgo]").is_enabled() and page.evaluate("C01.customs._req().extra.length") == 0)
            close()
            # R3 추가 필요
            setreq(REQ)
            openw(); ready()
            t = page.locator("[data-creq='extra']").inner_text() if page.locator("[data-creq='extra']").count() else ""
            ok("R3 노랑 문구 (写真（PHOTO）・搬入票) · 맨 위", "この通関業者は 写真（PHOTO）・搬入票 も必要です。" in t and "下書きで保存して、Outlook で添付してから送信してください。" in t
               and page.evaluate("document.querySelector('.c01-customs .c01-mbody').firstElementChild.matches('[data-creq]')"), t)
            ok("R3 기본 = 下書きで保存 (파랑) · 送信 = 회색 · 꺼짐", "c01-btn-pri" in (page.get_attribute("[data-cdraftgo]", "class") or "") and page.locator("[data-cdraftgo]").is_enabled()
               and page.locator("[data-csendgo]").is_disabled(), page.locator("[data-cwhy]").inner_text())
            page.screenshot(path=str(shots / "r3_extra.png"), full_page=False)
            page.check("[data-cextra]")
            ok("R3 「追加書類は別に送ります」 체크 → 送信 가능", page.locator("[data-csendgo]").is_enabled(), page.evaluate("C01.customs._sendBlockers()"))
            close()
            setreq(dict(REQ, domains={"broker.invalid": {"broker": "テスト", "extra": ["PHOTO"]}}))
            openw(); ready()
            t = page.locator("[data-creq='extra']").inner_text() if page.locator("[data-creq='extra']").count() else ""
            ok("R3 필요한 것만 (PHOTO 만 = 搬入票 글자 없음)", "写真（PHOTO） も必要です" in t and "搬入票" not in t, t)
            close()
            # R4 要確認
            setreq(dict(REQ, domains={"other.invalid": {"broker": "X", "extra": []}}))
            openw(); ready()
            t = page.locator("[data-creq='unknown']").inner_text() if page.locator("[data-creq='unknown']").count() else ""
            ok("R4 표에 없는 도메인 = 「必要書類を確認してください」 · 送信 막지 않음", "必要書類を確認してください" in t and "broker.invalid" in t and page.locator("[data-csendgo]").is_enabled(), t)
            close()
            # R5 下書き (道 1)
            setreq(REQ)
            openw(); ready()
            n_d = len(dlg)
            page.click("[data-cdraftgo]")
            page.wait_for_selector("[data-cdraftok]", timeout=15000)
            ok("R5 확인 창 1번 (Outlook で 写真（PHOTO）・搬入票 を添付)", len(dlg) == n_d + 1 and "下書き に保存" in dlg[-1] and "写真（PHOTO）・搬入票 を添付" in dlg[-1], dlg[n_d:])
            ok("R5 send 0 · createReplyAll → PATCH → 첨부 → 다시 읽기 → webLink", mail.sends == 0 and
               [c.split(" ")[0] + " " + c.split("/")[-1] for c in mail.calls if "D1" in c or "createReplyAll" in c or "webLink" in c][-6:] ==
               ["POST createReplyAll", "PATCH D1", "POST attachments", "GET D1", "GET attachments", "GET GET webLink"], mail.calls[-8:])
            ok("R5 「Outlook で開く」 링크", page.get_attribute("[data-cdraftlink]", "href") == "https://outlook.example.invalid/owa/?ItemID=D1")
            cs = [json.loads(f.read_text(encoding="utf-8")) for f in (root / "_actions").rglob("*.json")]
            cd = [x for x in cs if x.get("action") == "customs_draft"]
            v = cd[0]["value"] if cd else {}
            ok("R5 _actions customs_draft 1 (customs_sent 0) · test · draft_id · web_link · extra", len(cd) == 1 and not [x for x in cs if x.get("action") == "customs_sent"]
               and v.get("test") is True and v.get("draft_id") == "D1" and v.get("web_link", "").startswith("https://outlook") and v.get("extra") == ["PHOTO", "搬入票"] and v.get("route") == "s1_reply", v)
            close()
            # 실전 下書き 기록 흉내 (test false) → 머리줄
            page.evaluate("""(iv) => { const A = C01.app._api(); A.S.mine = (A.S.mine || []).concat([{action: {action: 'customs_draft', action_id: 'cd-live', iv: iv, by: 'staff.a@example.invalid',
                at: '2026-11-08T10:00:00+09:00', value: {test: false, web_link: 'https://outlook.example.invalid/x'}}}]); A.render(); }""", IV)
            hd = page.locator(f'tbody[data-iv="{IV}"] .c01-ivhead').inner_text()
            ok("R5 실전 下書き 기록 → 머리줄 「下書き作成済」 · 送付済 아님", "下書き作成済" in hd and "送付済" not in hd, hd)
            # R6 두 번 누름
            openw(); ready()
            ok("R6 창 = 「下書き作成済 … まだ送られていません」", page.locator("[data-cdraftrec]").count() == 1)
            ans["v"] = False
            n_d, n_calls = len(dlg), len(mail.calls)
            page.click("[data-cdraftgo]")
            page.wait_for_timeout(500)
            ok("R6 두 번째 = 「もう一つ作りますか」 확인 · 취소 = 下書き 0", len(dlg) == n_d + 2 and "もう一つ作りますか" in dlg[-1] and not any("createReplyAll" in c for c in mail.calls[n_calls:]), dlg[n_d:])
            ans["v"] = True
            close()
            # R7 下書き (道 2)
            S1 = {"kind": "customs_s1", "built_at": "2026-11-08T09:00:00+09:00", "by_pol": {}, "ivs": {IV: {
                "s1": {"k": "k1", "subject": f"新規通関依頼:BKG#{BKG}, CUT11/10 (KOBE TO TEST)", "at": "2026-11-05T10:00:00", "from": "staff.c@" + OURS, "from_name": "STAFF C"},
                "last": {"k": "k2", "subject": f"RE: 新規通関依頼:BKG#{BKG}", "at": "2026-11-06T12:00:00", "from": "broker.a@broker.invalid", "from_name": "BROKERA",
                         "to": [{"a": "staff.c@" + OURS, "n": "STAFF C"}], "cc": [], "body": "承知しました。", "body_ok": True},
                "staff": "staff.c@" + OURS, "staff_name": "STAFF C", "n_conv": 3, "s1_count": 1}}}
            page.evaluate("(x) => { C01.app._api().S.customsS1 = x; }", S1)
            openw(s1=False); ready()
            page.click("[data-cdraftgo]")
            page.wait_for_selector("[data-cdraftok]", timeout=15000)
            ok("R7 道 2 下書き = POST me/messages (새 下書き) · createReplyAll 0 · send 0", mail.newdraft is not None and not any("createReplyAll" in c for c in mail.calls) and mail.sends == 0, mail.calls[-6:])
            close()
            page.evaluate("C01.app._api().S.customsS1 = null")
            # R8 엔진이 본 메일
            page.evaluate("(iv) => { const A = C01.app._api(); A.ivById(iv).customs_mail = [{at: '2026-11-08T11:00:00', from: 'staff.a@example.invalid', test: true}]; A.render(); }", IV)
            hd = page.locator(f'tbody[data-iv="{IV}"] .c01-ivhead').inner_text()
            ok("R8 [test] 메일만 = 送付済 아님", "送付済" not in hd, hd)
            page.evaluate("(iv) => { const A = C01.app._api(); A.ivById(iv).customs_mail.push({at: '2026-11-08T12:00:00', from: 'staff.a@example.invalid', test: false}); A.render(); }", IV)
            hd = page.locator(f'tbody[data-iv="{IV}"] [data-csend]').inner_text()
            ok("R8 엔진이 본 실전 메일 = 「✓ 通関書類 送付済 11/08 · 이름」 (data-csent-mail)", "✓ 通関書類 送付済 11/08" in hd and page.locator(f'tbody[data-iv="{IV}"] [data-csent-mail]').count() == 1, hd)
            openw(); ready()
            ok("R8 창 = 送付済み 상자 (메일 1통) · 「もう一度送る」", "送付済み" in page.locator(".c01-customs").inner_text() and page.locator("[data-cagain]").count() == 1)
            close()
            page.evaluate("""(iv) => { const A = C01.app._api(); delete A.ivById(iv).customs_mail; A.S.mine = (A.S.mine || []).filter(m => (m.action || m).action !== 'customs_draft'); A.render(); }""", IV)
            # R12 (v0.3.81 · R12Y52 · #400 후속): 리부킹 = 옛 IV 송부 기록 (iv.customs_prev_iv) → 노랑 (두 번 송부 경고 아님)
            ok("R12 처음 = 노랑 0 (customs_prev_iv 없음)", page.locator(f'tbody[data-iv="{IV}"] [data-cprev]').count() == 0)
            page.evaluate("(iv) => { const A = C01.app._api(); A.ivById(iv).customs_prev_iv = [{iv: 'TST0000-OLD', at: '2026-11-07T10:00:00', by: 'staff.a@example.invalid', src: 'mail'}, {iv: 'TST0000-OLD', at: '2026-11-07T10:00:00', by: 'staff.a@example.invalid', src: 'tool'}]; A.render(); }", IV)
            hd = page.locator(f'tbody[data-iv="{IV}"] .c01-ivhead').inner_text()
            pv = page.locator(f'tbody[data-iv="{IV}"] [data-cprev]')
            ok("R12 머리줄 노랑 「前の IV (TST0000-OLD) で 11/07 送付済 · IV 番号が変わりました · 再送が必要か確認」 · 送付済 버튼 아님",
               pv.count() == 1 and pv.inner_text() == "前の IV (TST0000-OLD) で 11/07 送付済 · IV 番号が変わりました · 再送が必要か確認" and "✓ 通関書類 送付済" not in hd
               and page.locator(f'tbody[data-iv="{IV}"] [data-csent-mail]').count() == 0, hd)
            openw(); ready()
            bx = page.locator("[data-cprevbox]")
            ok("R12 창 = 노랑 상자 1 · 送付済み 빨강 상자 0 · 「もう一度送る」 0 · 막는 이유에 送付済み 없음",
               bx.count() == 1 and "IV 番号が変わりました" in bx.inner_text() and page.locator("[data-cagain]").count() == 0
               and not any("送付済み" in x for x in page.evaluate("C01.customs._sendBlockers()")), page.evaluate("C01.customs._sendBlockers()"))
            close()
            page.evaluate("(iv) => { const A = C01.app._api(); A.ivById(iv).customs_mail = [{at: '2026-11-08T12:00:00', from: 'staff.a@example.invalid', test: false}]; A.render(); }", IV)
            ok("R12 새 IV 로 보낸 메일 있음 = 「✓ 通関書類 送付済」 그대로 · 노랑 0", page.locator(f'tbody[data-iv="{IV}"] [data-csent-mail]').count() == 1 and page.locator(f'tbody[data-iv="{IV}"] [data-cprev]').count() == 0)
            openw(); ready()
            ok("R12 창 = 送付済み 빨강 (지금 경고 그대로) · 노랑 상자 0", page.locator("[data-cagain]").count() == 1 and page.locator("[data-cprevbox]").count() == 0)
            close()
            page.evaluate("(iv) => { const A = C01.app._api(); delete A.ivById(iv).customs_mail; delete A.ivById(iv).customs_prev_iv; A.render(); }", IV)
            # R9 링크 (관리자 시험)
            page.evaluate("C01.app._api().S.me.admin = true")
            page.evaluate("C01.CUSTOMS.sendTest = false")          # 실제 모드 설정이어도 관리자 시험 = 자기 1명 · [test]
            openw(); ready()
            ok("R9 관리자 = 「写真・搬入票リンクの試験」 체크 보임 · 처음 = 꺼짐 (下書き 기본)", page.locator("[data-csharetest]").count() == 1 and not page.evaluate("C01.customs._shareOn()"))
            page.check("[data-csharetest]")
            page.wait_for_timeout(200)
            t = page.locator("[data-creq='share']").inner_text() if page.locator("[data-creq='share']").count() else ""
            sf = page.evaluate("C01.customs._shareFiles()")
            ok("R9 체크 → 링크 안내 (7 日 · PHOTO.zip n 枚 · 搬入票.zip n) · 시험 모드 띠", "リンク で送ります" in t and "7 日" in t and f"写真 {n_photos} 枚" in t and f"搬入票.zip: {n_docs} ファイル" in t
               and page.locator("[data-ctrial]").count() == 1, t)
            ok("R9 写真なしCT 표시", page.locator("[data-cnophoto]").count() == 1 and nophoto_ct in page.locator("[data-cnophoto]").inner_text() and sf["noPhoto"] == [nophoto_ct], sf.get("noPhoto"))
            ok("R9 제목 [test] · 送信 파랑 (링크면 下書き 기본 아님) · 가능", page.locator(".c01-csubj").inner_text().startswith("[test] ") and "c01-btn-pri" in (page.get_attribute("[data-csendgo]", "class") or "")
               and page.locator("[data-csendgo]").is_enabled(), page.evaluate("C01.customs._sendBlockers()"))
            page.screenshot(path=str(shots / "r9_share.png"), full_page=False)
            share.reset()
            n_d = len(dlg)
            page.click("[data-csendgo]")
            page.wait_for_function("() => !document.querySelector('.c01-customs')", timeout=30000)
            page.wait_for_timeout(500)
            P = mail.patch or {}
            to = [x["emailAddress"]["address"] for x in P.get("toRecipients", [])]
            html = P.get("body", {}).get("content", "")
            ok("R9 확인 창 = 시험 (자기) · 링크 안내 줄", "【試験】" in dlg[n_d] and "リンク" in dlg[n_d], dlg[n_d:])
            ok("R9 올림 = _customs_share/{IV}/{時刻}/ PHOTO.zip · 搬入票.zip (conflictBehavior fail)", len(share.sessions) == 2 and all(s.startswith(f"_customs_share/{IV}/") for s in share.sessions)
               and [s.split("/")[-1] for s in share.sessions] == ["PHOTO.zip", "搬入票.zip"] and len(share.sessions[0].split("/")[2]) == 15, share.sessions)
            lk = [b for _, b in share.links]
            ok("R9 createLink = view · anonymous · 7 일 뒤 기한", len(lk) == 2 and all(b.get("type") == "view" and b.get("scope") == "anonymous" for b in lk)
               and all(6.9 < (time.mktime(time.strptime(b["expirationDateTime"][:19], "%Y-%m-%dT%H:%M:%S")) - time.mktime(time.gmtime())) / 86400 < 7.1 for b in lk), lk)
            ok("R9 받는 사람 = 나 1명 · [test] · send 1 · PDF 첨부 1", to == [ME] and str(P.get("subject", "")).startswith("[test] ") and mail.sends == 1 and len(mail.atts) == 1, [to, P.get("subject"), mail.sends])
            ok("R9 본문 = 「写真・搬入票は下記リンクからダウンロードしてください（m/d まで有効）」 + 링크 2", "写真・搬入票は下記リンクからダウンロードしてください（" in html and "まで有効）" in html
               and "https://share.example.invalid/ITEM1" in html and "https://share.example.invalid/ITEM2" in html and html.index("share.example.invalid") < html.index("QUOTED"), html[:300])
            zp = zipfile.ZipFile(io.BytesIO(share.files[share.sessions[0]]))
            names = zp.namelist()
            ok("R9 PHOTO.zip = CT 폴더 · 사진 수 = 목록 · 내용 = 원본 · 깨짐 0", len(names) == n_photos and all("/" in n for n in names) and zp.testzip() is None
               and zp.read(names[0]) == (root / ph_cs[0]["photos"][0]["path"]).read_bytes(), names[:3])
            zd = zipfile.ZipFile(io.BytesIO(share.files[share.sessions[1]]))
            ok("R9 搬入票.zip = 파일 수 = 목록 · 이름 그대로 (일본어 UTF-8)", len(zd.namelist()) == n_docs and zd.testzip() is None and all(n.startswith("搬入票_") for n in zd.namelist()), zd.namelist())
            cs = [json.loads(f.read_text(encoding="utf-8")) for f in (root / "_actions").rglob("*.json")]
            sent = [x for x in cs if x.get("action") == "customs_sent" and (x.get("value") or {}).get("share")]
            sh = sent[0]["value"]["share"] if sent else {}
            ok("R9 기록 customs_sent.share (place sp · 파일 2 · item id · 경로 · 크기 · 장수 · 기한 · 写真なしCT) · test true",
               len(sent) == 1 and sent[0]["value"]["test"] is True and sh.get("place") == "sp" and len(sh.get("files", [])) == 2 and sh["files"][0]["item_id"] == "ITEM1"
               and sh["files"][0]["path"] == share.sessions[0] and sh["files"][0]["n"] == n_photos and sh["files"][0]["size"] == len(share.files[share.sessions[0]])
               and sh.get("days") == 7 and sh.get("expires") and sh.get("no_photo_ct") == [nophoto_ct], sh)
            # R10 anonymous 아님
            share.reset(scope="organization")
            openw(); ready()
            page.check("[data-csharetest]")
            page.wait_for_timeout(200)
            page.click("[data-csendgo]")
            page.wait_for_selector("[data-creq='sharefail']", timeout=30000)
            # v0.3.78 (R12Y40 · #384): 링크 못 만듦 = 보내지 않고 0.3.76 동작 (노랑 「リンクを作れませんでした」 + 「追加書類は別に送ります」) · 이유에 「リンクを知っている全員」
            ok("R10 범위 organization = send 0 · 노랑 「リンクを作れませんでした」 (이유 「リンクを知っている全員」) · 「追加書類は別に送ります」 다시 나옴",
               mail.sends == 0 and "写真・搬入票のリンクを作れませんでした。Outlook で添付してください" in page.locator("[data-creq='sharefail']").inner_text()
               and "リンクを知っている全員" in page.locator("[data-creq='sharefail']").inner_text() and page.locator("[data-cextra]").count() == 1,
               page.locator("[data-creq='sharefail']").inner_text())
            close()
            page.evaluate("() => { const e = document.getElementById('c01-cerr'); if (e) e.remove(); }")
            # R11 off
            page.evaluate("C01.CUSTOMS.shareLink = 'off'")
            openw(); ready()
            ok("R11 shareLink off = 관리자도 체크 없음 · 노랑 = 下書き 안내", page.locator("[data-csharetest]").count() == 0 and page.locator("[data-creq='extra']").count() == 1)
            close()
            page.evaluate("C01.CUSTOMS.shareLink = 'admin_test'; C01.CUSTOMS.sendTest = true")
            # zipStore 단위 (CRC · 빈 이름 거부)
            okz = page.evaluate("""() => { const z = C01.zipStore([{name: 'a/b.txt', data: new TextEncoder().encode('hello')}]); let bad = false;
                try { C01.zipStore([{name: 'x', data: new Uint8Array(1)}, {name: 'x', data: new Uint8Array(1)}]); } catch (e) { bad = true; }
                return [Array.from(z.slice(0, 4)), C01.zipStore._crc32(new TextEncoder().encode('hello')), bad]; }""")
            ok("zipStore: PK 머리 · crc32('hello') = 0x3610a686 · 같은 이름 거부", okz[0] == [0x50, 0x4b, 3, 4] and okz[1] == 0x3610a686 and okz[2] is True, okz)
            page.screenshot(path=str(shots / "customs_r12y37.png"), full_page=False)
            errs = [e for e in RES["console_errors"] if "favicon" not in e and "404" not in e and not ("500" in e and "Failed to load resource" in e)]
            ok("콘솔 오류 0", not errs, errs[:3])
            br.close()
    finally:
        srv.terminate()
    n_ng = sum(1 for c in RES["checks"] if not c["ok"])
    print(json.dumps({"checks": len(RES["checks"]), "ng": n_ng, "shots": str(shots)}, ensure_ascii=False))
    sys.exit(1 if n_ng else 0)


if __name__ == "__main__":
    main()
