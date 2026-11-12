# ✦ Powered by LEENAI Automation System — C-01 搬入票 TOOL v0.1 画面試験 (Playwright · 가명 fixtures)
"""fixtures 를 임시 폴더로 복사 → serve_local.py (127.0.0.1) → Chromium 으로 열어 확인.
확인: 実況表 열 15 · 줄 색 4종 · 담당 港 거르기 · メール未着 줄 · 사진 보기 넘기기 · 確認・入力 4종 처리 · _actions JSON = 엔진 스키마 ·
      30초 겹쳐 보기 (다른 창) · 先勝ち · 체크디짓 거부 · Compass入力/催促 비활성 · 4테마 스크린샷 · 콘솔 오류 0 · 네트워크 = LEENAI_COMMON·로컬만.
사용: python tests/test_ui.py [--shots 폴더] [--engine C:\\LEENAI_C01_V2\\engine_r5] [--no-wait30]"""
import argparse
import json
import re
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


def fill_field(page, label, value):
    """v0.3.11: 카드 안 값 확인 칸 (label = CT番号 · ベール数 …) 에 입력."""
    page.locator(".c01-field[data-vq]", has_text=label).locator("input").fill(value)


def open_local(page, url, staff=None):
    page.goto(url)
    page.wait_for_selector("#c01-open-server", timeout=20000)
    page.click("#c01-open-server")
    page.wait_for_selector("body[data-c01-ready='1']", timeout=20000)
    if staff:
        page.select_option("#me-select", staff)
        page.wait_for_timeout(200)


def photo_tab_checks(page, ctx, shots):
    """v0.3.13 (R7L Part E · D-65): 사진 버튼 = 같은 창의 새 탭 (photo.html)."""
    page.evaluate("""() => { const o = window.open; window.__oa = []; window.open = function () { window.__oa.push([].slice.call(arguments)); return o.apply(window, arguments); }; }""")
    btn = page.locator("tbody[data-iv='TST2611-01'] .c01-phbtn").first
    key = btn.get_attribute("data-photos")
    iv_no, ct = key.split("|")[0], key.split("|")[1]
    n_pages0 = len(ctx.pages)
    with ctx.expect_page(timeout=10000) as pi:
        btn.click()
    tab = pi.value
    watch(tab, "PHOTO")
    tab.wait_for_selector(".c01-pv-th", timeout=10000)
    tab.wait_for_function("() => document.querySelectorAll('.c01-pv-thimg').length === 9 && [...document.querySelectorAll('.c01-pv-thimg')].every(e => e.complete && e.naturalWidth > 0)", timeout=10000)
    oa = page.evaluate("window.__oa")
    name = tab.evaluate("window.name")
    want = page.evaluate("k => C01.app.photoTabName(k)", key)
    ok("E 사진 클릭 = 새 탭 (window.open 인자 2개 · 창 기능 문자열 없음 = 팝업 창 아님)", len(oa) == 1 and len(oa[0]) == 2 and oa[0][1] == want and len(ctx.pages) == n_pages0 + 1, oa)
    ok("E 탭 이름 = c01-photo-{행 키 해시 8자리} · 주소 = photo.html?k=해시 (CT 를 이름·주소에 안 넣음)",
       name == want and re.fullmatch(r"c01-photo-[0-9a-f]{8}", name) and re.search(r"/photo\.html\?k=[0-9a-f]{8}$", tab.url) and ct not in tab.url and ct not in name, [name, tab.url])
    head = tab.locator("#pv-head").inner_text()
    ok("E 머리 = IV · CT · 업체 · 장수", iv_no in head and ct in head and "PACKER_A" in head and "9枚" in head, head)
    ok("E 탭 제목 = 写真 CT · IV", tab.title().startswith("写真 " + ct) and iv_no in tab.title(), tab.title())
    srcs = tab.eval_on_selector_all(".c01-pv-thimg", "els => els.map(e => e.src.slice(0, 5))")
    ok("E 사진 = 원래 탭에서 받은 Blob (새 탭 = 로그인·Graph 호출 0 · blob: URL)", srcs and all(x == "blob:" for x in srcs), srcs[:3])
    ok("E 새 탭에 로그인 화면 · LEENAI_COMMON JS 없음", tab.locator("#ln-splash").count() == 0 and tab.evaluate("typeof window.LEENAI") == "undefined")
    pos = lambda: tab.locator("#pv-pos").inner_text()
    p1 = pos()
    tab.keyboard.press("ArrowRight")
    p2 = pos()
    tab.keyboard.press("ArrowLeft")
    tab.keyboard.press("ArrowLeft")
    p3 = pos()
    tab.click(".c01-pv-th[data-go='2']")
    p4 = pos()
    tab.wait_for_function("() => { const e = document.querySelector('.c01-pv-img'); return e && e.complete && e.naturalWidth > 0; }", timeout=5000)
    ok("E 사진 크게 · ← → 키 · 썸네일 줄 9", (p1, p2, p3, p4) == ("1 / 9", "2 / 9", "9 / 9", "3 / 9") and tab.locator(".c01-pv-th").count() == 9, [p1, p2, p3, p4])
    chips = tab.eval_on_selector_all(".c01-pv-th .c01-pv-kind", "els => els.map(e => e.textContent)")
    ok("E 사진 종류 표시 (가명 라벨 → 空コンテナ · 積込中 · FULL · 扉 · SEAL)", {"空コンテナ", "積込中", "FULL", "SEAL", "扉"} <= set(chips) and tab.locator(".c01-pv-bar .c01-pv-kind").count() == 1, chips)
    # v0.3.14 (R7M C-1): エンジン fill (out_photo_fill) — 両扉 (fill door_closed) = 扉閉め · 片扉 (door_open) = 扉 · 積込 100% (full) = FULL
    ok("E 엔진 fill → 扉閉め (両扉 · door_closed) · 片扉 door_open = 扉", chips.count("扉閉め") == 1 and chips.count("扉") == 1 and chips.count("FULL") == 1, chips)
    km = tab.evaluate("""() => [{label:'interior'},{label:'cargo'},{fill:'full',label:'cargo'},{fill:'door_closed',label:'door'},{label:'door'},{label:'seal'},{label:'cotecna'},{label:''},{label:null}]
      .map(p => C01.photoKind(p).text)""")
    ok("E 종류 = 엔진 kind (interior 空 · cargo 積込中 · fill full FULL · door_closed 扉閉め · door 扉 · SEAL · COTECNA · 없음 = 표시 없음)",
       km == ["空コンテナ", "積込中", "FULL", "扉閉め", "扉", "SEAL", "COTECNA", "", ""], km)
    th = []
    for i in range(4):
        th.append(tab.evaluate("document.documentElement.getAttribute('data-theme')"))
        tab.screenshot(path=str(shots / f"photo_tab_{th[-1]}.png"))
        tab.click("#pv-theme")
    ok("E 새 탭 4 테마 (dark → light → leenai → focus)", th == ["dark", "light", "leenai", "focus"], th)
    tab.evaluate("localStorage.setItem('leenai_theme','dark'); document.documentElement.setAttribute('data-theme','dark')")
    page.evaluate("document.documentElement.setAttribute('data-theme','dark')")
    # 같은 컨테이너 다시 = 새 탭 안 만듦 (그 탭으로)
    tab.keyboard.press("ArrowRight")
    n1 = len(ctx.pages)
    btn.click()
    page.wait_for_timeout(800)
    ok("E 같은 컨테이너 다시 = 새 탭 없음 · 같은 탭 (다시 읽지 않음 · 1장으로)", len(ctx.pages) == n1 and not tab.is_closed() and pos() == "1 / 9"
       and page.evaluate("window.__oa.length") == 2, [len(ctx.pages), n1, pos()])
    # 다른 컨테이너 = 다른 탭
    other = page.locator("tbody[data-iv='TST2611-01'] .c01-phbtn").nth(1)
    with ctx.expect_page(timeout=10000) as pi2:
        other.click()
    tab2 = pi2.value
    tab2.wait_for_selector(".c01-pv-th", timeout=10000)
    ok("E 다른 컨테이너 = 다른 탭 (이름 다름)", tab2.evaluate("window.name") != name and tab2.evaluate("window.name").startswith("c01-photo-"))
    tab2.close()
    # 실況表에 없는 해시 · 원래 화면 없음
    with ctx.expect_page(timeout=10000) as pi3:
        page.evaluate("window.open('photo.html?k=00000000', 'c01-photo-test')")
    t3 = pi3.value
    t3.wait_for_selector(".c01-pv-msg", timeout=10000)
    ok("E 없는 컨테이너 = 「今の実況表にありません」", "実況表にありません" in t3.locator(".c01-pv-msg").inner_text())
    t3.close()
    lone = ctx.new_page()
    lone.goto(tab.url)
    lone.wait_for_selector(".c01-pv-msg", timeout=10000)
    ok("E 원래 화면 없이 열면 = 안내만 (로그인 시작 0)", "元の画面" in lone.locator(".c01-pv-msg").inner_text() and lone.locator("#ln-splash").count() == 0, lone.locator(".c01-pv-msg").inner_text())
    lone.close()
    tab.close()
    # 要確認 옆 창 「写真」 = 같은 새 탭 방식
    got = None
    for i in range(page.locator(".c01-checkbtn").count()):
        page.locator(".c01-checkbtn").nth(i).click()
        page.wait_for_selector("#panel-photo", timeout=5000)
        if page.locator("#panel-photo").is_enabled():
            with ctx.expect_page(timeout=10000) as pi4:
                page.click("#panel-photo")
            t4 = pi4.value
            t4.wait_for_selector(".c01-pv-th", timeout=10000)
            got = [t4.evaluate("window.name"), page.locator(".c01-lb").count()]
            t4.close()
            page.evaluate("C01.state.sel = null; C01.app.render()")
            break
        page.evaluate("C01.state.sel = null; C01.app.render()")
    ok("E 要確認 옆 창 写真 = 새 탭 (라이트박스 아님)", got and got[0].startswith("c01-photo-") and got[1] == 0, got)


def h4_checks(page, jj):
    """v0.3.15 (R7N Part H-4 · 결정 #166): 칸보다 줄이 많은 부킹 = 넘는 줄만 빨강 「COMPASS 枠外」 · 머리 「枠外 n」. 칸이 남은 未割当 = 그대로."""
    over = page.evaluate("""() => Object.fromEntries([...document.querySelectorAll('tbody[data-iv]')].map(tb => [tb.dataset.iv,
        [tb.querySelectorAll('tr.c01-row.over').length, (tb.querySelector('.c01-overhead') || {}).textContent || '',
         [...tb.querySelectorAll('tr.c01-row')].map(tr => tr.classList.contains('over') ? 'o' : tr.classList.contains('unassigned') ? 'u' : 's').join('')]]))""")
    # v0.3.18 (R7S #15 · 결정 #182): 줄 (칸 있는 줄 + 칸 없는 줄) > COMPASS 칸 = 칸 없는 줄 (未割当) 전부 빨강 (빈 칸이 남아도) · 줄 ≤ 칸 = 枠外 없음
    sg = lambda iv: {s["slot_guid"] for s in iv["slots"]}   # noqa: E731
    want = {iv["iv_no"]: (sum(1 for r in iv["rows"] if r.get("slot_guid") not in sg(iv)) if len(iv["rows"]) > len(iv["slots"]) else 0) for iv in jj["ivs"]}
    free02 = sum(1 for r in next(iv for iv in jj["ivs"] if iv["iv_no"] == "TST2611-02")["rows"] if not r.get("slot_guid"))
    ok("#15 枠外 줄 수 = 줄 > 칸 이면 칸 없는 줄 전부 (TST2611-02 = 4줄 · 3칸 · 빈 칸 1 남음 → 未割当 2줄 모두) · 다른 부킹 0",
       {k: v[0] for k, v in over.items()} == want and want["TST2611-02"] == 2 == free02, [over, want])
    ok("#15 머리 「枠外 2」 (그 부킹만 · n = 칸 없는 줄 수)", over["TST2611-02"][1] == "枠外 2" and all(v[1] == "" for k, v in over.items() if k != "TST2611-02"), over)
    ok("#15 TST2611-02 未割当 표시 0 (전부 枠外) · TST2611-04 (줄 4 ≤ 칸 4) 未割当 2줄 = 빨강 아님", "u" not in over["TST2611-02"][2] and over["TST2611-02"][2].endswith("oo")
       and over["TST2611-04"][2].count("u") == 2 and "o" not in over["TST2611-04"][2], over)
    tr = page.locator("tbody[data-iv='TST2611-02'] tr.c01-row.over")
    ok("H-4 枠外 줄 状況 칸 = 「COMPASS 枠外」 (未割当 표시 대신)", tr.count() == 2 and tr.locator(".c01-over").all_inner_texts() == ["COMPASS 枠外"] * 2
       and tr.locator(".c01-unassigned").count() == 0, tr.all_inner_texts())
    hd = page.locator("tbody[data-iv='TST2611-02'] .c01-ivhead").inner_text()
    ok("H-4 머리 n/N台 의 N = 3 (枠外 줄을 세지 않음)", re.search(r"[0-9]+/3台", hd) is not None, hd)
    ok("H-4 범례 「COMPASS 枠外」", "COMPASS 枠外" in page.locator(".c01-legend").inner_text())
    cols = []
    for th in ("dark", "light", "leenai", "focus"):
        page.evaluate(f"document.documentElement.setAttribute('data-theme','{th}')")
        cols.append(page.evaluate("""() => { const td = document.querySelector("tbody[data-iv='TST2611-02'] tr.c01-row.over td.c-st");
            const n = document.querySelector("tbody[data-iv='TST2611-02'] tr.c01-row:not(.over) td.c-st"); const ch = document.querySelector('.c01-overhead');
            const cs = getComputedStyle(td), rgb = s => (s.match(/[0-9.]+/g) || []).map(Number);
            return [document.documentElement.getAttribute('data-theme'), rgb(cs.backgroundColor), cs.fontWeight, rgb(getComputedStyle(n).backgroundColor), rgb(getComputedStyle(ch).backgroundColor)]; }"""))
    page.evaluate("document.documentElement.setAttribute('data-theme','dark')")
    red = lambda c: len(c) >= 3 and c[0] > c[1] + 60 and c[0] > c[2] + 40   # noqa: E731
    ok("H-4 4테마 모두 빨강 배경 · 굵은 글씨 · 「枠外」 표 빨강 (보통 줄과 다름)", all(red(c[1]) and int(c[2]) >= 700 and c[1] != c[3] and red(c[4]) for c in cols), cols)


def help_checks(page, shots):
    """v0.3.17 (R7P · #175 · #176): 머리 「使い方」 → 1 화면 안내 (병행 기간 · 試験表示 · 이름·메일 0 · 4테마)."""
    hb = page.locator("#c01-nav #help-open")
    ok("v0.3.17 머리 「使い方」 버튼", hb.count() == 1 and hb.inner_text().strip() == "使い方", hb.count())
    hb.click()
    page.wait_for_selector("#help-body")
    txt = page.locator("#help-body").inner_text()
    need = ["並行期間", "これまでのシステム", "見る", "確認・入力", "試験表示", "催促", "Compass入力", "自分の担当", "自動OK", "再確認", "受信中",
            "✎ 修正", "搬入票ではない", "元に戻す", "Ctrl+Shift+R", "気づいた点は担当の管理者へ（画面の写真と IV 番号）"]
    ok("v0.3.17 使い方 창 열림 · 내용 (試験表示 · 상태 · 確認・入力 · Ctrl+Shift+R · 관리자)", all(w in txt for w in need), [w for w in need if w not in txt])
    ok("v0.3.17 使い方 「\u78ba\u5b9a」 글자 0 · 메일·사람 이름 0", "\u78ba\u5b9a" not in txt and "@" not in txt and "\u674e" not in txt and "さんへ" not in txt)
    fit = page.evaluate("""() => { const m = document.querySelector('.c01-modal-help'), b = document.getElementById('help-body'); const r = m.getBoundingClientRect();
        return [r.top >= 0 && r.bottom <= innerHeight, b.scrollHeight <= b.clientHeight + 2, Math.round(r.height), b.scrollHeight, b.clientHeight]; }""")
    ok("v0.3.17 使い方 = 1 화면 (1440×1000 · 창 안 스크롤 없음)", fit[0] and fit[1], fit)
    cols = []
    for th in ("dark", "light", "leenai", "focus"):
        page.evaluate(f"document.documentElement.setAttribute('data-theme','{th}')")
        page.wait_for_timeout(100)
        cols.append(page.evaluate("""() => { const c = s => getComputedStyle(document.querySelector(s));
            return [c('.c01-help').color, c('.c01-modal-help').backgroundColor, c('.c01-help .c01-trial').color, c('.c01-help-lead').backgroundColor]; }"""))
        page.screenshot(path=str(shots / f"help_{th}.png"))
    page.evaluate("document.documentElement.setAttribute('data-theme','dark')")
    ok("v0.3.17 使い方 4테마 글자색 ≠ 배경색 (본문 · 試験表示)", len(cols) == 4 and all(c[0] != c[1] and c[2] != c[1] and c[2] != c[3] and c[0] != c[3] for c in cols), cols)
    page.click("[data-close]")
    ok("v0.3.17 使い方 닫기", page.locator("#c01-modal").is_hidden())


ROT_MEASURE = """() => { const ob = document.querySelector('.c01-orig-b'), box = document.querySelector('.c01-orig .c01-doc.img'), im = box && box.querySelector('img.c01-docimg');
  if (!ob || !im) return null;
  ob.scrollTop = 0; ob.scrollLeft = 0;
  const c = ob.getBoundingClientRect(), r = im.getBoundingClientRect(), b = box.getBoundingClientRect();
  const out = { rot: box.dataset.rot, fit: box.dataset.fit, top: r.top - c.top, left: r.left - c.left, bottom: r.bottom - c.top, right: r.right - c.left,
    sh: ob.scrollHeight, sw: ob.scrollWidth, w: r.width, h: r.height, bw: b.width, bh: b.height,
    inBox: r.left >= b.left - 2 && r.top >= b.top - 2 && r.right <= b.right + 2 && r.bottom <= b.bottom + 2 };
  ob.scrollTop = ob.scrollHeight; ob.scrollLeft = ob.scrollWidth;
  const c2 = ob.getBoundingClientRect(), r2 = im.getBoundingClientRect();
  out.endBottom = r2.bottom - c2.bottom; out.endRight = r2.right - c2.right;
  ob.scrollTop = 0; ob.scrollLeft = 0;
  return out; }"""


def rot_checks(page, shots):
    """v0.3.18 (R7S #3): 화상 원본 0 · 90 · 180 · 270 (엔진 180 + ⟳) × 확대 60 · 100 · 200 — 그린 화상이 스크롤 영역 안 (위 · 왼쪽이 잘리지 않음 ·
    끝까지 스크롤하면 아래 · 오른쪽 끝이 보임) · 90 · 270 = 가로 ↔ 세로."""
    res = {}
    for zoom in (100, 200, 60):
        for tgt in (0, 90, 180, 270):
            page.evaluate(f"C01.state.zoom = {zoom}; C01.state.rot = {(tgt - 180) % 360}; C01.app.render()")
            page.wait_for_function(f"""() => {{ const b = document.querySelector('.c01-orig .c01-doc.img'); const im = b && b.querySelector('img.c01-docimg');
                return b && b.dataset.rot === '{tgt}' && im && im.complete && im.naturalWidth > 0 && (b.dataset.fit || '').startsWith('{tgt}:'); }}""", timeout=10000)
            res[(zoom, tgt)] = page.evaluate(ROT_MEASURE)
            if zoom == 100 and tgt == 90:
                page.screenshot(path=str(shots / "r7s_rot90.png"))
    inside = {k: v for k, v in res.items() if not (v and v["top"] >= -0.5 and v["left"] >= -0.5 and v["bottom"] <= v["sh"] + 0.5 and v["right"] <= v["sw"] + 0.5
                                                    and v["endBottom"] <= 0.5 and v["endRight"] <= 0.5 and v["inBox"])}
    ok("#3 화상 0/90/180/270 × 확대 60/100/200 = 그린 화상이 스크롤 영역 안 (스크롤 0 에서 위·왼쪽 안 잘림 · 끝까지 스크롤하면 아래·오른쪽 보임 · 상자 안)",
       not inside, inside or [res[(100, 90)]])
    sw = all(abs(res[(z, 90)]["w"] - res[(z, 0)]["h"]) <= 2 and abs(res[(z, 90)]["h"] - res[(z, 0)]["w"]) <= 2 and abs(res[(z, 270)]["w"] - res[(z, 0)]["h"]) <= 2
             and abs(res[(z, 180)]["w"] - res[(z, 0)]["w"]) <= 2 and abs(res[(z, 90)]["bw"] - res[(z, 0)]["bh"]) <= 2 for z in (60, 100, 200))
    ok("#3 90° · 270° = 가로 ↔ 세로 (화상 · 상자 둘 다) · 180° = 그대로", sw, {f"{k[0]}:{k[1]}": [round(v["w"]), round(v["h"]), round(v["bw"]), round(v["bh"])] for k, v in res.items()})
    ok("#3 확대 200% = 1280px 폭 (90° 면 높이 1280px)", abs(res[(200, 0)]["w"] - 1280) <= 2 and abs(res[(200, 90)]["h"] - 1280) <= 2, [res[(200, 0)]["w"], res[(200, 90)]["h"]])
    page.evaluate("C01.state.zoom = 100; C01.state.rot = 90; C01.app.render()")



def r7w_checks(page, ctx, root, shots):
    """v0.3.23 (R7W): Part A 自動OK · 確認済 줄 修正 (状況 클릭 → 경고 → 修正 폼 · mode edit · 確認済 · 元に戻す · COMPASS 입력済 경고) · Part B 📄 서류 탭 (搬入票 먼저)."""
    jp = root / "_data" / "jikkyou.json"
    jt0 = jp.read_text(encoding="utf-8")
    dump = lambda o: json.dumps(o, ensure_ascii=False, indent=1) + "\n"   # noqa: E731
    j2 = json.loads(jt0)
    iv1 = next(x for x in j2["ivs"] if x["iv_no"] == "TST2611-01")
    r0 = next(r for r in iv1["rows"] if r.get("status") == "自動OK" and r.get("ct") and not r.get("human"))
    docs_dir = [p.relative_to(root).as_posix() for p in sorted((root / "TST2611-01" / "搬入票").glob("*.svg"))]
    r0["docs"] = [{"path": docs_dir[1], "name": "EIR_" + docs_dir[1].split("/")[-1], "page": None, "sha16": "e" * 16, "fields": ["t_w"], "doc_type": "eir"},
                  {"path": docs_dir[0], "name": docs_dir[0].split("/")[-1], "page": None, "sha16": "a" * 16, "fields": ["n_w", "seal"], "doc_type": "hannyuhyo"}]
    iv1["compass_input"] = [{"action_id": "cmp-r7w-0001", "by": "staff1@example.invalid", "at": "2026-11-08T09:00:00+09:00", "value": {"rows": 1}}]
    jp.write_text(dump(j2), encoding="utf-8")
    page.click("#tab-main")
    page.click("[data-port='all']")
    page.evaluate("C01.app.tick()")
    page.wait_for_timeout(500)
    tr = page.locator(f"tbody[data-iv='TST2611-01'] tr.c01-row:has-text('{r0['ct']}')").first
    btn = tr.locator(".c01-okedit")
    ok("A 自動OK 줄 状況 = 누를 수 있음 (修正)", btn.count() == 1 and btn.inner_text() == "自動OK", btn.count())
    btn.click()
    page.wait_for_selector(".c01-modal-okedit")
    mt = page.locator(".c01-modal-okedit").inner_text()
    ok("A 경고 1번 = 「この行は 自動OK です · 確認済（手入力）に変わり、記録されます · 修正しますか？」 + COMPASS 입력済 경고 · [修正する] [やめる]",
       "この行は 自動OK です" in mt and "確認済（手入力）に変わり、記録されます。修正しますか？" in mt and "COMPASS には入力済み — 修正後に Compass入力 をもう一度" in mt
       and page.locator("#okedit-go").inner_text() == "修正する" and "やめる" in mt, mt)
    page.screenshot(path=str(shots / "r7w_okedit_warn.png"))
    page.click("#okedit-go")
    page.wait_for_selector(".c01-side")
    side = page.locator(".c01-side")
    ok("A 修正 폼 = 옆 창 머리 「修正（自動OK）」 · 6 칸 ✎ (CT · seal · 正味 · 風袋 · ベール数 · 作業日) · 원본 · 사진",
       "修正（自動OK）" in side.inner_text() and side.locator(".c01-pf-edit .c01-edit").count() == 6 and side.locator("#panel-doc").count() == 1
       and side.locator("#panel-photo").count() == 1 and "COMPASS には入力済み" in side.inner_text(), side.locator(".c01-pf-edit .c01-edit").count())
    ids0 = {x["action_id"] for x in actions(root)}
    side.locator("[data-ef='seal'] .c01-edit").click()
    page.wait_for_selector("#edit-in")
    page.fill("#edit-in", "ZZ 9999")
    page.click("#edit-save")
    page.wait_for_timeout(500)
    new = [x for x in actions(root) if x["action_id"] not in ids0]
    ok("A 저장 = manual_input · mode edit · source 手入力 · 원래 값은 엔진이 기록 (resolved.replace)", len(new) == 1 and new[0]["action"] == "manual_input"
       and new[0].get("mode") == "edit" and new[0]["field"] == "seal" and new[0]["source"] == "手入力", new)
    st_now = page.locator(f"tbody[data-iv='TST2611-01'] tr.c01-row:has-text('{r0['ct']}')").first.get_attribute("data-status")
    ok("A 저장 뒤 실황표 상태 = 確認済 (엔진 반영 전에도 바로)", st_now == "確認済", st_now)
    page.screenshot(path=str(shots / "r7w_okedit_saved.png"))
    ub = page.locator(".c01-side [data-vundo='seal']")
    ok("A 修正한 칸 = 「元に戻す」", ub.count() == 1, ub.count())
    page.once("dialog", lambda d: d.accept())
    ub.click()
    page.wait_for_timeout(500)
    un = [x for x in actions(root) if x["action_id"] not in ids0 and x["action"] == "undo"]
    st2 = page.locator(f"tbody[data-iv='TST2611-01'] tr.c01-row:has-text('{r0['ct']}')").first.get_attribute("data-status")
    ok("A 元に戻す = undo (value.action_id = 修正) → 상태 自動OK 로", len(un) == 1 and un[0]["value"]["action_id"] == new[0]["action_id"] and st2 == "自動OK", [un, st2])
    page.evaluate("C01.state.sel = null; C01.state.editRow = null; C01.app.render()")
    # Part B 📄
    db = page.locator(f"tbody[data-iv='TST2611-01'] tr.c01-row:has-text('{r0['ct']}') .c01-docbtn").first
    ok("B 写真 옆 「📄2」 (그 줄 출처 서류 수 · 칸 폭 그대로)", db.count() == 1 and db.inner_text().strip() == "📄2", db.count() and db.inner_text())
    nodoc = page.locator("tbody[data-iv='TST2611-02'] tr.c01-row td:nth-child(14) .t2")
    ok("B 서류 없는 줄 = 「—」", nodoc.count() >= 1 and nodoc.first.inner_text().strip() == "—", nodoc.count())
    with ctx.expect_page(timeout=10000) as pi:
        db.click()
    tab = pi.value
    watch(tab, "DOC")
    tab.wait_for_selector(".c01-dv-tabs", timeout=10000)
    tabs = tab.eval_on_selector_all(".c01-dv-tabs [data-go]", "els => els.map(e => e.textContent)")
    ok("B 새 탭 doc.html?k=해시 · 탭 = 搬入票 먼저 · EIR 다음", re.search(r"/doc\.html\?k=[0-9a-f]{8}$", tab.url) and tabs and tabs[0].startswith("搬入票") and tabs[1].startswith("EIR")
       and r0["ct"] not in tab.url, [tab.url, tabs])
    tab.wait_for_function("() => { const i = document.querySelector('.c01-pv-img'); return i && i.complete && i.naturalWidth > 0; }", timeout=10000)
    ok("B 서류 = 원래 탭에서 받은 Blob (새 탭 로그인 · Graph 0)", tab.evaluate("document.querySelector('.c01-pv-img').src.slice(0,5)") == "blob:"
       and tab.evaluate("typeof window.LEENAI") == "undefined" and r0["ct"] in tab.locator("#pv-head").inner_text(), "")
    tab.keyboard.press("ArrowRight")
    tab.wait_for_timeout(200)
    ok("B → 키 = 다음 서류 (EIR)", "on" in (tab.locator(".c01-dv-tabs [data-go='1']").get_attribute("class") or ""), "")
    tab.screenshot(path=str(shots / "r7w_doc_tab.png"))
    tab.close()

    # Part D 「IVに連結」 (config linkIv · 엔진 s2_human_link_iv 켠 뒤)
    qp = root / "_data" / "queue.json"
    qt0 = qp.read_text(encoding="utf-8")
    qj = json.loads(qt0)
    hq = next(x for x in qj["items"] if x["kind"] == "業者・IV未定")
    hq["packer_guess"] = "PACKER_Z"
    qp.write_text(dump(qj), encoding="utf-8")
    page.evaluate("C01.RULES.linkIv = true; C01.app.tick()")
    page.wait_for_timeout(400)
    page.evaluate("q => { C01.state.view = 'input'; C01.state.qkind = 'all'; C01.state.qsel = q; C01.app.render(); }", hq["queue_id"])
    page.wait_for_selector("#link-iv")
    ok("D 業者・IV未定 = 「IVに連結」 (BKG/IV 입력 · 후보 칩) · 확인 버튼 = 「IV と枠を選んでください」 (꺼짐)",
       page.locator(".c01-linkiv [data-linkiv='TST2611-01']").count() == 1 and page.locator("#q-submit").is_disabled()
       and "IV と枠を選んでください" in page.locator("#q-submit").inner_text(), page.locator("#q-submit").inner_text())
    page.fill("#link-iv", "NOPE-9999")
    page.press("#link-iv", "Enter")
    page.wait_for_timeout(200)
    ok("D 없는 BKG / IV = 고를 수 없음 (안내)", "進行中のブッキングにありません" in page.locator(".c01-linkiv").inner_text() and page.locator("input[name='link-slot']").count() == 0, "")
    page.click(".c01-linkiv [data-linkiv='TST2611-01']")
    page.wait_for_timeout(200)
    opts = page.locator("input[name='link-slot']")
    used = page.locator(".c01-slotopt.used input")
    ok("D 칸 목록 = 그 부킹 칸 전부 (빈 칸 · 使用中 표시)", opts.count() >= 2 and used.count() >= 1, [opts.count(), used.count()])
    used.first.check()
    page.wait_for_timeout(200)
    t = page.locator(".c01-linkiv").inner_text()
    ok("D 업체 다름 · 이미 찬 칸 = 경고 표시 · 확인 버튼 켜짐", "業者（PACKER_Z）" in t and "もう行があります" in t and not page.locator("#q-submit").is_disabled(), t[-200:])
    ids0 = {x["action_id"] for x in actions(root)}
    dl = []

    def acc(d):
        dl.append(d.message)
        d.accept()
    page.on("dialog", acc)
    page.click("#q-submit")
    page.wait_for_timeout(600)
    new = [x for x in actions(root) if x["action_id"] not in ids0]
    ok("D 저장 = link_iv (iv · sha16 · slot_guid · warn · 확인창 2번)", len(new) == 1 and new[0]["action"] == "link_iv" and new[0]["iv"] == "TST2611-01"
       and new[0]["value"]["sha16"] == [hq["files"][0]["sha16"]] and new[0]["value"]["slot_guid"] and sorted(new[0]["value"]["warn"]) == ["packer", "slot_used"]
       and len(dl) == 2 and new[0]["queue_id"] == hq["queue_id"], [new, dl])
    page.evaluate("q => { C01.state.qkind = 'done'; C01.state.qsel = q; C01.app.render(); }", hq["queue_id"])
    page.wait_for_timeout(300)
    ok("D 연결 뒤 = 「IV に連結しました」 · 元に戻す", "IV に連結しました" in page.locator("#c01-main").inner_text() and page.locator("#q-undo").count() == 1, "")
    page.screenshot(path=str(shots / "r7w_link_iv.png"))
    page.click("#q-undo")
    page.wait_for_timeout(400)
    un = [x for x in actions(root) if x["action_id"] not in ids0 and x["action"] == "undo"]
    ok("D 元に戻す = undo (value.action_id = link_iv)", len(un) == 1 and un[0]["value"]["action_id"] == new[0]["action_id"], un)
    page.remove_listener("dialog", acc)
    page.evaluate("C01.RULES.linkIv = false; C01.state.qkind = 'all'")
    qp.write_text(qt0, encoding="utf-8")
    page.click("#tab-main")
    jp.write_text(jt0, encoding="utf-8")
    page.evaluate("C01.app.tick()")
    page.wait_for_timeout(300)


def r7x_checks(page, ctx, root, shots):
    """v0.3.24 (R7X): A 再確認 「このまま確認（OK）」 · 値の確認 카드 · B 이유 문구 (설명 1줄 + ?) · C Plant = 배정 칸 값만 ·
    E 사진 지문 (같으면 GET 0 · 실패 = 전 목록 유지) · H 📄 순서 (검사 서류 맨 끝)."""
    jp, qp = root / "_data" / "jikkyou.json", root / "_data" / "queue.json"
    jt0, qt0 = jp.read_text(encoding="utf-8"), qp.read_text(encoding="utf-8")
    dump = lambda o: json.dumps(o, ensure_ascii=False, indent=1) + "\n"   # noqa: E731
    j2, q2 = json.loads(jt0), json.loads(qt0)
    iv1 = next(x for x in j2["ivs"] if x["iv_no"] == "TST2611-01")
    r1 = iv1["rows"][0]
    r1.update({"status": "再確認", "engine_status": "再確認", "reasons": ["MIN_SOURCES", "WEIGHT_MISMATCH"], "reason_text": ["x", "y"], "human": None})
    vq = {"queue_id": "f" * 15 + "1", "kind": "値の確認", "iv_no": "TST2611-01", "ct": r1["ct"], "field": None, "container_id": r1["container_id"], "values": {},
          "candidates": [], "files": [], "note": "MIN_SOURCES,WEIGHT_MISMATCH", "resolved": None, "superseded": [], "cy_cut": iv1.get("cy_cut"), "issuer": None,
          "field_sources": {"n_w": [{"src": "搬入票", "value": r1["n_w"], "agree": True}], "seal": [{"src": "写真", "value": r1["seal"], "agree": True},
                                                                                             {"src": "搬入票", "value": r1["seal"], "agree": True}]},
          "field_source_text": {}, "final": {"ct": r1["ct"]}, "reason_codes": ["MIN_SOURCES", "WEIGHT_MISMATCH"]}
    q2["items"].append(vq)
    q2["kinds"] = list(q2["kinds"]) + ["値の確認"]
    # C: 2 번째 줄 = 배정 칸에 plant 없음 · 줄 plant 없음 · 다른 칸에는 있음 → 빈칸 (IV 다른 칸 값으로 채우지 않음)
    r2 = iv1["rows"][1]
    r2["plant"] = None
    for s_ in iv1["slots"]:
        if s_["slot_guid"] == r2["slot_guid"]:
            s_["plant"] = None
    # H: 서류 = 검사 (path) · 搬入票 (path) · 計量 (path) → 순서 搬入票 → 計量伝票 → 検査
    docs_dir = [p.relative_to(root).as_posix() for p in sorted((root / "TST2611-01" / "搬入票").glob("*.svg"))]
    r2["docs"] = [{"path": docs_dir[0], "name": "CHECK_" + docs_dir[0].split("/")[-1], "page": None, "sha16": "c" * 16, "fields": ["n_w"], "doc_type": "inspection"},
                  {"path": docs_dir[1], "name": docs_dir[1].split("/")[-1], "page": None, "sha16": "a" * 16, "fields": ["seal"], "doc_type": "hannyuhyo"},
                  {"path": docs_dir[0], "name": "KEIRYO_" + docs_dir[0].split("/")[-1], "page": 2, "sha16": "b" * 16, "fields": ["n_w"], "doc_type": "keiryo"},
                  {"path": None, "name": "nopath.jpg", "page": None, "sha16": "d" * 16, "fields": [], "doc_type": "eir"}]
    for iv in j2["ivs"]:
        iv["photos_sig"] = "sig-" + iv["iv_no"]
    jp.write_text(dump(j2), encoding="utf-8")
    qp.write_text(dump(q2), encoding="utf-8")
    page.click("#tab-main")
    page.click("[data-port='all']")
    page.evaluate("() => { if (document.activeElement) document.activeElement.blur(); Object.assign(C01.state, {qedit: null, picks: {}, panelInput: '', sel: null, qvals: {}, qchoice: {}, editRow: null}); C01.app.tick(); }")
    page.wait_for_timeout(600)
    tr = page.locator(f"tbody[data-iv='TST2611-01'] tr.c01-row[data-key*='{r1['ct']}']").first
    cb = tr.locator(".c01-checkbtn")
    ttl = cb.get_attribute("title") or ""
    ok("B 状況 = 「⚠ 要確認 · 確認1つ」 · hover = 설명 → 할 일 (正味＋風袋が総重量と合いません)", cb.count() == 1 and "確認1つ" in cb.inner_text()
       and "正味＋風袋が総重量と合いません。" in ttl and "→" in ttl, [cb.inner_text() if cb.count() else None, ttl])
    tr2 = page.locator(f"tbody[data-iv='TST2611-01'] tr.c01-row[data-key*='{r2['ct']}']").first
    plant2 = tr2.locator("td").nth(12).inner_text().strip()
    ok("C 배정 칸에 plant 없음 = 빈칸 (IV 다른 칸 「工場A 本社」 로 채우지 않음)", plant2 == "", plant2)
    # H 📄 = 열 수 있는 서류 3 · 순서
    db = tr2.locator(".c01-docbtn")
    ok("H 📄 숫자 = 열 수 있는 서류 수 (path 없는 것 뺌) = 3", db.count() == 1 and db.inner_text().strip() == "📄3", db.inner_text() if db.count() else None)
    with ctx.expect_page(timeout=10000) as pi:
        db.click()
    tab = pi.value
    watch(tab, "DOC7X")
    tab.wait_for_selector(".c01-dv-tabs", timeout=10000)
    tabs = tab.eval_on_selector_all(".c01-dv-tabs [data-go]", "els => els.map(e => e.textContent)")
    ok("H 탭 순서 = 搬入票 → 計量伝票 → 検査 (검사 서류 맨 끝)", len(tabs) == 3 and tabs[0].startswith("搬入票") and tabs[1].startswith("計量") and tabs[2].startswith("検査"), tabs)
    tab.close()
    # A 카드: 値の確認
    page.evaluate("q => { C01.state.view = 'input'; C01.state.qkind = 'all'; C01.state.qsel = q; C01.app.render(); }", vq["queue_id"])
    page.wait_for_selector(".c01-vchk")
    chips = page.eval_on_selector_all(".c01-kinds [data-kind]", "els => els.map(e => e.getAttribute('data-kind'))")
    sub = page.locator("#q-submit")
    ok("A 値の確認 카드 = 종류 칩 · 이유 설명 2줄 (?) · 값 6칸 ✎ · 「確認して次へ」 켜짐",
       "値の確認" in chips and page.locator(".c01-vchk .c01-rdesc").count() == 2 and page.locator(".c01-vchk .c01-rq").count() == 2
       and page.locator(".c01-form .c01-edit").count() == 6 and not sub.is_disabled() and "確認して次へ" in sub.inner_text(), [chips, sub.inner_text()])
    page.locator(".c01-vchk .c01-rq").first.click()
    page.wait_for_timeout(150)
    ok("B 「?」 클릭 = 할 일 1줄 (搬入票を見て値が合っていれば…)", "搬入票を見て値が合っていれば「確認する」。" in page.locator(".c01-vchk .c01-rtodo").first.inner_text(),
       page.locator(".c01-vchk").inner_text()[:200])
    page.screenshot(path=str(shots / "r7x_vchk_card.png"))
    # A 실황표 옆 창 → このまま確認
    page.click("#tab-main")
    page.evaluate("k => { C01.state.sel = k; C01.app.render(); }", tr.get_attribute("data-key"))
    page.wait_for_selector("#panel-keep")
    ok("A 옆 창 = 이유 설명 줄 (?) + 「このまま確認（OK）」", page.locator(".c01-side .c01-rdesc").count() == 2 and page.locator("#panel-keep").inner_text() == "このまま確認（OK）", "")
    page.screenshot(path=str(shots / "r7x_panel_keep.png"))
    ids0 = {x["action_id"] for x in actions(root)}
    page.click("#panel-keep")
    page.wait_for_selector(".c01-modal-keep")
    mt = page.locator(".c01-modal-keep").inner_text()
    ok("A 확인 창 = 「値を変えずに 確認済 にします」 + 지금 값", "値を変えずに" in mt and r1["ct"] in mt, mt[:120])
    page.click("#keep-go")
    page.wait_for_timeout(600)
    new = [x for x in actions(root) if x["action_id"] not in ids0]
    ok("A 저장 = confirm_value 1 (CT 그대로 · queue_id = 値の確認 · source 搬入票/写真/Excel)",
       len(new) == 1 and new[0]["action"] == "confirm_value" and new[0]["field"] == "ct" and new[0]["value"] == r1["ct"] and new[0]["queue_id"] == vq["queue_id"]
       and new[0]["source"] in ("搬入票", "写真", "Excel"), new)
    st = page.locator(f"tbody[data-iv='TST2611-01'] tr.c01-row[data-key*='{r1['ct']}']").first.get_attribute("data-status")
    ok("A 저장 뒤 = 確認済 (엔진 반영 전에도 바로)", st == "確認済", st)
    # A 값의 違い 카드 줄 (TST2611-02) = 옆 창에도 「このまま確認」 (값 있음)
    iv2 = next(x for x in j2["ivs"] if x["iv_no"] == "TST2611-04")
    rr = next(r for r in iv2["rows"] if r["reasons"] == ["RANGE"])
    page.evaluate("k => { C01.state.sel = k; C01.app.render(); }", "TST2611-04|" + (rr["ct"] or rr["container_id"]) + "|" + (rr.get("packer") or iv2.get("packer") or ""))
    page.wait_for_selector(".c01-side")
    ok("A 항목을 이미 사람이 확인한 줄 (確認済 표시) = 「このまま確認」 없음", page.locator("#panel-keep").count() == 0, [rr["reasons"], page.locator(".c01-side").inner_text()[:120]])
    page.evaluate("C01.state.sel = null; C01.app.render()")
    # E 사진 지문
    g0 = page.evaluate("C01.photoStat().get")
    page.evaluate("C01.app.tick()")
    page.wait_for_timeout(500)
    g1 = page.evaluate("C01.photoStat().get")
    ok("E 30초 갱신 · 지문 같음 = 사진 목록 GET 0", g1 == g0, [g0, g1])
    j3 = json.loads(jp.read_text(encoding="utf-8"))
    next(x for x in j3["ivs"] if x["iv_no"] == "TST2611-03")["photos_sig"] = "sig-changed"
    jp.write_text(dump(j3), encoding="utf-8")
    page.evaluate("C01.app.tick()")
    page.wait_for_timeout(500)
    g2 = page.evaluate("C01.photoStat().get")
    ok("E 지문 바뀐 IV 1개 = 그 IV 만 다시 읽음 (GET +1)", g2 == g1 + 1, [g1, g2])
    n_before = page.evaluate("(C01.state.photos['TST2611-01'].containers || []).length")
    page.evaluate("""() => { const s = C01.state.src; s._gj = s.getJson; s.getJson = function (rel) {
        return /^photos\\//.test(rel) ? Promise.reject(Object.assign(new Error('http429'), {status: 429})) : s._gj.call(s, rel); }; }""")
    next(x for x in j3["ivs"] if x["iv_no"] == "TST2611-01")["photos_sig"] = "sig-changed2"
    jp.write_text(dump(j3), encoding="utf-8")
    page.evaluate("C01.app.tick()")
    page.wait_for_timeout(500)
    st_ = page.evaluate("C01.photoStat()")
    n_after = page.evaluate("(C01.state.photos['TST2611-01'].containers || []).length")
    ok("E 사진 목록 읽기 실패 (429) = 전 목록 유지 (0枚 아님) · 실패 코드 기록", n_before > 0 and n_after == n_before and st_["fail"] >= 1 and "429" in st_["codes"], [n_before, n_after, st_])
    page.evaluate("() => { const s = C01.state.src; s.getJson = s._gj; delete s._gj; }")
    # G-3: ⟳ 로 돌린 각도 기억 (파일 sha16 + 쪽) — 다른 카드에 갔다 와도 그 각도
    qd = next(x for x in q2["items"] if x["kind"] == "値の違い" and any(f.get("sha16") for f in x.get("files") or []))
    fs_d = {f.get("sha16") for f in qd.get("files") or []}
    qo = next(x for x in q2["items"] if x.get("container_id") != qd.get("container_id") and x.get("files") and not ({f.get("sha16") for f in x["files"]} & fs_d))
    page.evaluate("q => { localStorage.removeItem('c01_rotmem'); C01.state.view = 'input'; C01.state.qkind = 'all'; C01.state.qsel = q; C01.app.render(); }", qd["queue_id"])
    page.wait_for_selector("#rot")
    page.click("#rot")
    page.wait_for_timeout(200)
    mem = page.evaluate("JSON.parse(localStorage.getItem('c01_rotmem') || '{}')")
    page.evaluate("q => { C01.state.qsel = q; C01.state.rot = 0; C01.state.rotKey = null; C01.app.render(); }", qo["queue_id"])
    page.wait_for_timeout(200)
    page.evaluate("q => { C01.state.qsel = q; C01.state.rot = 0; C01.state.rotKey = null; C01.app.render(); }", qd["queue_id"])
    page.wait_for_timeout(200)
    ok("G-3 ⟳ 각도 기억 (sha16#쪽 → 90) · 다른 카드 갔다 와도 90", list(mem.values()) == [90] and page.evaluate("C01.state.rot") == 90, [mem, page.evaluate("C01.state.rot")])
    page.evaluate("localStorage.removeItem('c01_rotmem'); C01.state.rot = 0; C01.state.rotKey = null")
    page.evaluate("C01.app.tick()")
    page.wait_for_timeout(400)
    jp.write_text(jt0, encoding="utf-8")
    qp.write_text(qt0, encoding="utf-8")
    page.evaluate("C01.state.view = 'main'; C01.app.tick()")
    page.wait_for_timeout(400)


def compass_r7x_checks(page):
    """v0.3.24 (R7X Part D): CT 빈 칸 예정값 = PLAN (警告 없음 · PATCH 에 들어감) · 形態 = NOINPUT · opts 없으면 옛 결과 (DIFF + EXISTING_DIFF)."""
    r = page.evaluate("""() => {
      const row = {container_id: 'c1', ct: 'TSTU0000001', seal: 'S1', n_w: 21000, t_w: 3800, bales: 20, status: '自動OK', packer: 'P', plant: '', item: '', ct_id: 'g1'};
      const cell = {'@odata.etag': 'W/1', crcf9_container_no: null, crcf9_seal_no: null, crcf9_n_w: 23000, crcf9_g_w: 23000, crcf9_t_w: null, crcf9_quantity: null, crcf9_type: '42GP'};
      const a = C01.compass.compareIv('X', [row], {g1: cell}, {}, {plan_fill: true, type_input: false});
      const b = C01.compass.compareIv('X', [row], {g1: cell}, {}, null);
      const st = (res, f) => res.rows[0].cells.filter(c => c.field === f)[0].state;
      return {a_nw: st(a, 'n_w'), a_gw: st(a, 'g_w'), a_type: st(a, 'type'), a_warn: a.rows[0].warnings, a_patch: Object.keys(a.patches[0].body).sort(),
              b_nw: st(b, 'n_w'), b_warn: b.rows[0].warnings, a_cnt: a.count.cells};
    }""")
    ok("D CT 빈 칸 예정값 (N/W 23,000) = PLAN 「予定値 → 入力」 · 경고 없음 · 形態 = 入力しない (PATCH 에 없음)",
       r["a_nw"] == "PLAN" and r["a_gw"] == "PLAN" and r["a_type"] == "NOINPUT" and r["a_warn"] == [] and "crcf9_type" not in r["a_patch"] and "crcf9_n_w" in r["a_patch"], r)
    ok("D opts 없음 = 엔진 규칙 그대로 (DIFF · EXISTING_DIFF · TYPE_42_22)", r["b_nw"] == "DIFF" and "EXISTING_DIFF" in r["b_warn"] and "TYPE_42_22" in r["b_warn"], r)


def r7v_side_checks(br, url, shots):
    """v0.3.21 (R7V F-1): 실황표 옆 창 머리 (CT) 가 상단 공통 바에 가리지 않음 · 패널 안 스크롤에도 머리 고정.
    넓이 1366 · 1600 · 1920 × 확대 100 % / 125 % (확대 = CSS 넓이 ÷ 1.25 + deviceScaleFactor 1.25 — 브라우저 확대와 같은 배치)."""
    res = []
    for w in (1366, 1600, 1920):
        for z in (1.0, 1.25):
            c = br.new_context(viewport={"width": int(w / z), "height": int(900 / z)}, device_scale_factor=z)
            pg = c.new_page()
            watch(pg, f"F1-{w}-{int(z*100)}")
            open_local(pg, url)
            pg.wait_for_selector("tr.c01-row[data-status]")
            pg.evaluate("k => { C01.state.sel = k; C01.app.render(); }", pg.locator("tr.c01-row[data-status]").first.get_attribute("data-key"))
            pg.wait_for_selector(".c01-side .c01-side-h .big")
            pg.wait_for_timeout(150)
            m = pg.evaluate("""() => { const h = document.querySelector('.ln-header').getBoundingClientRect(), s = document.querySelector('.c01-side'),
                b = document.querySelector('.c01-side-h .big').getBoundingClientRect(), sr = s.getBoundingClientRect();
                const hit = document.elementFromPoint(b.left + 4, b.top + b.height / 2);
                return {hb: h.bottom, st: sr.top, sb: sr.bottom, vh: innerHeight, ct: b.top, hit: !!(hit && hit.closest('.c01-side-h'))}; }""")
            pg.evaluate("document.querySelector('.c01-side').scrollTop = 10000")
            pg.wait_for_timeout(100)
            m2 = pg.evaluate("""() => { const b = document.querySelector('.c01-side-h .big').getBoundingClientRect();
                const hit = document.elementFromPoint(b.left + 4, b.top + b.height / 2); return !!(hit && hit.closest('.c01-side-h')); }""")
            good = m["st"] >= m["hb"] - 1 and m["ct"] >= m["hb"] and m["hit"] and m2 and abs(m["sb"] - m["vh"]) <= 1
            res.append((w, z, good, m, m2))
            pg.screenshot(path=str(shots / f"r7v_side_{w}_{int(z*100)}.png"))
            c.close()
    ok("F-1 옆 창 CT 줄 = 상단 바 밑 · 맨 위에서 보임 · 패널 안 스크롤에도 고정 · 패널 아래 = 화면 아래 (1366/1600/1920 × 100/125 %)",
       all(x[2] for x in res), [x for x in res if not x[2]] or len(res))


def r7v_checks(page, root, shots):
    """v0.3.22 (R7V): Part 0-2 #194 CY CUT ≥ 오늘 IV 만 (실황표 · 確認・入力 · 건수) · F-2 作業日要確認 = 회색 「?」 · WORK_DATE 줄 옆 창 = 作業日 ✎ 修正."""
    jp = root / "_data" / "jikkyou.json"
    jt0 = jp.read_text(encoding="utf-8")
    dump = lambda o: json.dumps(o, ensure_ascii=False, indent=1) + "\n"   # noqa: E731
    page.click("#tab-main")
    page.click("[data-port='all']")
    ivs_of = lambda: sorted(page.eval_on_selector_all("tbody[data-iv]", "els => els.map(e => e.getAttribute('data-iv'))"))   # noqa: E731
    before = ivs_of()
    j2 = json.loads(jt0)
    today = j2.get("today") or "2026-11-08"
    past = next(x for x in j2["ivs"] if x["iv_no"] == "TST2611-02")
    past["cy_cut"] = "2026-01-02"                     # 지난 IV
    nocut = next(x for x in j2["ivs"] if x["iv_no"] == "TST2611-05")
    nocut["cy_cut"] = None                            # CY CUT 없음 = 표시
    iv1 = next(x for x in j2["ivs"] if x["iv_no"] == "TST2611-01")
    r0 = next(r for r in iv1["rows"] if r.get("work_date") and not (r.get("human") or {}).get("work_date"))
    r0["info"] = (r0.get("info") or []) + ["作業日要確認(too_old)"]
    jp.write_text(dump(j2), encoding="utf-8")
    page.evaluate("C01.app.tick()")
    page.wait_for_timeout(500)
    after = ivs_of()
    ok("0-2 #194 CY CUT 지난 IV 숨김 · CY CUT 없는 IV 표시 · 나머지 그대로", "TST2611-02" in before and "TST2611-02" not in after and "TST2611-05" in after
       and sorted(set(before) - {"TST2611-02"}) == after, [before, after, today])
    page.click("#tab-input")
    page.wait_for_timeout(300)
    txt = page.locator("body").inner_text()
    ok("0-2 確認・入力 에도 지난 IV 항목 없음", "TST2611-02" not in txt, "")
    page.click("#tab-main")
    page.wait_for_timeout(200)
    wd = page.locator("tbody[data-iv='TST2611-01'] .c01-wddoubt")
    ok("F-2 作業日要確認 줄 = 작업일 칸 회색 「?」 (title 설명)", wd.count() == 1 and wd.inner_text().endswith("?") and "読み違い" in (wd.get_attribute("title") or ""),
       [wd.count(), wd.count() and wd.inner_text()])
    # WORK_DATE 줄 → 옆 창 作業日 ✎ 修正
    j3 = json.loads(jp.read_text(encoding="utf-8"))
    iv3 = next(x for x in j3["ivs"] if x["iv_no"] == "TST2611-01")
    r3 = next(r for r in iv3["rows"] if r.get("ct") and r.get("work_date"))
    r3["status"] = "再確認"
    r3["reasons"] = ["WORK_DATE"]
    r3["info"] = ["WORK_DATE(too_old)"]
    jp.write_text(dump(j3), encoding="utf-8")
    page.evaluate("C01.app.tick()")
    page.wait_for_timeout(400)
    key = page.locator(f"tbody[data-iv='TST2611-01'] tr.c01-row:has-text('{r3['ct']}')").first.get_attribute("data-key")
    page.evaluate("k => { C01.state.sel = k; C01.app.render(); }", key)
    page.wait_for_selector(".c01-side")
    ed = page.locator(".c01-side [data-ef='work_date'] .c01-edit")
    ok("F-2 WORK_DATE 줄 옆 창 = 作業日 ✎ 修正 + 안내", ed.count() == 1 and "作業日を原本で確認" in page.locator(".c01-side").inner_text(), ed.count())
    page.screenshot(path=str(shots / "r7v_wd_panel.png"))
    page.evaluate("C01.state.sel = null; C01.app.render()")
    jp.write_text(jt0, encoding="utf-8")
    page.evaluate("C01.app.tick()")
    page.wait_for_timeout(300)


def r7v_remind_checks(page, root, shots):
    """v0.3.22 (R7V Part B · #191 · #135): 催促 送信 = 시험 모드만 — 두 겹 잠금 (config remindTest · 엔진 send_mode.test) · 받는 곳 = 시험 주소 1개 ·
    제목 [test] · CC 0 · reminder_sent 기록 · 같은 업체·회차 다시 못 보냄 · 실제 받는 곳 (d.to · d.cc) 으로 가는 호출 0."""
    rp = root / "_data" / "remind.json"
    rt0 = rp.read_text(encoding="utf-8")
    TEST_TO = "test.box@example.invalid"
    r2 = json.loads(rt0)
    r2["send_mode"] = {"test": True, "to": TEST_TO, "tag": "[test]"}
    for ds in r2["ivs"].values():
        for d in ds:
            d["body_html"] = "<p>" + d["body_text"].replace(chr(10), "<br>") + "</p>"
    rp.write_text(json.dumps(r2, ensure_ascii=False, indent=1) + chr(10), encoding="utf-8")
    page.click("#tab-main")
    page.click("[data-port='all']")
    page.evaluate("""() => { C01.app.tick(); }""")
    page.wait_for_timeout(500)
    page.evaluate("""() => { window.__sent = []; C01.state.info.mode = 'graph';
        C01.state.src.sendMailTest = function (m) { window.__sent.push(m); return C01.sources.Graph.prototype.sendMailTest.call({ _fetch: function (u, o) {
            window.__sent.push({ url: u, body: JSON.parse(o.body) }); return Promise.resolve({ status: 202, ok: true }); } }, m); }; }""")
    page.click("tbody[data-iv='TST2611-02'] [data-remind]")
    page.wait_for_selector("[data-rsend]")
    bt = page.locator("[data-rsend]").first
    ok("B 催促 창 = 試験モード 표시 · 送信（試験） 버튼", page.locator("#remind-testmode").count() == 1 and bt.is_enabled() and "試験" in bt.inner_text(), bt.inner_text())
    page.locator("[data-rskip='0']").check()
    ok("B 「この業者には送らない」 = 버튼 꺼짐", page.locator("[data-rsend='0']").is_disabled())
    page.locator("[data-rskip='0']").uncheck()
    page.locator("[data-rsend='0']").click()
    for _ in range(30):
        if any(x["action"] == "reminder_sent" for x in actions(root)):
            break
        time.sleep(0.1)
    sent = page.evaluate("window.__sent")
    post = [x for x in sent if isinstance(x, dict) and x.get("url")]
    msg = post[0]["body"]["message"] if post else {}
    rec = [x for x in actions(root) if x["action"] == "reminder_sent"]
    ok("B 송신 = /me/sendMail 1번 · 받는 곳 = 시험 주소 1개 · CC 0 · 제목 [test] · 본문 앞 「実際の宛先」",
       len(post) == 1 and post[0]["url"].endswith("/me/sendMail") and [r["emailAddress"]["address"] for r in msg.get("toRecipients", [])] == [TEST_TO]
       and not msg.get("ccRecipients") and not msg.get("bccRecipients") and msg.get("subject", "").startswith("[test] ")
       and "実際の宛先" in msg.get("body", {}).get("content", ""), [len(post), msg.get("subject")])
    allr = json.dumps(sent, ensure_ascii=False)
    ok("B 실제 받는 곳 (초안 to · cc) 주소가 보낸 내용에 0", not any(a in allr for d in r2["ivs"]["TST2611-02"] for a in (d.get("to") or []) + (d.get("cc") or [])), "")
    ok("B reminder_sent 기록 (업체 · 회차 · test true · to = 시험 주소)", len(rec) == 1 and rec[0]["value"]["test"] is True and rec[0]["value"]["to"] == [TEST_TO]
       and rec[0]["iv"] == "TST2611-02", rec)
    page.wait_for_selector("[data-rsend][data-done]", timeout=5000)
    ok("B 보낸 뒤 = 「送信済」 · 같은 업체·회차 다시 못 보냄", page.locator("[data-rsend='0']").is_disabled() and "送信済" in page.locator(".c01-rsendrow").first.inner_text())
    page.screenshot(path=str(shots / "r7v_remind_test.png"))
    page.click("[data-close]")
    bad = page.evaluate("""() => C01.sources.Graph.prototype.sendMailTest.call({ _fetch: function () { return Promise.resolve({ status: 202, ok: true }); } },
        { subject: '[test] x', html: '', to: 'other@example.invalid' }).then(() => 'sent', e => 'blocked')""")
    bad2 = page.evaluate("""() => C01.sources.Graph.prototype.sendMailTest.call({ _fetch: function () { return Promise.resolve({ status: 202, ok: true }); } },
        { subject: 'no tag', html: '', to: '%s' }).then(() => 'sent', e => 'blocked')""" % TEST_TO)
    ok("B source 두 번째 잠금: 시험 주소 아님 / [test] 없음 = 보내지 않음", bad == "blocked" and bad2 == "blocked", [bad, bad2])
    r3 = json.loads(rp.read_text(encoding="utf-8"))
    r3["send_mode"]["test"] = False
    rp.write_text(json.dumps(r3, ensure_ascii=False, indent=1) + chr(10), encoding="utf-8")
    page.evaluate("C01.app.tick()")
    page.wait_for_timeout(500)
    page.click("tbody[data-iv='TST2611-02'] [data-remind]")
    page.wait_for_selector(".c01-rmd")
    ok("B 엔진 send_mode.test false = 送信 버튼 0 (실제 송신 코드 없음)", page.locator("[data-rsend]").count() == 0 and page.locator("#remind-send").is_disabled())
    page.click("[data-close]")
    rp.write_text(rt0, encoding="utf-8")
    page.evaluate("C01.state.info.mode = 'local'; C01.app.tick()")
    page.wait_for_timeout(300)


def r7u_checks(page, root, shots):
    """v0.3.20 (R7U): F-1 管理者 = 全港 (#201) · A-3 CT重複 / シール重複 · 再判読 표시 · A-4 手入力 CT 경고."""
    jp = root / "_data" / "jikkyou.json"
    jt0 = jp.read_text(encoding="utf-8")
    jj = json.loads(jt0)
    dump = lambda o: json.dumps(o, ensure_ascii=False, indent=1) + "\n"   # noqa: E731
    page.click("#tab-main")
    ivs_of = lambda: sorted(page.eval_on_selector_all("tbody[data-iv]", "els => els.map(e => e.getAttribute('data-iv'))"))   # noqa: E731
    page.select_option("#me-select", "STAFF_D")
    page.wait_for_timeout(200)
    page.click("[data-port='mine']")
    lab = page.locator("[data-port='mine']").inner_text()
    ok("F-1 #201 관리자 (portal_admin) = 自分の担当 대신 全港 (5 IV) · 「全港 · 管理者」", ivs_of() == ["TST2611-01", "TST2611-02", "TST2611-03", "TST2611-04", "TST2611-05"]
       and "全港 · 管理者" in lab, [ivs_of(), lab])
    page.select_option("#me-select", "STAFF_A")
    page.wait_for_timeout(200)
    page.click("[data-port='mine']")
    ok("F-1 직원 = 지금대로 (STAFF_A = TOKYO · YOKOHAMA)", ivs_of() == ["TST2611-01", "TST2611-02", "TST2611-03"], ivs_of())
    page.click("[data-port='all']")
    # A-3 CT重複 · シール重複 (같은 IV 두 줄에 같은 CT / 같은 seal)
    j2 = json.loads(jt0)
    iv = next(x for x in j2["ivs"] if x["iv_no"] == "TST2611-04")
    a, b2, c = iv["rows"][0], iv["rows"][1], iv["rows"][2]
    b2["ct"] = a["ct"]
    c["seal"] = a["seal"] = a.get("seal") or "TS00009999"
    c["info"] = (c.get("info") or []) + ["REREAD_MERGE(写真のみ行)"]
    jp.write_text(dump(j2), encoding="utf-8")
    page.evaluate("C01.app.tick()")
    page.wait_for_timeout(400)
    tb = "tbody[data-iv='TST2611-04']"
    nct = page.locator(tb + " .c01-over:has-text('CT重複')").count()
    nsl = page.locator(tb + " .c01-over:has-text('シール重複')").count()
    t1 = page.locator(tb + " .c01-over:has-text('CT重複')").first.get_attribute("title") or ""
    ok("A-3 같은 IV 같은 CT 2줄 = 두 줄 모두 빨간 「CT重複」 (몇 행째 안내) · 같은 seal = 「シール重複」", nct == 2 and nsl == 2 and "行目" in t1, [nct, nsl, t1])
    rr = page.locator(tb + " [data-info='reread']")
    ok("再判読 결과 배지 (엔진 info REREAD_MERGE → 일본어 설명)", rr.count() == 1 and "1 行に合わせました" in (rr.get_attribute("title") or ""), rr.count())
    w = page.evaluate("getComputedStyle(document.querySelector('#jikkyou-table col.w-st')).width")
    page.screenshot(path=str(shots / "r7u_dup.png"))
    # A-4 手入力 CT 경고: 다른 줄 CT 를 넣으면 저장 전 확인창 · 취소 = 기록 0
    jp.write_text(jt0, encoding="utf-8")
    page.evaluate("C01.app.tick()")
    page.wait_for_timeout(300)
    j3 = json.loads(jt0)
    iv3 = next(x for x in j3["ivs"] if x["iv_no"] == "TST2611-04")
    other_ct = iv3["rows"][0]["ct"]
    msgs = []
    page.once("dialog", lambda d: (msgs.append(d.message), d.dismiss()))
    res = page.evaluate("(a) => C01.app.ctDupWarn(a[0], a[1], a[2])", ["TST2611-04", other_ct, iv3["rows"][1]["container_id"]])
    ok("A-4 다른 줄에 있는 CT = 「このCTは n行目にあります」 확인창 · 취소 = 저장 안 함", res is False and msgs and "行目にあります" in msgs[0], msgs)
    res2 = page.evaluate("(a) => C01.app.ctDupWarn(a[0], a[1], a[2])", ["TST2611-04", "TSTU0000000", iv3["rows"][1]["container_id"]])
    ok("A-4 없는 CT = 확인창 없음", res2 is True)
    ok("칸 폭 그대로 (#193 · 상태 칸 col 폭 변화 없음)", bool(w), w)
    # Part D 他社搬入票候補 카드 — 「他社の書類」 = not_hannyuhyo · 「当社の書類」 = ours_doc (1 書類 = 1 枚)
    qp = root / "_data" / "queue.json"
    qt0 = qp.read_text(encoding="utf-8")
    qj = json.loads(qt0)
    used = {h for a_ in actions(root) if a_["action"] in ("not_hannyuhyo", "not_ours") for h in ((a_.get("value") or {}).get("sha16") or [])}
    src = next(x for x in qj["items"] if x["iv_no"] == "TST2611-04" and x["files"] and x["files"][0].get("sha16") and x["files"][0]["sha16"] not in used)
    fx = [dict(src["files"][0])]
    it1 = {**src, "queue_id": "f0e1a0000000000a", "kind": "他社搬入票候補", "field": None, "values": {}, "candidates": [], "files": fx,
           "note": "hannyuhyo:荷主・船社", "resolved": None, "superseded": []}
    src2 = next(x for x in qj["items"] if x["files"] and x["files"][0].get("sha16") and x["files"][0]["sha16"] not in used | {fx[0]["sha16"]})
    it2 = {**it1, "queue_id": "f0e1a0000000000b", "files": [dict(src2["files"][0])], "iv_no": src2["iv_no"]}
    q2 = json.loads(qt0)
    q2["items"] += [it1, it2]
    qp.write_text(dump(q2), encoding="utf-8")
    page.evaluate("C01.app.tick()")
    page.evaluate("C01.state.view = 'input'; C01.state.qkind = 'all'; C01.state.qsel = 'f0e1a0000000000a'; C01.app.render()")
    page.wait_for_selector("#q-ours", timeout=5000)
    body = page.locator(".c01-hold").first.inner_text()
    lab = page.locator("#q-submit").inner_text()
    ok("D 他社搬入票候補 카드 = 근거 1줄 (BKG · 荷主 · 船社) · 「他社の書類」 · 「当社の書類」 · 搬入票ではない 버튼 없음",
       "当社のどのブッキングにもない" in body and "荷主がリニアではない" in body and "船社" in body and lab == "他社の書類"
       and page.locator("#q-notours").count() == 0, [body, lab])
    page.screenshot(path=str(shots / "r7u_foreign.png"))
    n0 = len(actions(root))
    page.click("#q-submit")
    page.wait_for_timeout(500)
    a1 = [x for x in actions(root) if x.get("queue_id") == "f0e1a0000000000a"]
    ok("D 「他社の書類」 → not_hannyuhyo (그 파일 sha16)", len(a1) == 1 and a1[0]["action"] == "not_hannyuhyo" and a1[0]["value"]["sha16"] == [fx[0]["sha16"]], a1)
    page.evaluate("C01.state.qsel = 'f0e1a0000000000b'; C01.app.render()")
    page.wait_for_selector("#q-ours", timeout=5000)
    page.click("#q-ours")
    page.wait_for_timeout(500)
    a2 = [x for x in actions(root) if x.get("queue_id") == "f0e1a0000000000b"]
    ok("D 「当社の書類」 → ours_doc (학습 기록)", len(a2) == 1 and a2[0]["action"] == "ours_doc" and len(actions(root)) == n0 + 2, a2)
    qp.write_text(qt0, encoding="utf-8")
    page.evaluate("C01.state.view = 'main'; C01.app.render()")

def r7s_checks(page, root, shots):
    """v0.3.18 (R7S): #4 シール 후보 형식 · #5 同一コンテナ候補 원본 + 사진 · #13 옆 창 행 서류."""
    jp, qp = root / "_data" / "jikkyou.json", root / "_data" / "queue.json"
    jt0, qt0 = jp.read_text(encoding="utf-8"), qp.read_text(encoding="utf-8")
    jj, qj = json.loads(jt0), json.loads(qt0)
    dump = lambda o: json.dumps(o, ensure_ascii=False, indent=1) + "\n"   # noqa: E731
    page.click("#tab-main")
    page.click("[data-port='all']")
    iv4 = next(iv for iv in jj["ivs"] if iv["iv_no"] == "TST2611-04")
    r42 = iv4["rows"][2]                           # 自動OK 줄 (다른 항목 없음) 에 シール 値の違い 1 개를 붙임
    docrel = next(x for x in qj["items"] if x["iv_no"] == "TST2611-04" and x["files"])["files"][0]
    base = {"queue_id": "5ea1f0000000000a", "kind": "値の違い", "iv_no": "TST2611-04", "ct": r42["ct"], "field": "seal", "container_id": r42["container_id"],
            "values": {"写真": ["XS00001234", "TS0001234"], "搬入票": ["TS00001234"]}, "candidates": [], "files": [docrel], "note": "seal", "resolved": None, "superseded": [],
            "cy_cut": iv4["cy_cut"], "cy_open": None, "issuer": None, "field_sources": {}, "field_source_text": {}}

    def show(item):
        q2 = json.loads(qt0)
        q2["items"].append(item)
        qp.write_text(dump(q2), encoding="utf-8")
        page.evaluate("C01.app.tick()")
        page.evaluate(f"C01.state.qvals = {{}}; C01.state.view = 'input'; C01.state.qkind = 'all'; C01.state.qsel = '{item['queue_id']}'; C01.app.render()")
        page.wait_for_selector(f".c01-field[data-vq='{item['queue_id']}']", timeout=5000)
        fld = page.locator(f".c01-field[data-vq='{item['queue_id']}']")
        alts = fld.locator(".c01-alt2")
        return {"vals": [alts.nth(i).locator(".mono").inner_text() for i in range(alts.count())],
                "ng": [("c01-fmtng" in (alts.nth(i).get_attribute("class") or "")) for i in range(alts.count())],
                "tag": [alts.nth(i).locator(".c01-fmttag").count() for i in range(alts.count())],
                "input": fld.locator("input").input_value(), "pick": fld.locator("[data-fmtpick]").count(), "busy": page.evaluate("C01.app.busy()"),
                "submit": page.locator("#q-submit").is_enabled()}

    g = show(dict(base, seal_format={"prefixes": ["TS"], "digits": 8, "prefix_required": True}))
    ok("#4 seal_format = 형식에 맞는 후보 먼저 · 안 맞는 후보 회색 「形式不一致」 · 맞는 후보 1개 = 처음부터 선택 (입력 칸 · 안내) · 자동 갱신 막지 않음",
       g["vals"] == ["TS00001234", "XS00001234", "TS0001234"] and g["ng"] == [False, True, True] and g["tag"] == [0, 1, 1] and g["input"] == "TS00001234"
       and g["pick"] == 1 and g["busy"] is False and g["submit"], g)
    page.screenshot(path=str(shots / "r7s_seal_fmt.png"))
    cols = []
    for th in ("dark", "light", "leenai", "focus"):
        page.evaluate(f"document.documentElement.setAttribute('data-theme','{th}')")
        cols.append(page.evaluate("""() => { const n = document.querySelector('.c01-alt2.c01-fmtng'), o = document.querySelector('.c01-alt2:not(.c01-fmtng)'), t = n.querySelector('.c01-fmttag');
            const c = e => getComputedStyle(e); return [c(n).color, c(o).color, c(t).color, c(n).backgroundColor, c(n).opacity]; }"""))
    page.evaluate("document.documentElement.setAttribute('data-theme','dark')")
    ok("#4 4테마 「形式不一致」 = 보통 후보와 다른 색 (회색 · 흐림) · 글자색 ≠ 배경", all(c[0] != c[1] and c[2] != c[3] and float(c[4]) < 1 for c in cols), cols)
    g = show(dict(base, queue_id="5ea1f0000000000b", seal_fmt_ok={"TS00001234": True, "TS0001234": True, "XS00001234": False}))
    ok("#4 seal_fmt_ok (엔진 판정 맵) · 맞는 후보 2개 = 미리 선택 안 함 · 안 맞는 것만 「形式不一致」", g["vals"] == ["TS0001234", "TS00001234", "XS00001234"]
       and g["ng"] == [False, False, True] and g["input"] == "" and g["pick"] == 0, g)
    g = show(dict(base, queue_id="5ea1f0000000000c"))
    ok("#4 형식 정보 없음 = 지금까지 그대로 (순서 · 회색 0 · 선택 0)", g["vals"] == ["XS00001234", "TS0001234", "TS00001234"] and not any(g["ng"]) and g["input"] == "" and g["pick"] == 0, g)
    g = show(dict(base, queue_id="5ea1f0000000000d", seal_format={"regex": "TS[0-9]{8}$"}))
    ok("#4 seal_format.regex 도 (엔진 seal_ok 와 같은 규칙)", g["ng"] == [False, True, True] and g["input"] == "TS00001234", g)
    qp.write_text(qt0, encoding="utf-8")
    # ── #5 同一コンテナ候補: FAX 줄의 서류 (엔진 rows[].docs · 다음 판) = 원본 (그 쪽) + 오른쪽에 사진 줄의 扉 · シール 사진 · 없으면 「原本ファイルがありません」 아님
    iv3 = next(iv for iv in jj["ivs"] if iv["iv_no"] == "TST2611-03")
    fx = next(r for r in iv3["rows"] if (r.get("same_cand") or {}).get("role") == "fax")
    pid = fx["same_cand"]["pair_id"]
    page.evaluate("C01.app.tick()")
    page.evaluate(f"C01.state.view = 'input'; C01.state.qkind = 'all'; C01.state.qsel = '{pid}'; C01.app.render()")
    page.wait_for_selector(".c01-same", timeout=5000)
    to = page.locator(".c01-orig").inner_text()
    ok("#5 同一候補 · FAX 줄 서류 정보 없음 = 「FAX の行の原本がまだ分かりません」 (「原本ファイルがありません」 아님) · 사진 줄 사진은 보임",
       "原本ファイルがありません" not in to and page.locator("#q-samenodoc").count() == 1 and page.locator("#q-samephs .c01-sameph").count() >= 1, to[:200])
    ph3 = json.loads((root / "_data" / "photos" / "TST2611-03.json").read_text(encoding="utf-8"))
    drel = ph3["docs"][0]["path"]
    fx["docs"] = [{"path": drel, "name": drel.split("/")[-1], "page": None, "sha16": "f" * 16}]
    jp.write_text(dump(jj), encoding="utf-8")
    page.evaluate("C01.app.tick()")
    page.evaluate(f"C01.state.qsel = '{pid}'; C01.app.render()")
    page.wait_for_selector(".c01-orig img.c01-docimg", timeout=5000)
    kinds = page.locator("#q-samephs .c01-sameph span").all_inner_texts()
    lay = page.evaluate("""() => { const d = document.querySelector('.c01-orig .c01-doc').getBoundingClientRect(), p = document.querySelector('#q-samephs').getBoundingClientRect();
        return [p.left >= d.right - 1, Math.abs(p.top - d.top) < 40]; }""")
    ok("#5 同一候補 · rows[].docs = FAX 원본 (왼쪽) + 사진 줄의 扉 · シール 사진 (오른쪽 · 나란히)", page.locator("#q-samenodoc").count() == 0
       and drel.split("/")[-1] in page.locator(".c01-orig-h").inner_text() and "扉" in kinds and "シール" in kinds and all(lay), [kinds, lay])
    page.screenshot(path=str(shots / "r7s_same_side.png"))
    with page.context.expect_page(timeout=10000) as pi:
        page.locator("#q-samephs .c01-sameph").first.click()
    t = pi.value
    t.wait_for_selector(".c01-pv-th", timeout=10000)
    ok("#5 사진 클릭 = 사진 줄의 사진 탭 (그 사진부터)", fx["same_cand"]["partner"] and t.locator("#pv-head").inner_text().find(next(r["ct"] for r in iv3["rows"] if r["container_id"] == fx["same_cand"]["partner"])) >= 0,
       t.locator("#pv-head").inner_text())
    t.close()
    # ── #13 옆 창: 確認・入力 항목 없는 줄도 rows[].docs 가 있으면 「原本」 (썸네일 · 별 탭)
    page.click("#tab-main")
    page.evaluate("k => { C01.state.sel = k; C01.app.render(); }", f"TST2611-03|{fx['ct']}|{fx['packer']}")
    page.wait_for_selector(".c01-side", timeout=5000)
    pd = page.locator("#panel-doc")
    ok("#13 옆 창 = 행 서류 (rows[].docs) 썸네일 · 「原本なし」 아님", pd.is_enabled() and "原本なし" not in pd.inner_text() and drel.split("/")[-1] in pd.inner_text(), pd.inner_text())
    page.evaluate("C01.state.sel = null; C01.app.render()")
    jp.write_text(jt0, encoding="utf-8")
    page.evaluate("C01.app.tick()")


def r7n_checks(page, root, shots, engine):
    """v0.3.15 (R7N): F 자동 갱신 · G-1 搬入票 없는 줄 手入力 · G-2 서류 후보 · G-3 회전 · G-4 修正."""
    jp, qp = root / "_data" / "jikkyou.json", root / "_data" / "queue.json"
    jt0, qt0 = jp.read_text(encoding="utf-8"), qp.read_text(encoding="utf-8")
    jj, qj = json.loads(jt0), json.loads(qt0)
    dump = lambda o: json.dumps(o, ensure_ascii=False, indent=1) + "\n"   # noqa: E731
    page.click("#tab-main")
    page.click("[data-port='all']")
    page.wait_for_timeout(200)
    st = lambda k: page.evaluate(f"C01.state.{k}")   # noqa: E731
    # ── G-1: 受信中 · has_docs false 줄의 手入力 = 카드 없음 (実況表 「搬入票待ち」) · 同一候補 줄 = 同一コンテナ候補 카드로
    nod = [x for x in qj["items"] if x["kind"] == "手入力" and not x["files"] and x["iv_no"] == "TST2611-03"]
    cts = [x["ct"] for x in nod]
    ok("G-1 시험 데이터: TST2611-03 受信中 · has_docs false 줄 手入力 2 (파일 없음 · 1줄 同一候補)", len(nod) == 2, cts)
    wait = [page.locator("tr.c01-row", has_text=c).locator(".st-wait").inner_text() for c in cts]
    ok("G-1 実況表 = 「搬入票待ち」 그대로", all("搬入票待ち" in w for w in wait), wait)
    page.click("#tab-input")
    page.click(".c01-kinds [data-kind='all']")
    texts = page.locator(".c01-item").all_inner_texts()
    ok("G-1 確認・入力 = 그 두 줄의 手入力 카드 없음 (「原本を見て入力」 요구 0)", not any(c in t and "手入力" in t for c in cts for t in texts)
       and page.locator(f"[data-q='{nod[0]['queue_id']}'], [data-q='{nod[1]['queue_id']}']").count() == 0, texts)
    ok("G-1 同一候補 줄 = 「同一コンテナ候補」 카드는 그대로", any("同一コンテナ候補" in t for t in texts), texts)
    ok("G-1 배지 숫자 = 카드 수 (숨긴 手入力 안 셈)", page.locator("#badge-open").inner_text() == str(page.locator(".c01-item").count()),
       [page.locator("#badge-open").inner_text(), page.locator(".c01-item").count()])
    # ── G-2-0: 원본 지정 없는 手入力 (줄과 연결된 서류 없음) = 「搬入票なし（待ち）」 · IV 서류 전체 표시 없음
    iv2 = next(iv for iv in jj["ivs"] if iv["iv_no"] == "TST2611-02")
    r3 = iv2["rows"][3]
    q3 = next(x for x in qj["items"] if x["kind"] == "手入力" and x["container_id"] == r3["container_id"])

    def sel(qid, kind="all"):
        page.evaluate(f"C01.state.qkind = '{kind}'; C01.state.qsel = '{qid}'; C01.app.render()")
        page.wait_for_timeout(400)

    sel(q3["queue_id"])
    to = page.locator(".c01-orig").inner_text()
    ok("G-2-0 연결된 서류 없음 = 「搬入票なし（待ち）」 · IV 서류 표시 0 · 칩 0", "搬入票なし（待ち）" in to and "IV の書類" not in to
       and page.locator(".c01-orig img, .c01-orig [data-pdf]").count() == 0 and page.locator(".c01-qfiles [data-qf]").count() == 0, to[:200])
    page.screenshot(path=str(shots / "r7n_g20_nodoc.png"))
    # ── G-2 후보: 엔진 rows[].doc_sha16 (다음 판) 이 있으면 어느 줄에도 안 쓰인 IV 서류만 「候補」 (1~2) · 自動OK·確認済 줄 서류는 뺌
    ph2 = json.loads((root / "_data" / "photos" / "TST2611-02.json").read_text(encoding="utf-8"))
    for k, r in enumerate(iv2["rows"][:3]):
        r["doc_sha16"] = [ph2["docs"][k]["sha16"]]
    r3["doc_sha16"] = []
    jp.write_text(dump(jj), encoding="utf-8")
    page.evaluate("C01.app.tick()")
    sel(q3["queue_id"])
    chips = page.locator(".c01-qfiles [data-qf]")
    ok("G-2 후보 = 어느 줄에도 안 쓰인 서류 1개만 「候補」 (다른 줄 서류 3개 뺌) · 이유 표시",
       chips.count() == 1 and chips.first.get_attribute("data-cand") == "1" and "候補" in chips.first.inner_text() and ph2["docs"][3]["path"].split("/")[-1] in chips.first.inner_text()
       and "どの行にも使われていない" in page.locator("#q-candnote").inner_text(), [chips.count(), page.locator(".c01-orig").inner_text()[:200]])
    page.screenshot(path=str(shots / "r7n_g2_cand.png"))
    for r in iv2["rows"]:
        r["doc_sha16"] = [d["sha16"] for d in ph2["docs"]]          # 전부 쓰임 → 후보 0 → 搬入票なし
    jp.write_text(dump(jj), encoding="utf-8")
    page.evaluate("C01.app.tick()")
    sel(q3["queue_id"])
    ok("G-2 남는 서류 없음 = 후보 0 · 「搬入票なし（待ち）」", page.locator(".c01-qfiles [data-qf]").count() == 0 and "搬入票なし（待ち）" in page.locator(".c01-orig").inner_text())
    # 같은 컨테이너 다른 항목의 서류 = 보임 · 그중 自動OK 줄 (다른 컨테이너) 에 쓰인 서류 = 뺌
    r0 = iv2["rows"][0]
    d0 = {"path": ph2["docs"][0]["path"], "name": ph2["docs"][0]["path"].split("/")[-1], "page": 1, "bbox": None, "sha16": "a0" * 8}
    d3 = {"path": ph2["docs"][3]["path"], "name": ph2["docs"][3]["path"].split("/")[-1], "page": 1, "bbox": None, "sha16": "a3" * 8}
    jp.write_text(jt0, encoding="utf-8")
    qj2 = json.loads(qt0)
    qj2["items"].append(dict(q3, queue_id="b1" * 8, field="t_w", files=[d0, d3]))
    qj2["items"].append(dict(q3, queue_id="b2" * 8, kind="値の違い", field="seal", container_id=r0["container_id"], ct=r0["ct"], files=[d0],
                             resolved={"action": "confirm_value", "action_id": "fx-r7n-0001", "by": "staff.b@example.invalid", "at": "2026-11-08T09:00:00+09:00"}))
    qp.write_text(dump(qj2), encoding="utf-8")
    page.evaluate("C01.app.tick()")
    sel(q3["queue_id"])
    oh = page.locator(".c01-orig-h").inner_text()
    ok("G-2 같은 컨테이너 항목 서류만 · 自動OK 줄 (다른 컨테이너) 에 쓰인 서류는 뺌 (2 → 1)", page.locator(".c01-qfiles [data-qf]").count() == 0 and d3["name"] in oh and d0["name"] not in oh, oh)
    qp.write_text(qt0, encoding="utf-8")
    page.evaluate("C01.app.tick()")
    # ── G-3: 엔진 rotation (files[].rotation 180) = 처음부터 바로 · ⟳ 는 그 위에 더함
    fq = next(x for x in qj["items"] if x["kind"] == "未分類FAX")
    sel(fq["queue_id"], "done")
    if page.locator(".c01-orig .c01-doc").count() == 0:
        sel(fq["queue_id"], "all")
    # v0.3.18 (R7S #3): 화상 회전 = 안쪽 .c01-docrot (左上 축 + translate) · 상자 data-rot
    tf = page.get_attribute(".c01-orig .c01-docrot", "style") or ""
    ok("G-3 뒤집힌 FAX (rotation 180) = 처음부터 180° · 「向き補正 180°」", "rotate(180deg)" in tf and page.get_attribute(".c01-orig .c01-doc", "data-rot") == "180"
       and page.locator("#q-autorot").inner_text() == "向き補正 180°", tf)
    page.screenshot(path=str(shots / "r7n_g3_rot.png"))
    page.click("#rot")
    page.wait_for_timeout(200)
    tf2 = page.get_attribute(".c01-orig .c01-docrot", "style") or ""
    ok("G-3 ⟳ = 엔진 각도 위에 90° 더함 (270°)", "rotate(270deg)" in tf2 and page.get_attribute(".c01-orig .c01-doc", "data-rot") == "270", tf2)
    rot_checks(page, shots)
    rots = page.evaluate("""() => [180, -90, 450, 45, '90'].map(v => C01.app._rot({rotation: v, page: null}))""")
    rmap = page.evaluate("""() => [C01.app._rot({rotation: {'4': 180, '2': 90}, page: 1}), C01.app._rot({rotation: 270, page: 3})]""")
    ok("G-3 rotation 형식 (수 · {쪽: 각도} · 90 배수만 · 음수/360 넘음 정리)", rots == [{"*": 180}, {"*": 270}, {"*": 90}, {}, {"*": 90}] and rmap == [{"4": 180, "2": 90}, {"3": 270}], [rots, rmap])
    page.evaluate("C01.state.rot = 0; C01.app.render()")
    # ── G-4: 모든 값 칸 「✎ 修正」 → manual_input (source 手入力 · 사람 값 우선) · 이미 사람 값 = 못 누름 (이유)
    sel(q3["queue_id"])
    ro = page.locator(".c01-form .c01-field.ro[data-ef]")
    eds = page.locator(".c01-form .c01-field.ro[data-ef] .c01-edit")
    ok("G-4 값 칸마다 「✎ 修正」 (CT · シール · 風袋 · ベール · 作業日 = 입력 중 아닌 칸 전부)", ro.count() == 5 and eds.count() == 5, [ro.count(), eds.count()])
    ids0 = {x["action_id"] for x in actions(root)}
    page.click(".c01-form .c01-field[data-ef='t_w'] .c01-edit")
    page.wait_for_selector("#edit-in")
    page.fill("#edit-in", "3,700")
    page.click("#edit-save")
    page.wait_for_timeout(500)
    new = [x for x in actions(root) if x["action_id"] not in ids0]
    ok("G-4 修正 → _actions manual_input (t_w 3700 · source 手入力 · queue_id 16자 · queue 에 없는 id → 엔진은 IV+CT 로 찾음)",
       len(new) == 1 and new[0]["action"] == "manual_input" and new[0]["field"] == "t_w" and new[0]["value"] == 3700 and new[0]["source"] == "手入力"
       and re.fullmatch(r"[0-9a-f]{16}", new[0]["queue_id"] or "") is not None and new[0]["queue_id"] not in {x["queue_id"] for x in qj["items"]} and new[0]["ct"] == r3["ct"], new)
    fv = page.locator(".c01-form .c01-field[data-ef='t_w']")
    # v0.3.23 (R7W Part A): valueEdit = 사람 값이 있어도 다시 ✎ 修正 (mode edit) + 「元に戻す」 (옛 규칙 = 잠김)
    ok("G-4 修正 뒤 = 새 값 · 「✓ 修正」 · 그 칸 ✎ 다시 가능 + 元に戻す (R7W valueEdit) · action mode edit", "3,700" in fv.inner_text() and "修正" in fv.locator(".c01-hm2").inner_text()
       and not fv.locator(".c01-edit").is_disabled() and fv.locator("[data-vundo='t_w']").count() == 1 and new and new[0].get("mode") == "edit", fv.inner_text())
    sys.path.insert(0, engine)
    from engine.output import schema_check  # noqa: E402
    errs = schema_check.errors(new[0], schema_check.load("action")) if new else ["없음"]
    ok("G-4 修正 action = 엔진 action.schema.json (오류 0)", not errs, errs)
    page.click("#tab-main")
    trw = page.locator(f"tr.c01-row[data-key*='{r3['ct']}']")
    ok("G-4 実況表 줄도 사람 값 (3,700 ✓)", "3,700" in trw.inner_text() and trw.locator(".c01-hm").count() >= 1, trw.inner_text())
    pk = page.locator("tbody[data-iv='TST2611-04'] tr.c01-row").first.get_attribute("data-key")
    page.evaluate("k => { C01.state.sel = k; C01.app.render(); }", pk)       # 要確認 옆 창 (앞의 시험에서 再確認 줄은 모두 끝남)
    page.wait_for_selector(".c01-side")
    ok("G-4 要確認 옆 창 값 칸 ✎ 修正", page.locator(".c01-side .c01-edit").count() >= 3, page.locator(".c01-side .c01-edit").count())
    page.evaluate("C01.state.sel = null; C01.app.render()")
    # ── F: 자동 갱신 — 바뀐 것 없으면 다시 그리지 않음 · 스크롤 그대로 · 바뀐 줄만 · 입력 중이면 미룸
    page.set_viewport_size({"width": 1440, "height": 520})
    page.evaluate("C01.app.render()")
    page.evaluate("C01.app.tick()")
    wrap = "#jikkyou-wrap"
    page.evaluate(f"document.querySelector('{wrap}').scrollTop = 260")
    page.wait_for_timeout(100)
    sc0 = page.evaluate(f"document.querySelector('{wrap}').scrollTop")
    page.evaluate("document.querySelectorAll('tr.c01-row, tr.c01-row td').forEach(t => t._m = 1)")
    n0 = st("renders")
    page.evaluate("C01.app.tick()")
    page.wait_for_timeout(200)
    same = page.evaluate("[...document.querySelectorAll('tr.c01-row, tr.c01-row td')].every(t => t._m === 1)")
    ok("F 바뀐 것 없음 = 다시 그리지 않음 (render 0 · 줄 DOM 그대로 · 스크롤 그대로 · 「最終更新」 시각만)",
       sc0 >= 200 and st("renders") == n0 and same and page.evaluate(f"document.querySelector('{wrap}').scrollTop") == sc0 and page.locator("#c01-upd").count() == 1,
       [sc0, n0, st("renders"), same])
    jj3 = json.loads(jt0)
    iv4 = next(iv for iv in jj3["ivs"] if iv["iv_no"] == "TST2611-04")
    rr = next(r for r in iv4["rows"] if r["status"] == "自動OK")
    rr["n_w"] = (rr["n_w"] or 0) + 11
    jp.write_text(dump(jj3), encoding="utf-8")
    page.evaluate("C01.app.tick()")
    page.wait_for_timeout(200)
    um = page.evaluate("[...new Set([...document.querySelectorAll('tr.c01-row td')].filter(t => t._m !== 1).map(t => t.parentNode.dataset.key))]")
    sc1 = page.evaluate(f"document.querySelector('{wrap}').scrollTop")
    ok("F 다른 사람 변경 (1줄 값) = 그 줄의 칸만 바뀜 (다른 줄 DOM 그대로) · 스크롤 그대로", st("renders") == n0 + 1 and len(um) == 1 and rr["ct"] in um[0] and sc1 == sc0
       and f"{rr['n_w']:,}" in page.locator(f"tr.c01-row[data-key*='{rr['ct']}']").inner_text(), [st("renders"), n0, um, sc1, sc0])
    page.screenshot(path=str(shots / "r7n_f_scroll.png"))
    # 입력 중 = 미룸 (값 · 커서 그대로) → 입력 칸을 비우고 나가면 그때 갱신
    page.set_viewport_size({"width": 1440, "height": 1000})
    page.click("#tab-input")
    sel(q3["queue_id"])
    inp = page.locator(".c01-field[data-vq] input").first
    inp.click()
    inp.type("21500")
    page.evaluate("document.querySelectorAll('.c01-item').forEach(t => t._m = 1)")
    n1 = st("renders")
    rr["n_w"] += 11
    jp.write_text(dump(jj3), encoding="utf-8")
    page.evaluate("C01.app.tick()")
    page.wait_for_timeout(200)
    foc = page.evaluate("document.activeElement && document.activeElement.value")
    ok("F 입력 중 (커서 · 쓰던 값) = 갱신 미룸 (render 0 · 값 그대로 · 커서 그대로)", st("renders") == n1 and foc == "21500" and st("dirty") is True
       and page.evaluate("[...document.querySelectorAll('.c01-item')].every(t => t._m === 1)"), [n1, st("renders"), foc, st("dirty")])
    page.click(".c01-form-h")
    page.wait_for_timeout(200)
    ok("F 입력 칸에서 나가도 쓰던 값이 있으면 미룸 (저장 안 한 값 보호)", st("renders") == n1 and inp.input_value() == "21500", [n1, st("renders")])
    inp.fill("")
    page.click(".c01-form-h")
    page.wait_for_timeout(300)
    ok("F 쓰던 값을 지우고 나가면 그때 갱신 · 열린 카드 그대로", st("renders") == n1 + 1 and st("dirty") is False and st("qsel") == q3["queue_id"], [n1, st("renders"), st("qsel")])
    jp.write_text(jt0, encoding="utf-8")
    page.evaluate("C01.app.tick()")
    page.click("#tab-main")


def r7z_checks(page, root, shots):
    """v0.3.25 (R7Z Part A · #207 · #209 · #210 · #211): 確認・入力 「その他（AIに相談）」 — 닫힌 채 · 빠른 질문 → ask 파일 (카드 · 열린 원본) ·
    답 표시 · 목록 밖 동작 = 버튼 없음 · 이 화면에 없는 버튼 = 꺼짐 · 값 버튼 = 칸만 채움 (확인은 담당자) · 한국어 질문 lang ko."""
    qp = root / "_data" / "queue.json"
    q2 = json.loads(qp.read_text(encoding="utf-8"))
    jk = json.loads((root / "_data" / "jikkyou.json").read_text(encoding="utf-8"))
    iv2 = next(x for x in jk["ivs"] if x["iv_no"] == "TST2611-02")
    r = iv2["rows"][0]
    qid = "z" * 15 + "7"
    q2["items"].append({"queue_id": qid, "kind": "値の違い", "iv_no": iv2["iv_no"], "ct": r["ct"], "field": "seal", "container_id": r["container_id"],
                        "values": {"写真": ["TS112233"], "搬入票": ["TS112283"]}, "candidates": [], "files": [], "note": "SOURCE_MISMATCH", "resolved": None,
                        "superseded": [], "cy_cut": iv2.get("cy_cut"), "issuer": None})
    qp.write_text(json.dumps(q2, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    page.click("#tab-input")
    page.evaluate("() => C01.app.tick()")
    page.wait_for_timeout(800)
    page.click("[data-kind='all']")
    page.wait_for_timeout(300)
    page.locator(f"[data-q='{qid}']").first.click()
    page.wait_for_timeout(400)
    box = page.locator("#ask-box")
    ok("R7Z 「その他（AIに相談）」 欄 있음 · 처음엔 닫힘 · 試験表示", box.count() == 1 and not box.evaluate("e => e.open") and "試験表示" in box.locator("summary").inner_text())
    box.locator("summary").click()
    page.locator("[data-askq='0']").click()
    page.wait_for_timeout(500)
    files = sorted((root / "_actions" / "ask").rglob("*.json"))
    a = json.loads(files[-1].read_text(encoding="utf-8")) if files else {}
    card = a.get("card") or {}
    ok("R7Z 빠른 질문 → _actions/ask/{날짜}/{ask_id}.json (질문 · 담당자 · 카드 IV·CT·key · 열린 원본)", len(files) == 1 and a.get("question") == "どの値が正しい？"
       and a.get("by") and card.get("iv") and card.get("key") and "open" in card and files[-1].parent.name == str(a.get("at"))[:10], a)
    ok("R7Z 보낸 뒤 「回答待ち…」", page.locator(".c01-ask-a.wait").count() == 1)
    vq = qid
    q = page.evaluate("id => (C01.state.queue.items || []).filter(x => x.queue_id === id)[0]", vq)
    alts = [v for vs in (q.get("values") or {}).values() for v in vs]
    target = "TS112233"
    rep = {"ask_id": a["ask_id"], "status": "ok", "answer": "写真で読める値が正しいと思われます。", "kind": "value", "approval_request": "",
           "suggestions": [{"action": "pick_value", "field": q["field"], "value": target, "iv": "", "label": "この値を選ぶ"},
                           {"action": "delete_file", "field": "", "value": "", "iv": "", "label": "削除"},
                           {"action": "not_same", "field": "", "value": "", "iv": "", "label": "別のコンテナ"}]}
    (root / "_actions" / "ask_reply").mkdir(parents=True, exist_ok=True)
    (root / "_actions" / "ask_reply" / f"{a['ask_id']}.json").write_text(json.dumps(rep, ensure_ascii=False), encoding="utf-8")
    page.evaluate("() => C01.app.tick()")
    page.wait_for_timeout(800)
    sug = page.locator("[data-asksug]")
    ok("R7Z 답 표시 · 목록 밖 동작 (delete_file) = 버튼 없음 · 버튼 2", "写真で読める値" in page.locator(".c01-ask-log").inner_text() and sug.count() == 2
       and "削除" not in page.locator(".c01-ask-sug").inner_text(), sug.count())
    ok("R7Z 이 화면에 없는 버튼 (別のコンテナ) = 꺼짐", sug.nth(1).is_disabled())
    sug.nth(0).click()
    page.wait_for_timeout(300)
    ok("R7Z 값 버튼 = 값 칸만 채움 (確認은 담당자 · _actions 새 파일 0)", page.locator(f".c01-field[data-vq='{qid}'] input").first.input_value() == target
       and not [x for x in actions(root) if x.get("queue_id") == vq], target)
    page.screenshot(path=str(shots / "r7z_ask.png"), full_page=False)
    page.locator("#ask-box summary").click() if not page.locator("#ask-box").evaluate("e => e.open") else None
    page.fill("#ask-in", "이 값이 맞나요?")
    page.press("#ask-in", "Enter")
    page.wait_for_timeout(500)
    files = sorted((root / "_actions" / "ask").rglob("*.json"), key=lambda x: x.stat().st_mtime)
    k = json.loads(files[-1].read_text(encoding="utf-8")) if files else {}
    ok("R7Z 한국어 질문 · Enter = 보냄 · lang ko · 같은 카드 key", len(files) == 2 and k.get("lang") == "ko" and (k.get("card") or {}).get("key") == card.get("key"), k.get("lang"))
    ok("R7Z 같은 카드 대화 2건 표시", page.locator(".c01-ask-q").count() == 2)


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
            if r["ct"] == "TSTU0010630":          # v0.3.10 R7I Part D: 受信中・候補あり (엔진 jikkyou 줄 cand 형식 그대로)
                r["cand"] = {"level": "ct", "n": 1, "where": ["保留:NO_BKG"], "recv": ["2026-11-06"]}
            if r["ct"] == "TSTU0010218":
                HUMAN_SEAL = r["human"]["seal"]["value"]
                r["seal"] = HUMAN_SEAL
                r["info"] = ["human_vs_engine_diff(seal)"]
    jp.write_text(json.dumps(jj, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    # v0.3.10 (R7I · #143): meta.photo_range — PACKER_A 만 범위 (9〜12) · 그 밖 업체 = 지금 기준 (≤5 · ≥15)
    mp = root / "_data" / "meta.json"
    mm = json.loads(mp.read_text(encoding="utf-8"))
    mm["photo_range"] = {"computed_on": "2026-11-08", "rule": "test", "default": {"le": 5, "ge": 15}, "packers": {"PACKER_A": {"n": 20, "lo": 9, "hi": 12}}}
    mp.write_text(json.dumps(mm, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
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
            ok("탭 제목 = LEENAI C-01 搬入票 v0.3.24", page.title() == "LEENAI C-01 搬入票 v0.3.24", page.title())
            ok("로그인 버튼 활성 (R7A graph)", page.locator("#ln-login-btn").is_enabled())
            page.click("#c01-open-server")
            page.wait_for_selector("body[data-c01-ready='1']", timeout=20000)
            ok("헤더 C-01 · 버전 1곳", page.locator(".ln-header .ln-sys").inner_text() == "C-01" and "v0.3.24" in page.locator(".ln-hdr-ver").inner_text())
            # v0.3.10 #143: 장수 색 = 업체별 범위 (PACKER_A 8장 = 범위 밖 · 9장 = 안) · 범위 없는 업체 = ≤5·≥15
            page.wait_for_timeout(300)
            pa = page.evaluate("""() => [...document.querySelectorAll('tr.c01-row')].map(t => [t.innerText.includes('PACKER_A'),
                (t.querySelector('.c01-phbtn')||{}).innerText||'', !!t.querySelector('td.c01-ph-alert'), (t.querySelector('td.c01-ph-alert')||{}).title||''])""")
            a8 = [x for x in pa if x[0] and "8枚" in x[1]]
            a9 = [x for x in pa if x[0] and "9枚" in x[1]]
            oth = [x for x in pa if not x[0] and x[1] and int(x[1].split()[-1].rstrip("枚")) > 5]
            ok("#143 장수 색 = 업체 범위 (PACKER_A 8장 색 · 9장 색 없음 · 다른 업체 6~9장 색 없음)",
               bool(a8) and all(x[2] and "通常 9〜12枚の外" in x[3] for x in a8) and bool(a9) and not any(x[2] for x in a9) and bool(oth) and not any(x[2] for x in oth),
               (len(a8), len(a9), len(oth), pa[:3]))
            cw = page.locator("tr.c01-row", has_text="TSTU0010630").locator(".st-wait")
            cw0 = page.locator("tr.c01-row", has_text="TSTU0010706").locator(".st-wait")
            ok("Part D 受信中・候補あり (cand 줄만 · title = 保留 위치 · 다른 受信中 줄 그대로)",
               cw.count() == 1 and cw.inner_text().startswith("受信中・候補あり") and "保留:NO_BKG" in (cw.get_attribute("title") or "")
               and "催促の対象外" in (cw.get_attribute("title") or "") and cw0.count() == 1 and "候補あり" not in cw0.inner_text(),
               (cw.count() and cw.inner_text(), cw0.count() and cw0.inner_text()))
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
            # v0.3.10 (R7E Part C · D-42): No = 부킹마다 1 부터 · 줄 순서 = COMPASS 칸 seq · 칸 없는 줄 = 맨 아래 「未割当」 · 台数 = 칸 수 (이중 셈 0)
            nos = page.evaluate("""() => [...document.querySelectorAll('tbody[data-iv]')].map(tb => [tb.dataset.iv,
                [...tb.querySelectorAll('tr.c01-row td.c-no')].map(td => +td.textContent)])""")
            ok("D-42 No = 부킹마다 1, 2, 3 …", all(v == list(range(1, len(v) + 1)) for _, v in nos) and len(nos) == 5, nos)
            iv4 = next(iv for iv in jj["ivs"] if iv["iv_no"] == "TST2611-04")
            sq4 = {sl["slot_guid"]: sl["seq"] for sl in iv4["slots"]}
            want4 = [r["ct"] for r in sorted([r for r in iv4["rows"] if r.get("slot_guid")], key=lambda r: sq4[r["slot_guid"]])] +                     [r["ct"] for r in iv4["rows"] if not r.get("slot_guid")]
            got4 = page.evaluate("""() => [...document.querySelectorAll("tbody[data-iv='TST2611-04'] tr.c01-row")].map(tr => tr.children[4].textContent.trim())""")
            ok("C 줄 순서 = COMPASS 칸 seq (TST2611-04 칸 역순) · 未割当 맨 아래", got4 == want4 and want4 != [r["ct"] for r in iv4["rows"]], [got4, want4])
            un4 = page.evaluate("""() => [...document.querySelectorAll("tbody[data-iv='TST2611-04'] tr.c01-row")].map(tr => tr.classList.contains('unassigned') && !!tr.querySelector('.c01-unassigned'))""")
            ok("C 칸 없는 줄 = 「未割当」 표시 (TST2611-04 2줄 · 맨 아래)", un4 == [False, False, True, True], un4)
            tot = page.evaluate("""() => Object.fromEntries([...document.querySelectorAll('tbody[data-iv]')].map(tb => [tb.dataset.iv,
                (tb.querySelector('.c01-ivhead').textContent.match(/([0-9]+)[/]([0-9]+)台/) || [])[2]]))""")
            want_tot = {iv["iv_no"]: str(len(iv["slots"])) for iv in jj["ivs"]}
            ok("v0.3.15 H-4 台数 N = COMPASS 칸 수 그대로 (#166 · 줄이 칸보다 많아도 늘리지 않음)", tot == want_tot, [tot, want_tot])
            h4_checks(page, jj)
            ms = page.evaluate("""() => [...document.querySelectorAll("tbody[data-iv='TST2611-03'] tr.c01-row")].map(tr => tr.classList.contains('missing') ? 'm' : (tr.classList.contains('unassigned') ? 'u' : 's'))""")
            ok("C メール未着 칸 줄 = 칸 자리 · 未割当 줄은 그 아래 (v0.3.12: 搬入票待ち 1 줄 칸 있음 · FAX 줄 未割当)", ms == ["m", "s", "u", "u"], ms)
            page.uncheck("#show-unarrived")
            ok("メール未着も表示 끄기 → 줄 없음", page.locator("tr.missing").count() == 0)
            page.check("#show-unarrived")
            page.screenshot(path=str(shots / "jikkyou_dark_all.png"), full_page=True)
            help_checks(page, shots)
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
            # v0.3.24 (R7X Part D · #214): 形態 = 入力しない (NOINPUT · TYPE_42_22 경고 없음) · CT 빈 칸 예정값 = PLAN
            ok("경고 표시 (EXISTING_DIFF · CT_DUP) · 形態 경고 없음", {"EXISTING_DIFF", "CT_DUP"} <= warns and "TYPE_42_22" not in warns, sorted(warns))
            ok("v0.3.24 形態 = 入力しない (NOINPUT · PATCH 에 crcf9_type 없음)", "NOINPUT" in states and
               "crcf9_type" not in page.evaluate("JSON.stringify(C01.state.modal.res.patches)"), sorted(states))
            sb = page.locator("#compass-send")
            ok("送信 비활성 「DRY — 送信しません」", sb.is_disabled() and "DRY" in sb.inner_text(), sb.inner_text())
            tb = page.locator(".c01-mh [data-trial]")
            ok("v0.3.17 Compass入力 창 「試験表示（並行期間中は送信・入力しません）」", tb.count() == 1 and tb.inner_text() == "試験表示（並行期間中は送信・入力しません）")
            got = page.evaluate("JSON.stringify(C01.state.modal.res)")
            iv1 = next(x for x in jik["ivs"] if x["iv_no"] == "TST2611-01")
            snap = json.loads((root / "_data" / "compass_now" / "TST2611-01.json").read_text(encoding="utf-8"))
            rows_in = [{"container_id": r["container_id"], "ct": r["ct"], "seal": ((r.get("human") or {}).get("seal") or {}).get("value", r["seal"]), "n_w": r["n_w"],
                        "t_w": r["t_w"], "bales": r["bales"], "status": r["status"], "packer": r["packer"], "plant": r["plant"], "item": r["item"],
                        "ct_id": r["slot_guid"]} for r in iv1["rows"]]
            exp = compare_iv("TST2611-01", rows_in, snap["cells"], {k: set(v) for k, v in snap["dups"].items()})
            canon = lambda x: json.dumps(json.loads(json.dumps(x, default=sorted)), sort_keys=True, ensure_ascii=False)  # noqa: E731
            # v0.3.24: 화면 = opts (plan_fill · type_input false) → Python 비교는 opts 없는 같은 함수 (규칙 자체 = 엔진과 같음)
            got0 = page.evaluate("(a) => JSON.stringify(C01.compass.compareIv('TST2611-01', a.rows, a.cells, a.dups, {follow_same_cond_slot: false}))",
                                 {"rows": rows_in, "cells": snap["cells"], "dups": snap["dups"]})
            ok("화면 비교 함수 (opts 없음) = 엔진 Python 비교표 (같은 입력)", canon(json.loads(got0)) == canon(exp))
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
            ok("催促 送信 비활성 (엔진 send_mode 없음 = 「送信できません」 · 送信 버튼 0)", rs.is_disabled() and "送信できません" in rs.inner_text()
               and page.locator("[data-rsend]").count() == 0, rs.inner_text())
            tb = page.locator(".c01-mh [data-trial]")
            ok("v0.3.17 催促 창 「試験表示（並行期間中は送信・入力しません）」", tb.count() == 1 and tb.inner_text() == "試験表示（並行期間中は送信・入力しません）")
            ok("v0.3.11 催促 미리보기 「候補書類あり — 催促前に確認」 (엔진 remind.json cand)",
               page.locator(".c01-rcand").count() == 1 and "催促前に確認" in page.locator(".c01-rcand").inner_text())
            page.screenshot(path=str(shots / "remind_preview.png"))
            page.click("[data-close]")
            page.click("tbody[data-iv='TST2611-03'] [data-remind]")
            page.wait_for_selector(".c01-rmd")
            ok("주소 없는 업체 = 「送信先未登録」", "送信先未登録" in page.locator(".c01-rmeta").first.inner_text())
            ok("v0.3.12 催促 下書き 「候補あり — 確認してから送信」 (BKG 후보 줄도 대상 · D-55 (나))",
               page.locator(".c01-rcand-bkg").count() == 1 and "確認してから送信" in page.locator(".c01-rcand-bkg").inner_text())
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
            # v0.3.8 (R7D Part U-2): 担当港 복수 선택 · 기억
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
            # v0.3.13 (R7L Part E · D-65): 사진 = 같은 창의 새 탭 (photo.html) · 같은 컨테이너 = 그 탭 · Shift+클릭 = 라이트박스
            photo_tab_checks(page, ctx, shots)
            # 사진 보기 (Shift+클릭 = 라이트박스)
            page.locator("tbody[data-iv='TST2611-01'] .c01-phbtn").first.click(modifiers=["Shift"])
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
            ok("確認・入力 종류 칩 = すべて · 4종 · 業者・IV 未定 · 同一コンテナ候補 (v0.3.12) · 完了", [k.split(" ")[0] for k in kinds_txt] == ["すべて", "値の違い", "手入力", "写真の", "未分類", "業者・IV", "同一コンテナ候補", "完了"], kinds_txt)
            page.screenshot(path=str(shots / "input_dark.png"), full_page=True)
            # v0.3.8 (R7D Part U-3): 판단 버튼 = 오른쪽 패널 맨 위 (항목 제목 바로 아래) · 모든 종류 같은 위치
            pos_ok = []
            for kd in ["値の違い", "手入力", "写真のCT", "未分類FAX"]:
                page.click(f".c01-kinds [data-kind='{kd}']")
                if page.locator(".c01-item").count():
                    page.locator(".c01-item").first.click()
                    pos_ok.append((kd, page.evaluate("""() => { const h = document.querySelector('.c01-form .c01-form-h'); const a = h && h.nextElementSibling;
                      return !!(a && a.classList.contains('c01-form-a') && a.querySelector('#q-submit') && a.querySelector('#q-skip')
                        && a.getBoundingClientRect().top < document.querySelector('.c01-form .c01-form-b').getBoundingClientRect().top); }""")))
            ok("U-3 판단 버튼 위치 = 제목 바로 아래 (STAFF_A 담당 港 · 끝난 値の違い 카드는 목록에서 빠짐 (v0.3.11) · 手入力 은 아래 全港 에서)",
               len(pos_ok) >= 2 and all(v for _, v in pos_ok), pos_ok)
            page.click(".c01-kinds [data-kind='未分類FAX']")
            ok("U-3 「搬入票ではない」 도 위 (未分類FAX · 문구 바뀜)", page.locator(".c01-form-a #q-notours").count() == 1
               and page.locator("#q-notours").inner_text() == "搬入票ではない")
            page.click(".c01-kinds [data-kind='all']")
            page.click(".c01-kinds [data-kind='done']")         # v0.3.11: 위에서 확인한 シール 카드 = 完了
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
            ok("v0.3.11 Part A: 같은 컨테이너 手入力 2칸 (ベール数 · CT番号) = 카드 1장 · 입력 2칸", page.locator(".c01-field[data-vq]").count() == 2,
               page.locator(".c01-field[data-vq]").count())
            fill_field(page, "ベール数", "23")
            ok("v0.3.11 Part B: 「搬入票ではない」 = 手入力 카드에도", page.locator("#q-notours").count() == 1 and page.locator("#q-notours").inner_text() == "搬入票ではない")
            page.once("dialog", lambda dg: (dmsg.append(dg.message), dg.dismiss()))
            fill_field(page, "CT番号", "TSTU0000015")
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
            # 手入力 bales (같은 카드 · 같은 「確認して次へ」 로 함께 저장)
            ok("手入力 bales → manual_input 23 (같은 카드 한 번에)", any(x["action"] == "manual_input" and x["field"] == "bales" and x["value"] == 23 for x in actions(root)))
            page.click(".c01-kinds [data-kind='手入力']")
            ok("v0.3.11 Part B: 끝난 카드는 목록에서 빠짐 (手入力 칩)", not any("ベール数" in t for t in page.locator(".c01-item").all_inner_texts()),
               page.locator(".c01-item").all_inner_texts())
            page.click(".c01-kinds [data-kind='done']")
            ok("v0.3.11 Part B: 「完了」 칩 = 끝난 카드가 다시 보임", any("ベール数" in t for t in page.locator(".c01-item.done").all_inner_texts()),
               page.locator(".c01-item").all_inner_texts())
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
            ok("v0.3.11: 다른 사람이 끝낸 카드도 목록에서 빠짐", not any("風袋重量" in t for t in page.locator(".c01-item").all_inner_texts()))
            page.click(".c01-kinds [data-kind='done']")
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
            # v0.3.11 Part B: 「搬入票ではない」 (値の違い 카드) → 목록에서 빠짐 → 完了 → 「元に戻す」 → 다시 나옴
            page.click(".c01-kinds [data-kind='all']")
            n_before = page.locator(".c01-item").count()
            page.click(".c01-kinds [data-kind='業者・IV未定']")
            page.locator(".c01-item").first.click()
            dl2 = []
            page.once("dialog", lambda dg: (dl2.append(dg.message), dg.accept()))
            page.click("#q-notours")
            page.wait_for_timeout(400)
            nh = [x for x in actions(root) if x["action"] == "not_hannyuhyo"]
            ok("「搬入票ではない」 (業者・IV 未定) = 확인창 → not_hannyuhyo 1 (sha16 · queue_id)", len(dl2) == 1 and "搬入票ではない" in dl2[0] and len(nh) == 1
               and nh[0]["value"]["sha16"] and nh[0]["queue_id"], nh)
            page.click(".c01-kinds [data-kind='all']")
            ok("「搬入票ではない」 카드 = 목록에서 빠짐", page.locator(".c01-item").count() == n_before - 1, [n_before, page.locator(".c01-item").count()])
            page.click(".c01-kinds [data-kind='done']")
            items = page.locator(".c01-item.done")
            hit = None
            for i in range(items.count()):
                if "搬入票ではない" in items.nth(i).inner_text():
                    hit = i
            ok("完了 칩 = 「搬入票ではない」 카드 표시", hit is not None, items.all_inner_texts())
            if hit is not None:
                items.nth(hit).click()
                page.click("#q-undo")
                page.wait_for_timeout(400)
                ud = [x for x in actions(root) if x["action"] == "undo"]
                ok("「元に戻す」 → undo 1 (value.action_id = not_hannyuhyo · queue_id null)", len(ud) == 1 and ud[0]["value"]["action_id"] == nh[0]["action_id"]
                   and ud[0]["queue_id"] is None, ud)
                page.click(".c01-kinds [data-kind='all']")
                ok("「元に戻す」 뒤 카드가 다시 나옴", page.locator(".c01-item").count() == n_before, [n_before, page.locator(".c01-item").count()])
            # v0.3.11 Part C: 業者・IV 未定 (보류 메일 서류)
            page.click(".c01-kinds [data-kind='業者・IV未定']")
            page.locator(".c01-item").first.click()
            ok("業者・IV 未定 카드 = 보류 이유 · 候補 IV · 「搬入票ではない」 · 확인 버튼 잠김", page.locator(".c01-hold").count() == 1
               and "業者が合いません" in page.locator(".c01-hold").inner_text() and page.locator("#q-notours").count() == 1 and page.locator("#q-submit").is_disabled())
            # v0.3.11 Part C: 実況表 IV 머리 「候補書類あり (1)」 → 確認・入力 (그 IV 로 거름)
            page.click("#tab-main")
            hl = page.locator("[data-holdiv='TST2611-01']")
            ok("実況表 IV 머리 「候補書類あり (1)」", hl.count() == 1 and "候補書類あり (1)" in hl.inner_text())
            if hl.count():
                hl.click()
                page.wait_for_selector(".c01-input")
                ok("候補書類あり → 確認・入力 「業者・IV 未定」 · IV 거름 표시", page.locator(".c01-qiv").count() == 1 and page.locator(".c01-item").count() == 1)
                page.click("#qiv-clear")
            # 실況표 で 確認済 · 確認・入力 바지
            page.click("#tab-main")
            # v0.3.12 (R7K Part G · #153): 作業日 = 搬入票 값 (검정) · 없으면 칸 COMPASS 예정일 (회색 · 오늘 이전 = 굵은 빨강) · 표시만
            page.click("[data-port='all']")
            page.wait_for_timeout(200)
            t3 = "tbody[data-iv='TST2611-03']"
            wp = page.locator(t3 + " .c01-wdplan")
            ok("v0.3.12 Part G: 搬入票待ち 줄 작업일 = 칸 COMPASS 예정일 (어제 → 굵은 빨강 past)", wp.count() >= 1 and page.locator(t3 + " .c01-wdplan.past").count() >= 1
               and "予定日" in (wp.first.get_attribute("title") or ""), wp.count())
            t5 = "tbody[data-iv='TST2611-05']"
            if not page.locator("#show-unarrived").is_checked():
                page.click("#show-unarrived")
                page.wait_for_timeout(200)
            w5 = page.locator(t5 + " tr.missing .c01-wdplan")
            ok("v0.3.12 Part G: メール未着 칸 작업일 = 회색 (앞날 = past 아님)", w5.count() >= 1 and page.locator(t5 + " tr.missing .c01-wdplan.past").count() == 0, w5.count())
            ok("v0.3.12 Part G: 搬入票 작업일 있는 줄 = 그대로 (회색 표시 없음)", page.locator("tbody[data-iv='TST2611-01'] .c01-wdplan").count() == 0)
            # v0.3.12 (R7K Part C · #150): 同一コンテナ候補 — 実況表 두 줄 배지 → 確認・入力 카드 (두 줄 값 나란히) → 「同じコンテナとして合わせる」 → 完了 → 元に戻す
            sb = page.locator(t3 + " .c01-samebadge")
            ok("v0.3.12 Part C: 実況表 두 줄에 「同一候補」", sb.count() == 2, sb.count())
            ids_s = {x["action_id"] for x in actions(root)}
            sb.first.click()
            page.wait_for_selector(".c01-same")
            ok("同一候補 카드 = 두 줄 값 나란히 (FAX · 写真) · 다른 값 강조", page.locator(".c01-same tbody tr").count() == 7 and page.locator(".c01-same tr.d").count() >= 1
               and "同じコンテナとして合わせる" in page.locator("#q-submit").inner_text() and page.locator("#q-notsame").count() == 1)
            page.once("dialog", lambda dg: dg.accept())
            page.click("#q-submit")
            page.wait_for_timeout(400)
            ms = [x for x in actions(root) if x["action"] == "merge_same" and x["action_id"] not in ids_s]
            ok("「同じコンテナとして合わせる」 → merge_same 1 (fax · photo container_id · pair_id = queue_id)", len(ms) == 1 and ms[0]["value"]["fax_container_id"].endswith("FX1")
               and ms[0]["value"]["pair_id"] == ms[0]["queue_id"] and ms[0]["value"]["photo_container_id"].startswith("C-G-"), ms)
            page.click(".c01-kinds [data-kind='done']")
            di = page.locator(".c01-item.done", has_text="同一コンテナ候補")
            ok("合わせた카드 = 完了 에", di.count() == 1, di.count())
            if di.count():
                di.first.click()
                page.click("#q-undo")
                page.wait_for_timeout(400)
                un2 = [x for x in actions(root) if x["action"] == "undo" and x["value"]["action_id"] == (ms[0]["action_id"] if ms else None)]
                ok("同一候補 「元に戻す」 → undo (merge_same)", len(un2) == 1, un2)
            page.click(".c01-kinds [data-kind='同一候補']")
            ok("元に戻す 뒤 同一候補 카드가 다시 나옴", page.locator(".c01-item", has_text="同一コンテナ候補").count() == 1)
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
            r7n_checks(page, root, shots, a.engine)
            r7s_checks(page, root, shots)
            r7u_checks(page, root, shots)
            r7v_side_checks(br, url, shots)
            r7v_checks(page, root, shots)
            r7v_remind_checks(page, root, shots)
            r7w_checks(page, ctx, root, shots)
            r7x_checks(page, ctx, root, shots)
            compass_r7x_checks(page)
            r7z_checks(page, root, shots)
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
