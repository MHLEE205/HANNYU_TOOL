# ✦ Powered by LEENAI Automation System — v0.3.83 (R12Y55 · 決定 #401) 通関依頼済 の自動記録: node 試験 + エンジンと同じ例か
# 使い方: python tests/test_clearance.py [--engine <エンジン レポ>]  (エンジンが無ければ 例の比較は飛ばす)
import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
NODE = Path(r"C:\Program Files\Python313\Lib\site-packages\playwright\driver\node.exe")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", default=str(HERE.parent.parent / "engine_r12y55"))
    a = ap.parse_args()
    checks, ng = 0, []
    r = subprocess.run([str(NODE) if NODE.exists() else "node", str(HERE / "clearance_node.js")], capture_output=True, text=True, encoding="utf-8")
    checks += 1
    last = (r.stdout.strip().splitlines() or [""])[-1]
    if r.returncode != 0:
        ng.append("node: " + r.stdout[-800:] + r.stderr[-400:])
    print(last)
    eng = Path(a.engine)
    if (eng / "engine" / "output" / "customs_done.py").exists():
        sys.path.insert(0, str(eng))
        from engine.output import customs_done as CD   # noqa: E402
        mine = json.loads((HERE / "clearance_cases.json").read_text(encoding="utf-8"))
        theirs = [{"name": n, "rec": rr, "at": at, "old": o, "kind": k, "set": s} for n, rr, at, o, k, s in CD.CASES]
        checks += 1
        if mine != theirs:
            ng.append("clearance_cases.json ≠ エンジン customs_done.CASES")
    # index.html が clearance.js を customs.js の後 · boot.js の前で読む
    html = (HERE.parent / "index.html").read_text(encoding="utf-8")
    checks += 1
    i, j, k = html.find("js/customs.js"), html.find("js/clearance.js"), html.find("js/boot.js")
    if not (0 <= i < j < k):
        ng.append("index.html の script 順")
    print(json.dumps({"checks": checks, "ng": len(ng)}))
    for x in ng:
        print("NG " + x)
    sys.exit(1 if ng else 0)


if __name__ == "__main__":
    main()
