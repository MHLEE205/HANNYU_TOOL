# ✦ Powered by LEENAI Automation System — 試案 (relay\design\*.dc.html) 캡처 + TOOL 같은 크기 캡처 (시안 대조용)
r"""시안 HTML 은 디자인 도구 런타임 (support.js) 이 있어야 열린다 (폴더에 없음). 여기서는 시안 안의 Component 코드 (renderVals) 를
초기 상태 그대로 실행하고 템플릿 (sc-for · sc-if · {{ }}) 만 펼쳐 그린다 — 시안 코드·문구·색은 그대로, 외부 글꼴은 막음 (기본 글꼴).
TOOL 은 가명 fixtures + 라이트 테마 (시안 색과 같은 계열) 로 같은 크기 캡처. 결과: --out 폴더에 *_mockup.png · *_tool.png · *_side.png
사용: python tests/render_mockup.py --design C:\LEENAI_C01_V2\relay\design --out <폴더>"""
import argparse
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
RENDER_JS = r"""
() => {
  class DCLogic { constructor(p) { this.props = p; this.state = {}; } setState(o) { Object.assign(this.state, o); } }
  const code = document.getElementById('dc-code').textContent;
  const Comp = new Function('DCLogic', code + '\n;return Component;')(DCLogic);
  const comp = new Comp({});
  const vals = comp.renderVals();
  const ev = (expr, scope) => { const k = Object.keys(scope); return new Function(...k, 'return (' + expr + ');')(...k.map(x => scope[x])); };
  const sub = (s, scope) => s.replace(/\{\{\s*([\s\S]+?)\s*\}\}/g, (m, e) => { const v = ev(e, scope); return v == null ? '' : String(v); });
  const MAP = {'x-table':'table','x-thead':'thead','x-tbody':'tbody','x-tr':'tr','x-td':'td','x-th':'th'};
  function render(node, scope) {
    if (node.nodeType === 3) return [document.createTextNode(sub(node.textContent, scope))];
    if (node.nodeType !== 1) return [];
    const tag = node.tagName.toLowerCase();
    if (tag === 'sc-for') {
      const m = node.getAttribute('list').match(/\{\{\s*([\s\S]+?)\s*\}\}/);
      const list = ev(m[1], scope) || []; const as = node.getAttribute('as');
      const out = [];
      list.forEach(it => { const s2 = Object.assign({}, scope); s2[as] = it; node.childNodes.forEach(ch => out.push(...render(ch, s2))); });
      return out;
    }
    if (tag === 'sc-if') {
      const m = node.getAttribute('value').match(/\{\{\s*([\s\S]+?)\s*\}\}/);
      if (!ev(m[1], scope)) return [];
      const out = []; node.childNodes.forEach(ch => out.push(...render(ch, scope))); return out;
    }
    const el = document.createElement(MAP[tag] || tag);
    for (const a of node.attributes) {
      if (/^on/i.test(a.name) || a.name.startsWith('hint-')) continue;
      if (/\{\{/.test(a.value)) {
        const only = a.value.match(/^\{\{\s*([\s\S]+?)\s*\}\}$/);
        if (only) { const v = ev(only[1], scope); if (v === false || v == null) continue; if (v === true) { el.setAttribute(a.name, ''); continue; } el.setAttribute(a.name, String(v)); continue; }
        el.setAttribute(a.name, sub(a.value, scope));
      } else el.setAttribute(a.name, a.value);
    }
    node.childNodes.forEach(ch => render(ch, scope).forEach(x => el.appendChild(x)));
    return [el];
  }
  const tpl = document.getElementById('dc-tpl').content;
  const host = document.getElementById('dc-host');
  tpl.childNodes.forEach(ch => {
    if (ch.nodeType === 1 && ch.tagName.toLowerCase() === 'helmet') { ch.childNodes.forEach(h => { if (h.nodeType === 1) document.head.appendChild(h.cloneNode(true)); }); return; }
    render(ch, vals).forEach(x => host.appendChild(x));
  });
  return true;
}
"""


def mockup_html(src):
    s = src.read_text(encoding="utf-8")
    body = s.split("<x-dc>")[1].split("</x-dc>")[0]
    code = re.search(r'<script type="text/x-dc"[^>]*>([\s\S]*?)</script>', s).group(1)
    for a, b in (("<thead", "<x-thead"), ("</thead", "</x-thead"), ("<tbody", "<x-tbody"), ("</tbody", "</x-tbody"), ("<table", "<x-table"),
                 ("</table", "</x-table"), ("</tr", "</x-tr"), ("</td", "</x-td"), ("</th>", "</x-th>")):
        body = body.replace(a, b)
    body = re.sub(r"<tr(\s|>)", r"<x-tr\1", body)
    body = re.sub(r"<td(\s|>)", r"<x-td\1", body)
    body = re.sub(r"<th(\s|>)", r"<x-th\1", body)
    return ("<!doctype html><html lang='ja'><head><meta charset='utf-8'></head><body><div id='dc-host'></div>"
            f"<template id='dc-tpl'>{body}</template><script type='text/plain' id='dc-code'>{code}</script></body></html>")


def side_by_side(a, b, out):
    try:
        from PIL import Image
    except ImportError:
        return False
    ia, ib = Image.open(a), Image.open(b)
    h = max(ia.height, ib.height)
    im = Image.new("RGB", (ia.width + ib.width + 20, h), (255, 255, 255))
    im.paste(ia, (0, 0))
    im.paste(ib, (ia.width + 20, 0))
    im.save(out)
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--design", default=r"C:\LEENAI_C01_V2\relay\design")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    pairs = [("jikkyou", "시안_実況表_Main.dc.html", 1440, 1180), ("input", "시안_確認入力_Input.dc.html", 1440, 960)]
    tmp = Path(tempfile.mkdtemp(prefix="c01mock_"))
    root = tmp / "data"
    shutil.copytree(TOOL / "fixtures", root)
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    srv = subprocess.Popen([sys.executable, str(TOOL / "tools" / "serve_local.py"), "--root", str(root), "--port", str(port), "--today", "2026-11-08"],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    time.sleep(1.0)
    try:
        with sync_playwright() as p:
            br = p.chromium.launch()
            for name, fn, w, h in pairs:
                pg = br.new_context(viewport={"width": w, "height": h}).new_page()
                pg.route("**/*", lambda r: r.abort() if r.request.url.startswith("http") else r.continue_())
                pg.set_content(mockup_html(Path(a.design) / fn))
                pg.evaluate(RENDER_JS)
                pg.wait_for_timeout(300)
                pg.screenshot(path=str(out / f"{name}_mockup.png"))
                pg.close()
                tp = br.new_context(viewport={"width": w, "height": h}).new_page()
                tp.goto(f"http://127.0.0.1:{port}/")
                tp.evaluate("localStorage.setItem('leenai_theme','light'); localStorage.setItem('c01_local_me','STAFF_A')")
                tp.goto(f"http://127.0.0.1:{port}/")
                tp.wait_for_selector("#c01-open-server", timeout=20000)
                tp.click("#c01-open-server")
                tp.wait_for_selector("body[data-c01-ready='1']", timeout=20000)
                if name == "input":
                    tp.click("#tab-input")
                    tp.wait_for_timeout(300)
                tp.screenshot(path=str(out / f"{name}_tool.png"))
                tp.close()
                side_by_side(out / f"{name}_mockup.png", out / f"{name}_tool.png", out / f"{name}_side.png")
            br.close()
    finally:
        srv.terminate()
        shutil.rmtree(tmp, ignore_errors=True)
    print("ok", sorted(x.name for x in out.glob("*.png")))


if __name__ == "__main__":
    main()
