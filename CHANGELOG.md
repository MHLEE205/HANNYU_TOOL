# CHANGELOG — C-01 搬入票 TOOL

✦ Powered by LEENAI Automation System

## 0.3.9 (2026-11-10) — 実況表 줄 순서 = COMPASS 칸 순서 · No 부킹별 · 「AI 区分が異なる」 공개 (R7E Part C · D · E-3)
- **줄 순서 (형님 ②):** 부킹 안 줄 = COMPASS 칸 순서 (엔진 v0.5.32 `slots[].seq` · 없으면 칸 목록 순서). 칸이 정해진 줄은 그 칸 자리 · メール未着 칸 줄도 그 자리 ·
  **칸이 없는 줄 = 그 부킹 맨 아래 「未割当」 표** (점선 테두리 · 마우스 = 설명). 조건이 같은 칸끼리의 배정 순서는 의미 없음 (#130) — 화면 줄만 seq 순.
- **台数 = 칸 수 기준:** 「n/15台」 의 15 = 칸 수 (未割当 줄과 그 몫의 メール未着 칸을 따로 세지 않음 · 이중 셈 0). 칸보다 컨테이너가 많을 때만 컨테이너 수.
- **No (D-42):** 부킹마다 1 부터 (IV 머리줄 아래 1, 2, 3 …).
- 0.3.8 (브랜치) 의 「AI 区分が異なる」 정보를 합침 (R7E 지시서 절대 규칙 4 · 이번 push 에 포함).
- 시험: test_ui 65 (No 부킹별 · seq 순 · 未割当 맨 아래 · 台数 이중 셈 0 · メール未着 칸 자리) · test_layout 32 (칸 배정 줄 品目 · 条件 · 圧縮業者 · Plant 「・」 0) · 시험 데이터 TST2611-04 칸 seq 역순 · 버전 0.3.9

## 0.3.8 (2026-11-10 · 브랜치 r7d-ui-aidiff · R7D 에서는 공개 push 안 함 — 0.3.9 에 합쳐 공개) — 「AI 区分が異なる」 정보 (R7D Part A · 결정 #139 ①)
- 엔진 v0.5.31 `s2_structure_first` 로 구조 (폴더 · 파일명 · 업체 규칙) 묶음이 束済 가 된 줄 = jikkyou `info` 「AI_GROUP_DIFF」 → 実況表 상태 칸 옆 「AI区分」 표 (마우스 = 설명) · 確認・入力 머리 「AI 区分が異なる」. 판정 · 입력 영향 0 (정보만).
- 시험: `test_layout` R7D A 추가 (31) · 버전 0.3.8

## 0.3.7 (2026-11-10) — 형님 화면 확인 3건 (R7D Part U)
- **実況表 Plant 칸:** 엔진 줄에 plant 가 비면 IV 의 후보 칸 plant 전체를 「・」 로 이어 붙여 보였음 (예: 「…(第二営業所)・…(横浜)・…(船橋)」) →
  **칸 배정된 줄 = 배정 칸 (slot_guid) 의 값 1개** · 미배정 줄 = 컨테이너 값 → 후보 칸 값이 1종류면 그것 → 그 밖 「—」 (마우스 = 「候補: A / B」).
  品目 · 条件 (incoterms) · 圧縮業者 · 옆 창 머리 · 確認・入力 머리도 같은 방식 (圧縮業者 는 엔진 컨테이너 값이 먼저). 엔진 v0.5.31 도 배정 칸 plant · item 을 줄에 넣음.
- **担当港 복수 선택:** 港 버튼 = 토글 (여러 개) · 「全港」 = 전부 · 「自分の担当」 = 마스터 担当・補助 · 모두 빼면 全港 · 고른 조합은 브라우저에 기억 (`localStorage c01_ports` · 못 쓰는 환경 = 기억만 안 함).
- **確認・入力 판단 버튼 위치:** 「確認して次へ / 選んでください」 · 「スキップ（あとで）」 · 「当社案件ではない」 = 오른쪽 패널 **맨 위 (항목 제목 바로 아래)** · 모든 종류 (値の違い · 手入力 · 写真のCT · 未分類FAX · 写真不足) 같은 위치.
- 시험: `test_ui` U-2 · U-3 추가 (61) · `test_layout` U-1 추가 (30) · 버전 시험 0.3.7
- 버전 0.3.7 (`js/config.js` 한 곳)

## 0.3.6 (2026-11-10) — 「別タブで開く」 = SharePoint 보기 화면 (R7C · 형님 확인 「파일이 다운로드가 됨」)
- Graph `webUrl` 은 파일 자체 주소라 열면 내려받기가 됨 (Chrome 은 빈 탭을 닫음) → `?web=1` 을 붙여 SharePoint 보기 화면 (PDF 보기 · Excel Online) 으로 엶.
- 버전 0.3.6 (`js/config.js` 한 곳)

## 0.3.5 (2026-11-10) — 確認・入力: Excel 원본 안내 · Thumbs.db 제외 (R7C)
- 화면에 못 그리는 파일 (Excel 등) = 「上の「別タブで開く」で SharePoint で開けます」 안내 (실제: 手入力 16건은 원본이 Excel 뿐인 IV).
- IV 서류 목록에서 `.db` (메일 첨부 Thumbs.db 꼴) 제외.
- 버전 0.3.5 (`js/config.js` 한 곳)

## 0.3.4 (2026-11-10) — 確認・入力 원본 기본 선택 (R7C 실제 Graph 시험에서 발견)
- 파일 지정이 없는 항목 (手入力 등) 의 IV 서류 첫 번째가 Excel 이면 「このファイルは画面に表示できません」 만 보였음 → 아직 고르지 않았으면 **화면에 나오는 파일 (PDF · 사진) 중 이름에 「搬入」 이 있는 것 → 없으면 첫 PDF · 사진** 을 먼저 보여 줌. 칩으로 다른 파일 선택은 그대로.
- 버전 0.3.4 (`js/config.js` 한 곳)

## 0.3.3 (2026-11-10) — 파일 열기 전체 점검 (R7C · D-37 · 형님 「사진 · PDF 가 안 보임 · 開く 안 됨」)
- **원인 (실제 SharePoint · 실제 브라우저 시험):** 실제 Graph 404 114 = cy_cut 지난 IV 파일 109 (엔진 v0.5.28 동기가 올리지 않음 · 実況表 맨 위가 그 IV) + 선택 `_data` 5. 경로 · 인코딩 · CORS · 302 리다이렉트 문제 0 (표본 20 모두 열림 · 내용 같음). → **엔진 v0.5.30 이 TOOL 이 보여 주는 IV 를 올림** (TOOL 코드와 별도).
- **읽지 못한 파일 = 이유 표시:** 사진 · PDF 가 빈칸 / 흰 화면으로 남지 않고 「SharePoint にまだありません」 · 「見る権限がありません (403)」 · 「通信できませんでした」 (`Graph.fileError`). PDF 를 못 읽으면 빈 iframe 으로 물러나지 않음.
- **「別タブで開く」 = SharePoint 화면 (webUrl):** 옛 판은 파일을 받은 뒤 `window.open` → 브라우저가 팝업으로 막음 · blob 은 PDF 외부 열기 설정 PC 에서 내려받기만 됨. 지금 = 클릭 안에서 먼저 탭을 열고 SharePoint 주소로 이동 (`Graph.webUrl` · GET 만) · PDF 말고 Excel · 사진 원본에도 버튼.
- **確認・入力 원본:** 파일이 여러 개면 위에 칩으로 바꿔 보기 · 파일 지정이 없는 항목 (手入力 27 · 値の違い 5) 은 그 IV 의 서류 (photos/{IV}.json docs) 를 보여 줌 (「この項目の原本の指定がないため IV の書類を表示」).
- 実況表 사진 버튼: 사진 목록이 비면 아무 일도 안 일어나던 것 → 「このコンテナの写真はまだありません」.
- 시험: `tests/test_graph.py` 갱신 (404 이유 표시 · 별 탭 = webUrl · 파일 칩 · IV 서류) · 실제 Graph 브라우저 시험 (토르 PC · 엔진 토큰 · GET 만) 은 보고서
- 버전 0.3.3 (`js/config.js` 한 곳)

## 0.3.2 (2026-11-10) — 実況表 한 화면 · PDF 화면 안 표시 · 오래된 未分類 FAX 숨김 (R7B · 형님 지적 2건)
- **実況表 가로 스크롤 0:** `table-layout: fixed` + `colgroup` (숫자 칸 좁게 · 品目 · 圧縮業者 · Plant = 2줄까지 + 마우스 올리면 전체 (title)) · 글자 13px 그대로 ·
  칸 순서 · 이름 그대로. 화면 폭 상한 1500 → 1840px. 세로 = 창 높이에 맞춘 한 상자 (`fitTable` · 머리글 고정 · 상자 아래 끝이 창 밖으로 안 나감 · 창 크기 바꾸면 다시 맞춤)
- **PDF (搬入票 · 未分類 FAX) = pdf.js 로 화면 안에 그림** (`C01.PDF` · cdnjs 3.11.174 고정 · LEENAI 다른 TOOL 과 같은 판):
  브라우저 내장 PDF 보기가 꺼진 PC (Chrome/Edge `always_open_pdf_externally`) 에서 iframe 이 「PDF 아이콘 + GUID + 開く」 만 보이던 문제.
  확대 · 축소 · 회전 (pdf.js 그리기 · CSS 회전 없음) · 페이지 넘김 (‹ p.N / M ›) · 엔진 `page` 가 있으면 그 쪽부터 · 「別タブで開く」 보조 · pdf.js 를 못 읽으면 예전 iframe ·
  옆 창 원본 썸네일도 PDF 1쪽을 그림. 사진 (jpg) 은 그대로
- **未分類 FAX:** 받은 지 `C01.QUEUE.faxHideAfterDays` (7) 일 지난 것은 기본 목록에서 숨김 (지우기 0 · 「古い未分類 FAX も表示」 로 모두) — 받은 날 = 엔진 queue `received_at`
  (없는 항목은 숨기지 않음 · 지금 엔진 출력에는 없음). 보낸 곳 = `issuer` 가 있으면 표시 (없으면 「送信元 不明」) · 받은 날 표시
- 시험: `tests/test_layout.py` (새 · 1366 · 1600 · 1920 · 28) · `tests/test_graph.py` PDF 표시 11 추가 (가명 2쪽 PDF · canvas 그려짐 · 넘김 · 회전 · 확대 · 물러남 · FAX 숨김) = 27
- 버전 0.3.2 (`js/config.js` 한 곳)

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
