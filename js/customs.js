/* ✦ Powered by LEENAI Automation System — 通関書類送付 (v0.3.63 · 決定 #359 · #302 · #303 · #306 · #338 · #343 · #352 · v0.3.66 #366 · v0.3.86 #408 · v0.3.87 送付記録 S/I)
   - 実況表 IV 見出しの 「通関書類送付」 (Compass入力 の横) → 確認窓 → 担当者が 「送信」 を押した時だけ 1 通
   - PDF = D-03 自動モード (同じ出所 · ?auto=1 · 押した担当者のログイン · COMPASS は読むだけ)
   - メール = ① 通関依頼 の会話の一番新しいメールに 全員に返信 (押した担当者のメール · js/source.js customsSend)
   - 試験モード (C01.CUSTOMS.sendTest) = 宛先は押した本人 1 人だけ · 件名の前に [test]
   - 送ったら _actions customs_sent (IV · 誰 · いつ · メール ID · PDF sha256 · 選んだ値)
   v0.3.68 (R12Y7 · #367): 宛先の道 (route) — ① 自分のメールボックスの ① に 全員に返信 (s1_reply) → ② 無ければ 会社のメールボックスの ① の会話
   (エンジン customs_s1.json) と同じ宛先へ 新しいメール · ① を引用 (s1_shared) → ③ (v0.3.85 で無くした · 下を見る)。
   L インボイス (国内販売 · #218) = 送付ボタンの代わりに 「国内販売（通関書類は買い手側）」
   v0.3.76 (R12Y37 · #380): ① 通関業者ごとの 追加書類 (エンジン customs_broker_req.json · 決定 #380 の表) — 写真（PHOTO）・搬入票 が要る通関業者 = 確認窓の一番上に黄色 ·
   既定のボタン = 「下書きで保存」 (送らない · Outlook で添付して送る) · 「送信」 は 「追加書類は別に送ります」 のチェックの後だけ · 表に無い宛先 = 「必要書類を確認してください」。
   ② 「下書きで保存」 = 送信と同じ下書き (宛先 · 件名 · 本文 · PDF を確かめる) を作って 送らない → Outlook で開くリンク · _actions customs_draft · 実況表 「下書き作成済」 →
   その職員の 「通関書類送付_{IV}」 メールをエンジンが見たら 「送付済」 (エンジン iv.customs_mail)。
   ③ (Part 3B · C01.CUSTOMS.shareLink) 写真 · 搬入票 を zip にして 会社の SharePoint (PHOTO_V2/_customs_share) に置き 「リンクを知っている全員」 · 見るだけ · 7 日のリンクを本文に入れて送る —
   'admin_test' = 管理者の 「写真・搬入票リンクの試験」 だけ (宛先 = 自分 1 人 · [test]) · 'on' = 実際の送付 (rpa@ 試験メールの確認の後) · 'off' = 出さない
   v0.3.84 (R12Y59 · #404): COMPASS の booking の 「乙仲」 (cr49f_fowarder_id · 押した職員のログインで読むだけ) を 通関業者の表 (customs_broker_req.json) の名前に合わせる —
   道 1 · 2 = 宛先の通関業者 ≠ 乙仲 なら 赤 + 「宛先を確認しました」
   v0.3.85 (R12Y60 · #405 · #407): 道 3 (この港へ最近送った宛先 の提案) を無くした — ① (B-03 の件名 · 前の形 · 会社のメールボックス) が見つからない =
   宛先 · 宛名 は空 + 赤 「新規通関依頼メールが見つかりません — 担当（宛先）が分かりません」 · 職員が入れる (manual · 「宛先を確認しました」 の後 · 乙仲 と違えば 赤) ·
   宛名 = ① のあいさつ · 同じ会話 · この IV の送付記録 だけ (ほかの IV · 港 · 乙仲 の記録は使わない) */
'use strict';
window.C01 = window.C01 || {};

C01.customs = (function () {
  var A = null;
  function api() { return A || (A = C01.app._api()); }
  function on() { return !!(C01.CUSTOMS && C01.CUSTOMS.enabled); }
  /* v0.3.76: 管理者のリンク試験 = 試験モード · v0.3.78 (R12Y40 · #383): 下書き (forDraft) は 送らないので 試験の印を付けない (宛先は実際の値のまま) */
  function testMode(forDraft) { return !(C01.CUSTOMS && C01.CUSTOMS.sendTest === false) || (!forDraft && !!(st && st.shareTest)); }
  var BL_LABEL = { original: 'Original B/L', waybill: 'WAY BILL', surrender: 'SURRENDER' };
  var BL_CLS = { ORIG: 'original', WAY: 'waybill', SUR: 'surrender', original: 'original', waybill: 'waybill', surrender: 'surrender' };

  /* ── 送付の記録 (エンジン iv.customs_sent + 自分 · 他の人の _actions) — 新しい順 ── */
  function records(iv, kind) {
    kind = kind || 'customs_sent';                       /* v0.3.76 (R12Y37 · #380 ②): customs_draft (下書きで保存) も同じ形 */
    var S = api().S, xs = [], seen = {};
    ((iv && iv[kind]) || []).forEach(function (x) { seen[x.action_id] = 1; xs.push({ action_id: x.action_id, by: x.by, at: x.at, value: x.value || {} }); });
    (S.actions || []).concat(S.mine || []).forEach(function (x) {
      var a = x.action || x;
      if (a.action === kind && iv && a.iv === iv.iv_no && !seen[a.action_id]) { seen[a.action_id] = 1; xs.push({ action_id: a.action_id, by: a.by, at: a.at, value: a.value || {} }); }
    });
    return xs.sort(function (a, b) { return String(b.at).localeCompare(String(a.at)); });
  }
  /* v0.3.76 (R12Y37 · #380 ②): エンジンが見た 「通関書類送付_{IV}」 メール (自社 · RE/FW でない · [test] を除く) — 新しい順 */
  function mailSeen(iv) {
    return ((iv && iv.customs_mail) || []).filter(function (x) { return !x.test; }).slice().sort(function (a, b) { return String(b.at).localeCompare(String(a.at)); });
  }
  /* v0.3.81 (R12Y52 · #400 後続 · エンジン out_customs_prev_iv): IV 番号が変わった (リブッキング · 同じブッキング) — 前の IV で送った記録 (新しい順) */
  function prevSent(iv) {
    return ((iv && iv.customs_prev_iv) || []).slice().sort(function (a, b) { return String(b.at).localeCompare(String(a.at)); });
  }
  function prevText(p) {
    return '前の IV (' + p.iv + ') で ' + api().md(String(p.at).slice(0, 10)) + ' 送付済 · IV 番号が変わりました · 再送が必要か確認';
  }
  function lastDraft(iv) { return records(iv, 'customs_draft').filter(function (x) { return !x.value.test; })[0] || null; }
  function lastLive(iv) { return records(iv).filter(function (x) { return !x.value.test; })[0] || null; }
  function lastTest(iv) { return records(iv).filter(function (x) { return x.value.test; })[0] || null; }

  /* ── v0.3.88 (R12Y67 · #411): 輸出許可書 (エンジン iv.permit · meta.permit) — 実況表 IV 見出しの 「通関書類 送付済」 の横 · 表示だけ (判定 · 送付 · 値 は変えない)
     ok = 許可書あり (緑 「✓ 許可 MM/DD」 · 変更通知 = 「· 変更 MM/DD」) · check = 許可書らしい書類をエンジンが決められない (zip のパスワード · IV が違う · 読み取り不確か → 橙 「許可書 確認」) ·
     wait = 送付済 · まだ届かない (灰 「許可待ち」) · none = CY CUT を過ぎても無い (赤 「許可なし」) · L インボイス · エンジンが許可書を見ていない時 (meta.permit 無し) = 出さない ── */
  var PERMIT_WHY = { zip_password: 'zip のパスワード', text_iv_differs: '書類の IV が件名と違う', text_iv_missing: '書類に IV が無い', ai_unsure_or_iv: '読み取りが不確か',
    scan_need_ai: 'まだ読めていない', name_permit_text_other: 'ファイル名は許可書 · 中身は別の書類', subject_iv_missing: '件名に IV が無い' };
  var PERMIT_HOW = { text: 'PDF の文字', name: 'ファイル名', ai: '画像の読み取り (AI)', human: '人の確認待ち' };
  function permitOn() { var m = api().S.meta; return !!(m && m.permit && m.permit.on); }
  /* v0.3.89 (R12Y68 · #413 형님 「CUT 당일 오전부터 주황 · 17시까지 없으면 빨강」): CUT 당일 = 「許可待ち（本日CUT）」 橙 → 17:00 (meta.permit.none_hour) から 「許可なし」 赤 ·
     許可書 確認 (エンジンが決められない) は CUT 当日 17:00 から 赤い枠 · 対象 = 送付済 IV (送付前 · L インボイス = 出さない) */
  function noneHour() { var m = api().S.meta; return (m && m.permit && m.permit.none_hour) || (C01.PERMIT && C01.PERMIT.noneHour) || '17:00'; }
  function permitState(iv) {
    if (!iv || !permitOn() || domestic(iv)) return null;
    var p = iv.permit || null, nh = (p && p.need_human) || [];
    if (p && p.kind) return { st: 'ok', p: p, check: nh.length > 0 };
    var cut = iv.cy_cut ? String(iv.cy_cut).slice(0, 10) : '', today = api().todayJst();
    var sent = !!(lastLive(iv) || mailSeen(iv)[0]), late = !!cut && cut === today && api().nowHm() >= noneHour();
    if (nh.length) return { st: 'check', p: p, late: late && sent };
    if (cut && cut < today) return { st: 'none', p: p };
    if (!sent) return null;
    if (cut === today) return late ? { st: 'none', p: p, today: true } : { st: 'wait_cut', p: p };
    return { st: 'wait', p: p };
  }
  function permitNh(p) {
    return ((p && p.need_human) || []).map(function (x) {
      return (x.kind === 'CHANGE' ? '変更通知 — ' : '') + (PERMIT_WHY[x.why] || x.why) + ' (' + String(x.received_at || '').slice(0, 16).replace('T', ' ') + ' 受信)';
    }).join(' · ');
  }
  function permitBadge(g) {
    var a = api(), esc = a.esc, iv = g.iv, s = permitState(iv);
    if (!s) return '';
    var p = s.p || {}, md = function (x) { return a.md(String(x || '').slice(0, 10)); }, at = ' data-permit="' + esc(iv.iv_no) + '"';
    var chk = function (lead) { return '<button class="c01-permit c01-permit-chk"' + at + ' data-permit-chk title="' + esc(lead + permitNh(p) + ' — 通関業者のメールを確認してください') + '">許可書 確認</button>'; };
    if (s.st === 'ok') {
      var t = (p.kind === 'PERMIT' ? '輸出許可書 ' : '許可内容変更通知 ') + String(p.received_at || '').slice(0, 16).replace('T', ' ') + ' 受信' + (p.decl_no ? ' · 申告番号 ' + p.decl_no : '') +
        (p.permit_date ? ' · 許可年月日 ' + p.permit_date : '') + ' — 押すと許可書を開けます（表示だけ）';
      var main = p.kind === 'PERMIT' ? '✓ 許可 ' + esc(md(p.received_at)) + (p.change || []).map(function (c) { return ' · 変更 ' + esc(md(c.received_at)); }).join('') :
        '✓ 変更通知 ' + esc(md(p.received_at));
      return '<button class="c01-permit c01-permit-ok"' + at + ' data-permit-ok title="' + esc(t) + '">' + main + '</button>' + (s.check ? chk('ほかに エンジンが決められない書類があります — ') : '');
    }
    if (s.st === 'check') return s.late ? chk('本日 CY CUT · ' + noneHour() + ' を過ぎました — ').replace('c01-permit c01-permit-chk"', 'c01-permit c01-permit-chk c01-permit-late"') :
      chk('輸出許可書らしい書類が届きましたが エンジンが決められません — ');
    if (s.st === 'none') return s.today ?
      '<span class="c01-permit c01-permit-none" data-permit-none data-permit-today title="本日 CY CUT · ' + esc(noneHour()) + ' を過ぎても 輸出許可書 が届いていません（通関業者に確認 · エンジンの見落としの可能性 — 管理者へ）">許可なし</span>' :
      '<span class="c01-permit c01-permit-none" data-permit-none title="CY CUT を過ぎても 輸出許可書 のメールが見つかりません（通関業者の返信 · エンジンの見落としの可能性 — 管理者へ）">許可なし</span>';
    if (s.st === 'wait_cut') return '<span class="c01-permit c01-permit-cut" data-permit-wait-cut title="本日 CY CUT · 輸出許可書 はまだ届いていません — ' + esc(noneHour()) + ' までに届かなければ 「許可なし」（赤）">許可待ち（本日CUT）</span>';
    return '<span class="c01-permit c01-permit-wait" data-permit-wait title="通関書類は送付済 · 輸出許可書はまだ届いていません（通関業者の返信を待っています）">許可待ち</span>';
  }
  function openPermit(ivNo) {
    var a = api(), esc = a.esc, iv = a.ivById(ivNo), p = (iv && iv.permit) || {}, fs = p.files || [];
    var dt = function (x) { return String(x || '').slice(0, 16).replace('T', ' '); };
    var row = function (k, v) { return v ? '<tr><th>' + esc(k) + '</th><td>' + esc(v) + '</td></tr>' : ''; };
    var html = '<div class="c01-mh"><b>輸出許可書</b><span class="mono">' + esc(ivNo) + '</span><span class="t2">BKG ' + esc(iv ? iv.bkg_no : '') + '</span>' +
      '<span class="c01-flex"></span><button class="c01-btn-ghost2" data-close>閉じる</button></div><div class="c01-mb">' +
      '<table class="c01-permit-tbl" data-permit-tbl>' +
      row('受信', p.received_at ? dt(p.received_at) + (p.n > 1 ? '（許可書 ' + p.n + ' 通 · 開くのは最後のもの）' : '') : '') + row('申告番号', p.decl_no) + row('許可年月日', p.permit_date) +
      row('見つけ方', PERMIT_HOW[p.how] || p.how) +
      (p.change || []).map(function (c) { return row('変更通知', dt(c.received_at) + ' 受信'); }).join('') +
      (p.need_human || []).map(function (x) { return row('要確認', (x.kind === 'CHANGE' ? '変更通知 — ' : '') + (PERMIT_WHY[x.why] || x.why) + ' · ' + dt(x.received_at) + ' 受信'); }).join('') +
      '</table>' +
      (fs.length ? '<ul class="c01-customs-list">' + fs.map(function (f, i) {
        return '<li><button class="c01-btn-sub" data-permitopen="' + i + '">開く</button> <span>' + esc(f.name) + '</span></li>';
      }).join('') + '</ul>' : '<p class="c01-note2">開けるファイルがありません（zip のパスワード · IV が違う などは 通関業者のメールで確認してください）</p>') +
      '<p class="c01-note2">表示だけです（搬入票の値 · 判定には使いません）。許可書の中身（申告の内容）の確認はまだありません。</p></div>';
    a.showModal(html);
    document.getElementById('c01-modal').querySelectorAll('[data-permitopen]').forEach(function (b) { b.onclick = function () { a.openTab(fs[+b.getAttribute('data-permitopen')].path); }; });
  }

  /* ── v0.3.89 (R12Y68 · #412 · #414): 許可書の内容 (エンジン iv.permit.check · meta.permit.check) — 12/03 まで 管理者だけ (meta.permit.staff = 職員にも)
     closed = ✓ 終結 (緑) · kubun = 許可済（区分2/3）— 確認 (橙 · 1 クリック) · diff = 許可書 相違 (赤 · 項目の表 + PDF) · hyoki = 表記確認 (橙 · 同じ意味 / 違う) ·
     unread · no_ours · reopened = 内容 確認できず (橙) · 区分 メール (許可書の前) = 区分2 橙 / 区分3 赤 · 写真未送付 赤 · 記録 = _actions permit_ok (元に戻す = undo) ── */
  var CK_FIELD_JA = { '仕向人住所': '仕向人住所', '品目数量の合計': '品目の数量の合計' };
  var CK_R = { '相違': '相違', '처음보는다름': '表記確認', '読めず': '読めず', '相違?': '相違' };
  var CK_WHY = { no_ours: '当社の書類 (IV · PL · S/I) が見つかりません', unread: '許可書の項目を読めません', reopened: '輸出取止め の後の許可書がまだありません' };
  function checkOn() {
    var m = api().S.meta, p = m && m.permit;
    return !!(p && p.on && p.check && (p.staff || p.check === 'live' && p.staff || (api().isAdmin && api().isAdmin())));
  }
  function ckActs(ivNo) {
    /* エンジンの記録 (iv.permit.check.acts) + 自分 · 他の人の _actions (permit_ok) − 元に戻した (undo) */
    var S = api().S, iv = api().ivById(ivNo), c = (iv && iv.permit && iv.permit.check) || {}, xs = [], seen = {}, undone = {};
    (S.actions || []).concat(S.mine || []).forEach(function (x) { var a = x.action || x; if (a.action === 'undo' && a.value && a.value.action_id) undone[a.value.action_id] = 1; });
    (c.acts || []).forEach(function (a) { seen[a.action_id] = 1; if (!undone[a.action_id]) xs.push({ action_id: a.action_id, kind: a.kind, field: a.field || null, by: a.by, at: a.at }); });
    (S.actions || []).concat(S.mine || []).forEach(function (x) {
      var a = x.action || x;
      if (a.action === 'permit_ok' && a.iv === ivNo && !seen[a.action_id] && !undone[a.action_id]) { seen[a.action_id] = 1; xs.push({ action_id: a.action_id, kind: (a.value || {}).kind, field: (a.value || {}).field || null, by: a.by, at: a.at }); }
    });
    return xs;
  }
  function ckState(iv) {
    if (!iv || !checkOn() || domestic(iv)) return null;
    var c = iv.permit && iv.permit.check;
    if (!c || c.past_cut) return null;
    var acts = ckActs(iv.iv_no), st = c.st;
    var has = function (k, f) { return acts.some(function (a) { return a.kind === k && (f === undefined || a.field === f); }); };
    if (st === 'kubun' && has('kubun')) st = 'closed_kubun';
    if (st === 'hyoki') {
      var left = (c.fields || []).filter(function (f) { return f.r === '처음보는다름'; }).map(function (f) { return f.f; });
      if (left.some(function (f) { return has('diff', f); })) st = 'diff';
      else if (left.length && left.every(function (f) { return has('same', f); })) st = 'closed';
    }
    return { st: st, c: c, acts: acts };
  }
  function permitCheckBadge(g) {
    var a = api(), esc = a.esc, iv = g.iv, s = ckState(iv);
    if (!s) return '';
    var c = s.c, at = ' data-permitck="' + esc(iv.iv_no) + '"', out = '', km = c.kubun_mail;
    if (km && s.st !== 'closed' && s.st !== 'closed_kubun') {
      out += '<button class="c01-permit ' + (km.level === 3 ? 'c01-permit-none' : 'c01-permit-chk') + '"' + at + ' data-permit-kubun-mail title="通関業者のメール ' + esc(String(km.at || '').slice(0, 16).replace('T', ' ')) +
        ' — 区分' + km.level + (km.level === 3 ? '（検査）。検査指定票 · 検査日 · 費用 · CUT に間に合うか確認' : '（税関審査）。バンニング写真の送付を確認') + '">区分' + km.level + '</button>';
      if (km.photo === 'missing') out += '<button class="c01-permit c01-permit-none"' + at + ' data-permit-photo-missing title="区分のメールから ' + 30 + ' 分 · 当社の写真の送付が見つかりません">区分' + km.level + ' の写真未送付</button>';
    }
    if (s.st === 'closed' || s.st === 'closed_kubun') out += '<button class="c01-permit c01-permit-ok"' + at + ' data-permit-closed title="許可書の内容 = 当社の書類と一致' + (s.st === 'closed_kubun' ? ' · 区分' + esc(c.kubun) + ' 確認済' : '') + ' — 押すと項目の表">✓ 終結</button>';
    else if (s.st === 'kubun') out += '<button class="c01-permit c01-permit-chk"' + at + ' data-permit-kubun title="許可済ですが 区分' + esc(c.kubun) + '（審査 · 検査あり）— 担当が確認すると 終結">許可済（区分' + esc(String(c.kubun || '').slice(0, 1)) + '）— 確認</button>';
    else if (s.st === 'diff') out += '<button class="c01-permit c01-permit-none"' + at + ' data-permit-diff title="許可書の内容が違います — 押すと項目の表 · 通関業者に訂正を依頼">許可書 相違</button>';
    else if (s.st === 'hyoki') out += '<button class="c01-permit c01-permit-chk"' + at + ' data-permit-hyoki title="初めて見る表記 — 同じ意味か 違うか を選んでください">表記確認</button>';
    else if (CK_WHY[s.st]) out += '<button class="c01-permit c01-permit-chk"' + at + ' data-permit-unread title="' + esc(CK_WHY[s.st] + (c.why ? ' (' + c.why + ')' : '')) + '">内容 確認できず</button>';
    return out;
  }
  function ckWrite(ivNo, v) {
    var a = api();
    return a.writeAction(a.mkAction('permit_ok', { iv: ivNo, ct: null, field: null, source: null, value: v })).then(function () { a.toast('記録しました（反映は数分以内）'); openPermitCheck(ivNo); });
  }
  function ckUndo(ivNo, aid) {
    var a = api();
    return a.writeAction(a.mkAction('undo', { iv: ivNo, ct: null, field: null, source: null, value: { action_id: aid } })).then(function () { a.toast('元に戻しました'); openPermitCheck(ivNo); });
  }
  function openPermitCheck(ivNo) {
    var a = api(), esc = a.esc, iv = a.ivById(ivNo), s = ckState(iv);
    if (!s) return;
    var c = s.c, fs = (iv.permit && iv.permit.files) || [], dt = function (x) { return String(x || '').slice(0, 16).replace('T', ' '); };
    var by = function (k, f) { return s.acts.filter(function (x) { return x.kind === k && (f === undefined || x.field === f); }).slice(-1)[0]; };
    var undoBtn = function (x) { return x ? ' <span class="c01-note2">' + esc(a.staffName ? a.staffName(x.by) : x.by) + ' ' + esc(dt(x.at)) + '</span> <button class="c01-btn-ghost2" data-ckundo="' + esc(x.action_id) + '">元に戻す</button>' : ''; };
    var head = { closed: '✓ 終結 — 許可書の内容 = 当社の書類', closed_kubun: '✓ 終結 — 区分' + (c.kubun || '') + ' 確認済', kubun: '許可済（区分' + (c.kubun || '') + '）— 担当の確認で 終結',
      diff: '許可書の内容が違います — 通関業者に訂正を依頼してください', hyoki: '初めて見る表記があります — 同じ意味か 違うか', unread: CK_WHY.unread, no_ours: CK_WHY.no_ours, reopened: CK_WHY.reopened, before: '許可書はまだです' }[s.st] || '';
    var rows = (c.fields || []).map(function (f) {
      var lab = CK_R[f.r] || f.r, btn = '';
      if (f.r === '처음보는다름') {
        var sm = by('same', f.f), df = by('diff', f.f);
        btn = sm ? '同じ意味' + undoBtn(sm) : df ? '違う' + undoBtn(df) :
          '<button class="c01-btn-sub" data-cksame="' + esc(f.f) + '">同じ意味（登録）</button> <button class="c01-btn-sub" data-ckdiff="' + esc(f.f) + '">違う（相違）</button>';
      }
      return '<tr><th>' + esc(CK_FIELD_JA[f.f] || f.f) + '</th><td>' + esc(f.p || '—') + '</td><td>' + esc(f.o || '—') + '</td><td class="' + (f.r === '相違' ? 'c01-ck-red' : 'c01-ck-or') + '">' + esc(lab) + '</td><td>' + btn + '</td></tr>';
    }).join('');
    var km = c.kubun_mail, kub = by('kubun');
    var html = '<div class="c01-mh"><b>許可書の内容</b><span class="mono">' + esc(ivNo) + '</span><span class="t2">' + esc(head) + '</span>' +
      '<span class="c01-flex"></span><button class="c01-btn-ghost2" data-close>閉じる</button></div><div class="c01-mb">' +
      (km ? '<p class="c01-note2" data-ck-kubun-mail>区分' + km.level + ' のメール ' + esc(dt(km.at)) + ' · 写真 ' + (km.photo === 'sent' ? '送付済 ' + esc(dt(km.photo_at)) : km.photo === 'missing' ? '<b class="c01-ck-red">未送付</b>' : '待ち') + '</p>' : '') +
      (s.st === 'kubun' ? '<p><button class="c01-btn-pri" data-ckkubun>区分' + esc(c.kubun || '') + ' を確認しました（終結）</button></p>' : '') +
      (s.st === 'closed_kubun' && kub ? '<p class="c01-note2">区分' + esc(c.kubun || '') + ' 確認' + undoBtn(kub) + '</p>' : '') +
      (rows ? '<table class="c01-permit-tbl c01-ck-tbl" data-ck-tbl><tr><th>項目</th><th>許可書</th><th>当社 (IV · PL · S/I · COMPASS)</th><th>判定</th><th></th></tr>' + rows + '</table>' :
        '<p class="c01-note2">主な項目 ' + (c.main_ok || 0) + ' / 10 一致（表記の違いを含む）</p>') +
      (c.n_change ? '<p class="c01-note2">許可内容変更通知 ' + c.n_change + ' 通 — 本船 · 仕向地 は変更後の値で確認</p>' : '') +
      (c.vessel_src === 'compass' ? '<p class="c01-note2">本船 = COMPASS の最新と確認</p>' : '') +
      (s.st === 'diff' ? '<p class="c01-note2">相違 = 通関業者に訂正（内容変更）を依頼してください。理由がわかっている時は そのままで構いません（記録だけ）。</p>' : '') +
      (fs.length ? '<ul class="c01-customs-list">' + fs.map(function (f, i) { return '<li><button class="c01-btn-sub" data-ckopen="' + i + '">開く</button> <span>' + esc(f.name) + '</span></li>'; }).join('') + '</ul>' : '') +
      '<p class="c01-note2">表示だけです（搬入票の値 · 判定には使いません）。12/03 までは 管理者だけに表示しています。</p></div>';
    a.showModal(html);
    var m = document.getElementById('c01-modal');
    m.querySelectorAll('[data-ckopen]').forEach(function (b) { b.onclick = function () { a.openTab(fs[+b.getAttribute('data-ckopen')].path); }; });
    m.querySelectorAll('[data-ckundo]').forEach(function (b) { b.onclick = function () { ckUndo(ivNo, b.getAttribute('data-ckundo')); }; });
    var fld = function (n) { return (c.fields || []).filter(function (f) { return f.f === n; })[0] || {}; };
    m.querySelectorAll('[data-cksame]').forEach(function (b) { b.onclick = function () { var f = fld(b.getAttribute('data-cksame')); ckWrite(ivNo, { kind: 'same', field: f.f, p: f.p || null, o: f.o || null }); }; });
    m.querySelectorAll('[data-ckdiff]').forEach(function (b) { b.onclick = function () { var f = fld(b.getAttribute('data-ckdiff')); ckWrite(ivNo, { kind: 'diff', field: f.f, p: f.p || null, o: f.o || null }); }; });
    var kb = m.querySelector('[data-ckkubun]');
    if (kb) kb.onclick = function () { ckWrite(ivNo, { kind: 'kubun', kubun: c.kubun || null }); };
  }

  /* ── ボタンの条件 (実況表の値だけ · ① · S/I · COMPASS の値は押した後の確認窓で) ── */
  function lacks(g) {
    var out = [], iv = g.iv;
    var rows = (g.rows || []).filter(function (x) { return x.kind !== 'missing'; });
    var nMiss = (iv.mail_missing || []).length;
    var notOk = rows.filter(function (x) { return !(x.st === '自動OK' || x.st === '確認済'); }).length;
    if (g.okN !== g.total) out.push(g.okN + '/' + g.total + '台');
    if (notOk) out.push('未完了 ' + notOk + '台');
    if (nMiss) out.push('メール未着 ' + nMiss + '台');
    if (g.overA !== undefined ? g.overA : g.over) out.push('枠外 ' + (g.overA !== undefined ? g.overA : g.over));
    if (g.overB) out.push('枠未定 ' + g.overB);              /* v0.3.65 (R12Y Part 1) */
    if (rows.some(function (x) { return x.dup_ct; })) out.push('CT重複');
    if (rows.some(function (x) { return x.dup_seal; })) out.push('シール重複');
    if (!g.compassDone) out.push('Compass入力未完了 ' + rows.filter(function (x) { return !x.frozen; }).length + '台');
    else if (C01.COMPASS && C01.COMPASS.form_bales && api().compassRecords) {          /* v0.3.65 (R12Y · #361): Compass入力 の記録 (入力の後に読んだ) 形態 · タイプ 空欄 */
      var cr = api().compassRecords(iv)[0];
      var fb = cr && cr.value ? cr.value.formtype_blank : undefined;
      if (typeof fb === 'number' && fb > 0) out.push('形態・タイプ 空欄 ' + fb + '台');
    }
    if (!iv.bkg_no) out.push('BKG なし');
    return out;
  }
  /* v0.3.68 (R12Y7 · #367 Part 1): L インボイス = 国内販売 (#218 · 荷主 = 買い手 · S/I なし · 通関は買い手側) — 6 か月の送付 0 件 */
  function domestic(iv) {
    var pre = (C01.CUSTOMS && C01.CUSTOMS.domesticPrefix) || 'L';
    return String((iv && iv.iv_no) || '').toUpperCase().indexOf(pre) === 0;
  }
  var DOM_TEXT = '国内販売（L インボイス）です。荷主は買い手で、通関は買い手側の通関業者が行います — S/I はなく、こちらから 通関書類 を送りません。';
  function headerBtn(g) {
    if (!on()) return '';
    var a = api(), iv = g.iv, esc = a.esc;
    if (domestic(iv)) return '<button class="c01-csend-dom" data-csend="' + esc(iv.iv_no) + '" data-csend-off="1" title="' + esc(DOM_TEXT) + '">国内販売（通関書類は買い手側）</button>';
    a.S.customsG = a.S.customsG || {};
    a.S.customsG[iv.iv_no] = g;
    var l = lastLive(iv), t = lastTest(iv);
    if (l) return '<button class="c01-done c01-csent" data-csend="' + esc(iv.iv_no) + '" title="' + esc('通関書類 送付済 ' + String(l.at).slice(0, 16).replace('T', ' ') + ' · ' + a.staffName(l.by) + ' — 押すと記録 · 再送付') + '">✓ 通関書類 送付済 ' + esc(a.md(String(l.at).slice(0, 10))) + ' · ' + esc(a.staffName(l.by)) + '</button>';
    var ms = mailSeen(iv)[0];            /* v0.3.76: TOOL の記録が無くても 職員のメール (下書き → Outlook で送った · 手で送った) を見たら 送付済 */
    if (ms) return '<button class="c01-done c01-csent" data-csend="' + esc(iv.iv_no) + '" data-csent-mail="1" title="' + esc('通関書類送付 のメール ' + String(ms.at).slice(0, 16).replace('T', ' ') + ' · ' + (a.staffName(ms.from) || ms.from) + '（エンジンが受信したメール）— 押すと記録 · 再送付') + '">✓ 通関書類 送付済 ' + esc(a.md(String(ms.at).slice(0, 10))) + ' · ' + esc(a.staffName(ms.from) || ms.from) + '</button>';
    var dr = lastDraft(iv);
    var dmark = dr ? ' <small class="c01-cdraftmark" data-cdraftmark title="' + esc('下書きを保存 ' + String(dr.at).slice(0, 16).replace('T', ' ') + ' · ' + a.staffName(dr.by) + ' — Outlook で送ると 送付済 になります') + '">下書き作成済 ' + esc(a.md(String(dr.at).slice(0, 10))) + ' · ' + esc(a.staffName(dr.by)) + '</small>' : '';
    var miss = lacks(g);
    var pv = prevSent(iv)[0];            /* v0.3.81 (R12Y52): この IV の送付記録 · メールが無く 前の IV で送っていたら 黄色 (二重送付の警告ではない) */
    if (pv) dmark += ' <small class="c01-cprev" data-cprev title="' + esc(prevText(pv) + ' — ' + String(pv.at).slice(0, 16).replace('T', ' ') + ' · ' + (a.staffName(pv.by) || pv.by)) + '">' + esc(prevText(pv)) + '</small>';
    var tmark = dmark + (t ? ' <small class="c01-ctest" title="' + esc('試験送付 ' + String(t.at).slice(0, 16).replace('T', ' ') + ' · ' + a.staffName(t.by)) + '">試験済 ' + esc(a.md(String(t.at).slice(0, 10))) + '</small>' : '');
    if (miss.length) return '<button class="c01-blocked c01-csend-off" data-csend="' + esc(iv.iv_no) + '" data-csend-off="1" title="' + esc('まだ送れません: ' + miss.join(' · ')) + '">通関書類送付</button>' + tmark;
    return '<button class="c01-btn-pri c01-csend" data-csend="' + esc(iv.iv_no) + '" title="D-03 で IV・PL・SI を作り、① 通関依頼 の宛先へ送ります（送る前に確認窓）">✉ 通関書類送付</button>' + tmark;
  }

  /* ── COMPASS (読むだけ) — バイヤー · 前回の B/L ── */
  function dvGet(path) {
    var base = (C01.COMPASS && C01.COMPASS.dvUrl) || '';
    return LEENAI.auth.token('dataverse').then(function (tok) {
      return fetch(base + '/api/data/v9.2/' + path, { headers: { Authorization: 'Bearer ' + tok, Accept: 'application/json', 'OData-MaxVersion': '4.0', 'OData-Version': '4.0' } });
    }).then(function (r) { if (!r.ok) throw new Error('COMPASS ' + r.status); return r.json(); });
  }
  /* ── v0.3.84 (R12Y59 · #404): COMPASS の booking の 乙仲 (読むだけ) ──
     state: 'read' (名前あり) | 'blank' (乙仲 空欄) | 'noname' (乙仲 はあるが名前を読めない) | 'error' (booking を読めない) */
  var BC_NAV = 'cr49f_fowarder_id';
  function brokerCompass(ivNo) {
    var q = "cr49f_bookings?$filter=cr49f_invoice_no eq '" + String(ivNo).replace(/'/g, "''") + "'&$select=_cr49f_fowarder_id_value";
    var first = function (j) { return ((j && j.value) || [])[0] || null; };
    return dvGet(q + '&$expand=' + BC_NAV + '($select=crcf9_forwarder,crcf9_forwarder_to_email)').then(function (j) {
      var b = first(j);
      if (!b) return { state: 'error', why: 'booking なし' };
      if (!b._cr49f_fowarder_id_value) return { state: 'blank' };
      var x = b[BC_NAV] || {};
      var nm = String(x.crcf9_forwarder || '').trim();
      return nm ? { state: 'read', name: nm, email: String(x.crcf9_forwarder_to_email || '') } : { state: 'noname' };
    }, function () {
      return dvGet(q).then(function (j) {
        var b = first(j);
        return !b ? { state: 'error', why: 'booking なし' } : b._cr49f_fowarder_id_value ? { state: 'noname' } : { state: 'blank' };
      }, function (e) { return { state: 'error', why: e.message }; });
    });
  }
  /* 乙仲 の名前 → 通関業者の表の名前 (同じ · 片方が片方を含む · 「/」 で区切った別名 · 株式会社 などを除く) + COMPASS の 乙仲 アドレス → 表 */
  function normCo(s) {
    return String(s || '').normalize('NFKC').toLowerCase().replace(/株式会社|有限会社|\(株\)|\(有\)|co\.,?\s*ltd\.?|inc\./g, '').replace(/[\s\u3000・·.,，、]/g, '');
  }
  function bcAddrs(bc) { return String((bc && bc.email) || '').split(/[\s,;、，]+/).map(function (x) { return x.trim().toLowerCase(); }).filter(function (x) { return ADDR_RE.test(x); }); }
  function matchBroker(rq, bc) {
    var out = [];
    if (!rq || !bc || bc.state !== 'read') return out;
    var put = function (b) { if (b && out.indexOf(b) < 0) out.push(b); };
    var k = normCo(bc.name);
    (rq.brokers || []).forEach(function (b) {
      String(b.name || '').split('/').map(normCo).filter(function (x) { return x.length >= 2; }).forEach(function (al) {
        if (k.length >= 2 && (al === k || al.indexOf(k) >= 0 || k.indexOf(al) >= 0)) put(b.name);
      });
    });
    bcAddrs(bc).forEach(function (ad) { var hit = (rq.addrs || {})[ad] || (rq.domains || {})[domOf(ad)]; if (hit) put(hit.broker); });
    return out;
  }
  /* 確認窓の 乙仲: brokers = 表の名前 (0 = 表で分からない) */
  function bcNow() {
    var bc = st && st.bc;
    if (!bc) return { state: 'none', name: '', brokers: [] };
    return { state: bc.state, name: bc.name || '', brokers: matchBroker(api().S.customsReq, bc) };
  }
  /* 宛先の通関業者 と 乙仲 を比べる — bad = 乙仲 に無い 宛先の通関業者 · noKnown = 宛先の通関業者が表で 1 つも分からない */
  function bcCheck(rc) {
    var b = bcNow();
    if (!st || !st.route || !b.brokers.length) return { on: false, b: b, mismatch: false };
    var q = reqOf(rc || recips());
    var bad = q.brokers.filter(function (x) { return b.brokers.indexOf(x) < 0; });
    var noKnown = !q.brokers.length;
    return { on: true, b: b, q: q, bad: bad, noKnown: noKnown, mismatch: bad.length > 0 || noKnown };
  }
  /* v0.3.66 (R12Y3 · #366 ①): 販売契約 (SC) を 1 回だけ読み、バイヤーと S/I (POD 1/2/3 · B/L 用 POD · Port of Discharge) を一緒に読む。
     S/I が読めない = si null (確認窓は番号だけ + 黄色 · 送信は止めない — D-03 が PDF に入れた値が正本) */
  var SI_SEL = 'crcf9_sino,crcf9_place_of_delivery_1,crcf9_place_of_delivery_2,crcf9_place_of_delivery_3,crcf9_pod_bl1,crcf9_pod_bl2,crcf9_pod_bl3,crcf9_port_of_discharge';
  function contractOf(ivNo) {
    return dvGet("cr49f_bookings?$filter=cr49f_invoice_no eq '" + String(ivNo).replace(/'/g, "''") + "'&$select=_cr49f_sale_contract_id_value").then(function (j) {
      var b = (j.value || [])[0], sc = b && b._cr49f_sale_contract_id_value;
      if (!sc) return { buyer: '', si: null, sc: '', scNo: '', scIvs: null };
      var pB = dvGet('cr49f_sale_contracts(' + sc + ')?$select=_cr49f_buyer_id_value,cr49f_sale_contract_no').then(function (s) { return { buyer: s._cr49f_buyer_id_value || '', no: s.cr49f_sale_contract_no || '' }; }, function () { return { buyer: '', no: '' }; });
      var pS = dvGet('cr49f_s_is?$filter=_cr49f_sale_contract_id_value eq ' + sc + '&$select=' + SI_SEL).then(function (r) { return r.value || []; }, function () { return null; });
      /* v0.3.86 (R12Y63 · #408): 同じ販売契約の IV (ブッキング) — 読めない = null (B/L は空欄 · 赤) */
      var pI = dvGet('cr49f_bookings?$filter=_cr49f_sale_contract_id_value eq ' + sc + '&$select=cr49f_invoice_no').then(function (r) {
        return (r.value || []).map(function (b) { return String(b.cr49f_invoice_no || '').trim(); }).filter(Boolean);
      }, function () { return null; });
      return Promise.all([pB, pS, pI]).then(function (r) { return { buyer: r[0].buyer, si: r[1], sc: sc, scNo: r[0].no, scIvs: r[2] }; });
    }).catch(function () { return { buyer: '', si: null, sc: '', scNo: '', scIvs: null }; });
  }
  /* Consignee の前回 (D-03 prevCons · 同じバイヤー) = TOOL の送付記録 (customs_sent · 試験は除く) だけ — v0.3.86 (R12Y63 · #408): 6 か月の customs_bl.json は使わない (B/L にも使わない) */
  function consHistory(buyer, ivNo) {
    var S = api().S, out = [];
    ((S.jik && S.jik.ivs) || []).forEach(function (iv) {
      records(iv).forEach(function (r) { var v = r.value; if (!v.test && v.buyer_id === buyer && iv.iv_no !== ivNo) out.push({ at: r.at, cons: v.consignee || '' }); });
    });
    return out.sort(function (a, b) { return String(a.at).localeCompare(String(b.at)); });
  }
  /* v0.3.86 (R12Y63 · #408): B/L 形態の既定 = 同じ販売契約の 前に送った IV (TOOL の送付記録 customs_sent · 試験は除く · picks.bl) — 同じ契約 = 条件は同じ (#408)。
     バイヤーの 6 か月の実績 (#338 · customs_bl.json) は使わない (会社ごとに違う · #369 · #408)。エンジンの 手で送った 送付済 (#380) は B/L が分からないので使わない。
     IV ごとに 一番新しい記録 1 つ · 契約の中で 2 つ以上違う = 空欄 + 赤 · 無い = 空欄 + 赤。 */
  function contractBlHistory(scIvs, ivNo) {
    var a = api(), out = [];
    (scIvs || []).forEach(function (no) {
      if (!no || no === ivNo) return;
      var iv = a.ivById(no) || { iv_no: no };
      var r = records(iv).filter(function (x) { return !x.value.test && BL_CLS[x.value.bl]; })[0];
      if (r) out.push({ iv: no, at: r.at, bl: BL_CLS[r.value.bl] });
    });
    return out.sort(function (x, y) { return String(x.at).localeCompare(String(y.at)); });
  }
  /* v0.3.86 (R12Y63 · #408 Part 2): D-00 書類ツール の 契約ごとの B/L 形態 (共用ファイル) — エンジン meta.customs_contract_bl がある時だけ読む (今は無い = Part 1 だけ)。
     形 (仮 · D-00 の回答で決める): { contracts: { "{販売CO}": { bl: "WAY" | "ORIG" | "SUR" | "waybill" ... } } } */
  function d00Bl(scNo) {
    var x = api().S.customsContractBl, c = scNo && x && x.contracts && x.contracts[scNo];
    var v = c && BL_CLS[c.bl];
    return v ? { v: v, why: 'D-00 の契約の値（' + scNo + '）' } : null;
  }
  var BL_ASK = 'B/L 形態を選んでください';
  function pickBl(ct, ivNo) {
    ct = ct || {};
    var d = d00Bl(ct.scNo);
    if (d) return d;
    if (!ct.sc || !ct.scIvs) { var w0 = '販売契約を読めません'; return { v: '', why: w0, red: BL_ASK + '（' + w0 + '）' }; }
    var h = contractBlHistory(ct.scIvs, ivNo);
    if (!h.length) { var w1 = '同じ契約の送付記録がありません'; return { v: '', why: w1, red: BL_ASK + '（' + w1 + '）' }; }
    var kinds = {};
    h.forEach(function (x) { kinds[x.bl] = 1; });
    if (Object.keys(kinds).length > 1) { var w2 = '同じ契約で B/L 形態が違います'; return { v: '', why: w2, red: w2 }; }
    var last = h[h.length - 1];
    return { v: last.bl, why: '同じ販売契約（' + (ct.scNo || '—') + '）の前回 ' + last.iv + ' と同じ' };
  }

  /* ── D-03 自動モード (同じ出所の画面の中) ── */
  var frame = null, frameP = null;
  function d03() {
    if (frameP) return frameP;
    var url = (C01.CUSTOMS && C01.CUSTOMS.d03Url) || '';
    frameP = new Promise(function (ok, ng) {
      frame = document.createElement('iframe');
      frame.id = 'c01-d03auto';
      frame.setAttribute('aria-hidden', 'true');
      frame.style.cssText = 'position:fixed;left:-12000px;top:0;width:1200px;height:1600px;border:0;opacity:0;pointer-events:none';
      frame.src = url + (url.indexOf('?') >= 0 ? '&' : '?') + 'auto=1';
      document.body.appendChild(frame);
      var t0 = Date.now();
      (function wait() {
        var w = null;
        try { w = frame.contentWindow && frame.contentWindow.D03AUTO; } catch (e) { ng(new Error('D-03 を開けません（同じ出所ではありません）')); return; }
        if (w) { ok(w); return; }
        if (Date.now() - t0 > 45000) { ng(new Error('D-03 の自動モードが応答しません（45 秒）')); return; }
        setTimeout(wait, 300);
      })();
    });
    frameP.catch(function () { frameP = null; if (frame) { frame.remove(); frame = null; } });
    return frameP;
  }
  function runD03(o) { return d03().then(function (w) { return w.run(o); }); }
  /* v0.3.87 (R12Y64B): 送付記録だけ — D-03 の 既定の S/I (担当者が選ぶ前) · 候補の数 · 既定の出処 · 変えたか を残す。
     画面 · 既定の決め方 · メール · 宛先 · 添付 は 変えない。手元に無い値は null (作らない)。 */
  function siDefKeep(r) {
    var P = r.picks || {};
    if (st.over.ivSino == null && P.ivSino) st.siDefIv = { v: P.ivSino.v == null ? null : P.ivSino.v, why: String(P.ivSino.why || '') };
    if (st.over.siSino == null && P.siSino) st.siDefSi = { v: P.siSino.v == null ? null : P.siSino.v, why: String(P.siSino.why || '') };
  }
  /* 既定 (IV·PL) の出処 → 短いコード (SI 側は D-03 がいつも S/I①) */
  function siWhyCode(why, n) {
    why = String(why || '');
    if (why.indexOf('三国間') >= 0) return 'three_party';
    if (why.indexOf('残る S/I') >= 0) return 'no_rest';
    if (!why || why.indexOf('S/I がありません') >= 0) return 'none';
    if (n === 1) return 'only_one';
    if (why.indexOf('最終番号') === 0) return 'last_no';
    return 'other';
  }
  function siRec(r, s) {
    var P = (r && r.picks) || {}, dI = s && s.siDefIv, dS = s && s.siDefSi;
    var n = r && Array.isArray(r.si_avail) ? r.si_avail.length : null;
    var fI = P.ivSino ? P.ivSino.v : null, fS = P.siSino ? P.siSino.v : null;
    var ch = dI && dS ? (fI !== dI.v || fS !== dS.v) : null;
    return { si_default_iv: dI ? dI.v : null, si_default_si: dS ? dS.v : null, si_avail_n: n,
      si_why: ch === true ? 'staff_changed' : dI ? siWhyCode(dI.why, n) : null, si_changed: ch };
  }

  /* ── COMPASS (D-03 が読んだ値) = 実況表の値 ── */
  function normCt(s) { return String(s || '').replace(/[\s-]/g, '').toUpperCase(); }
  function cmpCompass(g, info) {
    var out = [];
    var rows = (g.rows || []).filter(function (x) { return x.kind !== 'missing' && !x.over; });
    var cs = (info && info.containers) || [];
    var byCt = {};
    cs.forEach(function (c) { byCt[normCt(c.ct)] = c; });
    if (cs.length !== rows.length) out.push('COMPASS のコンテナ ' + cs.length + ' 行 · 実況表 ' + rows.length + ' 行');
    rows.forEach(function (x) {
      var v = x.vals || {}, c = byCt[normCt(v.ct)];
      if (!c) { out.push((v.ct || '（CT なし）') + ' が COMPASS にありません'); return; }
      if (normCt(c.seal) !== normCt(v.seal)) out.push(v.ct + ' シール 実況表 ' + (v.seal || '—') + ' · COMPASS ' + (c.seal || '—'));
      [['n_w', 'nw', '正味'], ['t_w', 'tw', '風袋'], ['bales', 'bales', 'ベール']].forEach(function (f) {
        var a = v[f[0]], b = c[f[1]];
        if (a != null && a !== '' && Number(a) !== Number(b)) out.push(v.ct + ' ' + f[2] + ' 実況表 ' + a + ' · COMPASS ' + (b == null ? '—' : b));
      });
    });
    return out;
  }

  /* ── 本文 ── */
  function fill(t, m) { return String(t || '').replace(/\{(\w+)\}/g, function (x, k) { return m[k] != null ? m[k] : x; }); }
  var BROKER_PH = '（通関業者の会社名）', PERSON_PH = '（担当者名）';
  /* v0.3.66 (R12Y3 · #366 ②): 本文の先頭の あいさつ (会社名 / 〇〇 様) を読む — エンジン engine/output/customs_broker.py greeting() と同じ決まり
     (先頭 6 行 · 「いつも」 などの前まで · 「様」 で終わる最初の行 = 担当者 · その上の行 (2 行まで · ※ などの注意書きは除く) = 会社名) */
  var CO_RE = /(株式会社|㈱|有限会社|合同会社|\(株\)|（株）|Co\.,?\s*Ltd|CO\.,?\s*LTD|Corporation|Corp\.|Inc\.|LIMITED|Ltd\.)/i;
  var STOP_RE = /^(いつも|お世話|お疲れ|平素|大変お世話)/, SKIP_RE = /^[※*＊■□●◆【\[〔>＞-]/, SAMA_RE = /\s*(様|さま)\s*$/;
  function glines(t) {
    return String(t || '').replace(/[\u200b\ufeff]/g, '').replace(/[\u3000\u00a0]/g, ' ').split(/\r?\n/).map(function (x) { return x.trim(); }).filter(Boolean);
  }
  function greeting(text) {
    var ls = [], all = glines(text).slice(0, 6);
    for (var k = 0; k < all.length; k++) { if (STOP_RE.test(all[k])) break; ls.push(all[k]); }
    var i = -1;
    for (k = 0; k < ls.length; k++) { if (SAMA_RE.test(ls[k])) { i = k; break; } }
    if (i < 0) return { company: '', person: '' };
    var person = ls[i].replace(SAMA_RE, '').trim();
    var above = ls.slice(0, i).filter(function (x) { return !SKIP_RE.test(x) && x.indexOf('様') < 0; }).slice(-2);
    var company = above.join('\n');
    if (!above.length && CO_RE.test(person) && /\s/.test(person)) {
      var m = /^(.*\S)\s+(\S+)$/.exec(person);
      if (m) { company = m[1]; person = m[2]; }
    }
    if (person.length > 40 || company.length > 80) return { company: '', person: '' };
    return { company: company.trim(), person: person.trim() };
  }
  function domOf(a) { return String(a || '').toLowerCase().split('@')[1] || ''; }
  function normName(s) { return String(s || '').replace(/[\s\u3000]/g, '').toLowerCase(); }
  /* 宛名を探す順 (先に見つかったもの · 会社名と担当者はそれぞれ):
     ① ① の会話で 自社の職員が書いた一番新しいメールの あいさつ (宛先に 同じ通関業者のドメインがある時だけ)
     ② TOOL の送付記録 (customs_sent · 試験を除く · 同じドメイン) の 1 行目 · 2 行目 — v0.3.85 (R12Y60 · #405): この IV の記録だけ
     ③ (v0.3.85 で無くした: ほかの IV の 職員が手で送った 「通関書類送付」 = 同じ通関業者でも 別の港 · 別の担当 (LOTOS TOKYO の担当が OSAKA に出た))
     ④ 通関業者のメールの署名の会社名の行 (確認窓を開いた後に 1 通だけ読む) + 送信者の表示名
     ⑤ 見つからない = 書き換え用の印 (残っていたら送れない) */
  function brokerGuess(mail) {
    var a = api(), S = a.S, last = mail && mail.last, s1 = mail && mail.s1;
    var our = String(C01.CUSTOMS.ourDomain || 'leenearcorp.com').toLowerCase();
    var me = String((S.me || {}).email || '').toLowerCase();
    var ext = [].concat(last ? [{ a: last.from, n: last.from_name }] : [], (last && last.to) || [], (s1 && s1.to) || []).filter(function (x) { return x.a && domOf(x.a) !== our; });
    var p = ext[0] || { n: '', a: '' };
    var dom = domOf(p.a);
    var out = { broker: '', person: '', dom: dom, src: { broker: '', person: '' } };
    var put = function (co, ps, src) {
      if (co && !out.broker) { out.broker = co; out.src.broker = src; }
      if (ps && !out.person) { out.person = ps; out.src.person = src; }
    };
    if (dom) {
      // ①
      var conv = ((mail && mail.conv) || []).slice().reverse();
      for (var i = 0; i < conv.length && !(out.broker && out.person); i++) {
        var m = conv[i];
        if (domOf(m.from) !== our) continue;
        if (![].concat(m.to || [], m.cc || []).some(function (x) { return domOf(x.a) === dom; })) continue;
        var g = greeting(m.preview);
        if (!g.company && !g.person) continue;
        put(g.company, g.person, '① の会話（' + (m.from === me ? 'あなた' : (a.staffName(m.from) || m.from_name || m.from)) + 'のメール ' + a.md(String(m.at).slice(0, 10)) + '）');
      }
      // ②
      var rec = null;
      ((S.jik && S.jik.ivs) || []).forEach(function (iv) {
        if (!st || iv.iv_no !== st.iv) return;
        records(iv).forEach(function (r) { if (!r.value.test && r.value.broker_dom === dom && r.value.broker_line && (!rec || String(r.at) > String(rec.at))) rec = r; });
      });
      if (rec) put(rec.value.broker_line, rec.value.broker_person || '', 'TOOL の送付記録（' + a.md(String(rec.at).slice(0, 10)) + '）');
    }
    return out;
  }
  /* ④ 通関業者のメールの署名 (本文の会社名の行 · 一番下のもの) + 送信者の表示名 — ①〜③ で足りない時だけ (GET 1 回) */
  function sigCompany(text) {
    var ls = glines(text).filter(function (x) { return x.length <= 60 && CO_RE.test(x) && !/様/.test(x); });
    return ls.length ? ls[ls.length - 1].replace(/^[\s\-_=*■□●◆|]+|[\s\-_=*■□●◆|]+$/g, '') : '';
  }
  function cleanName(n) { return String(n || '').replace(/\s*[<(（\[].*$/, '').replace(/[\s\u3000]*(様|さま)$/, '').trim(); }
  function brokerSig(mail, gs) {
    var a = api(), src = a.S.src;
    if ((gs.broker && gs.person) || !gs.dom || !mail || typeof src.customsMailText !== 'function') return Promise.resolve(gs);
    var bm = ((mail.conv || []).slice().reverse().filter(function (m) { return domOf(m.from) === gs.dom; }))[0] ||
      (!(mail.conv || []).length && mail.last && domOf(mail.last.from) === gs.dom ? mail.last : null);     /* v0.3.68: 道 2 = 会社のメールボックスの ① の最新 (本文の GET はしない) */
    if (!bm) return Promise.resolve(gs);
    var nm = cleanName(bm.from_name);
    if (!gs.person && nm && nm.indexOf('@') < 0) { gs.person = nm; gs.src.person = '通関業者のメールの送信者名（' + a.md(String(bm.at).slice(0, 10)) + '）'; }
    if (gs.broker || !bm.id) return Promise.resolve(gs);
    return src.customsMailText(bm.id).then(function (t) {
      var co = sigCompany(t);
      if (co) { gs.broker = co; gs.src.broker = '通関業者のメールの署名（' + a.md(String(bm.at).slice(0, 10)) + '）'; }
      return gs;
    }, function () { return gs; });
  }
  function bodyText(st) {
    var me = api().S.me || {};
    var C = C01.CUSTOMS;
    return fill(C.body, { broker: st.broker || BROKER_PH, person: st.person || PERSON_PH }) + '\n\n' + fill(C.signature, { name: me.name || '', email: me.email || '' }) + '\n\n' + C.footer;
  }
  function bodyHtml(txt) {
    return '<div style="font-family:\'Meiryo\',\'Yu Gothic\',sans-serif;font-size:10.5pt">' + api().esc(txt).replace(/\n/g, '<br>') + '</div>';
  }

  /* ── 確認窓 ── */
  var st = null;
  function open(ivNo, off) {
    var a = api();
    var iv = a.ivById(ivNo), g = (a.S.customsG || {})[ivNo];
    if (!on() || !iv || !g) return;
    if (domestic(iv)) { a.toast(DOM_TEXT, 'info'); return; }
    if (off) { a.toast('まだ送れません: ' + lacks(g).join(' · '), 'error'); return; }
    st = { iv: ivNo, g: g, step: '準備中', mail: null, sent: [], d03: null, err: [], bl: '', blWhy: '', over: {}, ack: false, again: false, busy: false, body: null, broker: '', person: '',
      si: undefined, nameSrc: null, sendErr: '', route: '', shared: null, prop: null, addStaff: true, editTo: '', editCc: '', ackTo: false,
      extraAck: false, draftDone: null, shareTest: false, ph: null, shareStep: '', bc: null, noRouteWhy: '' };
    a.S.modal = { kind: 'customs', iv: ivNo };
    draw();
    var src = a.S.src;
    var graphOk = a.graphMode() && typeof src.customsFindS1 === 'function';
    var pMail = graphOk ? src.customsFindS1(iv.bkg_no, ivNo).catch(function (e) { st.err.push('① の検索: ' + e.message); return null; }) : Promise.resolve(null);
    var pSent = graphOk ? src.customsFindSent(ivNo).catch(function () { return []; }) : Promise.resolve([]);
    /* customs_bl.json = エンジンの meta.customs_bl がある時だけ読む (無いエンジンに 404 を出さない) */
    /* v0.3.86 (R12Y63 · #408): customs_bl.json (6 か月) は読まない · D-00 の契約ごとの値 = エンジンの meta.customs_contract_bl がある時だけ (今は無い) */
    var pBl = (a.S.customsContractBl === undefined && a.S.meta && a.S.meta.customs_contract_bl ? src.getJson(String(a.S.meta.customs_contract_bl)).then(function (x) { a.S.customsContractBl = x; }, function () { a.S.customsContractBl = null; }) : Promise.resolve())
      .then(function () { return graphOk ? contractOf(ivNo) : { buyer: '', si: null, sc: '', scNo: '', scIvs: null }; });
    /* v0.3.66 (R12Y3 · #366 ②): customs_broker.json = エンジンの meta.customs_broker がある時だけ読む */
    var pCb = a.S.customsBroker === undefined && a.S.meta && a.S.meta.customs_broker ? src.getJson(String(a.S.meta.customs_broker)).then(function (x) { a.S.customsBroker = x; }, function () { a.S.customsBroker = null; }) : Promise.resolve();
    /* v0.3.65 (R12Y · #361): 形態 · タイプ 空欄の枠 (CT が入った枠だけ · COMPASS GET だけ) — 読めない = null (送信を止める) */
    var pFt = C01.COMPASS && C01.COMPASS.form_bales ? (graphOk && iv.booking_guid ? dvGet('crcf9_container_informations?$select=crcf9_container_no,crcf9_type,_crcf9_form_value&$filter=' +
      encodeURIComponent('_crcf9_booking_id_value eq ' + iv.booking_guid)).then(function (j) {
      var cells = {}; (j.value || []).forEach(function (c, i) { cells[i] = c; }); return C01.compass.formTypeBlank(cells);
    }).catch(function () { return null; }) : Promise.resolve(null)) : Promise.resolve(0);
    /* v0.3.68 (R12Y7 · #367 Part 2): customs_s1.json = エンジンの meta.customs_s1 がある時だけ読む (会社のメールボックスの ① · 最近の宛先) */
    var pS1 = a.S.meta && a.S.meta.customs_s1 ? src.getJson(String(a.S.meta.customs_s1)).then(function (x) { a.S.customsS1 = x; }, function () { a.S.customsS1 = a.S.customsS1 || null; }) : Promise.resolve();
    /* v0.3.76 (R12Y37 · #380 ①): customs_broker_req.json = エンジンの meta.customs_broker_req がある時だけ読む (無い = 案内なし · 今までどおり) */
    var pReq = a.S.customsReq === undefined && a.S.meta && a.S.meta.customs_broker_req ? src.getJson(String(a.S.meta.customs_broker_req)).then(function (x) { a.S.customsReq = x; }, function () { a.S.customsReq = null; }) : Promise.resolve();
    /* v0.3.76 (#380 ③): 写真 · 搬入票 の一覧 (_data/photos/{IV}.json · 枚数 · 大きさ) — リンク送付の時だけ使う */
    /* v0.3.84 (R12Y59 · #404): COMPASS の 乙仲 (道を決める前に読む) */
    var pBc = graphOk ? brokerCompass(ivNo).then(function (x) { if (st && st.iv === ivNo) st.bc = x; }) : Promise.resolve();
    var pPh = shareCfg() !== 'off' ? src.getJson('photos/' + ivNo + '.json').then(function (x) { if (st && st.iv === ivNo) st.ph = x; }, function () { if (st && st.iv === ivNo) st.ph = null; }) : Promise.resolve();
    Promise.all([pMail, pSent, pBl, pFt, pCb, pS1, pReq, pPh, pBc]).then(function (r) {
      if (!st || st.iv !== ivNo) return;
      st.mail = r[0]; st.sent = r[1] || []; st.buyer = (r[2] || {}).buyer || ''; st.si = (r[2] || {}).si; st.ftBlank = r[3];
      st.sc = (r[2] || {}).sc || ''; st.scNo = (r[2] || {}).scNo || '';
      pickRoute(iv);
      var pb = pickBl(r[2], ivNo);
      st.bl = pb.v; st.blWhy = pb.why; st.blRed = pb.red || '';
      var h = st.buyer ? consHistory(st.buyer, ivNo) : [];
      st.prevCons = h.length ? (h[h.length - 1].cons || '') : null;
      return brokerSig(mailLike(), brokerGuess(mailLike())).then(function (gs) {
        if (!st || st.iv !== ivNo) return;
        st.broker = gs.broker; st.person = gs.person; st.brokerDom = gs.dom; st.nameSrc = gs.src;
        st.step = 'D-03';
        draw();
        return makePdf();
      });
    }).catch(function (e) { if (st && st.iv === ivNo) { st.err.push(e.message); st.step = '完了'; draw(); } });
  }
  function makePdf() {
    var ivNo = st.iv;
    st.prevD03 = st.d03 && st.d03.ok ? st.d03 : null;        /* v0.3.74 (R12Y18 Part 1): 作り直し中も前の選択表 · PDF の大きさを残す (位置が動かない) */
    st.step = 'D-03'; st.d03 = null; draw();
    var o = { iv: ivNo, bl: st.bl, blWhy: st.blWhy };
    if (st.prevCons != null) o.prevCons = st.prevCons;
    Object.keys(st.over).forEach(function (k) { o[k] = st.over[k]; });
    return runD03(o).then(function (r) {
      if (!st || st.iv !== ivNo) return;
      st.d03 = r; st.step = '完了'; st.prevD03 = null;
      if (r && r.ok) siDefKeep(r);
      if (st.pdfUrl) URL.revokeObjectURL(st.pdfUrl);
      st.pdfUrl = null;
      if (r && r.ok) {
        var bin = atob(r.pdf_b64), u8 = new Uint8Array(bin.length);
        for (var i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
        st.pdfUrl = URL.createObjectURL(new Blob([u8], { type: 'application/pdf' }));
      }
      draw();
    }).catch(function (e) { if (st && st.iv === ivNo) { st.d03 = { ok: false, error: e.message }; st.step = '完了'; st.prevD03 = null; draw(); } });
  }
  /* v0.3.70 (R12Y10): エンジン customs_s1 の ① が 会話 (conversationId) ごとに分かれていて 宛先が違う (ambiguous) 時 — 会話を選べる (既定 = 一番新しい ① の会話 = 今までと同じ) */
  function convPicked(sh) {
    var cs = (sh && sh.convs) || [], i;
    for (i = 0; i < cs.length; i++) if (cs[i].picked) return i;
    return -1;
  }
  function convView(sh, i) {
    var cv = sh && sh.convs && i >= 0 ? sh.convs[i] : null;
    if (!cv) return sh;
    return { s1: cv.s1, last: cv.last, staff: cv.staff, staff_name: cv.staff_name, n_conv: cv.n, s1_count: sh.s1_count, n_s1_conv: sh.n_s1_conv, ambiguous: sh.ambiguous, convs: sh.convs };
  }
  function ambOf(ivNo) {
    var S = api().S, sh = S.customsS1 && S.customsS1.ivs && S.customsS1.ivs[ivNo];
    return sh && sh.ambiguous ? sh : null;
  }
  /* v0.3.68 (R12Y7 · #367 Part 2): 宛先の道を決める (確認窓を開いた時 1 回) */
  function pickRoute(iv) {
    if (st.mail) { st.route = 's1_reply'; return; }
    var S = api().S, sh = S.customsS1 && S.customsS1.ivs && S.customsS1.ivs[st.iv];
    if (sh && sh.last) { st.route = 's1_shared'; st.sharedAll = sh; st.convI = convPicked(sh); st.shared = convView(sh, st.convI); return; }
    /* v0.3.85 (R12Y60 · #407): ① が無い = 提案しない · 宛先 · 宛名 は空 (職員が入れる) */
    st.route = 'manual'; st.prop = { src: 'manual', to: [], cc: [] };
    st.editTo = ''; st.editCc = '';
  }
  /* 宛名さがし (brokerGuess) 用 — 道 2 · 3 でも ① と同じ形 */
  function mailLike() {
    if (st.mail) return st.mail;
    if (st.route === 's1_shared') {
      /* v0.3.85 (R12Y60): ① の元のメールのあいさつ (エンジン s1.preview) = 宛名 (同じ会話) */
      var s = st.shared.s1 || {};
      return { s1: { subject: s.subject, to: s.to || [] }, last: st.shared.last,
        conv: s.preview ? [{ from: s.from, from_name: s.from_name, at: s.at, to: s.to || [], cc: s.cc || [], preview: s.preview }] : [] };
    }
    return null;                                             /* manual = ① が無い = 宛名は職員が入れる */
  }
  var ADDR_RE = /^[^@\s,;<>]+@[^@\s,;<>]+\.[^@\s,;<>]+$/;
  function parseAddrs(t) { return String(t || '').split(/[\s,;、，]+/).map(function (x) { return x.trim().toLowerCase(); }).filter(Boolean); }
  function recips() {
    var me = String((api().S.me || {}).email || '').toLowerCase();
    var seen = {};
    var pick = function (xs) { return xs.filter(function (x) { var k = x.a; if (!k || k === me || seen[k]) return false; seen[k] = 1; return true; }); };
    if (st.route === 'manual') {
      return { to: pick(parseAddrs(st.editTo).map(function (a) { return { a: a, n: '' }; })), cc: pick(parseAddrs(st.editCc).map(function (a) { return { a: a, n: '' }; })) };
    }
    var L = st.route === 's1_reply' ? st.mail && st.mail.last : st.route === 's1_shared' ? st.shared.last : null;
    if (!L) return { to: [], cc: [] };
    var b = baseRecips(L, st.route === 's1_reply' ? (st.mail.conv || []) : []);
    var to = pick(b.to);
    var ccs = b.cc.slice();
    /* 道 2: ① の担当職員を CC に (既定 · 外せる) — 他の職員の会話に入るので 担当者にも見えるように */
    if (st.route === 's1_shared' && st.addStaff && st.shared.staff) ccs.push({ a: st.shared.staff, n: st.shared.staff_name || '' });
    var cc = pick(ccs);
    return { to: to, cc: cc, how: b.how };
  }
  /* v0.3.78 (R12Y40 · #383 Part 2): 会話の一番新しいメールを 自社 (社内) の人が送った時 — 全員に返信 だと 送った社内の人が To に入る (11/25 の下書き) →
     その メールの To · CC をそのまま使う (社内の人は CC だけ)。社外の To が 0 = その前の 社外 (通関業者) のメールを 全員に返信 の形で · それでも 0 = そのまま (「宛先を確認しました」 が要る)。
     how: 'reply_all' (今までどおり) | 'ours_last' | 'prev_ext' | 'ours_only' */
  function ourDom() { return String((C01.CUSTOMS && C01.CUSTOMS.ourDomain) || 'leenearcorp.com').toLowerCase(); }
  function isOurs(a) { return domOf(String(a || '').trim().toLowerCase()) === ourDom(); }
  function baseRecips(L, conv) {
    var from = L.from ? [{ a: String(L.from).toLowerCase(), n: L.from_name || '' }] : [];
    var lw = function (xs) { return (xs || []).map(function (x) { return { a: String(x.a || '').toLowerCase(), n: x.n || '' }; }); };
    var split = function (to, cc) {
      return { to: to.filter(function (x) { return !isOurs(x.a); }), cc: to.filter(function (x) { return isOurs(x.a); }).concat(cc) };
    };
    /* v0.3.79 (R12Y42 · #385 ②): 一番新しいメールが 通関業者 でも その To の 社内の人 は CC へ (11/25 NHK の下書き = 通関業者 → 社内の人 To) */
    if (!isOurs(L.from)) { var r0 = split(from.concat(lw(L.to)), lw(L.cc)); return { to: r0.to, cc: r0.cc, how: 'reply_all' }; }
    var s = split(lw(L.to), lw(L.cc));
    if (s.to.length) return { to: s.to, cc: s.cc, how: 'ours_last' };
    var prev = (conv || []).filter(function (m) { return m && m.id !== L.id && !isOurs(m.from) && String(m.at || '') <= String(L.at || ''); })
      .sort(function (x, y) { return String(y.at || '').localeCompare(String(x.at || '')); })[0];
    if (prev) {
      var p = split([{ a: String(prev.from).toLowerCase(), n: prev.from_name || '' }].concat(lw(prev.to)), lw(prev.cc));
      if (p.to.length) return { to: p.to, cc: p.cc.concat(s.cc), how: 'prev_ext' };
    }
    return { to: lw(L.to), cc: lw(L.cc), how: 'ours_only' };
  }
  /* 宛先 (To) に 社内の人 */
  function oursInTo(rc) { return (rc.to || []).filter(function (x) { return isOurs(x.a); }); }
  function stripRe(s) { return String(s || '').replace(/^\s*((re|fw|fwd|返信|転送)\s*[:：]\s*)+/i, '').trim(); }
  function subject(forDraft) {
    var t = (testMode(forDraft) ? '[test] ' : '') + '【通関書類送付_' + st.iv + '】';
    if (st.route === 's1_shared') return t + 'RE: ' + stripRe(st.shared.s1.subject);
    if (st.route === 'manual') { var iv = api().ivById(st.iv) || {}; return t + 'BKG#' + (iv.bkg_no || '') + ' CUT ' + api().md(iv.cy_cut); }
    var s1 = st.mail && st.mail.s1;
    return t + 'Re: ' + (s1 ? stripRe(s1.subject) : '');
  }
  /* 自社の外のドメイン (宛先 · CC) */
  function extDoms(rc) {
    var our = String((C01.CUSTOMS && C01.CUSTOMS.ourDomain) || 'leenearcorp.com').toLowerCase(), d = {};
    rc.to.concat(rc.cc).forEach(function (x) { var k = domOf(x.a); if (k && k !== our) d[k] = 1; });
    return Object.keys(d).sort();
  }
  /* 道 2: 本文の下に ① の一番新しいメールを引用 (エンジンが GET した本文 · 文字) */
  function quoteHtml(L) {
    var esc = api().esc, line = function (xs) { return (xs || []).map(function (x) { return x.n ? x.n + ' <' + x.a + '>' : x.a; }).join('; '); };
    var head = '-----Original Message-----\nFrom: ' + (L.from_name ? L.from_name + ' <' + L.from + '>' : L.from) + '\nSent: ' + String(L.at || '').replace('T', ' ').slice(0, 16) +
      '\nTo: ' + line(L.to) + (L.cc && L.cc.length ? '\nCc: ' + line(L.cc) : '') + '\nSubject: ' + (L.subject || '') + '\n\n';
    return '<div style="font-family:\'Meiryo\',\'Yu Gothic\',sans-serif;font-size:10pt;color:#333;border-top:1px solid #b5c4df;margin-top:12pt;padding-top:6pt">' +
      esc(head + String(L.body || '')).replace(/\n/g, '<br>') + '</div>';
  }
  /* ── v0.3.76 (R12Y37 · #380 ①): 通関業者ごとの 追加書類 — エンジン customs_broker.req_of と同じ決まり (アドレス登録が先 · 次にドメイン · 表に無い社外ドメイン = 要確認) ── */
  var EXTRA_NAME = { PHOTO: '写真（PHOTO）', '搬入票': '搬入票' };
  function reqOf(rc) {
    var rq = api().S.customsReq;
    if (!rq || !rq.domains) return { on: false, extra: [], brokers: [], unknown: [] };
    var our = String((C01.CUSTOMS && C01.CUSTOMS.ourDomain) || 'leenearcorp.com').toLowerCase();
    var ex = [], br = [], unk = [];
    rc.to.concat(rc.cc).forEach(function (x) {
      var ad = String(x.a || '').trim().toLowerCase(), d = domOf(ad);
      if (!d || d === our) return;
      var hit = (rq.addrs || {})[ad] || rq.domains[d];
      if (!hit) { if (unk.indexOf(d) < 0) unk.push(d); return; }
      if (br.indexOf(hit.broker) < 0) br.push(hit.broker);
      (hit.extra || []).forEach(function (k) { if (ex.indexOf(k) < 0) ex.push(k); });
    });
    ex.sort(function (p, q) { return (p === 'PHOTO' ? 0 : 1) - (q === 'PHOTO' ? 0 : 1); });
    return { on: true, extra: ex, brokers: br, unknown: unk };
  }
  function reqNow() { return st && st.route ? reqOf(recips()) : { on: false, extra: [], brokers: [], unknown: [] }; }
  /* v0.3.76 (#380 ③): リンク送付の設定 'off' | 'admin_test' | 'on' */
  function shareCfg() { var v = C01.CUSTOMS && C01.CUSTOMS.shareLink; return v === 'on' || v === 'admin_test' ? v : 'off'; }
  function isAdmin() { return !!(api().S.me && api().S.me.admin); }
  /* リンクで送りたい (設定 'on' = 追加書類の要る通関業者は 全員 既定 · 'admin_test' = 管理者のチェックだけ) */
  function shareWanted() {
    var rq = reqNow();
    if (!rq.extra.length) return false;
    var c = shareCfg();
    return c === 'on' || (c === 'admin_test' && isAdmin() && !!st.shareTest);
  }
  /* v0.3.78 (R12Y40 · #384): リンクを作れない理由 (先に分かるもの) — あれば 0.3.76 の動き (PDF だけ + Outlook で添付) に戻る */
  function shareProblem() {
    if (!st.ph) return '写真・搬入票 の一覧を読めません';
    var sf = shareFiles();
    if (sf.needPhoto && !sf.photos.length) return '写真がありません';
    if (sf.needDocs && !sf.docs.length) return '搬入票がありません';
    return '';
  }
  function shareOn() { return shareWanted() && !st.shareFail && !shareProblem(); }
  /* リンクで送りたいのに 作れない (先に分かった理由 · 作ってみて失敗) = 0.3.76 の動きに戻る */
  function shareFallback() { return shareWanted() && !shareOn(); }
  function shareWhy() { return st.shareFail || shareProblem(); }
  /* リンクを作れなかった記録 (_actions customs_share_error · エンジン · リナイが数える) — 失敗しても 送付 · 下書き は止めない */
  function shareErrRec(mode, stage, msg) {
    var a = api(), rq = reqNow();
    try {
      return a.writeAction(a.mkAction('customs_share_error', { iv: st.iv, ct: null, field: null, source: null,
        value: { mode: mode, stage: stage, msg: String(msg || '').slice(0, 300), extra: rq.extra, test: testMode(mode === 'draft') } })).catch(function () { return null; });
    } catch (e) { return Promise.resolve(null); }
  }
  /* 時間切れ (既定 180 秒) — それ以上待たない */
  function shareTimeoutMs() { var t = Number(C01.CUSTOMS && C01.CUSTOMS.shareTimeoutSec); return (t > 0 && t <= 1800 ? t : 180) * 1000; }
  function withTimeout(p, ms, cancel) {
    return new Promise(function (ok, ng) {
      var done = false, tm = setTimeout(function () { if (!done) { done = true; if (cancel) cancel.v = true; ng(new Error('時間切れ（' + Math.round(ms / 1000) + ' 秒）')); } }, ms);
      p.then(function (v) { if (!done) { done = true; clearTimeout(tm); ok(v); } }, function (e) { if (!done) { done = true; clearTimeout(tm); ng(e); } });
    });
  }
  function shareSumText(sf, days) {
    return (sf.needPhoto ? '写真 ' + sf.photos.length + ' 枚' : '') + (sf.needPhoto && sf.needDocs ? '・' : '') + (sf.needDocs ? '搬入票 ' + sf.docs.length + ' 件' : '') +
      ' · リンク有効 ' + untilMd(days) + ' まで';
  }
  /* 写真 · 搬入票 の一覧 (実況表のこの IV の行の CT · 枠外は除く) */
  function shareFiles() {
    var ph = st.ph || {}, rq = reqNow(), g = st.g || {};
    var cts = {};
    (g.rows || []).filter(function (x) { return x.kind !== 'missing' && !x.over && x.r && x.r.container_id; }).forEach(function (x) { cts[x.r.container_id] = (x.vals || {}).ct || x.r.ct || ''; });
    var photos = [], noPhoto = [], docs = [];
    if (rq.extra.indexOf('PHOTO') >= 0) {
      Object.keys(cts).forEach(function (cid) {
        var c = (ph.containers || []).filter(function (x) { return x.container_id === cid; })[0];
        var ps = (c && c.photos) || [];
        if (!ps.length) noPhoto.push(cts[cid] || cid);
        ps.forEach(function (p) { if (p.path) photos.push({ ct: cts[cid] || (c && c.ct) || 'CT', path: p.path, size: p.size || 0 }); });
      });
    }
    if (rq.extra.indexOf('搬入票') >= 0) (ph.docs || []).forEach(function (d) { if (d.path) docs.push({ path: d.path, size: d.size || 0 }); });
    var sum = function (xs) { return xs.reduce(function (s, x) { return s + (x.size || 0); }, 0); };
    return { photos: photos, docs: docs, noPhoto: noPhoto, photoBytes: sum(photos), docBytes: sum(docs), needDocs: rq.extra.indexOf('搬入票') >= 0, needPhoto: rq.extra.indexOf('PHOTO') >= 0 };
  }
  function mb(n) { return (Math.round(n / 1048576 * 10) / 10) + ' MB'; }
  function shareDays() { var d = Number(C01.CUSTOMS && C01.CUSTOMS.shareDays); return d > 0 && d <= 30 ? d : 7; }
  function untilMd(days) { var d = new Date(Date.now() + days * 864e5 + 9 * 36e5); return (d.getUTCMonth() + 1) + '/' + d.getUTCDate(); }
  /* 送れない理由 (送信ボタンを止める) */
  function blockers() {
    var a = api(), out = [];
    var r = st.d03;
    if (!a.graphMode() || !(a.S.me && a.S.me.email) || typeof a.S.src.customsSend !== 'function') out.push('Microsoft 365 でログインした職員だけ送信できます');
    if (!st.route) out.push('宛先がありません');
    if (st.route === 's1_shared' && !st.shared.last.body_ok) out.push('① の本文をまだ読めていません — 数分後に もう一度開いてください');
    /* v0.3.74 (R12Y18 · #377): 実際の送付 · 道 2 (会社のメールボックスの ①) = 「宛先を確認しました」 のチェックが要る (道 3 = 今までどおり · 道 1 = チェックなし) */
    if (st.route === 's1_shared' && !testMode() && !st.ackTo) out.push('宛先を確認して 「宛先を確認しました」 にチェックしてください');
    if (st.route === 'manual') {
      var badA = parseAddrs(st.editTo).concat(parseAddrs(st.editCc)).filter(function (x) { return !ADDR_RE.test(x); });
      if (badA.length) out.push('アドレスの形が違います（' + badA.join(' / ') + '）');
      if (!st.ackTo) out.push('宛先を確認して 「宛先を確認しました」 にチェックしてください');
    }
    if (!r || !r.ok) out.push('PDF がありません' + (r && r.error ? '（' + r.error + '）' : ''));
    if (r && r.ok) {
      if (r.iv !== st.iv) out.push('D-03 の IV が違います（' + r.iv + '）');
      if (r.file !== st.iv + '_IV_PL_SI.pdf') out.push('添付の名前が違います');
      if (!(r.si_avail || []).length) out.push('S/I がありません');
      if (!r.picks.bl.v) out.push('B/L 形態を選んでください');
      cmpCompass(st.g, r.info).forEach(function (x) { out.push('COMPASS ≠ 実況表: ' + x); });
    }
    if (C01.COMPASS && C01.COMPASS.form_bales) {                     /* v0.3.65 (R12Y · #361): 形態 · タイプ 空欄 0 (確認窓で COMPASS を読む) */
      if (st.ftBlank === null) out.push('形態・タイプ を COMPASS で確認できません');
      else if (st.ftBlank > 0) out.push('形態・タイプ が空欄 ' + st.ftBlank + '台 — Compass入力 で入れてください');
    }
    var rc = recips();
    if (st.route && !rc.to.length) out.push('宛先がありません');
    /* v0.3.78 (R12Y40 · #383 Part 2): 社外の宛先が会話から見つからない (To = 社内の人だけ) = 道 1 でも 「宛先を確認しました」 が要る */
    if (st.route === 's1_reply' && rc.how === 'ours_only' && !testMode() && !st.ackTo) out.push('宛先を確認して 「宛先を確認しました」 にチェックしてください');
    /* v0.3.84 (R12Y59 · #404): 宛先の通関業者 ≠ COMPASS の 乙仲 = 「宛先を確認しました」 が要る (止めない · 乙仲の変更 · 書き間違いもある) */
    var ACK = '宛先を確認して 「宛先を確認しました」 にチェックしてください';
    if (st.route && bcCheck(rc).mismatch && !st.ackTo && out.indexOf(ACK) < 0) out.push(ACK);
    if (/（通関業者の会社名）|（担当者名）/.test(st.body || '')) out.push('本文の （通関業者の会社名） · （担当者名） を書き換えてください');
    if (/このメールは担当者確認後に送信してください/.test(st.body || '')) out.push('本文に 下書きの案内文 が残っています');
    if ((lastLive(a.ivById(st.iv)) || st.sent.some(function (x) { return !x.test; })) && !st.again) out.push('送付済みです — 再送付する時は 「もう一度送る」 にチェック');
    var red = r && r.ok ? r.warnings.filter(function (w) { return w.red; }) : [];
    if (red.length && !st.ack) out.push('赤の警告を確認してチェックしてください');
    if (st.busy) out.push('送信中');
    return out;
  }
  /* v0.3.76 (#380 ②③): 「送信」 だけの追加の理由 (下書きで保存 は blockers() だけ) */
  function sendBlockers() {
    var out = blockers().slice();
    var rq = reqNow();
    /* v0.3.78 (R12Y40 · #384): リンクを作れない時 = 0.3.76 と同じ (「追加書類は別に送ります」 のチェックが要る) */
    if (rq.extra.length && !shareOn() && !st.extraAck) out.push('この通関業者は ' + rq.extra.map(function (k) { return EXTRA_NAME[k] || k; }).join('・') + ' も必要です — 下書きで保存するか 「追加書類は別に送ります」 にチェック');
    return out;
  }
  /* v0.3.78 (R12Y40 · #383): 下書き にも リンク (管理者の試験中も 下書き は作れる · 宛先は実際の値 · 送らない) */
  function draftBlockers() {
    var out = blockers().slice();
    if (st.shareTest && st.route === 's1_shared' && !testMode(true) && !st.ackTo && out.indexOf('宛先を確認して 「宛先を確認しました」 にチェックしてください') < 0) out.push('宛先を確認して 「宛先を確認しました」 にチェックしてください');
    return out;
  }
  /* v0.3.70 (R12Y10): 「宛先を確認」 黄色 — 道 2 = 会話を選ぶ · 道 1 (自分のメールの ① に返信) = 知らせだけ */
  function ambHtml(esc) {
    var a = api();
    if (st.route === 's1_shared' && st.shared && st.shared.ambiguous && (st.shared.convs || []).length) {
      var cs = st.shared.convs;
      return '<div class="c01-camb" data-camb="shared"><b>宛先を確認 — ① のメールが ' + cs.length + ' 件あります</b>（会話ごとに宛先が違います · 既定 = 一番新しい ①）<br>' +
        '<select data-cconv>' + cs.map(function (cv, i) {
          return '<option value="' + i + '"' + (i === st.convI ? ' selected' : '') + '>' + esc(String(cv.s1.at).slice(0, 16).replace('T', ' ') + ' · ' + (cv.staff_name || a.staffName(cv.staff) || cv.staff) +
            ' · 社外ドメイン ' + cv.ext_doms + ' · ' + cv.n + ' 通' + (cv.iv_hit ? ' · IV 番号あり' : '') + (cv.picked ? ' · 既定' : '')) + '</option>';
        }).join('') + '</select></div>';
    }
    var am = st.route === 's1_reply' ? ambOf(st.iv) : null;
    if (am) return '<div class="c01-camb" data-camb="reply"><b>宛先を確認 — ① のメールが ' + (am.n_s1_conv || (am.convs || []).length) + ' 件あります</b>（会社のメールボックス · 会話ごとに宛先が違います · ここでは あなたのメールの一番新しい ① に返信します）</div>';
    return '';
  }
  /* v0.3.84 (R12Y59 · #404): COMPASS の 乙仲 と 宛先 — 合う = 灰色 1 行 · 違う = 赤 · 表で分からない = 黄色 */
  function bcHtml(rc, esc) {
    var b = bcNow();
    if (b.state === 'none') return '';
    if (b.state === 'blank') return '<p class="c01-cy" data-cbc="blank">COMPASS の 乙仲 が空欄です — 宛先の通関業者を確認してください</p>';
    if (b.state === 'noname' || b.state === 'error') return '<p class="c01-cy" data-cbc="' + b.state + '">COMPASS の 乙仲 を読めません' + (st.bc && st.bc.why ? '（' + esc(st.bc.why) + '）' : '') + ' — 宛先の通関業者を確認してください</p>';
    if (!b.brokers.length) return '<p class="c01-cy" data-cbc="unknown">乙仲（COMPASS）: ' + esc(b.name) + ' — 通関業者の表に無い名前です（要確認）</p>';
    var c = bcCheck(rc);
    if (!c.mismatch) return '<p class="t2" data-cbc="ok">乙仲（COMPASS）: ' + esc(b.name) + ' = 宛先の通関業者 ' + esc(c.q.brokers.join(' · ')) + '</p>';
    var to = c.noKnown ? (c.q.unknown.length ? '表に無いドメイン ' + c.q.unknown.join(' · ') : '通関業者が分かりません') : c.q.brokers.join(' · ');
    return '<p class="c01-cr" data-cbc="mismatch"><b>COMPASS の乙仲（' + esc(b.name) + '）と宛先（' + esc(to) + '）が違います</b> — 宛先を確認して 「宛先を確認しました」 にチェックしてください（COMPASS の 乙仲 が違う · 変わった 時もあります）</p>';
  }
  function bcRec() {
    var b = bcNow(), c = bcCheck();
    return b.state === 'none' ? undefined : { state: b.state, name: b.name, brokers: b.brokers, mismatch: c.mismatch || undefined, to_brokers: c.q ? c.q.brokers : undefined };
  }
  function draw() {
    var a = api(), esc = a.esc;
    if (!st || !a.S.modal || a.S.modal.kind !== 'customs') return;
    var iv = a.ivById(st.iv) || {};
    var r = st.d03, ready = st.step === '完了';
    var h = '<div class="c01-mh"><b>通関書類送付</b><span class="mono">' + esc(st.iv) + '</span><span class="t2">BKG ' + esc(iv.bkg_no || '') + ' · CY ' + esc(a.md(iv.cy_cut)) + '</span>' +
      (testMode() ? '<span class="c01-trial" data-ctrial>試験モード（宛先 = あなた 1 人だけ · 件名 [test] · 通関業者には送りません）</span>'
        : '<span class="c01-trial c01-live" data-clive title="押した職員のメールから 下の宛先 (通関業者) へ送ります">実際に通関業者へ送ります</span>') +      /* v0.3.74 (R12Y18 · #377) */
      '<span class="c01-flex"></span><button class="c01-btn-ghost2" data-close>閉じる</button></div><div class="c01-mbody c01-cbody">';
    var regen = !ready && st.step === 'D-03' && !!st.prevD03;
    if (!ready && !regen) {
      h += '<p class="c01-cstep">' + (st.step === 'D-03' ? '⟳ D-03 で IV・PL・SI を作成中…（COMPASS を読むだけ）' : '⟳ ① 通関依頼 メール · 送付記録 を確認中…') + '</p>';
    }
    st.err.forEach(function (e) { h += '<p class="c01-warn2">' + esc(e) + '</p>'; });
    h += reqHtml(esc);
    // 送付済み
    var l = lastLive(iv), sentMail = st.sent.filter(function (x) { return !x.test; });
    var seenM = mailSeen(iv);
    if (!sentMail.length && seenM.length) sentMail = seenM.map(function (x) { return { at: x.at, from: x.from, from_name: a.staffName(x.from) || x.from }; });       /* v0.3.76: エンジンが見たメール */
    var dr0 = lastDraft(iv);
    if (dr0 && !l && !sentMail.length) h += '<div class="c01-cbox c01-cy" data-cdraftrec><b>下書き作成済</b> ' + esc(String(dr0.at).slice(0, 16).replace('T', ' ')) + ' · ' + esc(a.staffName(dr0.by)) +
      ' — まだ送られていません（Outlook の 下書き から送ってください）' + (dr0.value && dr0.value.web_link ? ' <a href="' + esc(dr0.value.web_link) + '" target="_blank" rel="noopener">Outlook で開く</a>' : '') + '</div>';
    var pv0 = prevSent(iv)[0];
    if (pv0 && !l && !sentMail.length) h += '<div class="c01-cbox c01-cy" data-cprevbox><b>' + esc(prevText(pv0)) + '</b> — ' + esc(String(pv0.at).slice(0, 16).replace('T', ' ')) + ' · ' + esc(a.staffName(pv0.by) || pv0.by) +
      '（前の IV ' + esc(pv0.iv) + ' の記録 · 通関業者へ 新しい IV 番号で送り直すか確認してください）</div>';      /* v0.3.81 (R12Y52 · #400 後続) */
    if (l || sentMail.length) {
      h += '<div class="c01-cbox c01-cred"><b>送付済み</b> ' + (l ? esc(String(l.at).slice(0, 16).replace('T', ' ')) + ' · ' + esc(a.staffName(l.by)) + '（記録）' : '') +
        (sentMail.length ? ' · メール ' + sentMail.length + ' 通（' + esc(String(sentMail[0].at).slice(0, 16).replace('T', ' ')) + ' · ' + esc(sentMail[0].from_name || sentMail[0].from) + '）' : '') +
        '<label class="t2"><input type="checkbox" data-cagain' + (st.again ? ' checked' : '') + '> もう一度送る（再送付）</label></div>';
    }
    // 宛先
    var rc = recips();
    var RH = { s1_reply: '宛先（① 通関依頼 の会話の一番新しいメールに 全員に返信）', s1_shared: '宛先（① の会話と同じ宛先へ 新しいメール · ① を引用）', manual: '宛先（入力してください）' };
    h += '<section class="c01-csec" data-croute="' + esc(st.route || (ready ? 'none' : '')) + '"><h4>' + esc(RH[st.route] || '宛先') + '</h4>';
    if (st.route) h += bcHtml(rc, esc);      /* v0.3.84 (R12Y59 · #404): 乙仲 と 宛先 — 宛先の表 · 確認チェックの前 */
    var addrs = function (xs) { return xs.map(function (x) { return esc(x.n ? x.n + ' <' + x.a + '>' : x.a); }).join('<br>') || '—'; };
    if (!ready && !st.route) {
      h += '<p class="t2">確認中…</p>';
    } else if (!st.route) {
      h += '<p class="c01-warn2" data-cnoroute>宛先がありません — 送れません</p>';
    } else if (st.route === 'manual') {
      var bN = bcNow();
      h += '<p class="c01-cr" data-cmanual>新規通関依頼メールが見つかりません — 担当（宛先）が分かりません。宛先と宛名を入力してください' +
        (bN.state === 'read' && bN.name ? '（乙仲（COMPASS）: ' + esc(bN.name) + '）' : '') + '</p>';
      h += '<table class="c01-ctab"><tr><th>To</th><td><textarea class="c01-caddr" data-cedit="to" rows="2">' + esc(st.editTo) + '</textarea></td></tr>' +
        '<tr><th>CC</th><td><textarea class="c01-caddr" data-cedit="cc" rows="3">' + esc(st.editCc) + '</textarea></td></tr></table>' +
        '<p class="t2">アドレスは 「,」 か 改行 で区切ります。</p><label class="c01-cack"><input type="checkbox" data-cackto' + (st.ackTo ? ' checked' : '') + '> 宛先を確認しました</label>';
    } else {
      var L = st.route === 's1_reply' ? st.mail.last : st.shared.last;
      h += ambHtml(esc) + (st.route === 's1_shared' ? '<p class="c01-cy" data-cshared>① は ' + esc(st.shared.staff_name || a.staffName(st.shared.staff) || st.shared.staff) + ' のメールにあります — 新しいメールとして同じ宛先に送ります</p>' : '') +
        '<table class="c01-ctab"><tr><th>To</th><td>' + addrs(rc.to) + '</td></tr><tr><th>CC</th><td>' + addrs(rc.cc) + '</td></tr>' +
        '<tr><th>' + (st.route === 's1_reply' ? '返信先' : '① の最新') + '</th><td class="t2">' + esc(String(L.at).slice(0, 16).replace('T', ' ')) + ' · ' + esc(L.from_name || L.from) + ' · 会話 ' + (st.route === 's1_reply' ? st.mail.n_conv : st.shared.n_conv) + ' 通</td></tr></table>';
      if (st.route === 's1_shared' && st.shared.staff) h += '<label class="t2"><input type="checkbox" data-cstaff' + (st.addStaff ? ' checked' : '') + '> 担当の ' + esc(st.shared.staff_name || st.shared.staff) + ' を CC に入れる</label>';
      if (st.route === 's1_shared' && !st.shared.last.body_ok) h += '<p class="c01-warn2">① の本文をまだ読めていません（エンジンの次の周期で読みます）</p>';
      var needAck = st.route === 's1_shared' || (st.route === 's1_reply' && rc.how === 'ours_only') || bcCheck(rc).mismatch;
      if (needAck && (!testMode() || !testMode(true) || bcCheck(rc).mismatch)) h += '<br><label class="c01-cack"><input type="checkbox" data-cackto' + (st.ackTo ? ' checked' : '') + '> 宛先を確認しました</label>';
    }
    if (st.route) {
      /* v0.3.78 (R12Y40 · #383 Part 2): 会話の一番新しいメールが 社内の人から · To に 社内の人 */
      var HOW = { ours_last: '会話の一番新しいメールは 社内の人が送ったものです — そのメールの To · CC を宛先にしました（社内の人は CC）',
        prev_ext: '会話の一番新しいメールは 社内の人が送ったもので 社外の宛先がありません — その前の 通関業者のメールの宛先にしました（社内の人は CC）',
        ours_only: '会話に 社外の宛先が見つかりません — 宛先を必ず確認してください' };
      if (HOW[rc.how]) h += '<p class="c01-cy" data-chow="' + esc(rc.how) + '">' + esc(HOW[rc.how]) + '</p>';
      var oin = oursInTo(rc);
      if (oin.length) h += '<p class="c01-cy" data-cours>宛先に社内の人が入っています（To: ' + esc(oin.map(function (x) { return x.a; }).join(' · ')) + '）</p>';
      var xd = extDoms(rc);
      if (xd.length >= 2) h += '<p class="c01-cy" data-cdoms>宛先に 会社の外のドメインが ' + xd.length + ' つあります（' + esc(xd.join(' · ')) + '）— 通関業者 以外が入っていないか確認してください</p>';
      if (testMode()) h += '<p class="c01-trial">試験モード: 実際は ' + esc((a.S.me || {}).email || '') + ' だけに送ります（上の宛先には送りません）</p>';
    }
    h += '</section>';
    // 件名 · 本文
    if (st.body == null && st.route && ready) st.body = bodyText(st);
    h += '<section class="c01-csec"><h4>件名</h4><div class="mono c01-csubj">' + esc(st.route ? subject() : '—') + '</div>' +
      '<h4>本文（直せます' + (st.route === 's1_reply' ? ' · 下に 返信の元のメールが付きます' : st.route === 's1_shared' ? ' · 下に ① の一番新しいメールを引用します' : '') + '）</h4>' + nameSrcLine() + '<textarea class="c01-cbodytxt" data-cbody rows="12">' + esc(st.body || '') + '</textarea></section>';
    // 選んだ値
    h += '<section class="c01-csec"><h4>D-03 の選択（既定と理由 · 変えると PDF を作り直します）' + (regen ? ' <span class="c01-cstep" data-cregen>⟳ PDF を作り直し中…</span>' : '') + '</h4>';
    var rv = r || (regen ? st.prevD03 : null);          /* 作り直し中 = 前の表 (押せない) */
    if (rv && rv.ok) {
      var P = rv.picks, av = rv.si_avail || [];
      var dis = regen ? ' disabled' : '';
      var sel = function (k, cur) { return '<select data-cpick="' + k + '"' + dis + '>' + av.map(function (n) { return '<option value="' + n + '"' + (n === cur ? ' selected' : '') + '>S/I' + '①②③④'[n - 1] + '</option>'; }).join('') + '</select>'; };
      h += '<table class="c01-ctab">' +
        '<tr><th>S/I (IV·PL)</th><td>' + sel('ivSino', P.ivSino.v) + '</td><td class="t2' + (P.ivSino.red ? ' c01-cr' : '') + '">' + esc(P.ivSino.why) + '</td></tr>' +
        '<tr><th>S/I (SI)</th><td>' + sel('siSino', P.siSino.v) + '</td><td class="t2' + (P.siSino.red ? ' c01-cr' : '') + '">' + esc(P.siSino.why) + '</td></tr>' +
        '<tr><th>POD</th><td>' + podCell(P) + '</td><td class="t2' + (P.pod.red ? ' c01-cr' : '') + '">' + esc(P.pod.why) + '</td></tr>' +
        '<tr><th>FOB 運賃</th><td><label><input type="checkbox" data-cfreight' + (P.freight.v ? ' checked' : '') + dis + '> 表示</label></td><td class="t2' + (P.freight.red ? ' c01-cr' : '') + '">' + esc(P.freight.why) + '</td></tr>' +
        '<tr><th>B/L 形態</th><td><select data-cbl' + dis + '><option value=""' + (!P.bl.v ? ' selected' : '') + '>（選んでください）</option>' +
        ['original', 'waybill', 'surrender'].map(function (k) { return '<option value="' + k + '"' + (P.bl.v === k ? ' selected' : '') + '>' + BL_LABEL[k] + '</option>'; }).join('') + '</select></td><td class="t2' + (!P.bl.v ? ' c01-cr' : '') + '" data-cblwhy>' + esc(!P.bl.v && st.blRed && st.blWhy !== '担当者が選択' ? st.blRed : st.blWhy) + '</td></tr></table>';
      // 警告
      var W = rv.warnings || [];
      var cmp = cmpCompass(st.g, rv.info);
      if (W.length || cmp.length) {
        h += '<ul class="c01-cwarn">' + W.map(function (w) { return '<li class="' + (w.red ? 'c01-cr' : 'c01-cy') + '">' + esc(w.item) + ': ' + esc(w.text) + '</li>'; }).join('') +
          cmp.map(function (x) { return '<li class="c01-cr">COMPASS ≠ 実況表: ' + esc(x) + '</li>'; }).join('') + '</ul>';
        if (W.some(function (w) { return w.red; })) h += '<label class="c01-cack"><input type="checkbox" data-cack' + (st.ack ? ' checked' : '') + dis + '> 赤の警告を確認しました</label>';
      }
    } else if (r && !r.ok) {
      h += '<p class="c01-warn2">D-03: ' + esc(r.error || '失敗') + '</p>';
    } else h += '<p class="t2">作成中…</p>';
    h += '</section>';
    // PDF
    h += '<section class="c01-csec"><h4>添付 ' + (r && r.ok ? '<span class="mono">' + esc(r.file) + '</span> · ' + r.pages + ' ページ · ' + Math.round(r.bytes / 1024) + ' KB' : '') + '</h4>' +
      (st.pdfUrl && !regen ? '<iframe class="c01-cpdf" title="PDF" src="' + st.pdfUrl + '"></iframe>' : regen ? '<div class="c01-cpdf c01-cpdf-wait">⟳ PDF を作り直し中…</div>' : '<p class="t2">—</p>') + '</section>';
    h += '</div>';
    if (st.sendErr) h = h.replace(/<\/div>$/, '') + '<p class="c01-warn2 c01-csenderr" data-csenderr>送信できませんでした: ' + esc(st.sendErr) + '</p></div>';
    h += footHtml(ready);
    a.showModal(h, 'c01-customs', !!st.drawn);          /* v0.3.74 (R12Y18 Part 1): 2 回目からの描き直し = スクロール位置 · フォーカスそのまま */
    st.drawn = true;
    bind();
  }
  function bind() {
    var m = document.getElementById('c01-modal');
    if (!m) return;
    var q = function (s) { return m.querySelector(s); };
    var ta = q('[data-cbody]');
    if (ta) ta.oninput = function () {
      st.body = ta.value;
      var bl = sendBlockers(), dl = draftBlockers(), go = q('[data-csendgo]'), dg = q('[data-cdraftgo]'), w = q('[data-cwhy]');
      if (go) go.disabled = bl.length > 0;
      if (dg) dg.disabled = dl.length > 0;
      if (w) w.textContent = whyText(bl, dl);
    };
    var xa = q('[data-cextra]');
    if (xa) xa.onchange = function () { st.extraAck = xa.checked; draw(); };
    var stt = q('[data-csharetest]');
    if (stt) stt.onchange = function () { st.shareTest = stt.checked; st.extraAck = false; st.shareFail = ''; draw(); };
    var dgo = q('[data-cdraftgo]');
    if (dgo) dgo.onclick = saveDraft;
    var ag = q('[data-cagain]');
    if (ag) ag.onchange = function () { st.again = ag.checked; draw(); };
    var ak = q('[data-cack]');
    if (ak) ak.onchange = function () { st.ack = ak.checked; draw(); };
    var cvSel = q('[data-cconv]');
    if (cvSel) cvSel.onchange = function () {
      var before = st.body == null || st.body === bodyText(st);
      st.convI = +cvSel.value; st.shared = convView(st.sharedAll, st.convI); st.ackTo = false;      /* 宛先が変わる = もう一度確認 */
      return brokerSig(mailLike(), brokerGuess(mailLike())).then(function (gs) {
        if (!st || st.route !== 's1_shared') return;
        st.broker = gs.broker; st.person = gs.person; st.brokerDom = gs.dom; st.nameSrc = gs.src;
        if (before) st.body = null;              /* 本文を直していなければ 宛名を選んだ会話で作り直す */
        draw();
      });
    };
    var sf = q('[data-cstaff]');
    if (sf) sf.onchange = function () { st.addStaff = sf.checked; st.ackTo = false; draw(); };
    var at = q('[data-cackto]');
    if (at) at.onchange = function () { st.ackTo = at.checked; draw(); };
    m.querySelectorAll('[data-cedit]').forEach(function (el) {
      el.onchange = function () { if (el.getAttribute('data-cedit') === 'to') st.editTo = el.value; else st.editCc = el.value; st.ackTo = false; draw(); };
    });
    m.querySelectorAll('[data-cpick]').forEach(function (el) { el.onchange = function () { st.over[el.getAttribute('data-cpick')] = +el.value; st.ack = false; makePdf(); }; });
    m.querySelectorAll('[data-cpod]').forEach(function (el) {
      el.onchange = function () {
        var v = []; m.querySelectorAll('[data-cpod]').forEach(function (x) { if (x.checked) v.push(+x.getAttribute('data-cpod')); });
        if (!v.length) { el.checked = true; return; }
        st.over.pod = v; st.ack = false; makePdf();
      };
    });
    var fr = q('[data-cfreight]');
    if (fr) fr.onchange = function () { st.over.freight = fr.checked; st.ack = false; makePdf(); };
    var bl = q('[data-cbl]');
    if (bl) bl.onchange = function () { st.bl = bl.value; st.blWhy = bl.value ? '担当者が選択' : st.blWhy; st.ack = false; makePdf(); };
    var go = q('[data-csendgo]');
    if (go) go.onclick = send;
  }
  /* ── v0.3.76 (R12Y37 · #380): 黄色の案内 · ボタン ── */
  function reqHtml(esc) {
    if (!st || !st.route || st.step !== '完了') return '';
    var rq = reqNow();
    if (!rq.on) return '';
    var h = '';
    if (rq.extra.length) {
      var names = rq.extra.map(function (k) { return EXTRA_NAME[k] || k; }).join('・');
      if (shareOn()) {
        var sf = shareFiles(), days = shareDays();
        h += '<div class="c01-cbox c01-cy c01-creq" data-creq="share"><b>' + esc(names) + ' を リンク で送ります</b>（下書きで保存 · 送信 とも · 会社の SharePoint · 「リンクを知っている全員」 · 見るだけ · ' + days + ' 日（' + esc(untilMd(days)) + ' まで）· その後 zip は消えます · Outlook で添付する必要はありません）<br>' +
          '<span data-csharesum>' + esc(shareSumText(sf, days)) + '</span><br>' +
          (sf.needPhoto ? 'PHOTO.zip: 写真 ' + sf.photos.length + ' 枚 · ' + esc(mb(sf.photoBytes)) : '') + (sf.needPhoto && sf.needDocs ? ' / ' : '') +
          (sf.needDocs ? '搬入票.zip: ' + sf.docs.length + ' ファイル · ' + esc(mb(sf.docBytes)) : '') +
          (sf.noPhoto.length ? '<br><span class="c01-cr" data-cnophoto>写真なしCT: ' + esc(sf.noPhoto.join(' · ')) + '（送った後に来た写真は入りません）</span>' : '') +
          (st.shareStep ? '<br><span class="c01-cstep" data-csharestep>⟳ ' + esc(st.shareStep) + '</span>' : '') + '</div>';
      } else {
        /* v0.3.78 (R12Y40 · #384): リンクを作れない = 0.3.76 の動き (PDF だけ) + 黄色 */
        if (shareFallback()) h += '<div class="c01-cbox c01-cy c01-creq" data-creq="sharefail"><b>写真・搬入票のリンクを作れませんでした。Outlook で添付してください</b>' +
          '<span class="t2">（' + esc(shareWhy()) + '）</span></div>';
        h += '<div class="c01-cbox c01-cy c01-creq" data-creq="extra"><b>この通関業者は ' + esc(names) + ' も必要です。</b>下書きで保存して、Outlook で添付してから送信してください。' +
          (rq.brokers.length ? '<span class="t2">（' + esc(rq.brokers.join(' · ')) + '）</span>' : '') +
          '<br><label class="c01-cack"><input type="checkbox" data-cextra' + (st.extraAck ? ' checked' : '') + '> 追加書類は別に送ります（この画面から 「送信」 する）</label></div>';
      }
    } else if (rq.unknown.length) {
      h += '<div class="c01-cbox c01-cy c01-creq" data-creq="unknown"><b>必要書類を確認してください</b>（通関業者の表にない宛先: ' + esc(rq.unknown.join(' · ')) + '）</div>';
    }
    if (shareCfg() === 'admin_test' && isAdmin() && rq.extra.length) {
      h += '<label class="c01-cack c01-csharet" data-csharetbox><input type="checkbox" data-csharetest' + (st.shareTest ? ' checked' : '') + '> 管理者: 写真・搬入票リンクの試験（送信 = 自分 1 人 · 件名 [test] · 下書き = 下書きのみ · 送信は Outlook で · 宛先は実際の値）</label>';
    }
    return h;
  }
  function whyText(bl, dl) {
    if (!bl.length) return '送信できます';
    if (!dl.length) return '下書きで保存できます · 送信: ' + bl[bl.length - 1];
    return '送れません: ' + bl[0] + (bl.length > 1 ? '（ほか ' + (bl.length - 1) + '）' : '');
  }
  function footHtml(ready) {
    var bl = ready ? sendBlockers() : ['準備中'], dl = ready ? draftBlockers() : ['準備中'];
    var rq = ready ? reqNow() : { extra: [] };
    var draftFirst = rq.extra.length > 0 && !shareOn();          /* 追加書類が要る = 既定 = 下書きで保存 */
    var dBtn = '<button class="' + (draftFirst ? 'c01-btn-pri' : 'c01-btn-ghost2') + '" data-cdraftgo' + (dl.length ? ' disabled' : '') + ' title="送らずに Outlook の 下書き に保存します（宛先 · 件名 · 本文 · PDF 添付は 送信 と同じ）">下書きで保存</button>';
    var sBtn = '<button class="' + (draftFirst ? 'c01-btn-ghost2' : 'c01-btn-pri') + '" data-csendgo' + (bl.length ? ' disabled' : '') + '>' + (testMode() ? '送信（試験 · 自分あて）' : '送信（通関業者へ）') + '</button>';
    return '<div class="c01-mf"><span class="t2 c01-cwhy" data-cwhy>' + api().esc(whyText(bl, dl)) + '</span><span class="c01-flex"></span>' + dBtn + ' ' + sBtn + '</div>';
  }
  function mailArgs(forDraft) {
    var r = st.d03, rc = recips(), route = st.route;
    return { replyToId: route === 's1_reply' ? st.mail.last.id : null, newMail: route !== 's1_reply', conv: null, subject: subject(forDraft),
      html: bodyHtml(st.body || '') + (route === 's1_shared' ? quoteHtml(st.shared.last) : ''), pdf_b64: r.pdf_b64, file: r.file,
      to: rc.to.map(function (x) { return x.a; }), cc: rc.cc.map(function (x) { return x.a; }), forceTest: !forDraft && !!st.shareTest };
  }
  /* 本文 + リンク + (道 2 = ① の引用) */
  /* v0.3.79 (R12Y42 · #385 ①): リンクの段落は 署名 · 「✦ Powered by」 の下ではなく 本文の 「宜しくお願い致します。」 のすぐ次 (署名の前) ·
     あいさつの行が無い本文 = 署名 (---- の行) の前 · 署名も無い = 「✦ Powered by」 の前 · どれも無い = 今までどおり 本文の後 */
  function shareCut(txt) {
    var t = String(txt || ''), sig = t.search(/^-{10,}\s*$/m), foot = t.indexOf('✦ Powered by');
    var end = [sig, foot].filter(function (i) { return i >= 0; }).sort(function (x, y) { return x - y; })[0];
    var head = end == null ? t : t.slice(0, end), re = /(宜しく|よろしく)お願い(致|いた)します[^\n]*/g, m, cut = -1;
    while ((m = re.exec(head))) cut = m.index + m[0].length;
    if (cut >= 0) return cut;
    if (end != null) return end;
    return t.length;
  }
  function htmlWithShare(sh) {
    var t = String(st.body || ''), body;
    if (sh) {
      var k = shareCut(t), tail = t.slice(k).replace(/^\n/, '');
      body = bodyHtml(t.slice(0, k)) + shareHtml(sh) + (tail ? bodyHtml(tail) : '');
    } else body = bodyHtml(t);
    return body + (st.route === 's1_shared' ? quoteHtml(st.shared.last) : '');
  }
  function shareRec(sh) {
    return sh ? { place: sh.place, root: sh.root, stamp: sh.stamp, days: sh.days, expires: sh.expires, no_photo_ct: sh.no_photo_ct,
      files: sh.files.map(function (f) { return { name: f.name, item_id: f.item_id, path: f.path, size: f.size, n: f.n, url: f.url, expires: f.expires }; }) } : undefined;
  }
  /* v0.3.76 (R12Y37 · #380 ②): 下書きで保存 — 送信と同じ下書きを作って 送らない → Outlook で開くリンク · _actions customs_draft
     v0.3.78 (R12Y40 · #383 · #384): 追加書類の要る通関業者 = 下書き にも 写真・搬入票 リンク (zip → SharePoint · 本文にリンク · PDF 添付) ·
     リンクを作れない = 下書き は止めずに 0.3.76 の動き (PDF だけ) + 黄色 + _actions customs_share_error */
  function saveDraft() {
    var a = api();
    if (draftBlockers().length) return;
    var rq = reqNow(), iv = a.ivById(st.iv);
    var useShare = shareOn(), fb = shareFallback(), days = shareDays();
    var prev = lastDraft(iv) || (st.draftDone ? { at: st.draftDone.at } : null);
    var msg = '送らずに Outlook の 下書き に保存します（' + (testMode(true) ? '試験モード: 宛先 = あなた 1 人' : '宛先 ' + recips().to.length + ' 件 · CC ' + recips().cc.length + ' 件') + '）。\n件名: ' + subject(true) +
      (useShare ? '\n写真・搬入票: ' + shareSumText(shareFiles(), days) + '（zip を SharePoint に置き 本文にリンク）' : '') +
      (st.shareTest ? '\n下書きのみ · 送信は Outlook で（宛先は実際の値です）' : '') +
      (rq.extra.length && !useShare ? '\n\nOutlook で ' + rq.extra.map(function (k) { return EXTRA_NAME[k] || k; }).join('・') + ' を添付してから送信してください。' : '') + '\nよろしいですか？';
    if (!window.confirm(msg)) return;
    if (prev && !window.confirm('この IV の下書きはもう作ってあります（' + String(prev.at).slice(0, 16).replace('T', ' ') + '）。もう一つ作りますか？（Outlook の 下書き に 2 つになります）')) return;
    st.busy = true; st.sendErr = ''; draw();
    var ivNo = st.iv, r = st.d03, args = mailArgs(true), share = null, shareErr = '', cxl = {};
    args.draftOnly = true;
    if (fb) { shareErr = shareWhy(); shareErrRec('draft', 'precheck', shareErr); }
    (useShare ? withTimeout(prepareShare(cxl), shareTimeoutMs(), cxl).then(function (sh) { share = sh; args.html = htmlWithShare(sh); if (st) st.shareStep = '下書きを作っています'; }, function (e) {
      /* リンクを作れない = 下書き は PDF だけで続ける (0.3.76 と同じ) */
      shareErr = e.message; if (st && st.iv === ivNo) { st.shareFail = e.message; st.shareStep = ''; }
      return shareErrRec('draft', 'link', e.message);
    }) : Promise.resolve()).then(function () { return a.S.src.customsSend(args); }).then(function (res) {
      var v = { test: res.test, route: st.route, subject: args.subject, to: res.to, cc: res.cc, to_n: res.to.length, cc_n: res.cc.length, draft_id: res.draft_id, web_link: res.web_link || '',
        internet_message_id: res.internet_message_id || '', file: r.file, pages: r.pages, pdf_sha256: r.sha256, extra: rq.extra, brokers: rq.brokers, req_unknown: rq.unknown,
        broker_dom: st.brokerDom || '', real_to_n: recips().to.length, real_cc_n: recips().cc.length, to_how: recips().how,
        share: shareRec(share), share_error: shareErr ? shareErr.slice(0, 300) : undefined, share_test: st.shareTest ? true : undefined, broker_compass: bcRec() };
      return a.writeAction(a.mkAction('customs_draft', { iv: ivNo, ct: null, field: null, source: null, value: v })).then(function () { return res; });
    }).then(function (res) {
      if (!st || st.iv !== ivNo) return;
      st.busy = false; st.shareStep = '';
      st.draftDone = { at: new Date().toISOString(), link: res.web_link || '' };
      a.toast('下書きを保存しました — Outlook の 下書き から送ってください · ' + ivNo, 'ok');
      draw();
      var m = document.getElementById('c01-modal');
      var box = document.createElement('div');
      box.className = 'c01-cbox c01-cok';
      box.setAttribute('data-cdraftok', '1');
      var att = rq.extra.length && !share ? a.esc(rq.extra.map(function (k) { return EXTRA_NAME[k] || k; }).join('・')) + ' を添付して ' : '';
      box.innerHTML = '<b>下書きを保存しました</b>（送っていません）。' +
        (share ? '<span data-cdraftshare>写真・搬入票 のリンクを本文に入れました（' + a.esc(share.files.map(function (f) { return (f.name === 'PHOTO.zip' ? '写真 ' : '搬入票 ') + f.n + (f.name === 'PHOTO.zip' ? ' 枚' : ' 件'); }).join('・')) + ' · リンク有効 ' + a.esc(share.until) + ' まで）。</span>' : '') +
        (shareErr ? '<span class="c01-cy" data-cdraftsharefail>写真・搬入票のリンクを作れませんでした。Outlook で添付してください</span> ' : '') +
        'Outlook で ' + att + '送信してください。 ' +
        (res.web_link ? '<a href="' + a.esc(res.web_link) + '" target="_blank" rel="noopener" data-cdraftlink>Outlook で開く</a>' : '');
      var mb0 = m && m.querySelector('.c01-mbody');
      if (mb0) mb0.insertBefore(box, mb0.firstChild);
    }).catch(function (e) {
      if (st) { st.busy = false; st.shareStep = ''; st.sendErr = '下書き: ' + e.message + (share ? '（zip は SharePoint に残っている場合があります · リンクは期限で切れます）' : ''); draw(); }
      stickyErr('下書きを保存できませんでした: ' + e.message);
    });
  }
  /* v0.3.76 (R12Y37 · #380 ③ Part 3B): 写真 · 搬入票 zip → SharePoint (PHOTO_V2/_customs_share/{IV}/{時刻}/) → リンク (全員 · 見るだけ · 7 日) */
  function jstStamp() {
    var d = new Date(Date.now() + 9 * 36e5), p = function (n) { return (n < 10 ? '0' : '') + n; };
    return d.getUTCFullYear() + p(d.getUTCMonth() + 1) + p(d.getUTCDate()) + '-' + p(d.getUTCHours()) + p(d.getUTCMinutes()) + p(d.getUTCSeconds());
  }
  function base(p) { return String(p || '').split('/').pop(); }
  /* v0.3.78: cancel.v = true (時間切れ) → 次の段階で止まる (画面を描き直さない · まだ置いていなければ SharePoint に置かない) */
  function prepareShare(cancel) {
    var a = api(), src = a.S.src, sf = shareFiles(), ivNo = st.iv;
    cancel = cancel || {};
    if (typeof src.customsShareUpload !== 'function' || typeof src.customsFileBytes !== 'function' || typeof C01.zipStore !== 'function') return Promise.reject(new Error('この画面ではリンクを作れません'));
    var step = function (s) { if (!cancel.v && st && st.iv === ivNo) { st.shareStep = s; draw(); } };
    var get = function (xs, i, acc) {
      if (cancel.v) return Promise.reject(new Error('時間切れ'));
      if (i >= xs.length) return Promise.resolve(acc);
      step('写真・搬入票 を読んでいます ' + (i + 1) + '/' + xs.length);
      return src.customsFileBytes(xs[i].path).then(function (b) { acc.push({ x: xs[i], data: b }); return get(xs, i + 1, acc); });
    };
    var all = sf.photos.concat(sf.docs);
    return get(all, 0, []).then(function (got) {
      step('zip を作っています');
      var used = {}, uniq = function (n) { var k = n, i = 2; while (used[k]) { k = n.replace(/(\.[^.\/]*)?$/, '_' + i + '$1'); i += 1; } used[k] = 1; return k; };
      var ph = [], dc = [];
      got.forEach(function (g) {
        if (sf.photos.indexOf(g.x) >= 0) ph.push({ name: uniq(g.x.ct + '/' + base(g.x.path)), data: g.data });
        else dc.push({ name: uniq('搬入票/' + base(g.x.path)).replace(/^搬入票\//, ''), data: g.data });
      });
      var zips = [];
      if (sf.needPhoto) zips.push({ name: 'PHOTO.zip', bytes: C01.zipStore(ph), n: ph.length });
      if (sf.needDocs) zips.push({ name: '搬入票.zip', bytes: C01.zipStore(dc), n: dc.length });
      var days = shareDays(), exp = new Date(Date.now() + days * 864e5).toISOString();
      step('SharePoint に置いて リンクを作っています');
      var stamp = jstStamp();
      if (cancel.v) throw new Error('時間切れ');
      if (st) st.shareUp = true;                      /* ここから先の失敗 = zip が SharePoint に残っているかもしれない */
      return src.customsShareUpload(ivNo, stamp, zips, exp).then(function (files) {
        return { place: 'sp', root: (C01.SOURCE && C01.SOURCE.spLabel || 'PHOTO_V2') + '/_customs_share', iv: ivNo, stamp: stamp, days: days, expires: exp, until: untilMd(days),
          no_photo_ct: sf.noPhoto, files: files };
      });
    });
  }
  function shareHtml(sh) {
    var esc = api().esc;
    var label = { 'PHOTO.zip': '写真', '搬入票.zip': '搬入票' };
    return '<div style="font-family:\'Meiryo\',\'Yu Gothic\',sans-serif;font-size:10.5pt;margin-top:8pt;margin-bottom:8pt" data-cshare>写真・搬入票は下記リンクからダウンロードしてください（' + esc(sh.until) + ' まで有効）<br>' +
      sh.files.map(function (f) { return esc(label[f.name] || f.name) + '（' + esc(f.name) + ' · ' + f.n + ' ファイル · ' + esc(mb(f.size)) + '）: <a href="' + esc(f.url) + '">' + esc(f.url) + '</a>'; }).join('<br>') + '</div>';
  }
  function send() {
    var a = api();
    if (sendBlockers().length) return;
    var useShare = shareOn(), fb = shareFallback(), days = shareDays();
    var r = st.d03, rc = recips(), iv = a.ivById(st.iv), test = testMode(), sr = siRec(st.d03, st);
    var again = !!(lastLive(iv) || st.sent.some(function (x) { return !x.test; }));
    var subj = subject();
    var RW = { s1_reply: '① に 全員に返信', s1_shared: '① と同じ宛先へ 新しいメール（① は ' + ((st.shared && (st.shared.staff_name || st.shared.staff)) || '') + ' のメール）', manual: '入力した宛先（確認済み）' };
    var msg = (test ? '【試験】 あなた (' + a.S.me.email + ') だけに送ります。' : '【実際に通関業者へ送ります】 ' + st.iv + ' の通関書類を 宛先 ' + rc.to.length + ' 件 · CC ' + rc.cc.length + ' 件 に送ります（あなたのメールから）。') +
      '\n宛先の道: ' + RW[st.route] + '\n件名: ' + subj + '\n添付: ' + r.file + '（' + r.pages + ' ページ）' +
      (useShare ? '\n写真・搬入票: ' + shareSumText(shareFiles(), days) + '（zip を SharePoint に置き 本文にリンク）' : '') + '\nよろしいですか？';
    if (!window.confirm(msg)) return;
    if (again && !window.confirm('この IV はすでに送付済みです。本当にもう一度送りますか？')) return;
    st.busy = true; st.sendErr = ''; draw();
    var ivNo = st.iv;
    var route = st.route;
    var args = mailArgs(), share = null, rq = reqNow(), cxl = {};
    if (fb) shareErrRec('send', 'precheck', shareWhy());
    /* v0.3.78 (R12Y40 · #384): リンクを作れない = 送らずに止まる → 黄色 「写真・搬入票のリンクを作れませんでした。Outlook で添付してください」 + 「追加書類は別に送ります」 (0.3.76 と同じ) */
    var LINK_FAIL = {};
    (useShare ? withTimeout(prepareShare(cxl), shareTimeoutMs(), cxl).then(function (sh) { share = sh; args.html = htmlWithShare(sh); if (st) st.shareStep = 'メールを送っています'; }, function (e) {
      if (st && st.iv === ivNo) { st.shareFail = e.message; st.extraAck = false; }
      return shareErrRec('send', 'link', e.message).then(function () { throw LINK_FAIL; });
    }) : Promise.resolve()).then(function () { return a.S.src.customsSend(args); }).then(function (res) {
      return a.writeAction(a.mkAction('customs_sent', { iv: ivNo, ct: null, field: null, source: null,
        value: { test: res.test, again: again, subject: subj, to: res.to, cc: res.cc, to_n: res.to.length, cc_n: res.cc.length,
          internet_message_id: res.internet_message_id, file: r.file, pages: r.pages, pdf_sha256: r.sha256, d03: r.version,
          picks: { ivSino: r.picks.ivSino.v, siSino: r.picks.siSino.v, pod: r.picks.pod.v, freight: r.picks.freight.v },
          bl: r.picks.bl.v, bl_why: st.blWhy || '', sc_id: st.sc || '', sc_no: st.scNo || '', si_default_iv: sr.si_default_iv, si_default_si: sr.si_default_si,
          si_avail_n: sr.si_avail_n, si_why: sr.si_why, si_changed: sr.si_changed, buyer_id: (r.info || {}).buyer_id || st.buyer || '', consignee: (r.info || {}).consignee || '',
          red: (r.warnings || []).filter(function (w) { return w.red; }).map(function (w) { return w.item; }),
          real_to_n: rc.to.length, real_cc_n: rc.cc.length, to_how: rc.how, broker_dom: st.brokerDom || '', broker_line: String(st.body || '').split(/\r?\n/)[0].trim(),
          broker_person: personLine(st.body), name_src: st.nameSrc || null, route: route,
          s1_k: route === 's1_shared' ? st.shared.last.k : undefined, s1_amb: route === 's1_shared' && st.shared.ambiguous ? (st.shared.convs || []).length : undefined,
          s1_conv: route === 's1_shared' && st.shared.ambiguous && st.convI >= 0 ? st.shared.convs[st.convI].conv : undefined, s1_staff: route === 's1_shared' ? st.shared.staff : undefined,
          prop_src: route === 'manual' ? 'manual' : undefined, s1_how: (st.mail && st.mail.how) || (st.shared && st.sharedAll && st.sharedAll.how) || undefined, broker_compass: bcRec(),
          extra: rq.on ? rq.extra : undefined, extra_ack: rq.extra.length && !share ? !!st.extraAck : undefined,
          share_error: fb ? String(shareWhy()).slice(0, 300) : undefined, share: shareRec(share) } }));
    }).then(function () {
      if (!test && C01.clearance) C01.clearance.sent(ivNo, new Date().toISOString());   /* v0.3.83 (R12Y55 · #401): 通関依頼済 の記録 (影 = 試験用コピー + 一覧) · 失敗しても送付は終わっている */
      a.toast((test ? '試験送信しました（あなた宛て）' : '送信しました') + ' — ' + ivNo, 'ok');
      st = null; a.closeModal(); a.render();
    }).catch(function (e) {
      if (e === LINK_FAIL) {                       /* 送っていない · 黄色 + 「追加書類は別に送ります」 で もう一度 */
        if (st && st.iv === ivNo) { st.busy = false; st.shareStep = ''; st.shareUp = false; draw(); }
        a.toast('写真・搬入票のリンクを作れませんでした（送っていません）', 'info');
        return;
      }
      if (st) { st.busy = false; st.shareStep = ''; st.sendErr = e.message + (share || st.shareUp ? '（zip は SharePoint に残っている場合があります · リンクは期限で切れます）' : ''); st.shareUp = false; draw(); }
      stickyErr('送信できませんでした: ' + e.message);
    });
  }
  /* v0.3.66 (R12Y3 · #366 ③): 失敗の知らせは 「閉じる」 を押すまで消えない (すぐ消える toast では読めなかった) */
  function stickyErr(msg) {
    var old = document.getElementById('c01-cerr');
    if (old) old.remove();
    var d = document.createElement('div');
    d.id = 'c01-cerr';
    d.className = 'c01-cerr';
    d.setAttribute('role', 'alert');
    d.innerHTML = '<span></span><button type="button" class="c01-btn-ghost2" data-cerr-close>閉じる</button>';
    d.firstChild.textContent = msg;
    d.querySelector('[data-cerr-close]').onclick = function () { d.remove(); };
    document.body.appendChild(d);
  }
  function personLine(body) {
    var l = String(body || '').split(/\r?\n/).map(function (x) { return x.trim(); }).filter(function (x) { return SAMA_RE.test(x); })[0] || '';
    return l.replace(SAMA_RE, '').trim();
  }
  function nameSrcLine() {
    var s = st.nameSrc;
    if (!s) return '';
    var esc = api().esc;
    var b = s.broker || '見つかりません', p = s.person || '見つかりません';
    return '<p class="t2 c01-cnamesrc" data-cnamesrc>宛名の出どころ: ' + (b === p ? esc(b) : '会社名 = ' + esc(b) + ' · 担当者 = ' + esc(p)) + '</p>';
  }
  /* v0.3.66 (R12Y3 · #366 ①): POD = 今の S/I (IV·PL) の COMPASS の値 (D-03 の手動画面と同じ形 · 値の無い番号は薄く · 押せない) */
  function podCell(P) {
    var esc = api().esc, si = null;
    if (Array.isArray(st.si)) si = st.si.filter(function (x) { return Number(x.crcf9_sino) === Number(P.ivSino.v); })[0] || null;
    var h = [1, 2, 3].map(function (n) {
      var on = P.pod.v.indexOf(n) >= 0, ord = ['1st', '2nd', '3rd'][n - 1];
      if (!si) return '<label><input type="checkbox" data-cpod="' + n + '"' + (on ? ' checked' : '') + '> ' + n + '</label>';
      var val = si['crcf9_place_of_delivery_' + n] || '';
      var dis = !val && !on;
      return '<label class="c01-cpodl' + (dis ? ' c01-cpod-off' : '') + '"><input type="checkbox" data-cpod="' + n + '"' + (on ? ' checked' : '') + (dis ? ' disabled' : '') + '> ' + ord + ' POD' +
        (val ? ' <span class="c01-cpodv" data-cpodv="' + n + '">' + esc(val) + '</span>' : '') + '</label>';
    }).join('');
    if (!si) return h + '<div class="c01-cy" data-cpodng>COMPASS の POD を読めませんでした</div>';
    var bl = [1, 2, 3].map(function (n) { return si['crcf9_pod_bl' + n] || ''; }).filter(Boolean);
    var sub = (bl.length ? 'B/L: ' + bl.join(' / ') : '') + (si.crcf9_port_of_discharge ? (bl.length ? ' · ' : '') + 'Port of Discharge: ' + si.crcf9_port_of_discharge : '');
    return '<div class="c01-cpods">' + h + '</div>' + (sub ? '<div class="t2 c01-cpodsub" data-cpodsub>' + esc(sub) + '</div>' : '');
  }
  return { headerBtn: headerBtn, permitBadge: permitBadge, permitState: permitState, permitOn: permitOn, openPermit: openPermit, open: open,
    permitCheckBadge: permitCheckBadge, openPermitCheck: openPermitCheck, ckState: ckState, checkOn: checkOn, noneHour: noneHour,   /* v0.3.89 (R12Y68) */ lacks: lacks, records: records, _pickBl: pickBl, _cmp: cmpCompass, _blockers: function () { return st ? blockers() : null; },
    _greeting: greeting, _sigCompany: sigCompany, _shareCut: shareCut, _baseRecips: baseRecips, _domestic: domestic, _route: function () { return st ? st.route : null; }, _recips: function () { return st ? recips() : null; },
    _subject: function () { return st ? subject() : null; }, _req: function () { return st ? reqNow() : null; }, _sendBlockers: function () { return st ? sendBlockers() : null; },
    _draftBlockers: function () { return st ? draftBlockers() : null; }, _matchBroker: matchBroker, _normCo: normCo, _pickBl: pickBl, _siRec: siRec, _siWhyCode: siWhyCode, _siDef: function () { return st ? { iv: st.siDefIv || null, si: st.siDefSi || null } : null; }, _blState: function () { return st ? { bl: st.bl, why: st.blWhy, red: st.blRed || '', sc: st.sc, scNo: st.scNo } : null; }, _bc: function () { return st ? { now: bcNow(), check: bcCheck(), prop: st.prop, noRouteWhy: st.noRouteWhy } : null; }, _shareFiles: function () { return st ? shareFiles() : null; }, _shareOn: function () { return st ? shareOn() : null; } };
})();
