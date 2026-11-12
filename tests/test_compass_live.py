# ✦ Powered by LEENAI Automation System — C-01 搬入票 TOOL v0.3.19 Compass入力 実際の入力 시험 (R7T 결정 #190 · 가짜 Dataverse · 가짜 Graph — 실제 호출 0)
"""graph 모드로 열고 COMPASS (Dataverse) 요청은 page.route 로 가짜 서버가 받는다 (가명 fixtures compass_now 칸).
확인: 「試験運用中」 · 행 체크 (경고 행 = 체크 없음) · 보낸 요청 = GET · PATCH 만 (POST · DELETE 0) · PATCH 마다 If-Match ·
      다른 사람이 먼저 바꾼 행 (etag 바뀜) = 그 행만 「他の人が先に変更」 · 다른 행 계속 · 다시 읽어 확인 ·
      _actions 에 compass_done (전 값 · 후 값 · 누가 · 언제 · 실패 행) · 実況表 「✓ 入力済」 ·
      「元に戻す」 = 마지막 입력을 전 값으로 (지금 값 = 넣은 값인 항목만) · 기록 undo_of · 実況表 다시 「Compass入力」 · 콘솔 오류 0.
사용: python tests/test_compass_live.py"""
import json
import re
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
import test_graph as G  # noqa: E402  (가짜 Graph · 로그인 흉내 · ok() 그대로)

TOOL = G.TOOL
DV = "https://orgde512c6f.crm7.dynamics.com"
REQ = []


def dv_handler(cells, state):
    pre = "/api/data/v9.2/crcf9_container_informations"

    def handle(route, request):
        u = urlparse(request.url)
        path = unquote(u.path)
        REQ.append((request.method, path, dict(request.headers), request.post_data or "", unquote(u.query)))
        if not path.startswith(pre):
            return route.fulfill(status=403, body="{}")
        m = re.match(re.escape(pre) + r"\(([^)]+)\)$", path)
        hj = {"Content-Type": "application/json"}
        if request.method == "GET" and path == pre:
            q = unquote(u.query)
            if "_crcf9_booking_id_value eq " not in q:
                return route.fulfill(status=400, body="{}")
            return route.fulfill(status=200, body=json.dumps({"value": list(cells.values())}), headers=hj)
        if request.method == "GET" and m:
            c = cells.get(m.group(1))
            return route.fulfill(status=200, body=json.dumps(c), headers=hj) if c else route.fulfill(status=404, body="{}")
        if request.method == "PATCH" and m:
            c = cells.get(m.group(1))
            if not c:
                return route.fulfill(status=404, body="{}")
            im = request.headers.get("if-match")
            if not im or im != c["@odata.etag"]:
                return route.fulfill(status=412, body="{}")
            body = json.loads(request.post_data or "{}")
            c.update(body)
            state["n"] += 1
            c["@odata.etag"] = 'W/"%d"' % (2000 + state["n"])
            return route.fulfill(status=204, body="")
        return route.fulfill(status=405, body="{}")
    return handle


def main():
    ok = G.ok
    tmp = Path(tempfile.mkdtemp(prefix="c01_cl_"))
    root = tmp / "HANNYU_TOOL"
    shutil.copytree(TOOL / "fixtures", root)
    staff = json.loads((root / "_masters" / "pol_staff.json").read_text(encoding="utf-8"))
    snap = json.loads((root / "_data" / "compass_now" / "TST2611-01.json").read_text(encoding="utf-8"))
    cells = {k: {kk: vv for kk, vv in v.items() if not kk.startswith("_")} for k, v in snap["cells"].items()}
    orig = json.loads(json.dumps(cells))
    state = {"n": 0}
    port = G.free_port()
    srv = subprocess.Popen([sys.executable, str(TOOL / "tools" / "serve_local.py"), "--root", str(TOOL / "fixtures"), "--actions", str(tmp / "la"),
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
            page.on("console", lambda m: G.RES["console_errors"].append(m.text) if m.type == "error" else None)
            page.on("pageerror", lambda e: G.RES["console_errors"].append(f"pageerror {e}"))
            page.on("dialog", lambda d: d.accept())
            page.route("https://graph.microsoft.com/**", G.make_handler(root))
            page.route(DV + "/**", dv_handler(cells, state))
            page.goto(f"http://127.0.0.1:{port}/")
            page.wait_for_selector("#ln-splash", timeout=20000)
            ok("v0.3.19 config: Compass入力 = 실제 입력 (SEND.compass · dvUrl · 試験運用中) · v0.3.22 催促 = 試験送信만 (remindTest)",
               page.evaluate("C01.SEND.compass === true && C01.COMPASS.dvUrl === '%s' && C01.COMPASS.trial === true && C01.SEND.remind === true && C01.SEND.remindTest === true" % DV))   # v0.3.22 (R7V B): 催促 = 試験送信만
            page.evaluate(G.STUB, staff)
            page.evaluate("document.getElementById('ln-splash').style.display='none'; document.getElementById('app').style.display=''; "
                          "C01.app.start(new C01.sources.Graph())")
            page.wait_for_selector("body[data-c01-ready='1']", timeout=20000)
            page.locator('[data-compass="TST2611-01"]').first.click()
            page.wait_for_selector("#compass-table", timeout=15000)
            ok("Compass入力 창 「試験運用中」 · 로그인한 사람 이름", page.locator("[data-trial]").inner_text() == "試験運用中"
               and "STAFF A" in page.locator(".c01-mf").inner_text(), page.locator(".c01-mf").inner_text()[:120])
            boxes = page.locator("[data-cpick]")
            n_box, n_chk = boxes.count(), page.locator("[data-cpick]:checked").count()
            warned = page.evaluate("Array.from(document.querySelectorAll('[data-cpick]')).filter(b => b.closest('tr').querySelector('[data-warn]')).map(b => b.checked)")
            n_patch = page.evaluate("JSON.parse(document.getElementById('compass-patch').textContent).length")
            ok("행 체크: PATCH 대상 행마다 체크 칸 · 경고 행 (CT_DUP) = 체크 없음 · 나머지 체크", n_box == n_patch and n_box >= 3 and warned == [False] and n_chk == n_box - 1,
               (n_box, n_patch, n_chk, warned))
            ok("보내기 버튼 = 체크 수 · 활성", page.locator("#compass-n").inner_text() == str(n_chk) and page.locator("#compass-send").is_enabled())
            ok("창 열 때 = GET 1번 (그 부킹 칸 전부 · $filter) · 쓰기 0", [r[0] for r in REQ] == ["GET"] and "_crcf9_booking_id_value eq " + snap["booking_guid"] in REQ[0][4], [(r[0], r[4][-60:]) for r in REQ])
            # 다른 사람이 먼저 바꿈 = 체크된 행 1개 etag 바뀜 (서버 쪽)
            chk_ids = page.evaluate("Array.from(document.querySelectorAll('[data-cpick]:checked')).map(b => b.getAttribute('data-cpick'))")
            conflict = chk_ids[1]
            cells[conflict]["@odata.etag"] = 'W/"9999"'
            cells[conflict]["crcf9_seal_no"] = "OTHERSEAL1"
            n0 = len(REQ)
            page.locator("#compass-send").click()
            page.wait_for_function("(n) => document.querySelectorAll('.c01-cres.ok').length + document.querySelectorAll('.c01-cres.ng').length >= n", arg=n_chk, timeout=20000)
            page.wait_for_timeout(500)
            res = page.evaluate("Array.from(document.querySelectorAll('.c01-cres')).filter(e => e.textContent).map(e => [e.getAttribute('data-cres'), e.className.split(' ').pop(), e.textContent])")
            okids = [r[0] for r in res if r[1] == "ok"]
            ngs = [r for r in res if r[1] == "ng"]
            ok("결과: 나머지 행 入力済 · 먼저 바뀐 1행만 「他の人が先に変更」 (다른 행 계속)", len(okids) == n_chk - 1 and len(ngs) == 1 and ngs[0][0] == conflict and "他の人が先に変更" in ngs[0][2], res)
            sent = REQ[n0:]
            ok("보낸 요청 = GET · PATCH 만 (POST · DELETE · PUT 0) · PATCH = 성공 행 수 (먼저 바뀐 행은 PATCH 안 함)",
               {r[0] for r in sent} <= {"GET", "PATCH"} and sum(1 for r in sent if r[0] == "PATCH") == len(okids) and not any(r[0] == "PATCH" and conflict in r[1] for r in sent),
               [(r[0], r[1][-30:]) for r in sent])
            ok("PATCH 마다 If-Match (etag) · 토큰 = 로그인한 사람 (Authorization)", all(r[2].get("if-match") and r[2].get("authorization") == "Bearer test-token" for r in sent if r[0] == "PATCH"))
            ok("PATCH 뒤 다시 GET (확인)", all(any(r2[0] == "GET" and cid in r2[1] for r2 in sent[i + 1:]) for i, r in enumerate(sent) if r[0] == "PATCH" for cid in [r[1].split("(")[1].rstrip(")")]))
            ok("서버 값 = 넣은 값 (성공 행) · 먼저 바뀐 행 그대로", all(cells[c]["crcf9_n_w"] is not None for c in okids) and cells[conflict]["crcf9_seal_no"] == "OTHERSEAL1"
               and cells[conflict]["crcf9_n_w"] is None)
            allowed = {"crcf9_container_no", "crcf9_seal_no", "crcf9_n_w", "crcf9_g_w", "crcf9_t_w", "crcf9_quantity", "crcf9_type"}
            ok("PATCH 본문 = 입력 7칸 안 (작업일 · 다른 칸 0)", all(set(json.loads(r[3])) <= allowed for r in sent if r[0] == "PATCH"),
               [sorted(json.loads(r[3])) for r in sent if r[0] == "PATCH"])
            acts = sorted((root / "_actions").rglob("*.json"))
            a = json.loads(acts[-1].read_text(encoding="utf-8")) if acts else {}
            v = a.get("value") or {}
            ok("_actions compass_done 기록: 누가 · 언제 · 성공 행 (전 값 · 후 값) · 실패 1행 · 試験運用",
               a.get("action") == "compass_done" and a.get("iv") == "TST2611-01" and a.get("by") == "staff.a@example.invalid" and a.get("at")
               and len(v.get("cells") or []) == len(okids) and all(set(c) >= {"ct_id", "fields", "before", "after"} for c in v["cells"])
               and [f["ct_id"] for f in v.get("failed") or []] == [conflict] and v.get("trial") is True, {k: a.get(k) for k in ("action", "iv", "by")})
            ok("_actions 쓰기 = HANNYU_TOOL/_actions/{날짜}/ 만", all(x.relative_to(root).parts[0] == "_actions" and len(x.relative_to(root).parts) == 3 for x in acts), [str(x.relative_to(root)) for x in acts])
            page.locator("[data-close]").first.click()
            page.wait_for_timeout(300)
            hdr = page.locator('tbody[data-iv="TST2611-01"]').first.inner_text()
            ok("実況表 「✓ 入力済」 (자기 화면 바로)", "入力済" in hdr, hdr[:200])
            # ── 元に戻す ──
            ok("「✓ 入力済」 = 누르면 Compass入力 창 (기록 · 元に戻す)", page.locator('tbody[data-iv="TST2611-01"] .c01-done[data-compass]').count() == 1)
            page.locator('tbody[data-iv="TST2611-01"] .c01-done[data-compass]').first.click()
            page.wait_for_selector("#compass-table", timeout=15000)
            ok("기록 표시 (입력 n행 · 실패 1행) · 「元に戻す」 버튼", page.locator("#compass-undo").count() == 1 and f"入力 {len(okids)}行 · 失敗 1行" in page.locator("#compass-hist").inner_text(),
               page.locator("#compass-hist").inner_text() if page.locator("#compass-hist").count() else None)
            n1 = len(REQ)
            page.locator("#compass-undo").click()
            page.wait_for_function("() => !document.getElementById('compass-table')", timeout=20000)
            sent2 = REQ[n1:]
            ok("元に戻す: PATCH = 넣은 행만 · If-Match · GET/PATCH 만", sum(1 for r in sent2 if r[0] == "PATCH") == len(okids) and {r[0] for r in sent2} <= {"GET", "PATCH"}
               and all(r[2].get("if-match") for r in sent2 if r[0] == "PATCH"), [(r[0], r[1][-24:]) for r in sent2])
            ok("元に戻す: 서버 값 = 처음 값 (넣은 행) · 먼저 바뀐 행 그대로", all(all(cells[c].get(k) == orig[c].get(k) for k in orig[c] if k != "@odata.etag") for c in okids)
               and cells[conflict]["crcf9_seal_no"] == "OTHERSEAL1")
            acts = sorted((root / "_actions").rglob("*.json"), key=lambda x: x.stat().st_mtime)
            u = json.loads(acts[-1].read_text(encoding="utf-8"))
            ok("元に戻す 기록 = compass_done (undo_of = 앞 입력 · 같은 행 수)", u.get("action") == "compass_done" and (u.get("value") or {}).get("undo_of") == a.get("action_id")
               and len(u["value"].get("cells") or []) == len(okids))
            sys.path.insert(0, r"C:/LEENAI_C01_V2/engine")
            from engine.output import schema_check  # noqa: E402
            sch = schema_check.load("action")
            errs_s = {x.get("action_id"): schema_check.errors(x, sch) for x in (a, u)}
            ok("compass_done 기록 2개 = 엔진 action.schema.json (오류 0)", all(not e for e in errs_s.values()), errs_s)
            hdr2 = page.locator('tbody[data-iv="TST2611-01"]').first.inner_text()
            ok("実況表 = 다시 「Compass入力」 (入力済 아님)", "入力済" not in hdr2 and "Compass入力" in hdr2, hdr2[:200])
            errs = [e for e in G.RES["console_errors"] if not ("Failed to load resource" in e and ("404" in e or "409" in e or "ERR_FAILED" in e))]
            ok("콘솔 오류 0 (가짜 서버 404 빼고)", not errs, errs[:3])
            br.close()
    finally:
        srv.terminate()
    bad = [c for c in G.RES["checks"] if not c["ok"]]
    print(f"{len(G.RES['checks']) - len(bad)}/{len(G.RES['checks'])} OK")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
