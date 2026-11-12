# ✦ Powered by LEENAI Automation System — C-01 搬入票 TOOL v0.1 로컬 미리보기 서버 (127.0.0.1 전용)
r"""TOOL 코드 (이 레포) + 사용자가 고른 데이터 폴더 (`_data` · 사진 · 서류) 를 127.0.0.1 에서만 보여 준다.
- 바인드 주소는 127.0.0.1 고정 (다른 PC 에서 접속 불가).
- 데이터 폴더는 읽기만. `_actions` 쓰기는 --actions 폴더에만 (기본 = 데이터 폴더). 본 엔진 출력 폴더
  (`C:\LEENAI_C01_V2\data\photo_v2_local`) 에는 쓰지 않는다 (1분 tick 이 본 DB 에 반영하므로) — 그 경로면 시작을 거부.
- 외부 네트워크 호출 0 (이 서버는 파일만 돌려줌).
사용: python tools/serve_local.py --root <데이터 폴더> [--actions <사본 폴더>] [--port 8765] [--staff <pol_staff.json>]
      → 브라우저 http://127.0.0.1:8765/"""
import argparse
import datetime as dt
import json
import mimetypes
import os
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse, parse_qs

TOOL = Path(__file__).resolve().parent.parent
MAIN_OUTPUT = Path(r"C:\LEENAI_C01_V2\data\photo_v2_local").resolve()
ACTIONS = "_actions"
REQUIRED = ("schema_version", "action_id", "action", "iv", "ct", "field", "value", "source", "by", "at", "queue_id")
ACTION_ID_RE = re.compile(r"^[A-Za-z0-9_-]{8,64}$")
mimetypes.add_type("image/svg+xml", ".svg")
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/css", ".css")


def inside(base, p):
    try:
        p.resolve().relative_to(base.resolve())
        return True
    except ValueError:
        return False


class H(BaseHTTPRequestHandler):
    server_version = "C01ToolLocal/0.1"

    def log_message(self, fmt, *args):
        if self.server.verbose:
            sys.stderr.write("%s\n" % (fmt % args))

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False).encode("utf-8")
        elif isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _file(self, base, rel):
        p = (base / rel)
        if not inside(base, p) or not p.is_file():
            return self._send(404, {"error": "not found"})
        ctype = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in ("application/javascript", "application/json", "image/svg+xml"):
            ctype += "; charset=utf-8"
        return self._send(200, p.read_bytes(), ctype)

    def do_GET(self):
        u = urlparse(self.path)
        path = unquote(u.path)
        s = self.server
        if path in ("/", "/index.html"):
            return self._file(TOOL, "index.html")
        if path == "/photo.html":                    # v0.3.13 (R7L Part E): 写真ページ (新しいタブ)
            return self._file(TOOL, "photo.html")
        if path == "/doc.html":                      # v0.3.23 (R7W Part B): 書類ページ (新しいタブ)
            return self._file(TOOL, "doc.html")
        if path == "/api/config":
            return self._send(200, {"mode": "local", "today": s.today or dt.date.today().isoformat(), "root_name": s.root.name,
                                    "actions_separate": s.actions != s.root})
        if path == "/api/staff":
            for p in (s.staff, s.root / "_masters" / "pol_staff.json"):
                if p and Path(p).is_file():
                    return self._send(200, Path(p).read_bytes())
            return self._send(404, {"error": "pol_staff なし"})
        if path == "/api/actions":
            q = parse_qs(u.query)
            days = q.get("day") or []
            return self._send(200, {"items": self.list_actions(days)})
        if path == "/api/ask":                        # v0.3.25 (R7Z Part A): AI 相談 (質問 + 答え)
            return self._send(200, {"items": self.list_asks(parse_qs(u.query).get("day") or [])})
        if path.startswith("/data/"):
            rel = path[len("/data/"):]
            if rel.startswith(ACTIONS + "/"):
                return self._file(s.actions, rel)
            return self._file(s.root, rel)
        rel = path.lstrip("/")
        if rel.split("/")[0] in ("js", "app.css", "fixtures") or rel == "app.css":
            return self._file(TOOL, rel)
        return self._send(404, {"error": "not found"})

    def list_actions(self, days):
        base = self.server.actions / ACTIONS
        out = []
        if not base.exists():
            return out
        dirs = [base / d for d in days if re.fullmatch(r"\d{4}-\d{2}-\d{2}", d)] if days else [p for p in base.iterdir() if p.is_dir()]
        for d in dirs:
            if not d.is_dir() or d.name.startswith("_"):
                continue
            for p in sorted(d.glob("*.json")):
                try:
                    a = json.loads(p.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    continue
                out.append({"file": f"{d.name}/{p.name}", "done": p.with_name(p.name + ".done").exists(), "action": a})
        return out

    def list_asks(self, days):
        base = self.server.actions / ACTIONS
        out = []
        for d in days:
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", d) or not (base / "ask" / d).is_dir():
                continue
            for p in sorted((base / "ask" / d).glob("*.json")):
                try:
                    a = json.loads(p.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    continue
                rp = base / "ask_reply" / p.name
                try:
                    r = json.loads(rp.read_text(encoding="utf-8")) if rp.is_file() else None
                except (OSError, ValueError):
                    r = None
                out.append({"ask": a, "reply": r})
        return out

    def post_ask(self, a):
        if not ACTION_ID_RE.match(str(a.get("ask_id") or "")) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(a.get("at") or "")[:10]):
            return self._send(400, {"error": "schema"})
        d = self.server.actions / ACTIONS / "ask" / str(a["at"])[:10]
        d.mkdir(parents=True, exist_ok=True)
        p = d / f"{a['ask_id']}.json"
        if p.exists():
            return self._send(409, {"error": "exists"})
        p.write_text(json.dumps(a, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        return self._send(201, {"file": p.name})

    def do_POST(self):
        u = urlparse(self.path)
        if u.path == "/api/ask":
            n = int(self.headers.get("Content-Length") or 0)
            if n <= 0 or n > 16 * 1024:
                return self._send(400, {"error": "size"})
            try:
                return self.post_ask(json.loads(self.rfile.read(n).decode("utf-8")))
            except ValueError:
                return self._send(400, {"error": "json"})
        if u.path != "/api/actions":
            return self._send(404, {"error": "not found"})
        n = int(self.headers.get("Content-Length") or 0)
        if n <= 0 or n > 64 * 1024:
            return self._send(400, {"error": "size"})
        try:
            a = json.loads(self.rfile.read(n).decode("utf-8"))
        except ValueError:
            return self._send(400, {"error": "json"})
        miss = [k for k in REQUIRED if k not in a]
        if miss or not ACTION_ID_RE.match(str(a.get("action_id") or "")):
            return self._send(400, {"error": "schema", "missing": miss})
        day = str(a["at"])[:10]
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day):
            return self._send(400, {"error": "at"})
        d = self.server.actions / ACTIONS / day
        d.mkdir(parents=True, exist_ok=True)
        p = d / f"{a['action_id']}.json"
        if p.exists():
            return self._send(409, {"error": "exists"})
        tmp = d / f".{a['action_id']}.tmp"
        tmp.write_text(json.dumps(a, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        os.replace(tmp, p)
        return self._send(201, {"file": f"{day}/{p.name}"})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(TOOL / "fixtures"), help="데이터 폴더 (_data · 사진 · 서류) — 읽기만")
    ap.add_argument("--actions", help="_actions 를 쓸 폴더 (기본 = --root). 본 photo_v2_local 은 거부")
    ap.add_argument("--staff", help="pol_staff.json (기본 = {root}/_masters/pol_staff.json)")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--today", help="화면의 오늘 (시험용)")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args()
    root = Path(a.root).resolve()
    actions = Path(a.actions).resolve() if a.actions else root
    if inside(MAIN_OUTPUT, actions):
        sys.exit("거부: 본 엔진 출력 폴더 (photo_v2_local) 에는 _actions 를 쓰지 않습니다 — --actions 로 사본 폴더를 지정하세요")
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), H)
    srv.root, srv.actions, srv.staff, srv.today, srv.verbose = root, actions, (Path(a.staff) if a.staff else None), a.today, a.verbose
    print(f"C-01 TOOL ローカルプレビュー: http://127.0.0.1:{a.port}/  (data={root.name} · actions={'別フォルダ' if actions != root else '同じ'})", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
