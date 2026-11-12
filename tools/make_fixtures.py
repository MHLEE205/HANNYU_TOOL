# ✦ Powered by LEENAI Automation System — C-01 搬入票 TOOL v0.2 가명 fixtures 생성
r"""시험·스크린샷용 가명 `_data` 세트 (실제 IV·CT·seal·메일·직원 이름 없음).
구조는 엔진 출력 (engine/output/schema/*.schema.json) 과 같다. 사진·서류는 SVG 그림 (글자만).
v0.2.0 (R6): queue field_sources · field_source_text · _data/compass_now/{IV}.json (COMPASS 칸 가명 스냅샷) ·
_data/remind.json (엔진 engine/notify/remind.py 로 만든 催促 초안 — 엔진 폴더가 없으면 건너뜀) 추가.
사용: python tools/make_fixtures.py [--out fixtures] [--today 2026-11-08] [--engine C:\LEENAI_C01_V2\engine_r68]"""
import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

# 칸별 출처 일치 문장 (= 엔진 마스터 작업본 source_text 초안과 같은 문장)
SRC_TEXT = {"agree_all": "{srcs} と一致", "only_one": "{src} のみ", "agree_some": "{srcs} と一致（{others} は違う値）",
            "disagree": "{others} の値と違います", "none": "読み取った値がありません"}


def src_text(xs):
    if not xs:
        return SRC_TEXT["none"]
    ok = list(dict.fromkeys(x["src"] for x in xs if x["agree"]))
    ng = list(dict.fromkeys(x["src"] for x in xs if not x["agree"]))
    if ok and not ng:
        return (SRC_TEXT["agree_all"] if len(ok) >= 2 else SRC_TEXT["only_one"]).format(srcs="・".join(ok), src="・".join(ok))
    if ok:
        return SRC_TEXT["agree_some"].format(srcs="・".join(ok), others="・".join(ng))
    return SRC_TEXT["disagree"].format(others="・".join(ng))

LETTERS = {c: v for c, v in zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ",
                                [10, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 34, 35, 36, 37, 38])}


def ct_no(prefix, serial):
    """가명 CT (ISO 6346 체크디짓 맞음)."""
    body = f"{prefix}{serial:06d}"
    s = sum((LETTERS[ch] if ch.isalpha() else int(ch)) * (2 ** i) for i, ch in enumerate(body))
    return body + str((s % 11) % 10)


def bad_ct(prefix, serial):
    good = ct_no(prefix, serial)
    return good[:-1] + str((int(good[-1]) + 1) % 10)


def sha16(s):
    return hashlib.sha256(s.encode()).hexdigest()[:16]


PHOTO_LABELS = ["空コンテナ", "床", "積込 25%", "積込 50%", "積込 100%", "片扉", "両扉", "シール", "TARE 表示"]
PHOTO_FILL = {"積込 100%": "full", "両扉": "door_closed", "片扉": "door_open"}   # v0.3.14: エンジン fill (5種判読) の見本
COLORS = ["#3b4a5a", "#4a5a3b", "#5a3b4a", "#3b5a55", "#55503b", "#40405a", "#5a4a3b", "#3b3b3b", "#2f4f4f"]


def svg_photo(title, label, idx):
    c = COLORS[idx % len(COLORS)]
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="900" viewBox="0 0 1200 900">
<rect width="1200" height="900" fill="{c}"/>
<rect x="160" y="150" width="880" height="600" rx="18" fill="none" stroke="#d8d8d0" stroke-width="10" stroke-dasharray="30 18"/>
<text x="600" y="430" font-size="72" text-anchor="middle" fill="#f2f2ee" font-family="sans-serif">{label}</text>
<text x="600" y="520" font-size="36" text-anchor="middle" fill="#cfcfc7" font-family="monospace">{title}</text>
<text x="600" y="840" font-size="26" text-anchor="middle" fill="#a9a9a1" font-family="sans-serif">FIXTURE · 가명 데이터</text>
</svg>
"""


def svg_doc(title, boxes, faint=(), upside_down=False):
    cells = []
    for i, (k, (label, val)) in enumerate(boxes.items()):
        x = 60 + (i % 2) * 560
        y = 190 + (i // 2) * 130
        op = "0.35" if k in faint else "0.9"
        cells.append(f'<rect x="{x}" y="{y}" width="520" height="110" fill="none" stroke="#9a9a92" stroke-width="3"/>'
                     f'<text x="{x + 16}" y="{y + 30}" font-size="22" fill="#6b6b63" font-family="sans-serif">{label}</text>'
                     f'<text x="{x + 16}" y="{y + 84}" font-size="44" fill="#24304a" opacity="{op}" font-family="monospace">{val}</text>')
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="1000" viewBox="0 0 1200 1000">
<rect width="1200" height="1000" fill="#fcfcfa"/>
<text x="60" y="110" font-size="52" font-weight="700" fill="#2a2a26" font-family="sans-serif" letter-spacing="10">コンテナ貨物搬入票</text>
<text x="1140" y="110" font-size="24" text-anchor="end" fill="#6b6b63" font-family="sans-serif">{title}</text>
<line x1="60" y1="140" x2="1140" y2="140" stroke="#3a3a36" stroke-width="4"/>
{''.join(cells)}
<text x="60" y="960" font-size="22" fill="#8a8a82" font-family="sans-serif">上記の通り搬入いたします。 （FIXTURE · 가명 데이터）</text>
</svg>
""" if not upside_down else _flip(svg_doc(title, boxes, faint))


def _flip(svg):
    """v0.3.15 (R7N G-3): 上下逆に届いた FAX の見本 (180° 回した絵) — エンジンの rotation 180 で正しい向きに戻る"""
    head, rest = svg.split("\n", 1)
    return head + '\n<g transform="rotate(180 600 500)">\n' + rest.rsplit("</svg>", 1)[0] + "</g>\n</svg>\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent.parent / "fixtures"))
    ap.add_argument("--today", default="2026-11-08")
    ap.add_argument("--engine", default=r"C:\LEENAI_C01_V2\engine_r68")
    a = ap.parse_args()
    out = Path(a.out)
    today = dt.date.fromisoformat(a.today)
    d = lambda n: (today + dt.timedelta(days=n)).isoformat()  # noqa: E731
    files = {}

    def put(rel, text):
        files[rel] = text

    ivs_def = [
        # iv, pol, cy(+days), bkg, packer, plant, item, cond, rows
        ("TST2611-01", "TOKYO", 1, "BKG-TEST-0001", "PACKER_A", "工場A 本社", "JOCC", "港"),
        ("TST2611-02", "YOKOHAMA", 2, "BKG-TEST-0002", "PACKER_B", "工場B", "JONP", "店頭"),
        ("TST2611-03", "TOKYO", 5, "BKG-TEST-0003", "PACKER_C", "工場C 本社", "JMIX", "港"),
        ("TST2611-04", "KOBE", 4, "BKG-TEST-0004", "PACKER_D", "工場D", "JOCC", "港"),
        ("TST2611-05", "HAKATA", 9, "BKG-TEST-0005", "PACKER_E", "工場E", "JOCC", "港"),
    ]
    rows_def = {
        "TST2611-01": [("自動OK", [], 9), ("自動OK", [], 8), ("確認済", [], 8), ("自動OK", [], 9)],
        "TST2611-02": [("自動OK", [], 7), ("再確認", ["SOURCE_MISMATCH"], 8), ("自動OK", [], 8), ("受信中", ["MIN_SOURCES"], 0)],
        "TST2611-03": [("受信中", ["MIN_SOURCES"], 8), ("受信中", ["MIN_SOURCES"], 7)],
        "TST2611-04": [("再確認", ["RANGE"], 8), ("自動OK", [], 8), ("自動OK", [], 6), ("再確認", ["MISSING_FIELD"], 7)],
        "TST2611-05": [],
    }
    serial = 1000
    jik_ivs = []
    photos_files = {}
    queue = []
    by_status = {}
    no = 0
    for iv, pol, cyd, bkg, packer, plant, item, cond in ivs_def:
        guid = sha16("bk" + iv) + "-0000-0000-0000-000000000000"
        rows = []
        conts = []
        for i, (st, reasons, nph) in enumerate(rows_def[iv]):
            serial += 7
            ct = ct_no("TSTU", serial)
            no += 1
            cid = f"C-G-{guid[:8]}-{ct}"
            seal = f"TS{serial:06d}" if st != "受信中" or nph else None
            human = None
            engine_status = st if st != "確認済" else "再確認"
            if st == "確認済":
                human = {"seal": {"value": seal, "source": "搬入票", "by": "staff.a@example.invalid", "at": d(-1) + "T10:24:00+09:00",
                                  "action_id": "fx-human-0001"}}
            nw = None if st == "受信中" else 21000 + i * 130
            tw = 3740 if st != "受信中" or nph else None
            rows.append({"no": no, "container_id": cid, "ct": ct, "seal": seal, "n_w": nw, "t_w": tw, "bales": None if st == "受信中" else 22 + i,
                         "work_date": d(-2), "photos": nph, "status": st, "reasons": reasons, "reason_text": [], "packer": packer, "plant": plant,
                         "item": item, "slot_guid": (sha16(cid) + "-slot") if st in ("自動OK", "確認済") else None, "has_photos": nph > 0,
                         "has_docs": st != "受信中" or nph == 0, "engine_status": engine_status, "work_date_source": "搬入票" if st != "受信中" else None,
                         "info": [], "human": human})
            by_status[st] = by_status.get(st, 0) + 1
            ph = []
            for k in range(nph):
                rel = f"{iv}/{ct}/{k + 1:02d}_{PHOTO_LABELS[k % len(PHOTO_LABELS)].replace(' ', '')}.svg"
                put(rel, svg_photo(f"{iv} / {ct}", PHOTO_LABELS[k % len(PHOTO_LABELS)], k))
                it = {"path": rel, "no": k + 1, "label": PHOTO_LABELS[k % len(PHOTO_LABELS)], "size": 2000, "sha16": sha16(rel)}
                if PHOTO_FILL.get(it["label"]):        # v0.3.14 (R7M C-1): エンジン out_photo_fill の fill (写真ごとの判読) · 無い写真は null
                    it["fill"] = PHOTO_FILL[it["label"]]
                ph.append(it)
            conts.append({"container_id": cid, "ct": ct, "photos": ph})
            # 確認・入力
            docrel = f"{iv}/搬入票/搬入票_{i + 1:02d}.svg"
            boxes = {"bkg": ("BOOKING NO.", bkg), "ct": ("CONTAINER NO.", ct), "seal": ("SEAL NO.", seal or ""), "date": ("搬入日", d(-2)),
                     "nw": ("正味重量 (kg)", f"{nw or ''}"), "tw": ("風袋 (kg)", f"{tw or ''}"), "gw": ("総重量 (kg)", ""), "bales": ("個数", f"{22 + i}")}
            if st == "再確認" and "SOURCE_MISMATCH" in reasons:
                photo_seal = seal[:-1] + str((int(seal[-1]) + 3) % 10)
                put(docrel, svg_doc(packer, boxes))
                queue.append(dict(kind="値の違い", iv_no=iv, ct=ct, field="seal", container_id=cid, values={"搬入票": [seal], "写真": [photo_seal]},
                                  candidates=[], files=[{"path": docrel, "name": docrel.split("/")[-1], "page": 1, "bbox": [0.05, 0.32, 0.48, 0.43],
                                                         "sha16": sha16(docrel)}],
                                  note="写真のシールと搬入票のシールが違います", cy=d(cyd)))
            if st == "再確認" and "RANGE" in reasons:
                rows[-1]["t_w"] = 3200
                boxes["tw"] = ("風袋 (kg)", "3200")
                put(docrel, svg_doc(packer, boxes))
                queue.append(dict(kind="値の違い", iv_no=iv, ct=ct, field="t_w", container_id=cid, values={"搬入票": [3200], "写真": [3740]},
                                  candidates=[], files=[{"path": docrel, "name": docrel.split("/")[-1], "page": 1, "bbox": None, "sha16": sha16(docrel)}],
                                  note="RANGE", cy=d(cyd)))
            if st == "再確認" and "MISSING_FIELD" in reasons:
                rows[-1]["bales"] = None
                boxes["bales"] = ("個数", "2?")
                put(docrel, svg_doc(packer, boxes, faint=("bales",)))
                queue.append(dict(kind="手入力", iv_no=iv, ct=ct, field="bales", container_id=cid, values={"搬入票": []}, candidates=[],
                                  files=[{"path": docrel, "name": docrel.split("/")[-1], "page": 1, "bbox": None, "sha16": sha16(docrel)}],
                                  note="MISSING_FIELD(bales)", cy=d(cyd)))
                queue.append(dict(kind="手入力", iv_no=iv, ct=ct, field="ct", container_id=cid, values={"搬入票": []}, candidates=[],
                                  files=[{"path": docrel, "name": docrel.split("/")[-1], "page": 1, "bbox": None, "sha16": sha16(docrel + "ct")}],
                                  note="CT_CHECK", cy=d(cyd)))
        unassigned = []
        if iv == "TST2611-02":
            for k in range(4):
                rel = f"_unassigned/{iv}/M0001/{k + 1:02d}_写真.svg"
                put(rel, svg_photo(f"{iv} / CT 不明", PHOTO_LABELS[k], k + 2))
                unassigned.append({"path": rel, "no": k + 1, "label": PHOTO_LABELS[k], "size": 2000, "sha16": sha16(rel)})
            target = rows[3]
            queue.append(dict(kind="写真のCT", iv_no=iv, ct=None, field=None, container_id=None, values={},
                              candidates=[target["ct"], rows[0]["ct"]], files=[{"path": u["path"], "name": u["path"].split("/")[-1], "page": None,
                                                                                 "bbox": None, "sha16": u["sha16"]} for u in unassigned],
                              note="CT を読めなかった写真", cy=d(cyd)))
        docs = [{"path": f"{iv}/搬入票/搬入票_{i + 1:02d}.svg", "size": 3000, "sha16": sha16(iv + str(i))} for i in range(len(rows))]
        for dd in docs:
            if dd["path"] not in files:
                put(dd["path"], svg_doc(packer, {"bkg": ("BOOKING NO.", bkg), "ct": ("CONTAINER NO.", "—")}))
        photos_files[iv] = {"schema_version": 1, "iv_no": iv, "containers": conts, "unassigned": unassigned, "docs": docs}
        slots_n = max(len(rows), 3) if iv != "TST2611-05" else 2
        if iv == "TST2611-01":
            slots_n = len(rows) + 1                       # v0.2.2: 空き枠 1 つ (スロット変更の試験)
        if iv == "TST2611-02":
            slots_n = len(rows) - 1                       # v0.3.15 (R7N H-4 · #166): COMPASS 枠 3 < 行 4 → 枠外 1 行 (赤)
        mm = []
        if iv == "TST2611-03":
            mm = [{"slot_guid": sha16(iv + "m1") + "-slot", "work_date": d(1), "packer": packer, "plant": plant, "item": item, "incoterms": "CIF",
                   "status": "メール未着", "unassigned_rows": 0}]
        if iv == "TST2611-05":
            mm = [{"slot_guid": sha16(iv + f"m{k}") + "-slot", "work_date": d(3), "packer": packer, "plant": plant, "item": item, "incoterms": "CIF",
                   "status": "メール未着", "unassigned_rows": 0} for k in range(2)]
        # v0.2.2 (#109 ②): 枠一覧 (エンジン data_json ivs[].slots と同じ形) — 行の枠 + メール未着の枠 + 空き枠
        sl_guids = [r["slot_guid"] for r in rows if r["slot_guid"]] + [m["slot_guid"] for m in mm]
        sl_guids += [sha16(iv + f"free{k}") + "-slot" for k in range(max(0, slots_n - len(sl_guids)))]
        # v0.3.9 (R7E Part C): COMPASS 枠の順 seq — TST2611-04 は逆順 (行の並び ≠ 枠の並び の試験) · ほかは並びどおり
        rev = iv == "TST2611-04"
        slots = [{"slot_guid": g, "packer": packer, "plant": plant, "item": item, "incoterms": "CIF" if cond == "港" else "FOB", "type": "40HC",
                  "seq": (len(sl_guids) - 1 - k) if rev else k} for k, g in enumerate(sl_guids)]
        for m in mm:
            m["seq"] = next(x["seq"] for x in slots if x["slot_guid"] == m["slot_guid"])
        jik_ivs.append({"iv_no": iv, "booking_guid": guid, "bkg_no": bkg, "cy_cut": d(cyd), "cy_open": d(cyd - 6), "pol": pol, "state": "有効", "slots": slots,
                        "item": item, "incoterms": "CIF" if cond == "港" else "FOB", "packer": packer, "plant": plant, "slots_n": slots_n,
                        "containers_n": len(rows), "compass_input": [], "reminders": [], "rows": rows, "mail_missing": mm})
    # v0.3.12 (R7K Part G · #153): 枠の COMPASS 予定日 (slots[].work_date · 表示だけ) · TST2611-03 の 搬入票待ち 行に枠 (予定日 = 昨日 → 赤)
    # v0.3.12 (R7K Part C · #150): TST2611-03 = 写真の行 (1 行目) ↔ FAX の行 (足す · 写真なし) の 同一コンテナ候補 1 組
    for ivd in jik_ivs:
        for k, sl in enumerate(ivd["slots"]):
            sl["work_date"] = d(-1 if ivd["iv_no"] == "TST2611-03" else 2)
        if ivd["iv_no"] != "TST2611-03":
            continue
        used = {r["slot_guid"] for r in ivd["rows"]} | {m["slot_guid"] for m in ivd["mail_missing"]}
        free = [sl["slot_guid"] for sl in ivd["slots"] if sl["slot_guid"] not in used]
        r0 = ivd["rows"][0]
        if free:
            r0["slot_guid"] = free[0]
        r0["work_date"] = None
        serial += 7
        fx_ct = r0["ct"][:-3] + ("1" if r0["ct"][-3] != "1" else "2") + r0["ct"][-2:]
        no += 1
        fx = dict(r0, no=no, container_id=f"C-D-{ivd['booking_guid'][:8]}-FX1", ct=fx_ct, seal=(r0["seal"] or "TS000001")[:-1] + "9", n_w=21500, t_w=3740, bales=24,
                  work_date=d(-2), photos=0, status="受信中", engine_status="受信中", reasons=["MIN_SOURCES"], slot_guid=None, has_photos=False, has_docs=True,
                  work_date_source="搬入票")
        if not r0.get("seal"):
            r0["seal"] = "TS000001"
        pid = sha16("pair" + fx["container_id"] + r0["container_id"])
        fx["same_cand"] = {"pair_id": pid, "partner": r0["container_id"], "role": "fax", "ct_diff": 1, "seal_diff": 1}
        r0["same_cand"] = {"pair_id": pid, "partner": fx["container_id"], "role": "photo", "ct_diff": 1, "seal_diff": 1}
        ivd["rows"].append(fx)
        ivd["containers_n"] = len(ivd["rows"])
        by_status["受信中"] = by_status.get("受信中", 0) + 1
    # 未分類 FAX
    faxrel = "_fax_unmatched/2026-11-08/FAX_0001.svg"
    put(faxrel, svg_doc("発行者 不明", {"bkg": ("BOOKING NO.", "BKG-TEST-00?2"), "ct": ("CONTAINER NO.", "TSTU 10?0?5"), "seal": ("SEAL NO.", "TS00?0?7"),
                                     "nw": ("正味重量 (kg)", "21300")}, faint=("bkg", "ct"), upside_down=True))
    # v0.3.15 (R7N G-3): FAX は上下逆 → files[].rotation = 180 (時計回り · エンジンが判読の時に見つけた向き · TOOL が最初から正しい向きで表示)
    queue.append(dict(kind="未分類FAX", iv_no=None, ct=None, field=None, container_id=None, values={}, candidates=[],
                      files=[{"path": faxrel, "name": "FAX_0001.svg", "page": None, "bbox": None, "sha16": sha16(faxrel), "rotation": 180}], note="保留", cy=None))
    # v0.3.11 (R7J Part C): 保留中のメールの書類 (業者・IV 未定) — IV 候補 TST2611-01 · 実況表の IV 見出しに 「候補書類あり (1)」
    holdrel = "_hold/0a1b2c3d4e5f/HOLD_0001.svg"
    put(holdrel, svg_doc("発行者 不明 (保留)", {"bkg": ("BOOKING NO.", "BKG-TEST-0001"), "ct": ("CONTAINER NO.", "TSTU 1?0?75")}, faint=("ct",)))
    queue.append(dict(kind="業者・IV未定", iv_no="TST2611-01", ct=None, field=None, container_id=None, values={}, candidates=["TST2611-01"],
                      files=[{"path": holdrel, "name": "HOLD_0001.svg", "page": None, "bbox": None, "sha16": sha16(holdrel)}], note="PACKER_MISMATCH", cy=None,
                      extra={"received_at": today.isoformat() + "T09:10:00+09:00", "hold_code": "PACKER_MISMATCH", "packer_guess": None}))
    for iv_ in jik_ivs:
        if iv_["iv_no"] == "TST2611-01":
            iv_["hold_docs"] = 1
    # v0.3.15 (R7N Part G-1 · G-2-0): 搬入票の無い行の 手入力 (エンジンが出す形 · files なし)
    #  TST2611-03 = 受信中 · has_docs false の 2 行 (1 行は 同一候補あり) → 確認・入力 のカードにしない (実況表 「搬入票待ち」 だけ)
    #  TST2611-02 4 行目 = has_docs true だが 行と結び付いた書類なし → カードは出す · 原本 = 「搬入票なし（待ち）」 (IV の書類は出さない)
    for iv_ in jik_ivs:
        if iv_["iv_no"] == "TST2611-03":
            for r, fld in zip(iv_["rows"][:2], ("seal", "n_w")):
                queue.append(dict(kind="手入力", iv_no=iv_["iv_no"], ct=r["ct"], field=fld, container_id=r["container_id"], values={"搬入票": []}, candidates=[],
                                  files=[], note=f"MISSING_FIELD({fld})", cy=iv_["cy_cut"]))
        if iv_["iv_no"] == "TST2611-02":
            r = iv_["rows"][3]
            queue.append(dict(kind="手入力", iv_no=iv_["iv_no"], ct=r["ct"], field="n_w", container_id=r["container_id"], values={"搬入票": []}, candidates=[],
                              files=[], note="MISSING_FIELD(n_w)", cy=iv_["cy_cut"]))
    items = []
    row_of = {r["container_id"]: r for iv_ in jik_ivs for r in iv_["rows"]}
    for q in queue:
        qid = sha16("|".join([q["kind"], q["container_id"] or "", q["field"] or "", ",".join(f["sha16"] for f in q["files"])]))
        fs = {}
        r = row_of.get(q["container_id"]) if q["container_id"] else None
        if r:
            for f in ("ct", "seal", "n_w", "t_w", "bales", "work_date"):
                if f == q["field"]:
                    fs[f] = [{"src": k, "value": v, "agree": str(v) == str(r.get(f))} for k, vs in q["values"].items() for v in vs]
                elif r.get(f) is not None:
                    fs[f] = [{"src": "搬入票", "value": r[f], "agree": True}] + ([{"src": "Excel", "value": r[f], "agree": True}] if f in ("n_w", "bales") else [])
                else:
                    fs[f] = []
        items.append({"queue_id": qid, "kind": q["kind"], "iv_no": q["iv_no"], "ct": q["ct"], "field": q["field"], "container_id": q["container_id"],
                      "values": q["values"], "candidates": q["candidates"], "files": q["files"], "note": q["note"], "resolved": None, "superseded": [],
                      "cy_cut": q["cy"], "cy_open": None, "issuer": None,
                      "field_sources": fs, "field_source_text": {f: src_text(v) for f, v in fs.items()}, **q.get("extra", {})})
    reason_text = {"SOURCE_MISMATCH": "搬入票・写真・Excel で値が違います",          # = 엔진 마스터 작업본 reason_text 초안과 같은 문장
                   "RANGE": "値が通常の範囲の外です（風袋・重量・ベール数）",
                   "MISSING_FIELD": "必要な項目（CT・シール・重量・ベール数）が足りません",
                   "MIN_SOURCES": "確認に必要な書類・写真がまだそろっていません"}
    for iv_ in jik_ivs:
        for r in iv_["rows"]:
            r["reason_text"] = [reason_text.get(x, x) for x in r["reasons"]]
    jik = {"schema_version": 1, "today": today.isoformat(), "window": {"cy_from": d(-3), "cy_to": d(30)},
           "columns": [{"key": k, "label": lb, "from": fr} for k, lb, fr in (
               ("no", "No", "row"), ("cy_cut", "CYカット", "iv"), ("iv_no", "Invoice番号", "iv"), ("item", "品目", "iv"), ("ct", "CT番号", "row"),
               ("seal", "シール番号", "row"), ("n_w", "正味重量", "row"), ("t_w", "風袋重量", "row"), ("bales", "ベール数", "row"),
               ("work_date", "作業日", "row"), ("incoterms", "条件", "iv"), ("packer", "圧縮業者", "iv"), ("plant", "Plant", "iv"),
               ("photos", "写真", "row"), ("status", "状況", "row"))],
           "statuses": ["自動OK", "再確認", "受信中", "確認済"],
           "count": {"ivs": len(jik_ivs), "rows": sum(len(x["rows"]) for x in jik_ivs), "by_status": by_status,
                     "mail_missing": sum(len(x["mail_missing"]) for x in jik_ivs)}, "ivs": jik_ivs}
    qk = ["値の違い", "手入力", "写真のCT", "未分類FAX", "業者・IV未定"]
    qd = {"schema_version": 1, "today": today.isoformat(), "kinds": qk,
          "count": {k: sum(1 for x in items if x["kind"] == k) for k in qk}, "items": items, "open": len(items)}
    meta = {"schema_version": 1, "engine_version": "fixture", "engine_commit": None, "last_run": {"at": today.isoformat() + "T10:13:00+09:00", "status": "ok"},
            "next_run": None, "error": None, "generated_at": today.isoformat() + "T10:13:00+09:00", "today": today.isoformat(), "db_name": "fixture",
            "rows": {"containers": jik["count"]["rows"]}}
    staff = {"schema_version": 1, "note": "가명 — 시험용 (실제 마스터는 LEENAI.master pol_staff)",
             "staff": [{"code": "STAFF_A", "name": "STAFF A", "email": "staff.a@example.invalid"},
                       {"code": "STAFF_B", "name": "STAFF B", "email": "staff.b@example.invalid"},
                       {"code": "STAFF_C", "name": "STAFF C", "email": "staff.c@example.invalid"},
                       {"code": "STAFF_D", "name": "STAFF D", "email": "staff.d@example.invalid", "admin": True}],
             "items": [{"pol": "TOKYO", "main": "STAFF_A", "sub": "STAFF_B"}, {"pol": "YOKOHAMA", "main": "STAFF_B", "sub": "STAFF_A"},
                       {"pol": "KOBE", "main": "STAFF_C", "sub": ""}, {"pol": "*", "main": "STAFF_C", "sub": ""}]}
    data = out / "_data"
    (data / "photos").mkdir(parents=True, exist_ok=True)
    (out / "_masters").mkdir(parents=True, exist_ok=True)
    dump = lambda o: json.dumps(o, ensure_ascii=False, indent=1) + "\n"  # noqa: E731
    (data / "jikkyou.json").write_text(dump(jik), encoding="utf-8")
    (data / "queue.json").write_text(dump(qd), encoding="utf-8")
    (data / "meta.json").write_text(dump(meta), encoding="utf-8")
    for iv, p in photos_files.items():
        (data / "photos" / f"{iv}.json").write_text(dump(p), encoding="utf-8")
    (out / "_masters" / "pol_staff.json").write_text(dump(staff), encoding="utf-8")
    # v0.2.0: COMPASS 칸 가명 스냅샷 (TOOL local 모드 Compass入力 DRY 창) — 空欄 · 同じ · 違う値 · 42GP · CT 重複 를 섞음
    (data / "compass_now").mkdir(parents=True, exist_ok=True)
    for iv_ in jik_ivs:
        cells, dups = {}, {}
        for k, r in enumerate(iv_["rows"]):
            g = r["slot_guid"]
            if not g:
                continue
            c = {"crcf9_container_informationid": g, "@odata.etag": f'W/"{1000 + k}"', "crcf9_container_no": None, "crcf9_seal_no": None, "crcf9_n_w": None,
                 "crcf9_g_w": None, "crcf9_t_w": None, "crcf9_quantity": None, "crcf9_type": "45GP", "_packer": iv_["packer"], "_item": iv_["item"],
                 "_plant": iv_["plant"]}
            seal = (r.get("human") or {}).get("seal", {}).get("value") or r["seal"]
            if k == 1:          # 同じ
                c.update(crcf9_container_no=r["ct"], crcf9_seal_no=seal, crcf9_n_w=r["n_w"], crcf9_g_w=r["n_w"], crcf9_t_w=r["t_w"], crcf9_quantity=r["bales"])
            if k == 2:          # 違う値 (正味) + 42GP
                c.update(crcf9_container_no=r["ct"], crcf9_n_w=(r["n_w"] or 0) - 40, crcf9_type="42GP")
            if k == 3:          # CT が別の枠にもある
                dups[g] = [r["ct"]]
            cells[g] = c
        (data / "compass_now" / f"{iv_['iv_no']}.json").write_text(dump({"schema_version": 1, "iv_no": iv_["iv_no"], "booking_guid": iv_["booking_guid"],
                                                                         "cells": cells, "dups": dups, "note": "가명 — 시험용"}), encoding="utf-8")
    eng = Path(a.engine)
    if (eng / "engine" / "notify" / "remind.py").exists():
        sys.path.insert(0, str(eng))
        sys.path.insert(0, str(eng / "tools"))
        import remind_draft  # noqa: E402  (엔진 催促 규칙 · 문안 그대로)
        book = {r["packer"]: {"to": [f"{r['packer'].lower()}@example.invalid"], "cc": [], "company": f"{r['packer']} 株式会社"}
                for iv_ in jik_ivs for r in iv_["rows"] if r.get("packer") and r["packer"] != "PACKER_C"}
        drafts = remind_draft.from_ivs(jik_ivs, today, book)
        ri = remind_draft.tool_index(drafts, today)
        # v0.3.11 (R7J Part H): 「候補あり」 で催促から外した行 (エンジン remind.index_for の cand と同じ形)
        ri["cand"] = {"TST2611-02": {"PACKER_B": {"ct": 1, "bkg": 0, "cts": [ct_no("TSTU", 352)]}}}
        # v0.3.12 (R7K Part D ② · D-55 (나)): BKG だけ合う候補の行も催促の対象 — 下書きに cand_bkg · cand_note (エンジン remind.targets と同じ形)
        for d_ in (ri["ivs"].get("TST2611-03") or [])[:1]:
            d_.update(cand_bkg=1, cand_note="候補あり — 確認してから送信")
        (data / "remind.json").write_text(dump(ri), encoding="utf-8")
    for rel, text in files.items():
        p = out / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    print(json.dumps({"ivs": len(jik_ivs), "rows": jik["count"]["rows"], "queue": len(items), "files": len(files), "bad_ct_example": bad_ct("TSTU", 1)},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
