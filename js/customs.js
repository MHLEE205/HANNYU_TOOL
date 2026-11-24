/* ✦ Powered by LEENAI Automation System — 通関書類送付 (v0.3.63 · 決定 #359 · #302 · #303 · #306 · #338 · #343 · #352 · v0.3.66 #366)
   - 実況表 IV 見出しの 「通関書類送付」 (Compass入力 の横) → 確認窓 → 担当者が 「送信」 を押した時だけ 1 通
   - PDF = D-03 自動モード (同じ出所 · ?auto=1 · 押した担当者のログイン · COMPASS は読むだけ)
   - メール = ① 通関依頼 の会話の一番新しいメールに 全員に返信 (押した担当者のメール · js/source.js customsSend)
   - 試験モード (C01.CUSTOMS.sendTest) = 宛先は押した本人 1 人だけ · 件名の前に [test]
   - 送ったら _actions customs_sent (IV · 誰 · いつ · メール ID · PDF sha256 · 選んだ値)
   v0.3.68 (R12Y7 · #367): 宛先の道 (route) — ① 自分のメールボックスの ① に 全員に返信 (s1_reply) → ② 無ければ 会社のメールボックスの ① の会話
   (エンジン customs_s1.json) と同じ宛先へ 新しいメール · ① を引用 (s1_shared) → ③ それも無ければ 「この港へ最近送った宛先」 の提案 (proposal · 直せる) → ④ 宛先 0 = 止める。
   L インボイス (国内販売 · #218) = 送付ボタンの代わりに 「国内販売（通関書類は買い手側）」
   v0.3.76 (R12Y37 · #380): ① 通関業者ごとの 追加書類 (エンジン customs_broker_req.json · 決定 #380 の表) — 写真（PHOTO）・搬入票 が要る通関業者 = 確認窓の一番上に黄色 ·
   既定のボタン = 「下書きで保存」 (送らない · Outlook で添付して送る) · 「送信」 は 「追加書類は別に送ります」 のチェックの後だけ · 表に無い宛先 = 「必要書類を確認してください」。
   ② 「下書きで保存」 = 送信と同じ下書き (宛先 · 件名 · 本文 · PDF を確かめる) を作って 送らない → Outlook で開くリンク · _actions customs_draft · 実況表 「下書き作成済」 →
   その職員の 「通関書類送付_{IV}」 メールをエンジンが見たら 「送付済」 (エンジン iv.customs_mail)。
   ③ (Part 3B · C01.CUSTOMS.shareLink) 写真 · 搬入票 を zip にして 会社の SharePoint (PHOTO_V2/_customs_share) に置き 「リンクを知っている全員」 · 見るだけ · 7 日のリンクを本文に入れて送る —
   'admin_test' = 管理者の 「写真・搬入票リンクの試験」 だけ (宛先 = 自分 1 人 · [test]) · 'on' = 実際の送付 (rpa@ 試験メールの確認の後) · 'off' = 出さない */
'use strict';
window.C01 = window.C01 || {};

C01.customs = (function () {
  var A = null;
  function api() { return A || (A = C01.app._api()); }
  function on() { return !!(C01.CUSTOMS && C01.CUSTOMS.enabled); }
  function testMode() { return !(C01.CUSTOMS && C01.CUSTOMS.sendTest === false) || !!(st && st.shareTest); }      /* v0.3.76: 管理者のリンク試験 = 試験モード */
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
  function lastDraft(iv) { return records(iv, 'customs_draft').filter(function (x) { return !x.value.test; })[0] || null; }
  function lastLive(iv) { return records(iv).filter(function (x) { return !x.value.test; })[0] || null; }
  function lastTest(iv) { return records(iv).filter(function (x) { return x.value.test; })[0] || null; }

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
  /* v0.3.66 (R12Y3 · #366 ①): 販売契約 (SC) を 1 回だけ読み、バイヤーと S/I (POD 1/2/3 · B/L 用 POD · Port of Discharge) を一緒に読む。
     S/I が読めない = si null (確認窓は番号だけ + 黄色 · 送信は止めない — D-03 が PDF に入れた値が正本) */
  var SI_SEL = 'crcf9_sino,crcf9_place_of_delivery_1,crcf9_place_of_delivery_2,crcf9_place_of_delivery_3,crcf9_pod_bl1,crcf9_pod_bl2,crcf9_pod_bl3,crcf9_port_of_discharge';
  function contractOf(ivNo) {
    return dvGet("cr49f_bookings?$filter=cr49f_invoice_no eq '" + String(ivNo).replace(/'/g, "''") + "'&$select=_cr49f_sale_contract_id_value").then(function (j) {
      var b = (j.value || [])[0], sc = b && b._cr49f_sale_contract_id_value;
      if (!sc) return { buyer: '', si: null };
      var pB = dvGet('cr49f_sale_contracts(' + sc + ')?$select=_cr49f_buyer_id_value').then(function (s) { return s._cr49f_buyer_id_value || ''; }, function () { return ''; });
      var pS = dvGet('cr49f_s_is?$filter=_cr49f_sale_contract_id_value eq ' + sc + '&$select=' + SI_SEL).then(function (r) { return r.value || []; }, function () { return null; });
      return Promise.all([pB, pS]).then(function (r) { return { buyer: r[0], si: r[1] }; });
    }).catch(function () { return { buyer: '', si: null }; });
  }
  /* #338: バイヤーの 6 か月の B/L 実績 = エンジン customs_bl.json (あれば) + 送付記録 (customs_sent · 試験は除く) */
  function blHistory(buyer, ivNo) {
    var S = api().S, out = [], since = new Date(Date.now() - 183 * 864e5).toISOString().slice(0, 10);
    var seed = (S.customsBl && S.customsBl.buyers && S.customsBl.buyers[buyer]) || [];
    seed.forEach(function (x) { if (String(x.at || '') >= since && x.iv !== ivNo && BL_CLS[x.bl]) out.push({ at: x.at, bl: BL_CLS[x.bl], cons: x.cons || '' }); });
    ((S.jik && S.jik.ivs) || []).forEach(function (iv) {
      records(iv).forEach(function (r) { var v = r.value; if (!v.test && v.buyer_id === buyer && iv.iv_no !== ivNo && BL_CLS[v.bl]) out.push({ at: r.at, bl: BL_CLS[v.bl], cons: v.consignee || '' }); });
    });
    return out.sort(function (a, b) { return String(a.at).localeCompare(String(b.at)); });
  }
  function pickBl(h) {
    if (!h.length) return { v: '', why: '新しいバイヤー（6 か月の実績なし）' };
    var c = { original: 0, waybill: 0, surrender: 0 };
    h.forEach(function (x) { c[x.bl] += 1; });
    if (c.surrender) return { v: '', why: 'SURRENDER の実績あり' };
    if (c.original && c.waybill) return { v: '', why: '混在（WAY BILL ' + c.waybill + ' / Original ' + c.original + '）' };
    var v = c.waybill ? 'waybill' : 'original';
    return { v: v, why: '6 か月の実績 = ' + BL_LABEL[v] + '（' + (c[v]) + ' 件）' };
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
     ② TOOL の送付記録 (customs_sent · 試験を除く · 同じドメイン) の 1 行目 · 2 行目
     ③ 職員が手で送った 「通関書類送付」 (エンジン customs_broker.json · 同じドメイン · 担当者が複数 = 今の宛先にいる人 → 一番新しい人)
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
        records(iv).forEach(function (r) { if (!r.value.test && r.value.broker_dom === dom && r.value.broker_line && (!rec || String(r.at) > String(rec.at))) rec = r; });
      });
      if (rec) put(rec.value.broker_line, rec.value.broker_person || '', 'TOOL の送付記録（' + a.md(String(rec.at).slice(0, 10)) + '）');
      // ③
      var cb = S.customsBroker && S.customsBroker.domains && S.customsBroker.domains[dom];
      if (cb) {
        var names = [].concat((last && last.to) || [], (last && last.cc) || [], last ? [{ a: last.from, n: last.from_name }] : []).filter(function (x) { return domOf(x.a) === dom; }).map(function (x) { return normName(x.n); });
        var ps = (cb.persons || []).filter(function (x) { var k = normName(x.name); return k && names.some(function (n) { return n && n.indexOf(k) >= 0; }); })[0] || (cb.persons || [])[0];
        put(cb.company || '', ps ? ps.name : '', '過去の 通関書類送付（' + cb.n + ' 通）');
      }
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
      extraAck: false, draftDone: null, shareTest: false, ph: null, shareStep: '' };
    a.S.modal = { kind: 'customs', iv: ivNo };
    draw();
    var src = a.S.src;
    var graphOk = a.graphMode() && typeof src.customsFindS1 === 'function';
    var pMail = graphOk ? src.customsFindS1(iv.bkg_no).catch(function (e) { st.err.push('① の検索: ' + e.message); return null; }) : Promise.resolve(null);
    var pSent = graphOk ? src.customsFindSent(ivNo).catch(function () { return []; }) : Promise.resolve([]);
    /* customs_bl.json = エンジンの meta.customs_bl がある時だけ読む (無いエンジンに 404 を出さない) */
    var pBl = (a.S.customsBl === undefined && a.S.meta && a.S.meta.customs_bl ? src.getJson(String(a.S.meta.customs_bl)).then(function (x) { a.S.customsBl = x; }, function () { a.S.customsBl = null; }) : Promise.resolve())
      .then(function () { return graphOk ? contractOf(ivNo) : { buyer: '', si: null }; });
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
    var pPh = shareCfg() !== 'off' ? src.getJson('photos/' + ivNo + '.json').then(function (x) { if (st && st.iv === ivNo) st.ph = x; }, function () { if (st && st.iv === ivNo) st.ph = null; }) : Promise.resolve();
    Promise.all([pMail, pSent, pBl, pFt, pCb, pS1, pReq, pPh]).then(function (r) {
      if (!st || st.iv !== ivNo) return;
      st.mail = r[0]; st.sent = r[1] || []; st.buyer = (r[2] || {}).buyer || ''; st.si = (r[2] || {}).si; st.ftBlank = r[3];
      pickRoute(iv);
      var h = st.buyer ? blHistory(st.buyer, ivNo) : [];
      var pb = pickBl(h);
      st.bl = pb.v; st.blWhy = pb.why;
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
    var p = proposal(iv, st.buyer);
    if (p) {
      st.route = 'proposal'; st.prop = p;
      var me = String((S.me || {}).email || '').toLowerCase();
      var fmt = function (xs) { return (xs || []).filter(function (x) { return x.a && x.a !== me; }).map(function (x) { return x.a; }).join(', '); };
      st.editTo = fmt(p.to); st.editCc = fmt(p.cc);
      return;
    }
    st.route = '';
  }
  /* 「この港へ最近送った宛先」: ① TOOL の送付記録 (試験を除く) で 同じ POL · 同じバイヤー の一番新しいもの → ② 無ければ エンジンの by_pol (同じ POL の一番新しい ① · バイヤーは分からない = 赤) */
  function proposal(iv, buyer) {
    var S = api().S, best = null, pol = String((iv && iv.pol) || '').toUpperCase();
    if (!pol) return null;
    var ad = function (xs) { return (xs || []).map(function (a) { return typeof a === 'string' ? { a: a.toLowerCase(), n: '' } : a; }); };
    if (buyer) {
      ((S.jik && S.jik.ivs) || []).forEach(function (x) {
        if (String(x.pol || '').toUpperCase() !== pol || x.iv_no === iv.iv_no) return;
        records(x).forEach(function (r) {
          var v = r.value;
          if (v.test || v.buyer_id !== buyer || !(v.to || []).length) return;
          if (!best || String(r.at) > String(best.at)) best = { at: String(r.at), to: ad(v.to), cc: ad(v.cc), src: 'buyer', iv: x.iv_no };
        });
      });
    }
    if (best) return best;
    var bp = S.customsS1 && S.customsS1.by_pol && S.customsS1.by_pol[pol];
    if (bp && (bp.to || []).length) return { at: bp.at, to: ad(bp.to), cc: ad(bp.cc), src: 'pol', n: bp.n };
    return null;
  }
  /* 宛名さがし (brokerGuess) 用 — 道 2 · 3 でも ① と同じ形 */
  function mailLike() {
    if (st.mail) return st.mail;
    if (st.route === 's1_shared') return { s1: { subject: st.shared.s1.subject, to: [] }, last: st.shared.last, conv: [] };
    if (st.route === 'proposal') return { s1: null, last: { from: '', from_name: '', to: st.prop.to, cc: st.prop.cc }, conv: [] };
    return null;
  }
  var ADDR_RE = /^[^@\s,;<>]+@[^@\s,;<>]+\.[^@\s,;<>]+$/;
  function parseAddrs(t) { return String(t || '').split(/[\s,;、，]+/).map(function (x) { return x.trim().toLowerCase(); }).filter(Boolean); }
  function recips() {
    var me = String((api().S.me || {}).email || '').toLowerCase();
    var seen = {};
    var pick = function (xs) { return xs.filter(function (x) { var k = x.a; if (!k || k === me || seen[k]) return false; seen[k] = 1; return true; }); };
    if (st.route === 'proposal') {
      return { to: pick(parseAddrs(st.editTo).map(function (a) { return { a: a, n: '' }; })), cc: pick(parseAddrs(st.editCc).map(function (a) { return { a: a, n: '' }; })) };
    }
    var L = st.route === 's1_reply' ? st.mail && st.mail.last : st.route === 's1_shared' ? st.shared.last : null;
    if (!L) return { to: [], cc: [] };
    var to = pick([{ a: L.from, n: L.from_name }].concat(L.to || []));
    var ccs = (L.cc || []).slice();
    /* 道 2: ① の担当職員を CC に (既定 · 外せる) — 他の職員の会話に入るので 担当者にも見えるように */
    if (st.route === 's1_shared' && st.addStaff && st.shared.staff) ccs.push({ a: st.shared.staff, n: st.shared.staff_name || '' });
    var cc = pick(ccs);
    return { to: to, cc: cc };
  }
  function stripRe(s) { return String(s || '').replace(/^\s*((re|fw|fwd|返信|転送)\s*[:：]\s*)+/i, '').trim(); }
  function subject() {
    var t = (testMode() ? '[test] ' : '') + '【通関書類送付_' + st.iv + '】';
    if (st.route === 's1_shared') return t + 'RE: ' + stripRe(st.shared.s1.subject);
    if (st.route === 'proposal') { var iv = api().ivById(st.iv) || {}; return t + 'BKG#' + (iv.bkg_no || '') + ' CUT ' + api().md(iv.cy_cut); }
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
  function shareOn() {
    var rq = reqNow();
    if (!rq.extra.length) return false;
    var c = shareCfg();
    return c === 'on' || (c === 'admin_test' && isAdmin() && !!st.shareTest);
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
    if (!st.route) out.push('宛先がありません（① 通関依頼 も 最近この港へ送った宛先 もありません）');
    if (st.route === 's1_shared' && !st.shared.last.body_ok) out.push('① の本文をまだ読めていません — 数分後に もう一度開いてください');
    /* v0.3.74 (R12Y18 · #377): 実際の送付 · 道 2 (会社のメールボックスの ①) = 「宛先を確認しました」 のチェックが要る (道 3 = 今までどおり · 道 1 = チェックなし) */
    if (st.route === 's1_shared' && !testMode() && !st.ackTo) out.push('宛先を確認して 「宛先を確認しました」 にチェックしてください');
    if (st.route === 'proposal') {
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
    if (rq.extra.length && !shareOn() && !st.extraAck) out.push('この通関業者は ' + rq.extra.map(function (k) { return EXTRA_NAME[k] || k; }).join('・') + ' も必要です — 下書きで保存するか 「追加書類は別に送ります」 にチェック');
    if (shareOn()) {
      var sf = shareFiles();
      if (!st.ph) out.push('写真 · 搬入票 の一覧を読めません');
      else if (sf.needPhoto && !sf.photos.length) out.push('写真がありません（リンクで送れません）');
      else if (sf.needDocs && !sf.docs.length) out.push('搬入票がありません（リンクで送れません）');
    }
    return out;
  }
  function draftBlockers() {
    var out = blockers().slice();
    if (st.shareTest) out.push('リンクの試験中は 下書き を作れません（送信で試験してください）');
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
    if (l || sentMail.length) {
      h += '<div class="c01-cbox c01-cred"><b>送付済み</b> ' + (l ? esc(String(l.at).slice(0, 16).replace('T', ' ')) + ' · ' + esc(a.staffName(l.by)) + '（記録）' : '') +
        (sentMail.length ? ' · メール ' + sentMail.length + ' 通（' + esc(String(sentMail[0].at).slice(0, 16).replace('T', ' ')) + ' · ' + esc(sentMail[0].from_name || sentMail[0].from) + '）' : '') +
        '<label class="t2"><input type="checkbox" data-cagain' + (st.again ? ' checked' : '') + '> もう一度送る（再送付）</label></div>';
    }
    // 宛先
    var rc = recips();
    var RH = { s1_reply: '宛先（① 通関依頼 の会話の一番新しいメールに 全員に返信）', s1_shared: '宛先（① の会話と同じ宛先へ 新しいメール · ① を引用）', proposal: '宛先（この港へ最近送った宛先 · 直せます）' };
    h += '<section class="c01-csec" data-croute="' + esc(st.route || (ready ? 'none' : '')) + '"><h4>' + esc(RH[st.route] || '宛先') + '</h4>';
    var addrs = function (xs) { return xs.map(function (x) { return esc(x.n ? x.n + ' <' + x.a + '>' : x.a); }).join('<br>') || '—'; };
    if (!ready && !st.route) {
      h += '<p class="t2">確認中…</p>';
    } else if (!st.route) {
      h += '<p class="c01-warn2" data-cnoroute>宛先がありません — 送れません（① 通関依頼 が見つからず、この港 ' + esc(iv.pol || '') + ' へ最近送った宛先もありません）。</p>';
    } else if (st.route === 'proposal') {
      var P = st.prop;
      h += P.src === 'buyer' ? '<p class="c01-cy" data-cprop="buyer">①がありません — 宛先を確認してください（同じ港 · 同じバイヤーへ ' + esc(a.md(String(P.at).slice(0, 10))) + ' に送った宛先）</p>'
        : '<p class="c01-cr" data-cprop="pol">①がありません — 宛先を必ず確認（同じ港 ' + esc(iv.pol || '') + ' の一番新しい ① 通関依頼 ' + esc(a.md(String(P.at).slice(0, 10))) + ' の宛先 · バイヤーは確かめていません）</p>';
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
      if (st.route === 's1_shared' && !testMode()) h += '<br><label class="c01-cack"><input type="checkbox" data-cackto' + (st.ackTo ? ' checked' : '') + '> 宛先を確認しました</label>';
    }
    if (st.route) {
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
        ['original', 'waybill', 'surrender'].map(function (k) { return '<option value="' + k + '"' + (P.bl.v === k ? ' selected' : '') + '>' + BL_LABEL[k] + '</option>'; }).join('') + '</select></td><td class="t2' + (!P.bl.v ? ' c01-cr' : '') + '">' + esc(st.blWhy) + '</td></tr></table>';
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
    if (stt) stt.onchange = function () { st.shareTest = stt.checked; st.extraAck = false; st.body = st.body; draw(); };
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
        h += '<div class="c01-cbox c01-cy c01-creq" data-creq="share"><b>' + esc(names) + ' を リンク で送ります</b>（会社の SharePoint · 「リンクを知っている全員」 · 見るだけ · ' + days + ' 日（' + esc(untilMd(days)) + ' まで）· その後 zip は消えます）<br>' +
          (sf.needPhoto ? 'PHOTO.zip: 写真 ' + sf.photos.length + ' 枚 · ' + esc(mb(sf.photoBytes)) : '') + (sf.needPhoto && sf.needDocs ? ' / ' : '') +
          (sf.needDocs ? '搬入票.zip: ' + sf.docs.length + ' ファイル · ' + esc(mb(sf.docBytes)) : '') +
          (sf.noPhoto.length ? '<br><span class="c01-cr" data-cnophoto>写真なしCT: ' + esc(sf.noPhoto.join(' · ')) + '（送った後に来た写真は入りません）</span>' : '') +
          (st.shareStep ? '<br><span class="c01-cstep" data-csharestep>⟳ ' + esc(st.shareStep) + '</span>' : '') + '</div>';
      } else {
        h += '<div class="c01-cbox c01-cy c01-creq" data-creq="extra"><b>この通関業者は ' + esc(names) + ' も必要です。</b>下書きで保存して、Outlook で添付してから送信してください。' +
          (rq.brokers.length ? '<span class="t2">（' + esc(rq.brokers.join(' · ')) + '）</span>' : '') +
          '<br><label class="c01-cack"><input type="checkbox" data-cextra' + (st.extraAck ? ' checked' : '') + '> 追加書類は別に送ります（この画面から 「送信」 する）</label></div>';
      }
    } else if (rq.unknown.length) {
      h += '<div class="c01-cbox c01-cy c01-creq" data-creq="unknown"><b>必要書類を確認してください</b>（通関業者の表にない宛先: ' + esc(rq.unknown.join(' · ')) + '）</div>';
    }
    if (shareCfg() === 'admin_test' && isAdmin() && rq.extra.length) {
      h += '<label class="c01-cack c01-csharet" data-csharetbox><input type="checkbox" data-csharetest' + (st.shareTest ? ' checked' : '') + '> 管理者: 写真・搬入票リンクの試験（宛先 = 自分 1 人 · 件名 [test] · 通関業者には送りません）</label>';
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
  function mailArgs() {
    var r = st.d03, rc = recips(), route = st.route;
    return { replyToId: route === 's1_reply' ? st.mail.last.id : null, newMail: route !== 's1_reply', conv: null, subject: subject(),
      html: bodyHtml(st.body || '') + (route === 's1_shared' ? quoteHtml(st.shared.last) : ''), pdf_b64: r.pdf_b64, file: r.file,
      to: rc.to.map(function (x) { return x.a; }), cc: rc.cc.map(function (x) { return x.a; }), forceTest: !!st.shareTest };
  }
  /* v0.3.76 (R12Y37 · #380 ②): 下書きで保存 — 送信と同じ下書きを作って 送らない → Outlook で開くリンク · _actions customs_draft */
  function saveDraft() {
    var a = api();
    if (draftBlockers().length) return;
    var rq = reqNow(), iv = a.ivById(st.iv);
    var prev = lastDraft(iv) || (st.draftDone ? { at: st.draftDone.at } : null);
    var msg = '送らずに Outlook の 下書き に保存します（' + (testMode() ? '試験モード: 宛先 = あなた 1 人' : '宛先 ' + recips().to.length + ' 件 · CC ' + recips().cc.length + ' 件') + '）。\n件名: ' + subject() +
      (rq.extra.length ? '\n\nOutlook で ' + rq.extra.map(function (k) { return EXTRA_NAME[k] || k; }).join('・') + ' を添付してから送信してください。' : '') + '\nよろしいですか？';
    if (!window.confirm(msg)) return;
    if (prev && !window.confirm('この IV の下書きはもう作ってあります（' + String(prev.at).slice(0, 16).replace('T', ' ') + '）。もう一つ作りますか？（Outlook の 下書き に 2 つになります）')) return;
    st.busy = true; st.sendErr = ''; draw();
    var ivNo = st.iv, r = st.d03, args = mailArgs();
    args.draftOnly = true;
    a.S.src.customsSend(args).then(function (res) {
      var v = { test: res.test, route: st.route, subject: args.subject, to: res.to, cc: res.cc, to_n: res.to.length, cc_n: res.cc.length, draft_id: res.draft_id, web_link: res.web_link || '',
        internet_message_id: res.internet_message_id || '', file: r.file, pages: r.pages, pdf_sha256: r.sha256, extra: rq.extra, brokers: rq.brokers, req_unknown: rq.unknown,
        broker_dom: st.brokerDom || '', real_to_n: recips().to.length, real_cc_n: recips().cc.length };
      return a.writeAction(a.mkAction('customs_draft', { iv: ivNo, ct: null, field: null, source: null, value: v })).then(function () { return res; });
    }).then(function (res) {
      if (!st || st.iv !== ivNo) return;
      st.busy = false;
      st.draftDone = { at: new Date().toISOString(), link: res.web_link || '' };
      a.toast('下書きを保存しました — Outlook の 下書き から送ってください · ' + ivNo, 'ok');
      draw();
      var m = document.getElementById('c01-modal');
      var box = document.createElement('div');
      box.className = 'c01-cbox c01-cok';
      box.setAttribute('data-cdraftok', '1');
      box.innerHTML = '<b>下書きを保存しました</b>（送っていません）。Outlook で ' + (rq.extra.length ? a.esc(rq.extra.map(function (k) { return EXTRA_NAME[k] || k; }).join('・')) + ' を添付して ' : '') + '送信してください。 ' +
        (res.web_link ? '<a href="' + a.esc(res.web_link) + '" target="_blank" rel="noopener" data-cdraftlink>Outlook で開く</a>' : '');
      var mb0 = m && m.querySelector('.c01-mbody');
      if (mb0) mb0.insertBefore(box, mb0.firstChild);
    }).catch(function (e) {
      if (st) { st.busy = false; st.sendErr = '下書き: ' + e.message; draw(); }
      stickyErr('下書きを保存できませんでした: ' + e.message);
    });
  }
  /* v0.3.76 (R12Y37 · #380 ③ Part 3B): 写真 · 搬入票 zip → SharePoint (PHOTO_V2/_customs_share/{IV}/{時刻}/) → リンク (全員 · 見るだけ · 7 日) */
  function jstStamp() {
    var d = new Date(Date.now() + 9 * 36e5), p = function (n) { return (n < 10 ? '0' : '') + n; };
    return d.getUTCFullYear() + p(d.getUTCMonth() + 1) + p(d.getUTCDate()) + '-' + p(d.getUTCHours()) + p(d.getUTCMinutes()) + p(d.getUTCSeconds());
  }
  function base(p) { return String(p || '').split('/').pop(); }
  function prepareShare() {
    var a = api(), src = a.S.src, sf = shareFiles(), ivNo = st.iv;
    if (typeof src.customsShareUpload !== 'function' || typeof src.customsFileBytes !== 'function' || typeof C01.zipStore !== 'function') return Promise.reject(new Error('この画面ではリンクを作れません'));
    var step = function (s) { if (st && st.iv === ivNo) { st.shareStep = s; draw(); } };
    var get = function (xs, i, acc) {
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
    return '<div style="font-family:\'Meiryo\',\'Yu Gothic\',sans-serif;font-size:10.5pt;margin-top:8pt">写真・搬入票は下記リンクからダウンロードしてください（' + esc(sh.until) + ' まで有効）<br>' +
      sh.files.map(function (f) { return esc(label[f.name] || f.name) + '（' + esc(f.name) + ' · ' + f.n + ' ファイル · ' + esc(mb(f.size)) + '）: <a href="' + esc(f.url) + '">' + esc(f.url) + '</a>'; }).join('<br>') + '</div>';
  }
  function send() {
    var a = api();
    if (sendBlockers().length) return;
    var useShare = shareOn();
    var r = st.d03, rc = recips(), iv = a.ivById(st.iv), test = testMode();
    var again = !!(lastLive(iv) || st.sent.some(function (x) { return !x.test; }));
    var subj = subject();
    var RW = { s1_reply: '① に 全員に返信', s1_shared: '① と同じ宛先へ 新しいメール（① は ' + ((st.shared && (st.shared.staff_name || st.shared.staff)) || '') + ' のメール）', proposal: '最近この港へ送った宛先（提案 · 確認済み）' };
    var msg = (test ? '【試験】 あなた (' + a.S.me.email + ') だけに送ります。' : '【実際に通関業者へ送ります】 ' + st.iv + ' の通関書類を 宛先 ' + rc.to.length + ' 件 · CC ' + rc.cc.length + ' 件 に送ります（あなたのメールから）。') +
      '\n宛先の道: ' + RW[st.route] + '\n件名: ' + subj + '\n添付: ' + r.file + '（' + r.pages + ' ページ）' +
      (useShare ? '\n写真・搬入票: zip を SharePoint に置き リンク (' + shareDays() + ' 日) を本文に入れます' : '') + '\nよろしいですか？';
    if (!window.confirm(msg)) return;
    if (again && !window.confirm('この IV はすでに送付済みです。本当にもう一度送りますか？')) return;
    st.busy = true; st.sendErr = ''; draw();
    var ivNo = st.iv;
    var route = st.route;
    var args = mailArgs(), share = null, rq = reqNow();
    (useShare ? prepareShare().then(function (sh) { share = sh; args.html = bodyHtml(st.body || '') + shareHtml(sh) + (route === 's1_shared' ? quoteHtml(st.shared.last) : ''); if (st) st.shareStep = 'メールを送っています'; })
      : Promise.resolve()).then(function () { return a.S.src.customsSend(args); }).then(function (res) {
      return a.writeAction(a.mkAction('customs_sent', { iv: ivNo, ct: null, field: null, source: null,
        value: { test: res.test, again: again, subject: subj, to: res.to, cc: res.cc, to_n: res.to.length, cc_n: res.cc.length,
          internet_message_id: res.internet_message_id, file: r.file, pages: r.pages, pdf_sha256: r.sha256, d03: r.version,
          picks: { ivSino: r.picks.ivSino.v, siSino: r.picks.siSino.v, pod: r.picks.pod.v, freight: r.picks.freight.v },
          bl: r.picks.bl.v, buyer_id: (r.info || {}).buyer_id || st.buyer || '', consignee: (r.info || {}).consignee || '',
          red: (r.warnings || []).filter(function (w) { return w.red; }).map(function (w) { return w.item; }),
          real_to_n: rc.to.length, real_cc_n: rc.cc.length, broker_dom: st.brokerDom || '', broker_line: String(st.body || '').split(/\r?\n/)[0].trim(),
          broker_person: personLine(st.body), name_src: st.nameSrc || null, route: route,
          s1_k: route === 's1_shared' ? st.shared.last.k : undefined, s1_amb: route === 's1_shared' && st.shared.ambiguous ? (st.shared.convs || []).length : undefined,
          s1_conv: route === 's1_shared' && st.shared.ambiguous && st.convI >= 0 ? st.shared.convs[st.convI].conv : undefined, s1_staff: route === 's1_shared' ? st.shared.staff : undefined,
          prop_src: route === 'proposal' ? st.prop.src : undefined,
          extra: rq.on ? rq.extra : undefined, extra_ack: rq.extra.length && !share ? !!st.extraAck : undefined,
          share: share ? { place: share.place, root: share.root, stamp: share.stamp, days: share.days, expires: share.expires, no_photo_ct: share.no_photo_ct,
            files: share.files.map(function (f) { return { name: f.name, item_id: f.item_id, path: f.path, size: f.size, n: f.n, url: f.url }; }) } : undefined } }));
    }).then(function () {
      a.toast((test ? '試験送信しました（あなた宛て）' : '送信しました') + ' — ' + ivNo, 'ok');
      st = null; a.closeModal(); a.render();
    }).catch(function (e) {
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
  return { headerBtn: headerBtn, open: open, lacks: lacks, records: records, _pickBl: pickBl, _cmp: cmpCompass, _blockers: function () { return st ? blockers() : null; },
    _greeting: greeting, _sigCompany: sigCompany, _domestic: domestic, _route: function () { return st ? st.route : null; }, _recips: function () { return st ? recips() : null; },
    _subject: function () { return st ? subject() : null; }, _req: function () { return st ? reqNow() : null; }, _sendBlockers: function () { return st ? sendBlockers() : null; },
    _draftBlockers: function () { return st ? draftBlockers() : null; }, _shareFiles: function () { return st ? shareFiles() : null; }, _shareOn: function () { return st ? shareOn() : null; } };
})();
