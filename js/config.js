/* ✦ Powered by LEENAI Automation System — C-01 搬入票 TOOL 設定 (この 1 か所だけ)
   - バージョンは TOOL_INFO.version の 1 か所だけ (LEENAI.init がタブ名・ヘッダー・ログイン画面に表示)
   - 運用ルール (D-6) は RULES の 1 か所で切り替え */
'use strict';
window.C01 = window.C01 || {};

C01.TOOL_INFO = {
  sys: 'C-01',
  name: '搬入票',
  version: '0.3.54',
  date: '2026-11-18',
  desc: '実況表 · 確認・入力 · 写真 · Compass入力 · 催促プレビュー（Microsoft 365 でログイン → SharePoint PHOTO_V2 のデータを表示）'
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
  faxLinkIv: true,
  /* ⑧ v0.3.33 (R8Z Part B · #258 補足): 業者・IV 未定 カード = 「業者登録」 (送信元アドレス 1 つ → 業者 · 営業所 · 1 分で分類し直し · 元に戻す) — エンジン actions_register_sender が on の時だけ true */
  registerSender: true,
  /* ⑨ v0.3.40 (R9M Part A · #271 · #272 c): 確認・入力 に 「発信者未登録」 (送信元ごと · 推定 強→弱→なし · 業者登録 · 登録しない · 元に戻す · 枚数は別) — エンジン out_sender_cards が on の時だけ true */
  senderCards: true,
  /* ⑩ v0.3.41 (R9O Part 00-3 · #277): 「発信者未登録」 ② 代わりに送る所 (港運 · 倉庫 · 下請 · register_sender value.relay · 催促の宛先にしない) — エンジン actions_sender_relay が on の時だけ true */
  senderRelay: true,
  /* ⑪ v0.3.46 (R9X Part 00-2 · #295): 未分類FAX 「IVに連結」 = 同じ画面で FAX の値 ↔ IV の行の値 を確かめて 「連結して確認（OK）」 (link_iv + 確認した値) —
        エンジン actions_fax_link_confirm · out_fax_read_rows が on の時だけ true */
  faxLinkConfirm: true,
  /* ⑫ v0.3.49 (R10H Part 1 · #305 ③): CT を修正して 同じ BKG の別の行と同じ CT → 「{n}番の行にまとめる」 確認窓 (書類だけの行 · 値を並べて 違えば赤 + もう一度確認) →
        _actions merge_rows (エンジンが次の判定で まとめる · 元に戻す = 「⋯」) — エンジン s3_human_merge_rows が on の時だけ true */
  mergeRows: true
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
  remindTest: true,
  /* v0.3.37 (R9K Part B-0 · 決定 #270): 本番送信 — エンジン remind.json send_mode {test: false, live: true} の時だけ 「送信」 が出る
     (押した職員のメール · 宛先 = 元請だけ · 固定 CC · 送信直前にもう一度確認 C01.remindCheck)。false = 本番の送信ボタンを出さない */
  remindLive: true
};

/* v0.3.37 (R9K Part A-1 · 決定 #263 · #264): 催促 送信直前の確認 — エンジン notify/remind.guard と同じ決まり (エンジンが下書きに付けた allow を使う)。
   ① 宛先 (To) 1 件以上 ② To · CC (固定 CC を除く) · 確認した未受信 = すべて allow.domains (元請の会社ドメイン) か allow.addrs (元請の無料メール)
   ③ 固定 CC (cc_fixed) が CC に全部ある · To に無い ④ allow が無い下書き = 送らない。戻り = 送れない理由の配列 (空 = 送れる) */
C01.remindCheck = function (d, unOk) {
  var out = [];
  if (!d) return ['下書きがありません'];
  var low = function (a) { return String(a || '').trim().toLowerCase(); };
  var al = d.allow;
  if (!al || !Array.isArray(al.domains) || !Array.isArray(al.addrs)) return ['宛先の確認リストがありません（エンジンの更新を待ってください）'];
  var to = (d.to || []).map(low), cc = (d.cc || []).map(low), fixed = (d.cc_fixed || []).map(low);
  if (unOk) { to = to.concat((d.to_unreceived || []).map(low)); cc = cc.concat((d.cc_unreceived || []).map(low)); }
  to = to.filter(Boolean);
  cc = cc.filter(Boolean);
  if (!to.length) out.push('宛先 (To) がありません');
  if (!fixed.length) out.push('固定 CC がありません');
  fixed.forEach(function (a) {
    if (cc.indexOf(a) < 0) out.push('固定 CC がありません（' + a + '）');
    if (to.indexOf(a) >= 0) out.push('固定 CC が宛先 (To) にあります（' + a + '）');
  });
  var doms = al.domains.map(low), adr = al.addrs.map(low);
  to.concat(cc.filter(function (a) { return fixed.indexOf(a) < 0; })).forEach(function (a) {
    var ok = /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(a) && (adr.indexOf(a) >= 0 || doms.indexOf(a.split('@')[1]) >= 0);
    if (!ok && out.indexOf('元請以外のアドレス（' + a + '）') < 0) out.push('元請以外のアドレス（' + a + '）');
  });
  return out;
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
  /* 並行期間 (#176): compass_done 記録の trial (記録だけ · 入力の動きは同じ) */
  trial: true,
  /* v0.3.50 (R10Q): trialUntil (JST) から 記録の trial = false (11/24 単独運用 · 端末の時間帯に関係なし · C01.compass.trialAt) */
  trialUntil: '2026-11-24T00:00:00+09:00',
  /* v0.3.48 (R10B · #298): 窓の 「試験運用中」 の印 (false = 出さない · 記録の trial とは別) */
  badge: false
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
  trial: false,           /* v0.3.48 (R10B · #298): 「試験表示」 끔 */
  global: true,           /* v0.3.39 (R9L · #273): 右上 「AI 相談」 (画面全体 · 改善依頼 · 依頼一覧) — エンジン ask_global が切れていれば 「準備中」 の答え */
  /* v0.3.46 (R9X Part 0 · #291 ②): 答えの 「この操作をしますか？」 (AI が準備 · 押すのは担当者 · 今のボタンと同じ記録 · 元に戻す) — エンジン ask_proposed_actions */
  propose: true,
  /* v0.3.46 (R9X Part 2 · #291 ④): 答えごとに 「役に立った / 立たなかった」 (_actions ask_feedback · 立たなかった = 自動の改善依頼) — エンジン ask_feedback */
  feedback: true,
  /* v0.3.46 (R9W Part 1-2 · #290): 実況表の行の横の窓にも 「AIに相談」 (確認済 → 再確認 に戻した行など カードの無い行も) */
  rowAsk: true
};
