# ✦ Powered by LEENAI Automation System — v0.3.91 (R12Y73 · #417) 実況表 IV 見出し 「CY MM/DD」 急ぎ 색 (CY CUT ≤ 다음 영업일)
"""Playwright · 가명 fixtures · serve_local (실제 메일 · SharePoint · COMPASS 호출 0). 확인:
 B1 영업일 표 = 엔진 催促 is_biz (jpholiday) 와 2026-01-01 ~ 2028-12-31 하루씩 같음
 B2 금요일 → 다음 월요일 CUT 색 · 화요일 CUT 색 없음 · 오늘 CUT 색 · 토요일 CUT 색
 B3 공휴일 앞 (11/20 금 → 11/23 월 祝 → 11/24 화 까지) · 연휴 (5/1 → 5/7 까지) · 빈 값 · 틀린 꼴 = 없음
 B4 자정 경계: 엔진 날 (info.today) 이 어제여도 이 端末 JST 0:00 지나면 다음 날 기준 (23:59:59 / 00:00:00)
 B5 화면: 날짜 글자만 span (▼ CY 글자 · 줄 색 · 줄 수 · 순서 · 필터 그대로) · title 「次の営業日までの CUT」 · 색 = 다크 / 라이트 둘 다 보통 글자와 다름 (대비 4.5 이상) · 캡처 2장
 콘솔 오류 0
사용: python tests/test_cyurgent_r12y73.py [--shots 폴더] [--engine 엔진 레포]"""
import argparse
import datetime as dt
import json
import shutil
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_graph as TGR   # noqa: E402

TOOL = Path(__file__).resolve().parent.parent
RES = {"checks": [], "console_errors": []}


def ok(name, cond, detail=""):
    RES["checks"].append({"name": name, "ok": bool(cond), "detail": str(detail)[:300]})
    print(("OK  " if cond else "NG  ") + name + (f" — {detail}" if detail and not cond else ""), flush=True)


def lum(rgb):
    def ch(c):
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = rgb
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def contrast(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def rgb(s):
    import re
    m = re.findall(r"[\d.]+", s or "")
    return tuple(int(float(x)) for x in m[:3]) if len(m) >= 3 else None


def heads(page):
    return page.evaluate("""() => [...document.querySelectorAll('#jikkyou-table tbody[data-iv]')].map(t => {
      const b = t.querySelector('.c01-ivhead .b'), u = b && b.querySelector('.c01-cyurgent');
      return { iv: t.getAttribute('data-iv'), text: b ? b.textContent : null, urgent: u ? u.textContent : null, title: u ? u.title : null,
               rows: [...t.querySelectorAll('tr.c01-row')].map(r => r.className).join('|') }; })""")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shots")
    ap.add_argument("--engine", default=r"C:\LEENAI_C01_V2\engine")
    a = ap.parse_args()
    if not (TOOL / "fixtures" / "_data" / "jikkyou.json").is_file():
        sys.exit("fixtures/_data 없음 — 먼저 python tools/make_test_data.py")
    sys.path.insert(0, a.engine)
    from engine.notify import remind as RM          # 엔진 催促 의 영업일 (jpholiday)
    shots = Path(a.shots) if a.shots else Path(tempfile.mkdtemp(prefix="c01_r12y73_shots_"))
    shots.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="c01_r12y73_"))
    root = tmp / "fx"
    shutil.copytree(TOOL / "fixtures", root)
    # fixtures CUT: 01=11/09(월) 02=11/10(화) 03=11/13(금) 04=11/12(목) 05=11/17(화) · 오늘 = 11/06 (금) → 다음 영업일 11/09 (월) → 01 만 색
    port = TGR.free_port()
    import socket
    import subprocess
    import time
    srv = subprocess.Popen([sys.executable, str(TOOL / "tools" / "serve_local.py"), "--root", str(root), "--port", str(port), "--today", "2026-11-06"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(50):
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
            break
        except OSError:
            time.sleep(0.1)
    try:
        with sync_playwright() as p:
            br = p.chromium.launch()
            ctx = br.new_context(viewport={"width": 1600, "height": 900})
            page = ctx.new_page()
            page.on("console", lambda m: RES["console_errors"].append(m.text) if m.type == "error" else None)
            page.on("pageerror", lambda e: RES["console_errors"].append(f"pageerror {e}"))
            # 이 端末 시계 = 2026-11-06 10:00 JST (엔진 날과 같음)
            page.clock.set_fixed_time(dt.datetime(2026, 11, 6, 1, 0, 0, tzinfo=dt.timezone.utc))
            page.goto(f"http://127.0.0.1:{port}/")
            page.wait_for_selector("#c01-open-server", timeout=20000)
            page.click("#c01-open-server")
            page.wait_for_selector("body[data-c01-ready='1']", timeout=20000)
            page.wait_for_timeout(300)
            # B1 엔진과 하루씩 대조
            d0, d1 = dt.date(2026, 1, 1), dt.date(2028, 12, 31)
            days = [(d0 + dt.timedelta(days=i)).isoformat() for i in range((d1 - d0).days + 1)]
            js = page.evaluate("(ds) => ds.map(d => C01.bizday.isBizDay(d))", days)
            py = [RM.is_biz(dt.date.fromisoformat(d)) for d in days]
            diff = [d for d, x, y in zip(days, js, py) if x != y]
            ok(f"B1 영업일 = 엔진 is_biz ({len(days)}일 · 다름 0)", RM.jpholiday is not None and not diff, diff[:5])
            nb = page.evaluate("(ds) => ds.map(d => C01.bizday.nextBizDay(d))", days[:400])
            exp = []
            for d in days[:400]:
                x = dt.date.fromisoformat(d) + dt.timedelta(days=1)
                while not RM.is_biz(x):
                    x += dt.timedelta(days=1)
                exp.append(x.isoformat())
            ok("B1 다음 영업일 = 엔진 기준 (400일)", nb == exp, [(d, a1, b1) for d, a1, b1 in zip(days, nb, exp) if a1 != b1][:3])
            cases = page.evaluate("""() => { const f = C01.bizday.cyUrgent; return {
              friMon: f('2026-11-30', '2026-11-27'), friTue: f('2026-12-01', '2026-11-27'), friToday: f('2026-11-27', '2026-11-27'),
              friSat: f('2026-11-28', '2026-11-27'), thuFri: f('2026-11-27', '2026-11-26'), thuMon: f('2026-11-30', '2026-11-26'),
              holTue: f('2026-11-24', '2026-11-20'), holWed: f('2026-11-25', '2026-11-20'), gwThu: f('2026-05-07', '2026-05-01'), gwFri: f('2026-05-08', '2026-05-01'),
              empty: f('', '2026-11-27'), bad: f('11/27', '2026-11-27'), dt: f('2026-11-30T00:00:00', '2026-11-27') }; }""")
            ok("B2 금요일 → 월요일 CUT 색 · 화요일 없음 · 오늘 · 토요일 색", cases["friMon"] and not cases["friTue"] and cases["friToday"] and cases["friSat"], cases)
            ok("B2 목요일 → 금요일까지 (월요일 없음)", cases["thuFri"] and not cases["thuMon"], cases)
            ok("B3 공휴일 앞 (11/23 祝 → 11/24 까지) · 연휴 (5/7 까지)", cases["holTue"] and not cases["holWed"] and cases["gwThu"] and not cases["gwFri"], cases)
            ok("B3 빈 값 · 틀린 꼴 = 없음 · 시각 붙은 꼴 = 날짜로", not cases["empty"] and not cases["bad"] and cases["dt"], cases)
            # B4 자정: 엔진 날 11/06 그대로 · 端末 JST 23:59:59 = 11/06 · 00:00:00 = 11/07
            mid = page.evaluate("""() => { const D = Date.now; const r = {};
              Date.now = () => Date.UTC(2026, 10, 6, 14, 59, 59); r.before = C01.bizday.urgentToday();
              Date.now = () => Date.UTC(2026, 10, 6, 15, 0, 0); r.after = C01.bizday.urgentToday();
              r.cutTueAfter = C01.bizday.cyUrgent('2026-11-10');
              Date.now = () => Date.UTC(2026, 10, 5, 10, 0, 0); r.devOld = C01.bizday.urgentToday();
              Date.now = D; return r; }""")
            ok("B4 자정 경계 (23:59:59 = 11/06 · 00:00 = 11/07 · 端末 시계가 늦으면 엔진 날)",
               mid["before"] == "2026-11-06" and mid["after"] == "2026-11-07" and mid["devOld"] == "2026-11-06", mid)
            ok("B4 토요일 0:00 지나면 다음 영업일 = 월 (화요일 CUT 없음)", mid["cutTueAfter"] is False, mid)
            # B5 화면
            h = heads(page)
            by = {x["iv"]: x for x in h}
            urg = sorted(x["iv"] for x in h if x["urgent"])
            ok("B5 색 = CUT 11/09 (다음 영업일 월) IV 만", urg == ["TST2611-01"], [(x["iv"], x["text"], x["urgent"]) for x in h])
            u = by.get("TST2611-01") or {}
            ok("B5 날짜 글자만 · ▼ CY 글자 그대로 · title", u.get("text") == "▼ CY 11/09" and u.get("urgent") == "11/09" and u.get("title") == "次の営業日までの CUT", u)
            others = [x for x in h if x["iv"] != "TST2611-01"]
            ok("B5 다른 IV 머리줄 = 「▼ CY MM/DD」 그대로", all(x["text"].startswith("▼ CY ") and x["urgent"] is None for x in others), others[:2])
            # 줄 색 · 순서 · 필터 = 색 없는 시안과 같음 (cyUrgent 를 끈 화면과 비교)
            base = page.evaluate("""() => [...document.querySelectorAll('#jikkyou-table tbody[data-iv]')].map(t => t.getAttribute('data-iv') + ':' +
                [...t.querySelectorAll('tr.c01-row')].map(r => r.className + '/' + (r.getAttribute('data-status') || '')).join('|'))""")
            filt = page.evaluate("() => [...document.querySelectorAll('.c01-f')].map(e => e.textContent.trim())")
            cols = {}
            for th in ("dark", "light"):
                page.evaluate("(t) => document.documentElement.setAttribute('data-theme', t)", th)
                page.wait_for_timeout(150)
                c = page.evaluate("""() => { const b = document.querySelector("tbody[data-iv='TST2611-01'] .c01-ivhead .b"), u = b.querySelector('.c01-cyurgent');
                  const n = document.querySelector("tbody[data-iv='TST2611-02'] .c01-ivhead .b");
                  let el = b.closest('tr'), bg = 'rgba(0, 0, 0, 0)';
                  while (el && (bg === 'rgba(0, 0, 0, 0)' || bg === 'transparent')) { bg = getComputedStyle(el).backgroundColor; el = el.parentElement; }
                  return { u: getComputedStyle(u).color, uw: getComputedStyle(u).fontWeight, n: getComputedStyle(n).color, bg: bg }; }""")
                cols[th] = c
                page.locator("tbody[data-iv='TST2611-01'] tr.c01-ivrow").screenshot(path=str(shots / f"r12y73_cy_{th}.png"))
                page.locator("#jikkyou-table").screenshot(path=str(shots / f"r12y73_table_{th}.png"))
            for th, c in cols.items():
                cr = contrast(rgb(c["u"]), rgb(c["bg"])) if rgb(c["u"]) and rgb(c["bg"]) else 0
                ok(f"B5 {th}: 날짜 색 ≠ 보통 글자 · 굵게 · 대비 {cr:.1f} ≥ 4.5", c["u"] != c["n"] and int(c["uw"]) >= 700 and cr >= 4.5, c)
            page.locator(".c01-f").first.click()
            page.wait_for_timeout(150)
            page.locator(".c01-f").first.click()
            page.wait_for_timeout(150)
            base2 = page.evaluate("""() => [...document.querySelectorAll('#jikkyou-table tbody[data-iv]')].map(t => t.getAttribute('data-iv') + ':' +
                [...t.querySelectorAll('tr.c01-row')].map(r => r.className + '/' + (r.getAttribute('data-status') || '')).join('|'))""")
            filt2 = page.evaluate("() => [...document.querySelectorAll('.c01-f')].map(e => e.textContent.trim())")
            ok("B5 줄 색 · 순서 · 필터 수 = 그대로 (필터 눌렀다 풀어도 같음)", base == base2 and filt == filt2, [base[:2], base2[:2]])
            ctx.close()
            br.close()
    finally:
        srv.terminate()
    ok("콘솔 오류 0", not RES["console_errors"], RES["console_errors"][:3])
    print(json.dumps({"ok": sum(c["ok"] for c in RES["checks"]), "ng": sum(not c["ok"] for c in RES["checks"]), "shots": str(shots)}, ensure_ascii=False))
    sys.exit(0 if all(c["ok"] for c in RES["checks"]) else 1)


if __name__ == "__main__":
    main()
