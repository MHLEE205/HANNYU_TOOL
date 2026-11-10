# CHANGELOG — C-01 搬入票 TOOL

✦ Powered by LEENAI Automation System

## 0.3.1 (2026-11-10) — Microsoft 365 로그인 켬 (graph 모드 · SharePoint HANNYU_TOOL · R7A · 결정 #132 · #137) · 「写真不足」 옆 창 · 確認する (R6M13)
- **graph 모드 켬 (`js/config.js` `C01.SOURCE` 한 곳 · `graphEnabled: true` · `spRoot: 'HANNYU_TOOL'`):** 로그인 버튼 활성 → LEENAI_COMMON 로그인 (Graph 위임 토큰 · 새 권한 요청 없음) 뒤
  SharePoint ドキュメント / HANNYU_TOOL 에서 `_data/*.json` · 사진 · 원본 (blob) · `_actions/{날짜}/` (목록 + 내용 · eTag 같으면 다시 안 읽음 · `.done` = 처리됨) 을 읽음.
  쓰기 = `_actions/{날짜}/{action_id}.json` 하나뿐 (`conflictBehavior=fail` = 같은 이름 덮어쓰기 0 · 날짜 · id 형식 검사 뒤). 403 이면 「権限がありません」 안내.
  担当者 = 로그인한 사람 (`LEENAI.user` 메일 = `LEENAI.STAFF`) · 担当 港 = 공통 마스터 `pol_staff`. 상단 「SharePoint · HANNYU_TOOL」. 로컬 미리보기 (서버 · 폴더 선택) 는 그대로.
- 화면 시험 `tests/test_graph.py` (새 · 가짜 Graph · 가명 · 16) · `test_ui.py` 로그인 버튼 「활성」 으로
- 「写真不足」 queue 항목 옆 창 · 確認・入力 「確認する」 켜짐 → `confirm_value` (ct 값 그대로 · 写真) · 칩은 엔진 kinds 에 있을 때만 · 화면 시험 `tests/test_photoset.py` 16
- 버전 0.3.1 (`js/config.js` 한 곳)

## 0.3.0 (2026-11-10) — 첫 공개 (`MHLEE205/HANNYU_TOOL`) · 결정 #120 · #129 · #131 (R6T1)
- 합침: `prep-a` (#120) · `r619-reason` (R6M7) · `r620-photocount` (R6M8 · #129) · `r623-photokind` (R6M11 · #129 · #131 · #118). 충돌 1곳 = `js/app.js` `REASON_SHORT` (27·28 과 29·30 둘 다 넣음)
- #120 가명 시험 데이터를 레포에서 뺌: `fixtures/_data/` (14 파일) · `tests/compass_cases.json` (146KB) = `.gitignore` · 추적 해제. 시험 전 `tools/make_test_data.py` (새) 로 다시 만듦 —
  `make_fixtures.py` + 엔진 `tests/make_compass_cases.py` 사례 · 엔진 규칙. 다시 만든 파일 = 원래 파일과 바이트 같음 (`--check`). `tests/test_ui.py` · `tests/compass_cross.js` — 파일이 없으면 안내 후 멈춤
- 사유 짧은 표시: 27 `CONTRACT_MONTH_CONFLICT` 「契約月」 · 28 `NW_OVER_LIMIT` 「重量」 · 29 `PHOTO_SET_INCOMPLETE` 「写真不足（빠진 종류）」 · 30 `PACKER_AUTOSTOP` 「停止中」 (문장은 엔진 `reason_text`)
- #131 사유 29: 옆 창 문장의 `{없는 종류}` 를 엔진 `row.photo_missing` 으로 바꿔 표시 · 受信中 줄 기다림 「写真待ち（빠진 종류）」. 엔진이 사유를 켜기 전에는 표시할 줄이 없음 (표시만 준비)
- #129 사진 장수 색: 実況表 写真 칸 · 確認・入力 원본 머리 「写真 N枚」 — 5枚 이하 (0枚 포함) 또는 15枚 이상이면 `--ph-alert` (LIGHT `#FFC7CE` · 4테마) · 0枚 줄도 「0枚」 표시
- 버전 0.3.0 (`js/config.js` 한 곳) · README (레포 = 화면 코드만 · 데이터는 로그인 후 SharePoint 에서 읽음)

## 0.2.2 (2026-11-08) — 결정 #109 · #112 반영 · 「状況」 머리말 (R6.8 Part B)
- #109 ② `C01.RULES.slotChange = 'all'` — 実況表 줄 「⇄」 → スロット変更 창 (칸 목록 · 빈 칸 · 지금 칸). 옮길 칸에 다른 CT 가 있으면 확인창 「○○ が入っています。入れ替えますか」 →
  `slot_change` 1건 (`value: {slot_guid, slot_before, swap_ct}`) — 엔진이 두 대를 한 번에 반영 (반쪽 반영 없음). 줄에 「⇄ 枠変更」 (누가·언제·전→후) · 「元に戻す」 (전 칸으로 새 기록).
  `adminUsers` 는 `slotChange: 'admins'` 일 때만 씀
- #109 ③ `ctCheckDigitWrong = 'warn'` — 확인창 「チェックディジットが合いません。もう一度確認してください」 → 취소 = 저장 안 함 · 확인 = 저장 (`override: ["CT_CHECKDIGIT_OVERRIDE"]`) ·
  엔진 = 確認済 · 自動OK 안 됨 · 줄에 「CD」
- #109 ① 사람 값 유지 (전과 같음) + 엔진 `info` 「human_vs_engine_diff(칸)」 이 있으면 줄에 「ⓘ」 정보
- #112 催促 미리보기 서명 Email = 로그인 직원 주소 (엔진 초안 자리표시자 `(送信者のメールアドレス)` 바꿈) · CC · 끝 문구 · ✦ 그대로
- 実況表 오른쪽 끝 열 머리말 「状況」 (옛 이름에서 바꿈 — 시안에는 옛 이름만 있어 「状況」 으로 둠) · TOOL 레포 안 옛 상태 이름 글자 (確·定 붙은 것) 0
- fixtures: IV 에 `slots` (엔진 data_json 과 같은 형) · TST2611-01 빈 칸 1 · 시험 `tests/rules_cross.py` (새) · `test_ui.py` · `e2e_local.py` 새 항목 · 엔진 기본 경로 `engine_r68`

## 0.2.1 (2026-11-08) — Compass入力 D-11 (가) 규칙 준비 · 기본 OFF (R6.6)
- `js/compass.js` `compareIv(iv, rows, cells, dups, opts)` — `opts.follow_same_cond_slot` (설정 한 곳 `js/config.js` `C01.COMPASS` · 기본 false).
  켜면: 넣을 CT 가 v2 칸에 없고 같은 부킹 다른 칸 1개에 있으며 그 칸이 同一条件 (#26 — 칸 `_cond`: 営業所·品目·조건·타입·업체·단가·구매계약) 이면 그 칸으로 비교·입력
  (`SLOT_FOLLOWED` · 줄 `slot_from`). 조건 다른 칸 `CT_DUP_OTHER_COND` · 같은 CT 칸 2개 이상 `CT_DUP_MULTI` · 칸에 다른 CT `OTHER_CT_IN_SLOT` = 경고 + 입력 안 함.
  같은 CT 가 다른 칸에 없으면 (전환 후 빈 칸) v2 칸 그대로. 끄면 결과 0.2.0 과 같음
- 엔진 `engine/compass_input/rules.py` (v0.5.8 `compass_follow_same_cond_slot`) 와 같은 규칙 — 교차 시험 `tests/compass_cross.js` 43 (R6 26 + 새 17) · 실데이터 사본은 레포 밖
- 비교표 창: 새 경고·건너뜀 코드 일본어 문장 · 버전 0.2.1

## 0.2.0 (2026-11-08) — Compass入力 DRY 창 · 催促 미리보기 · 확인 칸 근거 문장 (R6)
- Compass入力 (설계 §6 · 결정 #1~#3 · #91): IV 머리줄 버튼 → 비교표 창 (칸마다 지금 값 → 넣을 값 · 同じ/空欄→入力/違う値/値なし 색 · 경고 · 건너뜀 사유 ·
  PATCH 본문 펼쳐 보기). 「全台 OK」 아닌 IV 는 비교표만 + 사유. 「送信」 = 항상 비활성 「DRY — 送信しません」.
  규칙 `js/compass.js` = 엔진 `engine/compass_input/rules.py` 와 같음 (교차 시험 `tests/compass_cross.js` · 사례 26 = 엔진 `tests/compass_cases.json`).
  local 모드는 `_data/compass_now/{IV}.json` (엔진 `tools/compass_dry.py --snap` 이 만든 미리보기 전용 칸 스냅샷) 을 읽음. graph 실행 틀 (`C01.compass.Writer`) 은 꺼짐 · 호출 0
- 催促 (설계 §7 · 결정 #97): IV 머리줄 「✉ 催促」 → 미리보기 창 (받는 사람 · CC · 보내는 사람 = 로그인 직원 · 제목 · 본문 · 회차 · 지난 催促 기록).
  「送信」 = 비활성 「下書きのみ」. 초안 = 엔진 `tools/remind_draft.py --tool-data` 의 `_data/remind.json` (현행 リマインダー 기준). 催促候補 = 초안이 있는 IV
- 確認・入力: 値の違い · 手入力 의 다른 칸 옆에 엔진 `field_source_text` 문장 (「Excel と一致」 등 — 마스터 작업본 `source_text` 초안)
- 写真のCT: 엔진 `candidates` 우선 (엔진 0.5.6 이 채움), 없으면 R5 화면 보완 그대로
- 港 칩 순서: pol_staff 에 `order` 열이 있으면 그 순서, 없으면 이름 순 (지금 마스터에 순서 열 없음)
- `C01.SEND` (compass · remind = false) 한 곳 · 버전 0.2.0 (`js/config.js`)

## 0.1.0 (2026-11-08) — 첫 로컬 미리보기 (R5)
- 実況表: 15열 · IV 머리줄 · 줄 색 (自動OK/確認済 · 要確認 · 受信待ち/メール未着) · 담당 港 자동 (#95) · 絞り込み 3 · メール未着 줄 · 사유 일본어 문장 (reason_text)
- 要確認 옆 패널: 출처별 값 고르기 · 직접 입력 · confirm_value
- 確認・入力: 4종 (値の違い · 手入力 · 写真の CT · 未分類 FAX) · 원본 확대/회전 · bbox 강조 (있을 때) · 「確認して次へ」「スキップ」 · 当社案件ではない
- 사진: 크게 · 좌우 (키보드) · 썸네일 띠 · 휠 확대
- `_actions` 설계 §5 형식 · 본인 즉시 반영 · 30초마다 다른 사람 기록 겹쳐 보기 (#100) · 先勝ち 「他の人が先に確認しました」
- 입력 검사 = 엔진 규칙 (CT 체크디짓 · seal · 숫자 · 작업일)
- 데이터 소스 local (127.0.0.1 서버 · 폴더 선택) / graph (R7, 꺼짐)
