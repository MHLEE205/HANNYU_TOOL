# C-01 搬入票 TOOL (v2)

✦ Powered by LEENAI Automation System

- 버전: **0.3.15** (2026-11-11) — 표기는 `js/config.js` `C01.TOOL_INFO` 한 곳 (LEENAI.init 이 탭 제목·헤더·로그인 카드에 표시)
- 화면: 実況表 · 確認・入力 · 사진 보기 (시안 `relay\design\시안_実況表_Main.dc.html` · `시안_確認入力_Input.dc.html` 기준)
- 공통: LEENAI_COMMON v1 (`https://mhlee205.github.io/LEENAI_COMMON/v1/`) — **읽기만**, 기본 DARK · 4테마 · 하단 표기
- **이 레포 = 화면 코드만.** 실제 데이터·번호·메일은 레포에 없음 — 직원이 로그인한 뒤 SharePoint (PHOTO_V2 `_data`) 에서 읽음 (R7 · 그 전에는 로컬 미리보기 = 고른 폴더에서 읽음)
- 가명 시험 데이터 (`fixtures/_data/` · `tests/compass_cases.json`) 도 레포에 넣지 않음 (결정 #120) — 시험 전 `tools/make_test_data.py` 로 만듦

## 데이터 소스 (`js/source.js`)
| 모드 | 상태 | 읽기 | `_actions` 쓰기 |
|---|---|---|---|
| local · 서버 | 사용 | `tools/serve_local.py` (127.0.0.1 만) 가 `--root` 폴더를 돌려줌 | `--actions` 폴더 (기본 = root) · 본 `data\photo_v2_local` 은 거부 |
| local · 폴더 | 사용 | 브라우저 폴더 선택 (Chrome/Edge File System Access) | 고른 폴더의 `_actions\{날짜}\` (사본 폴더를 고를 것) |
| **graph (기본)** | **R7A 켬** | 「Microsoft 365 でログイン」 → SharePoint ドキュメント / `HANNYU_TOOL` (직원 Graph 토큰 · `_data` · 사진 · 원본) | `HANNYU_TOOL/_actions/{날짜}/{id}.json` (덮어쓰기 0) |

- 직원 선택: 로그인 대신 `pol_staff` (local = 폴더의 `_masters/pol_staff.json`, 가명 fixtures 포함) 드롭다운. 담당 港 = 担当·補助 (#95), 마스터에 없는 港 = `*` 줄
- 자동 갱신 (R7N F): 30초마다 읽어 **바뀐 것이 없으면 다시 그리지 않음** (머리줄 「最終更新」 시각만) · 바뀌면 **바뀐 줄 · 칸만** 바꿈 (스크롤 · 열린 카드 · 원본 그대로) · **입력 중** (입력 칸 커서 · 쓰던 값 · ✎ 修正 중) 이면 미룸
- 確認・入力 원본 (R7N G): 줄과 연결된 서류만 (그 항목 + 같은 컨테이너 다른 항목의 서류 · 다른 自動OK·確認済 줄에 쓰인 서류 · 쪽은 뺌) · IV 서류 전체 표시 없음 · 없으면 「搬入票なし（待ち）」 ·
  엔진 `rows[].doc_sha16` 이 있으면 어느 줄에도 안 쓰인 서류 1~2개 「候補」 · 受信中 + `has_docs` false 줄의 手入力 = 카드 없음 (実況表 「搬入票待ち」 · 催促) ·
  엔진 `files[].rotation` / `docs[].rotation` (시계 방향 0·90·180·270 · 수 = 그 항목 쪽 · `{"쪽": 각도}`) = 처음부터 바로 · 값 칸마다 「✎ 修正」 = `manual_input` (사람 값 우선 #109)
- 実況表 「n/N台」 (R7N H-4 · #166): N = COMPASS 칸 수 그대로 · 칸보다 많은 줄 = 빨강 「COMPASS 枠外」 · 머리 「枠外 n」
- 운영 규칙 (결정 #109) = `js/config.js` `C01.RULES` 한 곳 — 엔진 `engine/actions/apply.py` `ACTION_RULES` 와 같은 규칙:
  ① 사람 값 ≠ 엔진 다시 판정 값 → 사람 값 유지 + 「ⓘ」 정보 · ② スロット変更 (⇄) = 모든 직원 — 옮길 칸에 다른 CT 가 있으면 「○○ が入っています。入れ替えますか」 → 입れ替え 1건 (`swap_ct`) · `_actions` 에 누가·언제·전→후 (`slot_before`) · 줄에 「⇄ 枠変更」 · 「元に戻す」 · ③ 체크디짓 틀린 CT = 확인창 「チェックディジットが合いません。もう一度確認してください」 → 확인하면 저장 (`override: ["CT_CHECKDIGIT_OVERRIDE"]` · 確認済 · 自動OK 안 됨 · 줄에 「CD」)
- 催促 서명 Email (#112) = 누른 직원 (로그인 사용자) 주소 — 초안의 자리표시자 `(送信者のメールアドレス)` 를 미리보기에서 바꿔 보여 줌 (엔진 `engine/notify/remind.py` `with_sender`)
- Compass入力 = 비교표 창 (DRY · `js/compass.js` = 엔진 규칙) · 催促 = 미리보기 창 — **「送信」 은 둘 다 비활성** (R7 이후 · 결정 뒤). `C01.SEND` 한 곳
- Compass入力 비교 규칙 (D-11 대기 · 기본 OFF): `js/config.js` `C01.COMPASS.follow_same_cond_slot` 한 곳 — 켜면 넣을 CT 가 같은 부킹 同一条件 다른 칸에 이미 있으면 그 칸으로 비교 (엔진 설정 `compass_follow_same_cond_slot` 과 같은 이름·규칙)
- 미리보기 전용 파일 (local): `_data/compass_now/{IV}.json` (엔진 `tools/compass_dry.py --snap`) · `_data/remind.json` (엔진 `tools/remind_draft.py --tool-data`)

## 실행 (형님이 직접 열어 보기)
```
python C:\LEENAI_C01_V2\tool\tools\serve_local.py --root C:\LEENAI_C01_V2\tool\fixtures
```
→ 브라우저 `http://127.0.0.1:8765/` → 「ローカルプレビューで開く」 (가명 데이터). 실제 데이터 사본으로 볼 때는 `--root <사본 photo_v2_local> --staff tool\fixtures\_masters\pol_staff.json`.

## 시험
- **먼저** `python tools/make_test_data.py [--engine <엔진 폴더>]` — 레포에 없는 가명 시험 데이터 `fixtures/_data/` · `tests/compass_cases.json` 을 다시 만듦 (같은 입력이면 바이트 같음 · `--check` = 같은지만 확인)
- `python tools/make_fixtures.py` — 가명 `_data` (엔진 스키마 그대로 · make_test_data 가 부름)
- `python tests/test_ui.py --shots <폴더>` — 화면 시험 (Playwright)
- `python tests/rules_cross.py` — #109·#112 규칙 Python ↔ JS 같음 (설정 · CT 입력 · 문구)
- `node tests/compass_cross.js` — Compass入力 규칙 교차 시험 (JS ↔ 엔진 Python 결과 `tests/compass_cases.json` — R6 26 + v0.2.1 17)
- `python tests/e2e_local.py --db <사본 DB> --root <사본 photo_v2_local> --data <사본 C01_DATA> --out <폴더>` — 끝-끝 (사본만)
- `python tests/render_mockup.py --out <폴더>` — 시안 대조 캡처

공개 레포 `MHLEE205/HANNYU_TOOL` (결정 #110 · #120) — v0.3.0 첫 공개 (2026-11-10) · v0.3.1 graph 모드 (R7A) · v0.3.2 実況表 한 화면 · PDF 화면 표시 (R7B) · v0.3.3 ~ v0.3.6 파일 열기 점검 (R7C) · v0.3.7 Plant 칸 · 担当港 복수 · 판단 버튼 위 (R7D) · v0.3.9 実況表 줄 순서 = COMPASS 칸 순서 · No 부킹별 · AI 区分 정보 (R7E) · v0.3.10 ~ v0.3.12 사진 장수 색 · 確認・入力 카드 · 同一コンテナ候補 · 作業日 予定日 (R7I ~ R7K) · v0.3.13 写真 = 새 탭 photo.html (R7L) · v0.3.14 사진 종류에 엔진 fill (FULL · 扉閉め) · README 버전 (R7M) · v0.3.15 자동 갱신 스크롤 유지 · 搬入票 없는 줄 手入力 숨김 · 원본 = 줄과 연결된 서류만 · 엔진 회전 · 値 修正 · COMPASS 枠外 빨강 (R7N). GitHub Pages 켜기 · Azure 리디렉트 URI · 직원 공개는 형님 작업.
- `python tests/test_graph.py` — graph 모드 시험 (가짜 Graph · 가명 · 실제 SharePoint 호출 0)
- `python tests/test_layout.py --shots <폴더>` — 実況表 한 화면 시험 (1366 · 1600 · 1920 폭 · 가로 스크롤 0 · 상자 아래 끝 ≤ 창 · 머리글 고정 · R7B)
