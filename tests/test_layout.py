# ✦ Powered by LEENAI Automation System — C-01 搬入票 TOOL 実況表 「한 화면」 시험 (R7B · Playwright · 가명 fixtures)
"""fixtures 를 임시 폴더로 복사 → 줄을 늘리고 (IV 복제) 긴 이름 (品目 · 圧縮業者 · Plant) 을 넣음 → serve_local.py → 세 폭에서 확인.
확인 (1366×768 · 1600×900 · 1920×1080): 가로 스크롤 0 (표 상자 · 페이지) · 상자 아래 끝 ≤ 창 높이 (범례 포함) · 머리글 고정 (상자 안 스크롤 뒤) ·
      칸 순서·이름 그대로 · 글자 13px (줄이지 않음) · 긴 칸 = 2줄 + title 전체 · 콘솔 오류 0.
사용: python tests/test_layout.py [--shots 폴더]"""
import argparse
import copy
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
RES = {"checks": [], "console_errors": []}
COLS = ["No", "CYカット", "Invoice番号", "品目", "CT番号", "シール番号", "正味重量", "風袋重量", "ベール数", "作業日", "条件", "圧縮業者", "Plant", "写真", "状況"]
SIZES = [(1366, 768), (1600, 900), (1920, 1080)]
LONG_PLANT = "テスト第二工場（長い名前の確認用）テスト第二工場"
LONG_PACKER = "テスト圧縮業者株式会社（長い名前）"
LONG_ITEM = "TEST GRADE 長い品目名 OCC MIXED"


def ok(name, cond, detail=""):
    RES["checks"].append({"name": name, "ok": bool(cond), "detail": str(detail)[:300]})
    print(("OK  " if cond else "NG  ") + name + (f" — {detail}" if detail and not cond else ""), flush=True)


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shots", default=str(TOOL / "tests" / "_shots"))
    a = ap.parse_args()
    if not (TOOL / "fixtures" / "_data" / "jikkyou.json").is_file():
        sys.exit("fixtures/_data 없음 — 먼저 python tools/make_test_data.py")
    shots = Path(a.shots)
    shots.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="c01layout_"))
    root = tmp / "data"
    shutil.copytree(TOOL / "fixtures", root)
    jp = root / "_data" / "jikkyou.json"
    jj = json.loads(jp.read_text(encoding="utf-8"))
    base = jj["ivs"]
    more = []
    for k in range(1, 4):                       # 줄 늘리기 (창보다 길게) — 가명 IV 번호에 -Xk 를 붙임
        for iv in base:
            c = copy.deepcopy(iv)
            c["iv_no"] = iv["iv_no"] + f"-X{k}"
            more.append(c)
    jj["ivs"] = base + more
    first = jj["ivs"][0]
    first["plant"] = LONG_PLANT
    first["packer"] = LONG_PACKER
    first["item"] = LONG_ITEM
    for r in first["rows"]:
        r["plant"] = LONG_PLANT
        r["packer"] = LONG_PACKER
        r["item"] = LONG_ITEM
    for sl in first["slots"]:                 # v0.3.7: 칸 배정 줄 = 배정 칸의 값 (긴 이름 시험은 칸에도)
        sl["plant"] = LONG_PLANT
        sl["item"] = LONG_ITEM
    # v0.3.7 (R7D Part U-1): 営業所 다른 칸 2개 IV — 칸 배정 줄 = 그 칸 plant 1개 (「・」 없음) · 미배정 줄 = 「—」 + 마우스 후보
    two = next(iv for iv in jj["ivs"] if iv["iv_no"] == "TST2611-02")
    for i, sl in enumerate(two["slots"]):
        sl["plant"] = "テスト一工場" if i % 2 == 0 else "テスト二工場"
    two["plant"] = "テスト一工場・テスト二工場"
    for r in two["rows"]:
        r["plant"] = None
    two["rows"][0]["info"] = ["AI_GROUP_DIFF"]          # v0.3.8 (R7D Part A): 구조 우선 묶음 줄 = 「AI区分」 정보
    jp.write_text(json.dumps(jj, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    port = free_port()
    srv = subprocess.Popen([sys.executable, str(TOOL / "tools" / "serve_local.py"), "--root", str(root), "--port", str(port), "--today", "2026-11-08"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(50):
            try:
                socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
                break
            except OSError:
                time.sleep(0.1)
        with sync_playwright() as p:
            br = p.chromium.launch()
            for w, h in SIZES:
                page = br.new_context(viewport={"width": w, "height": h}).new_page()
                page.on("console", lambda m: RES["console_errors"].append(m.text) if m.type == "error" else None)
                page.on("pageerror", lambda e: RES["console_errors"].append(f"pageerror {e}"))
                page.goto(f"http://127.0.0.1:{port}/")
                page.wait_for_selector("#c01-open-server", timeout=20000)
                page.click("#c01-open-server")
                page.wait_for_selector("body[data-c01-ready='1']", timeout=20000)
                page.wait_for_timeout(300)
                m = page.evaluate("""() => {
                  const w = document.getElementById('jikkyou-wrap'), lg = w.nextElementSibling, de = document.documentElement;
                  const td = document.querySelector('#jikkyou-table tbody tr.c01-row td:nth-child(5)');
                  return { wsw: w.scrollWidth, wcw: w.clientWidth, dsw: de.scrollWidth, iw: window.innerWidth, ih: window.innerHeight,
                           wb: w.getBoundingClientRect().bottom, lb: lg.getBoundingClientRect().bottom, wsh: w.scrollHeight, wch: w.clientHeight,
                           cols: [...document.querySelectorAll('#jikkyou-table thead th')].map(t => t.textContent.trim()),
                           fs: getComputedStyle(td).fontSize, dsh: de.scrollHeight };
                }""")
                tag = f"{w}×{h}"
                ok(f"{tag} 가로 스크롤 0 (표 상자)", m["wsw"] <= m["wcw"], m)
                ok(f"{tag} 가로 스크롤 0 (페이지)", m["dsw"] <= m["iw"], m)
                ok(f"{tag} 상자 아래 끝 ≤ 창 높이 (범례 포함)", m["wb"] <= m["ih"] and m["lb"] <= m["ih"], m)
                ok(f"{tag} 페이지 세로 스크롤 0 (상자 안에서만)", m["dsh"] <= m["ih"] + 1, m)
                ok(f"{tag} 줄이 창보다 많음 = 상자 안 스크롤", m["wsh"] > m["wch"], m)
                ok(f"{tag} 칸 순서·이름 그대로 (15)", m["cols"] == COLS, m["cols"])
                ok(f"{tag} 글자 13px (줄이지 않음)", m["fs"] == "13px", m["fs"])
                page.screenshot(path=str(shots / f"r7b_jikkyou_{w}.png"))
                page.evaluate("document.getElementById('jikkyou-wrap').scrollTop = 600")
                page.wait_for_timeout(100)
                st = page.evaluate("""() => { const w = document.getElementById('jikkyou-wrap'), th = w.querySelector('thead th');
                  return [Math.round(th.getBoundingClientRect().top - w.getBoundingClientRect().top), w.scrollTop]; }""")
                ok(f"{tag} 머리글 고정 (상자 안 스크롤 뒤 맨 위)", st[1] > 0 and abs(st[0]) <= 2, st)
                lc = page.evaluate("""(v) => { const s = [...document.querySelectorAll('.c01-clamp')].filter(x => x.textContent === v)[0];
                  if (!s) return null; const lh = parseFloat(getComputedStyle(s).lineHeight); return { t: s.title, h: s.getBoundingClientRect().height, lh }; }""", LONG_PLANT)
                ok(f"{tag} 긴 Plant = 2줄 이하 + title 전체", lc and lc["t"] == LONG_PLANT and lc["h"] <= lc["lh"] * 2 + 1, lc)
                if w == 1366:
                    pl = page.evaluate("""() => [...document.querySelectorAll("tbody[data-iv='TST2611-02'] tr.c01-row")].map(tr => {
                      const td = tr.children[12]; return { slot: tr.classList.contains('missing') ? 'm' : '', t: td.textContent, title: (td.querySelector('[title]') || td).title }; })""")
                    slots2 = [(r.get("slot_guid") or "") for r in next(iv for iv in jj["ivs"] if iv["iv_no"] == "TST2611-02")["rows"]]
                    slots2 = [g for g in slots2 if g] + [g for g in slots2 if not g]      # v0.3.9: 칸 배정 줄 (seq 순) 다음 未割当 줄
                    real = [x for x in pl if x["slot"] != "m"]
                    ok("U-1 칸 배정 줄 Plant 에 「・」 0 (배정 칸 1개)", all("・" not in x["t"] for x in real) and
                       [x["t"] for x, g in zip(real, slots2) if g] == ["テスト一工場", "テスト二工場"], pl)
                    dots = page.evaluate("""() => [...document.querySelectorAll("#jikkyou-table tr.c01-row:not(.missing):not(.unassigned)")].map(tr =>
                      [3, 10, 11, 12].map(i => tr.children[i].textContent))""")
                    ok("D-42 칸 배정 줄 品目 · 条件 · 圧縮業者 · Plant 에 「・」 0", len(dots) > 0 and all("・" not in t for row in dots for t in row), dots[:3])
                    ai = page.evaluate("""() => [...document.querySelectorAll("tbody[data-iv='TST2611-02'] [data-info='AI_GROUP_DIFF']")].map(e => e.title)""")
                    ok("R7D A: AI 区分が異なる 정보 = 그 줄 1개 (title 설명)", len(ai) == 1 and "AI 区分が異なる" in ai[0], ai)
                    ok("U-1 미배정 줄 = 「—」 · 마우스 = 후보", all(x["t"] == "—" for x, g in zip(real, slots2) if not g) and any(not g for g in slots2) and
                       all(x["title"] == "枠が未定 · 候補: テスト一工場 / テスト二工場" for x, g in zip(real, slots2) if not g), pl)   # v0.3.24 R7X C: 「枠が未定」
                page.context.close()
            br.close()
    finally:
        srv.terminate()
        shutil.rmtree(tmp, ignore_errors=True)
    errs = [e for e in RES["console_errors"] if not ("Failed to load resource" in e and "404" in e)]   # 복제 IV 의 compass_now 등 (선택 파일)
    ok("콘솔 오류 0 (복제 IV 의 선택 파일 404 제외)", not errs, errs[:5])
    n_ng = sum(1 for c in RES["checks"] if not c["ok"])
    (shots / "layout_result.json").write_text(json.dumps(RES, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"== {len(RES['checks']) - n_ng}/{len(RES['checks'])} OK")
    return 1 if n_ng else 0


if __name__ == "__main__":
    sys.exit(main())
