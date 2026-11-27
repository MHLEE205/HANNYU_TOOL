# ✦ Powered by LEENAI Automation System — v0.3.92 (R12Y74 · #419) 実況表 IV 区切り A (머리줄 한 단계 진하게 · 위 2px 선 · 왼쪽 4px 띠 · IV 사이 10px)
"""Playwright · 가명 fixtures · serve_local (실제 메일 · SharePoint · COMPASS 호출 0). 확인 (테마 4 = dark · light · leenai · focus):
 S1 IV 머리줄 배경 = --ivhead-strong (예전 --ivhead 보다 진함 · 글자 대비 4.5 이상) · 위 2px 선 + 왼쪽 4px 띠 = 강조색
 S2 첫 IV 위 틈 0 · 그 밖 IV 위 10px 틈 (색 = 표 바탕)
 S3 머리줄 배경 ≠ 줄 상태 색 (自動OK · 確認済 · 要確認 · 受信中 · 枠外)
 S4 줄 (c01-row) 배경 · 글자 · 줄 수 · 순서 · 필터 · CY 날짜 색 = 새 규칙을 끈 화면과 같음
 S5 1920 · 1366 · 1100 폭 가로 넘침 0 · 인쇄 (PDF) 됨 · 캡처
 콘솔 오류 0
사용: python tests/test_ivsep_r12y74.py [--shots 폴더]"""
import argparse
import datetime as dt
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_graph as TGR   # noqa: E402

TOOL = Path(__file__).resolve().parent.parent
RES = {"checks": [], "console_errors": []}
THEMES = ("dark", "light", "leenai", "focus")
OFF = ("<style id='ivsep-off'>.c01-table tbody[data-iv] > tr.c01-ivrow > td{background:var(--ivhead)!important;"
       "box-shadow:none!important;border-top:0!important;padding-left:12px!important}</style>")


def ok(name, cond, detail=""):
    RES["checks"].append({"name": name, "ok": bool(cond), "detail": str(detail)[:300]})
    print(("OK  " if cond else "NG  ") + name + (f" — {detail}" if detail and not cond else ""), flush=True)


def rgb(s):
    m = re.findall(r"[\d.]+", s or "")
    return tuple(int(float(x)) for x in m[:3]) if len(m) >= 3 else None


def lum(c):
    def ch(v):
        v = v / 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * ch(c[0]) + 0.7152 * ch(c[1]) + 0.0722 * ch(c[2])


def contrast(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def blend(fg, bg):
    """rgba 글자 → 바탕 위 실제 색."""
    m = re.findall(r"[\d.]+", fg or "")
    if len(m) == 4:
        a = float(m[3])
        return tuple(int(round(float(m[i]) * a + bg[i] * (1 - a))) for i in range(3))
    return rgb(fg)


PROBE = """() => {
  const wrap = document.querySelector('#jikkyou-wrap');
  let wb = getComputedStyle(wrap).backgroundColor;
  const tb = [...document.querySelectorAll('#jikkyou-table tbody[data-iv]')];
  const cs = getComputedStyle(document.documentElement);
  const v = n => cs.getPropertyValue(n).trim();
  const probe = document.createElement('div'); document.body.appendChild(probe);
  const col = x => { probe.style.color = ''; probe.style.color = x; return getComputedStyle(probe).color; };
  const r = { wrapBg: wb, accent: col(v('--ivsep') || 'red'), strong: col(v('--ivhead-strong')), old: col(v('--ivhead')),
    states: { ok: col(v('--row-ok')), hum: col(v('--row-hum')), check: col(v('--row-check')), wait: col(v('--row-wait')), over: col(v('--row-over')) },
    heads: tb.map((t, i) => { const td = t.querySelector('tr.c01-ivrow > td'), s = getComputedStyle(td), b = td.querySelector('.c01-ivhead .b');
      return { iv: t.getAttribute('data-iv'), bg: s.backgroundColor, bt: s.borderTopWidth, btc: s.borderTopColor, sh: s.boxShadow, txt: getComputedStyle(b).color }; }),
    rows: tb.map(t => [...t.querySelectorAll('tr.c01-row')].map(r => r.className + '/' + (r.getAttribute('data-status') || '') + '/' +
      [...r.children].map(c => getComputedStyle(c).backgroundColor).join(',')).join('|')),
    text: document.querySelector('#jikkyou-table').innerText,
    urgent: [...document.querySelectorAll('.c01-cyurgent')].map(e => e.textContent + '/' + getComputedStyle(e).color),
    filt: [...document.querySelectorAll('.c01-f')].map(e => e.textContent.trim()),
    over: wrap.scrollWidth - wrap.clientWidth };
  probe.remove(); return r; }"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shots")
    a = ap.parse_args()
    if not (TOOL / "fixtures" / "_data" / "jikkyou.json").is_file():
        sys.exit("fixtures/_data 없음 — 먼저 python tools/make_test_data.py")
    shots = Path(a.shots) if a.shots else Path(tempfile.mkdtemp(prefix="c01_r12y74_shots_"))
    shots.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="c01_r12y74_"))
    root = tmp / "fx"
    shutil.copytree(TOOL / "fixtures", root)
    port = TGR.free_port()
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
            ctx = br.new_context(viewport={"width": 1920, "height": 1000})
            page = ctx.new_page()
            page.on("console", lambda m: RES["console_errors"].append(m.text) if m.type == "error" else None)
            page.on("pageerror", lambda e: RES["console_errors"].append(f"pageerror {e}"))
            page.clock.set_fixed_time(dt.datetime(2026, 11, 6, 1, 0, 0, tzinfo=dt.timezone.utc))
            page.goto(f"http://127.0.0.1:{port}/")
            page.wait_for_selector("#c01-open-server", timeout=20000)
            page.click("#c01-open-server")
            page.wait_for_selector("body[data-c01-ready='1']", timeout=20000)
            page.wait_for_timeout(300)
            for th in THEMES:
                page.evaluate("(t) => document.documentElement.setAttribute('data-theme', t)", th)
                page.wait_for_timeout(150)
                on = page.evaluate(PROBE)
                hs = on["heads"]
                acc = rgb(on["accent"])
                ok(f"S1 {th}: IV {len(hs)} 머리줄 배경 = 진한 색 (예전 {on['old']} → {on['strong']})",
                   len(hs) >= 2 and all(h["bg"] == on["strong"] for h in hs) and on["strong"] != on["old"] and lum(rgb(on["strong"])) != lum(rgb(on["old"])), hs[:1])
                ok(f"S1 {th}: 위 2px 선 + 왼쪽 4px 띠 = 강조색",
                   all(rgb(h["sh"]) == acc and "4px 0px 0px 0px inset" in h["sh"] and "0px 2px 0px 0px inset" in h["sh"] for h in hs), hs[0]["sh"])
                crs = [contrast(rgb(h["txt"]), rgb(on["strong"])) for h in hs]
                ok(f"S1 {th}: 머리줄 글자 대비 {min(crs):.1f} ≥ 4.5", min(crs) >= 4.5, crs[:2])
                ok(f"S2 {th}: 첫 IV 위 틈 0 · 그 밖 10px (표 바탕색)",
                   hs[0]["bt"] in ("0px", "1px") and all(h["bt"] == "10px" and h["btc"] == on["wrapBg"] for h in hs[1:]), [(h["bt"], h["btc"]) for h in hs[:3]] + [on["wrapBg"]])
                sb = rgb(on["wrapBg"]) or (255, 255, 255)
                strong = rgb(on["strong"])
                same = {k: v for k, v in on["states"].items() if blend(v, sb) == strong}
                ok(f"S3 {th}: 머리줄 배경 ≠ 줄 상태 색 5", not same, same)
                page.evaluate("(h) => document.head.insertAdjacentHTML('beforeend', h)", OFF)
                off = page.evaluate(PROBE)
                page.evaluate("() => document.getElementById('ivsep-off').remove()")
                ok(f"S4 {th}: 줄 배경 · 글자 · 순서 · 필터 · CY 날짜 색 = 끈 화면과 같음",
                   on["rows"] == off["rows"] and on["text"] == off["text"] and on["filt"] == off["filt"] and on["urgent"] == off["urgent"] and on["urgent"],
                   [on["urgent"], off["urgent"]])
                for w in (1920, 1366):
                    page.set_viewport_size({"width": w, "height": 1000})
                    page.wait_for_timeout(150)
                    o = page.evaluate(PROBE)["over"]
                    ok(f"S5 {th} {w}: 가로 넘침 0", o <= 0, o)
                    page.screenshot(path=str(shots / f"r12y74_ivsep_{th}_{w}.png"))
                page.set_viewport_size({"width": 1920, "height": 1000})
            page.evaluate("() => document.documentElement.setAttribute('data-theme', 'light')")
            page.set_viewport_size({"width": 1100, "height": 900})
            page.wait_for_timeout(150)
            ok("S5 좁은 화면 1100: 가로 넘침 0", page.evaluate(PROBE)["over"] <= 0)
            page.set_viewport_size({"width": 1920, "height": 1000})
            pdf = tmp / "print.pdf"
            page.emulate_media(media="print")
            page.pdf(path=str(pdf))
            page.emulate_media(media="screen")
            ok("S5 인쇄 (PDF) 됨", pdf.is_file() and pdf.stat().st_size > 1000, pdf.stat().st_size if pdf.is_file() else 0)
            page.locator("#jikkyou-table").screenshot(path=str(shots / "r12y74_ivsep_table_light.png"))
            ctx.close()
            br.close()
    finally:
        srv.terminate()
    ok("콘솔 오류 0", not RES["console_errors"], RES["console_errors"][:3])
    print(json.dumps({"ok": sum(c["ok"] for c in RES["checks"]), "ng": sum(not c["ok"] for c in RES["checks"]), "shots": str(shots)}, ensure_ascii=False))
    sys.exit(0 if all(c["ok"] for c in RES["checks"]) else 1)


if __name__ == "__main__":
    main()
