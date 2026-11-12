# ✦ Powered by LEENAI Automation System — C-01 搬入票 TOOL graph 모드 시험 (R7A · Playwright · 가명 fixtures · 가짜 Graph — 실제 SharePoint 호출 0)
"""TOOL 을 127.0.0.1 로 열고, LEENAI_COMMON 로그인 결과 (토큰 · 사용자 · 마스터) 는 가짜로 바꾸고,
https://graph.microsoft.com/ 요청은 page.route 로 가로채 가명 fixtures 폴더 (임시 사본 = HANNYU_TOOL 흉내) 에서 돌려준다.
확인: 로그인 버튼 활성 · graph 로 実況表 · 사진 blob 표시 · 로그인한 사람 = 担当者 · _actions 쓰기 = HANNYU_TOOL/_actions/{날짜}/ 만 ·
      같은 id 다시 쓰기 거부 (409) · 처리 표시 (.done) 읽기 · Graph 주소는 모두 drives/{드라이브}/root:/HANNYU_TOOL/ 아래 · 콘솔 오류 0.
      v0.3.3 (R7C): 別タブで開く = webUrl 새 탭 · 없는 파일 이유 표시 · 파일 칩 · 파일 지정 없는 항목 = IV 서류.
      v0.3.2 (R7B): PDF (搬入票 · 未分類 FAX) = pdf.js 로 canvas 에 그림 (빈 화면 아님) · 페이지 넘김 · 회전 · 확대 · 別タブで開く ·
      pdf.js 를 못 읽으면 iframe 로 물러남 · 오래된 未分類 FAX 숨김 + 「古い未分類 FAX も表示」.
사용: python tests/test_graph.py [--shots 폴더]"""
import argparse
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

TOOL = Path(__file__).resolve().parent.parent
RES = {"checks": [], "console_errors": [], "graph_urls": []}
DRIVE = "b!TESTDRIVE"


def ok(name, cond, detail=""):
    RES["checks"].append({"name": name, "ok": bool(cond), "detail": str(detail)[:300]})
    print(("OK  " if cond else "NG  ") + name + (f" — {detail}" if detail and not cond else ""), flush=True)


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def make_pdf(path):
    """가명 2쪽 PDF (글자 없음): 1쪽 = 왼쪽 절반 검은 사각형 · 2쪽 = 오른쪽 절반."""
    pages = [b"0 0 0 rg 40 40 220 760 re f", b"0 0 0 rg 335 40 220 760 re f"]
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R 5 0 R] /Count 2 >>"]
    for i, c in enumerate(pages):
        objs.append(b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents %d 0 R >>" % (4 + 2 * i))
        objs.append(b"<< /Length %d >>\nstream\n" % len(c) + c + b"\nendstream")
    out = bytearray(b"%PDF-1.4\n")
    offs = []
    for i, o in enumerate(objs):
        offs.append(len(out))
        out += b"%d 0 obj\n" % (i + 1) + o + b"\nendobj\n"
    x = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1) + b"".join(b"%010d 00000 n \n" % v for v in offs)
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, x)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(bytes(out))


INK = """(sel) => { const c = document.querySelector(sel); if (!c) return null; const g = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
  let L = 0, R = 0; for (let y = 0; y < c.height; y += 4) for (let x = 0; x < c.width; x += 4) { const i = (y * c.width + x) * 4; if (g[i] < 80 && g[i + 3] > 0) { if (x < c.width / 2) L++; else R++; } }
  return { L, R, w: c.width, h: c.height, cssw: c.style.width }; }"""


def make_handler(root, web="https://sp.example.invalid/view?spview=1"):
    pre = f"/v1.0/drives/{DRIVE}/root:/HANNYU_TOOL/"

    def handle(route, request):
        u = urlparse(request.url)
        RES["graph_urls"].append(request.method + " " + u.path)
        path = unquote(u.path)
        if not path.startswith(pre):
            return route.fulfill(status=403, body="outside")
        rest = path[len(pre):]
        rel, _, tail = rest.partition(":")
        p = root / rel
        if request.method == "GET" and tail == "/content":
            if not p.is_file():
                RES.setdefault("not_found", []).append(rel)
                return route.fulfill(status=404, body="{}")
            ct = "application/json" if p.suffix == ".json" else ("image/jpeg" if p.suffix.lower() in (".jpg", ".jpeg") else
                                                                   "image/svg+xml" if p.suffix.lower() == ".svg" else "application/octet-stream")   # v0.3.13: 가명 사진 (svg) 도 Graph 처럼 형식
            return route.fulfill(status=200, body=p.read_bytes(), headers={"Content-Type": ct})
        if request.method == "GET" and tail == "":                 # v0.3.3: 아이템 정보 (webUrl · 「別タブで開く」)
            if not p.exists():
                return route.fulfill(status=404, body="{}")
            return route.fulfill(status=200, body=json.dumps({"webUrl": web + "&f=" + p.name}), headers={"Content-Type": "application/json"})
        if request.method == "GET" and tail == "/children":
            if not p.is_dir():
                return route.fulfill(status=404, body="{}")
            v = [{"name": x.name, "eTag": f"e{int(x.stat().st_mtime_ns)}", **({"folder": {}} if x.is_dir() else {"file": {}})} for x in sorted(p.iterdir())]
            return route.fulfill(status=200, body=json.dumps({"value": v}), headers={"Content-Type": "application/json"})
        if request.method == "PUT" and tail == "/content":
            if not rel.startswith("_actions/"):
                return route.fulfill(status=403, body="{}")
            if p.exists() and "conflictBehavior=fail" in request.url:
                return route.fulfill(status=409, body="{}")
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(request.post_data_buffer or b"")
            return route.fulfill(status=201, body=json.dumps({"name": p.name, "size": p.stat().st_size}), headers={"Content-Type": "application/json"})
        return route.fulfill(status=400, body="{}")
    return handle


STUB = """(staff) => {
  LEENAI.auth.token = async () => 'test-token';
  Object.defineProperty(LEENAI.auth, 'status', { get: () => ({ dataverse: 'ok', graph: 'ok', graphError: '' }), configurable: true });
  Object.defineProperty(LEENAI, 'user', { get: () => ({ name: 'STAFF A', email: 'staff.a@example.invalid', staffCode: 'STAFF_A' }), configurable: true });
  LEENAI.SP.DRIVE_ID = '%s';
  LEENAI.STAFF = staff.staff.map(s => ({ name: s.name, email: s.email, staffCode: s.code }));
  LEENAI.master.get = async (n) => { if (n !== 'pol_staff') throw new Error('x'); return staff.items; };
}""" % DRIVE


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shots")
    a = ap.parse_args()
    shots = Path(a.shots) if a.shots else Path(tempfile.mkdtemp(prefix="c01_graph_shots_"))
    shots.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="c01_graph_"))
    root = tmp / "HANNYU_TOOL"
    shutil.copytree(TOOL / "fixtures", root)
    staff = json.loads((root / "_masters" / "pol_staff.json").read_text(encoding="utf-8"))
    # v0.3.2 (R7B): 가명 PDF 2개 (搬入票 · FAX) 를 사본에 넣고 queue 의 値の違い 1 · 未分類FAX 1 이 PDF 를 가리키게 · 오래된 FAX 1 (受信 10/20) 추가
    make_pdf(root / "TST2611-02" / "搬入票" / "搬入票_02_test.pdf")
    make_pdf(root / "_fax_unmatched" / "2026-11-08" / "FAX_0001_test.pdf")
    qp = root / "_data" / "queue.json"
    qj = json.loads(qp.read_text(encoding="utf-8"))
    diff_q = next(x for x in qj["items"] if x["kind"] == "値の違い" and x["files"] and x["files"][0]["path"].startswith("TST2611-02/"))
    diff_q["files"][0]["path"] = "TST2611-02/搬入票/搬入票_02_test.pdf"
    diff_q["files"][0]["page"] = 1
    fax_q = next(x for x in qj["items"] if x["kind"] == "未分類FAX")
    fax_q["files"][0]["path"] = "_fax_unmatched/2026-11-08/FAX_0001_test.pdf"
    fax_q["received_at"] = "2026-11-07T09:00:00+09:00"
    # v0.3.3 (R7C): 値の違い = 파일 2개 (2번째는 SharePoint 에 없음) · 手入力 1건 = 파일 지정 없음 (→ IV 서류)
    diff_q["files"].append({"path": "TST2611-02/搬入票/no_such_r7c.pdf", "name": "no_such_r7c.pdf", "page": 1, "bbox": None, "sha16": "0" * 16})
    man_q = next(x for x in qj["items"] if x["kind"] == "手入力")
    man_q["files"] = []
    # v0.3.18 (R7S #1 · #2): 1 개 PDF 에 여러 컨테이너 — 다른 컨테이너 (같은 IV 自動OK 줄) 의 항목 = 같은 PDF 2쪽 → 2쪽으로 열림
    jd = json.loads((root / "_data" / "jikkyou.json").read_text(encoding="utf-8"))
    r02 = next(iv for iv in jd["ivs"] if iv["iv_no"] == "TST2611-02")["rows"][0]
    pg2_q = dict(json.loads(json.dumps(diff_q)), queue_id="d2pdfpage2000001", field="n_w", container_id=r02["container_id"], ct=r02["ct"],
                 values={"搬入票": [21000], "写真": [21010]}, files=[dict(diff_q["files"][0], page=2, sha16="2" * 16)], resolved=None, superseded=[])
    qj["items"].append(pg2_q)
    old_q = json.loads(json.dumps(fax_q))
    old_q["queue_id"] = "f0ldfax000000001"
    old_q["received_at"] = "2026-10-20T09:00:00+09:00"
    qj["items"].append(old_q)
    qp.write_text(json.dumps(qj, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    port = free_port()
    srv = subprocess.Popen([sys.executable, str(TOOL / "tools" / "serve_local.py"), "--root", str(TOOL / "fixtures"), "--actions", str(tmp / "local_actions"),
                            "--port", str(port), "--today", "2026-11-08"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(50):
            try:
                socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
                break
            except OSError:
                time.sleep(0.1)
        with sync_playwright() as p:
            br = p.chromium.launch()
            page = br.new_context(viewport={"width": 1440, "height": 1000}).new_page()
            page.on("console", lambda m: RES["console_errors"].append(m.text) if m.type == "error" else None)
            page.on("pageerror", lambda e: RES["console_errors"].append(f"pageerror {e}"))
            web = "https://sp.example.invalid/view?spview=1"            # SharePoint 화면 흉내 (https 만 허용 · 가짜 응답)
            page.context.route("https://sp.example.invalid/**", lambda r: r.fulfill(status=200, body="<title>SP</title>sp", headers={"Content-Type": "text/html"}))
            page.route("https://graph.microsoft.com/**", make_handler(root, web))
            page.goto(f"http://127.0.0.1:{port}/")
            page.wait_for_selector("#ln-splash", timeout=20000)
            ok("로그인 버튼 활성 (R7A graph)", page.locator("#ln-login-btn").count() == 1 and page.locator("#ln-login-btn").is_enabled())
            ok("탭 제목 v0.3.18", page.title() == "LEENAI C-01 搬入票 v0.3.18", page.title())
            ok("config: graph 켜짐 · HANNYU_TOOL", page.evaluate("C01.SOURCE.graphEnabled === true && C01.SOURCE.spRoot === 'HANNYU_TOOL' && C01.SOURCE.mode === 'graph'"))
            page.evaluate(STUB, staff)
            page.evaluate("document.getElementById('ln-splash').style.display='none'; document.getElementById('app').style.display=''; "
                          "C01.app.start(new C01.sources.Graph())")
            page.wait_for_selector("body[data-c01-ready='1']", timeout=20000)
            n_iv = page.locator("tbody[data-iv]").count()
            ok("graph 로 実況表 (가명 IV 표시)", n_iv >= 1, n_iv)
            ok("상단 = SharePoint · HANNYU_TOOL · 担当者 = 로그인한 사람", "SharePoint · HANNYU_TOOL" in page.locator("#c01-nav").inner_text()
               and "STAFF A" in page.locator("#me-name").inner_text() and page.locator("#me-select").count() == 0, page.locator("#c01-nav").inner_text())
            ok("担当 港 = 로그인한 사람 (自分の担当)", "自分の担当" in page.locator("body").inner_text())
            # 사진 (blob)
            ph = json.loads(next((root / "_data" / "photos").glob("*.json")).read_text(encoding="utf-8"))
            rel = next(x["path"] for c in ph.get("containers", []) for x in c.get("photos", []) if x.get("path"))
            u = page.evaluate("(r) => new C01.sources.Graph().resolveUrl(r)", rel)
            ok("사진 = blob URL (Graph 에서 읽음)", u.startswith("blob:"), u)
            u2 = page.evaluate("new C01.sources.Graph().resolveUrl('NO_SUCH/x.jpg')")
            ok("없는 사진 = 빈 값 (오류 없이)", u2 == "", u2)
            page.screenshot(path=str(shots / "graph_jikkyou.png"))
            # v0.3.13 (R7L Part E · D-65): 사진 = 새 탭 (photo.html) — 새 탭은 Graph 를 부르지 않고 (토큰 없음) 원래 탭이 읽은 Blob 을 받음
            g_tab = []
            page.context.on("request", lambda r: g_tab.append(r.url) if "graph.microsoft.com" in r.url and r.frame.page != page else None)
            n_g0 = len(RES["graph_urls"])
            with page.context.expect_page(timeout=15000) as pi_ph:
                page.locator(".c01-phbtn").first.click()
            ptab = pi_ph.value
            ptab.wait_for_function("() => { const t = [...document.querySelectorAll('.c01-pv-thimg')]; return t.length > 0 && t.every(e => e.complete && e.naturalWidth > 0); }", timeout=20000)
            n_ph = ptab.locator(".c01-pv-thimg").count()
            ok("E graph: 사진 새 탭 = 원래 탭이 Graph 로 읽은 사진 (Blob) 표시 · 새 탭의 Graph 호출 0 · 로그인 0",
               n_ph >= 1 and not g_tab and ptab.locator("#ln-splash").count() == 0 and ptab.evaluate("typeof window.LEENAI") == "undefined"
               and len(RES["graph_urls"]) > n_g0, [n_ph, g_tab[:2], len(RES["graph_urls"]) - n_g0])
            ptab.screenshot(path=str(shots / "graph_photo_tab.png"))
            ptab.close()
            # _actions 쓰기 · 다시 쓰기 거부 · 읽기
            act = {"action_id": "agraphtest01", "at": "2026-11-08T10:00:00+09:00", "by": "staff.a@example.invalid", "action": "confirm_value"}
            r1 = page.evaluate("(a) => new C01.sources.Graph().writeAction(a).then(r => r.file, e => 'ERR ' + e.message)", act)
            f = root / "_actions" / "2026-11-08" / "agraphtest01.json"
            ok("_actions 쓰기 = HANNYU_TOOL/_actions/{날짜}/{id}.json", r1 == "2026-11-08/agraphtest01.json" and f.exists()
               and json.loads(f.read_text(encoding="utf-8"))["action_id"] == "agraphtest01", r1)
            r2 = page.evaluate("(a) => new C01.sources.Graph().writeAction(a).then(r => 'OK', e => 'ERR ' + e.message)", act)
            ok("같은 id 다시 쓰기 = 거부 (409 · 덮어쓰기 0)", r2.startswith("ERR") and "409" in r2, r2)
            r3 = page.evaluate("(a) => new C01.sources.Graph().writeAction(a).then(r => 'OK', e => 'ERR ' + e.message)",
                               {**act, "action_id": "../x"})
            ok("action_id 이상 = 쓰기 전 거부", r3.startswith("ERR"), r3)
            (f.parent / "agraphtest01.json.done").write_text('{"result":"applied"}', encoding="utf-8")
            la = page.evaluate("new C01.sources.Graph().listActions(['2026-11-08','2026-11-09'])")
            ok("_actions 읽기 + 처리 표시 (.done)", len(la) == 1 and la[0]["done"] is True and la[0]["action"]["action_id"] == "agraphtest01", la)
            bad = [u for u in RES["graph_urls"] if f"/v1.0/drives/{DRIVE}/root:/HANNYU_TOOL/" not in unquote(u)]
            ok("Graph 주소 = 모두 HANNYU_TOOL 아래", RES["graph_urls"] and not bad, bad[:3])
            puts = [u for u in RES["graph_urls"] if u.startswith("PUT")]
            ok("쓰기 (PUT) = _actions 만", puts and all("/_actions/" in unquote(u) for u in puts), puts)
            nf = [x for x in RES.get("not_found", []) if x != "NO_SUCH/x.jpg"]
            ok("없는 파일 요청 = 선택 파일만 (compass_now · remind)", all(x.startswith(("_data/compass_now/", "_data/remind.json")) for x in nf), nf[:5])
            # ── v0.3.2 (R7B) PDF 표시 ──
            page.click("#tab-input")
            page.wait_for_timeout(300)
            page.click(f'[data-q="{diff_q["queue_id"]}"]')
            page.wait_for_selector(".c01-orig [data-pdf][data-drawn='1:0']", timeout=30000)
            ink = page.evaluate(INK, ".c01-orig [data-pdf] canvas")
            ok("PDF 搬入票 = canvas 에 그림 (빈 화면 아님 · 1쪽 = 왼쪽)", ink and ink["L"] > 50 and ink["R"] < ink["L"] / 10, ink)
            ok("PDF 쪽 표시 p.1 / 2 · iframe 없음", page.locator("#pdf-pg").inner_text() == "p.1 / 2" and page.locator(".c01-orig iframe").count() == 0, page.locator("#pdf-pg").inner_text())
            ok("別タブで開く (보조) 있음", page.locator("#pdf-open").count() == 1)
            page.click("#pdf-next")
            page.wait_for_selector(".c01-orig [data-pdf][data-drawn='2:0']", timeout=15000)
            ink2 = page.evaluate(INK, ".c01-orig [data-pdf] canvas")
            ok("페이지 넘김 → 2쪽 (오른쪽) · p.2 / 2", ink2["R"] > 50 and ink2["L"] < ink2["R"] / 10 and page.locator("#pdf-pg").inner_text() == "p.2 / 2", ink2)
            page.click("#pdf-prev")
            page.wait_for_selector(".c01-orig [data-pdf][data-drawn='1:0']", timeout=15000)
            ok("앞 페이지 → 1쪽", page.locator("#pdf-pg").inner_text() == "p.1 / 2")
            page.click("#rot")
            page.wait_for_selector(".c01-orig [data-pdf][data-drawn='1:90']", timeout=15000)
            ink3 = page.evaluate(INK, ".c01-orig [data-pdf] canvas")
            ok("회전 90° → 가로로 긴 canvas", ink3["w"] > ink3["h"], ink3)
            for _ in range(3):
                page.click("#rot")
                page.wait_for_timeout(150)
            page.wait_for_selector(".c01-orig [data-pdf][data-drawn='1:0']", timeout=15000)
            page.click("#z-in")
            page.wait_for_selector(".c01-orig [data-pdf][data-drawn='1:0']", timeout=15000)
            ok("확대 120% → canvas 768px", page.evaluate("document.querySelector('.c01-orig [data-pdf] canvas').style.width") == "768px")
            page.screenshot(path=str(shots / "graph_pdf.png"))
            # v0.3.18 (R7S #1 · #2): 같은 PDF 의 다른 컨테이너 항목 (page 2) = 2쪽으로 열림 (전에는 파일별 기억 → 앞에서 본 1쪽) · 다른 쪽도 넘김
            page.click("#z-out")
            page.click(f'[data-q="{pg2_q["queue_id"]}"]')
            page.wait_for_selector(".c01-orig [data-pdf][data-drawn='2:0']", timeout=15000)
            ink5 = page.evaluate(INK, ".c01-orig [data-pdf] canvas")
            ok("v0.3.18 #2 여러 컨테이너 PDF = 항목의 쪽 (files[].page 2) 으로 열림 · p.2 / 2 (앞에서 같은 PDF 1쪽을 봤어도)",
               page.locator("#pdf-pg").inner_text() == "p.2 / 2" and ink5["R"] > 50 and ink5["L"] < ink5["R"] / 10, [page.locator("#pdf-pg").inner_text(), ink5])
            page.click("#pdf-prev")
            page.wait_for_selector(".c01-orig [data-pdf][data-drawn='1:0']", timeout=15000)
            ok("v0.3.18 #2 다른 쪽도 넘김 (‹ → p.1 / 2)", page.locator("#pdf-pg").inner_text() == "p.1 / 2")
            page.click(f'[data-q="{diff_q["queue_id"]}"]')
            page.wait_for_selector(".c01-orig [data-pdf][data-drawn='1:0']", timeout=15000)
            page.click(f'[data-q="{pg2_q["queue_id"]}"]')
            page.wait_for_selector(".c01-orig [data-pdf][data-drawn]", timeout=15000)
            page.wait_for_timeout(300)
            ok("v0.3.18 #2 쪽 기억 = 항목마다 (다시 열면 그 항목에서 본 쪽 p.1)", page.locator("#pdf-pg").inner_text() == "p.1 / 2", page.locator("#pdf-pg").inner_text())
            page.click(f'[data-q="{diff_q["queue_id"]}"]')
            page.wait_for_selector(".c01-orig [data-pdf][data-drawn='1:0']", timeout=15000)
            # ── v0.3.3 (R7C) 파일 열기 ──
            with page.context.expect_page(timeout=15000) as pinfo:
                page.click("#pdf-open")
            tab = pinfo.value
            tab.wait_for_url("**spview=1**", timeout=15000)
            ok("別タブで開く = SharePoint 화면 (webUrl + web=1) 새 탭 (팝업 막힘 없음)", "spview=1" in tab.url and "f=" in tab.url and tab.url.endswith("web=1"), tab.url)
            tab.close()
            ok("파일 2개 = 칩 2개", page.locator(".c01-qfiles [data-qf]").count() == 2)
            page.click('.c01-qfiles [data-qf="1"]')
            page.wait_for_selector(".c01-orig [data-missing='1']", timeout=15000)
            t_miss = page.locator(".c01-orig").inner_text()
            ok("없는 파일 = 「SharePoint にまだありません」 (흰 화면 · 빈 iframe 아님)", "SharePoint にまだありません" in t_miss and page.locator(".c01-orig iframe").count() == 0, t_miss[:120])
            with page.context.expect_page(timeout=15000) as pinfo2:
                page.click("#pdf-open")
            tab2 = pinfo2.value
            page.wait_for_timeout(1500)
            ok("없는 파일 「別タブで開く」 = 탭 닫힘 + 이유", tab2.is_closed(), tab2.url if not tab2.is_closed() else "")
            page.click('.c01-qfiles [data-qf="0"]')
            page.wait_for_selector(".c01-orig [data-pdf][data-drawn]", timeout=15000)
            page.click("#tab-main")
            page.wait_for_timeout(300)
            page.click('[data-port="all"]')                          # 担当港 필터 해제 (手入力 가명 IV = 다른 港)
            page.click("#tab-input")
            page.wait_for_timeout(300)
            page.click(f'[data-q="{man_q["queue_id"]}"]')
            page.wait_for_timeout(800)
            t_man = page.locator(".c01-orig").inner_text()
            # v0.3.15 (R7N G-2-0): IV 서류 전체 표시 없앰 → 같은 컨테이너의 다른 항목 (手入力 CT) 의 서류 1개만 · 칩 없음
            ok("v0.3.15 手入力 (파일 지정 없음) = 같은 컨테이너 항목의 서류만 (IV 서류 전체 표시 없음 · 칩 0)", "IV の書類を表示" not in t_man and "搬入票_04" in t_man
               and page.locator(".c01-qfiles [data-qf]").count() == 0 and page.locator(".c01-orig img.c01-docimg[src^='blob:']").count() == 1, t_man[:120])
            ok("手入力 「原本ファイルがありません」 없음", "原本ファイルがありません" not in t_man)
            page.screenshot(path=str(shots / "graph_r7c_ivdocs.png"))
            # 未分類 FAX: 새 것만 기본 목록 · 오래된 것은 숨김 + 「古い未分類 FAX も表示」
            lab = page.locator("#fax-old-lab").inner_text() if page.locator("#fax-old-lab").count() else ""
            ok("오래된 未分類 FAX = 기본 목록에서 숨김 (1건)", page.locator('[data-q="f0ldfax000000001"]').count() == 0 and "1件" in lab, lab)
            page.check("#fax-old")
            page.wait_for_timeout(200)
            ok("「古い未分類 FAX も表示」 → 보임 (지우지 않음)", page.locator('[data-q="f0ldfax000000001"]').count() == 1)
            page.click(f'[data-q="{fax_q["queue_id"]}"]')
            page.wait_for_selector(".c01-orig [data-pdf][data-drawn]", timeout=30000)
            ink4 = page.evaluate(INK, ".c01-orig [data-pdf] canvas")
            # v0.3.15 (R7N G-3): 가명 FAX = files[].rotation 180 → 처음부터 180° 돌려 그림 (가명 PDF 의 글자는 왼쪽 → 돌리면 오른쪽)
            br4 = page.get_attribute(".c01-orig [data-pdf]", "data-base-rot")
            ok("未分類 FAX PDF = canvas 에 그림 · 受信 날짜 표시 · v0.3.15 엔진 rotation 180 = 처음부터 돌려 그림 (글자 오른쪽 · 「向き補正 180°」)",
               ink4 and ink4["R"] > 50 and ink4["L"] == 0 and br4 == "180" and "向き補正 180°" in page.locator(".c01-orig-h").inner_text()
               and "受信 11/07" in page.locator(".c01-form-h").inner_text(), [ink4, br4])
            page.screenshot(path=str(shots / "graph_fax.png"))
            # pdf.js 를 못 읽으면 iframe 로 물러남 (새 창 · cdnjs 막음)
            p2 = page.context.new_page()
            p2.route("https://graph.microsoft.com/**", make_handler(root))
            p2.route("https://cdnjs.cloudflare.com/**", lambda r: r.abort())
            p2.goto(f"http://127.0.0.1:{port}/")
            p2.wait_for_selector("#ln-splash", timeout=20000)
            p2.evaluate(STUB, staff)
            p2.evaluate("document.getElementById('ln-splash').style.display='none'; document.getElementById('app').style.display=''; C01.app.start(new C01.sources.Graph())")
            p2.wait_for_selector("body[data-c01-ready='1']", timeout=20000)
            p2.click("#tab-input")
            p2.wait_for_timeout(200)
            p2.click(f'[data-q="{diff_q["queue_id"]}"]')
            p2.wait_for_selector(".c01-orig [data-pdf][data-fallback] iframe", timeout=15000)
            ok("pdf.js 없음 → iframe (blob) 로 물러남", (p2.locator(".c01-orig iframe").get_attribute("src") or "").startswith("blob:"))
            p2.close()
            # v0.3.16 (R7O Part D): 担当者 = 職員マスター (staff) 이름 · pol_staff 열 = staff (担当) · assist (補助) · 마스터에 없으면 「職員マスター未登録」
            for case, (um, uc, want, ports_ok) in {"master": ("staff.b@example.invalid", "", "職員B", True),
                                                   "code": ("other@example.invalid", "STAFF_B", "職員B", True),
                                                   "none": ("nobody@example.invalid", "", "職員マスター未登録", False)}.items():
                p3 = page.context.new_page()
                p3.route("https://graph.microsoft.com/**", make_handler(root))
                p3.goto(f"http://127.0.0.1:{port}/")
                p3.wait_for_selector("#ln-splash", timeout=20000)
                p3.evaluate(STUB, staff)
                p3.evaluate("""([um, uc]) => {
                  Object.defineProperty(LEENAI, 'user', { get: () => ({ name: 'MS DISPLAY NAME', email: um, staffCode: uc }), configurable: true });
                  LEENAI.STAFF = [{ name: 'COMMON LIST NAME', email: 'staff.b@example.invalid', staffCode: 'STAFF_B' }];
                  LEENAI.master.get = async (n) => {
                    if (n === 'pol_staff') return [{ pol: 'TOKYO', staff: 'STAFF_A', assist: 'STAFF_B' }, { pol: 'YOKOHAMA', staff: 'STAFF_B', assist: '' }];
                    if (n === 'staff') return [{ code: 'STAFF_A', name_ja: '職員A', name_en: 'STAFF A', email: 'staff.a@example.invalid', active: true },
                                               { code: 'STAFF_B', name_ja: '職員B', name_en: 'STAFF B', email: 'Staff.B@example.invalid', active: true }];
                    throw new Error('x');
                  };
                }""", [um, uc])
                p3.evaluate("document.getElementById('ln-splash').style.display='none'; document.getElementById('app').style.display=''; C01.app.start(new C01.sources.Graph())")
                p3.wait_for_selector("body[data-c01-ready='1']", timeout=20000)
                me = p3.locator("#me-name").inner_text()
                body = p3.locator("body").inner_text()
                cond = want in me and "MS DISPLAY NAME" not in me and "COMMON LIST NAME" not in me
                if ports_ok:
                    cond = cond and "自分の担当（TOKYO · YOKOHAMA）" in body
                else:
                    cond = cond and "c01-warn" in (p3.locator("#me-name").get_attribute("class") or "")
                ok(f"v0.3.16 担当者 = 職員マスター ({case}) · pol_staff staff/assist", cond, [me, body[:200]])
                p3.close()
            # v0.3.18 (R7S #16): pol_staff 担当・補助 칸 = 직원 코드 · 메일 (대문자 · 공백) · 이름 (전각 · 공백) · 여러 값 (; , 、 / 줄바꿈 공백) 모두 맞음 ·
            #                   맞는 것 없음 = 「なし」 + 「担当港マスターに該当なし」 · 마스터를 못 읽음 = 「担当港マスターを読めません」 (全港 표시)
            staff_rows = [{"code": "STAFF_A", "name_ja": "職員A", "name_en": "STAFF A", "email": "staff.a@example.invalid", "active": True},
                          {"code": "STAFF_B", "name_ja": "職員 ビー", "name_en": "STAFF B", "email": "Staff.B@example.invalid", "active": True},
                          {"code": "STAFF_C", "name_ja": "職員C", "name_en": "STAFF C", "email": "staff.c@example.invalid", "active": True}]
            cases16 = {
                "code": ([{"pol": "TOKYO", "staff": "STAFF_B", "assist": ""}, {"pol": "YOKOHAMA", "staff": "STAFF_A", "assist": "STAFF_C"}], "（TOKYO）", ""),
                "email": ([{"pol": "TOKYO", "staff": "STAFF_A", "assist": "  STAFF.B@EXAMPLE.INVALID "}, {"pol": "YOKOHAMA", "staff": "STAFF_A", "assist": ""}], "（TOKYO）", ""),
                "name": ([{"pol": "TOKYO", "staff": "STAFF_A", "assist": ""}, {"pol": "YOKOHAMA", "staff": "職員\u3000ビー", "assist": ""}], "（YOKOHAMA）", ""),
                "name_nospace": ([{"pol": "KOBE", "staff": "職員ビー", "assist": ""}], "（KOBE）", ""),
                "multi": ([{"pol": "TOKYO", "staff": "STAFF_A; STAFF_B", "assist": ""}, {"pol": "YOKOHAMA", "staff": "STAFF_C、職員 ビー", "assist": ""},
                           {"pol": "KOBE", "staff": "STAFF_A / STAFF_C", "assist": "STAFF_C\nSTAFF_B"}, {"pol": "HAKATA", "staff": "STAFF_A STAFF_B", "assist": ""},
                           {"pol": "*", "staff": "", "assist": ["STAFF_C", "staff.b@example.invalid"]}], "（TOKYO · YOKOHAMA · KOBE · HAKATA · *）", ""),
                "nohit": ([{"pol": "TOKYO", "staff": "STAFF_A", "assist": "STAFF_C"}, {"pol": "YOKOHAMA", "staff": "STAFF_BB", "assist": "staff.bb@example.invalid"}],
                          "（なし）", "担当港マスターに該当なし"),
                "unreadable": (None, "（なし）", "担当港マスターを読めません"),
            }
            for case, (pol_rows, want_lab, want_why) in cases16.items():
                p4 = page.context.new_page()
                p4.route("https://graph.microsoft.com/**", make_handler(root))
                p4.goto(f"http://127.0.0.1:{port}/")
                p4.wait_for_selector("#ln-splash", timeout=20000)
                p4.evaluate(STUB, staff)
                p4.evaluate("""([pol, rows]) => {
                  Object.defineProperty(LEENAI, 'user', { get: () => ({ name: 'MS DISPLAY NAME', email: 'staff.b@example.invalid', staffCode: '' }), configurable: true });
                  LEENAI.master.get = async (n) => {
                    if (n === 'pol_staff') { if (!pol) throw new Error('403'); return pol; }
                    if (n === 'staff') return rows;
                    throw new Error('x');
                  };
                }""", [pol_rows, staff_rows])
                p4.evaluate("localStorage.removeItem('c01_ports'); document.getElementById('ln-splash').style.display='none'; document.getElementById('app').style.display=''; "
                            "C01.app.start(new C01.sources.Graph())")
                p4.wait_for_selector("body[data-c01-ready='1']", timeout=20000)
                lab = p4.locator("[data-port='mine']").inner_text()
                why = p4.locator("#mp-why").inner_text() if p4.locator("#mp-why").count() else ""
                n_iv4 = p4.locator("tbody[data-iv]").count()
                cond = lab.startswith("自分の担当" + want_lab) and (why.startswith(want_why) if want_why else why == "") and "職員 ビー" in p4.locator("#me-name").inner_text()
                if case == "unreadable":
                    cond = cond and n_iv4 == 5                       # 못 읽음 = 지금까지처럼 全港
                if case == "nohit":
                    cond = cond and n_iv4 == 0
                ok(f"v0.3.18 #16 自分の担当 ({case}) = {want_lab} {want_why}".strip(), cond, [lab, why, n_iv4])
                p4.close()
            errs = [e for e in RES["console_errors"] if not ("Failed to load resource" in e and ("404" in e or "409" in e or "ERR_FAILED" in e))]
            ok("콘솔 오류 0 (예상한 404 · 409 제외)", not errs, errs[:5])
            br.close()
    finally:
        srv.terminate()
        shutil.rmtree(tmp, ignore_errors=True)
    n_ng = sum(1 for c in RES["checks"] if not c["ok"])
    (shots / "graph_result.json").write_text(json.dumps(RES, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"== {len(RES['checks']) - n_ng}/{len(RES['checks'])} OK")
    return 1 if n_ng else 0


if __name__ == "__main__":
    sys.exit(main())
