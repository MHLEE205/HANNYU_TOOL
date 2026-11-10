# ✦ Powered by LEENAI Automation System — C-01 搬入票 TOOL R6M13 「写真不足」 確認経路 画面試験 (Playwright · 가명 fixtures)
"""fixtures 사본에 사유 29 (PHOTO_SET_INCOMPLETE) 再確認 줄 2개 + 엔진 queue 항목 「写真不足」 2개 (out_queue_photo_set 켬과 같은 모양) 를 넣고 확인:
옆 창 문장 (엔진 reason_text 그대로) · 「確認する」 켜짐 → confirm_value (칸 ct · 값 그대로 · 写真 · queue_id) · 줄 確認済 ·
確認・入力 칩 「写真不足 1」 · 「確認して次へ」 → 두 번째 action · _actions = 엔진 action.schema.json · 4테마 캡처 · 콘솔 오류 0 · 네트워크 = 로컬 · LEENAI_COMMON.
사용: python tests/test_photoset.py [--shots 폴더] [--engine C:\\LEENAI_C01_V2\\engine_r625]"""
import argparse
import hashlib
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
RT = "通関用写真が不足しています（{없는 종류}）"


def ok(name, cond, detail=""):
    RES["checks"].append({"name": name, "ok": bool(cond), "detail": str(detail)[:300]})
    print(("OK  " if cond else "NG  ") + name + (f" — {detail}" if detail and not cond else ""), flush=True)


def actions(root):
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted((root / "_actions").rglob("*.json")) if "_rejected" not in p.parts]


def prepare(root):
    """自動OK 줄 2개 → 再確認 + 사유 29 · queue 「写真不足」 항목 (엔진 data_json 과 같은 열쇠)."""
    jp, qp = root / "_data" / "jikkyou.json", root / "_data" / "queue.json"
    jj, qq = json.loads(jp.read_text(encoding="utf-8")), json.loads(qp.read_text(encoding="utf-8"))
    picked = []
    for iv in jj["ivs"]:
        for r in iv["rows"]:
            if len(picked) < 2 and r["status"] == "自動OK" and r.get("ct") and r.get("photos"):
                miss = "扉閉め" if not picked else "一部積込"
                r.update(status="再確認", engine_status="再確認", reasons=["PHOTO_SET_INCOMPLETE"], reason_text=[RT], photo_missing=miss)
                picked.append((iv, r, miss))
    pj = {}
    for iv, r, miss in picked:
        ph = pj.setdefault(iv["iv_no"], json.loads((root / "_data" / "photos" / f"{iv['iv_no']}.json").read_text(encoding="utf-8")))
        c = [x for x in ph["containers"] if x["container_id"] == r["container_id"]][0]
        files = [{"path": p["path"], "name": p["path"].split("/")[-1], "page": None, "bbox": None, "sha16": p["sha16"]} for p in c["photos"][:6]]
        qid = hashlib.sha256(("写真不足|" + r["container_id"] + "||" + ",".join(sorted(f["sha16"] for f in files))).encode()).hexdigest()[:16]
        qq["items"].append({"queue_id": qid, "kind": "写真不足", "iv_no": iv["iv_no"], "ct": r["ct"], "field": None, "container_id": r["container_id"],
                            "values": {}, "candidates": [], "files": files, "note": "PHOTO_SET_INCOMPLETE", "field_sources": {}, "field_source_text": {},
                            "cy_cut": iv.get("cy_cut"), "cy_open": iv.get("cy_open"), "issuer": None, "resolved": None, "superseded": [],
                            "missing": ["closed" if miss == "扉閉め" else "partial"], "reason_text": RT.replace("{없는 종류}", miss)})
    qq["kinds"] = list(qq["kinds"]) + ["写真不足"]
    qq["count"]["写真不足"] = len(picked)
    qq["open"] = qq.get("open", 0) + len(picked)
    jp.write_text(json.dumps(jj, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    qp.write_text(json.dumps(qq, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return [(iv["iv_no"], r["ct"], miss) for iv, r, miss in picked], [q for q in qq["items"] if q["kind"] == "写真不足"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shots", default=str(TOOL / "tests" / "_shots" / "photoset"))
    ap.add_argument("--engine", default=r"C:\LEENAI_C01_V2\engine_r625")
    a = ap.parse_args()
    shots = Path(a.shots)
    shots.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="c01_photoset_"))
    root = tmp / "site"
    shutil.copytree(TOOL / "fixtures", root)
    rows, qs = prepare(root)
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    srv = subprocess.Popen([sys.executable, str(TOOL / "tools" / "serve_local.py"), "--root", str(root), "--port", str(port), "--today", "2026-11-08"],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:
        for _ in range(50):
            try:
                socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
                break
            except OSError:
                time.sleep(0.1)
        url = f"http://127.0.0.1:{port}/"
        with sync_playwright() as p:
            br = p.chromium.launch()
            page = br.new_context(viewport={"width": 1440, "height": 1000}).new_page()
            page.on("console", lambda m: RES["console_errors"].append(m.text) if m.type == "error" else None)
            page.on("pageerror", lambda e: RES["console_errors"].append(f"pageerror {e}"))
            page.on("request", lambda r: RES["external_requests"].append(r.url) if not r.url.startswith(ALLOWED) else None)
            page.goto(url)
            page.wait_for_selector("#c01-open-server", timeout=20000)
            page.click("#c01-open-server")
            page.wait_for_selector("body[data-c01-ready='1']", timeout=20000)
            page.select_option("#me-select", "STAFF_A")
            page.wait_for_timeout(200)
            iv1, ct1, miss1 = rows[0]
            body = page.locator("#jikkyou-table").inner_text()
            ok("再確認 짧은 표시 「写真不足（扉閉め）」", f"写真不足（{miss1}）" in body)
            page.locator(f"tr.c01-row[data-key*='{ct1}'] .c01-checkbtn").first.click()
            page.wait_for_selector(".c01-side", timeout=5000)
            side = page.locator(".c01-side").inner_text()
            ok("옆 창 문장 = 엔진 사유 문장", f"通関用写真が不足しています（{miss1}）" in side, side[:120])
            ok("옆 창 「ここで確認できる項目はありません」 안 나옴", "ここで確認できる項目はありません" not in side)
            btn = page.locator("#panel-ok")
            ok("「確認する」 켜짐", btn.is_enabled() and btn.inner_text().strip() == "確認する", btn.inner_text())
            ok("사진 보기 단추 있음", page.locator("#panel-photo").is_enabled())
            page.screenshot(path=str(shots / "side_photoset.png"))
            btn.click()
            page.wait_for_selector(f"tr.c01-row[data-key*='{ct1}'][data-status='確認済']", timeout=3000)
            ok("줄 再確認 → 確認済 (본인 화면)", True)
            for _ in range(30):
                if actions(root):
                    break
                time.sleep(0.1)
            acts = actions(root)
            a1 = acts[0] if acts else {}
            ok("_actions 1 = confirm_value · 칸 ct · 값 그대로 · 写真 · queue_id",
               len(acts) == 1 and a1.get("action") == "confirm_value" and a1.get("field") == "ct" and a1.get("value") == ct1 and a1.get("source") == "写真"
               and a1.get("queue_id") == qs[0]["queue_id"] and a1.get("iv") == iv1, a1)
            # 確認・入力 화면
            page.click("#nav-input") if page.locator("#nav-input").count() else page.locator("button", has_text="確認・入力").first.click()
            page.wait_for_selector(".c01-kinds", timeout=5000)
            chips = page.eval_on_selector_all(".c01-kinds .c01-chip", "els => els.map(e => e.textContent.trim())")
            ok("確認・入力 칩 「写真不足」 (엔진 kinds 에 있을 때)", any(c.startswith("写真不足") for c in chips), chips)
            page.click(".c01-kinds [data-kind='写真不足']")
            page.wait_for_selector("#q-submit", timeout=3000)
            note = page.locator(".c01-qnote").inner_text()
            iv2, ct2, miss2 = rows[1]
            ok("確認・入力 안내 = 엔진 사유 문장", f"通関用写真が不足しています（{miss2}）" in note, note)
            ok("確認・入力 사진 표시 (사진 격자)", page.locator(".c01-grid .c01-gph").count() > 0)
            sb = page.locator("#q-submit")
            ok("「確認して次へ」 켜짐", sb.is_enabled() and "確認して次へ" in sb.inner_text(), sb.inner_text())
            page.screenshot(path=str(shots / "input_photoset.png"))
            sb.click()
            for _ in range(30):
                if len(actions(root)) >= 2:
                    break
                time.sleep(0.1)
            acts = actions(root)
            a2 = [x for x in acts if x.get("queue_id") == qs[1]["queue_id"]]
            ok("두 번째 action = confirm_value · ct · 값 그대로", len(acts) == 2 and a2 and a2[0]["field"] == "ct" and a2[0]["value"] == ct2, acts[-1] if acts else None)
            sys.path.insert(0, a.engine)
            from engine.output import schema_check  # noqa: E402
            sch = schema_check.load("action")
            errs = {x["action_id"]: schema_check.errors(x, sch) for x in acts}
            ok("_actions JSON = 엔진 action.schema.json (오류 0)", all(not e for e in errs.values()), {k: v for k, v in errs.items() if v})
            for th in ("dark", "light", "leenai", "focus"):
                page.evaluate(f"localStorage.setItem('leenai_theme','{th}'); document.documentElement.setAttribute('data-theme','{th}')")
                page.wait_for_timeout(300)
                page.screenshot(path=str(shots / f"input_{th}.png"))
            ok("4 테마 캡처", all((shots / f"input_{t}.png").exists() for t in ("dark", "light", "leenai", "focus")))
            ok("콘솔 오류 0", not RES["console_errors"], RES["console_errors"][:3])
            ok("네트워크 = LEENAI_COMMON · 127.0.0.1 만", not RES["external_requests"], RES["external_requests"][:3])
            br.close()
    finally:
        srv.terminate()
    n = sum(1 for c in RES["checks"] if c["ok"])
    print(f"== {n}/{len(RES['checks'])} OK")
    (shots / "result.json").write_text(json.dumps(RES, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0 if n == len(RES["checks"]) else 1


if __name__ == "__main__":
    sys.exit(main())
