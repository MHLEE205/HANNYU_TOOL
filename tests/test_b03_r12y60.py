# ✦ Powered by LEENAI Automation System — v0.3.85 (R12Y60 · #405) ① 新規通関依頼 = B-03 P/O 発注ツール の件名 · 本文 I/V NO — js/source.js
"""node (Playwright driver) 로 js/source.js 를 읽어 (가명 값만 · 실제 메일 0):
 1. b03 · b03Orig · ivLine · isS1Subject = 표 (CASES) 그대로 · 엔진 customs_s1 (있으면) 과 같은 답
 2. customsFindS1 (가짜 _mailGet): B-03 원본 우선 ([P/O送付] Re: 는 원본 아님) · BKG 없음 → IV 로 찾아 본문 「I/V NO」 · how
사용: python tests/test_b03_r12y60.py"""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_customs as TC  # noqa: E402

TOOL = Path(__file__).resolve().parent.parent
NODE = Path(r"C:\Program Files\Python313\Lib\site-packages\playwright\driver\node.exe")
ENG = TOOL.parent / "engine"
BKG = "TSTB123456"
IVN = "TST2611-07"
# (subject, b03, b03_orig, is_s1)
CASES = [
    (f"新規通関依頼:BKG#{BKG}, CUT12/03 (OSAKA TO TEST, JOMG)", True, True, True),
    (f"新規通関依頼: BKG#{BKG}、CUT 12/3 (TOKYO TO TEST)", True, True, True),
    (f"新規通関+ドレージ申請:BKG#{BKG}, CUT12/03 (OSAKA TO TEST, JKGB)", True, True, True),
    (f"新規輸出通関依頼（BKG#{BKG}, CUT 12/3）", True, True, True),
    (f"新規輸出通関+ドレージ申請（BKG#{BKG}, CUT 12/3）", True, True, True),
    (f"新規通関依頼(通関のみ):BKG#{BKG}, CUT12/03 (OSAKA TO TEST, JKGB)", True, True, True),
    (f"新規通関のご依頼:BKG#{BKG}, CUT12/3 (NAHA TO TEST, JOCC)", True, True, True),
    (f"[P/O送付] Re: 新規通関+ドレージ申請:BKG#{BKG}, CUT12/03 (OSAKA TO TEST, JKGB)", True, False, True),
    (f"「追加1本」　RE: 新規通関依頼:BKG#{BKG}, CUT12/03 (OSAKA TO TEST, JOMG)", True, False, True),
    (f"RE: 新規通関依頼:BKG#{BKG}, CUT12/03", True, False, True),
    (f"【通関書類送付_{IVN}】Re: 新規通関依頼:BKG#{BKG}, CUT12/03", True, False, False),
    (f"新規通関依頼:BKG#{BKG}9, CUT12/03", False, False, True),
    (f"新規通関依頼:BKG#OTHER99999, CUT12/03", False, False, True),
    (f"ドレージ依頼:BKG#{BKG}, CUT12/4 (OSAKA TO TEST, OCC)", False, False, False),
    (f"ブッキング情報のご案内と搬入表ご送付の件(BKG#{BKG}, CUT 11/30)", False, False, False),
    (f"【新規ドレージ、通関依頼】　BKG NO.{BKG} CUT 12/3", False, False, True),
]
# (text, iv, hit)
IVCASES = [
    ("テスト乙仲\n担当者様\n\nBKG NO.    X\nI/V NO     " + IVN + "\n船名", IVN, True),
    ("BOOKING NO.  : X\nI/V NO       : " + IVN + "\n", IVN, True),
    ("I/V NO      " + IVN + "-2\n", IVN, False),
    ("I/V NO      " + IVN + "1\n", IVN, False),
    ("IV " + IVN, IVN, False),
]
RES = {"checks": []}


def ok(name, cond, detail=""):
    RES["checks"].append({"name": name, "ok": bool(cond)})
    print(("OK  " if cond else "NG  ") + name + (f" — {detail}" if detail and not cond else ""), flush=True)


JS = r"""
const fs = require('fs'), vm = require('vm');
const ctx = { window: {}, console: console, Promise: Promise, encodeURIComponent: encodeURIComponent, fetch: () => Promise.reject(new Error('no fetch')) };
ctx.window = ctx; vm.createContext(ctx);
vm.runInContext(fs.readFileSync(process.argv[2], 'utf8'), ctx);
const G = ctx.C01.sources.Graph, B = G.prototype._b03;
const inp = JSON.parse(fs.readFileSync(0, 'utf8'));
const out = { cases: inp.cases.map(c => [B.b03(c[0], inp.bkg), B.b03Orig(c[0], inp.bkg), B.isS1Subject(c[0])]), iv: inp.ivcases.map(c => B.ivLine(c[0], c[1])), find: [] };
const ours = inp.ours;
function mk(id, subj, at, conv, prev) { return { id: id, subject: subj, conversationId: conv, sentDateTime: at, isDraft: false,
  from: { emailAddress: { address: 'me@' + ours, name: 'ME' } }, toRecipients: [{ emailAddress: { address: 'b@broker.invalid', name: 'B' } }], ccRecipients: [], bodyPreview: prev || '' }; }
async function run(name, search, convs, bkg, iv) {
  const g = new G(); g.urls = {};
  const calls = [];
  g._mailGet = function (p) { calls.push(p); if (p.indexOf('$search') >= 0) { const q = decodeURIComponent(p.split('$search=')[1].split('&')[0]); return Promise.resolve({ value: search[q] || [] }); }
    const cid = decodeURIComponent(p).match(/conversationId eq '([^']+)'/)[1]; return Promise.resolve({ value: convs[cid] || [] }); };
  ctx.C01.CUSTOMS = { ourDomain: ours };
  const r = await g.customsFindS1(bkg, iv);
  out.find.push({ name: name, s1: r && r.s1.id, last: r && r.last.id, how: r && r.how, n_search: calls.filter(c => c.indexOf('$search') >= 0).length });
}
(async () => {
  const b = inp.bkg, iv = inp.ivn;
  const orig = mk('O1', '新規通関+ドレージ申請:BKG#' + b + ', CUT12/03 (OSAKA TO TEST, JKGB)', '2026-11-18T01:34:00Z', 'C1');
  const po = mk('P1', '[P/O送付] Re: 新規通関+ドレージ申請:BKG#' + b + ', CUT12/03 (OSAKA TO TEST, JKGB)', '2026-11-18T07:47:00Z', 'C1');
  await run('b03_first', { ['"' + b + '"']: [po, orig] }, { C1: [orig, po] }, b, iv);
  const old = mk('H1', '【新規ドレージ、通関依頼】　BKG NO.' + b + ' CUT 12/3', '2026-11-18T01:00:00Z', 'C2');
  await run('old_only', { ['"' + b + '"']: [old] }, { C2: [old] }, b, iv);
  const ivm = mk('V1', '新規通関依頼:BKG#OTHER12345, CUT12/03 (TOKYO TO TEST)', '2026-11-10T01:00:00Z', 'C3', 'テスト\n担当者様\n\nBKG NO.    OTHER12345\nI/V NO     ' + iv + '\n');
  const ivx = mk('V2', '新規通関依頼:BKG#OTHER12346, CUT12/03 (TOKYO TO TEST)', '2026-11-11T01:00:00Z', 'C4', 'I/V NO     ' + iv + '-2\n');
  await run('iv_body', { ['"' + iv + '"']: [ivx, ivm] }, { C3: [ivm] }, b, iv);
  await run('none', {}, {}, b, iv);
  process.stdout.write(JSON.stringify(out));
})();
"""


def main():
    js = TOOL / "tests" / "_b03_run.js"
    js.write_text(JS, encoding="utf-8")
    try:
        p = subprocess.run([str(NODE), str(js), str(TOOL / "js" / "source.js")], input=json.dumps({"cases": CASES, "ivcases": IVCASES, "bkg": BKG, "ivn": IVN, "ours": TC.OURS}),
                           capture_output=True, text=True, encoding="utf-8", timeout=60)
    finally:
        js.unlink()
    if p.returncode != 0:
        ok("node 실행", False, p.stderr[:500])
        return
    out = json.loads(p.stdout)
    for c, got in zip(CASES, out["cases"]):
        ok(f"표 {c[0][:40]} → b03 {c[1]} · 원본 {c[2]} · ① {c[3]}", got == [c[1], c[2], c[3]], got)
    for c, got in zip(IVCASES, out["iv"]):
        ok(f"I/V NO {c[0][:30]!r} → {c[2]}", got == c[2], got)
    f = {x["name"]: x for x in out["find"]}
    ok("find B-03 원본 우선 ([P/O送付] Re: 가 더 새것이어도 원본 = O1) · 대화 최신 = P1 · how b03", f["b03_first"]["s1"] == "O1" and f["b03_first"]["last"] == "P1" and f["b03_first"]["how"] == "b03"
       and f["b03_first"]["n_search"] == 1, f["b03_first"])
    ok("find 옛 꼴 (손으로 쓴 ①) = 그대로 찾음 · how old", f["old_only"]["s1"] == "H1" and f["old_only"]["how"] == "old", f["old_only"])
    ok("find 제목에 BKG 없음 → IV 로 검색 · 본문 「I/V NO {IV}」 정확 (-2 는 아님) · how iv_body", f["iv_body"]["s1"] == "V1" and f["iv_body"]["how"] == "iv_body" and f["iv_body"]["n_search"] == 2, f["iv_body"])
    ok("find 없음 = null (검색 2 번)", f["none"]["s1"] is None and f["none"]["n_search"] == 2, f["none"])
    if (ENG / "engine" / "output" / "customs_s1.py").exists():
        sys.path.insert(0, str(ENG))
        from engine.output import customs_s1 as S1
        eng = [[S1.b03(c[0], BKG), S1.b03_orig(c[0], BKG), S1.kind(c[0]) == "①"] for c in CASES]
        ok("엔진 customs_s1 (b03 · b03_orig · kind) = TOOL 과 같은 답", eng == out["cases"], [i for i, (a, b) in enumerate(zip(eng, out["cases"])) if a != b])
        ok("엔진 iv_line = TOOL ivLine", [S1.iv_line(c[0], c[1]) for c in IVCASES] == out["iv"])
    else:
        print("(엔진 레포 없음 — 엔진 대조 건너뜀)")


if __name__ == "__main__":
    main()
    ng = [c for c in RES["checks"] if not c["ok"]]
    print(f"== {len(RES['checks']) - len(ng)}/{len(RES['checks'])} OK")
    sys.exit(1 if ng else 0)
