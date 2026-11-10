# ✦ Powered by LEENAI Automation System — C-01 搬入票 TOOL v0.1 画面試験 (Playwright · 가명 fixtures)
"""fixtures 를 임시 폴더로 복사 → serve_local.py (127.0.0.1) → Chromium 으로 열어 확인.
확인: 実況表 열 15 · 줄 색 4종 · 담당 港 거르기 · メール未着 줄 · 사진 보기 넘기기 · 確認・入力 4종 처리 · _actions JSON = 엔진 스키마 ·
      30초 겹쳐 보기 (다른 창) · 先勝ち · 체크디짓 거부 · Compass入力/催促 비활성 · 4테마 스크린샷 · 콘솔 오류 0 · 네트워크 = LEENAI_COMMON·로컬만.
사용: python tests/test_ui.py [--shots 폴더] [--engine C:\\LEENAI_C01_V2\\engine_r5] [--no-wait30]"""
import argparse
import json
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

TOOL = Path(__file__).resolve().parent.parent
ALLOWED = ("http://127.0.0.1", "https://mhlee205.github.io/LEENAI_COMMON/")
RES = {"checks": [], "console_errors": [], "external_requests": []}


def ok(name, cond, detail=""):
    RES["checks"].append({"name": name, "ok": bool(cond), "detail": str(detail)[:300]})
    print(("OK  " if cond else "NG  ") + name + (f" — {detail}" if detail and not cond else ""), flush=True)


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def actions(root):
    out = []
    for p in sorted((root / "_actions").rglob("*.json")):
        if "_rejected" in p.parts:
            continue
        out.append(json.loads(p.read_text(encoding="utf-8")))
    return out


def watch(page, tag):
    page.on("console", lambda m: RES["console_errors"].append(f"{tag}: {m.text}") if m.type == "error" else None)
    page.on("pageerror", lambda e: RES["console_errors"].append(f"{tag}: pageerror {e}"))
    page.on("request", lambda r: RES["external_requests"].append(r.url) if not r.url.startswith(ALLOWED) and not r.url.startswith("data:")
            and not r.url.startswith("blob:") else None)


HUMAN_SEAL = None


def open_local(page, url, staff=None):
    page.goto(url)
    page.wait_for_selector("#c01-open-server", timeout=20000)
    page.click("#c01-open-server")
    page.wait_for_selector("body[data-c01-ready='1']", timeout=20000)
    if staff:
        page.select_option("#me-select", staff)
        page.wait_for_timeout(200)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shots", default=str(TOOL / "tests" / "_shots"))
    ap.add_argument("--engine", default=r"C:\LEENAI_C01_V2\engine_r68")
    ap.add_argument("--no-wait30", action="store_true")
    a = ap.parse_args()
    if not (TOOL / "fixtures" / "_data" / "jikkyou.json").is_file():
        sys.exit("fixtures/_data 없음 — 먼저 python tools/make_test_data.py (레포에 넣지 않는 가명 시험 데이터)")
    shots = Path(a.shots)
    shots.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="c01tool_"))
    root = tmp / "data"
    shutil.copytree(TOOL / "fixtures", root)
    # v0.2.2 (#109 ①): 사본 _data 에 「다시 판정 값이 사람 값과 다름」 정보를 넣음 (엔진 data_json 의 info 형식 그대로)
    global HUMAN_SEAL
    jp = root / "_data" / "jikkyou.json"
    jj = json.loads(jp.read_text(encoding="utf-8"))
    for iv in jj["ivs"]:
        for r in iv["rows"]:
            if r["ct"] == "TSTU0010218":
                HUMAN_SEAL = r["human"]["seal"]["value"]
                r["seal"] = HUMAN_SEAL
                r["info"] = ["human_vs_engine_diff(seal)"]
    jp.write_text(json.dumps(jj, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    port = free_port()
    srv = subprocess.Popen([sys.executable, str(TOOL / "tools" / "serve_local.py"), "--root", str(root), "--port", str(port), "--today", "2026-11-08"],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    url = f"http://127.0.0.1:{port}/"
    for _ in range(50):
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
            break
        except OSError:
            time.sleep(0.1)
    try:
        with sync_playwright() as p:
            br = p.chromium.launch()
            ctx = br.new_context(viewport={"width": 1440, "height": 1000})
            page = ctx.new_page()
            watch(page, "A")
            page.goto(url)
            page.wait_for_selector("#ln-splash", timeout=20000)
            ok("LEENAI_COMMON 로그인 카드 + ローカルプレビュー 버튼", page.locator("#c01-open-server").count() == 1 and page.locator(".ln-logo").count() >= 1)
            ok("탭 제목 = LEENAI C-01 搬入票 v0.3.7", page.title() == "LEENAI C-01 搬入票 v0.3.7", page.title())
            ok("로그인 버튼 활성 (R7A graph)", page.locator("#ln-login-btn").is_enabled())
            page.click("#c01-open-server")
            page.wait_for_selector("body[data-c01-ready='1']", timeout=20000)
            ok("헤더 C-01 · 버전 1곳", page.locator(".ln-header .ln-sys").inner_text() == "C-01" and "v0.3.7" in page.locator(".ln-hdr-ver").inner_text())
            ok("기본 테마 DARK", page.evaluate("document.documentElement.getAttribute('data-theme')") == "dark")
            ths = page.locator("#jikkyou-table thead th").all_inner_texts()
            ok("実況表 열 15 · 순서", ths == ["No", "CYカット", "Invoice番号", "品目", "CT番号", "シール番号", "正味重量", "風袋重量", "ベール数", "作業日", "条件", "圧縮業者",
                                       "Plant", "写真", "状況"], ths)
            ok("화면에 「確\u5b9a」 글자 0 (実況表)", "\u78ba\u5b9a" not in page.locator("body").inner_text())      # 글자는 escape (레포 grep 0)
            ok("화면 ✦ 표기 (Powered by LEENAI)", "✦ Powered by LEENAI Automation System" in page.locator("body").inner_text())
            # #109 ①: 사람 값 ≠ 엔진 다시 판정 값 → 사람 값 유지 + 정보 표시
            hrow = page.locator("tr.c01-row", has_text="TSTU0010218")
            ok("#109 ① 사람 값 유지 + 정보 (ⓘ)", hrow.locator("[data-info='human_vs_engine']").count() == 1 and HUMAN_SEAL in hrow.inner_text(),
               hrow.inner_text())
            # 전체 (担当者 미선택 = 全港)
            n_all = page.locator("tbody[data-iv]").count()
            ok("担当者 미선택 = 全港 (IV 5)", n_all == 5, n_all)
            cls = page.eval_on_selector_all("tr.c01-row", "els => els.map(e => e.className)")
            kinds = {k for c in cls for k in ("ok", "check", "wait") if f" {k}" in c}
            sts = set(page.eval_on_selector_all("tr.c01-row", "els => els.map(e => e.getAttribute('data-status') || 'メール未着')"))
            ok("줄 색 4종 (自動OK·確認済 초록 / 再確認 주황 / 受信中·メール未着 회색)", kinds == {"ok", "check", "wait"} and {"自動OK", "確認済", "再確認", "受信中", "メール未着"} <= sts, sorted(sts))
            ok("メール未着 줄", page.locator("tr.missing").count() == 3, page.locator("tr.missing").count())
            page.uncheck("#show-unarrived")
            ok("メール未着も表示 끄기 → 줄 없음", page.locator("tr.missing").count() == 0)
            page.check("#show-unarrived")
            page.screenshot(path=str(shots / "jikkyou_dark_all.png"), full_page=True)
            # ── v0.2.0 Compass入力 DRY 창 ──
            sys.path.insert(0, a.engine)
            from engine.compass_input.rules import compare_iv  # noqa: E402
            jik = json.loads((root / "_data" / "jikkyou.json").read_text(encoding="utf-8"))
            ok("전원 OK IV = Compass入力 버튼 (TST2611-01) · 催促 버튼 없음",
               page.locator("tbody[data-iv='TST2611-01'] .c01-btn-pri[data-compass]").count() == 1 and page.locator("tbody[data-iv='TST2611-01'] [data-remind]").count() == 0)
            page.click("tbody[data-iv='TST2611-01'] [data-compass]")
            page.wait_for_selector("#compass-table")
            states = set(page.eval_on_selector_all("#compass-table td[data-state]", "els => els.map(e => e.getAttribute('data-state'))"))
            warns = set(page.eval_on_selector_all("#compass-table [data-warn]", "els => els.map(e => e.getAttribute('data-warn'))"))
            ok("비교표 칸 색 (SAME · FILL · DIFF)", {"SAME", "FILL", "DIFF"} <= states, sorted(states))
            ok("경고 표시 (EXISTING_DIFF · TYPE_42_22 · CT_DUP)", {"EXISTING_DIFF", "TYPE_42_22", "CT_DUP"} <= warns, sorted(warns))
            sb = page.locator("#compass-send")
            ok("送信 비활성 「DRY — 送信しません」", sb.is_disabled() and "DRY" in sb.inner_text(), sb.inner_text())
            got = page.evaluate("JSON.stringify(C01.state.modal.res)")
            iv1 = next(x for x in jik["ivs"] if x["iv_no"] == "TST2611-01")
            snap = json.loads((root / "_data" / "compass_now" / "TST2611-01.json").read_text(encoding="utf-8"))
            rows_in = [{"container_id": r["container_id"], "ct": r["ct"], "seal": ((r.get("human") or {}).get("seal") or {}).get("value", r["seal"]), "n_w": r["n_w"],
                        "t_w": r["t_w"], "bales": r["bales"], "status": r["status"], "packer": r["packer"], "plant": r["plant"], "item": r["item"],
                        "ct_id": r["slot_guid"]} for r in iv1["rows"]]
            exp = compare_iv("TST2611-01", rows_in, snap["cells"], {k: set(v) for k, v in snap["dups"].items()})
            canon = lambda x: json.dumps(json.loads(json.dumps(x, default=sorted)), sort_keys=True, ensure_ascii=False)  # noqa: E731
            ok("화면 비교표 = 엔진 Python 비교표 (같은 입력)", canon(json.loads(got)) == canon(exp))
            page.screenshot(path=str(shots / "compass_dry.png"))
            page.click("[data-close]")
            page.click("tbody[data-iv='TST2611-02'] [data-compass]")
            page.wait_for_selector("#compass-table")
            ok("전원 OK 아닌 IV = 비교표만 · 사유 · 送信 비활성", page.locator("#cmp-reason").count() == 1 and "未確認" in page.locator("#cmp-reason").inner_text()
               and page.locator("#compass-send").is_disabled(), page.locator("#cmp-reason").inner_text() if page.locator("#cmp-reason").count() else "")
            page.click("[data-close]")
            # ── v0.2.0 催促 미리보기 ──
            page.click("tbody[data-iv='TST2611-02'] [data-remind]")
            page.wait_for_selector(".c01-rmd")
            body = page.locator(".c01-rbody").first.inner_text()
            subj = page.locator(".rsub").first.inner_text()
            rs = page.locator("#remind-send")
            ok("催促 미리보기 (받는 사람 · 제목 · 본문 · 회차 · 지난 기록)", "BKG-TEST-0002" in subj and "example.invalid" in page.locator(".c01-rmeta").first.inner_text()
               and "回目" in page.locator(".c01-rmeta").first.inner_text() and page.locator(".c01-rpast").count() == 1, subj)
            ok("催促 본문 끝 = ✦ Powered by LEENAI Automation System", body.strip().endswith("✦ Powered by LEENAI Automation System"))
            ok("催促 送信 비활성 「下書きのみ」", rs.is_disabled() and "下書き" in rs.inner_text())
            page.screenshot(path=str(shots / "remind_preview.png"))
            page.click("[data-close]")
            page.click("tbody[data-iv='TST2611-03'] [data-remind]")
            page.wait_for_selector(".c01-rmd")
            ok("주소 없는 업체 = 「送信先未登録」", "送信先未登録" in page.locator(".c01-rmeta").first.inner_text())
            page.click("[data-close]")
            # 담당 港 (#95)
            page.select_option("#me-select", "STAFF_A")
            page.wait_for_timeout(200)
            ivs = page.eval_on_selector_all("tbody[data-iv]", "els => els.map(e => e.getAttribute('data-iv'))")
            ok("담당 港 자동 (STAFF_A = TOKYO 担当 · YOKOHAMA 補助)", sorted(ivs) == ["TST2611-01", "TST2611-02", "TST2611-03"], ivs)
            page.select_option("#me-select", "STAFF_C")
            page.wait_for_timeout(200)
            ivs = page.eval_on_selector_all("tbody[data-iv]", "els => els.map(e => e.getAttribute('data-iv'))")
            ok("마스터에 없는 港 = * 줄 (STAFF_C = KOBE + * → HAKATA)", sorted(ivs) == ["TST2611-04", "TST2611-05"], ivs)
            page.click("[data-port='all']")
            ok("全港 전환", page.locator("tbody[data-iv]").count() == 5)
            # v0.3.7 (R7D Part U-2): 担当港 복수 선택 · 기억
            ivs_of = lambda: sorted(page.eval_on_selector_all("tbody[data-iv]", "els => els.map(e => e.getAttribute('data-iv'))"))
            page.click("[data-port='TOKYO']")
            page.click("[data-port='KOBE']")
            ok("U-2 港 2개 토글 = 두 港 IV (TOKYO 2 · KOBE 1)", ivs_of() == ["TST2611-01", "TST2611-03", "TST2611-04"], ivs_of())
            on = sorted(page.eval_on_selector_all("[data-port][aria-pressed='true']", "els => els.map(e => e.getAttribute('data-port'))"))
            ok("U-2 고른 港 버튼 2개 켜짐 (全港 · 自分の担当 꺼짐)", on == ["KOBE", "TOKYO"], on)
            saved = json.loads(page.evaluate("localStorage.getItem('c01_ports')") or "null")
            ok("U-2 브라우저 기억 (localStorage c01_ports)", saved == {"port": "set", "ports": ["TOKYO", "KOBE"]}, saved)
            page.click("[data-port='KOBE']")
            ok("U-2 다시 누르면 빠짐 (TOKYO 만)", ivs_of() == ["TST2611-01", "TST2611-03"], ivs_of())
            page.reload()
            page.wait_for_selector("#c01-open-server", timeout=20000)
            page.click("#c01-open-server")
            page.wait_for_selector("body[data-c01-ready='1']", timeout=20000)
            ok("U-2 다시 열어도 기억한 조합 (TOKYO)", ivs_of() == ["TST2611-01", "TST2611-03"], ivs_of())
            page.click("[data-port='TOKYO']")
            ok("U-2 모두 빼면 全港", page.locator("tbody[data-iv]").count() == 5 and page.locator("[data-port='all'][aria-pressed='true']").count() == 1)
            page.click("[data-port='mine']")
            ok("U-2 自分の担当 = 마스터 担当·補助 (STAFF_C = KOBE + *)", ivs_of() == ["TST2611-04", "TST2611-05"], ivs_of())
            page.click("[data-port='all']")
            page.select_option("#me-select", "STAFF_A")
            page.wait_for_timeout(200)
            # #112 催促 서명 = 누른 직원 주소 (초안 자리표시자 → 로그인 직원)
            page.click("[data-port='all']")
            page.click("tbody[data-iv='TST2611-02'] [data-remind]")
            page.wait_for_selector(".c01-rmd")
            body = page.locator(".c01-rbody").first.inner_text()
            ok("#112 催促 서명 Email = 로그인 직원 주소 · AI 문구 · ✦ 유지", "Email: staff.a@example.invalid" in body and "(送信者のメールアドレス)" not in body
               and "このメールはAIが自動送信しています" in body and body.strip().endswith("✦ Powered by LEENAI Automation System"), body[-200:])
            page.click("[data-close]")
            page.select_option("#me-select", "STAFF_A")
            page.wait_for_timeout(200)
            # 사진 보기
            page.locator("tbody[data-iv='TST2611-01'] .c01-phbtn").first.click()
            page.wait_for_selector(".c01-lb")
            c1 = page.locator(".c01-lb-h .c").inner_text()
            page.click("#lb-next")
            c2 = page.locator(".c01-lb-h .c").inner_text()
            page.keyboard.press("ArrowLeft")
            c3 = page.locator(".c01-lb-h .c").inner_text()
            strip = page.locator(".c01-lb-th").count()
            page.wait_for_function("() => { const e = document.querySelector('.c01-lbimg'); return e && e.complete && e.naturalWidth > 0; }", timeout=5000)
            nat = page.eval_on_selector(".c01-lbimg", "e => e.naturalWidth")
            ok("사진 크게 · 좌우 · 썸네일 띠", c1.startswith("1 / 9") and c2.startswith("2 / 9") and c3.startswith("1 / 9") and strip == 9 and nat > 0, [c1, c2, c3, strip, nat])
            page.screenshot(path=str(shots / "photo_viewer.png"))
            page.keyboard.press("Escape")
            # 30초 겹쳐 보기용 두 번째 창 (STAFF_B)
            page2 = ctx.new_page() if False else br.new_context(viewport={"width": 1440, "height": 1000}).new_page()
            watch(page2, "B")
            open_local(page2, url, "STAFF_B")
            # 要確認 옆 패널 → confirm_value (값의 違い seal)
            page.locator("tbody[data-iv='TST2611-02'] .c01-checkbtn").first.click()
            page.wait_for_selector(".c01-side")
            page.screenshot(path=str(shots / "panel.png"))
            page.locator(".c01-side [data-pick='seal']").nth(1).click()
            t0 = time.time()
            page.click("#panel-ok")
            page.wait_for_selector("tbody[data-iv='TST2611-02'] tr[data-status='確認済']", timeout=3000)
            ok("본인 화면 즉시 반영 (再確認 → 確認済)", True, f"{time.time() - t0:.2f}s")
            for _ in range(30):
                if actions(root):
                    break
                time.sleep(0.1)
            ok("_actions 파일 1 (confirm_value · 写真)", len(actions(root)) == 1 and actions(root)[0]["action"] == "confirm_value" and actions(root)[0]["source"] == "写真",
               actions(root))
            # 다른 창: 30초 안 (자동 polling)
            if not a.no_wait30:
                t1 = time.time()
                try:
                    page2.wait_for_selector("tbody[data-iv='TST2611-02'] tr[data-status='確認済']", timeout=32000)
                    ok("다른 창 30초 안 반영 (자동 polling)", True)
                    RES["other_window_secs"] = round(time.time() - t1, 1)
                except Exception as e:  # noqa: BLE001
                    ok("다른 창 30초 안 반영 (자동 polling)", False, e)
            # 確認・入力
            page.click("#tab-input")
            page.wait_for_selector(".c01-input")
            kinds_txt = page.locator(".c01-kinds .c01-chip").all_inner_texts()
            ok("確認・入力 4종 + すべて", [k.split(" ")[0] for k in kinds_txt] == ["すべて", "値の違い", "手入力", "写真の", "未分類"] or len(kinds_txt) == 5, kinds_txt)
            page.screenshot(path=str(shots / "input_dark.png"), full_page=True)
            # v0.3.7 (R7D Part U-3): 판단 버튼 = 오른쪽 패널 맨 위 (항목 제목 바로 아래) · 모든 종류 같은 위치
            pos_ok = []
            for kd in ["値の違い", "手入力", "写真のCT", "未分類FAX"]:
                page.click(f".c01-kinds [data-kind='{kd}']")
                if page.locator(".c01-item").count():
                    page.locator(".c01-item").first.click()
                    pos_ok.append((kd, page.evaluate("""() => { const h = document.querySelector('.c01-form .c01-form-h'); const a = h && h.nextElementSibling;
                      return !!(a && a.classList.contains('c01-form-a') && a.querySelector('#q-submit') && a.querySelector('#q-skip')
                        && a.getBoundingClientRect().top < document.querySelector('.c01-form .c01-form-b').getBoundingClientRect().top); }""")))
            ok("U-3 판단 버튼 위치 = 제목 바로 아래 (STAFF_A 담당 港 3종 · 手入力 은 아래 全港 에서)", len(pos_ok) == 3 and all(v for _, v in pos_ok), pos_ok)
            page.click(".c01-kinds [data-kind='未分類FAX']")
            ok("U-3 当社案件ではない 도 위 (未分類FAX)", page.locator(".c01-form-a #q-notours").count() == 1)
            page.click(".c01-kinds [data-kind='all']")
            page.click(".c01-kinds [data-kind='値の違い']")
            items = page.locator(".c01-item")
            for i in range(items.count()):
                if "シール" in items.nth(i).inner_text():
                    items.nth(i).click()
                    break
            srcs = page.eval_on_selector_all(".c01-src", "els => els.map(e => e.textContent)")
            ok("確認・入力 다른 칸 근거 문장 (field_source_text)", len(srcs) >= 3 and any("と一致" in x for x in srcs), srcs)
            page.screenshot(path=str(shots / "input_sources.png"))
            # 체크디짓 거부 (手入力 CT) — STAFF_C 담당 KOBE 의 항목이라 全港 으로
            page.click("#tab-main")
            page.click("[data-port='all']")
            page.click("#tab-input")
            page.click(".c01-kinds [data-kind='手入力']")
            ok("U-3 판단 버튼 위치 = 제목 바로 아래 (手入力)", page.evaluate("""() => { const h = document.querySelector('.c01-form .c01-form-h'); const a = h && h.nextElementSibling;
              return !!(a && a.classList.contains('c01-form-a') && a.querySelector('#q-submit') && a.querySelector('#q-skip')); }"""))
            items = page.locator(".c01-item")
            target = None
            for i in range(items.count()):
                if "CT番号" in items.nth(i).inner_text():
                    target = i
            items.nth(target).click()
            dmsg = []
            page.once("dialog", lambda dg: (dmsg.append(dg.message), dg.dismiss()))
            page.fill("#q-in", "TSTU0000015")
            page.click("#q-submit")
            page.wait_for_timeout(300)
            err = page.locator("#q-err").inner_text() if page.locator("#q-err").count() else ""
            ok("#109 ③ 체크디짓 틀림 = 확인창 「チェックディジットが合いません。もう一度確認してください」 · 취소 = 저장 안 함",
               dmsg == ["チェックディジットが合いません。もう一度確認してください"] and len(actions(root)) == 1 and "チェックディジット" in err, [dmsg, err])
            page.once("dialog", lambda dg: (dmsg.append(dg.message), dg.accept()))
            page.click("#q-submit")
            page.wait_for_timeout(400)
            ovr = [x for x in actions(root) if x["action"] == "manual_input" and x["field"] == "ct"]
            ok("#109 ③ 확인 = 저장 (manual_input · override CT_CHECKDIGIT_OVERRIDE)", len(ovr) == 1 and ovr[0]["value"] == "TSTU0000015"
               and ovr[0].get("override") == ["CT_CHECKDIGIT_OVERRIDE"], ovr)
            # 手入力 bales
            page.click(".c01-kinds [data-kind='手入力']")
            items = page.locator(".c01-item:not(.done)")
            for i in range(items.count()):
                if "ベール数" in items.nth(i).inner_text():
                    items.nth(i).click()
                    break
            page.fill("#q-in", "23")
            page.click("#q-submit")
            page.wait_for_timeout(300)
            ok("手入力 bales → manual_input 23", any(x["action"] == "manual_input" and x["field"] == "bales" and x["value"] == 23 for x in actions(root)))
            # 先勝ち: 다른 사람이 먼저 (파일 직접 — 다른 창 흉내) → polling 뒤 「他の人が先に確認しました」
            q = json.loads((root / "_data" / "queue.json").read_text(encoding="utf-8"))
            tw = next(x for x in q["items"] if x["kind"] == "値の違い" and x["field"] == "t_w")
            other = {"schema_version": 1, "action_id": "zz-other-0001", "action": "confirm_value", "iv": tw["iv_no"], "ct": tw["ct"], "field": "t_w", "value": 3740,
                     "source": "写真", "by": "staff.c@example.invalid", "at": "2026-11-08T09:00:00+09:00", "queue_id": tw["queue_id"]}
            d = root / "_actions" / "2026-11-08"
            d.mkdir(parents=True, exist_ok=True)
            (d / "zz-other-0001.json").write_text(json.dumps(other, ensure_ascii=False), encoding="utf-8")
            page.evaluate("C01.app.tick()")
            page.wait_for_timeout(500)
            page.click(".c01-kinds [data-kind='値の違い']")
            items = page.locator(".c01-item")
            for i in range(items.count()):
                if "風袋重量" in items.nth(i).inner_text():
                    items.nth(i).click()
                    break
            lost = page.locator(".c01-form .c01-lost").count() == 1 and "他の人が先に確認しました" in page.locator(".c01-form .c01-lost").inner_text()
            ok("先勝ち: 다른 사람이 먼저 → 「他の人が先に確認しました」", lost)
            page.screenshot(path=str(shots / "input_conflict.png"))
            # 写真のCT
            page.click(".c01-kinds [data-kind='写真のCT']")
            page.locator(".c01-item").first.click()
            page.locator("[data-choice='0']").click()
            page.click("#q-submit")
            page.wait_for_timeout(300)
            ok("写真のCT → assign_photos (paths 4)", any(x["action"] == "assign_photos" and len(x["value"]["paths"]) == 4 for x in actions(root)))
            # 未分類FAX
            page.click(".c01-kinds [data-kind='未分類FAX']")
            page.locator(".c01-item").first.click()
            page.fill("#q-iv", "tst2611-01")
            page.click("#q-submit")
            page.wait_for_timeout(300)
            ok("未分類FAX → link_fax (IV 대문자)", any(x["action"] == "link_fax" and x["iv"] == "TST2611-01" for x in actions(root)))
            # 실況표 で 確認済 · 確認・入力 바지
            page.click("#tab-main")
            # _actions JSON = 엔진 스키마
            sys.path.insert(0, a.engine)
            from engine.output import schema_check  # noqa: E402
            sch = schema_check.load("action")
            errs = {x["action_id"]: schema_check.errors(x, sch) for x in actions(root)}
            ok("_actions JSON = 엔진 action.schema.json (오류 0)", all(not e for e in errs.values()), {k: v for k, v in errs.items() if v})
            RES["actions"] = [{k: x[k] for k in ("action", "field", "source", "queue_id")} for x in actions(root)]
            # #109 ② slot_change = 모든 직원 (STAFF_A · 관리자 목록 없음) · 빈 칸으로 · 입れ替え 확인창 · 되돌리기
            page.click("#tab-main")
            page.click("[data-port='all']")
            page.wait_for_timeout(200)
            tb = "tbody[data-iv='TST2611-01']"
            ok("#109 ② ⇄ 버튼 = 관리자 아닌 직원에게도", page.locator(tb + " [data-slot]").count() == 4, page.locator(tb + " [data-slot]").count())
            n0 = len(actions(root))
            ids0 = {x["action_id"] for x in actions(root)}
            iv1 = next(x for x in json.loads((root / "_data" / "jikkyou.json").read_text(encoding="utf-8"))["ivs"] if x["iv_no"] == "TST2611-01")
            r0, r1, r2 = iv1["rows"][0], iv1["rows"][1], iv1["rows"][2]
            page.locator(tb + " [data-slot]").nth(0).click()
            page.wait_for_selector("[data-slotpick]")
            free = page.locator("[data-slotpick]", has_text="空き")
            ok("슬롯 창: 칸 목록 · 빈 칸 표시", page.locator("[data-slotpick]").count() == 5 and free.count() == 1, page.locator("[data-slotpick]").count())
            free_guid = free.get_attribute("data-slotpick")
            free.click()
            page.click("#slot-apply")
            page.wait_for_timeout(400)
            sc = [x for x in actions(root) if x["action"] == "slot_change" and x["action_id"] not in ids0]
            ok("빈 칸으로 변경 → slot_change 1 (누가·언제·전→후)", len(sc) == 1 and sc[0]["ct"] == r0["ct"] and sc[0]["by"] == "staff.a@example.invalid" and sc[0]["at"]
               and sc[0]["value"] == {"slot_guid": free_guid, "slot_before": r0["slot_guid"], "swap_ct": None}, sc)
            badge = page.locator(f"tr.c01-row[data-key*='{r0['ct']}'] [data-info='slot_change']")
            ok("줄 정보 표시 「⇄ 枠変更」 (누가·언제·전→후)", badge.count() == 1 and "STAFF A" in (badge.get_attribute("title") or "") and "→" in (badge.get_attribute("title") or ""),
               badge.get_attribute("title") if badge.count() else None)
            # 입れ替え: r1 을 r2 칸으로 → 확인창 (취소 → 기록 0 · 확인 → 2건)
            dl = []
            page.locator(tb + " [data-slot]").nth(1).click()
            page.wait_for_selector("[data-slotpick]")
            page.locator(f"[data-slotpick='{r2['slot_guid']}']").click()
            page.once("dialog", lambda dg: (dl.append(dg.message), dg.dismiss()))
            page.click("#slot-apply")
            page.wait_for_timeout(300)
            n1 = len(actions(root))
            ids1 = {x["action_id"] for x in actions(root)}
            page.once("dialog", lambda dg: (dl.append(dg.message), dg.accept()))
            page.click("#slot-apply")
            page.wait_for_timeout(400)
            sw = [x for x in actions(root) if x["action"] == "slot_change" and x["action_id"] not in ids1]
            ok("#109 ② 입れ替え 확인창 「○○ が入っています。入れ替えますか」 · 취소 = 기록 0", dl and dl[0] == f"{r2['ct']} が入っています。入れ替えますか" and n1 == n0 + 1, dl)
            ok("입れ替え 확인 → slot_change 1건 (swap_ct · 두 대를 한 기록으로)", len(sw) == 1 and (sw[0]["ct"], sw[0]["value"]["slot_guid"], sw[0]["value"]["slot_before"],
               sw[0]["value"]["swap_ct"]) == (r1["ct"], r2["slot_guid"], r1["slot_guid"], r2["ct"]), sw)
            b2 = page.locator(f"tr.c01-row[data-key*='{r2['ct']}'] [data-info='slot_change']")
            ok("입れ替え 상대 줄에도 정보 표시", b2.count() == 1 and r1["ct"] in (b2.get_attribute("title") or ""), b2.get_attribute("title") if b2.count() else None)
            # 되돌리기 (r0)
            page.locator(tb + " [data-slot]").nth(0).click()
            page.wait_for_selector("#slot-undo")
            page.click("#slot-undo")
            page.wait_for_timeout(400)
            un = sorted([x for x in actions(root) if x["action"] == "slot_change" and x["ct"] == r0["ct"]], key=lambda x: (x["at"], x["value"]["slot_guid"] == r0["slot_guid"]))
            ok("元に戻す → slot_change (전 칸으로 · slot_before = 지금 칸)", len(un) == 2 and un[-1]["value"]["slot_guid"] == r0["slot_guid"]
               and un[-1]["value"]["slot_before"] == free_guid, un[-1:])
            page.screenshot(path=str(shots / "slot_change.png"))
            # 4 테마
            for th in ("dark", "light", "leenai", "focus"):
                page.evaluate(f"localStorage.setItem('leenai_theme','{th}'); document.documentElement.setAttribute('data-theme','{th}')")
                page.wait_for_timeout(150)
                page.screenshot(path=str(shots / f"jikkyou_{th}.png"), full_page=False)
                RES.setdefault("themes", []).append(page.evaluate("document.documentElement.getAttribute('data-theme')"))
            ok("4 테마 전환 (dark · light · leenai · focus)", RES.get("themes") == ["dark", "light", "leenai", "focus"], RES.get("themes"))
            page.click("#tab-input")
            page.evaluate("document.documentElement.setAttribute('data-theme','light')")
            page.screenshot(path=str(shots / "input_light.png"), full_page=False)
            ok("콘솔 오류 0", not RES["console_errors"], RES["console_errors"][:5])
            ok("네트워크 = LEENAI_COMMON · 127.0.0.1 만", not RES["external_requests"], sorted(set(RES["external_requests"]))[:5])
            br.close()
    finally:
        srv.terminate()
        shutil.rmtree(tmp, ignore_errors=True)
    n_ng = sum(1 for c in RES["checks"] if not c["ok"])
    (shots / "result.json").write_text(json.dumps(RES, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"== {len(RES['checks']) - n_ng}/{len(RES['checks'])} OK")
    return 1 if n_ng else 0


if __name__ == "__main__":
    sys.exit(main())
