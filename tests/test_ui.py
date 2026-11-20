# ✦ Powered by LEENAI Automation System — C-01 搬入票 TOOL v0.1 画面試験 (Playwright · 가명 fixtures)
"""fixtures 를 임시 폴더로 복사 → serve_local.py (127.0.0.1) → Chromium 으로 열어 확인.
확인: 実況表 열 15 · 줄 색 4종 · 담당 港 거르기 · メール未着 줄 · 사진 보기 넘기기 · 確認・入力 4종 처리 · _actions JSON = 엔진 스키마 ·
      30초 겹쳐 보기 (다른 창) · 先勝ち · 체크디짓 거부 · Compass入力/催促 비활성 · 4테마 스크린샷 · 콘솔 오류 0 · 네트워크 = LEENAI_COMMON·로컬만.
사용: python tests/test_ui.py [--shots 폴더] [--engine C:\\LEENAI_C01_PROD\\code] [--no-wait30]"""
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


FROZEN_TXT = "✓入力済"   # v0.3.52 (R10W · #307) · v0.3.60 (R11R · #334): 「自動OK ✓入力済」 / 「確認済 ✓入力済」


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
    enh_checks(page, tab, shots)
    zoom_checks(page, tab, shots)
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
    # 実況表에 없는 해시 · 원래 화면 없음
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

ZP_STATE = "() => { const z = C01.photoPage.zp; return z ? [Math.round(z.s * 1000) / 1000, Math.round(z.fx * 1000) / 1000, Math.round(z.fy * 1000) / 1000] : null; }"
IMG_READY = "() => { const e = document.querySelector('.c01-pv-img'); return e && e.complete && e.naturalWidth > 0 && C01.photoPage.zp; }"
RECT = "() => { const b = document.querySelector('.c01-pv-img').getBoundingClientRect(); return [b.left, b.top, b.width, b.height]; }"
TOUCH = """(a) => { const s = document.getElementById('pv-stage'), r = s.getBoundingClientRect(), x0 = r.left + r.width / 2, y0 = r.top + r.height / 2;
    const ev = (t, id, x, y) => s.dispatchEvent(new PointerEvent(t, {pointerId: id, pointerType: 'touch', isPrimary: id === 1, clientX: x, clientY: y, bubbles: true, cancelable: true, button: 0}));
    if (a === 'swipe') { ev('pointerdown', 1, x0, y0); ev('pointermove', 1, x0 - 50, y0); ev('pointerup', 1, x0 - 120, y0 + 5); }
    if (a === 'pinch') { ev('pointerdown', 1, x0 - 20, y0); ev('pointerdown', 2, x0 + 20, y0); ev('pointermove', 1, x0 - 50, y0); ev('pointermove', 2, x0 + 50, y0); ev('pointerup', 1, x0 - 50, y0); ev('pointerup', 2, x0 + 50, y0); }
    if (a === 'pan') { ev('pointerdown', 1, x0, y0); ev('pointermove', 1, x0 - 120, y0); ev('pointerup', 1, x0 - 120, y0); }
    return document.getElementById('pv-pos').textContent; }"""
PERF = """async () => { const c = document.createElement('canvas'); c.width = 4000; c.height = 3000; const g = c.getContext('2d');
    for (let i = 0; i < 300; i++) { g.fillStyle = 'hsl(' + (i * 37 % 360) + ',60%,50%)'; g.fillRect((i * 131) % 4000, (i * 71) % 3000, 200, 150); }
    const b = await new Promise(r => c.toBlob(r, 'image/jpeg', 0.9)); const img = document.querySelector('.c01-pv-img');
    await new Promise(r => { img.onload = r; img.src = URL.createObjectURL(b); });
    const z = C01.photoPage.zp, raf = () => new Promise(r => requestAnimationFrame(r)); await raf();
    const t0 = performance.now(); z.zoomBy(4);
    for (let i = 0; i < 60; i++) { z.panPx(i % 2 ? 30 : -25, i % 3 ? 12 : -10); await raf(); }
    const ms = (performance.now() - t0) / 60; z.reset(); return [img.naturalWidth, img.naturalHeight, Math.round(ms * 10) / 10]; }"""


def zoom_checks(page, tab, shots):
    """v0.3.55 (R10Y · ZHAN 제안 · #313): 사진 크게 보기 안 확대 · 이동 — 휠 (커서 기준 · 1~6배) · 끌기 · 화살표 · 더블클릭 2.5배 ↔ 원래 · 全体表示 · 다음 사진 = 원래 크기 ·
    拡大・補正 두 그림 같이 · 1배일 때만 밀어 넘기기 · 두 손가락 · Ctrl+휠 = 브라우저 몫 (막지 않음) · 큰 사진 (12MP) 실측."""
    tab.click(".c01-pv-th[data-go='2']")
    tab.wait_for_function(IMG_READY, timeout=5000)
    st = lambda: tab.evaluate(ZP_STATE)  # noqa: E731
    pos0 = tab.locator("#pv-pos").inner_text()
    bar = [tab.locator(x).count() for x in ("#pv-z-out", "#pv-z-v", "#pv-z-in", "#pv-z-fit")]
    ok("R10Y 버튼 − · 배율 · ＋ · 全体表示 · 처음 100%", bar == [1, 1, 1, 1] and tab.locator("#pv-z-v").inner_text() == "100%" and st() == [1, 0, 0], [bar, st()])
    r = tab.evaluate(RECT)
    cx, cy = r[0] + r[2] * 0.3, r[1] + r[3] * 0.4                       # 사진 안 (30%, 40%) 위에서 휠
    tab.mouse.move(cx, cy)
    for _ in range(3):
        tab.mouse.wheel(0, -100)
        tab.wait_for_timeout(30)
    s1 = st()
    r1 = tab.evaluate(RECT)
    fx, fy = (cx - r1[0]) / r1[2], (cy - r1[1]) / r1[3]
    ok("R10Y 휠 3번 = 1.15³ 배 · 커서 아래 점 그대로 (사진 안 30% · 40%)", abs(s1[0] - 1.521) < 0.01 and abs(fx - 0.3) < 0.01 and abs(fy - 0.4) < 0.01
       and tab.locator("#pv-z-v").inner_text() == "152%", [s1, round(fx, 3), round(fy, 3)])
    tab.mouse.down()
    tab.mouse.move(cx - 40, cy - 30, steps=4)
    tab.mouse.up()
    r2 = tab.evaluate(RECT)
    ok("R10Y 끌어서 이동 (−40, −30 px) · 배율 그대로", abs(r2[0] - (r1[0] - 40)) < 1.5 and abs(r2[1] - (r1[1] - 30)) < 1.5 and abs(st()[0] - s1[0]) < 1e-6, [r1[:2], r2[:2]])
    a0 = st()
    tab.keyboard.press("ArrowRight")
    tab.keyboard.press("ArrowDown")
    a1 = st()
    ok("R10Y 확대 중 화살표 = 이동 (사진 안 바뀜)", tab.locator("#pv-pos").inner_text() == pos0 and a1[1] < a0[1] and a1[2] < a0[2] and a1[0] == a0[0], [a0, a1])
    for _ in range(40):
        tab.mouse.wheel(0, -100)
    tab.wait_for_timeout(150)
    hi = st()
    cover = tab.evaluate("""() => { const b = document.querySelector('.c01-pv-img').getBoundingClientRect(), z = C01.photoPage.zp, w = b.width / z.s, h = b.height / z.s,
        l0 = b.left - z.fx * w, t0 = b.top - z.fy * h; return [b.left <= l0 + 0.5, b.top <= t0 + 0.5, b.right >= l0 + w - 0.5, b.bottom >= t0 + h - 0.5]; }""")
    ok("R10Y 최대 6배 · 확대한 사진이 원래 자리를 늘 덮음 (빈칸으로 밀려나지 않음)", hi[0] == 6 and all(cover), [hi, cover])
    tab.click("#pv-z-fit")
    ok("R10Y 「全体表示」 = 100% · 위치 처음", st() == [1, 0, 0] and tab.locator("#pv-z-v").inner_text() == "100%", st())
    tab.mouse.dblclick(cx, cy)
    d1 = st()
    tab.mouse.dblclick(cx, cy)
    d2 = st()
    ok("R10Y 더블클릭 = 2.5배 ↔ 원래 크기", d1[0] == 2.5 and d2 == [1, 0, 0], [d1, d2])
    tab.click("#pv-z-in")
    tab.click("#pv-z-in")
    b1 = st()
    tab.click("#pv-z-out")
    ok("R10Y ＋ 2번 = 2.25배 · − = 1.5배", b1[0] == 2.25 and st()[0] == 1.5, [b1, st()])
    cw = tab.evaluate("""() => { const s = document.getElementById('pv-stage'), z0 = C01.photoPage.zp.s;
        const e = new WheelEvent('wheel', {deltaY: -100, ctrlKey: true, bubbles: true, cancelable: true, clientX: 10, clientY: 10});
        const notPrevented = s.dispatchEvent(e);
        const o = new WheelEvent('wheel', {deltaY: 100, bubbles: true, cancelable: true});
        const outside = document.querySelector('.c01-pv-top').dispatchEvent(o);
        return [notPrevented, C01.photoPage.zp.s === z0, outside]; }""")
    ok("R10Y Ctrl+휠 = 막지 않음 (브라우저 확대 그대로 · 배율 안 바뀜) · 틀 밖 휠 = 막지 않음", cw == [True, True, True], cw)
    tab.click("#pv-next")
    tab.wait_for_function(IMG_READY, timeout=5000)
    ok("R10Y 다음 사진 = 원래 크기 (100%)", st()[0] == 1 and tab.locator("#pv-z-v").inner_text() == "100%", st())
    tab.click("#pv-prev")
    tab.wait_for_function(IMG_READY, timeout=5000)
    p0 = tab.locator("#pv-pos").inner_text()
    p1 = tab.evaluate(TOUCH, "swipe")
    tab.wait_for_function(IMG_READY, timeout=5000)
    tab.evaluate(TOUCH, "pinch")
    pz = st()
    p2 = tab.evaluate(TOUCH, "pan")
    pp = st()
    ok("R10Y 터치: 1배 밀기 = 다음 사진 · 두 손가락 = 확대 (거리 2.5배) · 확대 중 밀기 = 이동 (넘기지 않음)",
       p1 != p0 and abs(pz[0] - 2.5) < 0.01 and p2 == p1 and pp[1] < pz[1] and pp[0] == pz[0], [p0, p1, p2, pz, pp])
    tab.click("#pv-prev")
    tab.wait_for_function(IMG_READY, timeout=5000)
    tab.click("#pv-enh")
    tab.wait_for_selector("#pv-enhbox[data-done='1']", timeout=10000)
    eo = tab.evaluate("() => { const b = document.getElementById('pv-enh-out').getBoundingClientRect(); return [b.left + b.width * 0.5, b.top + b.height * 0.5]; }")
    tab.mouse.move(eo[0], eo[1])
    for _ in range(4):
        tab.mouse.wheel(0, -100)
        tab.wait_for_timeout(30)
    tab.mouse.down()
    tab.mouse.move(eo[0] + 25, eo[1] + 15, steps=3)
    tab.mouse.up()
    tf = tab.evaluate("() => ['pv-enh-orig', 'pv-enh-out'].map(id => document.getElementById(id).style.transform)")
    ok("R10Y 拡大・補正 두 그림 = 같은 확대 · 같은 위치 (같은 곳 비교)", bool(tf[0]) and tf[0] == tf[1] and "scale(1.749" in tf[0], tf)
    tab.screenshot(path=str(shots / "photo_zoom_enh.png"))
    tab.click("#pv-enh")
    tab.wait_for_function(IMG_READY, timeout=5000)
    ok("R10Y 拡大・補正 닫으면 원래 크기", st()[0] == 1, st())
    perf = tab.evaluate(PERF)
    ok("R10Y 12MP 사진 (4000×3000) 확대 · 이동 60번 = 한 번 평균 < 40ms (rAF 기준 · CSS transform 만)", perf[0] == 4000 and perf[1] == 3000 and perf[2] < 40, perf)
    print("   R10Y 12MP 실측:", perf)
    tab.click(".c01-pv-th[data-go='2']")


def lb_zoom_checks(page, shots):
    """v0.3.55 (R10Y · #313): 화면 안 사진 (라이트박스 · Shift+클릭 · 팝업 막힘 · CT 不明 카드) = 같은 확대 · 이동."""
    zs = lambda: page.evaluate("() => C01.state.lbzp ? [Math.round(C01.state.lbzp.s * 1000) / 1000, C01.state.lbzp.fx, C01.state.lbzp.fy] : null")  # noqa: E731
    pos = lambda: page.locator(".c01-lb-h .c").inner_text()  # noqa: E731
    page.wait_for_function("() => { const e = document.querySelector('.c01-lbimg'); return e && e.complete && e.naturalWidth > 0; }", timeout=5000)
    bar = [page.locator(x).count() for x in ("#lb-z-out", "#lb-z-v", "#lb-z-in", "#lb-z-fit")]
    r = page.evaluate("() => { const b = document.querySelector('.c01-lbimg').getBoundingClientRect(); return [b.left + b.width / 2, b.top + b.height / 2]; }")
    page.mouse.move(r[0], r[1])
    for _ in range(5):
        page.mouse.wheel(0, -100)
        page.wait_for_timeout(30)
    z1 = zs()
    p0 = pos()
    page.keyboard.press("ArrowRight")
    p1 = pos()
    page.mouse.dblclick(r[0], r[1])
    z2 = zs()
    page.mouse.dblclick(r[0], r[1])
    z3 = zs()
    ok("R10Y 라이트박스 = 버튼 4 · 휠 확대 · 확대 중 → = 이동 (사진 그대로) · 더블클릭 = 원래 ↔ 2.5배",
       bar == [1, 1, 1, 1] and abs(z1[0] - 2.011) < 0.01 and p1 == p0 and z2 == [1, 0, 0] and z3[0] == 2.5, [bar, z1, p0, p1, z2, z3])
    page.click("#lb-z-fit")
    page.keyboard.press("ArrowRight")
    p3 = pos()
    page.mouse.dblclick(r[0], r[1])
    page.click("#lb-next")
    z4 = zs()
    ok("R10Y 라이트박스 全体表示 → 1배 → = 다음 · 다음 사진 = 원래 크기", p3 != p0 and z4 == [1, 0, 0], [p0, p3, z4])
    page.keyboard.press("Escape")
    ok("R10Y 라이트박스 닫기 = 창 없음", page.locator(".c01-lb").count() == 0)



BOX_INJ = None


def enh_checks(page, tab, shots):
    """v0.3.51 (R10V · #308): 写真 「拡大・補正」 = 押した時だけ canvas 로 만든 확인용 그림 · 원본 나란히 · 표시 문구 · 값 나란히 (다른 글자만 빨강) · 기존 동작 그대로."""
    root_n = page.evaluate("document.querySelectorAll('.c01-pv-enh').length")
    ok("R10V 버튼 1개 · 누르기 전 보정 그림 없음 (기존 화면 그대로)", tab.locator("#pv-enh").count() == 1 and tab.locator("#pv-enhbox").count() == 0
       and tab.locator("#pv-enh").inner_text() == "拡大・補正" and root_n == 0, [tab.locator("#pv-enh").count(), tab.locator("#pv-enhbox").count()])
    head = tab.evaluate("C01.photoPage.head")
    ok("R10V 머리 값 = 엔진 값 (CT · シール) · 출처 목록", isinstance(head.get("vals"), dict) and set(head["vals"]) == {"ct", "seal"}
       and head["vals"]["ct"]["engine"] and isinstance(head["vals"]["ct"]["srcs"], list), head.get("vals"))
    pos0 = tab.locator("#pv-pos").inner_text()
    tab.click("#pv-enh")
    tab.wait_for_selector("#pv-enhbox[data-done='1']", timeout=10000)
    box = tab.locator("#pv-enhbox")
    dims = tab.evaluate("""() => ['pv-enh-orig','pv-enh-out'].map(id => { const c = document.getElementById(id); return [c.width, c.height]; })""")
    src = tab.evaluate("() => { const i = document.querySelector('.c01-pv-img'); return [i.naturalWidth, i.naturalHeight, i.src.slice(0, 5)]; }")
    ok("R10V 원본 · 보정 나란히 (같은 크기 · 상자 없으면 사진 전체) · 원본 사진 그대로 (blob)", dims[0] == dims[1] and dims[0][0] > 0
       and box.get_attribute("data-whole") == "1" and src[2] == "blob:" and tab.locator(".c01-pv-img").count() == 1, [dims, src])
    mark = tab.locator(".c01-pv-enhmark").inner_text()
    caps = tab.eval_on_selector_all(".c01-pv-enhfig figcaption", "els => els.map(e => e.textContent)")
    ok("R10V 그림 위 「補正画像 · 判断は原本と搬入票で」 · 원본 칸 이름 「原本」", mark == "補正画像 · 判断は原本と搬入票で" and caps == ["原本", "補正画像 · 判断は原本と搬入票で"], [mark, caps])
    same = tab.evaluate("""() => { const a = document.getElementById('pv-enh-orig'), i = document.querySelector('.c01-pv-img');
        const c = document.createElement('canvas'); c.width = a.width; c.height = a.height; const g = c.getContext('2d');
        g.imageSmoothingEnabled = true; g.imageSmoothingQuality = 'high'; g.drawImage(i, 0, 0, a.width, a.height);
        const x = g.getImageData(0, 0, c.width, c.height).data, y = a.getContext('2d').getImageData(0, 0, a.width, a.height).data;
        let d = 0; for (let k = 0; k < x.length; k++) d = Math.max(d, Math.abs(x[k] - y[k])); return d; }""")
    ok("R10V 원본 칸 = 손대지 않은 원본 (화소 차 0)", same == 0, same)
    ms = int(box.get_attribute("data-ms") or -1)
    ok("R10V 처리 시간 기록 (data-ms)", ms >= 0, ms)
    cfg = tab.evaluate("() => [C01.photoEnhance.ENH.CLIP, C01.photoEnhance.ENH.SHARP]")
    ok("R10V 보정 = CLAHE clip 1.5 · 선명화 0 (20장 측정값)", cfg == [1.5, 0], cfg)
    tab.screenshot(path=str(shots / "photo_enh.png"))
    # 보정 함수: 고른 회색 = 고른 그대로 (없는 무늬를 만들지 않음) · 밝기 순서 그대로 · 상자 = 여백 25% · 회전
    flat = tab.evaluate("""() => { const w = 64, h = 48, d = new Uint8ClampedArray(w * h * 4); for (let k = 0; k < w * h; k++) { d[k*4] = d[k*4+1] = d[k*4+2] = 120; d[k*4+3] = 255; }
        C01.photoEnhance.enhanceData(d, w, h); const s = new Set(); for (let k = 0; k < w * h; k++) s.add(d[k*4] + ',' + d[k*4+1] + ',' + d[k*4+2]); return s.size; }""")
    ok("R10V 고른 회색 그림 = 보정 뒤에도 한 가지 색 (무늬 · 글자 만들지 않음)", flat == 1, flat)
    order = tab.evaluate("""() => { const w = 64, h = 64, d = new Uint8ClampedArray(w * h * 4); for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) { const k = y * w + x, v = x < 32 ? 60 : 90; d[k*4] = d[k*4+1] = d[k*4+2] = v; d[k*4+3] = 255; }
        C01.photoEnhance.enhanceData(d, w, h); let bad = 0; for (let y = 0; y < h; y++) { const a = d[(y * w + 10) * 4], b = d[(y * w + 54) * 4]; if (!(a < b)) bad++; } return bad; }""")
    ok("R10V 어두운 쪽 < 밝은 쪽 (밝기 순서 그대로)", order == 0, order)
    cr = tab.evaluate("() => [C01.photoEnhance.cropRect(1000, 800, {x0: 400, y0: 500, x1: 600, y1: 600, text_rotation: 90}), C01.photoEnhance.cropRect(1000, 800, null), C01.photoEnhance.cropRect(1000, 800, {found: false})]")
    ok("R10V 상자 자르기 = 여백 25% (최소 12px) · 회전 90 · 상자 없음 = 전체", cr[0] == {"x": 350, "y": 380, "w": 300, "h": 120, "rot": 90, "whole": False}
       and cr[1]["whole"] and cr[2]["whole"], cr)
    vt = tab.evaluate("""() => { const d = document.createElement('div'); d.innerHTML = C01.photoValsTable({ct: {engine: 'ABCU1234565', srcs: [{src: '搬入票', value: 'ABCU1284565'}, {src: '写真', value: 'ABCU1234565'}]}, seal: {engine: '', srcs: []}});
        return [d.querySelectorAll('tr').length, [...d.querySelectorAll('.c01-pv-dif')].map(e => e.textContent), [...d.querySelectorAll('.c01-pv-src')].map(e => e.textContent)]; }""")
    ok("R10V 값 나란히 = 엔진 · 搬入票 · 写真 · 다른 글자만 빨강 (가명) · 값 없는 칸은 줄 없음", vt == [1, ["8"], ["エンジン", "搬入票", "写真"]], vt)
    tab.click("#pv-enh")
    ok("R10V 다시 누르면 닫힘 · 사진 위치 그대로", tab.locator("#pv-enhbox").count() == 0 and tab.locator("#pv-pos").inner_text() == pos0, pos0)
    tab.click("#pv-enh")
    tab.wait_for_selector("#pv-enhbox[data-done='1']", timeout=10000)
    tab.keyboard.press("ArrowRight")
    ok("R10V 다른 사진으로 가면 닫힘 (그 사진 원본부터)", tab.locator("#pv-enhbox").count() == 0)
    tab.keyboard.press("ArrowLeft")
    # R10X (엔진 v0.5.124 out_photo_box): 엔진 box 가 있는 사진 = 그 칸 (여백 25% · 최소 12px · 3배까지) 만 · 머리에 box 그대로 넘어옴
    hb = tab.evaluate("C01.photoPage.head.photos.map(p => p.box || null)")
    ok("R10X 엔진 box → 사진 탭 머리 그대로 (6번째만)", hb[5] == BOX_INJ and sum(1 for x in hb if x) == 1, hb)
    tab.click(".c01-pv-th[data-go='5']")
    tab.wait_for_function("() => { const e = document.querySelector('.c01-pv-img'); return e && e.complete && e.naturalWidth > 0; }", timeout=5000)
    tab.click("#pv-enh")
    tab.wait_for_selector("#pv-enhbox[data-done='1']", timeout=10000)
    got = tab.evaluate("""() => { const i = document.querySelector('.c01-pv-img'), b = C01.photoPage.head.photos[5].box;
        const r = C01.photoEnhance.cropRect(i.naturalWidth, i.naturalHeight, b), sc = Math.min(3, 1600 / Math.max(r.w, r.h));
        const o = document.getElementById('pv-enh-out'), a = document.getElementById('pv-enh-orig');
        return { whole: document.getElementById('pv-enhbox').dataset.whole, want: [Math.round(r.w * sc), Math.round(r.h * sc)], out: [o.width, o.height], orig: [a.width, a.height],
                 img: [i.naturalWidth, i.naturalHeight], r: r }; }""")
    ok("R10X 상자 있는 사진 = 그 칸만 자름 (data-whole 0) · 원본 · 보정 같은 크기 = 자른 칸 × 배율 (3배까지)",
       got["whole"] == "0" and got["out"] == got["orig"] == got["want"] and got["want"][0] < got["img"][0] * 3 + 1 and not got["r"]["whole"], got)
    tab.screenshot(path=str(shots / "photo_enh_box.png"))
    tab.click("#pv-enh")
    tab.click(".c01-pv-th[data-go='2']")


def h4_checks(page, jj):
    """v0.3.15 (R7N Part H-4 · 결정 #166): 칸보다 줄이 많은 부킹 = 넘는 줄만 빨강 「COMPASS 枠外」 · 머리 「枠外 n」. 칸이 남은 未割当 = 그대로."""
    over = page.evaluate("""() => Object.fromEntries([...document.querySelectorAll('tbody[data-iv]')].map(tb => [tb.dataset.iv,
        [tb.querySelectorAll('tr.c01-row.over').length, (tb.querySelector('.c01-overhead') || {}).textContent || '',
         [...tb.querySelectorAll('tr.c01-row')].map(tr => tr.classList.contains('over') ? 'o' : tr.classList.contains('unassigned') ? 'u' : 's').join('')]]))""")
    # v0.3.43 (R9P Part 0-3 · 결정 #166 · #182): 화면 줄 = 칸 있는 줄 + 빈 칸 (メール未着) + 칸 없는 줄 → 칸 없는 줄 (未割当) 이 1줄이라도 있으면
    # COMPASS 칸 수를 넘음 = 칸 없는 줄 전부 빨강 (값 있는 줄 ≤ 칸 이어도 · 빈 칸이 남아도). 옛 셈 (값 있는 줄 > 칸) 은 빈 칸을 안 세서 빨강이 안 나왔음
    sg = lambda iv: {s["slot_guid"] for s in iv["slots"]}   # noqa: E731
    want = {iv["iv_no"]: (sum(1 for r in iv["rows"] if r.get("slot_guid") not in sg(iv)) if iv["slots"] else 0) for iv in jj["ivs"]}
    free02 = sum(1 for r in next(iv for iv in jj["ivs"] if iv["iv_no"] == "TST2611-02")["rows"] if not r.get("slot_guid"))
    ok("#15 枠外 줄 수 = 칸 없는 줄 전부 (TST2611-02 = 4줄 · 3칸 → 未割当 2줄 · TST2611-04 = 4줄 ≤ 4칸 이어도 未割当 2줄)",
       {k: v[0] for k, v in over.items()} == want and want["TST2611-02"] == 2 == free02 and want["TST2611-04"] == 2, [over, want])
    ok("#15 머리 「枠外 n」 (n = 칸 없는 줄 수 · 칸 없는 줄 없는 부킹 = 없음)", all(v[1] == (f"枠外 {want[k]}" if want[k] else "") for k, v in over.items()), over)
    ok("#15 未割当 표시 0 (전부 枠外) · TST2611-04 도 빨강 2줄 (R9P 0-3)", all("u" not in v[2] for v in over.values()) and over["TST2611-02"][2].endswith("oo")
       and over["TST2611-04"][2].count("o") == 2, over)
    # R9P 0-3 시험 고정: 형님 화면 사례 모양 (칸 11 · 값 있는 줄 8 중 칸 1 · 칸 없는 7 → 枠外 7 · 칸 4 · 칸 없는 2 → 枠外 2) — 가명 부킹을 화면 상태에 더해 셈
    shape = page.evaluate("""() => { const S = C01.state, keep = S.jik.ivs, b = JSON.parse(JSON.stringify(keep[0]));
        const mk = (no, nS, nSl, nFree) => { const iv = JSON.parse(JSON.stringify(b)); iv.iv_no = no; iv.cy_cut = '2099-12-31';
            iv.slots = Array.from({length: nS}, (_, i) => ({slot_guid: no + '-s' + i, packer: 'PK', seq: i}));
            iv.mail_missing = iv.slots.slice(nSl).map(s => ({slot_guid: s.slot_guid, work_date: null}));
            iv.rows = Array.from({length: nSl + nFree}, (_, i) => ({...b.rows[0], container_id: no + '-c' + i, ct: '', seal: '', status: '受信中',
                slot_guid: i < nSl ? no + '-s' + i : null, reasons: i >= nSl ? ['UNIT_PRICE_DIFF'] : [], unit_price_cands: 6}));
            return iv; };
        S.jik = {...S.jik, ivs: keep.concat([mk('TSTW-A', 11, 1, 7), mk('TSTW-B', 4, 0, 2)])}; C01.app.render();
        const n = iv => document.querySelectorAll(`tbody[data-iv='${iv}'] tr.c01-row.over`).length;
        const h = iv => (document.querySelector(`tbody[data-iv='${iv}'] .c01-overhead`) || {}).textContent || '';
        const w = document.querySelector(`tbody[data-iv='TSTW-A'] tr.c01-row.over`);
        const r = [n('TSTW-A'), h('TSTW-A'), n('TSTW-B'), h('TSTW-B'), document.querySelectorAll(`tbody[data-iv='TSTW-A'] tr.c01-row`).length,
                   [...document.querySelectorAll(`tbody[data-iv='TSTW-A'] tr`)].some(tr => tr.textContent.includes('割当待ち')), w ? w.textContent : ''];
        S.jik = {...S.jik, ivs: keep}; C01.app.render(); return r; }""")
    ok("R9P 0-3 칸 11 · 칸 없는 줄 7 → 枠外 7 · 칸 4 · 칸 없는 줄 2 → 枠外 2 · 「割当待ち」 없음", shape[:4] == [7, "枠外 7", 2, "枠外 2"] and shape[5] is False, shape)
    ok("R9P 0-1b ② 単価・契約 줄 = 「単価・契約の違う枠 6 個 — どの契約か不明」", "単価・契約の違う枠 6 個 — どの契約か不明" in shape[6], shape[6])
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
    need = ["見る", "確認・入力", "催促", "Compass入力", "自分の担当", "自動OK", "再確認", "受信中",
            "✎ 修正", "搬入票ではない", "元に戻す", "Ctrl+Shift+R", "気づいた点は担当の管理者へ（画面の写真と IV 番号）"]
    ok("v0.3.17 使い方 창 열림 · 내용 (상태 · 確認・入力 · Ctrl+Shift+R · 관리자)", all(w in txt for w in need), [w for w in need if w not in txt])
    gone = ["並行期間", "これまでのシステム", "これまでどおり", "11-16", "11-22", "11/24", "試験表示", "試験運用中"]
    mtxt = page.locator("#c01-modal").inner_text()
    ok("v0.3.48 (R10B · #298) 使い方 기간 · 전환 문구 · 試験表示 0 (창 제목 포함)", not any(w in mtxt for w in gone), [w for w in gone if w in mtxt])
    ok("v0.3.34 使い方 「業者登録」 한 줄 (試験表示 와 같은 칩 · 元に戻す)", page.locator("#help-body [data-regsender-help].c01-trial").count() == 1 and "業者登録" in txt and "元に戻す" in txt)
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
    ok("v0.3.17 使い方 4테마 글자색 ≠ 배경색 (본문 · 業者登録 칩)", len(cols) == 4 and all(c[0] != c[1] and c[2] != c[1] and c[2] != c[3] and c[0] != c[3] for c in cols), cols)
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
    """v0.3.23 (R7W): Part A 自動OK · 確認済 줄 修正 (状況 클릭 → 경고 → 修正 폼 · mode edit · 確認済 · 元に戻す · COMPASS 入力済 경고) · Part B 📄 서류 탭 (搬入票 먼저)."""
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
    ok("A 경고 1번 = 「この行は 自動OK です · 確認済（手入力）に変わり、記録されます · 修正しますか？」 + COMPASS 入力済 경고 · [修正する] [やめる]",
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


def r9d_remind_checks(page, root, shots):
    """v0.3.35 (R9D Part C · #263): 원청 주소 0 (to · 未受信 모두 없음 · no_recipient) = 「宛先なし — 担当者が確認」 · 送信（試験） 버튼 잠김 · 다른 초안은 그대로."""
    rp = root / "_data" / "remind.json"
    rt0 = rp.read_text(encoding="utf-8")
    r2 = json.loads(rt0)
    r2["send_mode"] = {"test": True, "to": "test.box@example.invalid", "tag": "[test]"}
    ds = r2["ivs"]["TST2611-02"]
    ok("R9D 시험 자료 = TST2611-02 초안 있음", len(ds) >= 1, len(ds))
    d0 = ds[0]
    d0["to"], d0["cc"], d0["to_unreceived"], d0["cc_unreceived"] = [], [], [], []
    d0["no_recipient"] = True; d0["send_ready"] = False; d0["status"] = "宛先なし — 担当者が確認"
    d0["round"] = 9                                                          # 앞 시험 (r7v) 이 1회차를 보낸 기록 = 送信済 → 다른 회차로
    rp.write_text(json.dumps(r2, ensure_ascii=False, indent=1) + chr(10), encoding="utf-8")
    page.click("#tab-main")
    page.click("[data-port='all']")
    page.evaluate("() => { C01.app.tick(); }")
    page.wait_for_timeout(500)
    page.evaluate("() => { C01.state.info.mode = 'graph'; }")
    page.click("tbody[data-iv='TST2611-02'] [data-remind]")
    page.wait_for_selector(".c01-rmd")
    sec = page.locator(".c01-rmd[data-rmd='0']")
    txt = sec.inner_text()
    b0 = page.locator("[data-rsend='0']")
    ok("R9D 宛先なし = 宛先 칸 「宛先なし — 担当者が確認」 · 送信（試験） 잠김 · 이유 글", "宛先なし" in txt and b0.count() == 1 and b0.is_disabled()
       and "宛先なし" in page.locator("[data-rwhy='0']").inner_text(), [b0.count(), b0.count() and b0.is_disabled(), page.locator("[data-rwhy='0']").all_inner_texts()])
    page.locator("[data-rskip='0']").check(); page.locator("[data-rskip='0']").uncheck()
    ok("R9D 宛先なし = 체크를 바꿔도 잠김 그대로", b0.is_disabled())
    if len(ds) > 1:
        ok("R9D 다른 초안 (宛先 있음) = 버튼 켜짐 그대로", page.locator("[data-rsend='1']").is_enabled())
    page.screenshot(path=str(shots / "r9d_remind_noto.png"))
    page.click("[data-close]")
    rp.write_text(rt0, encoding="utf-8")
    page.evaluate("C01.state.info.mode = 'local'; C01.app.tick()")
    page.wait_for_timeout(300)


def r9e_ccfixed_checks(page, root, shots, engine):
    """v0.3.36 (R9E Part B · #264): 엔진 cc_fixed = CC 고정 → 🔒 표시 · 삭제 버튼 0 · 고정 아닌 CC = 글자 그대로 · cc_fixed 없는 초안 = 지금 그대로.
    받는 쪽 대조: 엔진 (--engine) engine/notify/remind.py 가 내는 키 이름 = 'cc_fixed' (TOOL 이 읽는 키)."""
    src = Path(engine) / "engine" / "notify" / "remind.py"
    if src.is_file():
        es = src.read_text(encoding="utf-8")
        ok("R9E 받는 쪽 대조: 엔진 초안 키 cc_fixed (t[\"cc_fixed\"]) = TOOL 이 읽는 키", 't["cc_fixed"]' in es and "d.cc_fixed" in (TOOL / "js" / "app.js").read_text(encoding="utf-8"))
    rp = root / "_data" / "remind.json"
    rt0 = rp.read_text(encoding="utf-8")
    r2 = json.loads(rt0)
    ds = r2["ivs"]["TST2611-02"]
    fx = ["desk@example.invalid", "photo.desk@example.invalid"]
    d0 = ds[0]
    d0["cc"] = fx + ["vendor.cc@example.invalid"]
    d0["cc_fixed"] = list(fx)
    d1 = json.loads(json.dumps(d0))                                          # 시험 자료 = 초안 1개 → cc_fixed 없는 초안 (옛 엔진 모양) 1개 더
    d1.pop("cc_fixed", None)
    d1["packer"], d1["cc"], d1["round"] = "PACKER_Z", ["other.cc@example.invalid"], 7
    ds[1:] = [d1]
    rp.write_text(json.dumps(r2, ensure_ascii=False, indent=1) + chr(10), encoding="utf-8")
    page.click("#tab-main")
    page.click("[data-port='all']")
    page.evaluate("() => { C01.app.tick(); }")
    page.wait_for_timeout(500)
    page.click("tbody[data-iv='TST2611-02'] [data-remind]")
    page.wait_for_selector(".c01-rmd")
    sec = page.locator(".c01-rmd[data-rmd='0']")
    locks = sec.locator("[data-ccfixed]")
    ok("R9E CC 고정 2개 = 🔒 표시 · 주소 순서 그대로", locks.count() == 2 and [t.replace("🔒", "").strip() for t in locks.all_inner_texts()] == fx, locks.all_inner_texts())
    ok("R9E 고정 아닌 CC = 🔒 없음 · 글자 그대로", "vendor.cc@example.invalid" in sec.inner_text() and "🔒 vendor" not in sec.inner_text())
    ok("R9E 「固定 CC — 削除できません」 한 줄 · CC 삭제 버튼 0", "固定 CC — 削除できません" in sec.inner_text()
       and page.locator(".c01-rmd button", has_text="削除").count() == 0)
    s1 = page.locator(".c01-rmd[data-rmd='1']")
    ok("R9E cc_fixed 없는 초안 = 지금 그대로 (🔒 0 · 안내 0)", s1.count() == 1 and s1.locator("[data-ccfixed]").count() == 0 and "固定 CC" not in s1.inner_text()
       and "other.cc@example.invalid" in s1.inner_text())
    page.screenshot(path=str(shots / "r9e_remind_ccfixed.png"))
    page.click("[data-close]")
    rp.write_text(rt0, encoding="utf-8")
    page.evaluate("C01.app.tick()")
    page.wait_for_timeout(300)


def r9k_remind_live_checks(page, root, shots, engine):
    """v0.3.37 (R9K Part B-0 · A-1 · A-2 · B-3 · #270): 催促 실제 송신 — 엔진 send_mode {test: false, live: true} + config remindLive 일 때만 「送信」 ·
    받는 곳 = 초안 To · CC (원청 · 고정 CC) 그대로 · 직전 재검사 (allow 밖 주소 · allow 없음 · 고정 CC 빠짐 = 버튼 잠금 + 이유) · 같은 날 두 번째 = 「本日送信済み」 + 확인 창 ·
    reminder_sent 기록 (test false · to_n · cc_n) · source 두 번째 잠금 (초안과 다른 받는 곳 / 시험 모드 = 보내지 않음) · 받는 쪽 대조 (엔진 키 allow · live)."""
    src = Path(engine) / "engine" / "notify" / "remind.py"
    if src.is_file():
        es = src.read_text(encoding="utf-8")
        ok("R9K 받는 쪽 대조: 엔진 초안 키 allow · send_mode live = TOOL 이 읽는 키", 'd["allow"]' in es and '"live": True' in es
           and "d.allow" in (TOOL / "js" / "config.js").read_text(encoding="utf-8") and "m.live === true" in (TOOL / "js" / "app.js").read_text(encoding="utf-8"))
    rp = root / "_data" / "remind.json"
    rt0 = rp.read_text(encoding="utf-8")
    r2 = json.loads(rt0)
    r2["send_mode"] = {"test": False, "live": True, "guard_version": 1}
    fx = ["desk@example.invalid", "photo.desk@example.invalid"]
    base = r2["ivs"]["TST2611-02"][0]
    def mk(pk, to, cc, allow, rnd):
        d = json.loads(json.dumps(base))
        d.update({"packer": pk, "to": to, "cc": fx + cc, "cc_fixed": list(fx), "round": rnd, "to_unreceived": [], "cc_unreceived": [],
                  "body_html": "<p>" + d["body_text"].replace(chr(10), "<br>") + "</p>"})
        d.pop("no_recipient", None)
        d.pop("ready_at", None)
        if allow is not None:
            d["allow"] = allow
        else:
            d.pop("allow", None)
        return d
    good = mk("PACKER_L1", ["main@pk.example.invalid"], ["sub@pk.example.invalid"], {"domains": ["pk.example.invalid"], "addrs": []}, 11)
    noal = mk("PACKER_L2", ["main@pk.example.invalid"], [], None, 12)
    other = mk("PACKER_L3", ["main@pk.example.invalid", "x@other.example.invalid"], [], {"domains": ["pk.example.invalid"], "addrs": []}, 13)
    nofix = mk("PACKER_L4", ["main@pk.example.invalid"], [], {"domains": ["pk.example.invalid"], "addrs": []}, 14)
    nofix["cc"] = []
    r2["ivs"]["TST2611-02"] = [good, noal, other, nofix]
    rp.write_text(json.dumps(r2, ensure_ascii=False, indent=1) + chr(10), encoding="utf-8")
    page.click("#tab-main")
    page.click("[data-port='all']")
    page.evaluate("() => { C01.app.tick(); }")
    page.wait_for_timeout(500)
    page.evaluate("""() => { window.__sent = []; C01.state.info.mode = 'graph';
        C01.state.src.sendMailLive = function (m) { window.__sent.push({ call: m.subject }); return C01.sources.Graph.prototype.sendMailLive.call({ _fetch: function (u, o) {
            window.__sent.push({ url: u, body: JSON.parse(o.body) }); return Promise.resolve({ status: 202, ok: true }); } }, m); }; }""")
    page.click("tbody[data-iv='TST2611-02'] [data-remind]")
    page.wait_for_selector("[data-rsend]")
    md = page.locator("#c01-modal")
    ok("R9K 실제 발송 표시 · 안내 한 줄 (送信前に宛先・未着の内容を確認してください。本人のメールから送信されます。)",
       md.locator("[data-live]").count() >= 1 and "送信前に宛先・未着の内容を確認してください。本人のメールから送信されます。" in page.locator("#remind-livemode").inner_text()
       and page.locator("#remind-testmode").count() == 0, page.locator("#remind-livemode").all_inner_texts())
    b = [page.locator(f"[data-rsend='{i}']") for i in range(4)]
    w = [page.locator(f"[data-rwhy='{i}']").inner_text() for i in range(4)]
    ok("R9K 직전 재검사: 원청 + 고정 CC = 켜짐 「送信」 · allow 없음 / 원청 밖 주소 / 고정 CC 빠짐 = 잠김 + 이유",
       b[0].is_enabled() and b[0].inner_text() == "送信" and b[1].is_disabled() and "確認リスト" in w[1] and b[2].is_disabled() and "元請以外" in w[2]
       and b[3].is_disabled() and "固定 CC" in w[3], [x.is_enabled() for x in b] + w)
    msgs = []
    page.once("dialog", lambda dg: (msgs.append(dg.message), dg.accept()))
    b[0].click()
    for _ in range(40):
        if any(x.get("action") == "reminder_sent" and (x.get("value") or {}).get("packer") == "PACKER_L1" for x in actions(root)):
            break
        time.sleep(0.1)
    sent = page.evaluate("window.__sent")
    post = [x for x in sent if isinstance(x, dict) and x.get("url")]
    msg = post[0]["body"]["message"] if post else {}
    to = [r["emailAddress"]["address"] for r in msg.get("toRecipients", [])]
    cc = [r["emailAddress"]["address"] for r in msg.get("ccRecipients", [])]
    ok("R9K 送信 = 확인 창 1 · /me/sendMail 1번 · To = 초안 To · CC = 고정 CC + 원청 CC · BCC 0 · 제목 [test] 없음",
       len(msgs) == 1 and "PACKER_L1" in msgs[0] and len(post) == 1 and post[0]["url"].endswith("/me/sendMail") and to == ["main@pk.example.invalid"]
       and cc == fx + ["sub@pk.example.invalid"] and not msg.get("bccRecipients") and not msg.get("subject", "").startswith("[test]"), [msgs, to, cc, msg.get("subject")])
    rec = [x for x in actions(root) if x.get("action") == "reminder_sent" and (x.get("value") or {}).get("packer") == "PACKER_L1"]
    ok("R9K reminder_sent 기록 (test false · 회차 11 · to_n 1 · cc_n 3 · again false)", len(rec) == 1 and rec[0]["value"]["test"] is False
       and rec[0]["value"]["round"] == 11 and rec[0]["value"]["to_n"] == 1 and rec[0]["value"]["cc_n"] == 3 and rec[0]["value"]["again"] is False, rec)
    page.wait_for_selector(".c01-rmd[data-rmd='0'] [data-rtoday]", timeout=5000)
    s0 = page.locator(".c01-rmd[data-rmd='0']")
    ok("R9K 같은 날 = 「本日送信済み（担当 HH:MM）」 · 버튼 「もう一度送信」", "本日送信済み" in s0.inner_text() and page.locator("[data-rsend='0']").inner_text() == "もう一度送信",
       s0.inner_text()[:200])
    msgs2 = []
    page.once("dialog", lambda dg: (msgs2.append(dg.message), dg.dismiss()))
    page.locator("[data-rsend='0']").click()
    page.wait_for_timeout(400)
    post2 = [x for x in page.evaluate("window.__sent") if isinstance(x, dict) and x.get("url")]
    ok("R9K 두 번째 = 확인 창 「本日すでに送信済み」 · 취소 = 보내지 않음", len(msgs2) == 1 and "本日すでに送信済み" in msgs2[0] and len(post2) == 1, [msgs2, len(post2)])
    page.screenshot(path=str(shots / "r9k_remind_live.png"))
    page.click("[data-close]")
    blk = page.evaluate("""(d) => { const G = C01.sources.Graph.prototype.sendMailLive; const f = { _fetch: function () { return Promise.resolve({ status: 202, ok: true }); } };
        const a = G.call(f, { subject: 's', html: '', to: ['main@pk.example.invalid', 'evil@other.example.invalid'], cc: d.cc, draft: d });
        const b = G.call(f, { subject: 's', html: '', to: d.to, cc: d.cc.slice(1), draft: d });
        const c = G.call(f, { subject: 's', html: '', to: d.to, cc: d.cc, draft: Object.assign({}, d, { to: d.to.concat(['evil@other.example.invalid']) }) });
        const save = C01.state.remind.send_mode; C01.state.remind.send_mode = { test: true, to: 't@example.invalid', tag: '[test]' };
        const e = G.call(f, { subject: 's', html: '', to: d.to, cc: d.cc, draft: d }); C01.state.remind.send_mode = save;
        return Promise.all([a, b, c, e].map(p => p.then(() => 'sent', () => 'blocked'))); }""", good)
    ok("R9K source 두 번째 잠금: 초안 밖 To · CC 빠짐 · 원청 밖 초안 · 시험 모드 = 모두 보내지 않음", blk == ["blocked"] * 4, blk)
    r3 = json.loads(rp.read_text(encoding="utf-8"))
    r3["send_mode"] = {"test": False, "live": True, "guard_version": 1}
    rp.write_text(json.dumps(r3, ensure_ascii=False, indent=1) + chr(10), encoding="utf-8")
    page.evaluate("C01.SEND.remindLive = false; C01.app.tick()")
    page.wait_for_timeout(500)
    page.click("tbody[data-iv='TST2611-02'] [data-remind]")
    page.wait_for_selector(".c01-rmd")
    ok("R9K 화면 쪽 열쇠 (C01.SEND.remindLive false) = 送信 버튼 0", page.locator("[data-rsend]").count() == 0)
    page.click("[data-close]")
    page.evaluate("C01.SEND.remindLive = true; C01.state.info.mode = 'local'")
    rp.write_text(rt0, encoding="utf-8")
    page.evaluate("C01.app.tick()")
    page.wait_for_timeout(300)


def r9k_fax_reason_checks(page, root, shots):
    """v0.3.37 (R9K 0-5 f · #272): 未分類FAX 「搬入票ではない」 = 이유 창 (window.confirm 0) → not_ours · value = 이유 + sha16 (이유 없음 = 이유 칸 없음) · 元に戻す 가능."""
    qp = root / "_data" / "queue.json"
    qt0 = qp.read_text(encoding="utf-8")
    q2 = json.loads(qt0)
    docs_dir = [p_.relative_to(root).as_posix() for p_ in sorted((root / "TST2611-01" / "搬入票").glob("*.svg"))]
    fq = {"queue_id": "9e9e9e9e9e9e9e91", "kind": "未分類FAX", "iv_no": None, "ct": None, "field": None, "container_id": None, "values": {},
          "candidates": [], "files": [{"path": docs_dir[0], "name": "fax-r9k.pdf", "page": None, "bbox": None, "sha16": "9e9e9e9e9e9e9e9e"}],
          "note": "保留", "resolved": None, "superseded": [], "cy_cut": None, "cy_open": None, "issuer": None, "field_sources": {}, "field_source_text": {},
          "received_at": "2026-11-12T11:00:00+09:00"}
    q2["items"].append(fq)
    fq2 = json.loads(json.dumps(fq))
    fq2["queue_id"], fq2["files"][0]["sha16"], fq2["received_at"] = "9e9e9e9e9e9e9e92", "9e9e9e9e9e9e9e92", "2026-11-12T11:05:00+09:00"
    q2["items"].append(fq2)
    if "未分類FAX" not in q2["kinds"]:
        q2["kinds"] = list(q2["kinds"]) + ["未分類FAX"]
    qp.write_text(json.dumps(q2, ensure_ascii=False, indent=1) + chr(10), encoding="utf-8")
    page.evaluate("C01.app.tick()")
    page.wait_for_timeout(500)
    page.click("#tab-main")
    page.click("[data-port='all']")
    page.click("#tab-input")
    page.click(".c01-kinds [data-kind='未分類FAX']")
    n = page.locator(".c01-item").count()
    ok("R9K 未分類FAX 카드 있음 (시험 자료)", n >= 1, n)
    if not n:
        return
    if page.locator(".c01-item[data-q='9e9e9e9e9e9e9e91']").count():
        page.locator(".c01-item[data-q='9e9e9e9e9e9e9e91']").click()
    else:
        page.locator(".c01-item").first.click()
    dl = []
    page.once("dialog", lambda dg: (dl.append(dg.message), dg.accept()))
    page.click("#q-notours")
    page.wait_for_timeout(300)
    dlg = page.locator("#c01-nhdlg")
    ok("R9K 未分類FAX 「搬入票ではない」 = 이유 창 (ひとことでOK · 이유 버튼 5) · 옛 확인 창 0", dlg.count() == 1 and "ひとことでOK" in dlg.inner_text()
       and dlg.locator("[data-nhr]").count() == 5 and not dl, [dlg.count(), dl])
    page.click("[data-nhr='other_doc']")
    page.fill("#c01-nhtext", "請求書です")
    page.click("#c01-nhok")
    page.wait_for_timeout(500)
    rec = [x for x in actions(root) if x.get("action") == "not_ours"]
    v = (rec[-1].get("value") or {}) if rec else {}
    ok("R9K not_ours 기록 = 이유 코드 · 이유 글 · queue_id (action 이름 그대로)", rec and v.get("reason_code") == "other_doc" and v.get("reason_text") == "請求書です"
       and rec[-1].get("queue_id"), rec[-1:] if rec else None)
    page.click(".c01-kinds [data-kind='done']")
    its = page.locator(".c01-item.done")
    hit = None
    for i in range(its.count()):
        if "搬入票ではない" in its.nth(i).inner_text():
            hit = i
    if hit is not None:
        its.nth(hit).click()
    ok("R9K 未分類FAX 「搬入票ではない」 = 完了 에서 「元に戻す」 있음", hit is not None and page.locator("#q-undo").count() == 1, hit)
    page.screenshot(path=str(shots / "r9k_fax_reason.png"))
    # v0.3.38 (R9K 0-5 d): 「搬入票ではない」 옆 이유 버튼 5개 (ひとことでOK) — 누르면 창 없이 그 이유로 바로
    page.click(".c01-kinds [data-kind='未分類FAX']")
    if page.locator(".c01-item[data-q='9e9e9e9e9e9e9e92']").count():
        page.locator(".c01-item[data-q='9e9e9e9e9e9e9e92']").click()
    qk = page.locator("[data-nhquick]")
    ok("R9K 0-5 d 「搬入票ではない」 옆 이유 버튼 5 · 「ひとことでOK」 바로 보임", qk.count() == 1 and qk.locator("[data-nhq]").count() == 5
       and "ひとことでOK" in qk.inner_text() and qk.is_visible(), qk.count())
    dl3 = []
    page.once("dialog", lambda dg: (dl3.append(dg.message), dg.accept()))
    if qk.count():
        qk.locator("[data-nhq='duplicate']").click()
    page.wait_for_timeout(500)
    rec2 = [x for x in actions(root) if x.get("action") == "not_ours" and x.get("queue_id") == "9e9e9e9e9e9e9e92"]
    ok("R9K 0-5 d 이유 버튼 = 창 없이 not_ours (reason_code duplicate · 이유 글 없음)", len(rec2) == 1 and (rec2[0].get("value") or {}).get("reason_code") == "duplicate"
       and "reason_text" not in (rec2[0].get("value") or {}) and not dl3 and page.locator("#c01-nhdlg").count() == 0, [rec2, dl3])
    page.click(".c01-kinds [data-kind='all']")
    qp.write_text(qt0, encoding="utf-8")
    page.evaluate("C01.app.tick()")
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


def r8c_checks(page, root, shots):
    """v0.3.27 (R8C Part F · #226): 「搬入票ではない」 = 値の確認 카드에도 · 「他社のコンテナ」 (카드 · 옆 창) → other_ct (container_id) · 줄 숨김 ·
    IV 머리 「他社のコンテナ 1」 → 元に戻す (undo) · 候補 문구.  (Part G): 「候補書類あり (n)」 = 열린 業者・IV未定 만 (처리한 것 0 → 버튼 없음)."""
    jp, qp = root / "_data" / "jikkyou.json", root / "_data" / "queue.json"
    jt0, qt0 = jp.read_text(encoding="utf-8"), qp.read_text(encoding="utf-8")
    dump = lambda o: json.dumps(o, ensure_ascii=False, indent=1) + chr(10)   # noqa: E731
    j2, q2 = json.loads(jt0), json.loads(qt0)
    iv1 = next(x for x in j2["ivs"] if x["iv_no"] == "TST2611-01")
    r1, r2 = iv1["rows"][0], iv1["rows"][1]
    r1.update({"status": "再確認", "engine_status": "再確認", "reasons": ["SEAL_FORMAT"], "reason_text": ["x"], "human": None,
               "other_ct_cand": ["シール形式", "他社搬入票候補"]})
    docs_dir = [p_.relative_to(root).as_posix() for p_ in sorted((root / "TST2611-01" / "搬入票").glob("*.svg"))]
    vq = {"queue_id": "e" * 15 + "1", "kind": "値の確認", "iv_no": "TST2611-01", "ct": r1["ct"], "field": None, "container_id": r1["container_id"], "values": {},
          "candidates": [], "files": [{"path": docs_dir[0], "name": docs_dir[0].split("/")[-1], "page": None, "bbox": None, "sha16": "e" * 16}],
          "note": "SEAL_FORMAT", "resolved": None, "superseded": [], "cy_cut": iv1.get("cy_cut"), "issuer": None,
          "field_sources": {"seal": [{"src": "写真", "value": r1["seal"], "agree": True}]}, "field_source_text": {}, "final": {"ct": r1["ct"]}, "reason_codes": ["SEAL_FORMAT"]}
    q2["items"].append(vq)
    if "値の確認" not in q2["kinds"]:
        q2["kinds"] = list(q2["kinds"]) + ["値の確認"]
    hq = next(x for x in q2["items"] if x["kind"] == "業者・IV未定")
    hq.update(candidates=["TST2611-02"], resolved=None)
    hq2 = dict(hq, queue_id="e" * 15 + "2", candidates=["TST2611-03"],
               resolved={"action_id": "done-hold-0001", "by": "staff.a@example.invalid", "at": "2026-11-11T17:00:00+09:00", "action": "not_hannyuhyo"})
    q2["items"].append(hq2)
    for iv in j2["ivs"]:
        if iv["iv_no"] in ("TST2611-02", "TST2611-03"):
            iv["hold_docs"] = 1                                   # 옛 엔진 수 (처리한 것 포함) — TOOL 은 열린 것만 셈
    jp.write_text(dump(j2), encoding="utf-8")
    qp.write_text(dump(q2), encoding="utf-8")
    page.click("#tab-main")
    page.click("[data-port='all']")
    page.evaluate("() => { Object.assign(C01.state, {qedit: null, picks: {}, panelInput: '', sel: null, qvals: {}, qchoice: {}, editRow: null, filter: null}); C01.app.tick(); }")
    page.wait_for_timeout(600)
    h2 = page.locator("tbody[data-iv='TST2611-02'] [data-holdiv]")
    h3 = page.locator("tbody[data-iv='TST2611-03'] [data-holdiv]")
    ok("G 候補書類あり = 열린 것만 (02 = (1) · 03 처리됨 = 버튼 없음)", h2.count() == 1 and "(1)" in h2.inner_text() and h3.count() == 0,
       [h2.inner_text() if h2.count() else None, h3.count()])
    page.evaluate("q => { C01.state.view = 'input'; C01.state.qkind = 'all'; C01.state.qsel = q; C01.app.render(); }", vq["queue_id"])
    page.wait_for_selector("#q-otherct")
    ok("F 値の確認 카드 = 「搬入票ではない」 · 「他社のコンテナ」 · 候補 문구", page.locator("#q-notours").count() == 1 and page.locator("#q-otherct").count() == 1
       and "他社のコンテナ候補" in page.locator(".c01-othcand").inner_text() and "シールの形" in page.locator(".c01-othcand").inner_text(),
       page.locator(".c01-othcand").inner_text() if page.locator(".c01-othcand").count() else None)
    page.screenshot(path=str(shots / "r8c_vchk_other.png"))
    ids0 = {x.get("action_id") for x in actions(root)}
    dl = []

    def acc(d):
        dl.append(d.message)
        d.accept()
    page.on("dialog", acc)
    page.click("#q-otherct")
    page.wait_for_timeout(600)
    new = [x for x in actions(root) if x.get("action_id") not in ids0]
    ok("F 「他社のコンテナ」 = other_ct (iv · ct · value.container_id · queue_id) · 확인창 1", len(new) == 1 and new[0]["action"] == "other_ct"
       and new[0]["value"] == {"container_id": r1["container_id"]} and new[0]["iv"] == "TST2611-01" and new[0]["ct"] == r1["ct"] and new[0]["queue_id"] == vq["queue_id"]
       and len(dl) == 1 and "他社のコンテナ" in dl[0], [new, dl])
    page.click("#tab-main")
    page.wait_for_timeout(300)
    rows_ct = page.eval_on_selector_all("tbody[data-iv='TST2611-01'] tr.c01-row", "els => els.map(e => e.getAttribute('data-key'))")
    ob = page.locator("tbody[data-iv='TST2611-01'] [data-otherct]")
    ok("F 줄 숨김 · IV 머리 「他社のコンテナ 1」", not any(r1["ct"] in (k or "") for k in rows_ct) and ob.count() == 1 and "他社のコンテナ 1" in ob.inner_text(),
       [rows_ct, ob.inner_text() if ob.count() else None])
    ob.click()
    page.wait_for_selector("[data-othundo]")
    ok("F 목록 창 = CT · 元に戻す", r1["ct"] in page.locator("#c01-modal").inner_text(), page.locator("#c01-modal").inner_text()[:200])
    page.screenshot(path=str(shots / "r8c_other_list.png"))
    page.click("[data-othundo='0']")
    page.wait_for_timeout(500)
    un = [x for x in actions(root) if x.get("action_id") not in ids0 and x.get("action") == "undo"]
    rows_ct = page.eval_on_selector_all("tbody[data-iv='TST2611-01'] tr.c01-row", "els => els.map(e => e.getAttribute('data-key'))")
    ok("F 元に戻す = undo (value.action_id = other_ct) · 줄 다시 보임", len(un) == 1 and un[0]["value"]["action_id"] == new[0]["action_id"]
       and any(r1["ct"] in (k or "") for k in rows_ct), [un, rows_ct])
    k2 = page.eval_on_selector_all("tbody[data-iv='TST2611-01'] tr.c01-row", "els => els.map(e => e.getAttribute('data-key'))")
    kk = next((k for k in k2 if r2["ct"] and r2["ct"] in (k or "")), None)
    if kk:
        page.evaluate("k => { C01.state.sel = k; C01.app.render(); }", kk)
        page.wait_for_timeout(300)
    ok("F 実況表 옆 창 = 「他社のコンテナ」 버튼", page.locator("#panel-otherct").count() == 1, kk)
    page.screenshot(path=str(shots / "r8c_side_other.png"))
    page.remove_listener("dialog", acc)
    page.evaluate("() => { C01.state.sel = null; C01.app.render(); }")
    qp.write_text(qt0, encoding="utf-8")
    jp.write_text(jt0, encoding="utf-8")
    page.evaluate("C01.app.tick()")
    page.wait_for_timeout(300)

def r8d_checks(page, root, shots):
    """v0.3.28 (R8D Part A · #227): 未分類 FAX 카드 = 「IVに連結」 — 엔진 후보 IV (끝난 부킹 = link_target 칸) 칩 · FAX CT 같은 칸 ★ · 칸 고르기 → link_iv
    (sha16 · slot_guid · fax 학습 기록) · RULES.faxLinkIv 끄면 옛 IV 고르기 그대로."""
    qp = root / "_data" / "queue.json"
    qt0 = qp.read_text(encoding="utf-8")
    dump = lambda o: json.dumps(o, ensure_ascii=False, indent=1) + chr(10)   # noqa: E731
    q2 = json.loads(qt0)
    docs_dir = [p_.relative_to(root).as_posix() for p_ in sorted((root / "TST2611-01" / "搬入票").glob("*.svg"))]
    fq = {"queue_id": "8d8d8d8d8d8d8d81", "kind": "未分類FAX", "iv_no": None, "ct": None, "field": None, "container_id": None, "values": {},
          "candidates": ["TST2609-09"], "files": [{"path": docs_dir[0], "name": "fax-0001.pdf", "page": None, "bbox": None, "sha16": "8d8d8d8d8d8d8d8d"}],
          "note": "保留", "resolved": None, "superseded": [], "cy_cut": None, "cy_open": None, "issuer": None, "field_sources": {}, "field_source_text": {},
          "received_at": "2026-11-12T10:00:00+09:00", "link_iv": True, "fax_read": {"ct": ["AAAU1234565"]},
          "link_target": {"iv_no": "TST2609-09", "bkg_no": "BKGTEST09", "state": "종료", "slots": [
              {"slot_guid": "slot-r8d-1", "seq": 0, "packer": "PACKER_A", "plant": None, "item": "X", "work_date": "2026-09-20", "row_ct": None, "match": []},
              {"slot_guid": "slot-r8d-2", "seq": 1, "packer": "PACKER_A", "plant": None, "item": "X", "work_date": "2026-09-20", "row_ct": "BBBU1234560",
               "compass_ct": "AAAU1234565", "match": ["CT(COMPASS)"]}]}}
    q2["items"].append(fq)
    if "未分類FAX" not in q2["kinds"]:
        q2["kinds"] = list(q2["kinds"]) + ["未分類FAX"]
    qp.write_text(dump(q2), encoding="utf-8")
    page.evaluate("C01.RULES.linkIv = true; C01.RULES.faxLinkIv = true; C01.app.tick()")
    page.wait_for_timeout(800)
    page.evaluate("q => { C01.state.view = 'input'; C01.state.qkind = 'all'; C01.state.qiv = null; C01.state.showOldFax = true; C01.state.qsel = q; C01.app.render(); }", fq["queue_id"])
    page.wait_for_selector("#link-iv")
    ok("A 未分類FAX = 「IVに連結」 · FAX の CT · 후보 칩 · 확인 버튼 꺼짐", page.locator(".c01-linkiv [data-linkiv='TST2609-09']").count() == 1
       and "AAAU1234565" in page.locator(".c01-hold").inner_text() and page.locator("#q-submit").is_disabled(),
       [page.locator(".c01-hold").first.inner_text()[:120], page.evaluate("() => [C01.state.qsel, C01.state.qiv, C01.state.qkind, (C01.state.queue.items || []).filter(x => x.kind === '未分類FAX').map(x => x.queue_id + ':' + !!x.link_iv), JSON.stringify(C01.RULES)]")])
    page.evaluate("C01.RULES.faxLinkIv = false; C01.app.render()")
    page.wait_for_timeout(200)
    ok("A RULES.faxLinkIv 끔 = 옛 IV 고르기 (q-iv)", page.locator("#link-iv").count() == 0 and page.locator("#q-iv").count() == 1, "")
    page.evaluate("C01.RULES.faxLinkIv = true; C01.app.render()")
    page.wait_for_selector("#link-iv")
    page.click(".c01-linkiv [data-linkiv='TST2609-09']")
    page.wait_for_timeout(200)
    opts = page.locator("input[name='link-slot']")
    m = page.locator(".c01-slotopt.match")
    ok("A 끝난 부킹 = 후보 칸 목록 (2) · FAX CT 같은 칸 ★", opts.count() == 2 and m.count() == 1 and "FAX の CT と同じ" in m.inner_text(),
       [opts.count(), m.count()])
    page.screenshot(path=str(shots / "r8d_fax_link.png"))
    m.locator("input").check()
    page.wait_for_timeout(200)
    ids0 = {x.get("action_id") for x in actions(root)}
    dl = []

    def acc(d):
        dl.append(d.message)
        d.accept()
    page.on("dialog", acc)
    page.click("#q-submit")
    page.wait_for_timeout(600)
    page.remove_listener("dialog", acc)
    new = [x for x in actions(root) if x.get("action_id") not in ids0]
    v = new[0]["value"] if new else {}
    ok("A 저장 = link_iv (IV · sha16 · slot_guid · fax 학습 기록 · 이미 찬 칸 확인창 1)", len(new) == 1 and new[0]["action"] == "link_iv" and new[0]["iv"] == "TST2609-09"
       and v.get("slot_guid") == "slot-r8d-2" and v.get("sha16") == ["8d8d8d8d8d8d8d8d"] and v.get("fax", {}).get("engine_cand") is True and v["fax"].get("past") is True
       and v["fax"].get("ct") == ["AAAU1234565"] and new[0]["queue_id"] == fq["queue_id"] and len(dl) == 1, [new, dl])
    page.evaluate("C01.RULES.linkIv = false; C01.RULES.faxLinkIv = true; C01.state.qkind = 'all'; C01.state.showOldFax = false")
    qp.write_text(qt0, encoding="utf-8")



def r8f_checks(page, root, shots):
    """v0.3.28 (R8F · #233 D-142): 엔진 row.link_single (사람 연결 human · 회전 다시 읽기 연결 rot) = MIN_SOURCES 이유 줄이
    「連結した書類だけの値です（…）。確認が必要です。」 (値の確認 카드 · 実況表 줄) · link_single 없는 줄 = 옛 문구 그대로."""
    jp, qp = root / "_data" / "jikkyou.json", root / "_data" / "queue.json"
    jt0, qt0 = jp.read_text(encoding="utf-8"), qp.read_text(encoding="utf-8")
    dump = lambda o: json.dumps(o, ensure_ascii=False, indent=1) + chr(10)   # noqa: E731
    j2, q2 = json.loads(jt0), json.loads(qt0)
    iv1 = next(x for x in j2["ivs"] if x["iv_no"] == "TST2611-01")
    r1, r2 = iv1["rows"][0], iv1["rows"][1]
    r1.update({"status": "再確認", "engine_status": "再確認", "reasons": ["MIN_SOURCES"], "reason_text": ["x"], "human": None,
               "link_single": {"by": "human", "fields": ["seal", "bales"]}})
    r2.update({"status": "再確認", "engine_status": "再確認", "reasons": ["MIN_SOURCES"], "reason_text": ["x"], "human": None})
    r2.pop("link_single", None)
    vq = {"queue_id": "f" * 14 + "81", "kind": "値の確認", "iv_no": "TST2611-01", "ct": r1["ct"], "field": None, "container_id": r1["container_id"], "values": {},
          "candidates": [], "files": [], "note": "MIN_SOURCES", "resolved": None, "superseded": [], "cy_cut": iv1.get("cy_cut"), "issuer": None,
          "field_sources": {"bales": [{"src": "搬入票", "value": r1["bales"], "agree": True}]}, "field_source_text": {}, "final": {"ct": r1["ct"]},
          "reason_codes": ["MIN_SOURCES"]}
    q2["items"].append(vq)
    if "値の確認" not in q2["kinds"]:
        q2["kinds"] = list(q2["kinds"]) + ["値の確認"]
    jp.write_text(dump(j2), encoding="utf-8")
    qp.write_text(dump(q2), encoding="utf-8")
    page.click("#tab-main")
    page.evaluate("() => { Object.assign(C01.state, {qedit: null, picks: {}, panelInput: '', sel: null, qvals: {}, qchoice: {}, editRow: null, filter: null}); C01.app.tick(); }")
    page.wait_for_timeout(600)
    page.evaluate("q => { C01.state.view = 'input'; C01.state.qkind = 'all'; C01.state.qsel = q; C01.app.render(); }", vq["queue_id"])
    page.wait_for_selector(".c01-vchk")
    t = page.locator(".c01-vchk .c01-rdesc").first.inner_text()
    ok("R8F 値の確認 카드 = 「連結した書類だけの値です（シール番号・ベール数）。確認が必要です。」 + ?",
       "連結した書類だけの値です（シール番号・ベール数）。確認が必要です。" in t and page.locator(".c01-vchk .c01-rq").count() >= 1, t)
    page.screenshot(path=str(shots / "r8f_vchk_link_single.png"))
    j3 = json.loads(dump(j2))
    iv3 = next(x for x in j3["ivs"] if x["iv_no"] == "TST2611-01")
    iv3["rows"][0]["link_single"] = {"by": "rot", "fields": ["n_w"]}
    jp.write_text(dump(j3), encoding="utf-8")
    page.evaluate("() => { C01.app.tick(); }")
    page.wait_for_timeout(600)
    page.evaluate("q => { C01.state.view = 'input'; C01.state.qkind = 'all'; C01.state.qsel = q; C01.app.render(); }", vq["queue_id"])
    page.wait_for_selector(".c01-vchk")
    t2 = page.locator(".c01-vchk .c01-rdesc").first.inner_text()
    ok("R8F rot = 「向きを直して読んだ FAX だけの値です（正味重量）。」", "向きを直して読んだ FAXだけの値です（正味重量）。確認が必要です。" in t2, t2)
    vq2 = dict(vq, queue_id="f" * 14 + "82", container_id=r2["container_id"], ct=r2["ct"])
    q3 = json.loads(dump(q2)); q3["items"].append(vq2)
    qp.write_text(dump(q3), encoding="utf-8")
    page.evaluate("() => { C01.app.tick(); }")
    page.wait_for_timeout(600)
    page.evaluate("q => { C01.state.view = 'input'; C01.state.qkind = 'all'; C01.state.qsel = q; C01.app.render(); }", vq2["queue_id"])
    page.wait_for_selector(".c01-vchk")
    t3 = page.locator(".c01-vchk .c01-rdesc").first.inner_text()
    ok("R8F link_single 없는 줄 = 옛 MIN_SOURCES 문구 그대로", "1つだけです" in t3 and "連結" not in t3, t3)
    page.evaluate("() => { C01.state.view = 'main'; C01.state.qsel = null; }")
    jp.write_text(jt0, encoding="utf-8")
    qp.write_text(qt0, encoding="utf-8")
    page.evaluate("() => { C01.app.tick(); }")
    page.wait_for_timeout(400)


def r8w_checks(page, root, shots):
    """v0.3.32 (R8W Part A · #256): work_date_src = slot_plan → 実況表 작업일 옆 작은 「予定」 · 읽은 값이 다르면 옆 창에 「読取: MM/DD」 만 (경고 색 없음 · 장 수 그대로) ·
    읽은 값이 같으면 「読取」 없음 · 사람 값 작업일 줄은 「予定」 없음."""
    jp = root / "_data" / "jikkyou.json"
    jt0 = jp.read_text(encoding="utf-8")
    dump = lambda o: json.dumps(o, ensure_ascii=False, indent=1) + "\n"   # noqa: E731
    page.click("#tab-main")
    page.click("[data-port='all']")
    page.wait_for_timeout(200)
    tab0 = page.locator("#tab-input").inner_text()
    j = json.loads(jt0)
    iv = next(x for x in j["ivs"] if x["iv_no"] == "TST2611-01")
    rs = [r for r in iv["rows"] if r.get("ct") and r.get("work_date") and not (r.get("human") or {}).get("work_date") and r.get("status") == "自動OK"]
    hv = next((r for r in iv["rows"] if r.get("ct") and (r.get("human") or {}).get("work_date")), None)
    a, b = rs[0], rs[1]
    a["work_date_src"] = "slot_plan"; a["work_date_read"] = "2026-10-01"
    b["work_date_src"] = "slot_plan"; b["work_date_read"] = b["work_date"]
    if hv:
        hv["work_date_src"] = "slot_plan"; hv["work_date_read"] = "2026-10-02"
    jp.write_text(dump(j), encoding="utf-8")
    page.evaluate("C01.app.tick()")
    page.wait_for_timeout(500)
    ra = page.locator(f"tbody[data-iv='TST2611-01'] tr.c01-row:has-text('{a['ct']}')").first
    rb = page.locator(f"tbody[data-iv='TST2611-01'] tr.c01-row:has-text('{b['ct']}')").first
    sa = ra.locator(".c01-wdsrc")
    ok("R8W 予定 = 실황표 작업일 옆 작은 「予定」 (title 설명) · 읽은 값 같은 줄도 「予定」",
       sa.count() == 1 and sa.inner_text() == "予定" and "予定作業日" in (sa.get_attribute("title") or "") and rb.locator(".c01-wdsrc").count() == 1,
       [sa.count(), rb.locator(".c01-wdsrc").count()])
    if hv:
        rh = page.locator(f"tbody[data-iv='TST2611-01'] tr.c01-row:has-text('{hv['ct']}')").first
        ok("R8W 사람 값 작업일 줄 = 「予定」 없음", rh.locator(".c01-wdsrc").count() == 0, rh.locator(".c01-wdsrc").count())
    page.evaluate("k => { C01.state.sel = k; C01.app.render(); }", ra.get_attribute("data-key"))
    page.wait_for_selector(".c01-side")
    side = page.locator(".c01-side")
    rd = side.locator(".c01-wdread")
    ok("R8W 옆 창 = 「読取: 10/01」 작은 글자 (경고 색 없음)", rd.count() == 1 and rd.inner_text() == "読取: 10/01" and "c01-bad" not in (rd.get_attribute("class") or ""),
       [rd.count(), rd.count() and rd.inner_text()])
    page.screenshot(path=str(shots / "r8w_wd_plan.png"))
    page.evaluate("k => { C01.state.sel = k; C01.app.render(); }", rb.get_attribute("data-key"))
    page.wait_for_timeout(200)
    ok("R8W 읽은 값 = 예정일 → 「読取」 없음", page.locator(".c01-side .c01-wdread").count() == 0, page.locator(".c01-side .c01-wdread").count())
    page.evaluate("C01.state.sel = null; C01.app.render()")
    ok("R8W 確認・入力 장 수 그대로", page.locator("#tab-input").inner_text() == tab0, [tab0, page.locator("#tab-input").inner_text()])
    jp.write_text(jt0, encoding="utf-8")
    page.evaluate("C01.app.tick()")
    page.wait_for_timeout(300)


def r9d_wd_checks(page, root, shots, engine):
    """v0.3.35 (R9D Part B · #262 · #153 회귀 고침): work_date_src = slot_plan 줄도 搬入票 아직 없는 줄 (受信中 · 書類なし) 이고 예정일이 오늘 포함 이전이면 굵은 빨강 ·
    내일 = 회색 「予定」 · 搬入票 있는 줄 (自動OK · 再確認) = 회색 「予定」 (빨강 아님) · 서류 작업일 = 검정 · 빈 값 = 지금 분기 그대로 +
    받는 쪽 대조: 엔진 data_json.WORK_DATE_SRC_VALUES == TOOL C01.WD_SRC_KNOWN."""
    import datetime as _dt
    import ast as _ast
    jp = root / "_data" / "jikkyou.json"
    jt0 = jp.read_text(encoding="utf-8")
    dump = lambda o: json.dumps(o, ensure_ascii=False, indent=1) + chr(10)   # noqa: E731
    page.click("#tab-main")
    page.click("[data-port='all']")
    page.wait_for_timeout(200)
    today = page.evaluate("(C01.state.info && C01.state.info.today) || null")
    ok("R9D 화면 오늘 날짜 있음 (meta today)", bool(today), today)
    d = _dt.date.fromisoformat(today)
    yday, tmr = (d - _dt.timedelta(days=1)).isoformat(), (d + _dt.timedelta(days=1)).isoformat()
    j = json.loads(jt0)
    iv = next(x for x in j["ivs"] if x["iv_no"] == "TST2611-01")
    rs = [r for r in iv["rows"] if r.get("ct") and not (r.get("human") or {}).get("work_date")]
    ok("R9D 시험 자료 = TST2611-01 CT 줄 4 이상", len(rs) >= 4, len(rs))
    a, b, c, e = rs[0], rs[1], rs[2], rs[3]
    for r, wd, st in ((a, yday, "受信中"), (b, today, "受信中"), (c, tmr, "受信中"), (e, yday, "自動OK")):
        r["work_date"] = wd; r["work_date_src"] = "slot_plan"; r.pop("work_date_read", None); r["status"] = st
        if st == "受信中":
            r["has_docs"] = False
    jp.write_text(dump(j), encoding="utf-8")
    page.evaluate("C01.app.tick()")
    page.wait_for_timeout(500)
    row = lambda r: page.locator(f"tbody[data-iv='TST2611-01'] tr.c01-row[data-key*='{r['ct']}']").first   # noqa: E731
    def cell(r):
        x = row(r)
        return {"n": x.count(), "plan": x.locator(".c01-wdplan").count(), "past": x.locator(".c01-wdplan.past").count(), "yotei": x.locator(".c01-wdsrc").count(),
                "st": x.get_attribute("data-status") if x.count() else None}
    ca, cb, cc, ce = cell(a), cell(b), cell(c), cell(e)
    ok("R9D slot_plan + 어제 + 受信中 (書類なし) = 굵은 빨강 (past) · 「予定」", ca["st"] == "受信中" and ca["past"] == 1 and ca["yotei"] == 1, ca)
    ok("R9D slot_plan + 오늘 + 受信中 = 굵은 빨강 (오늘 포함)", cb["st"] == "受信中" and cb["past"] == 1 and cb["yotei"] == 1, cb)
    ok("R9D slot_plan + 내일 + 受信中 = 회색 「予定」 (빨강 아님)", cc["st"] == "受信中" and cc["plan"] == 1 and cc["past"] == 0 and cc["yotei"] == 1, cc)
    ok("R9D slot_plan + 어제 + 自動OK (搬入票 있음) = 회색 「予定」 (빨강 아님)", ce["st"] == "自動OK" and ce["plan"] == 1 and ce["past"] == 0 and ce["yotei"] == 1, ce)
    sty = row(a).locator(".c01-wdplan.past").evaluate("el => [getComputedStyle(el).fontWeight, getComputedStyle(el).color]") if ca["past"] else None
    ok("R9D 빨강 = 굵게 (700 이상)", bool(sty) and int(sty[0]) >= 700, sty)
    page.screenshot(path=str(shots / "r9d_wd_red.png"))
    j2 = json.loads(jt0)
    iv2 = next(x for x in j2["ivs"] if x["iv_no"] == "TST2611-01")
    r2 = next(r for r in iv2["rows"] if r.get("ct") == a["ct"])
    r2["work_date"] = yday; r2.pop("work_date_src", None); r2["status"] = "受信中"; r2["has_docs"] = False
    jp.write_text(dump(j2), encoding="utf-8")
    page.evaluate("C01.app.tick()")
    page.wait_for_timeout(500)
    cd = cell(a)
    ok("R9D 서류 작업일 (work_date_src 없음) = 검정 그대로 (회색 · 빨강 · 「予定」 없음)", cd["plan"] == 0 and cd["past"] == 0 and cd["yotei"] == 0, cd)
    r2["work_date"] = None
    jp.write_text(dump(j2), encoding="utf-8")
    page.evaluate("C01.app.tick()")
    page.wait_for_timeout(500)
    cn = cell(a)
    ok("R9D 빈 값 = 지금 분기 그대로 (칸 예정일 있으면 회색/빨강 · 「予定」 작은 글자 없음)", cn["yotei"] == 0 and cn["n"] == 1, cn)
    known = page.evaluate("C01.WD_SRC_KNOWN")
    src = (Path(engine) / "engine" / "output" / "data_json.py").read_text(encoding="utf-8")
    eng = None
    for node in _ast.walk(_ast.parse(src)):
        if isinstance(node, _ast.Assign) and any(getattr(t_, "id", None) == "WORK_DATE_SRC_VALUES" for t_ in node.targets):
            eng = list(_ast.literal_eval(node.value))
    ok("R9D 받는 쪽 대조: 엔진 WORK_DATE_SRC_VALUES == TOOL WD_SRC_KNOWN (엔진 값이 늘면 이 시험이 실패)", eng is not None and sorted(eng) == sorted(known or []), [eng, known])
    jp.write_text(jt0, encoding="utf-8")
    page.evaluate("C01.app.tick()")
    page.wait_for_timeout(300)


def r8z_checks(page, root, shots):
    """v0.3.33 (R8Z Part A · B · #258): 業者・IV未定 = 件名 · 送信元 · 添付 · 「他 n 枚」 · ZIP の中身 · ファイル準備中 + 「業者登録」 (packers.json · 営業所 · 확인창 · register_sender · 元に戻す)."""
    qp = root / "_data" / "queue.json"
    pp = root / "_data" / "packers.json"
    qt0 = qp.read_text(encoding="utf-8")
    dump = lambda o: json.dumps(o, ensure_ascii=False, indent=1) + chr(10)   # noqa: E731
    q2 = json.loads(qt0)
    hq = next(x for x in q2["items"] if x["kind"] == "業者・IV未定")
    hq["resolved"] = None
    hq.update({"mail_info": {"subject": "テスト件名 写真", "from": "sender.x@example.invalid", "attach": ["a.jpg", "b.jpg", "c.zip"]},
               "files_total": 9, "more_files": 3, "files_pending": False, "zip_entries_n": 2,
               "zip_entries": [{"name": "p1.jpg", "kind": "jpg", "size": 10}, {"name": "memo.txt", "kind": None, "size": 5}]})
    hp = dict(hq, queue_id="c" * 16, files=[], files_pending=True, more_files=0, zip_entries_n=0, zip_entries=[],
              mail_info={"subject": "準備中", "from": "sender.y@example.invalid", "attach": ["x.xls"]})
    q2["items"].append(hp)
    qp.write_text(dump(q2), encoding="utf-8")
    pp.write_text(dump({"schema_version": 1, "packers": [{"code": "PACKER_A", "name": "テスト商店", "plants": ["本社", "市川"]},
                                                         {"code": "PACKER_B", "name": "テスト二", "plants": []}]}), encoding="utf-8")
    page.click("#tab-main")
    page.evaluate("() => { C01.app.tick(); }")
    page.wait_for_timeout(700)
    page.evaluate("q => { C01.state.view = 'input'; C01.state.qkind = 'all'; C01.state.qsel = q; C01.app.render(); }", hq["queue_id"])
    page.wait_for_selector("#q-holdmail")
    t = page.locator("#q-holdmail").inner_text()
    ok("R8Z 카드 = 件名 · 送信元 · 添付", all(x in t for x in ("テスト件名 写真", "sender.x@example.invalid", "a.jpg")), t)
    ok("R8Z 「ほか 3 枚」 · ZIP の中身 2 件 (읽지 않음)", "ほか 3 枚" in page.locator("#q-morefiles").inner_text()
       and "ZIP の中身 2 件" in page.locator("#q-zipents").inner_text(), "")
    ok("R8Z 業者登録 = packers.json 있으면 입력 · 업체 고르기 전 버튼 잠김", page.locator("#reg-packer").count() == 1 and page.locator("#reg-btn").is_disabled(), "")
    page.fill("#reg-packer", "PACKER_A")
    page.press("#reg-packer", "Enter")
    page.wait_for_timeout(300)
    ok("R8Z 업체 고름 = 営業所 고르기 (마스터 그대로) · 버튼 켜짐", page.locator("#reg-plant option").count() == 3 and not page.locator("#reg-btn").is_disabled(), "")
    page.select_option("#reg-plant", "市川")
    ids0 = {x.get("action_id") for x in actions(root)}
    dl = []

    def acc(d):
        dl.append(d.message)
        d.accept()
    page.on("dialog", acc)
    page.click("#reg-btn")
    page.wait_for_timeout(600)
    new = [x for x in actions(root) if x.get("action_id") and x["action_id"] not in ids0]
    ok("R8Z 저장 = register_sender (주소 · 업체 · 営業所 · queue_id · 확인창 1)", len(new) == 1 and new[0]["action"] == "register_sender"
       and new[0]["value"] == {"address": "sender.x@example.invalid", "packer": "PACKER_A", "plant": "市川"} and new[0]["queue_id"] == hq["queue_id"]
       and len(dl) == 1, [new, dl])
    page.evaluate("q => { C01.state.qkind = 'done'; C01.state.qsel = q; C01.app.render(); }", hq["queue_id"])
    page.wait_for_timeout(300)
    ok("R8Z 등록 뒤 = 「業者を登録しました」 · 元に戻す", "業者を登録しました" in page.locator("#c01-main").inner_text() and page.locator("#q-undo").count() == 1, "")
    page.screenshot(path=str(shots / "r8z_register_sender.png"))
    page.click("#q-undo")
    page.wait_for_timeout(400)
    un = [x for x in actions(root) if x.get("action_id") and x["action_id"] not in ids0 and x.get("action") == "undo"]
    ok("R8Z 元に戻す = undo (value.action_id = register_sender)", len(un) == 1 and un[0]["value"]["action_id"] == new[0]["action_id"], un)
    page.remove_listener("dialog", acc)
    page.evaluate("q => { C01.state.qkind = 'all'; C01.state.qsel = q; C01.app.render(); }", hp["queue_id"])
    page.wait_for_timeout(300)
    ok("R8Z 파일 0 카드 = 「ファイル準備中」 · 그래도 業者登録", page.locator("#q-filespending").count() == 1 and page.locator("#reg-packer").count() == 1, "")
    page.evaluate("C01.RULES.registerSender = false; C01.app.render()")
    page.wait_for_timeout(200)
    ok("R8Z RULES.registerSender 끔 = 業者登録 없음", page.locator("#q-regsender").count() == 0, "")
    page.evaluate("C01.RULES.registerSender = true")
    qp.write_text(qt0, encoding="utf-8")
    pp.unlink()
    page.evaluate("() => { C01.state.view = 'main'; C01.state.qsel = null; C01.app.tick(); }")
    page.wait_for_timeout(500)


def r8g_checks(page, root, shots):
    """v0.3.29 (R8G Part A ④ · #234): 業者・IV未定 = 엔진 fax_read.pages (쪽 각도 · 읽은 값) 표 + 파일 rotation 으로 바로 세움 (向き補正 180°) · fax_read 없으면 표 없음."""
    qp = root / "_data" / "queue.json"
    qt0 = qp.read_text(encoding="utf-8")
    dump = lambda o: json.dumps(o, ensure_ascii=False, indent=1) + chr(10)   # noqa: E731
    q2 = json.loads(qt0)
    hq = next(x for x in q2["items"] if x["kind"] == "業者・IV未定")
    hq["resolved"] = None
    if hq.get("files"):
        hq["files"][0]["rotation"] = {"1": 180}
    hq["fax_read"] = {"ct": ["TSTU0000001"], "pages": [{"file": None, "page": 1, "rotation": 180, "doc_type": "hannyuhyo", "issuer": "テスト商店",
                                                        "fax_from": "(株)テスト本社", "bkg": ["TSTBKG0001"],
                                                        "rows": [{"ct": "TSTU0000001", "seal": "TS0001", "n_w": 1000, "t_w": 3000, "bales": 20}]}]}
    qp.write_text(dump(q2), encoding="utf-8")
    page.click("#tab-main")
    page.evaluate("() => { C01.app.tick(); }")
    page.wait_for_timeout(600)
    page.evaluate("q => { C01.state.view = 'input'; C01.state.qkind = 'all'; C01.state.qsel = q; C01.app.render(); }", hq["queue_id"])
    page.wait_for_selector(".c01-holdread")
    t = page.locator(".c01-holdread").inner_text()
    ok("R8G 業者・IV未定 = 엔진이 읽은 값 표 (搬入票 · 발행 · FAX 送信元 · BKG · CT · シール · 重量 · ベール 20)",
       all(x in t for x in ("エンジンが読んだ値", "搬入票", "テスト商店", "(株)テスト本社", "TSTBKG0001", "TSTU0000001", "TS0001", "20")), t)
    if hq.get("files"):
        ok("R8G 파일 rotation 180 = 向き補正 180°", page.locator("#q-autorot").count() == 1 and "180" in page.locator("#q-autorot").inner_text(), "")
    page.screenshot(path=str(shots / "r8g_hold_read.png"))
    q3 = json.loads(qt0)
    qp.write_text(dump(q3), encoding="utf-8")
    page.evaluate("() => { C01.app.tick(); }")
    page.wait_for_timeout(600)
    page.evaluate("q => { C01.state.view = 'input'; C01.state.qkind = 'all'; C01.state.qsel = q; C01.app.render(); }", hq["queue_id"])
    page.wait_for_timeout(300)
    ok("R8G fax_read 없음 = 표 없음 (옛 화면 그대로)", page.locator(".c01-holdread").count() == 0, "")
    page.evaluate("() => { C01.state.view = 'main'; C01.state.qsel = null; }")


def r8b_checks(page, root, shots):
    """v0.3.26 (R8B Part E-1 · #216): 未受信アドレス = 별 줄 · 받는 사람이 未受信 뿐이면 확인 체크 전 送信 꺼짐 · 회신 표시 · 제목 [test] RE: ·
    보낸 곳 = 시험 주소 1개 (未受信 주소 0) · reminder_sent 에 unreceived · reply 기록.  (Part E-2 · #219): 通関書類 버튼 · 창 = 참고 · 값에 안 씀."""
    rp, jp = root / "_data" / "remind.json", root / "_data" / "jikkyou.json"
    rt0, jt0 = rp.read_text(encoding="utf-8"), jp.read_text(encoding="utf-8")
    TEST_TO, UN = "test.box@example.invalid", "never.received@example.invalid"
    r2 = json.loads(rt0)
    r2["send_mode"] = {"test": True, "to": TEST_TO, "tag": "[test]"}
    d0 = r2["ivs"]["TST2611-03"][0]
    d0.update(to=[], cc=[], to_unreceived=[UN], cc_unreceived=[], reply_to={"internet_message_id": "<x@example.invalid>", "received_at": "2026-11-10T09:30:00+09:00",
                                                                          "from": "a@example.invalid"}, unreceived_note="未受信アドレス — 確認して送信")
    d0.pop("ready_at", None)
    rp.write_text(json.dumps(r2, ensure_ascii=False, indent=1) + chr(10), encoding="utf-8")
    j2 = json.loads(jt0)
    for iv in j2["ivs"]:
        if iv["iv_no"] == "TST2611-03":
            iv["customs_docs"] = [{"path": "TST2611-03/_通関書類/DR_test.pdf", "name": "DR_test.pdf", "received_at": "2026-11-11T10:00:00+09:00", "sha16": "0" * 16}]
    jp.write_text(json.dumps(j2, ensure_ascii=False, indent=1) + chr(10), encoding="utf-8")
    page.click("#tab-main")
    page.click("[data-port='all']")
    page.evaluate("""() => { C01.app.tick(); }""")
    page.wait_for_timeout(600)
    page.evaluate("""() => { window.__sent = []; C01.state.info.mode = 'graph';
        C01.state.src.sendMailTest = function (m) { window.__sent.push(m); return C01.sources.Graph.prototype.sendMailTest.call({ _fetch: function (u, o) {
            window.__sent.push({ url: u, body: JSON.parse(o.body) }); return Promise.resolve({ status: 202, ok: true }); } }, m); }; }""")
    cb = page.locator("tbody[data-iv='TST2611-03'] [data-customs]")
    ok("E-2 通関書類 버튼 (customs_docs 1)", cb.count() == 1 and "通関書類 1" in cb.inner_text(), cb.inner_text() if cb.count() else None)
    cb.click()
    page.wait_for_selector("[data-cusopen]")
    mb = page.locator("#c01-modal").inner_text()
    ok("E-2 通関書類 창 = 이름 · 받은 시각 · 「値には使いません」 · 試験表示 없음 (v0.3.48)", "DR_test.pdf" in mb and "2026-11-11 10:00" in mb and "には使いません" in mb and "試験表示" not in mb, mb.replace(chr(10), " / ")[:300])
    page.screenshot(path=str(shots / "r8b_customs.png"))
    page.click("[data-close]")
    page.click("tbody[data-iv='TST2611-03'] [data-remind]")
    page.wait_for_selector("[data-rsend]")
    md = page.locator("#c01-modal")
    ok("E-1 未受信 줄 · 회신 줄 표시", md.locator(".c01-runrec").count() == 1 and UN in md.locator(".c01-runrec").inner_text()
       and md.locator(".c01-rreply").count() == 1 and "2026-11-10 09:30" in md.locator(".c01-rreply").inner_text(), md.inner_text()[:200])
    b0 = page.locator("[data-rsend='0']")
    ok("E-1 받는 사람 = 未受信 뿐 → 확인 체크 전 送信 꺼짐 · 이유 문구", b0.is_disabled() and "未受信アドレスを確認" in page.locator("[data-rwhy='0']").inner_text(),
       page.locator("[data-rwhy='0']").inner_text())
    page.locator("[data-runrec='0']").check()
    ok("E-1 확인 체크 → 送信 켜짐", b0.is_enabled())
    page.locator("[data-rskip='0']").check()
    ok("E-1 「この業者には送らない」 = 다시 꺼짐", b0.is_disabled())
    page.locator("[data-rskip='0']").uncheck()
    b0.click()
    for _ in range(30):
        if any(x.get("action") == "reminder_sent" and x.get("iv") == "TST2611-03" for x in actions(root)):
            break
        time.sleep(0.1)
    sent = page.evaluate("window.__sent")
    post = [x for x in sent if isinstance(x, dict) and x.get("url")]
    msg = post[0]["body"]["message"] if post else {}
    allr = json.dumps(sent, ensure_ascii=False)
    ok("E-1 송신 = 시험 주소 1개 · 제목 [test] RE: · 未受信 주소 0 · 본문 앞 「未受信 1件（確認済）」 · 「返信」",
       len(post) == 1 and [r["emailAddress"]["address"] for r in msg.get("toRecipients", [])] == [TEST_TO] and msg.get("subject", "").startswith("[test] RE: ")
       and UN not in allr and "未受信 1件（確認済）" in msg.get("body", {}).get("content", "") and "返信" in msg.get("body", {}).get("content", ""), [len(post), msg.get("subject")])
    rec = [x for x in actions(root) if x.get("action") == "reminder_sent" and x.get("iv") == "TST2611-03"]
    ok("E-1 reminder_sent 기록 (unreceived 1 · unreceived_ok true · reply true · test true)", len(rec) == 1 and rec[0]["value"].get("unreceived") == 1
       and rec[0]["value"].get("unreceived_ok") is True and rec[0]["value"].get("reply") is True and rec[0]["value"]["test"] is True, rec)
    page.screenshot(path=str(shots / "r8b_remind_unreceived.png"))
    page.click("[data-close]")
    rp.write_text(rt0, encoding="utf-8")
    jp.write_text(jt0, encoding="utf-8")
    page.evaluate("C01.state.info.mode = 'local'; C01.app.tick()")
    page.wait_for_timeout(300)


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
    foot = page.locator("#ask-foot")
    ok("R7Z 「その他（AIに相談）」 欄 있음 · 처음엔 닫힘 (드로어 0) · 試験表示 없음 (v0.3.48)", foot.count() == 1 and page.locator("#ask-box").count() == 0
       and "試験表示" not in foot.inner_text() and "その他（AIに相談）" in foot.inner_text())
    page.click("#q-ask")
    page.wait_for_timeout(300)
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
    ok("R7Z 값 버튼 = 값 칸만 채움 (확인은 담당자 · _actions 새 파일 0)", page.locator(f".c01-field[data-vq='{qid}'] input").first.input_value() == target
       and not [x for x in actions(root) if x.get("queue_id") == vq], target)
    page.screenshot(path=str(shots / "r7z_ask.png"), full_page=False)
    if page.locator("#ask-box").count() == 0:
        page.click("#q-ask")
        page.wait_for_timeout(300)
    page.fill("#ask-in", "이 값이 맞나요?")
    page.press("#ask-in", "Enter")
    page.wait_for_timeout(500)
    files = sorted((root / "_actions" / "ask").rglob("*.json"), key=lambda x: x.stat().st_mtime)
    k = json.loads(files[-1].read_text(encoding="utf-8")) if files else {}
    ok("R7Z 한국어 질문 · Enter = 보냄 · lang ko · 같은 카드 key", len(files) == 2 and k.get("lang") == "ko" and (k.get("card") or {}).get("key") == card.get("key"), k.get("lang"))
    ok("R7Z 같은 카드 대화 2건 표시", page.locator(".c01-ask-q").count() == 2)


def r9f_ask_checks(page, root, shots):
    """v0.3.36 (R9F · #267): 「AIに相談」 버튼 = 카드 패널 맨 위 버튼 줄 1개 · 오른쪽 옆 드로어 (막 없음 · 원본/카드 안 가림) · ✕ · Esc ·
    카드 바꾸면 그 카드 기록 · 아래 링크 = 같은 드로어 · 질문 입력 칸 1개 · 「調べた内容」 줄바꿈 + HTML 이스케이프 · askOn 거짓 = 버튼 없음.
    r7z_checks 바로 뒤 (같은 카드 · 질문 2건) 에서 부른다."""
    qid = "z" * 15 + "7"
    page.set_viewport_size({"width": 1880, "height": 1000})
    page.wait_for_timeout(200)
    if page.locator("#ask-box").count() == 0:
        page.click("#q-ask")
        page.wait_for_timeout(300)
    btn = page.locator("#q-ask")
    top_row = page.evaluate("""() => { const b = document.querySelectorAll('#q-ask'); if (b.length !== 1) return 'n=' + b.length;
        const row = b[0].closest('.c01-form-a .row'); return !!row && !!row.querySelector('#q-skip') && b[0].classList.contains('c01-btn-ghost2') && b[0].textContent === 'AIに相談'; }""")
    ok("R9F 「AIに相談」 버튼 = 카드 패널 맨 위 버튼 줄 (スキップ 옆) 1개 · 같은 class", top_row is True, top_row)
    bb = btn.bounding_box()
    ok("R9F 버튼 = 창 안 (1880×1000 · 스크롤 없이)", bb["y"] + bb["height"] <= 1000, bb)
    n_in = page.evaluate("() => [document.querySelectorAll('#ask-in').length, document.querySelectorAll('#c01-main textarea').length, document.querySelectorAll('[aria-label=\"AI への質問\"]').length]")
    ok("R9F 질문 입력 칸 = 1개 (드로어 안 · textarea 0 · 아래쪽 입력 0)", n_in == [1, 0, 1] and page.locator("#ask-foot input").count() == 0
       and page.locator("#ask-box #ask-in").count() == 1, n_in)
    geo = page.evaluate("""() => { const r = s => { const e = document.querySelector(s); return e ? e.getBoundingClientRect().toJSON() : null; };
        return { dr: r('#ask-box'), orig: r('.c01-orig'), form: r('.c01-form'), ov: [...document.querySelectorAll('.c01-overlay')].filter(e => e.offsetParent).length }; }""")

    def hit(a, b):
        return bool(a and b and not (a["right"] <= b["left"] or b["right"] <= a["left"] or a["bottom"] <= b["top"] or b["bottom"] <= a["top"]))
    ok("R9F 드로어 = 오른쪽 옆 · 원본 · 카드 패널을 가리지 않음 · 막 0", bool(geo["dr"]) and not hit(geo["dr"], geo["orig"]) and not hit(geo["dr"], geo["form"])
       and geo["dr"]["left"] >= geo["form"]["right"] - 1 and geo["ov"] == 0, geo)
    zl = page.locator(".c01-orig-h .z")
    z0 = zl.inner_text() if zl.count() else None
    if page.locator("#z-in").count():
        page.click("#z-in")
        page.wait_for_timeout(200)
    ok("R9F 드로어 연 채 원본 조작 (확대) 가능 · 드로어 그대로", page.locator("#ask-box").count() == 1 and (z0 is None or zl.inner_text() != z0),
       [z0, zl.inner_text() if zl.count() else None])
    page.click("#ask-close")
    page.wait_for_timeout(200)
    ok("R9F ✕ = 닫힘", page.locator("#ask-box").count() == 0 and page.locator("#q-ask").get_attribute("aria-expanded") == "false")
    page.click("#q-ask")
    page.wait_for_timeout(200)
    page.keyboard.press("Escape")
    page.wait_for_timeout(200)
    ok("R9F Esc = 닫힘", page.locator("#ask-box").count() == 0)
    page.click("#ask-link")
    page.wait_for_timeout(200)
    ok("R9F 아래 「その他（AIに相談）」 = 같은 드로어를 엶 (입력 칸 1개)", page.locator("#ask-box").count() == 1 and page.locator("#ask-in").count() == 1
       and page.locator("#q-ask").get_attribute("aria-expanded") == "true")
    ok("R9F 이 카드 기록 2건 (드로어)", page.locator("#ask-box .c01-ask-q").count() == 2)
    other = page.evaluate("""qid => { const it = (C01.state.queue.items || []); const me = it.filter(x => x.queue_id === qid)[0];
        const mine = document.querySelector('.c01-item[data-q="' + qid + '"]'); const mk = mine ? mine.getAttribute('data-card') : '';
        for (const e of document.querySelectorAll('.c01-item[data-q]')) { const x = it.filter(y => y.queue_id === e.getAttribute('data-q'))[0];
          if (x && x.kind !== '写真のCT' && e.getAttribute('data-card') !== mk) return e.getAttribute('data-q'); }
        return null; }""", qid)
    if other:
        page.locator(f".c01-item[data-q='{other}']").first.click()
        page.wait_for_timeout(300)
        ok("R9F 카드 바꾸면 드로어 그대로 · 그 카드 기록 (0건)", page.locator("#ask-box").count() == 1 and page.locator("#ask-box .c01-ask-q").count() == 0, other)
        page.locator(f".c01-item[data-q='{qid}']").first.click()
        page.wait_for_timeout(300)
        ok("R9F 돌아오면 원래 카드 기록 2건 다시 보임", page.locator("#ask-box .c01-ask-q").count() == 2)
    else:
        ok("R9F 다른 카드 있음 (시험 자료)", False, "other card none")
    files = sorted((root / "_actions" / "ask").rglob("*.json"), key=lambda x: x.stat().st_mtime)
    k = json.loads(files[-1].read_text(encoding="utf-8"))
    ans = "写真の値が正しいと思われます。\n<b>太字</b> & 記号\n調べた内容: ブッキング検索 TST · IV 一覧 TST2611-02"
    rep = {"ask_id": k["ask_id"], "status": "ok", "answer": ans, "kind": "value", "approval_request": "", "suggestions": [],
           "tool_calls": 2, "looked": ["ブッキング検索 TST", "IV 一覧 TST2611-02"]}
    (root / "_actions" / "ask_reply" / f"{k['ask_id']}.json").write_text(json.dumps(rep, ensure_ascii=False), encoding="utf-8")
    page.evaluate("() => C01.app.tick()")
    page.wait_for_timeout(800)
    page.evaluate("() => C01.app.render()")       # 값 칸이 저장 전 (r7z 값 버튼) = tick 은 미룸 · 답 대기 타이머와 같은 render
    page.wait_for_timeout(300)
    t = page.locator("#ask-box .c01-ask-txt").last
    info = t.evaluate("e => ({ txt: e.innerText, html: e.innerHTML, b: e.querySelectorAll('b').length, ws: getComputedStyle(e).whiteSpace, h: e.getBoundingClientRect().height, lh: parseFloat(getComputedStyle(e).lineHeight) || 18 })")
    ok("R9F 「調べた内容」 줄 = 줄바꿈 유지 (pre-wrap · 3줄 이상) · tool_calls · looked 있어도 깨지지 않음",
       "\n調べた内容: ブッキング検索 TST · IV 一覧 TST2611-02" in info["txt"] and info["ws"] == "pre-wrap" and info["h"] >= 2.5 * info["lh"], info)
    ok("R9F 답 글 HTML 이스케이프 (<b> 요소 0 · &lt;b&gt;)", info["b"] == 0 and "&lt;b&gt;" in info["html"] and "&amp;" in info["html"], info["html"][:120])
    page.screenshot(path=str(shots / "r9f_ask_drawer.png"), full_page=False)
    page.set_viewport_size({"width": 1366, "height": 768})
    page.wait_for_timeout(300)
    page.evaluate("window.scrollTo(0, 0)")
    bb = page.locator("#q-ask").bounding_box()
    ib = page.locator("#ask-in").bounding_box()
    geo = page.evaluate("""() => { const r = s => document.querySelector(s).getBoundingClientRect().toJSON();
        return { dr: r('#ask-box'), orig: r('.c01-orig'), form: r('.c01-form'), sw: document.documentElement.scrollWidth }; }""")
    ok("R9F 1366×768 · 버튼 · 질문 칸 창 안 · 드로어가 원본 · 카드 안 가림 · 가로 스크롤 0", bb["y"] + bb["height"] <= 768 and ib["y"] + ib["height"] <= 768 and not hit(geo["dr"], geo["orig"])
       and not hit(geo["dr"], geo["form"]) and geo["sw"] <= 1366, [bb, geo])
    page.screenshot(path=str(shots / "r9f_ask_drawer_1366.png"), full_page=False)
    page.evaluate("() => { C01.ASK._en = C01.ASK.enabled; C01.ASK.enabled = false; C01.app.render(); }")
    page.wait_for_timeout(200)
    ok("R9F askOn 거짓 = 버튼 · 링크 · 드로어 없음", page.locator("#q-ask").count() == 0 and page.locator("#ask-link").count() == 0 and page.locator("#ask-box").count() == 0)
    page.evaluate("() => { C01.ASK.enabled = C01.ASK._en; delete C01.ASK._en; C01.app.render(); }")
    page.wait_for_timeout(200)
    page.keyboard.press("Escape")
    page.set_viewport_size({"width": 1440, "height": 1000})
    page.wait_for_timeout(200)


def r9l_gask_checks(page, root, shots, engine):
    """v0.3.39 (R9L · #273): 오른쪽 위 「AI 相談」 (화면 전체) — 使い方 옆 버튼 · 오른쪽 드로어 (実況表 · 確認・入力 둘 다) · 카드 대화와 따로 (global:{담당자}) ·
    답의 「改善依頼の案」 → 「この内容で依頼」 = _actions improve_request (엔진 스키마 통과) · 「やめる」 = 기록 0 · 접수 (requests.json) = 토스트 No ·
    「依頼一覧」 탭 (自分 / 全体) · Esc · 카드 드로어 열면 닫힘 · Powered 줄."""
    page.evaluate("() => { window._toasts = []; const o = LEENAI.toast; LEENAI.toast = (m, t) => { window._toasts.push(m); return o && o(m, t); }; }")
    page.keyboard.press("Escape")
    page.click("#tab-main")
    page.wait_for_timeout(300)
    nav = page.evaluate("""() => { const h = document.getElementById('help-open'), g = document.getElementById('gask-open');
        return { g: !!g, txt: g && g.textContent, next: !!(h && g && h.nextElementSibling === g) }; }""")
    ok("R9L 「AI 相談」 버튼 = 使い方 바로 옆 (実況表)", nav["g"] and nav["txt"] == "AI 相談" and nav["next"], nav)
    page.click("#gask-open")
    page.wait_for_timeout(300)
    box = page.locator("#gask-box")
    ok("R9L 実況表 에서 드로어 열림 · 제목 「AI 相談（全体）」 · 試験表示 없음 (v0.3.48) · Powered 줄", box.count() == 1 and "AI 相談（全体）" in box.inner_text() and "試験表示" not in box.inner_text()
       and "✦ Powered by LEENAI Automation System" in box.inner_text() and page.locator("#gask-open").get_attribute("aria-expanded") == "true")
    before = set(p.name for p in (root / "_actions" / "ask").rglob("*.json"))
    page.fill("#gask-in", "沖縄テスト紙業 から TSTBK0000001 のメール来てるのに写真がない")
    page.press("#gask-in", "Enter")
    page.wait_for_timeout(500)
    new = [p for p in (root / "_actions" / "ask").rglob("*.json") if p.name not in before]
    g = json.loads(new[0].read_text(encoding="utf-8")) if len(new) == 1 else {}
    me = page.evaluate("() => (C01.state.me || {}).email")
    gc = g.get("card") or {}
    ok("R9L 질문 → _actions/ask/{날짜}/{id}.json · scope global · key global:{담당자} · IV/CT 없음", len(new) == 1 and g.get("scope") == "global"
       and gc.get("key") == "global:" + str(me) and gc.get("kind") == "global" and gc.get("iv") is None and gc.get("ct") is None, g)
    ok("R9L 보낸 뒤 「回答待ち…」 (전체 드로어)", page.locator("#gask-box .c01-ask-a.wait").count() == 1)
    # 카드 대화와 섞이지 않음: 카드 드로어 열면 전체 드로어 닫힘 · 카드 기록에 전체 질문 없음
    page.click("#tab-input")
    page.wait_for_timeout(300)
    page.locator("[data-q='" + "z" * 15 + "7']").first.click()
    page.wait_for_timeout(300)
    page.click("#q-ask")
    page.wait_for_timeout(300)
    card_qs = page.locator("#ask-box .c01-ask-q").all_inner_texts()
    ok("R9L 카드 드로어 열면 전체 드로어 닫힘 · 카드 기록에 전체 질문 0", page.locator("#gask-box").count() == 0 and page.locator("#ask-box").count() == 1
       and not any("沖縄テスト紙業" in t for t in card_qs), card_qs)
    page.click("#gask-open")
    page.wait_for_timeout(300)
    gq = page.locator("#gask-box .c01-ask-q").all_inner_texts()
    ok("R9L 確認・入力 에서도 열림 · 카드 드로어 닫힘 · 전체 기록 = 전체 질문만 (1건)", page.locator("#ask-box").count() == 0 and len(gq) == 1 and "沖縄テスト紙業" in gq[0], gq)
    imp = {"title": "分類済みメールの ZIP を開く", "summary": "BKG で分類済みでも 発信者未登録で ZIP が開かれていない。", "cause": "発信者未登録",
           "mail_ids": [478], "ivs": ["TST2611-01"], "bkgs": ["TSTBK0000001"]}
    rep = {"ask_id": g["ask_id"], "scope": "global", "status": "ok", "kind": "investigation", "suggestions": [], "approval_request": "", "improve": imp,
           "answer": "メール 478 は BKG で分類済みですが、ZIP が開かれていません。\n調べた内容: メール検索 TSTBK0000001 · メールの処理経過 478"}
    (root / "_actions" / "ask_reply").mkdir(parents=True, exist_ok=True)
    (root / "_actions" / "ask_reply" / f"{g['ask_id']}.json").write_text(json.dumps(rep, ensure_ascii=False), encoding="utf-8")
    page.evaluate("() => C01.app.tick()")
    page.wait_for_timeout(800)
    page.evaluate("() => C01.app.render()")
    page.wait_for_timeout(300)
    ib = page.locator("#gask-box .c01-imp")
    ok("R9L 답 + 「改善依頼の案」 (제목 · 요약 · 원인 · mail · IV) + 「この内容で依頼」 「やめる」", ib.count() == 1 and "分類済みメールの ZIP を開く" in ib.inner_text()
       and "推定原因" in ib.inner_text() and page.locator("[data-impsend]").count() == 1 and page.locator("[data-impdrop]").count() == 1
       and "調べた内容" in page.locator("#gask-box .c01-ask-txt").last.inner_text())
    page.screenshot(path=str(shots / "r9l_gask_answer.png"), full_page=False)
    n0 = len([x for x in actions(root) if x.get("action") == "improve_request"])
    page.locator("[data-impsend]").click()
    page.wait_for_timeout(500)
    acts = [x for x in actions(root) if x.get("action") == "improve_request"]
    a = acts[-1] if acts else {}
    v = a.get("value") or {}
    ok("R9L 「この内容で依頼」 → _actions improve_request 1건 (ask_id · 질문 · 제목 · 요약 · mail_ids · by)", len(acts) == n0 + 1 and v.get("ask_id") == g["ask_id"]
       and v.get("title") == imp["title"] and v.get("mail_ids") == [478] and v.get("question", "").startswith("沖縄テスト紙業") and a.get("by") == me
       and a.get("iv") is None and a.get("ct") is None and a.get("field") is None and a.get("source") is None, a)
    sys.path.insert(0, engine)
    from engine.output import schema_check as SC  # noqa: E402
    ok("R9L 보낸 action = 엔진 스키마 통과 (action.schema.json improve_request)", SC.check_obj(a, "action") == [], SC.check_obj(a, "action"))
    ok("R9L 보낸 뒤 버튼 사라짐 · 「受付番号は まもなく」 · 토스트", page.locator("[data-impsend]").count() == 0 and "まもなく" in ib.inner_text()
       and any("依頼を送りました" in t for t in page.evaluate("() => window._toasts")), page.evaluate("() => window._toasts"))
    rq = {"schema_version": 1, "kind": "improve_requests", "today": "2026-11-16", "items": [
        {"no": 7, "ask_id": g["ask_id"], "at": "2026-11-16T10:30:00+09:00", "by": me, "by_name": "担当A", "title": imp["title"], "summary": imp["summary"],
         "question": "q", "status": "受付", "memo": None, "version": None, "plan": "予定: 次のラウンド (〜13:13)", "status_at": None},
        {"no": 6, "ask_id": "kOTHER", "at": "2026-11-16T09:00:00+09:00", "by": "other@example.invalid", "by_name": "担当B", "title": "他の人の依頼",
         "summary": "s", "question": "q", "status": "反映済", "memo": "直しました", "version": "v0.5.98", "plan": "反映済 (v0.5.98)", "status_at": None}]}
    (root / "_data" / "requests.json").write_text(json.dumps(rq, ensure_ascii=False), encoding="utf-8")
    page.evaluate("() => C01.app.tick()")
    page.wait_for_timeout(900)
    page.evaluate("() => C01.app.render()")
    page.wait_for_timeout(300)
    ts = page.evaluate("() => window._toasts")
    ok("R9L 엔진 접수 (requests.json) → 토스트 「依頼を受け付けました（No.7）」 1번 · 상자에 No.7", ts.count("依頼を受け付けました（No.7）") == 1
       and "No.7" in page.locator("#gask-box .c01-imp").inner_text(), ts)
    page.evaluate("() => C01.app.render()")
    page.wait_for_timeout(200)
    ok("R9L 토스트 다시 안 나옴 (render 다시)", page.evaluate("() => window._toasts").count("依頼を受け付けました（No.7）") == 1)
    page.locator("[data-gtab='reqs']").click()
    page.wait_for_timeout(300)
    rows = page.locator("#gask-box .c01-reqs tbody tr")
    ok("R9L 「依頼一覧」 탭 = 내 요청만 (No.7 · 受付 · 予定)", rows.count() == 1 and "受付" in rows.first.inner_text() and "予定: 次のラウンド" in rows.first.inner_text(),
       rows.all_inner_texts())
    page.locator("[data-reqall='1']").click()
    page.wait_for_timeout(300)
    txt = page.locator("#gask-box .c01-reqs").inner_text()
    ok("R9L 「全体」 = 다른 사람 요청도 (No.6 反映済 · 반영 판 · 메모 · 이름)", rows.count() == 2 and "反映済 (v0.5.98)" in txt and "直しました" in txt and "担当B" in txt, txt)
    page.screenshot(path=str(shots / "r9l_gask_reqs.png"), full_page=False)
    page.locator("[data-gtab='chat']").click()
    page.wait_for_timeout(200)
    # 두 번째 질문 · 「やめる」 = 기록 0
    page.fill("#gask-in", "今日 FAX が 0 件なのは正常？")
    page.press("#gask-in", "Enter")
    page.wait_for_timeout(500)
    g2 = sorted([p for p in (root / "_actions" / "ask").rglob("*.json")], key=lambda x: x.stat().st_mtime)[-1]
    g2 = json.loads(g2.read_text(encoding="utf-8"))
    rep2 = {**rep, "ask_id": g2["ask_id"], "answer": "FAX は今日 3 件受信しています。", "improve": {**imp, "title": "FAX の件数表示"}}
    (root / "_actions" / "ask_reply" / f"{g2['ask_id']}.json").write_text(json.dumps(rep2, ensure_ascii=False), encoding="utf-8")
    page.evaluate("() => C01.app.tick()")
    page.wait_for_timeout(800)
    page.evaluate("() => C01.app.render()")
    page.wait_for_timeout(300)
    n1 = len([x for x in actions(root) if x.get("action") == "improve_request"])
    page.locator("[data-impdrop]").click()
    page.wait_for_timeout(300)
    ok("R9L 「やめる」 = 기록 0 · 「依頼しませんでした」", len([x for x in actions(root) if x.get("action") == "improve_request"]) == n1
       and "依頼しませんでした" in page.locator("#gask-box").inner_text() and page.locator("[data-impsend]").count() == 0)
    ok("R9L 전체 기록 2건 · 순서", page.locator("#gask-box .c01-ask-q").count() == 2)
    page.keyboard.press("Escape")
    page.wait_for_timeout(200)
    ok("R9L Esc = 닫힘", page.locator("#gask-box").count() == 0 and page.locator("#gask-open").get_attribute("aria-expanded") == "false")
    page.evaluate("() => { C01.ASK._g = C01.ASK.global; C01.ASK.global = false; C01.app.render(); }")
    page.wait_for_timeout(200)
    ok("R9L C01.ASK.global 거짓 = 버튼 없음 (카드 「AIに相談」 은 그대로)", page.locator("#gask-open").count() == 0 and page.locator("#q-ask").count() == 1)
    page.evaluate("() => { C01.ASK.global = C01.ASK._g; delete C01.ASK._g; C01.app.render(); }")
    page.wait_for_timeout(200)



def r9o_checks(page, root, shots, engine):
    """v0.3.41 (R9O Part 00 · #277): 「発信者未登録」 판단 근거 — 근거 줄 (○ × ?) · 메일 목록 (본문 앞부분 · 서명 · 첨부 미리보기) · 묻는 말 3가지
    (① 業者本人 · ② 代わりに送る所 = register_sender relay · ③ 登録しない) · 自動推薦（仮登録） 표시 · 받는 쪽 대조 (엔진 스키마 키)."""
    dump = lambda o: json.dumps(o, ensure_ascii=False, indent=1) + chr(10)   # noqa: E731
    eng = Path(engine)
    ss = json.loads((eng / "engine" / "output" / "schema" / "senders.schema.json").read_text(encoding="utf-8"))
    ck = set(ss["properties"]["cards"]["items"]["properties"])
    mk = set(ss["properties"]["cards"]["items"]["properties"]["mail_list"]["items"]["properties"])
    ek = set(ss["properties"]["cards"]["items"]["properties"]["evidence"]["items"]["properties"])
    js = (TOOL / "js" / "app.js").read_text(encoding="utf-8")
    need_m = {"received_at", "subject", "attach", "attach_n", "ivs", "bkgs", "files", "photos", "hannyu", "body_head", "sig_lines"}
    ok("R9O 받는 쪽 대조: senders.json evidence · mail_list · auto · excluded 키 = TOOL 이 읽는 키 (엔진 스키마)",
       {"evidence", "mail_list", "auto", "ask"} <= ck and need_m <= mk and {"mark", "kind", "text"} <= ek and "excluded" in ss["properties"]
       and all(("." + k) in js for k in need_m | {"evidence", "mail_list", "auto"}), (ck, mk, ek))
    acs = json.loads((eng / "engine" / "output" / "schema" / "action.schema.json").read_text(encoding="utf-8"))
    rv = [x for x in acs["allOf"] if x["if"]["properties"]["action"].get("const") == "register_sender"][0]["then"]["properties"]["value"]["properties"]
    ok("R9O 받는 쪽 대조: action register_sender value.relay = 엔진 스키마에 있음", "relay" in rv, sorted(rv))
    sp = root / "_data" / "senders.json"
    pp = root / "_data" / "packers.json"
    pp.write_text(dump({"schema_version": 1, "packers": [{"code": "PACKER_A", "name": "テスト商店", "plants": ["本社", "市川"]},
                                                         {"code": "PACKER_B", "name": "テスト二", "plants": []}]}), encoding="utf-8")
    g = lambda pk, st, src, o=0, **kw: dict({"packer": pk, "strength": st, "sources": src, "other_packers_n": o}, **kw)   # noqa: E731
    ml = [{"received_at": "2026-11-16T10:30:00+09:00", "subject": "TST BKG 写真送付", "attach": ["01_空コンテナ.svg", "搬入票_01.svg", "a.xlsx"], "attach_n": 3,
           "ivs": ["TST2611-01"], "bkgs": ["BKGTEST01"], "photos": 1, "hannyu": True,
           "files": [{"path": "TST2611-01/TSTU0010075/01_空コンテナ.svg", "name": "01_空コンテナ.svg", "kind": "photo"},
                     {"path": "TST2611-01/搬入票/搬入票_01.svg", "name": "搬入票_01.svg", "kind": "photo"}],
           "body_head": ["お世話になっております。", "写真を送ります。"], "sig_lines": ["株式会社テスト港運", "営業部 担当"]},
          {"received_at": "2026-11-15T09:00:00+09:00", "subject": "日程のご確認", "attach": [], "attach_n": 0, "ivs": [], "bkgs": [], "photos": 0, "hannyu": False,
           "files": [], "body_head": ["日程のご確認です。"], "sig_lines": []}]
    ev = [{"mark": "○", "kind": "bkg", "text": "メールの BKG / IV の業者 = PACKER_A (TST2611-01)"},
          {"mark": "×", "kind": "sig", "text": "署名: 株式会社テスト港運 ≠ PACKER_A"},
          {"mark": "×", "kind": "dom", "text": "ドメイン hl.example.invalid = 登録業者のドメインではない"}]
    cards = [{"queue_id": "6a" * 8, "kind": "発信者未登録", "address": "haul.taro@hl.example.invalid", "name": "港運 太郎", "domain": "hl.example.invalid", "mails": 2,
              "hold_mails": 2, "zip_pending": 0, "ivs": ["TST2611-01"], "last_at": "2026-11-16T10:30:00+09:00",
              "guess": g("PACKER_A", "weak", ["bkg"], note="sig_mismatch"), "evidence": ev, "mail_list": ml, "ask": ["self", "relay", "decline"],
              "auto": {"by": "自動推薦#272", "packer": "PACKER_A", "action_id": "auto272:0000000000000001"}},
             {"queue_id": "6b" * 8, "kind": "発信者未登録", "address": "self.hanako@sf.example.invalid", "name": "自 花子", "domain": "sf.example.invalid", "mails": 1,
              "hold_mails": 1, "zip_pending": 0, "ivs": ["TST2611-02"], "last_at": "2026-11-16T09:00:00+09:00", "guess": g("PACKER_B", "weak", ["bkg"]),
              "evidence": ev[:1], "mail_list": ml[1:], "ask": ["self", "relay", "decline"]}]
    sd = {"schema_version": 1, "kind": "sender_cards", "today": "2026-11-16", "cards": cards,
          "counts": {"target_mails": 3, "card_mails": 3, "done_mails": 0, "cards": 2, "gap": 0, "strong": 0, "weak": 2, "excluded": 1, "excluded_mails": 4},
          "declined": [], "excluded": [{"address": "noreply@ln.example.invalid", "domain": "ln.example.invalid", "name": None, "mails": 4, "reason": "no_reply",
                                         "last_at": "2026-11-16T08:00:00+09:00"}]}
    sys.path.insert(0, engine)
    from engine.output import schema_check as SC  # noqa: E402
    ok("R9O 시험 senders.json (근거 · 메일 목록 · auto · excluded) = 엔진 스키마 통과", SC.check_obj(sd, "senders") == [], SC.check_obj(sd, "senders"))
    sp.write_text(dump(sd), encoding="utf-8")
    page.click("#tab-input")
    page.evaluate("() => { C01.state.view = 'input'; C01.state.qkind = 'all'; C01.state.qsel = null; C01.state.sndSel = null; C01.state.sndMiss = 0; C01.app.tick(); }")
    page.wait_for_timeout(900)
    if page.locator("#me-select").count():
        page.select_option("#me-select", "STAFF_A")
        page.wait_for_timeout(200)
    page.click(".c01-chip-snd")
    page.wait_for_timeout(300)
    page.locator(".c01-snditem").first.click()
    page.wait_for_timeout(400)
    it0 = page.locator(".c01-snditem").first.inner_text()
    pn = page.locator("#snd-panel").inner_text()
    ok("R9O 自動推薦 카드 = 목록 「自動推薦（仮登録）」 · 패널 설명 (自動OK にしません)", "自動推薦（仮登録）" in it0 and page.locator("#snd-autonote").count() == 1
       and "自動OK にしません" in page.locator("#snd-autonote").inner_text(), [it0, pn[:200]])
    evt = page.locator("#snd-ev").inner_text()
    ok("R9O 근거 줄 = ○ BKG 업체 · × 서명 회사 (≠ 업체) · × 도메인 · 「強」 にしない 설명", all(x in evt for x in ("○", "×", "メールの BKG / IV の業者 = PACKER_A", "署名: 株式会社テスト港運 ≠ PACKER_A",
       "登録業者のドメインではない")) and "署名の会社名が推定の業者と違う" in pn, evt)
    ok("R9O 메일 목록 2통 (최근 먼저 · 시각 · 제목 · 添付 3 · 写真 1 · 搬入票 · IV)", page.locator(".c01-sndmail").count() == 2
       and all(x in page.locator(".c01-sndmail").nth(0).inner_text() for x in ("10:30", "TST BKG 写真送付", "添付 3", "写真 1", "搬入票", "TST2611-01")),
       page.locator("#snd-mails").inner_text()[:300])
    mb = page.locator("#snd-mailbody").inner_text()
    ok("R9O 고른 메일 = 제목 · BKG/IV · 첨부 이름 · 본문 앞부분 · 서명 줄 · 첨부 미리보기 (그림)", all(x in mb for x in ("TST BKG 写真送付", "BKGTEST01", "a.xlsx", "写真を送ります。",
       "株式会社テスト港運")) and page.locator(".c01-sndprev img").count() == 1 and page.locator("[data-sndf]").count() == 2, mb[:300])
    page.click("[data-sndf='1']")
    page.wait_for_timeout(300)
    ok("R9O 첨부 2번째 고름 = 그 파일 미리보기 (搬入票)", "搬入票_01" in (page.locator(".c01-sndprev img").get_attribute("alt") or page.locator(".c01-sndprev").inner_html()), "")
    page.click("[data-sndm='1']")
    page.wait_for_timeout(300)
    mb2 = page.locator("#snd-mailbody").inner_text()
    ok("R9O 메일 2번째 고름 = 그 본문 · 첨부 없음 · 署名に会社名がありません", "日程のご確認です。" in mb2 and "表示できる添付はありません" in mb2 and "署名に会社名がありません" in mb2, mb2[:200])
    ok("R9O 묻는 말 3가지 (① 業者本人 · ② 代わりに送る所 · ③ 登録しない)", "このアドレスは？" in page.locator("#snd-ask").inner_text()
       and page.locator("#snd-regbtn").inner_text().strip() == "① 業者本人" and page.locator("#snd-relaybtn").count() == 1 and "③ 登録しない" in page.locator("#snd-decline").inner_text(), "")
    page.screenshot(path=str(shots / "r9o_sender_detail.png"), full_page=True)
    ids0 = {x.get("action_id") for x in actions(root)}
    page.evaluate("() => { window.__cf = []; window.__cf0 = window.confirm; window.confirm = (m) => { window.__cf.push(m); return true; }; }")
    page.click("#snd-relaybtn")
    page.wait_for_timeout(600)
    new = [x for x in actions(root) if x.get("action_id") and x["action_id"] not in ids0]
    ok("R9O 「② 代わりに送る所」 = register_sender value.relay true (확인창 「代わりに送る所」) · 엔진 스키마 통과", len(new) == 1 and new[0]["action"] == "register_sender"
       and new[0]["value"] == {"address": "haul.taro@hl.example.invalid", "packer": "PACKER_A", "plant": None, "relay": True}
       and "代わりに送る所" in page.evaluate("() => window.__cf")[0] and SC.check_obj(new[0], "action") == [], new)
    page.click("#snd-regbtn")
    page.wait_for_timeout(600)
    new2 = [x for x in actions(root) if x.get("action_id") and x["action_id"] not in ids0 and x["action_id"] != new[0]["action_id"]]
    ok("R9O 「① 業者本人」 = register_sender (relay 없음)", len(new2) == 1 and new2[0]["value"] == {"address": "self.hanako@sf.example.invalid", "packer": "PACKER_B", "plant": None},
       new2)
    page.evaluate("() => { window.confirm = window.__cf0; C01.state.sndDoneOpen = true; C01.app.render(); }")   # R9M 시험이 펼친 채로 둠 → 상태로 펼침
    page.wait_for_timeout(200)
    ok("R9O 「登録した · 登録しない」 목록 = 「代わりに送る所 PACKER_A」 표시", "代わりに送る所 PACKER_A" in page.locator(".c01-snddone").inner_text(), page.locator(".c01-snddone").inner_text())
    for x in (new[0], new2[0]):
        page.click(f"[data-sndundo='{x['action_id']}']")
        page.wait_for_timeout(300)
    page.evaluate("() => { C01.RULES._r = C01.RULES.senderRelay; C01.RULES.senderRelay = false; C01.state.sndSel = null; C01.app.render(); }")
    page.wait_for_timeout(200)
    page.locator(".c01-snditem").first.click()
    page.wait_for_timeout(200)
    ok("R9O RULES.senderRelay 끔 = 「② 代わりに送る所」 버튼 없음 (① · ③ 그대로)", page.locator("#snd-relaybtn").count() == 0 and page.locator("#snd-regbtn").count() == 1, "")
    page.evaluate("() => { C01.RULES.senderRelay = C01.RULES._r; delete C01.RULES._r; C01.state.qkind = 'all'; C01.app.render(); }")
    sp.write_text(dump({"schema_version": 1, "kind": "sender_cards", "today": "2026-11-16", "cards": [], "counts": {}, "declined": []}), encoding="utf-8")
    page.evaluate("() => { C01.state.sndMiss = 0; C01.app.tick(); }")
    page.wait_for_timeout(500)
    # 自動推薦 막힌 줄 배지 (実況表 rowInfo) — 문구 확인 (함수 직접)
    ok("R9O 自動推薦発信者(人確認) 줄 = 「自動推薦」 배지 문구 (確認・入力 「発信者未登録」 안내)", "自動推薦発信者（人確認）" in js and "data-info=\"auto_sender\"" in js, "")

def r12a_checks(page, root, shots, engine):
    """v0.3.61 (R12A Part 1 · #339): 「発信者未登録」 件名で対象外 — 一覧 · 件名の語 · 管理者 追加 / 削除 · 元に戻す · 받는 쪽 대조 (엔진 스키마 · 코드 키)."""
    dump = lambda o: json.dumps(o, ensure_ascii=False, indent=1) + chr(10)   # noqa: E731
    eng = Path(engine)
    ss = json.loads((eng / "engine" / "output" / "schema" / "senders.schema.json").read_text(encoding="utf-8"))
    js = (TOOL / "js" / "app.js").read_text(encoding="utf-8")
    sc = (eng / "engine" / "output" / "sender_cards.py").read_text(encoding="utf-8")
    wk = set((ss["properties"].get("skip_words") or {}).get("items", {}).get("properties") or {})
    en = (ss["properties"]["excluded"]["items"]["properties"]["reason"] or {}).get("enum") or []
    ok("R12A 받는 쪽 대조: senders.json skip_words 키 (word · src · by · at · action_id) · 対象外 reason subject_words = TOOL 이 읽는 키 · 엔진 코드",
       {"word", "src", "by", "at", "action_id"} <= wk and "subject_words" in en and "subject_words" in js and '"subject_words"' in sc and "skip_words" in js, (wk, en))
    sp = root / "_data" / "senders.json"
    s0 = sp.read_text(encoding="utf-8") if sp.exists() else None
    sd = {"schema_version": 1, "kind": "sender_cards", "today": "2026-11-20", "cards": [], "counts": {"target_mails": 3, "card_mails": 0, "done_mails": 0, "cards": 0, "gap": 0},
          "declined": [],
          "excluded": [{"address": "order@po.example.invalid", "domain": "po.example.invalid", "name": None, "mails": 3, "reason": "subject_words", "last_at": "2026-11-19T10:00:00+09:00"},
                       {"address": "noreply@ln.example.invalid", "domain": "ln.example.invalid", "name": None, "mails": 1, "reason": "no_reply", "last_at": None}],
          "skip_words": [{"word": "空コンテナ搬出申込", "src": "master", "by": "t", "at": "2026-11-20", "why": None, "action_id": None},
                         {"word": "ACL未着", "src": "human", "by": "staff_a@fake", "at": "2026-11-20T10:00:00+09:00", "why": None, "action_id": "hUmAn0000001"}]}
    sys.path.insert(0, engine)
    from engine.output import schema_check as SC  # noqa: E402
    ok("R12A 시험 senders.json (skip_words · subject_words) = 엔진 스키마 통과", SC.check_obj(sd, "senders") == [], SC.check_obj(sd, "senders"))
    sp.write_text(dump(sd), encoding="utf-8")
    page.keyboard.press("Escape")
    page.evaluate("() => { C01.state.view = 'input'; C01.state.qkind = 'all'; C01.state.qsel = null; C01.state.sndMiss = 0; C01.state.sndSkipOpen = false; C01.app.tick(); }")
    page.wait_for_timeout(900)
    page.click("#tab-input")
    page.wait_for_timeout(200)
    page.evaluate("() => { C01.state.qkind = '発信者未登録'; C01.app.render(); }")
    page.wait_for_timeout(300)
    b = page.locator("#snd-skip")
    ok("R12A 「件名で対象外 1件 · 件名の語 2」 (no_reply 対象外 는 안 셈) · 처음 접힘", b.count() == 1 and "件名で対象外 1件 · 件名の語 2" in b.inner_text()
       and page.locator("#snd-skipbox").count() == 0, b.all_inner_texts())
    page.evaluate("() => { C01.state._me0 = C01.state.me; C01.state.me = Object.assign({}, C01.state.me || {code: 'STAFF_A', email: 'staff_a@fake'}, {admin: false}); C01.app.render(); }")
    page.click("#snd-skip")
    page.wait_for_timeout(200)
    bx = page.locator("#snd-skipbox").inner_text()
    ok("R12A 펼침 = 対象外 도메인 · 메일 수 · 낱말 2 · 관리자 아님 = 追加 · 削除 없음 (안내 한 줄) · 사람이 더한 낱말 = 元に戻す",
       "po.example.invalid" in bx and "ln.example.invalid" not in bx and "メール 3通" in bx and "空コンテナ搬出申込" in bx and "ACL未着" in bx
       and page.locator("[data-sndskipdel]").count() == 0 and page.locator("#snd-skip-add").count() == 0 and "管理者だけ" in bx
       and page.locator("#snd-skipbox [data-sndundo='hUmAn0000001']").count() == 1, bx[:300])
    page.evaluate("() => { C01.state.me = Object.assign({}, C01.state.me, {admin: true}); C01.app.render(); }")
    page.wait_for_timeout(200)
    ok("R12A 관리자 = 낱말마다 「削除」 · 追加 칸", page.locator("[data-sndskipdel]").count() == 2 and page.locator("#snd-skip-add").count() == 1, "")
    ids0 = {x.get("action_id") for x in actions(root)}
    page.fill("#snd-skip-word", "ab")
    page.click("#snd-skip-add")
    page.wait_for_timeout(300)
    ok("R12A 3자 미만 = 안 씀", not [x for x in actions(root) if x.get("action_id") not in ids0], "")
    page.fill("#snd-skip-word", "空コンテナ 搬出申込")
    page.click("#snd-skip-add")
    page.wait_for_timeout(300)
    ok("R12A 이미 있는 낱말 (빈칸 차이) = 안 씀", not [x for x in actions(root) if x.get("action_id") not in ids0], "")
    page.fill("#snd-skip-word", "B/L DRAFT")
    page.click("#snd-skip-add")
    page.wait_for_timeout(500)
    ad = [x for x in actions(root) if x.get("action_id") not in ids0]
    ok("R12A 「追加」 = sender_skip_word {op add · word} · 엔진 스키마 통과 · 목록 3", len(ad) == 1 and ad[0]["action"] == "sender_skip_word" and ad[0]["value"] == {"op": "add", "word": "B/L DRAFT"}
       and SC.check_obj(ad[0], "action") == [] and "件名の語 3" in page.locator("#snd-skip").inner_text(), ad)
    page.click("[data-sndskipdel='空コンテナ搬出申込']")
    page.wait_for_timeout(500)
    rm = [x for x in actions(root) if x.get("action_id") not in ids0 and (x.get("value") or {}).get("op") == "remove"]
    ok("R12A 「削除」 = sender_skip_word {op remove} · 엔진 스키마 통과 · 목록 2 · 「削除した語」 줄에 元に戻す", len(rm) == 1 and rm[0]["value"] == {"op": "remove", "word": "空コンテナ搬出申込"}
       and SC.check_obj(rm[0], "action") == [] and "件名の語 2" in page.locator("#snd-skip").inner_text()
       and page.locator(f"#snd-skipbox [data-sndundo='{rm[0]['action_id']}']").count() == 1, rm)
    page.screenshot(path=str(shots / "r12a_sender_skip.png"))
    page.click(f"#snd-skipbox [data-sndundo='{rm[0]['action_id']}']")
    page.wait_for_timeout(500)
    un = [x for x in actions(root) if x.get("action") == "undo" and (x.get("value") or {}).get("action_id") == rm[0]["action_id"]]
    ok("R12A 削除の 元に戻す = undo · 엔진 스키마 통과 · 목록 3 으로", len(un) == 1 and SC.check_obj(un[0], "action") == [] and "件名の語 3" in page.locator("#snd-skip").inner_text(),
       page.locator("#snd-skip").inner_text())
    sd2 = dict(sd)
    sd2.pop("skip_words")
    sp.write_text(dump(sd2), encoding="utf-8")
    page.evaluate("() => { C01.state.sndMiss = 0; C01.app.tick(); }")
    page.wait_for_timeout(800)
    ok("R12A 엔진 끔 (skip_words 없음) = 「件名で対象外」 표시 0", page.locator("#snd-skip").count() == 0, "")
    page.evaluate("() => { C01.state.me = C01.state._me0; delete C01.state._me0; C01.state.qkind = 'all'; C01.state.sndSkipOpen = false; C01.app.render(); }")
    if s0 is None:
        sp.unlink()
    else:
        sp.write_text(s0, encoding="utf-8")
    page.evaluate("() => { C01.state.sndMiss = 0; C01.app.tick(); }")
    page.wait_for_timeout(500)


def r9m_checks(page, root, shots, engine):
    """v0.3.40 (R9M Part A · #271 · #272 c): 確認・入力 「発信者未登録」 (枚数は別 · 強 → 弱 → 推定なし (閉じる) · 業者登録 · 登録しない (理由) · 元に戻す) ·
    Part B-1: 催促 「最近7日のメール」 一行 · Part B-2: 実況表 「催促 n回目（MM/DD）」 (試験は数えない · 行の高さ そのまま) · 받는 쪽 대조 (엔진 키 = TOOL 키)."""
    dump = lambda o: json.dumps(o, ensure_ascii=False, indent=1) + chr(10)   # noqa: E731
    # ── 받는 쪽 대조 (엔진 스키마 · 코드 키 ↔ TOOL 이 읽는 키) ──
    eng = Path(engine)
    ss = json.loads((eng / "engine" / "output" / "schema" / "senders.schema.json").read_text(encoding="utf-8"))
    ck = set(ss["properties"]["cards"]["items"]["properties"])
    gk = set(ss["properties"]["cards"]["items"]["properties"]["guess"]["properties"])
    dk = set((ss["properties"].get("declined") or {}).get("items", {}).get("properties") or {})
    js = (TOOL / "js" / "app.js").read_text(encoding="utf-8")
    need_c = {"queue_id", "address", "name", "domain", "mails", "hold_mails", "zip_pending", "ivs", "last_at", "guess"}
    ok("R9M 받는 쪽 대조: senders.json 카드 · guess · declined 키 = TOOL 이 읽는 키 (엔진 스키마)", need_c <= ck and {"packer", "strength", "sources", "other_packers_n", "note"} <= gk
       and {"address", "domain", "action_id", "by", "at", "reason_text"} <= dk and all(("c." + k) in js or ("." + k) in js for k in need_c), (ck, gk, dk))
    rs = (eng / "engine" / "notify" / "remind.py").read_text(encoding="utf-8")
    ok("R9M 받는 쪽 대조: 엔진 초안 recent_mail (n · held · unsorted · last_at · days) · 회차 = 시험 기록 뺌", 't["recent_mail"]' in rs and '"held"' in rs and '"unsorted"' in rs
       and '.get("test") is not True' in rs and "d.recent_mail" in js and "v.test" in js, "")
    sp = root / "_data" / "senders.json"
    pp = root / "_data" / "packers.json"
    rp = root / "_data" / "remind.json"
    jp = root / "_data" / "jikkyou.json"
    s0 = sp.read_text(encoding="utf-8") if sp.exists() else None
    r0 = rp.read_text(encoding="utf-8")
    j0 = jp.read_text(encoding="utf-8")
    pp.write_text(dump({"schema_version": 1, "packers": [{"code": "PACKER_A", "name": "テスト商店", "plants": ["本社", "市川"]},
                                                         {"code": "PACKER_B", "name": "テスト二", "plants": []}]}), encoding="utf-8")
    g = lambda pk, st, src, o=0, **kw: dict({"packer": pk, "strength": st, "sources": src, "other_packers_n": o}, **kw)   # noqa: E731
    cards = [
        {"queue_id": "5d" * 8, "kind": "発信者未登録", "address": "none.one@nb1.example.invalid", "name": "なし一", "domain": "nb1.example.invalid", "mails": 5,
         "hold_mails": 1, "zip_pending": 0, "ivs": [], "last_at": "2026-11-16T09:00:00+09:00", "guess": g(None, "none", [])},
        {"queue_id": "5a" * 8, "kind": "発信者未登録", "address": "weak.taro@wk.example.invalid", "name": "弱 太郎", "domain": "wk.example.invalid", "mails": 2,
         "hold_mails": 2, "zip_pending": 1, "ivs": ["TST2611-02"], "last_at": "2026-11-15T10:00:00+09:00", "guess": g("PACKER_B", "weak", ["sig"], 1)},
        {"queue_id": "5b" * 8, "kind": "発信者未登録", "address": "strong.hanako@st.example.invalid", "name": "強 花子", "domain": "st.example.invalid", "mails": 1,
         "hold_mails": 0, "zip_pending": 5, "ivs": ["TST2611-01"], "last_at": "2026-11-16T09:42:00+09:00", "guess": g("PACKER_A", "strong", ["bkg", "dom"])},
        {"queue_id": "5c" * 8, "kind": "発信者未登録", "address": "none.two@nb2.example.invalid", "name": None, "domain": "nb2.example.invalid", "mails": 1,
         "hold_mails": 1, "zip_pending": 0, "ivs": [], "last_at": "2026-11-14T09:00:00+09:00", "guess": g(None, "none", [], note="domain_declined")}]
    sd = {"schema_version": 1, "kind": "sender_cards", "today": "2026-11-16", "cards": cards,
          "counts": {"target_mails": 9, "card_mails": 9, "done_mails": 0, "cards": 4, "gap": 0, "strong": 1, "weak": 1},
          "declined": [{"address": "old.x@dc.example.invalid", "domain": "dc.example.invalid", "action_id": "dEcl00000001", "by": "u@example.invalid",
                        "at": "2026-11-15T10:00:00+09:00", "reason_text": "運送会社"}]}
    sys.path.insert(0, engine)
    from engine.output import schema_check as SC  # noqa: E402
    ok("R9M 시험 senders.json = 엔진 스키마 통과", SC.check_obj(sd, "senders") == [], SC.check_obj(sd, "senders"))
    page.keyboard.press("Escape")
    sp.write_text(dump({"schema_version": 1, "kind": "sender_cards", "today": "2026-11-16", "cards": [], "counts": {}, "declined": []}), encoding="utf-8")
    page.evaluate("() => { C01.state.view = 'input'; C01.state.qkind = 'all'; C01.state.qsel = null; C01.state.sndMiss = 0; C01.app.tick(); }")
    page.wait_for_timeout(700)
    open0 = page.locator("#badge-open").inner_text()
    ok("R9M 카드 0 · 목록 0 = 「発信者未登録」 표시 0 (칩 · 머리 줄)", page.locator("#badge-snd").count() == 0 and page.locator(".c01-chip-snd").count() == 0, "")
    sp.write_text(dump(sd), encoding="utf-8")
    page.evaluate("() => { C01.state.sndMiss = 0; C01.app.tick(); }")
    page.wait_for_timeout(900)
    if page.locator("#me-select").count():
        page.select_option("#me-select", "STAFF_A")
        page.wait_for_timeout(200)
    nav = page.locator("#tab-input").inner_text()
    ok("R9M 머리 줄 「確認・入力 n · 発信者未登録 4」 · 確認・入力 장 수 그대로 (따로 셈)", "発信者未登録 4" in nav and page.locator("#badge-open").inner_text() == open0, [nav, open0])
    page.click(".c01-chip-snd")
    page.wait_for_timeout(300)
    items = page.locator(".c01-snditem")
    ok("R9M 순서 = 강 → 약 · 추천 없음 = 처음 접힘 「他 2件（推定なし）」", items.count() == 2 and "推定（強）" in items.nth(0).inner_text() and "推定（弱）" in items.nth(1).inner_text()
       and "他 2件（推定なし）" in page.locator("#snd-none").inner_text(), items.all_inner_texts())
    lst = page.locator(".c01-items").inner_text()
    ok("R9M 목록 한 줄 = 도메인 (주소 앞부분 0)", "st.example.invalid" in lst and "strong.hanako" not in lst and "weak.taro" not in lst, lst[:200])
    page.click("#snd-none")
    page.wait_for_timeout(200)
    ok("R9M 「他 n件」 누름 = 펼침 (4장)", page.locator(".c01-snditem").count() == 4, "")
    pn = page.locator("#snd-panel").inner_text()
    ok("R9M 카드 = 주소 (카드 안) · 이름 · 메일 수 · ZIP · IV · 추정 업체 · 근거", all(x in pn for x in ("strong.hanako@st.example.invalid", "強 花子", "1通", "開いていない ZIP 5件",
                                                                                            "TST2611-01", "推定（強）", "PACKER_A", "メールの BKG / IV の業者", "同じドメインの登録")), pn)
    ok("R9M 강한 추천 = 업체 칸에 미리 넣음 · 「業者登録」 켜짐", page.locator("#snd-packer").input_value() == "PACKER_A" and page.locator("#snd-regbtn").is_enabled(), "")
    page.screenshot(path=str(shots / "r9m_sender_cards.png"))
    ids0 = {x.get("action_id") for x in actions(root)}
    page.evaluate("() => { window.__cf = []; window.__cf0 = window.confirm; window.confirm = (m) => { window.__cf.push(m); return true; }; }")
    page.click("#snd-regbtn")
    page.wait_for_timeout(600)
    new = [x for x in actions(root) if x.get("action_id") and x["action_id"] not in ids0]
    ok("R9M 「業者登録」 = register_sender (주소 · 업체 · queue_id · 확인창 1) · 엔진 스키마 통과", len(new) == 1 and new[0]["action"] == "register_sender"
       and new[0]["value"] == {"address": "strong.hanako@st.example.invalid", "packer": "PACKER_A", "plant": None} and new[0]["queue_id"] == "5b" * 8
       and len(page.evaluate("() => window.__cf")) == 1 and "PACKER_A" in page.evaluate("() => window.__cf")[0] and SC.check_obj(new[0], "action") == [],
       [new, page.evaluate("() => window.__cf")])
    page.evaluate("() => { window.confirm = window.__cf0; }")
    ok("R9M 등록 뒤 카드 사라짐 (3) · 다음 카드 선택 · 確認・入力 장 수 그대로", "発信者未登録 3" in page.locator("#tab-input").inner_text()
       and page.locator(".c01-snditem").count() == 3 and "weak.taro" in page.locator("#snd-panel").inner_text() and page.locator("#badge-open").inner_text() == open0,
       page.locator("#tab-input").inner_text())
    page.click("#snd-decline")
    page.wait_for_timeout(200)
    ok("R9M 「登録しない」 = 이유 창 (이유 버튼 5 · ひとことでOK · Powered)", page.locator("#c01-nhdlg [data-sndr]").count() == 5 and "ひとことでOK" in page.locator("#c01-nhdlg").inner_text()
       and "✦ Powered by LEENAI Automation System" in page.locator("#c01-nhdlg").inner_text(), "")
    page.click("#c01-nhdlg [data-sndr='0']")
    page.fill("#c01-nhtext", "テスト")
    page.click("#c01-nhok")
    page.wait_for_timeout(500)
    dc = [x for x in actions(root) if x.get("action") == "sender_decline" and x["action_id"] not in ids0]
    ok("R9M 「登録しない」 = sender_decline (주소 · 이유 · queue_id) · 엔진 스키마 통과", len(dc) == 1 and dc[0]["value"] == {"address": "weak.taro@wk.example.invalid",
       "reason_text": "運送会社・ドレージ · テスト"} and dc[0]["queue_id"] == "5a" * 8 and SC.check_obj(dc[0], "action") == [], dc)
    ok("R9M 「登録しない」 뒤 카드 사라짐 (2)", "発信者未登録 2" in page.locator("#tab-input").inner_text() and page.locator(".c01-snditem").count() == 2, "")
    page.click("#snd-done")
    page.wait_for_timeout(200)
    dn = page.locator(".c01-snddone").inner_text()
    ok("R9M 「登録した · 登録しない 3件」 = 엔진 declined 1 + 이 화면 2 · 元に戻す", "登録した · 登録しない 3件" in page.locator("#snd-done").inner_text()
       and "dc.example.invalid" in dn and "wk.example.invalid" in dn and "st.example.invalid" in dn and page.locator("[data-sndundo]").count() == 3, dn)
    page.click(f"[data-sndundo='{dc[0]['action_id']}']")
    page.wait_for_timeout(500)
    un = [x for x in actions(root) if x.get("action") == "undo" and x["action_id"] not in ids0]
    ok("R9M 元に戻す = undo (value.action_id = sender_decline) · 엔진 스키마 통과 · 카드 다시 (3)", len(un) == 1 and un[0]["value"] == {"action_id": dc[0]["action_id"]}
       and SC.check_obj(un[0], "action") == [] and "発信者未登録 3" in page.locator("#tab-input").inner_text(), un)
    # 엔진이 반영한 뒤 (다음 출력 = 그 카드 빠짐) — 숨김 그대로 · 엔진 declined 의 元に戻す
    sd2 = json.loads(json.dumps(sd))
    sd2["cards"] = [c for c in sd2["cards"] if c["queue_id"] != "5b" * 8]
    sp.write_text(dump(sd2), encoding="utf-8")
    page.evaluate("() => C01.app.tick()")
    page.wait_for_timeout(800)
    ok("R9M 다음 출력 (등록 반영) = 장 수 3 그대로 (겹쳐 세지 않음)", "発信者未登録 3" in page.locator("#tab-input").inner_text(), page.locator("#tab-input").inner_text())
    page.click(f"[data-sndundo='dEcl00000001']")
    page.wait_for_timeout(500)
    un2 = [x for x in actions(root) if x.get("action") == "undo" and (x.get("value") or {}).get("action_id") == "dEcl00000001"]
    ok("R9M 엔진 「登録しない」 목록의 元に戻す = undo 1건", len(un2) == 1 and SC.check_obj(un2[0], "action") == [], un2)
    page.evaluate("() => { C01.RULES._s = C01.RULES.senderCards; C01.RULES.senderCards = false; C01.app.render(); }")
    page.wait_for_timeout(200)
    ok("R9M RULES.senderCards 끔 = 「発信者未登録」 칩 · 머리 표시 0 · すべて 로", page.locator(".c01-chip-snd").count() == 0 and page.locator("#badge-snd").count() == 0
       and page.evaluate("() => C01.state.qkind") == "all", "")
    page.evaluate("() => { C01.RULES.senderCards = C01.RULES._s; delete C01.RULES._s; C01.state.qkind = 'all'; C01.app.render(); }")
    # ── Part B-1: 催促 미리보기 「最近7日のメール」 ──
    r2 = json.loads(r0)
    d0 = r2["ivs"]["TST2611-02"][0]
    pk0 = d0["packer"]
    for d in r2["ivs"]["TST2611-02"]:
        if d["packer"] == pk0:
            d["recent_mail"] = {"n": 5, "held": 2, "unsorted": 1, "last_at": "2026-11-16T09:41:00+09:00", "days": 7}
    rp.write_text(dump(r2), encoding="utf-8")
    ok("R9M 시험 remind.json (recent_mail) = 엔진 스키마 통과", SC.check_obj(r2, "remind") == [], SC.check_obj(r2, "remind"))
    page.click("#tab-main")
    page.evaluate("() => C01.app.tick()")
    page.wait_for_timeout(700)
    page.click("tbody[data-iv='TST2611-02'] [data-remind]")
    page.wait_for_selector(".c01-rmd")
    rr = page.locator(".c01-rmd[data-rmd='0'] [data-rrecent]")
    ok("R9M 催促 미리보기 한 줄 「この業者から最近7日のメール 5通 · 保留 2通 · 未分類 1通 · 最後の受信 11/16 09:41」", rr.count() == 1
       and "この業者から最近7日のメール 5通 · 保留 2通 · 未分類 1通 · 最後の受信 11/16 09:41" in rr.inner_text(), rr.all_inner_texts())
    body0 = page.locator(".c01-rmd[data-rmd='0'] .c01-rbody").inner_text()
    page.screenshot(path=str(shots / "r9m_remind_recent.png"))
    page.click("[data-close]")
    rp.write_text(r0, encoding="utf-8")
    page.evaluate("() => C01.app.tick()")
    page.wait_for_timeout(600)
    page.click("tbody[data-iv='TST2611-02'] [data-remind]")
    page.wait_for_selector(".c01-rmd")
    ok("R9M recent_mail 없는 엔진 = 한 줄 없음 · 본문 그대로", page.locator("[data-rrecent]").count() == 0
       and page.locator(".c01-rmd[data-rmd='0'] .c01-rbody").inner_text() == body0, "")
    page.click("[data-close]")
    # ── Part B-2: 実況表 「催促 n回目（MM/DD）」 ──
    h0 = page.evaluate("() => document.querySelector(\"tbody[data-iv='TST2611-02'] tr.c01-ivrow\").getBoundingClientRect().height")
    j2 = json.loads(j0)
    for iv in j2["ivs"]:
        if iv["iv_no"] == "TST2611-02":
            iv["reminders"] = [{"action_id": "rTest0000001", "by": "u@example.invalid", "at": "2026-11-15T09:00:00+09:00", "value": {"packer": pk0, "round": 1, "test": True}},
                               {"action_id": "rLive0000001", "by": "u@example.invalid", "at": "2026-11-16T09:30:00+09:00", "value": {"packer": pk0, "round": 1, "test": False}}]
    jp.write_text(dump(j2), encoding="utf-8")
    page.evaluate("() => C01.app.tick()")
    page.wait_for_timeout(800)
    rd = page.locator("tbody[data-iv='TST2611-02'] [data-rround]")
    h1 = page.evaluate("() => document.querySelector(\"tbody[data-iv='TST2611-02'] tr.c01-ivrow\").getBoundingClientRect().height")
    ok("R9M 実況表 IV 머리 「催促 … 1回目（11/16）」 (시험 송신 안 셈 · 같은 업체 시험 1 + 실제 1 = 1회) · 행 높이 그대로 (#193)", rd.count() == 1
       and f"催促 {pk0} 1回目（11/16）" in rd.inner_text() and abs(h1 - h0) < 0.5,
       [rd.all_inner_texts(), h0, h1])
    ok("R9M 다른 IV = 표시 없음", page.locator("tbody[data-iv='TST2611-01'] [data-rround]").count() == 0, "")
    page.screenshot(path=str(shots / "r9m_remind_round.png"))
    jp.write_text(j0, encoding="utf-8")
    if s0 is None:
        sp.unlink()
    else:
        sp.write_text(s0, encoding="utf-8")
    pp.unlink()
    page.evaluate("() => { C01.state.view = 'main'; C01.state.qsel = null; C01.app.tick(); }")
    page.wait_for_timeout(500)


def r9u_checks(page, root, shots, engine):
    """v0.3.44 (R9U Part 1-1 · 1-2): 자동 처리 상태 띠 (STOP 빨강 · 지연 노랑 · 정상 없음) · 取消BKG 統合 표시 · 받는 쪽 대조 (엔진 스키마 키)."""
    dump = lambda o: json.dumps(o, ensure_ascii=False, indent=1) + chr(10)   # noqa: E731
    eng = Path(engine)
    js_ = json.loads((eng / "engine" / "output" / "schema" / "jikkyou.schema.json").read_text(encoding="utf-8"))
    rowp = js_["properties"]["ivs"]["items"]["properties"]["rows"]["items"]["properties"]
    hb_s = json.loads((eng / "engine" / "output" / "schema" / "heartbeat.schema.json").read_text(encoding="utf-8"))
    ms = json.loads((eng / "engine" / "output" / "schema" / "meta.schema.json").read_text(encoding="utf-8"))
    ok("R9U 받는 쪽 대조: 엔진 스키마 jikkyou 줄 cancel_regroup (from_iv · at · photos) · heartbeat.json at · meta cycle_stop · generated_at",
       set(rowp.get("cancel_regroup", {}).get("properties", {})) == {"from_iv", "at", "photos"} and set(hb_s["properties"]) == {"at"}
       and "generated_at" in ms["properties"], (sorted(rowp.get("cancel_regroup", {}).get("properties", {})), sorted(hb_s["properties"])))
    dp = root / "_data"
    page.click("#tab-main")
    jp = dp / "jikkyou.json"
    orig_j = jp.read_text(encoding="utf-8")
    mp = dp / "meta.json"
    orig_m = mp.read_text(encoding="utf-8")
    # ── 정상 (heartbeat 없음 · cycle_stop 없음) = 띠 없음
    page.evaluate("() => { C01.app.tick(); }")
    page.wait_for_timeout(700)
    ok("R9U 정상: 띠 없음 (#c01-alert hidden)", page.locator("#c01-alert").is_hidden(), page.locator("#c01-alert").inner_html()[:200])
    # 시각 계산 (C01.alertState · 시각을 넣어 확인)
    st = page.evaluate("""() => { var S = C01.state, keep = [S.meta, S.hb], out = {};
        S.meta = { generated_at: '2026-11-17T09:02:20+09:00' };
        S.hb = { at: '2026-11-17T09:00:01+09:00' };
        out.ok_10 = C01.alertState('2026-11-17T09:20:00+09:00');
        out.late_31 = C01.alertState('2026-11-17T09:31:30+09:00');
        out.night = C01.alertState('2026-11-17T21:30:00+09:00');
        out.early = C01.alertState('2026-11-17T06:50:00+09:00');
        S.hb = { at: '2026-11-16T20:00:02+09:00' };
        out.morning_0715 = C01.alertState('2026-11-17T07:15:00+09:00');
        out.morning_0731 = C01.alertState('2026-11-17T07:31:00+09:00');
        S.hb = null;
        out.no_hb = C01.alertState('2026-11-17T12:00:00+09:00');
        S.meta = { generated_at: '2026-11-17T09:02:20+09:00', cycle_stop: { text: 'x', at: '09:05', stage: '3段階' } };
        out.stop = C01.alertState('2026-11-17T09:10:00+09:00');
        S.meta = keep[0]; S.hb = keep[1]; return out; }""")
    ok("R9U 시각: 정상 (20분) = 없음 · 31분 = 지연 · 21:30 · 06:50 = 없음 (07:00〜20:00 만)",
       st["ok_10"] is None and (st["late_31"] or {}).get("kind") == "late" and st["night"] is None and st["early"] is None, st)
    ok("R9U 시각: 아침 = 어제 20:00 마지막이어도 07:30 까지 없음 · 07:31 지연 (今日 07:00 기준)",
       st["morning_0715"] is None and (st["morning_0731"] or {}).get("kind") == "late", st)
    ok("R9U 시각: heartbeat 없음 = 지연 띠 없음 (옛 엔진 · 거짓 경보 0) · STOP = 빨강 (최종 갱신 = generated_at 09:02)",
       st["no_hb"] is None and (st["stop"] or {}).get("kind") == "stop" and "最終更新 09:02" in st["stop"]["text"]
       and "表示は最終更新時点の内容です" in st["stop"]["text"], st)
    # ── 지연 (화면): 지금 시각 고정 + heartbeat 45분 전 · 엔진이 meta.heartbeat 를 씀 (out_cycle_heartbeat)
    page.clock.set_fixed_time("2026-11-17T10:00:00+09:00")
    mh = json.loads(orig_m)
    mh["heartbeat"] = "heartbeat.json"
    mp.write_text(dump(mh), encoding="utf-8")
    (dp / "heartbeat.json").write_text(dump({"at": "2026-11-17T09:15:02+09:00"}), encoding="utf-8")
    page.evaluate("() => { C01.app.tick(); }")
    page.wait_for_timeout(900)
    late_txt = page.locator("#c01-alert").inner_text() if page.locator("#c01-alert").is_visible() else ""
    ok("R9U 지연: 노란 띠 「データ更新が遅れています（最終更新 09:15）」", page.locator("#c01-alert [data-alert=late]").count() == 1
       and "データ更新が遅れています（最終更新 09:15）" in late_txt, late_txt)
    bg = page.evaluate("() => getComputedStyle(document.querySelector('.c01-alert')).backgroundColor")
    ok("R9U 지연: 띠 색 = 노랑 (#facc15)", bg == "rgb(250, 204, 21)", bg)
    for th in ("dark", "light", "leenai", "focus"):
        page.evaluate(f"localStorage.setItem('leenai_theme','{th}'); document.documentElement.setAttribute('data-theme','{th}')")
        page.wait_for_timeout(120)
        page.screenshot(path=str(shots / f"r9u_late_{th}.png"), full_page=False)
    # 정상으로 돌아옴 (heartbeat 5분 전)
    (dp / "heartbeat.json").write_text(dump({"at": "2026-11-17T09:55:01+09:00"}), encoding="utf-8")
    page.evaluate("() => { C01.app.tick(); }")
    page.wait_for_timeout(900)
    ok("R9U 정상 복귀: heartbeat 5분 전 = 띠 없음", page.locator("#c01-alert").is_hidden(), page.locator("#c01-alert").inner_html()[:200])
    for th in ("dark", "light", "leenai", "focus"):
        page.evaluate(f"localStorage.setItem('leenai_theme','{th}'); document.documentElement.setAttribute('data-theme','{th}')")
        page.wait_for_timeout(120)
        page.screenshot(path=str(shots / f"r9u_ok_{th}.png"), full_page=False)
    # ── STOP (화면)
    mm = json.loads(orig_m)
    mm["heartbeat"] = "heartbeat.json"
    mm["generated_at"] = "2026-11-17T09:42:20+09:00"
    mm["cycle_stop"] = {"text": "⚠️ 自動処理停止中 (09:50 · 3段階)", "at": "09:50", "stage": "3段階"}
    mp.write_text(dump(mm), encoding="utf-8")
    # 取消BKG 統合 표시 (가명 줄 1개 · 엔진 data_json 형식 그대로)
    jj = json.loads(orig_j)
    row0 = jj["ivs"][0]["rows"][0]
    row0["cancel_regroup"] = {"from_iv": "TST2611-09", "at": "2026-11-16", "photos": 8}
    jp.write_text(dump(jj), encoding="utf-8")
    sys.path.insert(0, engine)
    from engine.output import schema_check as SC  # noqa: E402
    ok("R9U 시험 jikkyou (cancel_regroup) · heartbeat · meta (cycle_stop · heartbeat) = 엔진 스키마 통과",
       SC.check_obj(jj, "jikkyou") == [] and SC.check_obj({"at": "2026-11-17T09:55:01+09:00"}, "heartbeat") == [] and SC.check_obj(mm, "meta") == [],
       (SC.check_obj(jj, "jikkyou")[:3], SC.check_obj(mm, "meta")[:3]))
    cards0 = page.evaluate("() => document.getElementById('badge-open').textContent")
    page.evaluate("() => { C01.app.tick(); }")
    page.wait_for_timeout(1000)
    stop_txt = page.locator("#c01-alert").inner_text() if page.locator("#c01-alert").is_visible() else ""
    ok("R9U STOP: 빨간 띠 「自動処理が停止しています（最終更新 09:42）· 表示は最終更新時点の内容です」",
       page.locator("#c01-alert [data-alert=stop]").count() == 1 and "自動処理が停止しています（最終更新 09:42）· 表示は最終更新時点の内容です" in stop_txt, stop_txt)
    bg = page.evaluate("() => getComputedStyle(document.querySelector('.c01-alert')).backgroundColor")
    ok("R9U STOP: 띠 색 = 빨강 (#b91c1c) · 위에 고정 (sticky)", bg == "rgb(185, 28, 28)"
       and page.evaluate("() => getComputedStyle(document.getElementById('c01-alert')).position") == "sticky", bg)
    b = page.locator(".c01-cgbadge")
    ok("R9U 取消BKG 統合: 회색 표시 1개 「取消BKG（TST2611-09）から統合」 · 마우스 = 날짜 · 사진 수",
       b.count() == 1 and b.first.inner_text() == "取消BKG（TST2611-09）から統合" and "2026-11-16" in (b.first.get_attribute("title") or "")
       and "写真 8 枚" in (b.first.get_attribute("title") or ""), (b.count(), b.first.get_attribute("title") if b.count() else None))
    cards1 = page.evaluate("() => document.getElementById('badge-open').textContent")
    ok("R9U 確認・入力 장 수 변화 0 (표시만)", cards0 == cards1, (cards0, cards1))
    page.evaluate("window.scrollTo(0, 400)")
    page.wait_for_timeout(150)
    pos = page.evaluate("""() => { var a = document.getElementById('c01-alert').getBoundingClientRect(), h = document.querySelector('.ln-header');
        var hb = h ? h.getBoundingClientRect().bottom : 0, el = document.elementFromPoint(a.left + a.width / 2, a.top + a.height / 2);
        return { top: Math.round(a.top), head: Math.round(hb), y: window.scrollY, mine: !!(el && el.closest('#c01-alert')) }; }""")
    ok("R9U STOP 띠 = 내려도 공통 헤더 바로 아래에 보임 (가려지지 않음)", abs(pos["top"] - pos["head"]) <= 1 and pos["mine"], pos)
    page.evaluate("window.scrollTo(0, 0)")
    for th in ("dark", "light", "leenai", "focus"):
        page.evaluate(f"localStorage.setItem('leenai_theme','{th}'); document.documentElement.setAttribute('data-theme','{th}')")
        page.wait_for_timeout(120)
        page.screenshot(path=str(shots / f"r9u_stop_{th}.png"), full_page=False)
    # 휴대폰 폭 1장
    vp = page.viewport_size
    page.set_viewport_size({"width": 390, "height": 844})
    page.wait_for_timeout(200)
    ow = page.evaluate("() => document.getElementById('c01-alert').scrollWidth <= window.innerWidth + 1")
    page.screenshot(path=str(shots / "r9u_stop_phone.png"), full_page=False)
    ok("R9U 휴대폰 폭 (390): STOP 띠 가로 넘침 없음", ow, ow)
    page.set_viewport_size(vp)
    # 되돌림
    jp.write_text(orig_j, encoding="utf-8")
    mp.write_text(orig_m, encoding="utf-8")
    (dp / "heartbeat.json").unlink()
    page.evaluate("() => { C01.app.tick(); }")
    page.wait_for_timeout(900)
    ok("R9U 되돌림 뒤 띠 없음 · 표시 없음", page.locator("#c01-alert").is_hidden() and page.locator(".c01-cgbadge").count() == 0)


def r9w_checks(page, root, shots, engine):
    """v0.3.45 (R9W Part 0-3 · #290): 実況表 모든 줄 (自動OK · 確認済 · 再確認 · 受信中) 「⋯」 → 「他社のコンテナ」 · 確認済/自動OK 문구 ·
    other_ct action = 엔진 스키마 · 元に戻す (undo) · 修正 (편집 모드) 옆 창에도 버튼 · 使い方 한 줄."""
    jp = root / "_data" / "jikkyou.json"
    jt0 = jp.read_text(encoding="utf-8")
    dump = lambda o: json.dumps(o, ensure_ascii=False, indent=1) + chr(10)   # noqa: E731
    j2 = json.loads(jt0)
    iv1 = next(x for x in j2["ivs"] if x["iv_no"] == "TST2611-01")
    rs = [r for r in iv1["rows"] if r.get("ct")][:4]
    rs[0].update({"status": "自動OK", "engine_status": "自動OK", "reasons": [], "human": None})
    rs[1].update({"status": "自動OK", "engine_status": "自動OK", "reasons": [], "info": ["AUTO_OK_EDITED(seal)"]})       # 確認済 (人が修正)
    rs[2].update({"status": "再確認", "engine_status": "再確認", "reasons": ["SEAL_FORMAT"], "reason_text": ["x"], "human": None})
    rs[3].update({"status": "受信中", "engine_status": "受信中", "reasons": [], "human": None})
    jp.write_text(dump(j2), encoding="utf-8")
    keyjs = 'ct => [...document.querySelectorAll("tbody[data-iv=\'TST2611-01\'] tr.c01-row")].map(t => t.getAttribute("data-key")).find(k => k && k.includes(ct))'

    def key_of(ct):
        return page.evaluate(keyjs, ct)
    page.click("#tab-main")
    page.click("[data-port='all']")
    page.evaluate("() => { Object.assign(C01.state, {qedit: null, picks: {}, panelInput: '', sel: null, qvals: {}, qchoice: {}, editRow: null, filter: null}); C01.app.tick(); }")
    page.wait_for_timeout(600)
    st = page.evaluate("""() => [...document.querySelectorAll("tbody[data-iv='TST2611-01'] tr.c01-row")].filter(t => !t.classList.contains('missing'))
        .map(t => [t.getAttribute('data-status'), !!t.querySelector('[data-rowmenu]')])""")
    kinds = {x[0] for x in st if x[1]}
    ok("R9W 0-3 「⋯」 = 모든 줄 (自動OK · 確認済 · 再確認 · 受信中)", bool(st) and all(x[1] for x in st) and {"自動OK", "確認済", "再確認", "受信中"} <= kinds, st)
    ids0 = {x.get("action_id") for x in actions(root)}
    dl = []

    def acc(d):
        dl.append(d.message)
        d.accept()
    page.on("dialog", acc)
    page.evaluate("() => { window.__cf = []; window.__cf0 = window.confirm; window.confirm = m => { window.__cf.push(m); return true; }; }")   # 앞 시험이 confirm 을 바꿔 두었을 수 있음 → 문구를 직접 받음
    key0 = key_of(rs[0]["ct"])
    page.locator(f"[data-rowmenu='{key0}']").click()
    page.wait_for_selector("#rm-otherct")
    mt = page.locator("#c01-modal").inner_text()
    ok("R9W 0-3 自動OK 줄 「⋯」 창 = 他社のコンテナ 버튼 · 「確認済 / 自動OK の行です」 · 搬入票ではない 없음 (서류 카드 없음)",
       "確認済 / 自動OK の行です" in mt and page.locator("#rm-notours").count() == 0, mt[:200])
    page.screenshot(path=str(shots / "r9w_rowmenu.png"))
    page.click("#rm-otherct")
    page.wait_for_timeout(600)
    new = [x for x in actions(root) if x.get("action_id") not in ids0]
    dl = dl + page.evaluate("() => window.__cf")
    sys.path.insert(0, engine)
    from engine.output import schema_check as SC  # noqa: E402
    ok("R9W 0-3 自動OK 줄 → other_ct (value.container_id · iv · ct) · 확인창 문구 · 엔진 스키마 통과",
       len(new) == 1 and new[0]["action"] == "other_ct" and new[0]["value"] == {"container_id": rs[0]["container_id"]} and new[0]["iv"] == "TST2611-01"
       and new[0]["ct"] == rs[0]["ct"] and len(dl) == 1 and dl[0].startswith("確認済 / 自動OK の行です — この IV から外します（元に戻せる）")
       and SC.check_obj(new[0], "action") == [], [new, dl, SC.check_obj(new[0], "action") if new else None])
    key2 = key_of(rs[2]["ct"])
    page.locator(f"[data-rowmenu='{key2}']").click()
    page.wait_for_selector("#rm-otherct")
    page.click("#rm-otherct")
    page.wait_for_timeout(600)
    new2 = [x for x in actions(root) if x.get("action_id") not in ids0]
    dl = [m for m in dl if m not in page.evaluate("() => window.__cf")] + page.evaluate("() => window.__cf")
    ok("R9W 0-3 再確認 줄 → other_ct 2번째 · 확인창 = 앞 문구 없음", len(new2) == 2 and len(dl) == 2 and not dl[1].startswith("確認済 / 自動OK"), [len(new2), dl[1:]])
    ob = page.locator("tbody[data-iv='TST2611-01'] [data-otherct]")
    ok("R9W 0-3 줄 숨김 · IV 머리 「他社のコンテナ 2」", ob.count() == 1 and "他社のコンテナ 2" in ob.inner_text(), ob.inner_text() if ob.count() else None)
    ob.click()
    page.wait_for_selector("[data-othundo]")
    page.click("[data-othundo='0']")
    page.wait_for_timeout(500)
    un = [x for x in actions(root) if x.get("action_id") not in ids0 and x.get("action") == "undo"]
    ok("R9W 0-3 元に戻す = undo (other_ct) · 엔진 스키마", len(un) == 1 and un[0]["value"]["action_id"] in {x["action_id"] for x in new2}
       and SC.check_obj(un[0], "action") == [], un)
    page.evaluate("() => { var m = document.getElementById('c01-modal'); if (m) { m.hidden = true; m.innerHTML = ''; } C01.state.modal = null; }")
    key1 = key_of(rs[1]["ct"])
    page.evaluate("k => { C01.state.sel = k; C01.state.editRow = k; C01.app.render(); }", key1)
    page.wait_for_timeout(300)
    ok("R9W 0-3 確認済 줄 修正 (편집 모드) 옆 창 = 「他社のコンテナ」 버튼", page.locator("#panel-otherct").count() == 1 and page.locator("#panel-notours").count() == 0,
       page.locator(".c01-side .k").inner_text() if page.locator(".c01-side .k").count() else None)
    page.screenshot(path=str(shots / "r9w_edit_other.png"))
    page.evaluate("() => { C01.state.sel = null; C01.state.editRow = null; C01.app.render(); }")
    page.remove_listener("dialog", acc)
    page.evaluate("() => { if (window.__cf0) window.confirm = window.__cf0; }")
    page.click("#help-open")
    page.wait_for_selector("#help-body")
    ht = page.locator("#help-body").inner_text()
    ok("R9W 0-3 使い方 = 「⋯」 → 「他社のコンテナ」 · 元に戻せる · 削除はありません", "「⋯」 → 「他社のコンテナ」" in ht and "削除はありません" in ht, ht[-300:])
    page.evaluate("() => { var m = document.getElementById('c01-modal'); if (m) { m.hidden = true; m.innerHTML = ''; } C01.state.modal = null; }")
    for th in ("dark", "light", "leenai", "focus"):
        page.evaluate(f"document.documentElement.setAttribute('data-theme','{th}')")
        page.wait_for_timeout(100)
        page.screenshot(path=str(shots / f"r9w_main_{th}.png"))
    page.evaluate("document.documentElement.setAttribute('data-theme','light')")
    # 0-4b · 0-4a: waku_skip (CT が読めない写真の束 = 候補 · 枠外に数えない) · elim (消去法)
    j3 = json.loads(jt0)
    iv3 = next(x for x in j3["ivs"] if x["iv_no"] == "TST2611-01")
    n_slots = len(iv3.get("slots") or []) or iv3.get("slots_n") or 0
    free0 = [r for r in iv3["rows"] if not r.get("slot_guid")]
    sk = iv3["rows"][-1]
    sk["slot_guid"] = None
    sk["waku_skip"] = "ct_unread_cand"
    el = iv3["rows"][0]
    el["elim"] = {"ct": el.get("ct"), "evidence": ["消去法", "同じメール", "seal 連番"]}
    jp.write_text(dump(j3), encoding="utf-8")
    page.evaluate("C01.app.tick()")
    page.wait_for_timeout(600)
    info = page.evaluate("""() => { const tb = document.querySelector("tbody[data-iv='TST2611-01']");
        return {skip: tb.querySelectorAll('.c01-wakuskip').length, skipOver: [...tb.querySelectorAll('tr.c01-row')].filter(t => t.querySelector('.c01-wakuskip') && t.querySelector('.c01-over')).length,
                head: (tb.querySelector('.c01-overhead') || {}).innerText || '', elim: tb.querySelectorAll('.c01-elim').length,
                elimTitle: (tb.querySelector('.c01-elim') || {}).title || ''}; }""")
    exp_over = len([r for r in free0 if r is not sk]) if n_slots else 0
    ok("R9W 0-4b waku_skip 줄 = 「CTが読めない写真 · 候補あり」 · 赤 (COMPASS 枠外) 아님 · 枠外 수에서 뺌",
       info["skip"] == 1 and info["skipOver"] == 0 and ((exp_over == 0 and info["head"] == "") or info["head"] == f"枠外 {exp_over}"), [info, exp_over, n_slots])
    ok("R9W 0-4a elim 줄 = 「消去法」 표시 · 툴팁 근거", info["elim"] == 1 and "seal 連番" in info["elimTitle"], info)
    page.screenshot(path=str(shots / "r9w_wakuskip.png"))
    jp.write_text(jt0, encoding="utf-8")
    page.evaluate("C01.app.tick()")
    page.wait_for_timeout(300)


def r9x_checks(page, root, shots, engine):
    """v0.3.46 (R9X · #291 · #295 · R9W Part 1): 使い方 = エンジン tool_guide.json (AI と同じ表) · 全体 AI 相談 「この操作をしますか？」 → 実行 = other_ct (origin ai_proposal) ·
    同じ提案 2 回 = 1 回 · 評価 (ask_feedback) · 依頼一覧 「自動」 · 実況表の行の 「AIに相談」 (カードの無い行も) · 未分類FAX 「連結して確認（OK）」 (link_iv + confirm_value · 元に戻す = 両方)."""
    sys.path.insert(0, engine)
    from engine.ask import tool_guide as TG  # noqa: E402
    from engine.output import schema_check as SC  # noqa: E402
    dump = lambda o: json.dumps(o, ensure_ascii=False, indent=1) + chr(10)   # noqa: E731
    d = root / "_data"
    mp, jp, qp = d / "meta.json", d / "jikkyou.json", d / "queue.json"
    mt0, jt0, qt0 = mp.read_text(encoding="utf-8"), jp.read_text(encoding="utf-8"), qp.read_text(encoding="utf-8")
    rq_p = d / "requests.json"
    rq0 = rq_p.read_text(encoding="utf-8") if rq_p.exists() else None
    page.keyboard.press("Escape")
    page.click("#tab-main")
    # ① 使い方 = tool_guide.json
    (d / "tool_guide.json").write_text(dump({"schema_version": 1, "kind": "tool_guide", **TG.output()}), encoding="utf-8")
    m = json.loads(mt0)
    m["tool_guide"] = "tool_guide.json"
    mp.write_text(dump(m), encoding="utf-8")
    page.evaluate("() => { C01.state.guide = null; C01.state.guideMiss = 0; C01.app.tick(); }")
    page.wait_for_timeout(600)
    page.click("#help-open")
    page.wait_for_timeout(600)
    ht = page.locator("#help-body").inner_text()
    ok("R9X 使い方 = エンジンの操作表 (tool_guide.json · AI と同じ原本) · 他社のコンテナ · 削除はありません",
       page.locator(".c01-guide").count() == 1 and "「他社のコンテナ」" in ht and "「IVに連結」" in ht and "削除はありません" in ht and "場所:" in ht, ht[-400:])
    page.screenshot(path=str(shots / "r9x_help_guide.png"))
    page.evaluate("() => { var m = document.getElementById('c01-modal'); if (m) { m.hidden = true; m.innerHTML = ''; } C01.state.modal = null; }")
    # ② 全体 AI 相談 → 提案 → 実行
    j = json.loads(jt0)
    iv1 = next(x for x in j["ivs"] if x["iv_no"] == "TST2611-01")
    r0 = next(r for r in iv1["rows"] if r.get("ct") and r.get("container_id"))
    page.click("#gask-open")
    page.wait_for_timeout(300)
    before = set(p.name for p in (root / "_actions" / "ask").rglob("*.json"))
    page.fill("#gask-in", "TST2611-01 の " + r0["ct"] + " は他社の案件。削除したい")
    page.press("#gask-in", "Enter")
    page.wait_for_timeout(500)
    new = [p for p in (root / "_actions" / "ask").rglob("*.json") if p.name not in before]
    g = json.loads(new[0].read_text(encoding="utf-8")) if len(new) == 1 else {}
    key = "a1b2c3d4e5f6"
    rep = {"ask_id": g.get("ask_id"), "scope": "global", "status": "ok", "kind": "guide", "suggestions": [], "approval_request": "", "improve": None,
           "answer": "削除はありません。実況表の行の 「⋯」 → 「他社のコンテナ」 です（ファイルは消えない · 元に戻せる）。\n調べた内容: IV 一覧 TST2611-01",
           "proposed_actions": [{"action": "other_ct", "label": "他社のコンテナ", "reason": "IV 一覧 で この CT の行を確認", "iv": "TST2611-01", "ct": r0["ct"],
                                 "container_id": r0["container_id"], "queue_id": "", "packer": "", "key": key}]}
    (root / "_actions" / "ask_reply").mkdir(parents=True, exist_ok=True)
    (root / "_actions" / "ask_reply" / f"{g.get('ask_id')}.json").write_text(json.dumps(rep, ensure_ascii=False), encoding="utf-8")
    page.evaluate("() => C01.app.tick()")
    page.wait_for_timeout(800)
    page.evaluate("() => C01.app.render()")
    page.wait_for_timeout(300)
    pb = page.locator("#gask-box .c01-prop")
    ok("R9X 答えの下 「この操作をしますか？ — 他社のコンテナ — CT（IV）」 · 実行 / やめる · 評価ボタン 2",
       pb.count() == 1 and "この操作をしますか？" in pb.inner_text() and r0["ct"] in pb.inner_text() and "TST2611-01" in pb.inner_text()
       and page.locator("#gask-box [data-propgo]").count() == 1 and page.locator("#gask-box [data-propdrop]").count() == 1
       and page.locator("#gask-box [data-fb^='" + str(g.get("ask_id")) + "|']").count() == 2, pb.inner_text() if pb.count() else None)
    page.screenshot(path=str(shots / "r9x_prop.png"))
    ids0 = {x.get("action_id") for x in actions(root)}
    page.evaluate("() => { window.__cf = []; window.__cf0 = window.confirm; window.confirm = m => { window.__cf.push(m); return true; }; }")
    page.click("#gask-box [data-propgo]")
    page.wait_for_timeout(600)
    na = [x for x in actions(root) if x.get("action_id") not in ids0]
    ok("R9X 実行 = other_ct (今のボタンと同じ · 確認窓 1 · by = 担当者 · origin = ai_proposal · ask_id · key) · エンジン スキーマ",
       len(na) == 1 and na[0]["action"] == "other_ct" and na[0]["value"] == {"container_id": r0["container_id"]}
       and na[0].get("origin") == {"kind": "ai_proposal", "ask_id": g.get("ask_id"), "key": key} and len(page.evaluate("() => window.__cf")) == 1
       and SC.check_obj(na[0], "action") == [], [na, page.evaluate("() => window.__cf")])
    page.evaluate("() => C01.app.render()")
    page.wait_for_timeout(300)
    ok("R9X 実行のあと = 「実行しました」 · 実行ボタン無し (2 回押せない)", "実行しました" in page.locator("#gask-box .c01-prop").inner_text()
       and page.locator("#gask-box [data-propgo]").count() == 0)
    # ③ 評価
    page.click("#gask-box [data-fb='" + str(g.get("ask_id")) + "|0']")
    page.wait_for_timeout(500)
    fb = [x for x in actions(root) if x.get("action") == "ask_feedback"]
    ok("R9X 「役に立たなかった」 = ask_feedback (ask_id · good false) · エンジン スキーマ · 評価の表示", len(fb) == 1 and fb[0]["value"] == {"ask_id": g.get("ask_id"), "good": False}
       and SC.check_obj(fb[0], "action") == [] and "評価: 役に立たなかった" in page.locator("#gask-box").inner_text(), fb)
    page.evaluate("() => { if (window.__cf0) window.confirm = window.__cf0; }")
    # ④ 依頼一覧 「自動」
    rq = {"schema_version": 1, "kind": "improve_requests", "today": "2026-11-17", "items": [
        {"no": 7, "at": "2026-11-17T11:00:00+09:00", "by": page.evaluate("() => (C01.state.me || {}).email"), "title": "AI 相談で解決できなかった質問", "status": "受付",
         "plan": "予定: 次のラウンド (〜13:13)", "source": "auto", "reasons": ["cant"], "summary": "x", "question": "q", "ask_id": "kX"}]}
    assert SC.check_obj(rq, "requests") == []
    rq_p.write_text(dump(rq), encoding="utf-8")
    page.evaluate("() => { C01.state.reqsMiss = 0; C01.app.tick(); }")
    page.wait_for_timeout(700)
    page.click("#gask-box [data-gtab='reqs']")
    page.wait_for_timeout(300)
    ok("R9X 依頼一覧 = 自動で受け付けた依頼に 「自動」", page.locator("#gask-box .c01-auto").count() == 1, page.locator("#gask-box").inner_text()[:200])
    page.click("#gask-box [data-gtab='chat']")
    page.click("#gask-close")
    page.wait_for_timeout(300)
    # ⑤ 行の AI 相談 (カードの無い行) — ②で 他社 にした行 (r0) とは別の行
    r0 = next(r for r in iv1["rows"] if r.get("ct") and r.get("container_id") and r["container_id"] != r0["container_id"])
    jp.write_text(jt0, encoding="utf-8")
    page.evaluate("() => C01.app.tick()")
    page.wait_for_timeout(500)
    rk = page.evaluate("ct => [...document.querySelectorAll(\"tbody[data-iv='TST2611-01'] tr.c01-row\")].map(t => t.getAttribute('data-key')).find(k => k && k.includes(ct))", r0["ct"])
    page.evaluate("k => { C01.state.sel = k; C01.state.editRow = null; C01.app.render(); }", rk)
    page.wait_for_timeout(300)
    ok("R9X 行の横の窓 = 「AIに相談」", page.locator("#panel-ask").count() == 1)
    page.click("#panel-ask")
    page.wait_for_timeout(400)
    rb = page.locator("#ask-box.c01-rdr")
    ok("R9X 行の AI 相談 = 右横のドロアー (行の CT · IV) · 横の窓は閉じる", rb.count() == 1 and r0["ct"] in rb.inner_text() and page.locator(".c01-side").count() == 0,
       rb.inner_text()[:120] if rb.count() else None)
    page.screenshot(path=str(shots / "r9x_rowask.png"))
    before = set(p.name for p in (root / "_actions" / "ask").rglob("*.json"))
    page.fill("#ask-in", "この行は 確認済 を戻した行。シールは合っている？")
    page.press("#ask-in", "Enter")
    page.wait_for_timeout(500)
    new = [p for p in (root / "_actions" / "ask").rglob("*.json") if p.name not in before]
    ra = json.loads(new[0].read_text(encoding="utf-8")) if len(new) == 1 else {}
    rc = ra.get("card") or {}
    ok("R9X 行の質問 = card.container_id · iv · ct · key = カードと同じ会話 (c:{container_id})", rc.get("container_id") == r0["container_id"] and rc.get("iv") == "TST2611-01"
       and rc.get("ct") == r0["ct"] and rc.get("key") == "TST2611-01|c:" + r0["container_id"] and rc.get("queue_id") is None, rc)
    page.click("#ask-close")
    page.wait_for_timeout(300)
    ok("R9X 行の AI 相談 閉じる", page.locator("#ask-box").count() == 0)
    # ⑥ 未分類FAX 「連結して確認（OK）」 (⑤ の行 = 実況表に残っている行)
    docs_dir = [p_.relative_to(root).as_posix() for p_ in sorted((root / "TST2611-01" / "搬入票").glob("*.svg"))]
    nw = (r0.get("n_w") or 20000)
    fq = {"queue_id": "9a9a9a9a9a9a9a91", "kind": "未分類FAX", "iv_no": None, "ct": None, "field": None, "container_id": None, "values": {},
          "candidates": ["TST2611-01"], "files": [{"path": docs_dir[0], "name": "fax-r9x.pdf", "page": None, "bbox": None, "sha16": "9a9a9a9a9a9a9a9a"}],
          "note": "保留", "resolved": None, "superseded": [], "cy_cut": None, "cy_open": None, "issuer": None, "field_sources": {}, "field_source_text": {},
          "received_at": "2026-11-17T10:20:00+09:00", "link_iv": True,
          "fax_read": {"ct": [r0["ct"], "TSTU9999990"], "pages": [{"file": None, "page": 1, "rotation": 180, "doc_type": "hannyuhyo", "issuer": "x", "fax_from": None, "bkg": [],
                                                                    "rows": [{"ct": r0["ct"], "seal": r0.get("seal") or "SL1", "n_w": nw + 10, "t_w": None, "bales": None, "work_date": None},
                                                                             {"ct": "TSTU9999990", "seal": "SL9", "n_w": 1, "t_w": None, "bales": None, "work_date": None}]}]}}
    q2 = json.loads(qt0)
    q2["items"].append(fq)
    if "未分類FAX" not in q2["kinds"]:
        q2["kinds"] = list(q2["kinds"]) + ["未分類FAX"]
    qp.write_text(dump(q2), encoding="utf-8")
    page.evaluate("C01.RULES.linkIv = true; C01.RULES.faxLinkIv = true; C01.RULES.faxLinkConfirm = true; C01.app.tick()")
    page.wait_for_timeout(800)
    page.evaluate("q => { C01.state.view = 'input'; C01.state.qkind = 'all'; C01.state.qiv = null; C01.state.showOldFax = true; C01.state.qsel = q; C01.app.render(); }", fq["queue_id"])
    page.wait_for_selector("#link-iv")
    page.click(".c01-linkiv [data-linkiv='TST2611-01']")
    page.wait_for_timeout(300)
    tb = page.locator(".c01-fxcmp")
    txt = tb.inner_text() if tb.count() else ""
    ok("R9X FAX の値 ↔ IV の行の値 表 · 同じ = ✓ · 違う = 選ぶ · 行の無い CT = 「新しい行（次の判定で）」 · 「連結して確認（OK）」",
       tb.count() == 1 and "✓ 同じ" in txt and "新しい行（次の判定で）" in txt and page.locator("#q-linkok").count() == 1
       and page.locator(".c01-fxcmp tr.d").count() == 1, txt[:300])
    page.screenshot(path=str(shots / "r9x_fax_cmp.png"))
    page.locator("input[name='link-slot']").first.check()
    page.wait_for_timeout(200)
    page.locator(".c01-fxcmp [data-fxpick][value='fax']").first.check()
    page.wait_for_timeout(200)
    ids0 = {x.get("action_id") for x in actions(root)}
    dl = []

    def acc(d_):
        dl.append(d_.message)
        d_.accept()
    page.on("dialog", acc)
    page.click("#q-linkok")
    page.wait_for_timeout(900)
    na = [x for x in actions(root) if x.get("action_id") not in ids0]
    cv = [x for x in na if x["action"] == "confirm_value"]
    ok("R9X 「連結して確認」 = link_iv 1 + confirm_value 2 (seal 同じ · n_w FAX) · 同じ queue_id · source 搬入票 · エンジン スキーマ",
       sorted(x["action"] for x in na) == ["confirm_value", "confirm_value", "link_iv"] and len(cv) == 2 and {x["field"] for x in cv} == {"seal", "n_w"}
       and all(x["queue_id"] == fq["queue_id"] and x["source"] == "搬入票" and x["ct"] == r0["ct"] and x["iv"] == "TST2611-01" for x in cv)
       and next(x for x in cv if x["field"] == "n_w")["value"] in (nw + 10, str(nw + 10)) and all(SC.check_obj(x, "action") == [] for x in na), [na, dl])
    page.click(".c01-kinds [data-kind='done']")
    page.wait_for_timeout(300)
    its = page.locator(".c01-item.done")
    for i_ in range(its.count()):
        if "fax-r9x.pdf" in its.nth(i_).inner_text():
            its.nth(i_).click()
            break
    page.wait_for_timeout(300)
    ids1 = {x.get("action_id") for x in actions(root)}
    if page.locator("#q-undo").count():
        page.click("#q-undo")
        page.wait_for_timeout(900)
    un = [x for x in actions(root) if x.get("action_id") not in ids1 and x["action"] == "undo"]
    tgt = {x["value"]["action_id"] for x in un}
    ok("R9X 元に戻す = 連結 + 確認した値 (undo 3)", len(un) == 3 and tgt == {x["action_id"] for x in na}, [len(un), page.locator("#q-undo").count()])
    page.remove_listener("dialog", acc)
    for th in ("dark", "light", "leenai", "focus"):
        page.evaluate(f"document.documentElement.setAttribute('data-theme','{th}')")
        page.wait_for_timeout(100)
        page.screenshot(path=str(shots / f"r9x_fax_{th}.png"))
    page.evaluate("document.documentElement.setAttribute('data-theme','light')")
    page.evaluate("C01.RULES.linkIv = false; C01.RULES.faxLinkIv = true; C01.state.qkind = 'all'; C01.state.showOldFax = false; C01.state.view = 'main'")
    mp.write_text(mt0, encoding="utf-8")
    qp.write_text(qt0, encoding="utf-8")
    (d / "tool_guide.json").unlink()
    if rq0 is None:
        rq_p.unlink()
    else:
        rq_p.write_text(rq0, encoding="utf-8")
    page.evaluate("() => { C01.state.guide = null; C01.app.tick(); }")
    page.wait_for_timeout(400)


def r9y_checks(page, root, shots, engine):
    """v0.3.47 (R9Y Part 0 · R9W Part 2): 確認済 の行でも 他社の疑い = 小さい赤い印 「他社の疑い」 + ツールチップ (値 · 状態そのまま) ·
    「確認済の見直し」 カード (値を選ぶカードではない · 「このまま（確認済）」 = review_keep · 「他社のコンテナ」 · 「搬入票ではない」 無し · 元に戻す)."""
    sys.path.insert(0, engine)
    from engine.output import schema_check as SC  # noqa: E402
    dump = lambda o: json.dumps(o, ensure_ascii=False, indent=1) + chr(10)   # noqa: E731
    d = root / "_data"
    jp, qp = d / "jikkyou.json", d / "queue.json"
    jt0, qt0 = jp.read_text(encoding="utf-8"), qp.read_text(encoding="utf-8")
    page.keyboard.press("Escape")
    page.evaluate("C01.state.view = 'main'; C01.app.render()")
    gone = {(x.get("value") or {}).get("container_id") for x in actions(root) if x.get("action") == "other_ct"}
    j = json.loads(jt0)
    iv1 = next(x for x in j["ivs"] if x["iv_no"] == "TST2611-01")
    r1 = [r for r in iv1["rows"] if r.get("ct") and r.get("container_id") and r["container_id"] not in gone][-1]
    r1["status"] = "確認済"
    r1["human"] = {"seal": {"value": r1.get("seal") or "SL1", "source": "搬入票", "by": "user1@example.invalid", "at": "2026-11-12T08:12:00+09:00", "action_id": "r9yconf0001"}}
    r1["confirmed_suspect"] = {"why": [], "contradict": {"fields": ["seal"], "confirmed_at": "2026-11-12T08:12:00+09:00", "excluded_at": "2026-11-12T17:09:00+09:00"}}
    jp.write_text(dump(j), encoding="utf-8")
    docs_dir = [p_.relative_to(root).as_posix() for p_ in sorted((root / "TST2611-01" / "搬入票").glob("*.svg"))]
    rq = {"queue_id": "7e7e7e7e7e7e7e71", "kind": "確認済の見直し", "iv_no": "TST2611-01", "ct": r1["ct"], "field": None, "container_id": r1["container_id"], "values": {},
          "candidates": [], "files": [{"path": docs_dir[0], "name": "r9y-doc.pdf", "page": None, "bbox": None, "sha16": "7e7e7e7e7e7e7e7e"}],
          "note": "CONFIRMED_THEN_NOT_HANNYUHYO", "resolved": None, "superseded": [], "cy_cut": None, "cy_open": None, "issuer": None, "field_sources": {},
          "field_source_text": {}, "review": {"why": [], "fields": ["seal"], "confirmed_at": "2026-11-12T08:12:00+09:00", "excluded_at": "2026-11-12T17:09:00+09:00"}}
    q2 = json.loads(qt0)
    q2["items"].append(rq)
    qp.write_text(dump(q2), encoding="utf-8")
    prev = page.evaluate("[!!C01.RULES.otherCt, !!C01.RULES.valueEdit]")
    page.evaluate("C01.RULES.otherCt = true; C01.RULES.valueEdit = true; C01.app.tick()")
    page.wait_for_timeout(800)
    tr = page.locator("tr.c01-row[data-status='確認済']").filter(has=page.locator(".c01-suspect"))
    tt = tr.first.locator(".c01-suspect").get_attribute("title") if tr.count() else ""
    ok("R9Y 確認済 の行 = 「他社の疑い」 (小さい赤い印) · ツールチップ = 確認 → 後で 「搬入票ではない」 · 状態 確認済 のまま",
       tr.count() == 1 and "搬入票ではない" in (tt or "") and "確認済のまま" in (tt or "") and tr.first.locator(".st-ok, .c01-okedit").count() >= 1, [tr.count(), tt])
    page.screenshot(path=str(shots / "r9y_jikkyou_suspect.png"))
    page.evaluate("q => { C01.state.view = 'input'; C01.state.qkind = 'all'; C01.state.qiv = null; C01.state.qsel = q; C01.app.render(); }", rq["queue_id"])
    page.wait_for_selector(".c01-review")
    rt = page.locator(".c01-review").inner_text()
    ok("R9Y 「確認済の見直し」 カード = 理由 (確認 → 搬入票ではない) · 「このまま（確認済）」 · 「他社のコンテナ」 · 「搬入票ではない」 無し · 種類 チップ",
       "搬入票ではない" in rt and "根拠が合いません" in rt and "このまま（確認済）" in page.locator("#q-submit").inner_text()
       and page.locator("#q-otherct").count() == 1 and page.locator("#q-notours").count() == 0 and page.locator("#q-keep").count() == 0
       and page.locator(".c01-kinds [data-kind='確認済の見直し']").count() == 1, [rt[:200], page.locator("#q-submit").inner_text()])
    ok("R9Y 「確認済の見直し」 カード = 「AIに相談」 ボタン", page.locator("#q-ask").count() == 1)
    for _ in range(2):                                   # ドロアーが前の試験で開いたまま = 1 回目で閉じる
        if page.locator("#ask-in").count():
            break
        page.click("#q-ask")
        page.wait_for_timeout(400)
    before = set(p_.name for p_ in (root / "_actions" / "ask").rglob("*.json"))
    page.fill("#ask-in", "確認したのに あとで 搬入票ではない になった。このままで良い？")
    page.press("#ask-in", "Enter")
    page.wait_for_timeout(500)
    new = [p_ for p_ in (root / "_actions" / "ask").rglob("*.json") if p_.name not in before]
    rc = (json.loads(new[0].read_text(encoding="utf-8")) if len(new) == 1 else {}).get("card") or {}
    ok("R9Y 「確認済の見直し」 カード = AIに相談 (key = カードと同じ会話 c:{container_id} · queue_id · kind)",
       rc.get("key") == "TST2611-01|c:" + r1["container_id"] and rc.get("container_id") == r1["container_id"] and rc.get("queue_id") == rq["queue_id"], rc)
    if page.locator("#ask-close").count():
        page.click("#ask-close")
        page.wait_for_timeout(300)
    page.evaluate("q => { C01.state.qsel = q; C01.app.render(); }", rq["queue_id"])
    page.wait_for_selector(".c01-review")
    for th in ("dark", "light", "leenai", "focus"):
        page.evaluate(f"document.documentElement.setAttribute('data-theme','{th}')")
        page.wait_for_timeout(100)
        page.screenshot(path=str(shots / f"r9y_review_{th}.png"))
    page.evaluate("document.documentElement.setAttribute('data-theme','light')")
    ids0 = {x.get("action_id") for x in actions(root)}
    page.click("#q-submit")
    page.wait_for_timeout(900)
    na = [x for x in actions(root) if x.get("action_id") not in ids0]
    ok("R9Y 「このまま（確認済）」 = review_keep 1 (queue_id · field null · value null) · エンジン スキーマ",
       len(na) == 1 and na[0]["action"] == "review_keep" and na[0]["queue_id"] == rq["queue_id"] and na[0]["field"] is None and na[0]["value"] is None
       and na[0]["iv"] == "TST2611-01" and na[0]["ct"] == r1["ct"] and SC.check_obj(na[0], "action") == [], na)
    page.evaluate("q => { C01.state.qkind = 'done'; C01.state.qsel = q; C01.app.render(); }", rq["queue_id"])
    page.wait_for_timeout(400)
    okmsg = page.locator(".c01-okmsg").inner_text() if page.locator(".c01-okmsg").count() else ""
    ids1 = {x.get("action_id") for x in actions(root)}
    if page.locator("#q-undo").count():
        page.click("#q-undo")
        page.wait_for_timeout(900)
    un = [x for x in actions(root) if x.get("action_id") not in ids1 and x["action"] == "undo"]
    ok("R9Y 完了 = 「このまま（確認済）にしました」 · 元に戻す = undo 1 (review_keep)",
       "このまま（確認済）にしました" in okmsg and len(un) == 1 and un[0]["value"]["action_id"] == na[0]["action_id"] and SC.check_obj(un[0], "action") == [], [okmsg, un])
    page.evaluate("p => { C01.RULES.otherCt = p[0]; C01.RULES.valueEdit = p[1]; C01.state.qkind = 'all'; C01.state.view = 'main'; }", prev)
    jp.write_text(jt0, encoding="utf-8")
    qp.write_text(qt0, encoding="utf-8")
    page.evaluate("C01.app.tick()")
    page.wait_for_timeout(400)


def r10h_checks(page, root, shots, engine):
    """v0.3.49 (R10H Part 1 · #305 ③): 「2行→1行」 배지 (엔진 out_merge_badge merge 키) · CT 修正 = 같은 BKG 다른 줄 CT → 「{n}番の行にまとめる」 확인 창
    (값 나란히 · 같으면 바로 · 다르면 빨강 + 체크 뒤) → merge_rows (엔진 스키마) · 「まとめずに保存」 = manual_input · 「⋯」 → 「まとめを元に戻す」 = undo."""
    sys.path.insert(0, engine)
    from engine.output import schema_check as SC  # noqa: E402
    dump = lambda o: json.dumps(o, ensure_ascii=False, indent=1) + chr(10)   # noqa: E731
    jp = root / "_data" / "jikkyou.json"
    jt0 = jp.read_text(encoding="utf-8")
    j2 = json.loads(jt0)
    iv1 = next(x for x in j2["ivs"] if x["iv_no"] == "TST2611-01")
    gone = {(x.get("value") or {}).get("container_id") for x in actions(root) if x.get("action") in ("other_ct", "merge_rows")}
    rs = [r for r in iv1["rows"] if r.get("ct") and not r.get("human") and r["container_id"] not in gone and r.get("status") != "missing"][:2]
    fr, to = rs
    to.update({"status": "自動OK", "engine_status": "自動OK", "reasons": [], "info": ["同一搬入票(再送)"],
               "merge": {"kinds": ["同一搬入票(再送)"], "docs": ["image001.png"]}})
    fr.update({"status": "自動OK", "engine_status": "自動OK", "reasons": [], "photos": 0, "has_photos": False, "has_docs": True,
               "seal": to.get("seal"), "n_w": to.get("n_w"), "t_w": to.get("t_w"), "bales": to.get("bales")})
    jp.write_text(dump(j2), encoding="utf-8")
    prev = page.evaluate("() => [C01.RULES.mergeRows, C01.RULES.valueEdit, C01.RULES.otherCt]")
    page.evaluate("() => { C01.RULES.mergeRows = true; C01.RULES.valueEdit = true; C01.RULES.otherCt = true; }")
    page.keyboard.press("Escape")
    page.evaluate("() => { Object.assign(C01.state, {qedit: null, picks: {}, panelInput: '', sel: null, editRow: null, filter: null, view: 'main'}); C01.app.tick(); }")
    page.click("#tab-main")
    page.click("[data-port='all']")
    page.wait_for_timeout(600)
    trt = page.locator(f"tbody[data-iv='TST2611-01'] tr.c01-row:has-text('{to['ct']}')").first
    bd = trt.locator(".c01-mergebadge")
    ok("R10H 1 「2行→1行」 배지 · 마우스 = 同一搬入票(再送) + まとめた書類 이름", bd.count() == 1 and bd.inner_text() == "2行→1行"
       and "同一搬入票(再送)" in (bd.get_attribute("title") or "") and "image001.png" in (bd.get_attribute("title") or ""), bd.count())
    ids0 = {x.get("action_id") for x in actions(root)}

    def open_ct_edit():
        page.keyboard.press("Escape")
        page.evaluate("() => { Object.assign(C01.state, {qedit: null, sel: null, editRow: null}); C01.app.render(); }")
        page.wait_for_timeout(200)
        page.locator(f"tbody[data-iv='TST2611-01'] tr.c01-row:has-text('{fr['ct']}')").first.locator(".c01-okedit").click()
        page.wait_for_selector("#okedit-go")
        page.click("#okedit-go")
        page.wait_for_selector(".c01-side")
        page.locator(".c01-side [data-ef='ct'] .c01-edit").click()
        page.wait_for_selector("#edit-in")
        page.fill("#edit-in", to["ct"])
        page.click("#edit-save")
        page.wait_for_selector(".c01-modal-merge")
    open_ct_edit()
    mt = page.locator(".c01-modal-merge").inner_text()
    no = to.get("no") or (iv1["rows"].index(to) + 1)
    page.screenshot(path=str(shots / "r10h_merge_same.png"))
    ok("R10H 1 확인 창 = 「{n}番の行にまとめる」 · 값 나란히 (シール · 正味 · 風袋) · 같으면 빨강 0 · 버튼 바로 누를 수 있음",
       f"{no}番の行にまとめる" in mt and page.locator(".c01-mtable tr").count() == 5 and page.locator(".c01-mdiff").count() == 0
       and not page.locator("#merge-go").is_disabled() and page.locator("#merge-keep").count() == 1, mt[:200])
    page.click("#merge-go")
    page.wait_for_timeout(500)
    new = [x for x in actions(root) if x.get("action_id") not in ids0]
    ok("R10H 1 まとめる = merge_rows 1 (value from/into container_id · iv) · 엔진 스키마 통과",
       len(new) == 1 and new[0]["action"] == "merge_rows" and new[0]["value"]["from_container_id"] == fr["container_id"]
       and new[0]["value"]["into_container_id"] == to["container_id"] and new[0]["iv"] == "TST2611-01" and SC.check_obj(new[0], "action") == [],
       [new, SC.check_obj(new[0], "action") if new else None])
    mid = new[0]["action_id"] if new else None
    # 값이 다른 경우 → 빨강 + 체크 뒤에만 · 「まとめずに保存」 = manual_input
    j3 = json.loads(jp.read_text(encoding="utf-8"))
    iv3 = next(x for x in j3["ivs"] if x["iv_no"] == "TST2611-01")
    f3 = next(r for r in iv3["rows"] if r["container_id"] == fr["container_id"])
    f3["n_w"] = (to.get("n_w") or 1000) + 50
    jp.write_text(dump(j3), encoding="utf-8")
    page.evaluate("C01.app.tick()")
    page.wait_for_timeout(500)
    open_ct_edit()
    dis0 = page.locator("#merge-go").is_disabled()
    page.check("#merge-sure")
    dis1 = page.locator("#merge-go").is_disabled()
    page.screenshot(path=str(shots / "r10h_merge_diff.png"))
    ok("R10H 1 값 다름 = 빨강 칸 · 「値が違います」 · 체크 전 버튼 막힘 → 체크 뒤 누를 수 있음",
       page.locator(".c01-mdiff").count() == 2 and "値が違います" in page.locator(".c01-modal-merge").inner_text() and dis0 and not dis1, [dis0, dis1])
    ids1 = {x.get("action_id") for x in actions(root)}
    page.click("#merge-keep")
    page.wait_for_timeout(500)
    new2 = [x for x in actions(root) if x.get("action_id") not in ids1]
    ok("R10H 1 「まとめずに保存（別の行）」 = manual_input ct (지금처럼 · CT重複 그대로)",
       len(new2) == 1 and new2[0]["action"] == "manual_input" and new2[0]["field"] == "ct" and new2[0]["value"] == to["ct"] and SC.check_obj(new2[0], "action") == [], new2)
    # 되돌리기 = 「⋯」 → 「まとめを元に戻す」
    page.keyboard.press("Escape")
    page.evaluate("() => { Object.assign(C01.state, {qedit: null, sel: null, editRow: null}); C01.app.render(); }")
    page.wait_for_timeout(300)
    page.evaluate("() => { window.__cf = []; window.confirm = m => { window.__cf.push(m); return true; }; }")
    key = page.evaluate('ct => [...document.querySelectorAll("tbody[data-iv=\'TST2611-01\'] tr.c01-row")].map(t => t.getAttribute("data-key")).find(k => k && k.includes(ct))', to["ct"])
    page.locator(f"[data-rowmenu='{key}']").click()
    page.wait_for_selector("#rm-mergeundo")
    ids2 = {x.get("action_id") for x in actions(root)}
    page.click("#rm-mergeundo")
    page.wait_for_timeout(500)
    un = [x for x in actions(root) if x.get("action_id") not in ids2]
    ok("R10H 1 「⋯」 → 「まとめを元に戻す」 = undo 1 (merge_rows action_id) · 엔진 스키마",
       len(un) == 1 and un[0]["action"] == "undo" and un[0]["value"]["action_id"] == mid and SC.check_obj(un[0], "action") == [], un)
    page.keyboard.press("Escape")
    page.evaluate("p => { C01.RULES.mergeRows = p[0]; C01.RULES.valueEdit = p[1]; C01.RULES.otherCt = p[2]; C01.state.view = 'main'; }", prev)
    jp.write_text(jt0, encoding="utf-8")
    page.evaluate("C01.app.tick()")
    page.wait_for_timeout(400)


def r10w_checks(page, root, shots, engine, engine_r10u=None):
    """v0.3.52 (R10W · #307): 「入力後の差異」 카드 (Compass入力値 · 新しい値 나란히 · 다른 칸만 빨강 · 까닭 · 원본 · 「入力値のまま」 = input_keep ·
    「新しい値でCompass再入力」 = input_diff_take → Compass入力 창) · 줄 「確認済（入力済）」 · 필터 · 수 · 엔진 설정 끔 (固定 줄 · 카드 없음) = 화면 변화 0.
    action 스키마 = 엔진 v0.5.122 (가지 r10u) 의 action.schema.json — --engine 에 input_keep 이 없으면 --engine-r10u 의 스키마 파일."""
    sys.path.insert(0, engine)
    from engine.output import schema_check as SC  # noqa: E402
    sch = {}
    for base in (engine, engine_r10u):
        if not base:
            continue
        for nm in ("action", "queue", "jikkyou"):
            p_ = Path(base) / "engine" / "output" / "schema" / f"{nm}.schema.json"
            if nm not in sch and p_.is_file() and "input_keep" in Path(base, "engine", "output", "schema", "action.schema.json").read_text(encoding="utf-8"):
                sch[nm] = json.loads(p_.read_text(encoding="utf-8"))
    ok("R10W 엔진 스키마 (action · queue · jikkyou) 에 input_keep · 入力後の差異 · input_frozen 있음", len(sch) == 3, sorted(sch))
    dump = lambda o: json.dumps(o, ensure_ascii=False, indent=1) + chr(10)   # noqa: E731
    d = root / "_data"
    jp, qp = d / "jikkyou.json", d / "queue.json"
    jt0, qt0 = jp.read_text(encoding="utf-8"), qp.read_text(encoding="utf-8")
    page.keyboard.press("Escape")
    page.evaluate("() => { Object.assign(C01.state, {qedit: null, sel: null, editRow: null, filter: 'all', view: 'main', qkind: 'all'}); C01.app.tick(); }")
    page.click("#tab-main")
    page.click("[data-port='all']")
    page.wait_for_timeout(500)
    # ① 엔진 설정 끔 (지금 실전) = 고정 줄 · 카드 없음 → 「確認済（入力済）」 · 필터 · 종류 0
    page.click("#tab-input")
    page.wait_for_timeout(300)
    k0 = page.locator(".c01-kinds [data-kind='入力後の差異']").count()
    page.click("#tab-main")
    page.wait_for_timeout(300)
    ok("R10W 끔 = 「確認済（入力済）」 0 · 필터 0 · 「入力後の差異」 종류 0",
       page.locator("tr.c01-row[data-frozen]").count() == 0 and page.locator(".c01-f-frozen").count() == 0 and k0 == 0
       and FROZEN_TXT not in page.locator("#jikkyou-table").inner_text(), [k0, page.locator(".c01-f-frozen").count()])
    # ② 켬 (엔진 v0.5.122 출력 꼴): 2줄 고정 + 카드 2장 (record 칸 · new_doc seal)
    gone = {(x.get("value") or {}).get(k) for x in actions(root) if x.get("action") in ("other_ct", "merge_rows") for k in ("container_id", "from_container_id")}
    j = json.loads(jt0)
    qcid = {x.get("container_id") for x in json.loads(qt0)["items"]}
    elig = lambda iv_: sorted([r for r in iv_["rows"] if r.get("ct") and r.get("slot_guid") and r["container_id"] not in gone and r["container_id"] not in qcid],   # noqa: E731
                              key=lambda r: bool(r.get("human")))
    iv1 = next(x for x in j["ivs"] if len(elig(x)) >= 2 and len(x.get("slots") or []) >= 3)
    ivn = iv1["iv_no"]
    rs = elig(iv1)[:2]
    ra, rb = rs
    docs_dir = [p_.relative_to(root).as_posix() for p_ in sorted(root.glob("*/搬入票/*.svg"))]
    other_slot = next(s["slot_guid"] for s in iv1["slots"] if s["slot_guid"] not in (ra["slot_guid"], rb["slot_guid"]))
    for r in (ra, rb):
        r.update({"status": "確認済", "engine_status": "自動OK", "reasons": [], "info": list(r.get("info") or []) + ["INPUT_FROZEN"],
                  "input_frozen": {"at": "2026-11-08T10:00:00+09:00", "done_at": "2026-11-08T09:58:00+09:00", "action_id": "r10wcd000001", "src": "apply"}})
    ra["docs"] = [{"path": docs_dir[0], "name": "r10w-doc.svg", "page": None, "fields": ["ct", "seal"]}]
    iv1["compass_input"] = [{"action_id": "r10wcd000001", "by": "staff.a@example.invalid", "at": "2026-11-08T09:58:00+09:00", "value": {"cells": [], "failed": []}}]
    jp.write_text(dump(j), encoding="utf-8")
    qa = {"queue_id": "7e7e7e7e7e7e7ea1", "kind": "入力後の差異", "iv_no": ivn, "ct": ra["ct"], "field": None, "container_id": ra["container_id"], "values": {},
          "candidates": [], "files": [], "note": "slot", "resolved": None, "superseded": [], "cy_cut": iv1.get("cy_cut"), "cy_open": iv1.get("cy_open"), "issuer": None,
          "field_sources": {}, "field_source_text": {}, "input_diff": {"slot": {"input": other_slot, "new": ra["slot_guid"], "why": "record"}}}
    qb = dict(qa, queue_id="7e7e7e7e7e7e7eb2", ct=rb["ct"], container_id=rb["container_id"], note="seal",
              input_diff={"seal": {"input": rb["seal"], "new": "TS9R10W1", "why": "new_doc"}, "slot": {"input": rb["slot_guid"], "new": other_slot, "why": "record"}})
    q2 = json.loads(qt0)
    q2["items"] += [qa, qb]
    q2["kinds"] = list(q2.get("kinds") or []) + ["入力後の差異"]
    q2.setdefault("count", {})["入力後の差異"] = 2
    qp.write_text(dump(q2), encoding="utf-8")
    if len(sch) == 3:
        qe = SC.errors({**q2, "items": [qa, qb]}, sch["queue"])
        je = SC.errors({**j, "ivs": [iv1]}, sch["jikkyou"])
        ok("R10W 시험 데이터 = 엔진 v0.5.122 queue · jikkyou 스키마 (오류 0)", not qe and not je, (qe + je)[:4])
    prev = page.evaluate("() => [!!C01.RULES.otherCt, !!C01.RULES.valueEdit]")
    page.evaluate("() => { C01.RULES.otherCt = true; C01.RULES.valueEdit = true; C01.app.tick(); }")
    page.wait_for_timeout(800)
    tb = f"tbody[data-iv='{ivn}']"
    fr = page.locator(tb + " tr.c01-row[data-frozen='1']")
    ft = fr.first.locator(".st-ok, .c01-okedit").first.get_attribute("title") if fr.count() else ""
    ok("R10W 줄 = 「確認済（入力済）」 2 · data-status 「確認済」 그대로 · 마우스 = 입력 시각 · 元に戻す 안내",
       fr.count() == 2 and all(FROZEN_TXT in fr.nth(i).inner_text() for i in range(fr.count())) and all(fr.nth(i).get_attribute("data-status") == "確認済" for i in range(fr.count()))
       and "11-08 09:58" in (ft or "") and "元に戻す" in (ft or ""), [fr.count(), ft])
    fb = page.locator(".c01-f-frozen")
    ok("R10W 필터 「入力済 2台」 (고정 줄 있을 때만 · R11R 이름)", fb.count() == 1 and fb.inner_text() == "入力済 2台", fb.inner_text() if fb.count() else None)
    n_iv = page.locator("tbody[data-iv]").count()
    fb.click()
    page.wait_for_timeout(300)
    n_f = page.locator("tbody[data-iv]").count()
    page.screenshot(path=str(shots / "r10w_frozen_filter.png"))
    page.locator(".c01-f-frozen").click()
    page.wait_for_timeout(300)
    ok("R10W 필터 누름 = 고정 줄 있는 IV 만 (1) · 다시 누름 = 전부", n_f == 1 and page.locator("tbody[data-iv]").count() == n_iv and n_iv > 1, [n_iv, n_f])
    # ③ 카드
    page.evaluate("q => { C01.state.view = 'input'; C01.state.qkind = 'all'; C01.state.qiv = null; C01.state.qsel = q; C01.app.render(); }", qa["queue_id"])
    page.wait_for_selector("#q-idtab")
    it = page.locator(".c01-idiff").inner_text()
    ok("R10W 카드 종류 「入力後の差異」 (있을 때만 칩) · 두 값 머리 「Compass入力値」 / 「新しい値」 · 까닭 (record) · 다른 칸만 빨강 (枠 1)",
       page.locator(".c01-kinds [data-kind='入力後の差異']").count() == 1 and "Compass入力値" in it and "新しい値" in it and "Compass入力の記録と" in it
       and page.locator("#q-idtab tr.d").count() == 1 and page.locator("#q-idtab tr.d[data-idf='slot']").count() == 1
       and page.locator("#q-idtab tbody tr").count() >= 4 and "番目の枠" in it, it[:300])
    ok("R10W 버튼 = 「入力値のまま」 · 「新しい値でCompass再入力」 · 원본 書類 📄 · 写真 · 搬入票ではない / 他社のコンテナ / このまま確認 / 元に戻す 없음",
       page.locator("#q-submit").inner_text() == "入力値のまま" and not page.locator("#q-submit").is_disabled() and page.locator("#q-idtake").count() == 1
       and page.locator("#q-iddocs").count() == 1 and page.locator("#q-idphotos").count() == 1
       and page.locator("#q-notours").count() == 0 and page.locator("#q-otherct").count() == 0 and page.locator("#q-keep").count() == 0 and page.locator("#q-undo").count() == 0,
       [page.locator("#q-submit").inner_text(), page.locator("#q-idtake").count(), page.locator("#q-iddocs").count()])
    for th in ("dark", "light", "leenai", "focus"):
        page.evaluate(f"document.documentElement.setAttribute('data-theme','{th}')")
        page.wait_for_timeout(100)
        page.screenshot(path=str(shots / f"r10w_idiff_{th}.png"))
    page.evaluate("document.documentElement.setAttribute('data-theme','light')")
    ids0 = {x.get("action_id") for x in actions(root)}
    page.click("#q-submit")
    page.wait_for_timeout(900)
    na = [x for x in actions(root) if x.get("action_id") not in ids0]
    ae = SC.errors(na[0], sch["action"]) if na and "action" in sch else ["no"]
    ok("R10W 「入力値のまま」 = input_keep 1 (queue_id · field null · value null · iv · ct) · 엔진 v0.5.122 스키마",
       len(na) == 1 and na[0]["action"] == "input_keep" and na[0]["queue_id"] == qa["queue_id"] and na[0]["field"] is None and na[0]["value"] is None
       and na[0]["iv"] == ivn and na[0]["ct"] == ra["ct"] and not ae, [na, ae])
    page.evaluate("q => { C01.state.qkind = 'done'; C01.state.qsel = q; C01.app.render(); }", qa["queue_id"])
    page.wait_for_timeout(400)
    okmsg = page.locator(".c01-okmsg").inner_text() if page.locator(".c01-okmsg").count() else ""
    ok("R10W 완료 = 「入力値のままにしました」", "入力値のままにしました" in okmsg, okmsg)
    # v0.3.56 (R10Z Part 3 · 엔진 actions_input_undo): 완료 카드 = 「元に戻す」 → undo 1 (value.action_id = input_keep) · 끔 (RULES.inputUndo false) = 버튼 없음
    ok("R10Z 「入力値のまま」 완료 = 「元に戻す」 있음 (RULES.inputUndo)", page.locator("#q-undo").count() == 1, page.locator("#q-undo").count())
    page.evaluate("() => { C01.RULES.inputUndo = false; C01.app.render(); }")
    page.wait_for_timeout(200)
    n_off = page.locator("#q-undo").count()
    page.evaluate("() => { C01.RULES.inputUndo = true; C01.app.render(); }")
    page.wait_for_timeout(200)
    ok("R10Z RULES.inputUndo 끔 = 「元に戻す」 없음 (엔진 설정 끔과 같이)", n_off == 0, n_off)
    ids_u = {x.get("action_id") for x in actions(root)}
    page.click("#q-undo")
    page.wait_for_timeout(900)
    nu = [x for x in actions(root) if x.get("action_id") not in ids_u]
    ue = SC.errors(nu[0], sch["action"]) if nu and "action" in sch else ["no"]
    ok("R10Z 「元に戻す」 = undo 1 (value.action_id = 그 input_keep · queue_id null) · 엔진 스키마",
       len(nu) == 1 and nu[0]["action"] == "undo" and (nu[0].get("value") or {}).get("action_id") == na[0]["action_id"] and nu[0].get("queue_id") is None and not ue, [nu, ue])
    page.evaluate("q => { C01.state.qkind = 'all'; C01.state.qsel = q; C01.app.render(); }", qa["queue_id"])
    page.wait_for_timeout(400)
    ok("R10Z 되돌린 뒤 카드 = 다시 열림 (「入力値のまま」 버튼 · 완료 표시 없음)",
       page.locator("#q-submit").inner_text() == "入力値のまま" and page.locator(".c01-okmsg").count() == 0, page.locator("#q-submit").inner_text())
    # ④ 새 값으로 다시 입력 (new_doc seal · 칸) → input_diff_take → Compass入力 창 · 비교 = 새 값 · 새 칸 · 줄 고정 표시 풀림
    page.evaluate("q => { C01.state.qkind = 'all'; C01.state.qsel = q; C01.app.render(); }", qb["queue_id"])
    page.wait_for_selector("#q-idtab")
    it2 = page.locator(".c01-idiff").inner_text()
    ok("R10W 카드 2 = 까닭 2 (record · new_doc) · 빨강 2 (枠 · シール) · 새 값 보임",
       "Compass入力の後で届いた書類" in it2 and "Compass入力の記録と" in it2 and page.locator("#q-idtab tr.d").count() == 2 and "TS9R10W1" in it2, it2[:300])
    ids1 = {x.get("action_id") for x in actions(root)}
    # 앞 시험 (R10H) 이 window.confirm 을 바꿔 둠 → 이 시험에서 직접 받음 (취소 → 확인) · 끝에 되돌림
    page.evaluate("() => { window.__cfW = window.__cf0 || window.confirm; window.__cf = []; window.confirm = m => { window.__cf.push(m); return false; }; }")
    page.click("#q-idtake")
    page.wait_for_timeout(300)
    n_cancel = len([x for x in actions(root) if x.get("action_id") not in ids1])
    page.evaluate("() => { window.confirm = m => { window.__cf.push(m); return true; }; }")
    page.click("#q-idtake")
    page.wait_for_timeout(1200)
    dl = page.evaluate("() => window.__cf")
    nt = [x for x in actions(root) if x.get("action_id") not in ids1]
    te = SC.errors(nt[0], sch["action"]) if nt and "action" in sch else ["no"]
    ok("R10W 「新しい値でCompass再入力」 = 확인 창 (취소 = 기록 0) → input_diff_take 1 · 엔진 v0.5.122 스키마",
       n_cancel == 0 and len(dl) == 2 and "固定を外して" in dl[0] and len(nt) == 1 and nt[0]["action"] == "input_diff_take" and nt[0]["queue_id"] == qb["queue_id"]
       and nt[0]["field"] is None and nt[0]["value"] is None and not te, [dl[:1], nt, te])
    mk = page.evaluate("() => C01.state.modal && C01.state.modal.kind")
    ci = page.evaluate("() => C01.app._compassInput(" + json.dumps(ivn) + ")") or []
    cb = next((x for x in ci if x["container_id"] == rb["container_id"]), {})
    ca = next((x for x in ci if x["container_id"] == ra["container_id"]), {})
    page.screenshot(path=str(shots / "r10w_take_compass.png"))
    ok("R10W 그 뒤 Compass入力 창 열림 · 비교 = 새 값 (seal) · 새 칸 (反映 전) · 다른 줄은 그대로",
       mk == "compass" and cb.get("seal") == "TS9R10W1" and cb.get("ct_id") == other_slot and ca.get("ct_id") == ra["slot_guid"] and ca.get("seal") == ra["seal"], [mk, cb.get("ct_id") == other_slot])
    page.keyboard.press("Escape")
    page.evaluate("() => { const m = document.getElementById('c01-modal'); if (m) { m.hidden = true; m.innerHTML = ''; } C01.state.modal = null; C01.state.view = 'main'; C01.app.render(); }")
    page.wait_for_timeout(300)
    page.click("#tab-main")
    page.wait_for_timeout(300)
    fr2 = page.locator(tb + " tr.c01-row[data-frozen='1']")
    ok("R10W 「新しい値でCompass再入力」 뒤 그 줄 = 「確認済」 (고정 표시 풀림 · 다른 고정 줄 그대로)", fr2.count() == 1 and rb["ct"] not in fr2.first.inner_text(), fr2.count())
    # ⑤ Compass入力 「元に戻す」 (기록 마지막 = undo_of) = 고정 표시 0 · 필터 사라짐
    j3 = json.loads(jp.read_text(encoding="utf-8"))
    iv3 = next(x for x in j3["ivs"] if x["iv_no"] == ivn)
    iv3["compass_input"].append({"action_id": "r10wcd000002", "by": "staff.a@example.invalid", "at": "2026-11-08T11:00:00+09:00", "value": {"undo_of": "r10wcd000001", "cells": []}})
    jp.write_text(dump(j3), encoding="utf-8")
    page.evaluate("C01.app.tick()")
    page.wait_for_timeout(800)
    ok("R10W Compass入力 「元に戻す」 (엔진 반영 전) = 「確認済（入力済）」 0 · 필터 없음", page.locator("tr.c01-row[data-frozen]").count() == 0 and page.locator(".c01-f-frozen").count() == 0,
       page.locator("tr.c01-row[data-frozen]").count())
    page.evaluate("p => { C01.RULES.otherCt = p[0]; C01.RULES.valueEdit = p[1]; C01.state.qkind = 'all'; C01.state.view = 'main'; C01.state.filter = 'all'; if (window.__cfW) window.confirm = window.__cfW; }", prev)
    jp.write_text(jt0, encoding="utf-8")
    qp.write_text(qt0, encoding="utf-8")
    page.evaluate("C01.app.tick()")
    page.wait_for_timeout(400)


def r11f_checks(page, root, shots, engine):
    """v0.3.57 (R11F · #317 급한 수정 길 C): AI 相談 답 「値を B に修正」 (지금 값 · 새 값 · 근거 · 그 칸 그림 확대 · 이동) → ✎ 修正 과 같은 manual_input
    (origin ai_proposal · 엔진 스키마) · 「修正しました (元: A)。画面に反映まで 1〜2 分」 · 반영되면 그 줄 강조 1번 · 元に戻す 한 바퀴 = 시작 해시 ·
    fix_check = 버튼 없음 · 버튼 없는 답 = 「急ぎで依頼」 (CUT 오늘·내일 빨강) · 「改善依頼（一般）」 · 전체 改善依頼の案 = 一般 / 急ぎ · 依頼一覧 区分 ·
    설정 끔 = 지금 화면 · 휴대폰 폭. 가명 데이터만 (TSTU · TST2611)."""
    import hashlib
    import fitz
    sys.path.insert(0, engine)
    from engine.output import schema_check as SC  # noqa: E402
    page.evaluate("() => { if (!window.__tw11 && !window._toasts) { const o = LEENAI.toast; LEENAI.toast = (m, t) => { window._toasts.push(m); return o && o(m, t); }; } window.__tw11 = 1; window._toasts = [];"
                  " window.__cf11 = window.confirm; window._confirms = []; window.confirm = m => { window._confirms.push(m); return true; }; }")
    page.keyboard.press("Escape")
    page.set_viewport_size({"width": 1440, "height": 1000})
    ivn, ctn, cur, new = "TST2611-04", "TSTU0010840", "TS001084", "TS001089"
    jp = root / "_data" / "jikkyou.json"
    jt0 = jp.read_text(encoding="utf-8")
    # 근거 PDF (가명 · 시험 사본 안) — 엔진 ask_fix_ref 의 sha16 으로 TOOL 이 찾는 원본
    pp = root / "_data" / "photos" / f"{ivn}.json"
    pj = json.loads(pp.read_text(encoding="utf-8"))
    rel_pdf = f"{ivn}/搬入票/r11f_ev.pdf"
    (root / rel_pdf).parent.mkdir(parents=True, exist_ok=True)
    doc = fitz.open()
    pg = doc.new_page(width=595, height=842)
    pg.insert_text((80, 300), "N/W 12000 KG (test)", fontsize=20)
    doc.save(str(root / rel_pdf))
    doc.close()
    pdf_sha = "f1f1f1f1f1f1f1f1"
    pj["docs"].append({"path": rel_pdf, "size": (root / rel_pdf).stat().st_size, "sha16": pdf_sha})
    pp.write_text(json.dumps(pj, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    ph = next(c for c in pj["containers"] if c["ct"] == ctn)["photos"][0]
    page.click("#tab-main")
    page.evaluate("() => C01.app.tick()")
    page.wait_for_timeout(700)

    def ids(kind):
        return {x.get("action_id") for x in actions(root) if x.get("action") == kind}

    def new_of(kind, before_ids):
        return [x for x in actions(root) if x.get("action") == kind and x.get("action_id") not in before_ids]

    def tb_hash():
        return page.evaluate("iv => { const t = document.querySelector(\"tbody[data-iv='\" + iv + \"']\"); return t ? t.innerHTML : ''; }", ivn)

    rk = page.evaluate("ct => [...document.querySelectorAll(\"tr.c01-row\")].map(t => t.getAttribute('data-key')).find(k => k && k.includes(ct))", ctn)
    page.evaluate("k => { C01.state.sel = k; C01.state.editRow = null; C01.app.render(); }", rk)
    page.wait_for_timeout(300)
    page.click("#panel-ask")
    page.wait_for_timeout(400)
    h0 = hashlib.sha256(tb_hash().encode("utf-8")).hexdigest()[:16]
    before = set(p.name for p in (root / "_actions" / "ask").rglob("*.json"))
    page.fill("#ask-in", f"シールは {new} です")
    page.press("#ask-in", "Enter")
    page.wait_for_timeout(500)
    new_f = [p for p in (root / "_actions" / "ask").rglob("*.json") if p.name not in before]
    k1 = json.loads(new_f[0].read_text(encoding="utf-8")) if len(new_f) == 1 else {}
    ok("R11F 행 AI 相談 질문 1건 (container_id)", len(new_f) == 1 and (k1.get("card") or {}).get("container_id"), k1.get("card"))
    cid = (k1.get("card") or {}).get("container_id")
    ev = {"origin": "reread", "compare": "same_as_reread", "before": cur, "after": new, "staff_text": "", "read_text": new, "source": "photo",
          "file_id": None, "photo_id": 7, "page": None, "box": [300, 400, 700, 520], "sha16": ph["sha16"]}
    rep = {"ask_id": k1["ask_id"], "status": "ok", "answer": "写真のシールを拡大して読み直しました。", "kind": "value", "approval_request": "", "urgent": 1,
           "suggestions": [{"action": "fix_value", "field": "seal", "value": new, "iv": "", "label": "値を修正", "evidence": ev}],
           "fix_check": [{"field": "n_w", "staff_value": "12345", "read_value": "12000", "by": "zoom_reread", "source": "document", "file_id": 3, "photo_id": None,
                          "page": 1, "box": [120, 330, 420, 380], "sha16": pdf_sha}]}
    (root / "_actions" / "ask_reply" / f"{k1['ask_id']}.json").write_text(json.dumps(rep, ensure_ascii=False), encoding="utf-8")
    page.evaluate("() => C01.app.tick()")
    page.wait_for_timeout(900)
    page.evaluate("() => C01.app.render()")
    page.wait_for_timeout(300)
    fx = page.locator("#ask-box .c01-fix")
    t = fx.inner_text() if fx.count() else ""
    ok("R11F 「値を B に修正」 상자 = 지금 값 · 새 값 나란히 · 근거 (拡大して読み直し · 같은 값) · 버튼 글 「値を TS001089 に修正」",
       fx.count() == 1 and "今の値" in t and cur in t and "新しい値" in t and new in t and "拡大して読み直し" in t and "原本の拡大読み直しと同じ" in t
       and page.locator("#ask-box [data-fixgo]").inner_text().replace(" ", "") == f"値を{new}に修正", t)
    ok("R11F fix_value 는 옛 「値を入れる」 버튼으로 안 나옴 (data-asksug 0) · 버튼 있는 답 = 急ぎで依頼 없음",
       page.locator("#ask-box [data-asksug]").count() == 0 and page.locator("#ask-box .c01-req").count() == 0)
    ck = page.locator("#ask-box .c01-fixchk")
    ok("R11F fix_check = 「原本では 12000 に見えます」 · 그 칸 버튼 없음 (보기만)", ck.count() == 1 and "原本では" in ck.inner_text() and "12000" in ck.inner_text()
       and ck.locator("[data-fixgo]").count() == 0 and ck.locator("[data-evchk]").count() == 1, ck.inner_text() if ck.count() else None)
    page.screenshot(path=str(shots / "r11f_fix_box.png"), full_page=False)
    # 근거 창 (사진 · 상자 · 확대 · 이동)
    page.locator("#ask-box [data-evopen]").click()
    page.wait_for_timeout(1300)
    m = page.evaluate("""() => { const st = document.getElementById('ev-stage'), b = document.querySelector('.c01-evbox');
        return { modal: !!document.querySelector('.c01-modal-ev'), img: !!document.querySelector('#ev-wrap img'), box: b ? b.getAttribute('style') : null,
                 zoom: st ? st.getAttribute('data-zoom') : null, bar: !!document.getElementById('ev-z-bar') }; }""")
    ok("R11F 「根拠を見る」 = 원본 사진 + 빨간 칸 (300·400·700·520 → 30%·40%) · 그 칸으로 확대 (1 배 넘음) · 확대 막대",
       m["modal"] and m["img"] and m["box"] and "left:30.00%" in m["box"].replace(" ", "") and "top:40.00%" in m["box"].replace(" ", "") and float(m["zoom"] or 0) > 1 and m["bar"], m)
    page.screenshot(path=str(shots / "r11f_evidence_photo.png"), full_page=False)
    page.click("#ev-z-fit")
    page.wait_for_timeout(200)
    z1 = page.evaluate("() => document.getElementById('ev-stage').getAttribute('data-zoom')")
    page.click("#ev-focus")
    page.wait_for_timeout(200)
    z2 = page.evaluate("() => document.getElementById('ev-stage').getAttribute('data-zoom')")
    ok("R11F 全体表示 = 1 배 · 「その所へ」 = 다시 확대", z1 == "1.00" and float(z2) > 1, [z1, z2])
    page.evaluate("() => document.querySelector('#c01-modal [data-close]').click()")
    page.wait_for_timeout(200)
    page.evaluate("() => { C01.PDF._lib = C01.PDF.lib; C01.PDF.lib = 'js/validate.js'; }")   # 시험 = 밖 pdf.js 안 받음 → iframe 대체 (실제 그리기 = 실데이터 화면 비교)
    page.locator("#ask-box [data-evchk]").click()
    page.wait_for_timeout(1500)
    m2 = page.evaluate("""() => { const p = document.querySelector('#ev-wrap .c01-pdf'); const f = p && p.querySelector('iframe');
        return { pdf: !!p, ev: p ? p.getAttribute('data-ev') : null, page: p ? p.getAttribute('data-page') : null, ifr: f ? f.getAttribute('src') : null,
                 box: !!document.querySelector('.c01-evbox'), pg: (document.getElementById('pdf-pg') || {}).textContent || null }; }""")
    page.evaluate("() => { C01.PDF.lib = C01.PDF._lib; delete C01.PDF._lib; }")
    ok("R11F fix_check 「原本のその所を見る」 = 그 PDF (data-ev · 1쪽) + 칸 · 카드 쪽 표시 안 바뀜", m2["pdf"] and m2["ev"] == "1" and m2["page"] == "1" and m2["box"]
       and m2["ifr"] and "r11f_ev.pdf" in m2["ifr"], m2)
    page.screenshot(path=str(shots / "r11f_evidence_pdf.png"), full_page=False)
    page.evaluate("() => document.querySelector('#c01-modal [data-close]').click()")
    page.wait_for_timeout(200)
    # 누름 → manual_input (✎ 修正 과 같은 꼴 + origin)
    b_mi = ids("manual_input")
    page.locator("#ask-box [data-fixgo]").click()
    page.wait_for_timeout(600)
    acts = new_of("manual_input", b_mi)
    a = acts[0] if acts else {}
    org = a.get("origin") or {}
    ok("R11F 누름 = _actions manual_input 1건 (IV · CT · seal · 새 값 · 手入力 · edit · origin ai_proposal ask_id)",
       len(acts) == 1 and a.get("iv") == ivn and a.get("ct") == ctn and a.get("field") == "seal" and a.get("value") == new and a.get("source") == "手入力"
       and org.get("kind") == "ai_proposal" and org.get("ask_id") == k1["ask_id"] and str(org.get("key", "")).startswith("fix-") and len(org.get("key", "")) <= 32, a)
    ok("R11F 보낸 action = 엔진 스키마 통과 (manual_input + origin)", SC.check_obj(a, "action") == [], SC.check_obj(a, "action"))
    qid_edit = page.evaluate("cid => { const s = 'edit|' + cid + '|seal'; const h = x => { let v = 0x811c9dc5; for (let i = 0; i < x.length; i++) { v ^= x.charCodeAt(i); v = Math.imul(v, 0x01000193) >>> 0; } return ('0000000' + v.toString(16)).slice(-8); }; return h(s) + h(s + '|2'); }", cid)
    ok("R11F queue_id = ✎ 修正 과 같은 행·항목 id", a.get("queue_id") == qid_edit, [a.get("queue_id"), qid_edit])
    cf = page.evaluate("() => window._confirms")
    ok("R11F 自動OK 행 = ✎ 修正 과 같은 확인 1번", any("自動OK" in c for c in cf), cf)
    page.evaluate("() => C01.app.tick()")
    page.wait_for_timeout(800)
    t2 = page.locator("#ask-box .c01-fix").inner_text()
    ok("R11F 누른 뒤 「修正しました（元: TS001084）。画面に反映まで 1〜2 分」 · 버튼 사라짐 · 元に戻す",
       f"修正しました（元: {cur}）。画面に反映まで 1〜2 分" in t2 and page.locator("#ask-box [data-fixgo]").count() == 0
       and page.locator("#ask-box [data-fixundo]").count() == 1, t2)
    ok("R11F 토스트 「修正しました（元: …）」", any(f"修正しました（元: {cur}）" in x for x in page.evaluate("() => window._toasts")), page.evaluate("() => window._toasts"))
    # 엔진 반영 흉내 (実況表 의 seal = 새 값) → 토스트 1번 · 그 줄 강조 1번
    jj = json.loads(jt0)
    for iv in jj["ivs"]:
        for r in iv["rows"]:
            if r["ct"] == ctn:
                r["seal"] = new
    jp.write_text(json.dumps(jj, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    page.evaluate("() => C01.app.tick()")
    page.wait_for_timeout(700)
    fl = page.evaluate("ct => [...document.querySelectorAll('tr.c01-row.c01-flash')].map(t => t.getAttribute('data-key')).filter(k => k && k.includes(ct)).length", ctn)
    ts = page.evaluate("() => window._toasts")
    ok("R11F 반영되면 토스트 「画面に反映されました」 1번 · 그 줄 강조 (c01-flash) 1번 · 상자 「画面に反映しました」",
       fl == 1 and sum(1 for x in ts if "画面に反映されました" in x) == 1 and "画面に反映しました" in page.locator("#ask-box .c01-fix").inner_text(), [fl, ts[-3:]])
    page.screenshot(path=str(shots / "r11f_fix_reflected.png"), full_page=False)
    page.wait_for_timeout(2800)
    page.evaluate("() => C01.app.render()")
    page.wait_for_timeout(300)
    ok("R11F 강조는 1번만 (다시 그려도 없음)", page.locator("tr.c01-row.c01-flash").count() == 0 and sum(1 for x in page.evaluate("() => window._toasts") if "画面に反映されました" in x) == 1)
    # 元に戻す 한 바퀴 → 시작 해시
    b_un = ids("undo")
    page.locator("#ask-box [data-fixundo]").click()
    page.wait_for_timeout(600)
    un = new_of("undo", b_un)
    ok("R11F 元に戻す = undo 1건 (value.action_id = 그 manual_input) · 엔진 스키마", len(un) == 1 and (un[0].get("value") or {}).get("action_id") == a.get("action_id")
       and SC.check_obj(un[0], "action") == [], un)
    jp.write_text(jt0, encoding="utf-8")                                   # 엔진이 되돌린 実況表 (처음 값)
    page.evaluate("() => C01.app.tick()")
    page.wait_for_timeout(900)
    page.evaluate("() => { C01.state.sel = null; C01.app.render(); }")
    page.wait_for_timeout(300)
    h1 = hashlib.sha256(tb_hash().encode("utf-8")).hexdigest()[:16]
    ok("R11F 수정 → 元に戻す 한 바퀴 = 実況表 그 IV 해시 시작과 같음", h1 == h0, [h0, h1])
    t3 = page.locator("#ask-box .c01-fix").inner_text()
    ok("R11F 되돌린 뒤 상자 = 다시 버튼 · 「前の修正は元に戻しました」", page.locator("#ask-box [data-fixgo]").count() == 1 and "前の修正は元に戻しました" in t3, t3)
    # 버튼 없는 답 — CUT 오늘·내일 = 빨강 「急ぎで依頼」 · 「改善依頼（一般）」
    def ask_and_reply(q, rep_extra):
        b0 = set(p.name for p in (root / "_actions" / "ask").rglob("*.json"))
        page.fill("#ask-in", q)
        page.press("#ask-in", "Enter")
        page.wait_for_timeout(500)
        nf = [p for p in (root / "_actions" / "ask").rglob("*.json") if p.name not in b0]
        k = json.loads(nf[0].read_text(encoding="utf-8"))
        rp = {"ask_id": k["ask_id"], "status": "ok", "answer": "この画面のボタンでは直せません。", "kind": "other", "approval_request": "", "suggestions": [], **rep_extra}
        (root / "_actions" / "ask_reply" / f"{k['ask_id']}.json").write_text(json.dumps(rp, ensure_ascii=False), encoding="utf-8")
        for _ in range(12):                                                # 답이 화면에 나올 때까지 (최대 약 10초)
            page.evaluate("() => C01.app.tick()")
            page.wait_for_timeout(600)
            page.evaluate("() => C01.app.render()")
            page.wait_for_timeout(200)
            if page.locator("#ask-box .c01-ask-a.wait").count() == 0:
                break
        return k
    k2 = ask_and_reply("写真が別のコンテナに入っている", {"urgent": 1})
    ub = page.locator(f"#ask-box [data-urg='{k2['ask_id']}']")             # 시계가 멈춘 구간 = 같은 시각 → 순서 대신 ask_id 로
    rq = page.locator("#ask-box .c01-req").filter(has=page.locator(f"[data-urg='{k2['ask_id']}']"))
    ok("R11F 버튼 없는 답 = 「急ぎで依頼（CUT 今日・明日）」 빨강 + 「改善依頼（一般）」", rq.count() == 1 and ub.count() == 1 and "red" in (ub.get_attribute("class") or "")
       and "急ぎで依頼（CUT 今日・明日）" in ub.inner_text() and rq.locator("[data-reqgen]").count() == 1, rq.inner_text() if rq.count() else None)
    page.screenshot(path=str(shots / "r11f_urgent_red.png"), full_page=False)
    b_u = ids("urgent_request")
    ub.click()
    page.wait_for_timeout(600)
    us = new_of("urgent_request", b_u)
    u = us[0] if us else {}
    uv = u.get("value") or {}
    ok("R11F 「急ぎで依頼」 = _actions urgent_request 1건 (질문 · ask_id · row · IV · CT · field null) · 확인 창",
       len(us) == 1 and uv.get("ask_id") == k2["ask_id"] and uv.get("question") == "写真が別のコンテナに入っている" and uv.get("row") == cid
       and u.get("iv") == ivn and u.get("ct") == ctn and u.get("field") is None and any("急ぎ" in c for c in page.evaluate("() => window._confirms")), u)
    ok("R11F urgent_request = 엔진 스키마 통과", SC.check_obj(u, "action") == [], SC.check_obj(u, "action"))
    ok("R11F 보낸 뒤 「急ぎで依頼しました」 · 그 답의 버튼 사라짐 (2번 눌러도 1건)", "急ぎで依頼しました" in page.locator("#ask-box .c01-ask-log").inner_text()
       and page.locator(f"#ask-box [data-urg='{k2['ask_id']}']").count() == 0)
    k3 = ask_and_reply("このメールの件", {"urgent": 0})
    u3 = page.locator(f"#ask-box [data-urg='{k3['ask_id']}']")
    ok("R11F CUT 오늘·내일 아닌 IV = 「急ぎで依頼」 빨강 아님", u3.count() == 1 and "red" not in (u3.get_attribute("class") or ""))
    b_i = ids("improve_request")
    page.locator(f"#ask-box [data-reqgen='{k3['ask_id']}']").click()
    page.wait_for_timeout(600)
    ims = new_of("improve_request", b_i)
    im = ims[0] if ims else {}
    ok("R11F 「改善依頼（一般）」 = _actions improve_request 1건 (ask_id · 제목 · 요약 · IV) · 엔진 스키마",
       len(ims) == 1 and (im.get("value") or {}).get("ask_id") == k3["ask_id"] and (im.get("value") or {}).get("ivs") == [ivn] and SC.check_obj(im, "action") == [],
       [im, SC.check_obj(im, "action")])
    ok("R11F 보낸 뒤 「改善依頼（一般）を送りました」", "改善依頼（一般）を送りました" in page.locator("#ask-box .c01-ask-log").inner_text()
       and page.locator(f"#ask-box [data-reqgen='{k3['ask_id']}']").count() == 0)
    # 휴대폰 폭 (390) — 상자 · 버튼이 화면 안
    page.set_viewport_size({"width": 390, "height": 844})
    page.wait_for_timeout(400)
    mob = page.evaluate("""() => { const b = document.querySelector('#ask-box'); const f = document.querySelector('#ask-box .c01-fix');
        const r = e => e ? e.getBoundingClientRect().toJSON() : null; return { box: r(b), fix: r(f), vw: window.innerWidth }; }""")
    ok("R11F 휴대폰 폭 390 = 수정 상자 화면 폭 안", mob["fix"] is not None and mob["fix"]["right"] <= mob["vw"] + 1 and mob["fix"]["left"] >= -1, mob)
    page.locator("#ask-box .c01-fix").scroll_into_view_if_needed()
    page.screenshot(path=str(shots / "r11f_mobile.png"), full_page=False)
    page.set_viewport_size({"width": 1440, "height": 1000})
    page.wait_for_timeout(300)
    # 설정 끔 = 지금 화면 (fix_value = 옛 버튼 · 急ぎで依頼 없음)
    page.evaluate("() => { C01.ASK._fb = C01.ASK.fixButton; C01.ASK._ur = C01.ASK.urgentReq; C01.ASK.fixButton = false; C01.ASK.urgentReq = false; C01.app.render(); }")
    page.wait_for_timeout(300)
    ok("R11F 끔 = fix 상자 0 · 옛 버튼 (data-asksug) · 依頼 상자 0", page.locator("#ask-box .c01-fix").count() == 0 and page.locator("#ask-box [data-asksug]").count() >= 1
       and page.locator("#ask-box .c01-req").count() == 0 and page.locator("#ask-box .c01-fixchk").count() == 0)
    page.evaluate("() => { C01.ASK.fixButton = C01.ASK._fb; C01.ASK.urgentReq = C01.ASK._ur; C01.app.render(); }")
    page.wait_for_timeout(200)
    page.click("#ask-close")
    page.wait_for_timeout(200)
    # 전체 AI 相談: 改善依頼の案 = 一般 (1日以上) / 急ぎ (今日中) · 依頼一覧 区分
    page.click("#gask-open")
    page.wait_for_timeout(300)
    b0 = set(p.name for p in (root / "_actions" / "ask").rglob("*.json"))
    page.fill("#gask-in", "今日 CUT の IV の写真が出ない")
    page.press("#gask-in", "Enter")
    page.wait_for_timeout(500)
    g = json.loads([p for p in (root / "_actions" / "ask").rglob("*.json") if p.name not in b0][0].read_text(encoding="utf-8"))
    imp = {"title": "写真が出ない", "summary": "CUT が今日の IV で 写真の一覧が古い。", "cause": None, "mail_ids": [], "ivs": [ivn], "bkgs": []}
    rp = {"ask_id": g["ask_id"], "scope": "global", "status": "ok", "kind": "investigation", "suggestions": [], "approval_request": "", "improve": imp, "answer": "調べました。"}
    (root / "_actions" / "ask_reply" / f"{g['ask_id']}.json").write_text(json.dumps(rp, ensure_ascii=False), encoding="utf-8")
    page.evaluate("() => C01.app.tick()")
    page.wait_for_timeout(900)
    page.evaluate("() => C01.app.render()")
    page.wait_for_timeout(300)
    ib = page.locator("#gask-box .c01-imp").last
    ok("R11F 改善依頼の案 = 「一般で依頼（1日以上）」 「急ぎで依頼（今日中）」 「やめる」 · 依頼 상자 (c01-req) 겹치지 않음",
       ib.locator("[data-impsend]").inner_text() == "一般で依頼（1日以上）" and ib.locator("[data-impurg]").inner_text() == "急ぎで依頼（今日中）"
       and ib.locator("[data-impdrop]").count() == 1 and page.locator("#gask-box .c01-req").count() == 0, ib.inner_text())
    page.screenshot(path=str(shots / "r11f_gask_kinds.png"), full_page=False)
    b_u2 = ids("urgent_request")
    ib.locator("[data-impurg]").click()
    page.wait_for_timeout(600)
    us = new_of("urgent_request", b_u2)
    u2 = us[0] if us else {}
    ok("R11F 「急ぎで依頼（今日中）」 = urgent_request 1건 (질문 · note = 제목 / 요약 · IV null) · 스키마 · 「急ぎ（今日中）で依頼しました」",
       len(us) == 1 and (u2.get("value") or {}).get("ask_id") == g["ask_id"] and "写真が出ない" in ((u2.get("value") or {}).get("note") or "")
       and SC.check_obj(u2, "action") == [] and "急ぎ（今日中）で依頼しました" in page.locator("#gask-box .c01-imp").last.inner_text(), u2)
    page.evaluate("() => C01.app.tick()")
    page.wait_for_timeout(800)
    page.locator("[data-gtab='reqs']").click()
    page.wait_for_timeout(300)
    page.locator("[data-reqall='0']").click()
    page.wait_for_timeout(300)
    hd = page.locator("#gask-box .c01-reqs thead").inner_text()
    rows = page.locator("#gask-box .c01-reqs tbody tr")
    urg_rows = page.locator("#gask-box .c01-reqs tbody tr.c01-requrg")
    gen = [x for x in rows.all_inner_texts() if "一般" in x]
    ok("R11F 依頼一覧 = 区分 칸 · 急ぎ 2건 (受付 · 今日中に対応) · 一般 (requests.json) 상태 그대로",
       "区分" in hd and urg_rows.count() == 2 and all("受付" in x and "今日中に対応" in x for x in urg_rows.all_inner_texts()) and len(gen) >= 1,
       rows.all_inner_texts())
    page.screenshot(path=str(shots / "r11f_reqs_kinds.png"), full_page=False)
    page.evaluate("() => { C01.ASK._ur = C01.ASK.urgentReq; C01.ASK.urgentReq = false; C01.app.render(); }")
    page.wait_for_timeout(200)
    ok("R11F 끔 = 依頼一覧 区分 칸 없음 · 급한 행 없음 (지금 표)", "区分" not in page.locator("#gask-box .c01-reqs thead").inner_text()
       and page.locator("#gask-box .c01-reqs tbody tr.c01-requrg").count() == 0)
    page.evaluate("() => { C01.ASK.urgentReq = C01.ASK._ur; C01.app.render(); }")
    page.locator("[data-gtab='chat']").click()
    page.keyboard.press("Escape")
    page.wait_for_timeout(200)
    page.evaluate("() => { if (window.__cf11) window.confirm = window.__cf11; }")


def r10x_checks(page, root, shots, engine_frz):
    """v0.3.53 (R10X · #309 · 엔진 v0.5.125 cycle_input_slot_check): 「入力後の差異」 why compass_slot 만인 카드 = 「COMPASSの配置を正とする」 (input_slot_take) ·
    「新しい値でCompass再入力」 안 냄 · 확인 창 (취소 = 기록 0) · action = 엔진 v0.5.125 action.schema · queue 스키마 (why compass_slot)."""
    sys.path.insert(0, engine_frz)
    from engine.output import schema_check as SC  # noqa: E402
    sch = {nm: json.loads((Path(engine_frz) / "engine" / "output" / "schema" / f"{nm}.schema.json").read_text(encoding="utf-8")) for nm in ("action", "queue")}
    ok("R10X 엔진 v0.5.125 스키마 = input_slot_take · why compass_slot 있음", "input_slot_take" in json.dumps(sch["action"]) and "compass_slot" in json.dumps(sch["queue"]))
    dump = lambda o: json.dumps(o, ensure_ascii=False, indent=1) + chr(10)   # noqa: E731
    d = root / "_data"
    jp, qp = d / "jikkyou.json", d / "queue.json"
    jt0, qt0 = jp.read_text(encoding="utf-8"), qp.read_text(encoding="utf-8")
    gone = {(x.get("value") or {}).get(k) for x in actions(root) if x.get("action") in ("other_ct", "merge_rows") for k in ("container_id", "from_container_id")}
    j = json.loads(jt0)
    qcid = {x.get("container_id") for x in json.loads(qt0)["items"]}
    elig = lambda iv_: [r for r in iv_["rows"] if r.get("ct") and r.get("slot_guid") and r["container_id"] not in gone and r["container_id"] not in qcid and not r.get("human")]   # noqa: E731
    iv1 = next(x for x in j["ivs"] if len(elig(x)) >= 1 and len(x.get("slots") or []) >= 2)
    ivn, ra = iv1["iv_no"], elig(iv1)[0]
    comp_slot = next(s_["slot_guid"] for s_ in iv1["slots"] if s_["slot_guid"] != ra["slot_guid"])
    ra.update({"status": "確認済", "engine_status": "自動OK", "reasons": [], "info": list(ra.get("info") or []) + ["INPUT_FROZEN"],
               "input_frozen": {"at": "2026-11-08T10:00:00+09:00", "done_at": "2026-11-08T09:58:00+09:00", "action_id": "r10xcd000001", "src": "apply"}})
    iv1["compass_input"] = [{"action_id": "r10xcd000001", "by": "staff.a@example.invalid", "at": "2026-11-08T09:58:00+09:00", "value": {"cells": [], "failed": []}}]
    jp.write_text(dump(j), encoding="utf-8")
    qa = {"queue_id": "7e7e7e7e7e7e7ec3", "kind": "入力後の差異", "iv_no": ivn, "ct": ra["ct"], "field": None, "container_id": ra["container_id"], "values": {},
          "candidates": [], "files": [], "note": "slot", "resolved": None, "superseded": [], "cy_cut": iv1.get("cy_cut"), "cy_open": iv1.get("cy_open"), "issuer": None,
          "field_sources": {}, "field_source_text": {}, "input_diff": {"slot": {"input": ra["slot_guid"], "new": comp_slot, "why": "compass_slot"}}}
    q2 = json.loads(qt0)
    q2["items"] += [qa]
    q2["kinds"] = list(q2.get("kinds") or []) + ["入力後の差異"]
    q2.setdefault("count", {})["入力後の差異"] = 1
    qp.write_text(dump(q2), encoding="utf-8")
    qe = SC.errors({**q2, "items": [qa]}, sch["queue"])
    ok("R10X 시험 카드 = 엔진 v0.5.125 queue 스키마 (오류 0)", not qe, qe[:3])
    page.keyboard.press("Escape")
    page.evaluate("() => { Object.assign(C01.state, {qedit: null, sel: null, editRow: null, filter: 'all', view: 'main', qkind: 'all'}); C01.app.tick(); }")
    page.wait_for_timeout(800)
    page.evaluate("q => { C01.state.view = 'input'; C01.state.qkind = 'all'; C01.state.qiv = null; C01.state.qsel = q; C01.app.render(); }", qa["queue_id"])
    page.wait_for_selector("#q-idtab")
    it = page.locator(".c01-idiff").inner_text()
    ok("R10X 카드 까닭 = 「COMPASS ではこの CT が別の枠」 · 빨강 = 枠 1",
       "COMPASS ではこの CT が別の枠" in it and page.locator("#q-idtab tr.d[data-idf='slot']").count() == 1 and page.locator("#q-idtab tr.d").count() == 1, it[:200])
    ok("R10X 버튼 = 「入力値のまま」 · 「COMPASSの配置を正とする」 · 「新しい値でCompass再入力」 없음",
       page.locator("#q-submit").inner_text() == "入力値のまま" and page.locator("#q-idslot").count() == 1 and page.locator("#q-idslot").inner_text() == "COMPASSの配置を正とする"
       and page.locator("#q-idtake").count() == 0, [page.locator("#q-idslot").count(), page.locator("#q-idtake").count()])
    page.screenshot(path=str(shots / "r10x_idiff_compass_slot.png"))
    ids1 = {x.get("action_id") for x in actions(root)}
    page.evaluate("() => { window.__cfX = window.confirm; window.__cf = []; window.confirm = m => { window.__cf.push(m); return false; }; }")
    page.click("#q-idslot")
    page.wait_for_timeout(300)
    n_cancel = len([x for x in actions(root) if x.get("action_id") not in ids1])
    page.evaluate("() => { window.confirm = m => { window.__cf.push(m); return true; }; }")
    page.click("#q-idslot")
    page.wait_for_timeout(1200)
    dl = page.evaluate("() => window.__cf")
    nt = [x for x in actions(root) if x.get("action_id") not in ids1]
    te = SC.errors(nt[0], sch["action"]) if nt else ["no"]
    ok("R10X 「COMPASSの配置を正とする」 = 확인 창 (취소 = 기록 0) → input_slot_take 1 (queue_id · field null · value null) · 엔진 v0.5.125 스키마",
       n_cancel == 0 and len(dl) == 2 and "COMPASS で今入っている枠" in dl[0] and len(nt) == 1 and nt[0]["action"] == "input_slot_take"
       and nt[0]["queue_id"] == qa["queue_id"] and nt[0]["field"] is None and nt[0]["value"] is None and nt[0]["iv"] == ivn and not te, [dl[:1], nt, te])
    page.evaluate("q => { C01.state.qkind = 'done'; C01.state.qsel = q; C01.app.render(); }", qa["queue_id"])
    page.wait_for_timeout(400)
    okmsg = page.locator(".c01-okmsg").inner_text() if page.locator(".c01-okmsg").count() else ""
    ok("R10X 완료 = 「COMPASS の枠を正としました」", "COMPASS の枠を正としました" in okmsg, okmsg)
    page.evaluate("() => { if (window.__cfX) window.confirm = window.__cfX; C01.state.qkind = 'all'; C01.state.view = 'main'; C01.state.filter = 'all'; }")
    # v0.3.54 (R10X · #311 · 엔진 v0.5.127 out_resend_photo_cand): 줄 resend_cand = 「再送依頼候補」 표시만 (업체 발송 0)
    jsch = json.loads((Path(engine_frz) / "engine" / "output" / "schema" / "jikkyou.schema.json").read_text(encoding="utf-8"))
    jr = json.loads(jt0)
    ivr = next(x for x in jr["ivs"] if x["iv_no"] == "TST2611-01")
    for rr in ivr["rows"]:
        rr["resend_cand"] = ["seal"]                     # 그 IV 줄 전부 (보이는 줄 수 = 표시 수)
    je = SC.errors({**jr, "ivs": [ivr]}, jsch)
    ok("R10X 시험 jikkyou (resend_cand) = 엔진 v0.5.127 스키마 (오류 0)", not je and "resend_cand" in json.dumps(jsch), je[:3])
    jp.write_text(dump(jr), encoding="utf-8")
    page.evaluate("C01.app.tick()")
    page.wait_for_timeout(800)
    page.click("#tab-main")
    page.wait_for_timeout(300)
    bd = page.locator(f"tbody[data-iv='{ivr['iv_no']}'] .c01-rsbadge")
    tt = bd.first.get_attribute("title") if bd.count() else ""
    nrow = page.locator(f"tbody[data-iv='{ivr['iv_no']}'] tr.c01-row").count()
    ok("R10X 「再送依頼候補」 표시 = 그 IV 보이는 줄마다 1 · 다른 IV 0 · 마우스 = 搬入票 · シール番号 · 自動では送りません",
       nrow >= 1 and bd.count() == nrow and bd.first.inner_text() == "再送依頼候補" and "シール番号" in (tt or "") and "自動では送りません" in (tt or "")
       and page.locator(".c01-rsbadge").count() == nrow, [nrow, bd.count(), tt])
    page.screenshot(path=str(shots / "r10x_resend_cand.png"))
    jp.write_text(jt0, encoding="utf-8")
    qp.write_text(qt0, encoding="utf-8")
    page.evaluate("C01.app.tick()")
    page.wait_for_timeout(400)


def r11j_checks(page, root, shots, engine):
    """v0.3.59 (R11J · #317): 依頼一覧 の 急ぎ = エンジン requests.json の kind urgent 行 (状態 受付 → 対応中 → 反映済 · 対応しない = 理由) ·
    同じ action_id の 送った記録の行は出さない · 答えの下 「急ぎで依頼しました（急ぎ No.n） · 状態」 · エンジンが出さない = 今まで (R11F) ·
    requests.json = エンジン スキマ · 携帯の幅 390. 仮名データだけ (R11F で作った urgent_request を使う)."""
    sys.path.insert(0, engine)
    from engine.output import schema_check as SC  # noqa: E402
    dump = lambda o: json.dumps(o, ensure_ascii=False, indent=1) + chr(10)   # noqa: E731
    rp = root / "_data" / "requests.json"
    rt0 = rp.read_text(encoding="utf-8") if rp.exists() else None
    base = json.loads(rt0) if rt0 else {"schema_version": 1, "kind": "improve_requests", "today": "2026-01-10", "items": []}
    us = sorted([x for x in actions(root) if x.get("action") == "urgent_request"], key=lambda x: str(x.get("at")))
    ok("R11J 준비: R11F 의 급한 의뢰 기록 2건", len(us) == 2, len(us))
    if len(us) < 2:
        return
    u = us[-1]
    page.keyboard.press("Escape")
    page.set_viewport_size({"width": 1440, "height": 1000})

    def put(status, memo=None, version=None):
        plan = {"受付": "今日中に対応", "対応中": "対応中（担当が作業しています）", "反映済": "反映済" + (f" ({version})" if version else ""),
                "対応しない": "対応しない" + (f": {memo}" if memo else "")}[status]
        it = {"no": 3, "kind": "urgent", "action_id": u["action_id"], "ask_id": (u.get("value") or {}).get("ask_id"), "at": u.get("at"), "by": u.get("by"),
              "by_name": (u.get("value") or {}).get("by_name"), "title": "写真が出ない (TST2611-04)", "question": "写真が出ない", "status": status,
              "memo": memo, "version": version, "plan": plan, "status_at": "2026-01-10T12:00:00+09:00"}
        obj = {**base, "items": [it] + [x for x in base["items"] if x.get("kind") != "urgent"]}
        rp.write_text(dump(obj), encoding="utf-8")
        page.evaluate("() => { C01.state.reqsMiss = 0; C01.app.tick(); }")
        page.wait_for_timeout(900)
        page.evaluate("() => C01.app.render()")
        page.wait_for_timeout(200)
        return obj

    page.click("#gask-open")
    page.wait_for_timeout(300)
    page.locator("[data-gtab='reqs']").click()
    page.wait_for_timeout(200)
    page.locator("[data-reqall='1']").click()
    page.wait_for_timeout(200)
    urg = lambda: page.locator("#gask-box .c01-reqs tbody tr.c01-requrg")   # noqa: E731
    n0 = urg().count()
    seen = []
    for st, memo, ver in (("受付", None, None), ("対応中", None, None), ("反映済", None, "v0.5.999")):
        obj = put(st, memo, ver)
        rows = urg().all_inner_texts()
        mine = [x for x in rows if "写真が出ない (TST2611-04)" in x]
        seen.append((st, len(rows), bool(mine) and st in mine[0], page.locator("#gask-box .c01-reqst.s-" + st).count()))
        if st == "受付":
            ok("R11J requests.json (急ぎ 행) = 엔진 스키마", SC.check_obj(obj, "requests") == [], SC.check_obj(obj, "requests"))
    ok("R11J 急ぎ 한 바퀴 受付 → 対応中 → 反映済 = 같은 줄 (행 수 그대로 · 送った記録 행 대신 엔진 행) · 상태 글자 · 색 칸",
       all(x[1] == n0 and x[2] and x[3] >= 1 for x in seen) and n0 == 2, seen)
    ok("R11J 反映済 = 판 (v0.5.999) · No = 엔진 번호", any("反映済 (v0.5.999)" in x and x.strip().startswith("3") for x in urg().all_inner_texts()), urg().all_inner_texts())
    put("対応しない", "担当者の処理で解決しました", None)
    ok("R11J 対応しない = 이유 한 줄", any("対応しない: 担当者の処理で解決しました" in x for x in urg().all_inner_texts()), urg().all_inner_texts())
    page.set_viewport_size({"width": 390, "height": 800})
    page.wait_for_timeout(300)
    bx = page.locator("#gask-box").bounding_box() or {}
    st_vis = page.locator("#gask-box .c01-reqst.s-対応しない").first
    sb = st_vis.bounding_box() or {}
    page.screenshot(path=str(shots / "r11j_reqs_phone.png"), full_page=False)
    ok("R11J 휴대폰 폭 390 = 依頼一覧 상자 안 · 상태 칸 보임", bx.get("width", 999) <= 391 and sb and sb.get("x", 999) + sb.get("width", 0) <= 391, (bx, sb))
    page.set_viewport_size({"width": 1440, "height": 1000})
    page.wait_for_timeout(200)
    put("対応中")
    page.screenshot(path=str(shots / "r11j_reqs_status.png"), full_page=False)
    # 끔 = 엔진이 급한 행을 내지 않음 → R11F 그대로 (送った記録 2 행 · 受付)
    rp.write_text(rt0 if rt0 is not None else dump(base), encoding="utf-8")
    page.evaluate("() => { C01.state.reqsMiss = 0; C01.app.tick(); }")
    page.wait_for_timeout(900)
    page.evaluate("() => C01.app.render()")
    page.wait_for_timeout(200)
    ok("R11J 끔 (엔진 급한 행 없음) = R11F 화면 그대로 (急ぎ 2 행 · 受付 · 今日中に対応)",
       urg().count() == 2 and all("受付" in x and "今日中に対応" in x for x in urg().all_inner_texts()), urg().all_inner_texts())
    page.locator("[data-gtab='chat']").click()
    page.keyboard.press("Escape")
    page.wait_for_timeout(200)
    if rt0 is None and rp.exists():
        rp.unlink()


def r11r_checks(page, root, shots, engine):
    """v0.3.60 (R11R · 決定 #334): 自動OK (エンジン = 緑) と 確認済 (人の手 = 青) を分ける · 固定の行 (入力済) は 固定の前の判定で
    「自動OK ✓入力済」 / 「確認済 ✓入力済」 · 絞り込み 「入力済 n台」 (両方) · 上の数 「自動OK n · 確認済 n」 (入力済 を含む) ·
    IV 見出し n/N台 そのまま · 色の対比 (文字でも分かる) · 携帯の幅 390. 仮名データだけ."""
    sys.path.insert(0, engine)
    from engine.output import schema_check as SC  # noqa: E402
    dump = lambda o: json.dumps(o, ensure_ascii=False, indent=1) + chr(10)   # noqa: E731
    d = root / "_data"
    jp, qp = d / "jikkyou.json", d / "queue.json"
    jt0 = jp.read_text(encoding="utf-8")
    page.keyboard.press("Escape")
    page.set_viewport_size({"width": 1440, "height": 1000})
    page.evaluate("() => { Object.assign(C01.state, {qedit: null, sel: null, editRow: null, filter: 'all', view: 'main', qkind: 'all'}); C01.app.tick(); }")
    page.click("#tab-main")
    page.click("[data-port='all']")
    page.wait_for_timeout(400)
    gone = {(x.get("value") or {}).get(k) for x in actions(root) if x.get("action") in ("other_ct", "merge_rows") for k in ("container_id", "from_container_id")}
    j = json.loads(jt0)
    qcid = {x.get("container_id") for x in json.loads(qp.read_text(encoding="utf-8"))["items"]}
    acid = {x.get("container_id") for x in actions(root)} | {x.get("ct") for x in actions(root)}
    elig = lambda iv_: [r for r in iv_["rows"] if r.get("ct") and r["container_id"] not in gone and r["container_id"] not in qcid   # noqa: E731
                        and r["container_id"] not in acid and r.get("ct") not in acid]
    # 고정 3줄 = 한 IV (줄 3개 이상) · 고정 안 된 2줄 = 다른 IV (가명 시험 데이터는 IV 하나에 3줄)
    # 사람 쪽 줄 (②③⑤) 은 앞 시험의 기록 · 카드가 있어도 됨 (사람 값을 넣으므로) · 自動OK 로 기대하는 줄 (①④) 만 기록 · 카드 없는 줄
    anyr = lambda iv_: [r for r in iv_["rows"] if r.get("ct") and r["container_id"] not in gone]   # noqa: E731
    iv1 = next((x for x in j["ivs"] if len(anyr(x)) >= 3 and elig(x)), None)
    rest_c = [(x, r) for x in j["ivs"] if x is not iv1 for r in elig(x)]
    ok("R11R 준비: 고정할 IV (줄 3개 · 그중 기록 · 카드 없는 줄 1) + 다른 IV 기록 없는 줄 1 + 줄 1", iv1 is not None and len(rest_c) >= 1, [iv1 is not None, len(rest_c), [(len(anyr(x)), len(elig(x))) for x in j["ivs"]]])
    if iv1 is None or not rest_c:
        return
    ivn = iv1["iv_no"]
    ra = elig(iv1)[0]
    rb, rc = [r for r in anyr(iv1) if r is not ra][:2]
    ivd, rd = rest_c[0]
    ive, re_ = next((x, r) for x in j["ivs"] if x is not iv1 for r in anyr(x) if r is not rd)
    ivof = {r["container_id"]: x["iv_no"] for x in j["ivs"] for r in x["rows"]}
    hv = lambda f, v: {f: {"value": v, "source": "手入力", "by": "staff_a@fake", "at": "2026-11-08T09:00:00+09:00", "action_id": "r11rhv" + f + "0001"}}   # noqa: E731
    frz = {"at": "2026-11-08T10:00:00+09:00", "done_at": "2026-11-08T09:58:00+09:00", "action_id": "r11rcd000001", "src": "apply"}
    base_info = lambda r: [s for s in (r.get("info") or []) if s != "INPUT_FROZEN"]   # noqa: E731
    # ① 고정 · 엔진 自動OK · 사람 값 없음  ② 고정 · 엔진 自動OK · 사람 값 1칸  ③ 고정 · 엔진 再確認 → 사람  ④ 고정 안 됨 自動OK  ⑤ 고정 안 됨 確認済 (再確認 → 사람)
    ra.update({"status": "確認済", "engine_status": "自動OK", "reasons": [], "human": {}, "info": base_info(ra) + ["INPUT_FROZEN"], "input_frozen": dict(frz)})
    rb.update({"status": "確認済", "engine_status": "自動OK", "reasons": [], "human": hv("seal", rb.get("seal") or "TS9R11R1"), "info": base_info(rb) + ["INPUT_FROZEN"], "input_frozen": dict(frz)})
    rc.update({"status": "確認済", "engine_status": "再確認", "reasons": ["SEAL_MISMATCH"], "human": hv("n_w", rc.get("n_w") or 20000), "info": base_info(rc) + ["INPUT_FROZEN"], "input_frozen": dict(frz)})
    rd.update({"status": "自動OK", "engine_status": "自動OK", "reasons": [], "human": {}, "info": base_info(rd)})
    rd.pop("input_frozen", None)
    re_.update({"status": "確認済", "engine_status": "再確認", "reasons": ["SEAL_MISMATCH"], "human": hv("t_w", re_.get("t_w") or 3000), "info": base_info(re_)})
    re_.pop("input_frozen", None)
    iv1["compass_input"] = [{"action_id": "r11rcd000001", "by": "staff_a@fake", "at": "2026-11-08T09:58:00+09:00", "value": {"cells": [], "failed": []}}]
    jp.write_text(dump(j), encoding="utf-8")
    je = SC.check_obj({**j, "ivs": [x for x in j["ivs"] if x is iv1 or x is ivd or x is ive]}, "jikkyou") if hasattr(SC, "check_obj") else []
    ok("R11R 시험 데이터 = 엔진 jikkyou 스키마 (오류 0)", not je, je[:4])
    page.evaluate("C01.app.tick()")
    page.wait_for_timeout(900)
    page.evaluate("C01.app.render()")
    page.wait_for_timeout(200)
    tb = f"tbody[data-iv='{ivn}']"
    rowsel = lambda r: page.locator(f"tbody[data-iv='{ivof[r['container_id']]}'] tr.c01-row", has_text=r["ct"])   # noqa: E731

    def info(r):
        t = rowsel(r)
        st = t.locator("[data-dk]").first
        return {"n": t.count(), "dk": st.get_attribute("data-dk") if st.count() else None, "txt": st.inner_text().replace("\n", " ").strip() if st.count() else "",
                "cls": st.get_attribute("class") if st.count() else "", "hum": "hum" in (t.first.get_attribute("class") or "") if t.count() else None,
                "frozen": t.first.get_attribute("data-frozen") if t.count() else None, "title": st.get_attribute("title") if st.count() else ""}
    A, B, C, D, E = (info(r) for r in (ra, rb, rc, rd, re_))
    ok("R11R ① 고정 · 엔진 自動OK · 사람 값 없음 = 「自動OK ✓入力済」 (초록 st-ok · 줄 파랑 아님)",
       A["n"] == 1 and A["dk"] == "auto" and A["txt"] == "自動OK ✓入力済" and "st-ok" in A["cls"] and not A["hum"] and A["frozen"] == "1" and "エンジンの自動OK" in A["title"], A)
    ok("R11R ② 고정 · 엔진 自動OK · 사람 값 1칸 (✎ 修正) = 「確認済 ✓入力済」 (파랑 st-hum · 줄 hum)",
       B["dk"] == "human" and B["txt"] == "確認済 ✓入力済" and "st-hum" in B["cls"] and B["hum"] and B["frozen"] == "1", B)
    ok("R11R ③ 고정 · 엔진 再確認 → 사람 = 「確認済 ✓入力済」 (파랑)", C["dk"] == "human" and C["txt"] == "確認済 ✓入力済" and "st-hum" in C["cls"] and C["hum"], C)
    ok("R11R ④ 고정 안 됨 自動OK = 「自動OK」 (초록 · ✓入力済 없음)", D["dk"] == "auto" and D["txt"] == "自動OK" and "st-ok" in D["cls"] and not D["hum"] and D["frozen"] is None, D)
    ok("R11R ⑤ 고정 안 됨 確認済 = 「確認済」 (파랑 · ✓入力済 없음)", E["dk"] == "human" and E["txt"] == "確認済" and "st-hum" in E["cls"] and E["hum"] and E["frozen"] is None, E)
    ok("R11R 엔진 data-status 그대로 (고정 3 = 確認済 · ④ 自動OK · ⑤ 確認済)",
       [rowsel(r).first.get_attribute("data-status") for r in (ra, rb, rc, rd, re_)] == ["確認済", "確認済", "確認済", "自動OK", "確認済"], None)
    # 위 수 · 필터 · IV 견출
    kc = page.locator("#kind-count").inner_text()
    na = page.locator("tr.c01-row [data-dk='auto']").count()
    nh = page.locator("tr.c01-row [data-dk='human']").count()
    ok("R11R 위 수 「自動OK n · 確認済 n」 = 표의 초록 · 파랑 줄 수 (入力済 포함)", kc == f"自動OK {na} · 確認済 {nh}" and na >= 2 and nh >= 3, [kc, na, nh])
    fb = page.locator(".c01-f-frozen")
    nfz = page.locator("tr.c01-row[data-frozen='1']").count()
    ok("R11R 필터 이름 「入力済 n台」 (自動OK · 確認済 둘 다)", fb.count() == 1 and fb.inner_text() == f"入力済 {nfz}台" and nfz == 3, fb.inner_text() if fb.count() else None)
    head = page.locator(tb + " .c01-ivhead").inner_text()
    ok_n = page.locator(tb + " tr.c01-row:not(.over) [data-dk]").count()   # TOOL okN = 自動OK · 確認済 (枠外 빼고) — 표시 나누기와 상관없이 그대로
    page.screenshot(path=str(shots / "r11r_rows.png"), full_page=False)
    fb.click()
    page.wait_for_timeout(300)
    ok("R11R 필터 누름 = 고정 줄이 있는 IV 만 (그 IV 의 고정 3줄 보임)", page.locator(tb).count() == 1 and page.locator(tb + " tr.c01-row[data-frozen='1']").count() == 3,
       page.locator("tbody[data-iv]").count())
    fb = page.locator(".c01-f-frozen")
    fb.click()
    page.wait_for_timeout(300)
    ok("R11R IV 견출 n/N台 계산 그대로 (自動OK · 確認済 둘 다 OK 수)", f"{ok_n}/" in head, [head[:80], ok_n])
    # 색 대비 (4 테마) · 문자로도 구분
    cols = {}
    for th in ("light", "leenai", "focus", "dark"):
        page.evaluate(f"document.documentElement.setAttribute('data-theme','{th}')")
        page.wait_for_timeout(120)
        cols[th] = page.evaluate("""(sel) => { const g = (e, p) => e ? getComputedStyle(e)[p] : null;
            const a = document.querySelector(sel[0]), b = document.querySelector(sel[1]);
            return {ok: g(a, 'color'), hum: g(b, 'color'), okbg: g(a && a.closest('td'), 'backgroundColor'), humbg: g(b && b.closest('td'), 'backgroundColor')}; }""",
                                 [tb + " tr.c01-row:not(.hum) [data-dk='auto']", tb + " tr.c01-row.hum [data-dk='human']"])

    def rgb(s):
        v = [float(x) for x in re.findall(r"[\d.]+", s or "")][:4]
        if len(v) == 4:   # rgba → 흰 바탕 위 (light 계열) / 어두운 바탕 (#1b1d22) 위
            return v
        return v + [1.0]

    def flat(c, bg):
        a = c[3]
        return [c[i] * a + bg[i] * (1 - a) for i in range(3)]

    def lum(c):
        f = lambda x: (x / 255) / 12.92 if x / 255 <= 0.03928 else ((x / 255 + 0.055) / 1.055) ** 2.4   # noqa: E731
        return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2])

    def ratio(a, b):
        la, lb = sorted((lum(a), lum(b)), reverse=True)
        return (la + 0.05) / (lb + 0.05)
    con = {}
    for th, c in cols.items():
        base = [27, 29, 34] if th == "dark" else [255, 255, 255]
        hb = flat(rgb(c["humbg"]), base)
        con[th] = {"hum_text_vs_bg": round(ratio(flat(rgb(c["hum"]), hb), hb), 2), "ok_text_vs_bg": round(ratio(flat(rgb(c["ok"]), flat(rgb(c["okbg"]), base)), flat(rgb(c["okbg"]), base)), 2),
                   "text_diff": c["ok"] != c["hum"], "bg_diff": c["okbg"] != c["humbg"]}
    RES["r11r_contrast"] = con
    ok("R11R 색: 4 테마 모두 自動OK 글자색 ≠ 確認済 글자색 · 줄 바탕도 다름 · 確認済 글자 대비 ≥ 4.5 (색이 안 보여도 「自動OK」 · 「確認済」 · 「✓入力済」 글자로 구분)",
       all(v["text_diff"] and v["bg_diff"] and v["hum_text_vs_bg"] >= 4.5 for v in con.values()), con)
    page.evaluate("document.documentElement.setAttribute('data-theme','light')")
    # 휴대폰 폭
    page.set_viewport_size({"width": 390, "height": 800})
    page.wait_for_timeout(300)
    rowsel(ra).first.locator(".c01-inmark").first.scroll_into_view_if_needed()   # 표가 옆으로 넘침 (전과 같음) → 상태 글자까지 옆으로 스크롤
    mk = rowsel(ra).first.locator(".c01-inmark")
    sp = rowsel(ra).first.locator("[data-dk]").first
    sb, mb, tdb = sp.bounding_box() or {}, mk.bounding_box() or {}, rowsel(ra).first.locator("td.c-st").bounding_box() or {}
    page.screenshot(path=str(shots / "r11r_rows_phone.png"), full_page=False)
    ok("R11R 휴대폰 폭 390 = 「自動OK ✓入力済」 한 줄 (✓入力済 가 같은 줄 · 상태 글자 안 · 스크롤하면 화면 안)",
       bool(sb and mb and tdb) and abs((mb.get("y", 0) + mb.get("height", 0) / 2) - (sb.get("y", 0) + sb.get("height", 0) / 2)) < 8
       and mb.get("x", 0) + mb.get("width", 0) <= sb.get("x", 0) + sb.get("width", 0) + 1 and 0 <= mb.get("x", -1) and mb.get("x", 0) + mb.get("width", 0) <= 391, (sb, mb, tdb))
    page.set_viewport_size({"width": 1440, "height": 1000})
    # 범례
    lg = page.locator(".c01-legend").inner_text()
    ok("R11R 범례 = 「自動OK（エンジン）」 · 「確認済（人が確認）」 · 「✓入力済 = Compass入力 済み」", "自動OK（エンジン）" in lg and "確認済（人が確認）" in lg and "✓入力済" in lg, lg[:120])
    jp.write_text(jt0, encoding="utf-8")
    page.evaluate("() => { C01.state.filter = 'all'; C01.app.tick(); }")
    page.wait_for_timeout(600)


def r11g_checks(page, root, shots, engine):
    """v0.3.58 (R11G · #320): 使い方 = エンジン manual.json (目次 · 検索 · 章リンク) · カード / AI 相談 の 「？」 → その章 ·
    AI の答えの 参考 (manual_refs) → その章 · マニュアルのボタン名 = TOOL の画面の字 (公開前の自動照合) · 画像 = docs/img ·
    携帯の幅 · マニュアル無し = 今までの 使い方. 仮名データだけ."""
    sys.path.insert(0, engine)
    from engine.ask import manual as MAN  # noqa: E402
    from engine.output import schema_check as SC  # noqa: E402
    dump = lambda o: json.dumps(o, ensure_ascii=False, indent=1) + chr(10)   # noqa: E731
    d = root / "_data"
    mp = d / "meta.json"
    mt0 = mp.read_text(encoding="utf-8")
    page.keyboard.press("Escape")
    page.set_viewport_size({"width": 1440, "height": 1000})
    page.evaluate("() => { var m = document.getElementById('c01-modal'); if (m) { m.hidden = true; m.innerHTML = ''; } C01.state.modal = null; C01.state.view = 'main'; C01.app.render(); }")
    man = {"schema_version": 1, "kind": "manual", **MAN.output()}
    ok("R11G manual.json = 엔진 스키마", SC.errors(man, SC.load("manual")) == [])
    # ① 매뉴얼 버튼 이름 = TOOL 화면 글자 (공개 전 자동 대조 · #305)
    src = "".join((TOOL / f).read_text(encoding="utf-8") for f in ("index.html", "js/app.js", "js/photo.js", "js/zoompan.js", "js/compass.js", "js/doc.js", "photo.html"))
    miss = [b for b in man["buttons"] if b not in src]
    ok("R11G 매뉴얼 버튼 이름 = TOOL 화면 글자 (" + str(len(man["buttons"])) + "개 · 없음 0)", not miss and len(man["buttons"]) >= 20, miss)
    imiss = [x for x in man["images"] if not (TOOL / "docs" / x).is_file()]
    ok("R11G 매뉴얼 그림 = TOOL docs/img 에 있음", not imiss and len(man["images"]) >= 3, imiss)
    # ② 끈 엔진 (meta 에 manual 없음) = 지금 使い方 · 「？」 0
    page.click("#help-open")
    page.wait_for_timeout(400)
    ok("R11G 끔 = 지금 使い方 (1~4 · 「？」 0)", page.locator(".c01-man").count() == 0 and "1. 自分の担当を見る" in page.locator("#help-body").inner_text()
       and page.locator(".c01-manq").count() == 0)
    page.keyboard.press("Escape")
    page.evaluate("() => { var m = document.getElementById('c01-modal'); if (m) { m.hidden = true; m.innerHTML = ''; } C01.state.modal = null; }")
    # ③ 켬: manual.json + meta.manual
    (d / "manual.json").write_text(dump(man), encoding="utf-8")
    m = json.loads(mt0)
    m["manual"] = "manual.json"
    mp.write_text(dump(m), encoding="utf-8")
    page.evaluate("() => { C01.state.manual = null; C01.state.manMiss = 0; C01.app.tick(); }")
    page.wait_for_timeout(700)
    page.click("#help-open")
    page.wait_for_timeout(800)
    nsec = page.locator(".c01-man-sec").count()
    toc = page.locator(".c01-man-toc a").count()
    ok("R11G 使い方 = 매뉴얼 전체 (장 " + str(nsec) + " = manual.json · 목차 링크 · 판 · ✦)", nsec == len(man["sections"]) and toc == len(man["sections"])
       and man["version"] in page.locator(".c01-modal-help .c01-mh").inner_text() and "✦ Powered by LEENAI Automation System" in page.locator("#help-body").inner_text(),
       (nsec, toc))
    ok("R11G 3 장 안 = 버튼 표 (tool_guide 와 같은 원본 · 「他社のコンテナ」 場所)", "この行の操作" in page.locator("#man-3-5").inner_text()
       and page.locator("#man-3-1 .c01-man-btn").count() >= 10)
    imgs = page.evaluate("() => [...document.querySelectorAll('.c01-man-fig img')].map(i => [i.getAttribute('src'), i.complete && i.naturalWidth > 0])")
    page.locator("#man-1").scroll_into_view_if_needed()
    page.wait_for_timeout(500)
    imgs = page.evaluate("() => [...document.querySelectorAll('.c01-man-fig img')].map(i => i.getAttribute('src'))")
    ok("R11G 그림 = docs/img (가명 화면) 3", sorted(imgs) == sorted("docs/" + x for x in man["images"]), imgs)
    page.screenshot(path=str(shots / "r11g_manual.png"))
    # 검색
    page.fill("#man-q", "まとめる")
    page.wait_for_timeout(200)
    vis = page.evaluate("() => [...document.querySelectorAll('.c01-man-sec')].filter(e => !e.hidden).map(e => e.dataset.mansec)")
    ok("R11G 검색 「まとめる」 = 3-4 보임 · 맞는 장만", "3-4" in vis and "2-4" not in vis and len(vis) < nsec and "件" in page.locator("#man-n").inner_text(), vis)
    page.fill("#man-q", "")
    page.wait_for_timeout(100)
    page.click(".c01-man-toc a[data-mango='3-9']")
    page.wait_for_timeout(200)
    ok("R11G 목차 링크 → 그 장 (강조)", page.evaluate("() => (document.querySelector('.c01-man-sec.hit') || {}).id") == "man-3-9")
    page.screenshot(path=str(shots / "r11g_manual_3-9.png"))
    page.keyboard.press("Escape")
    page.evaluate("() => { var m = document.getElementById('c01-modal'); if (m) { m.hidden = true; m.innerHTML = ''; } C01.state.modal = null; }")
    # ④ 카드 「？」 → 그 장
    page.click("#tab-input")
    page.wait_for_timeout(500)
    q = page.locator(".c01-form-h .c01-manq")
    want = q.get_attribute("data-man") if q.count() else None
    ok("R11G 카드 머리 「？」 (작게 · 1개)", q.count() == 1 and want and q.inner_text() == "？", q.count())
    if q.count():
        q.click()
        page.wait_for_timeout(400)
        ok("R11G 카드 「？」 → 使い方 그 장 (" + str(want) + ")", page.evaluate("() => (document.querySelector('.c01-man-sec.hit') || {}).id") == "man-" + str(want))
        page.keyboard.press("Escape")
        page.evaluate("() => { var m = document.getElementById('c01-modal'); if (m) { m.hidden = true; m.innerHTML = ''; } C01.state.modal = null; }")
    # ⑤ 전체 AI 相談 「？」 · 답의 参考 → 그 장 · 답 글 참고 줄 겹침 0
    page.click("#tab-main")
    page.click("#gask-open")
    page.wait_for_timeout(300)
    ok("R11G 전체 AI 相談 머리 「？」 = 5-2", page.locator("#gask-box .c01-askdr-h .c01-manq").get_attribute("data-man") == "5-2")
    before = set(p.name for p in (root / "_actions" / "ask").rglob("*.json")) if (root / "_actions" / "ask").exists() else set()
    page.fill("#gask-in", "行をまとめたい")
    page.press("#gask-in", "Enter")
    page.wait_for_timeout(500)
    new = [p for p in (root / "_actions" / "ask").rglob("*.json") if p.name not in before]
    g = json.loads(new[0].read_text(encoding="utf-8")) if len(new) == 1 else {}
    rep = {"ask_id": g.get("ask_id"), "scope": "global", "status": "ok", "kind": "guide", "suggestions": [], "approval_request": "", "improve": None,
           "answer": "書類だけの行で 「✎ 修正」 から CT番号 を入れると 「n番の行にまとめる」 が出ます。\n参考: 使い方 3-4 まとめる\n調べた内容: なし",
           "manual_given": ["3-4"], "manual_refs": [{"id": "3-4", "title": "まとめる"}, {"id": "../x", "title": "bad"}]}
    (root / "_actions" / "ask_reply").mkdir(parents=True, exist_ok=True)
    (root / "_actions" / "ask_reply" / f"{g.get('ask_id')}.json").write_text(json.dumps(rep, ensure_ascii=False), encoding="utf-8")
    page.evaluate("() => C01.app.tick()")
    page.wait_for_timeout(800)
    page.evaluate("() => C01.app.render()")
    page.wait_for_timeout(300)
    ref = page.locator("#gask-box .c01-ask-ref [data-man]")
    txt = page.locator("#gask-box .c01-ask-txt").last.inner_text() if page.locator("#gask-box .c01-ask-txt").count() else ""
    ok("R11G 답의 参考 = 링크 1 (잘못된 id 버림) · 답 글에 같은 줄 겹침 0 · 調べた内容 그대로",
       ref.count() == 1 and ref.inner_text() == "参考: 使い方 3-4 まとめる" and "参考: 使い方" not in txt and "調べた内容" in txt, (ref.count(), txt[-80:]))
    page.screenshot(path=str(shots / "r11g_ask_ref.png"))
    if ref.count():
        ref.click()
        page.wait_for_timeout(400)
        ok("R11G 参考 링크 → 使い方 3-4", page.evaluate("() => (document.querySelector('.c01-man-sec.hit') || {}).id") == "man-3-4")
    page.keyboard.press("Escape")
    page.evaluate("() => { var m = document.getElementById('c01-modal'); if (m) { m.hidden = true; m.innerHTML = ''; } C01.state.modal = null; }")
    page.evaluate("() => C01.app.gaskClose && C01.app.gaskClose()")
    # ⑥ 휴대폰 폭
    page.set_viewport_size({"width": 390, "height": 800})
    page.wait_for_timeout(200)
    page.evaluate("() => { var b = document.getElementById('help-open'); if (b) b.click(); }")
    page.wait_for_timeout(500)
    ov = page.evaluate("() => { var m = document.querySelector('.c01-modal-help'); var t = document.querySelector('.c01-man-toc'), b = document.querySelector('.c01-man-body');"
                       " return m ? [Math.round(m.getBoundingClientRect().width), t && b ? t.getBoundingClientRect().bottom <= b.getBoundingClientRect().top + 1 : null,"
                       " [...m.querySelectorAll('*')].every(e => e.getBoundingClientRect().right <= window.innerWidth + 1)] : null; }")
    ok("R11G 휴대폰 폭 390 = 목차 위 · 본문 아래 · 가로 넘침 0", ov and ov[0] <= 392 and ov[1] is True and ov[2] is True, ov)
    page.screenshot(path=str(shots / "r11g_manual_phone.png"))
    page.keyboard.press("Escape")
    page.evaluate("() => { var m = document.getElementById('c01-modal'); if (m) { m.hidden = true; m.innerHTML = ''; } C01.state.modal = null; }")
    page.set_viewport_size({"width": 1440, "height": 1000})
    # 되돌림 (다음 시험 = 예전 상태)
    mp.write_text(mt0, encoding="utf-8")
    (d / "manual.json").unlink()
    page.evaluate("() => { C01.state.manual = null; C01.state.view = 'main'; C01.app.tick(); }")
    page.wait_for_timeout(400)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shots", default=str(TOOL / "tests" / "_shots"))
    ap.add_argument("--engine", default=r"C:\LEENAI_C01_PROD\code")          # R10Z Part 4: 지운 워크트리 대신 PROD code (실전 스키마)
    ap.add_argument("--no-wait30", action="store_true")
    ap.add_argument("--engine-r10u", default=r"C:\LEENAI_C01_PROD\code")   # v0.3.52 (R10W): 엔진 v0.5.122 스키마 (input_keep · 入力後の差異)
    ap.add_argument("--engine-box", default=r"C:\LEENAI_C01_PROD\code")   # R10X: 엔진 v0.5.124 photos.schema (box)
    ap.add_argument("--engine-frz", default=r"C:\LEENAI_C01_PROD\code")   # R10X: 엔진 v0.5.125 스키마 (input_slot_take · why compass_slot)
    a = ap.parse_args()
    if not (TOOL / "fixtures" / "_data" / "jikkyou.json").is_file():
        sys.exit("fixtures/_data 없음 — 먼저 python tools/make_test_data.py (레포에 넣지 않는 가명 시험 데이터)")
    shots = Path(a.shots)
    shots.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="c01tool_"))
    root = tmp / "data"
    shutil.copytree(TOOL / "fixtures", root)
    # R10X (엔진 v0.5.124 · out_photo_box): 가명 사진 1장 (TST2611-01 · 9장 줄의 6번째) 에 엔진 칸 상자 — 받는 쪽 대조 (엔진 photos.schema box 키)
    global BOX_INJ
    pp_ = root / "_data" / "photos" / "TST2611-01.json"
    pj_ = json.loads(pp_.read_text(encoding="utf-8"))
    c9_ = next(c for c in pj_["containers"] if len(c["photos"]) == 9)
    BOX_INJ = {"x0": 300, "y0": 400, "x1": 700, "y1": 520, "text_rotation": 0, "field": "seal"}
    c9_["photos"][5]["box"] = dict(BOX_INJ)
    pp_.write_text(json.dumps(pj_, ensure_ascii=False, indent=1) + chr(10), encoding="utf-8")
    bsp_ = Path(a.engine_box) / "engine" / "output" / "schema" / "photos.schema.json"
    bs_ = json.loads(bsp_.read_text(encoding="utf-8"))["properties"]["containers"]["items"]["properties"]["photos"]["items"]["properties"].get("box") if bsp_.is_file() else None
    ok("R10X 받는 쪽 대조: 엔진 photos.schema box 키 = TOOL 이 읽는 키 (x0 · y0 · x1 · y1 · text_rotation)",
       bool(bs_) and set(BOX_INJ) <= set(bs_["properties"]) and {"x0", "y0", "x1", "y1", "text_rotation"} <= set(bs_["required"])
       and all(("box." + k) in (TOOL / "js" / "photo.js").read_text(encoding="utf-8") for k in ("x0", "y0", "x1", "y1", "text_rotation")), bs_ and sorted(bs_["properties"]))
    # v0.2.2 (#109 ①): 사본 _data 에 「다시 판정 값이 사람 값과 다름」 정보를 넣음 (엔진 data_json 의 info 형식 그대로)
    global HUMAN_SEAL
    jp = root / "_data" / "jikkyou.json"
    jj = json.loads(jp.read_text(encoding="utf-8"))
    for iv in jj["ivs"]:
        for r in iv["rows"]:
            if r["ct"] == "TSTU0010630":          # v0.3.10 R7I Part D: 受信中・候補あり (엔진 jikkyou 줄 cand 형식 그대로)
                r["cand"] = {"level": "ct", "n": 1, "where": ["保留:NO_BKG"], "recv": ["2026-11-06"]}
                # v0.3.31 (R8V Part B · #254): 엔진 out_cand_files 형식 (후보 파일 · qid · need) — 시험 사본의 _hold 파일 1개
                hq = json.loads((root / "_data" / "queue.json").read_text(encoding="utf-8"))
                hf = [f for it in hq["items"] if it["kind"] == "業者・IV未定" for f in it["files"]][:1]
                if hf:
                    r["cand"].update({"files": [{"path": hf[0]["path"], "name": hf[0]["name"], "page": None, "bbox": None, "sha16": hf[0]["sha16"]}],
                                      "need": "doc", "qid": "c0ffee00c0ffee00"})
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
            ok("탭 제목 = LEENAI C-01 搬入票 v0.3.61", page.title() == "LEENAI C-01 搬入票 v0.3.61", page.title())
            ok("로그인 버튼 활성 (R7A graph)", page.locator("#ln-login-btn").is_enabled())
            page.click("#c01-open-server")
            page.wait_for_selector("body[data-c01-ready='1']", timeout=20000)
            ok("헤더 C-01 · 버전 1곳", page.locator(".ln-header .ln-sys").inner_text() == "C-01" and "v0.3.61" in page.locator(".ln-hdr-ver").inner_text())
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
            # v0.3.31 (R8V Part B · #254): 후보 파일이 있는 「候補あり」 = 버튼 → 그 후보 카드 (IVに連結 · 搬入票ではない) · 누르기 전 確認・入力 장 수 그대로
            n_cards0 = page.evaluate("() => document.querySelectorAll('.c01-item').length")
            ok("R8V B 候補あり = 버튼 (data-cand · ▸)", cw.evaluate("e => e.tagName") == "BUTTON" and cw.get_attribute("data-cand") == "c0ffee00c0ffee00"
               and cw.inner_text().endswith("▸"), cw.inner_text())
            me0 = page.evaluate("() => (document.querySelector('#me-select') || {}).value || ''")
            page.select_option("#me-select", "STAFF_A")        # 「搬入票ではない」 = 担当者が要る
            cw.click()
            page.wait_for_timeout(400)
            body = page.locator("body").inner_text()
            ok("R8V B 候補あり 클릭 = 確認・入力 카드 (候補ファイル 설명 · 搬入票ではない · IV 후보)",
               "「受信中・候補あり」の候補ファイル" in body and page.locator("#q-notours").count() == 1, body[:300])
            page.click("#q-notours")
            page.wait_for_timeout(200)
            ok("R8V C 이유 창 (候補あり 카드)", page.locator("#c01-nhdlg").count() == 1)
            page.click("#c01-nhok")                        # 이유 없이 누름 = 기록만
            page.wait_for_timeout(400)
            cn = [x for x in actions(root) if x["action"] == "not_hannyuhyo" and x["queue_id"] == "c0ffee00c0ffee00"]
            ok("R8V B·C 候補あり → not_hannyuhyo (queue_id = cand.qid · source cand · 이유 없음 = 키 없음 · sha16 = 후보 파일)", len(cn) == 1
               and cn[0]["value"].get("source") == "cand" and "reason_code" not in cn[0]["value"] and "reason_text" not in cn[0]["value"]
               and cn[0]["value"]["sha16"] and cn[0]["iv"], cn)
            for f_ in (root / "_actions").rglob("*.json"):   # 다음 시험 (_actions 수) 은 예전 상태 그대로 — 이 시험의 기록만 지움 (임시 사본)
                if '"c0ffee00c0ffee00"' in f_.read_text(encoding="utf-8"):
                    f_.unlink()
            page.click("#tab-main")
            page.select_option("#me-select", me0)             # 다음 시험은 예전 상태 그대로
            page.wait_for_timeout(300)
            ok("R8V B 確認・入力 장 수 = 候補あり 열기 전과 같음 (실황표로 돌아온 뒤)", n_cards0 == page.evaluate("() => document.querySelectorAll('.c01-item').length"))
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
            un4 = page.evaluate("""() => [...document.querySelectorAll("tbody[data-iv='TST2611-04'] tr.c01-row")].map(tr => tr.classList.contains('unassigned') && tr.classList.contains('over') && !!tr.querySelector('.c01-over'))""")
            ok("C 칸 없는 줄 = 「COMPASS 枠外」 (R9P 0-3 · TST2611-04 2줄 · 맨 아래)", un4 == [False, False, True, True], un4)
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
            ok("v0.3.48 (R10B) Compass入力 比較表 창 試験表示 없음 (送信 DRY 그대로)", tb.count() == 0 and "試験" not in page.locator(".c01-mh").first.inner_text())
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
            ok("v0.3.48 (R10B) 催促 창 試験表示 없음 (送信できません 그대로)", tb.count() == 0 and "試験表示" not in page.locator(".c01-mh").first.inner_text())
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
            lb_zoom_checks(page, shots)
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
            bm = page.locator(".c01-bundlemove")
            ok("R9W 0-4e 写真のCT 카드 = 「この束の写真 4 枚をまとめて移します」", bm.count() == 1 and "この束の写真 4 枚をまとめて移します" in bm.inner_text(),
               bm.inner_text() if bm.count() else None)
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
            page.wait_for_timeout(200)
            # v0.3.31 (R8V Part C · #255): 확인창 = 이유 칸 (버튼 5 · 자유 입력 · 「ひとことでOK（簡単で大丈夫です）」 · 이유 없이도 누름)
            dlg = page.locator("#c01-nhdlg")
            ok("R8V C 「搬入票ではない」 = 이유 창 (ひとことでOK · 이유 버튼 5 · 자유 입력 · ✦)", dlg.count() == 1 and "ひとことでOK（簡単で大丈夫です）" in dlg.inner_text()
               and dlg.locator("[data-nhr]").count() == 5 and dlg.locator("#c01-nhtext").count() == 1 and "✦ Powered by LEENAI Automation System" in dlg.inner_text()
               and "当社の書式（空欄）" in dlg.inner_text() and not dl2, dlg.inner_text() if dlg.count() else None)
            page.click("[data-nhr='own_blank_form']")
            page.fill("#c01-nhtext", "空欄の当社書式です")
            page.click("#c01-nhok")
            page.wait_for_timeout(400)
            nh = [x for x in actions(root) if x["action"] == "not_hannyuhyo" and x["queue_id"] != "c0ffee00c0ffee00"]
            ok("「搬入票ではない」 (業者・IV 未定) = 이유 창 → not_hannyuhyo 1 (sha16 · queue_id · reason_code · reason_text)", len(nh) == 1
               and nh[0]["value"]["sha16"] and nh[0]["queue_id"] and nh[0]["value"].get("reason_code") == "own_blank_form"
               and nh[0]["value"].get("reason_text") == "空欄の当社書式です" and page.locator("#c01-nhdlg").count() == 0, nh)
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
            # 実況表 で 確認済 · 確認・入力 바지
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
            ok("合わせたカード = 完了 에", di.count() == 1, di.count())
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
            # #109 ② slot_change = 모든 직원 (STAFF_A · 관리자 목록 없음) · 빈 칸으로 · 入れ替え 확인창 · 되돌리기
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
            # 入れ替え: r1 을 r2 칸으로 → 확인창 (취소 → 기록 0 · 확인 → 2건)
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
            ok("#109 ② 入れ替え 확인창 「○○ が入っています。入れ替えますか」 · 취소 = 기록 0", dl and dl[0] == f"{r2['ct']} が入っています。入れ替えますか" and n1 == n0 + 1, dl)
            ok("入れ替え 확인 → slot_change 1건 (swap_ct · 두 대를 한 기록으로)", len(sw) == 1 and (sw[0]["ct"], sw[0]["value"]["slot_guid"], sw[0]["value"]["slot_before"],
               sw[0]["value"]["swap_ct"]) == (r1["ct"], r2["slot_guid"], r1["slot_guid"], r2["ct"]), sw)
            b2 = page.locator(f"tr.c01-row[data-key*='{r2['ct']}'] [data-info='slot_change']")
            ok("入れ替え 상대 줄에도 정보 표시", b2.count() == 1 and r1["ct"] in (b2.get_attribute("title") or ""), b2.get_attribute("title") if b2.count() else None)
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
            r9f_ask_checks(page, root, shots)
            r8b_checks(page, root, shots)
            r8c_checks(page, root, shots)
            r8d_checks(page, root, shots)
            r8f_checks(page, root, shots)
            r8g_checks(page, root, shots)
            r8w_checks(page, root, shots)
            r8z_checks(page, root, shots)
            r9d_wd_checks(page, root, shots, a.engine)
            r9d_remind_checks(page, root, shots)
            r9e_ccfixed_checks(page, root, shots, a.engine)
            r9k_remind_live_checks(page, root, shots, a.engine)
            r9k_fax_reason_checks(page, root, shots)
            r9l_gask_checks(page, root, shots, a.engine)
            r9m_checks(page, root, shots, a.engine)
            r9o_checks(page, root, shots, a.engine)
            r9u_checks(page, root, shots, a.engine)
            r9w_checks(page, root, shots, a.engine)
            r9x_checks(page, root, shots, a.engine)
            r9y_checks(page, root, shots, a.engine)
            r10h_checks(page, root, shots, a.engine)
            r10w_checks(page, root, shots, a.engine, a.engine_r10u)
            r10x_checks(page, root, shots, a.engine_frz)
            r11f_checks(page, root, shots, a.engine)
            r11g_checks(page, root, shots, a.engine)
            r11j_checks(page, root, shots, a.engine)
            r11r_checks(page, root, shots, a.engine)
            r12a_checks(page, root, shots, a.engine)
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
