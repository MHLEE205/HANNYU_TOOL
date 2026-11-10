/* ✦ Powered by LEENAI Automation System — C-01 搬入票 TOOL 設定 (この 1 か所だけ)
   - バージョンは TOOL_INFO.version の 1 か所だけ (LEENAI.init がタブ名・ヘッダー・ログイン画面に表示)
   - 運用ルール (D-6) は RULES の 1 か所で切り替え */
'use strict';
window.C01 = window.C01 || {};

C01.TOOL_INFO = {
  sys: 'C-01',
  name: '搬入票',
  version: '0.3.0',
  date: '2026-11-10',
  desc: '実況表 · 確認・入力 · 写真 · Compass入力 (DRY) · 催促プレビュー（ローカルプレビュー版 — データは選んだフォルダから読みます）'
};

/* D-6 → 決定 #109 (R6.8) で決まった規則。ここだけ変える (エンジン engine/actions/apply.py ACTION_RULES と同じ規則) */
C01.RULES = {
  /* ① 人が確認した値 ≠ 後でエンジンが判定し直した値: 'keep_info' = 人の値を残して情報表示 (#109 ①) / 'recheck' = 要確認に戻す */
  humanVsEngine: 'keep_info',
  /* ② slot_change (スロット変更): 'all' = 全職員 (#109 ②) / 'admins' = adminUsers だけ (旧)。
        移す枠に他の CT があれば「○○ が入っています。入れ替えますか」→ 入れ替え。_actions に 誰・いつ・前→後 · 行に表示 · 元に戻せる */
  slotChange: 'all',
  adminUsers: [],
  /* ③ チェックデジットが合わない CT の手入力: 'warn' = 確認窓のあと保存 (#109 ③ · CT_CHECKDIGIT_OVERRIDE · 確認済 · 自動OK にしない) / 'reject' = 受け付けない (旧) */
  ctCheckDigitWrong: 'warn'
};

/* データの読み先: 'local' (今 — 127.0.0.1 サーバー or フォルダ選択) / 'graph' (R7 — SharePoint PHOTO_V2、今は使わない) */
C01.SOURCE = {
  mode: 'local',
  pollMs: 30000,          /* 他の人の確認を 30 秒ごとに読む (決定 #100) */
  graphEnabled: false     /* R7 まで false — graph への呼び出し 0 */
};

/* v0.2.0 (R6): Compass入力 · 催促 は下書き・比較表だけ。送信ボタンは常に無効 (R7 以降 · 決定のあと) */
C01.SEND = {
  compass: false,         /* true にしても R6 のコードは送らない — js/compass.js Writer は enabled + fetchFn が無いと PATCH しない */
  remind: false
};

/* v0.2.1 (R6.6): Compass入力 比較の規則 — 決定 D-11 待ち。ここだけ変える (エンジン設定 compass_follow_same_cond_slot と同じ名前・同じ規則)
   follow_same_cond_slot: true = 入れる CT が同じブッキングの同一条件の別の枠に既にあれば、その枠で比較・入力 (D-11 (가)) / false = 今のまま (既定) */
C01.COMPASS = {
  follow_same_cond_slot: false
};
