# ✦ Powered by LEENAI Automation System — v0.3.79 (R12Y42 · #385) 통관 송부 링크 문단 자리 (「宜しくお願い致します。」 바로 다음 · 서명 앞) · 우리 쪽 주소는 늘 To → CC
"""Playwright · 가명 fixtures · 가짜 Graph · 가짜 D-03 · 가짜 SharePoint (실제 메일 · SharePoint · COMPASS 호출 0). 확인:
 P1 shareCut 본문 꼴 5 (기본 · 인사 줄 없음 = 서명 앞 · 서명 없음 = 꼬리 앞 · 아무것도 없음 = 끝 · 직원이 고친 인사)
 P2 baseRecips 4 (NHK 꼴 통관업자 → 우리 직원 To = CC 로 · 사외 To 섞임 · 사외만 · 사외 0 = ours_only 그대로)
 P3 下書き + 링크 = 본문 순서 (인사 → 링크 → 서명 → 꼬리 → 인용) · NHK 꼴 PATCH 받는 사람 (To 사내 0 · 중복 0)
 P4 送信 + 링크 = 같은 순서 · 받는 사람 = 창과 같음 · P5 링크 없음 = 본문 그대로
사용: python tests/test_customs_r12y42.py [--shots 폴더]"""
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
from urllib.parse import unquote, urlparse

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_graph as TGR   # noqa: E402
import test_customs as TC  # noqa: E402
import test_customs_r12y37 as T37  # noqa: E402

TOOL = Path(__file__).resolve().parent.parent
RES = {"checks": [], "console_errors": []}
DRIVE = TGR.DRIVE
OURS = TC.OURS
ME = TC.ME
IV = TC.IV
BKG = TC.BKG
BR_A, BR_B = "broker.a@broker.invalid", "broker.b@broker.invalid"
ST_B, ST_Z, RCP = "staff.b@" + OURS, "staff.z@" + OURS, "rcp@" + OURS
REQ = T37.REQ


def ok(name, cond, detail=""):
    RES["checks"].append({"name": name, "ok": bool(cond), "detail": str(detail)[:300]})
    print(("OK  " if cond else "NG  ") + name + (f" — {detail}" if detail and not cond else ""), flush=True)


class Mail(T37.Mail):
    """대화를 바꿀 수 있는 가짜 메일함 (conv = [(id, from, to, cc, at)] · 첫 줄 = ①)"""
    conv = None

    def msgs(self):
        if not self.conv:
            return super().msgs()
        r = lambda a: {"emailAddress": {"address": a, "name": a.split("@")[0].upper()}}
        out = []
        for i, (mid, frm, to, cc, at) in enumerate(self.conv):
            subj = (f"新規通関依頼:BKG#{BKG}, CUT11/10 (TOKYO TO TEST)" if i == 0 else f"RE: 新規通関依頼:BKG#{BKG}, CUT11/10 (TOKYO TO TEST)")
            out.append({"id": mid, "subject": subj, "conversationId": "CONV1", "sentDateTime": at, "receivedDateTime": at, "isDraft": False,
                        "from": r(frm), "toRecipients": [r(x) for x in to], "ccRecipients": [r(x) for x in cc], "internetMessageId": "<" + mid + ">",
                        "bodyPreview": "お疲れ様です。" if frm.endswith("@" + OURS) else "いつもお世話になっております。"})
        return out


S1 = ("M1", ME, [BR_A], [ST_B], "2026-11-05T01:00:00Z")
R1 = ("M2", BR_A, [ME], [BR_B, ST_B], "2026-11-05T03:00:00Z")
CONVS = {
    "W1": [S1, R1],
    "W2": [S1, R1, ("M3", ST_Z, [BR_A], [BR_B, RCP], "2026-11-05T05:00:00Z")],
    "W3": [S1, R1, ("M3", ST_Z, [ST_B], [], "2026-11-05T05:00:00Z")],
    "W4": [S1, R1, ("M3", ST_Z, [ST_B], [BR_A], "2026-11-05T05:00:00Z")],
    "W5": [S1, ("M2", BR_B, [ST_B], [ME], "2026-11-05T03:00:00Z")],
    "W6": [("M1", ME, [ST_B], [], "2026-11-05T01:00:00Z"), ("M3", ST_B, [ST_Z], [RCP], "2026-11-05T05:00:00Z")],
    "NHK": [S1, ("M2", BR_B, [ST_B], [RCP], "2026-11-05T03:00:00Z")],
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shots")
    a = ap.parse_args()
    shots = Path(a.shots) if a.shots else Path(tempfile.mkdtemp(prefix="c01_r12y42_shots_"))
    shots.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="c01_r12y42_"))
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
    pj = root / "_data" / "photos" / f"{IV}.json"
    ph = json.loads(pj.read_text(encoding="utf-8"))
    cid_rows = {r.get("container_id") for r in t4["rows"]}
    ph_cs = [c for c in ph["containers"] if c["container_id"] in cid_rows]
    n_photos = sum(len(c["photos"]) for c in ph_cs)
    n_docs = len(ph.get("docs") or [])
    pdfp = tmp / "x.pdf"
    TGR.make_pdf(pdfp)
    pdf_b64 = base64.b64encode(pdfp.read_bytes()).decode()
    port = TGR.free_port()
    srv = subprocess.Popen([sys.executable, str(TOOL / "tools" / "serve_local.py"), "--root", str(TOOL / "fixtures"), "--actions", str(tmp / "local_actions"),
                            "--port", str(port), "--today", "2026-11-08"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    mail = Mail()
    share = T37.Share()
    sp = TGR.make_handler(root)
    pre = f"/v1.0/drives/{DRIVE}/root:/{TGR.SP}/"

    def graph(route, request):
        if "/v1.0/me/" in request.url:
            return mail.handle(route, request)
        path = unquote(urlparse(request.url).path)
        J = lambda st, b: route.fulfill(status=st, body=json.dumps(b), headers={"Content-Type": "application/json"})
        if request.method == "POST" and path.startswith(pre + "_customs_share/") and path.endswith(":/createUploadSession"):
            rel = path[len(pre):-len(":/createUploadSession")]
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
            dlg = []
            page.on("dialog", lambda d: (dlg.append(d.message), d.accept()))
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
            ok("탭 제목 v0.3.79", page.title() == "LEENAI C-01 搬入票 v0.3.85", page.title())
            ok("설정: shareLink on · sendTest false · shareTimeoutSec 180", page.evaluate("C01.CUSTOMS.shareLink === 'on' && C01.CUSTOMS.sendTest === false && C01.CUSTOMS.shareTimeoutSec === 180"))
            page.evaluate(TGR.STUB, staff)
            page.evaluate(f"C01.CUSTOMS.d03Url = '/__d03fake.html'; C01.CUSTOMS.ourDomain = '{OURS}'; localStorage.setItem('c01_ports', JSON.stringify({{port: 'all', ports: []}}));")
            page.evaluate("document.getElementById('ln-splash').style.display='none'; document.getElementById('app').style.display=''; C01.app.start(new C01.sources.Graph())")
            page.wait_for_selector("body[data-c01-ready='1']", timeout=20000)

            def openw(conv=None):
                mail.reset(s1=True)
                mail.conv = conv
                share.reset()
                up_buf.clear()
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

            def clean():
                page.evaluate("""(iv) => { const A = C01.app._api(); delete A.ivById(iv).customs_mail; A.S.mine = []; A.render(); }""", IV)
                for f in (root / "_actions").rglob("*.json"):
                    f.unlink()

            def rcp(P):
                return ([x["emailAddress"]["address"] for x in (P or {}).get("toRecipients", [])], [x["emailAddress"]["address"] for x in (P or {}).get("ccRecipients", [])])

            page.evaluate("(x) => { C01.app._api().S.customsReq = x; }", REQ)
            # P1 링크 문단 자리 (shareCut) — 본문 꼴 5
            SIG = "----------------------------------------\nTEST STAFF\nCOMPANY\nstaff@example.invalid"
            FOOT = "✦ Powered by LEENAI Automation System"
            cases = {
                "기본 (인사 줄 · 서명 · 꼬리)": ("BROKER\nA 様\n\nいつもお世話になっております。\n書類を送付いたします。\n\n宜しくお願い致します。\n\n" + SIG + "\n\n" + FOOT, "宜しくお願い致します。"),
                "인사 줄 없음 = 서명 앞": ("BROKER\nA 様\n\n書類を送付いたします。\n\n" + SIG + "\n\n" + FOOT, "書類を送付いたします。\n\n"),
                "서명 없음 = 꼬리 앞": ("BROKER\nA 様\n\n書類を送付いたします。\n\n" + FOOT, "書類を送付いたします。\n\n"),
                "아무것도 없음 = 끝": ("BROKER\nA 様\n\n書類を送付いたします。", "書類を送付いたします。"),
                "직원이 고친 인사 (よろしくお願いいたします。) · 서명 아래 인사 무시": ("本文\nよろしくお願いいたします。\n\n" + SIG + "\n宜しくお願い致します。\n\n" + FOOT, "よろしくお願いいたします。"),
            }
            for name, (body, head) in cases.items():
                k = page.evaluate("(t) => C01.customs._shareCut(t)", body)
                ok(f"P1 자리 · {name}", body[:k].endswith(head), [k, body[:k][-30:]])
            # P2 받는 사람 (baseRecips) — 우리 쪽 주소는 늘 To → CC
            R = lambda a: {"a": a, "n": ""}
            recs = {
                "NHK 꼴: 통관업자 → 우리 직원 To · rcp CC": ({"id": "x", "from": BR_B, "to": [R(ST_B)], "cc": [R(RCP)]}, [BR_B], [ST_B, RCP], "reply_all"),
                "통관업자 → 우리 To + 사외 To": ({"id": "x", "from": BR_A, "to": [R(ST_B), R(BR_B)], "cc": [R(RCP)]}, [BR_A, BR_B], [ST_B, RCP], "reply_all"),
                "통관업자 → 사외 To 만 (그대로)": ({"id": "x", "from": BR_A, "to": [R(BR_B)], "cc": [R(ST_B)]}, [BR_A, BR_B], [ST_B], "reply_all"),
                "사외 0 (ours_only 그대로 · 확인 체크)": ({"id": "x", "from": ST_B, "to": [R(ST_Z)], "cc": [R(RCP)]}, [ST_Z], [RCP], "ours_only"),
            }
            page.evaluate(f"C01.CUSTOMS.ourDomain = '{OURS}'")
            for name, (L, eto, ecc, ehow) in recs.items():
                b = page.evaluate("(L) => C01.customs._baseRecips(L, [])", L)
                got = ([x["a"] for x in b["to"]], [x["a"] for x in b["cc"]], b["how"])
                ok(f"P2 {name}", got == (eto, ecc, ehow), got)
            # P3 下書き · 링크 = 본문 「宜しくお願い致します。」 → 링크 → 서명 → 꼬리 → 인용 · NHK 꼴 받는 사람 (To 사내 0 · 중복 0)
            openw(CONVS["NHK"]); ready()
            rc = page.evaluate("C01.customs._recips()")
            ok("P3 창 받는 사람 = To 통관업자 만 · 우리 직원 · rcp = CC · 노랑 「宛先に社内の人」 0", [x["a"] for x in rc["to"]] == [BR_B] and [x["a"] for x in rc["cc"]] == [ST_B, RCP]
               and page.locator("[data-cours]").count() == 0, rc)
            page.click("[data-cdraftgo]")
            page.wait_for_selector("[data-cdraftok]", timeout=30000)
            P = mail.patch or {}
            html = P.get("body", {}).get("content", "")
            to, cc = rcp(P)
            ok("P3 下書き PATCH 받는 사람 = To [통관업자] · CC [직원 · rcp] · 중복 0 · send 0", to == [BR_B] and cc == [ST_B, RCP] and len(set(to + cc)) == len(to + cc) and mail.sends == 0, [to, cc])
            pos = [html.find(x) for x in ("宜しくお願い致します。", "下記リンクから", "----------", "✦ Powered by", "QUOTED")]
            ok("P3 본문 순서 = 宜しくお願い致します。 → 링크 → 서명 → ✦ Powered by → 인용", all(p >= 0 for p in pos) and pos == sorted(pos), pos)
            cd = actions("customs_draft")
            ok("P3 customs_draft to_how reply_all · share 2", len(cd) == 1 and cd[0]["value"].get("to_how") == "reply_all" and len(cd[0]["value"].get("share", {}).get("files", [])) == 2, cd and cd[0]["value"].get("to_how"))
            page.screenshot(path=str(shots / "p3_draft_nhk.png"), full_page=False)
            close(); clean()
            # P4 送信 · 링크 = 같은 순서 · 받는 사람 = 창과 같음
            openw(CONVS["NHK"]); ready()
            page.click("[data-csendgo]")
            page.wait_for_function("() => !document.querySelector('.c01-customs')", timeout=30000)
            page.wait_for_timeout(300)
            P = mail.patch or {}
            html = P.get("body", {}).get("content", "")
            to, cc = rcp(P)
            pos = [html.find(x) for x in ("宜しくお願い致します。", "下記リンクから", "----------", "✦ Powered by")]
            ok("P4 送信 = send 1 · To [통관업자] · CC [직원 · rcp] · 본문 순서 같음", mail.sends == 1 and to == [BR_B] and cc == [ST_B, RCP] and all(p >= 0 for p in pos) and pos == sorted(pos), [to, cc, pos])
            clean()
            # P5 링크 없음 (LOTOS) = 본문 한 덩어리 그대로 (링크 문단 0)
            page.evaluate("(x) => { C01.app._api().S.customsReq = x; }", dict(REQ, domains={"broker.invalid": {"broker": "LOTOS", "extra": []}}))
            openw(); ready()
            page.click("[data-cdraftgo]")
            page.wait_for_selector("[data-cdraftok]", timeout=30000)
            html = (mail.patch or {}).get("body", {}).get("content", "")
            ok("P5 LOTOS 下書き = 링크 문단 0 · 서명 · 꼬리 그대로", "下記リンク" not in html and "data-cshare" not in html and "✦ Powered by" in html and "----------" in html, html[:200])
            close(); clean()
            page.evaluate("(x) => { C01.app._api().S.customsReq = x; }", REQ)
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
