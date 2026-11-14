/* ✦ Powered by LEENAI Automation System — C-01 搬入票 TOOL 設定 (この 1 か所だけ)
   - バージョンは TOOL_INFO.version の 1 か所だけ (LEENAI.init がタブ名・ヘッダー・ログイン画面に表示)
   - 運用ルール (D-6) は RULES の 1 か所で切り替え */
'use strict';
window.C01 = window.C01 || {};

C01.TOOL_INFO = {
  sys: 'C-01',
  name: '搬入票',
  version: '0.3.31',
  date: '2026-11-13',
  desc: '実況表 · 確認・入力 · 写真 · Compass入力 (試験運用中) · 催促プレビュー（Microsoft 365 でログイン → SharePoint PHOTO_V2 のデータを表示）'
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
  ctCheckDigitWrong: 'warn',
  /* ④ v0.3.23 (R7W Part A · 형님 15:3x): 自動OK · 確認済 の行も 修正 — 状況を押す → 警告 1 回 → 修正フォーム · 人の値があっても新しい値 (mode edit) · 元に戻す。
        エンジン v0.5.50 actions_value_edit が on の時だけ true にする (off のエンジンは mode を知らず 先の値が勝つ) */
  valueEdit: true,
  /* ⑤ v0.3.23 (R7W Part D · 決定 #206): 業者・IV 未定 カード = 「IVに連結」 (BKG/IV + 枠を担当者が選ぶ) — エンジン s2_human_link_iv が on の時だけ true */
  linkIv: true,
  /* ⑥ v0.3.27 (R8C Part F · 決定 #226): 「他社のコンテナ」 — その CT の写真 + 書類だけ IV から外す (原本は消さない · 元に戻す) — エンジン s3_human_other_ct が on の時だけ true */
  otherCt: true,
  /* ⑦ v0.3.28 (R8D Part A · 決定 #227): 未分類 FAX カード = 「IVに連結」 (印刷 BKG の候補 IV · 枠を選ぶ · 終わったブッキングも候補なら選べる) — エンジン out_fax_link_iv が on の時だけ true */
  faxLinkIv: true
};

/* データの読み先: 'graph' (R7A — Microsoft 365 ログイン → SharePoint ドキュメント / PHOTO_V2 · v0.3.29 まで HANNYU_TOOL) / 'local' (127.0.0.1 サーバー or フォルダ選択 · プレビュー) */
C01.SOURCE = {
  mode: 'graph',
  pollMs: 30000,          /* 他の人の確認を 30 秒ごとに読む (決定 #100) */
  graphEnabled: true,     /* R7A (決定 #132 · #137): ログインボタン有効 — false に戻すとログインボタン無効 · graph 呼び出し 0 */
  /* v0.3.30 (R8U Part A · 決定 #251): 読む・書く場所 = PHOTO_V2 の 1 か所 (_data · 写真 · 搬入票 · _unassigned · _hold · _fax_unmatched · _actions · AI 相談)。
     ドキュメント ライブラリからの相対パス。元に戻す = 'HANNYU_TOOL' (エンジン設定 sp_tool_root も同時に戻す) */
  spRoot: '古紙/-. 古紙書類/▲ LEENAI 通関作業中/PHOTO_V2',
  spLabel: 'PHOTO_V2'     /* 画面に出す名前 (長いパスの代わり) */
};

/* v0.2.0 (R6): Compass入力 · 催促 は下書き・比較表だけ。送信ボタンは常に無効 (R7 以降 · 決定のあと) */
C01.SEND = {
  /* v0.3.19 (R7T 決定 #190): Compass入力 = 実際に入力 (graph モード · ログインした人のトークン = その人の権限 · 記録 + 元に戻す)。
     false = 比較表だけ (DRY · 送信ボタン無効) */
  compass: true,
  /* v0.3.22 (R7V Part B · 決定 #191): 催促 = 下書き → 担当者が「送信」。remindTest = 試験モード (件名 [test] · 宛先 = エンジン remind.json send_mode.to 1 件だけ)。
     11/24 の実際の送信への切り替えは 管理者の確認の後 (この版には 実際の宛先へ送るコードが無い — remindTest: false にすると 送信ボタンが消えるだけ) */
  remind: true,
  remindTest: true
};

/* v0.2.1 (R6.6): Compass入力 比較の規則 — 決定 D-11 待ち。ここだけ変える (エンジン設定 compass_follow_same_cond_slot と同じ名前・同じ規則)
   follow_same_cond_slot: true = 入れる CT が同じブッキングの同一条件の別の枠に既にあれば、その枠で比較・入力 (D-11 (가)) / false = 今のまま (既定) */
C01.COMPASS = {
  follow_same_cond_slot: false,      /* v0.3.24 (R7X Part D-4): 켜지 않음 (v2 単独なら行き違いなし) */
  /* v0.3.24 (R7X Part D · #214): CT が空の枠の 数値 = ブッキング予定値 → 「予定値 → 入力」 (緑 · 警告なし) / 形態は入力しない (保留) */
  plan_fill: true,
  type_input: false,
  /* v0.3.19 (R7T 決定 #190): COMPASS (Dataverse) の場所 — LEENAI_COMMON と同じ環境 · 読み書きは職員トークン (LEENAI.auth.token('dataverse')) */
  dvUrl: 'https://orgde512c6f.crm7.dynamics.com',
  /* 並行期間 (#176): 職員の業務は旧方式のまま — 窓に「試験運用中」 */
  trial: true
};

/* v0.3.2 (R7B): PDF を画面の中に描く pdf.js (cdnjs · 版固定 · LEENAI の他 TOOL と同じ版) */
C01.PDF = {
  lib: 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js',
  worker: 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js'
};

/* v0.3.2 (R7B): 確認・入力 の 未分類 FAX — 受信から faxHideAfterDays 日を過ぎたものは既定の一覧で隠す (隠すだけ · 消さない · 「古い未分類 FAX も表示」で全部)
   受信日 = エンジン queue 項目の received_at (無い項目は隠さない) · 0 = 隠さない */
C01.QUEUE = {
  faxHideAfterDays: 7
};

/* v0.3.25 (R7Z Part A · 決定 #207 · #209 · #210 · #211): 確認・入力 の右の欄 「その他（AIに相談）」 — 質問 = {base}/ask/{日付}/{ask_id}.json ·
   答え = エンジン (RPA PC · claude-sonnet-5-5) が {base}/ask_reply/{ask_id}.json に書く。AI は値を変えない — 答えのボタン = この画面の今のボタンだけ。
   enabled: false = 欄を出さない · trial = 「試験表示」 */
C01.ASK = {
  enabled: true,
  base: '_actions',
  pollMs: 10000,          /* 答え待ちの間だけ 10 秒ごと */
  trial: true
};
