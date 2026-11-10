# ✦ Powered by LEENAI Automation System — v0.2.2 (R6.8 · 결정 #109 · #112) Python ↔ JS 같은 규칙 시험
r"""TOOL (js/config.js · js/validate.js · js/app.js) 과 엔진 (engine/actions/apply.py · engine/notify/remind.py) 이 같은 규칙인지 확인한다.
- ① 설정: C01.RULES slotChange ↔ ACTION_RULES["slot_change"] · ctCheckDigitWrong 'warn' ↔ ct_checkdigit_override · humanVsEngine 'keep_info'
- ② CT 입력: 같은 입력 (가명) 을 JS validate.field('ct') 와 엔진 norm_value('ct', v, override) 에 넣어 받음/거부·값·override 가 같은지
- ③ 문구: 체크디짓 확인창 · 催促 서명 자리표시자 · 슬롯 입れ替え 확인창 형식
node = Playwright 에 들어 있는 node.exe (따로 설치 없음). 데이터 없음 (가명 CT 만).
사용: python tests/rules_cross.py [--engine C:\LEENAI_C01_V2\engine_r68]"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

TOOL = Path(__file__).resolve().parent.parent
CASES = ["TSTU0000015", "tstu 000001-5", "TSTU0000014", "TSTU0000010", "TSTU000001", "TST10000015", "", "  TSTU0000016  "]


def node_exe():
    import playwright
    return str(Path(playwright.__file__).parent / "driver" / "node.exe")


JS = r"""
global.window = global; global.C01 = {};
const fs = require('fs');
eval(fs.readFileSync(process.argv[1] + '/js/config.js', 'utf8'));
eval(fs.readFileSync(process.argv[1] + '/js/validate.js', 'utf8'));
const cases = JSON.parse(process.argv[2]);
const out = { rules: C01.RULES, msg: C01.validate.CHECKDIGIT_MSG, ct: cases.map(c => C01.validate.field('ct', c)) };
process.stdout.write(JSON.stringify(out));
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", default=r"C:\LEENAI_C01_V2\engine_r68")
    a = ap.parse_args()
    sys.path.insert(0, a.engine)
    from engine.actions import apply as AP  # noqa: E402
    from engine.notify import remind as R  # noqa: E402
    js = json.loads(subprocess.run([node_exe(), "-e", JS, str(TOOL), json.dumps(CASES)], capture_output=True, text=True, encoding="utf-8", check=True).stdout)
    res = []

    def ok(name, cond, detail=""):
        res.append(bool(cond))
        print(("OK  " if cond else "NG  ") + name + (f" — {detail}" if detail and not cond else ""))

    rl = js["rules"]
    ok("① slot_change 규칙 같음 (TOOL slotChange ↔ 엔진 ACTION_RULES)", rl["slotChange"] == AP.ACTION_RULES["slot_change"] == "all", rl)
    ok("① 체크디짓 = 경고 후 저장 (TOOL 'warn' ↔ 엔진 override 받음)", rl["ctCheckDigitWrong"] == "warn" and AP.ACTION_RULES["ct_checkdigit_override"] is True, rl)
    ok("① 사람 값 유지 + 정보 (keep_info)", rl["humanVsEngine"] == "keep_info", rl)
    for c, j in zip(CASES, js["ct"]):
        ovr = [j["override"]] if j.get("override") else []
        try:
            ev, eok = AP.norm_value("ct", c, ovr), True
        except AP.Reject:
            ev, eok = None, False
        same = (j["ok"] == eok) and (not eok or j["value"] == ev)
        # override 표시: JS 가 override 를 단 것 = 엔진이 override 없이는 거부하는 것 (체크디짓만 틀림)
        if j.get("override"):
            try:
                AP.norm_value("ct", c)
                same = False
            except AP.Reject:
                pass
        ok(f"② CT {c!r}: JS {j.get('ok')}/{j.get('value')}{'/override' if j.get('override') else ''} ↔ 엔진 {eok}/{ev}", same)
    ok("③ 체크디짓 확인창 문구", js["msg"] == "チェックディジットが合いません。もう一度確認してください", js["msg"])
    app = (TOOL / "js" / "app.js").read_text(encoding="utf-8")
    ok("③ 催促 서명 자리표시자 같음 (remind.SIGN_PLACEHOLDER)", f"var SIGN_PLACEHOLDER = '{R.SIGN_PLACEHOLDER}'" in app, R.SIGN_PLACEHOLDER)
    ok("③ 입れ替え 확인창 「○○ が入っています。入れ替えますか」", "occ.ct + ' が入っています。入れ替えますか'" in app)
    ok("③ override 이름 같음 (CT_CHECKDIGIT_OVERRIDE)", AP.CT_CHECKDIGIT_OVERRIDE in app and AP.CT_CHECKDIGIT_OVERRIDE in (TOOL / "js" / "validate.js").read_text(encoding="utf-8"))
    print(f"== {sum(res)}/{len(res)} OK")
    return 0 if all(res) else 1


if __name__ == "__main__":
    sys.exit(main())
