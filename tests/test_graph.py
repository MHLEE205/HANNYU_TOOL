# ✦ Powered by LEENAI Automation System — C-01 搬入票 TOOL graph 모드 시험 (R7A · Playwright · 가명 fixtures · 가짜 Graph — 실제 SharePoint 호출 0)
"""TOOL 을 127.0.0.1 로 열고, LEENAI_COMMON 로그인 결과 (토큰 · 사용자 · 마스터) 는 가짜로 바꾸고,
https://graph.microsoft.com/ 요청은 page.route 로 가로채 가명 fixtures 폴더 (임시 사본 = HANNYU_TOOL 흉내) 에서 돌려준다.
확인: 로그인 버튼 활성 · graph 로 実況表 · 사진 blob 표시 · 로그인한 사람 = 担当者 · _actions 쓰기 = HANNYU_TOOL/_actions/{날짜}/ 만 ·
      같은 id 다시 쓰기 거부 (409) · 처리 표시 (.done) 읽기 · Graph 주소는 모두 drives/{드라이브}/root:/HANNYU_TOOL/ 아래 · 콘솔 오류 0.
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


def make_handler(root):
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
            ct = "application/json" if p.suffix == ".json" else ("image/jpeg" if p.suffix.lower() in (".jpg", ".jpeg") else "application/octet-stream")
            return route.fulfill(status=200, body=p.read_bytes(), headers={"Content-Type": ct})
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
            page.route("https://graph.microsoft.com/**", make_handler(root))
            page.goto(f"http://127.0.0.1:{port}/")
            page.wait_for_selector("#ln-splash", timeout=20000)
            ok("로그인 버튼 활성 (R7A graph)", page.locator("#ln-login-btn").count() == 1 and page.locator("#ln-login-btn").is_enabled())
            ok("탭 제목 v0.3.1", page.title() == "LEENAI C-01 搬入票 v0.3.1", page.title())
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
            errs = [e for e in RES["console_errors"] if not ("Failed to load resource" in e and ("404" in e or "409" in e))]
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
