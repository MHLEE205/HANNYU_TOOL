/* ✦ Powered by LEENAI Automation System — 通関書類送付 (v0.3.63 · 決定 #359 · #302 · #303 · #306 · #338 · #343 · #352)
   - 実況表 IV 見出しの 「通関書類送付」 (Compass入力 の横) → 確認窓 → 担当者が 「送信」 を押した時だけ 1 通
   - PDF = D-03 自動モード (同じ出所 · ?auto=1 · 押した担当者のログイン · COMPASS は読むだけ)
   - メール = ① 通関依頼 の会話の一番新しいメールに 全員に返信 (押した担当者のメール · js/source.js customsSend)
   - 試験モード (C01.CUSTOMS.sendTest) = 宛先は押した本人 1 人だけ · 件名の前に [test]
   - 送ったら _actions customs_sent (IV · 誰 · いつ · メール ID · PDF sha256 · 選んだ値) */
'use strict';
window.C01 = window.C01 || {};

C01.customs = (function () {
  var A = null;
  function api() { return A || (A = C01.app._api()); }
  function on() { return !!(C01.CUSTOMS && C01.CUSTOMS.enabled); }
  function testMode() { return !(C01.CUSTOMS && C01.CUSTOMS.sendTest === false); }
  var BL_LABEL = { original: 'Original B/L', waybill: 'WAY BILL', surrender: 'SURRENDER' };
  var BL_CLS = { ORIG: 'original', WAY: 'waybill', SUR: 'surrender', original: 'original', waybill: 'waybill', surrender: 'surrender' };

  /* ── 送付の記録 (エンジン iv.customs_sent + 自分 · 他の人の _actions) — 新しい順 ── */
  function records(iv) {
    var S = api().S, xs = [], seen = {};
    ((iv && iv.customs_sent) || []).forEach(function (x) { seen[x.action_id] = 1; xs.push({ action_id: x.action_id, by: x.by, at: x.at, value: x.value || {} }); });
    (S.actions || []).concat(S.mine || []).forEach(function (x) {
      var a = x.action || x;
      if (a.action === 'customs_sent' && iv && a.iv === iv.iv_no && !seen[a.action_id]) { seen[a.action_id] = 1; xs.push({ action_id: a.action_id, by: a.by, at: a.at, value: a.value || {} }); }
    });
    return xs.sort(function (a, b) { return String(b.at).localeCompare(String(a.at)); });
  }
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
  function headerBtn(g) {
    if (!on()) return '';
    var a = api(), iv = g.iv, esc = a.esc;
    a.S.customsG = a.S.customsG || {};
    a.S.customsG[iv.iv_no] = g;
    var l = lastLive(iv), t = lastTest(iv);
    if (l) return '<button class="c01-done c01-csent" data-csend="' + esc(iv.iv_no) + '" title="' + esc('通関書類 送付済 ' + String(l.at).slice(0, 16).replace('T', ' ') + ' · ' + a.staffName(l.by) + ' — 押すと記録 · 再送付') + '">✓ 通関書類 送付済 ' + esc(a.md(String(l.at).slice(0, 10))) + ' · ' + esc(a.staffName(l.by)) + '</button>';
    var miss = lacks(g);
    var tmark = t ? ' <small class="c01-ctest" title="' + esc('試験送付 ' + String(t.at).slice(0, 16).replace('T', ' ') + ' · ' + a.staffName(t.by)) + '">試験済 ' + esc(a.md(String(t.at).slice(0, 10))) + '</small>' : '';
    if (miss.length) return '<button class="c01-blocked c01-csend-off" data-csend="' + esc(iv.iv_no) + '" data-csend-off="1" title="' + esc('まだ送れません: ' + miss.join(' · ')) + '">通関書類送付</button>' + tmark;
    return '<button class="c01-btn-pri c01-csend" data-csend="' + esc(iv.iv_no) + '" title="D-03 で IV・PL・SI を作り、① 通関依頼 のメールに 全員に返信 します（送る前に確認窓）">✉ 通関書類送付</button>' + tmark;
  }

  /* ── COMPASS (読むだけ) — バイヤー · 前回の B/L ── */
  function dvGet(path) {
    var base = (C01.COMPASS && C01.COMPASS.dvUrl) || '';
    return LEENAI.auth.token('dataverse').then(function (tok) {
      return fetch(base + '/api/data/v9.2/' + path, { headers: { Authorization: 'Bearer ' + tok, Accept: 'application/json', 'OData-MaxVersion': '4.0', 'OData-Version': '4.0' } });
    }).then(function (r) { if (!r.ok) throw new Error('COMPASS ' + r.status); return r.json(); });
  }
  function buyerOf(ivNo) {
    return dvGet("cr49f_bookings?$filter=cr49f_invoice_no eq '" + String(ivNo).replace(/'/g, "''") + "'&$select=_cr49f_sale_contract_id_value").then(function (j) {
      var b = (j.value || [])[0];
      if (!b || !b._cr49f_sale_contract_id_value) return '';
      return dvGet('cr49f_sale_contracts(' + b._cr49f_sale_contract_id_value + ')?$select=_cr49f_buyer_id_value').then(function (s) { return s._cr49f_buyer_id_value || ''; });
    }).catch(function () { return ''; });
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
  var BROKER_PH = '（通関業者の会社名）';
  function brokerGuess(mail) {
    var last = mail && mail.last, s1 = mail && mail.s1;
    var our = String(C01.CUSTOMS.ourDomain || 'leenearcorp.com');
    var ext = [].concat(last ? [{ a: last.from, n: last.from_name }] : [], (last && last.to) || [], (s1 && s1.to) || []).filter(function (x) { return x.a && x.a.split('@')[1] !== our; });
    var p = ext[0] || { n: '', a: '' };
    var dom = String(p.a || '').split('@')[1] || '';
    /* 会社名 = 同じ通関業者 (メールのドメイン) へ前に送った時の 1 行目 (送付記録) · 無ければ 書き換え用の印 (残っていたら送れない) */
    var line = '';
    ((api().S.jik && api().S.jik.ivs) || []).forEach(function (iv) {
      records(iv).forEach(function (r) { if (!line && r.value.broker_dom === dom && r.value.broker_line) line = r.value.broker_line; });
    });
    return { broker: line || BROKER_PH, person: String(p.n || '').replace(/\s*[<(（].*$/, '').trim() || '（担当者名）', dom: dom };
  }
  function bodyText(st) {
    var me = api().S.me || {};
    var C = C01.CUSTOMS;
    return fill(C.body, { broker: st.broker, person: st.person }) + '\n\n' + fill(C.signature, { name: me.name || '', email: me.email || '' }) + '\n\n' + C.footer;
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
    if (off) { a.toast('まだ送れません: ' + lacks(g).join(' · '), 'error'); return; }
    st = { iv: ivNo, g: g, step: '準備中', mail: null, sent: [], d03: null, err: [], bl: '', blWhy: '', over: {}, ack: false, again: false, busy: false, body: null, broker: '', person: '' };
    a.S.modal = { kind: 'customs', iv: ivNo };
    draw();
    var src = a.S.src;
    var graphOk = a.graphMode() && typeof src.customsFindS1 === 'function';
    var pMail = graphOk ? src.customsFindS1(iv.bkg_no).catch(function (e) { st.err.push('① の検索: ' + e.message); return null; }) : Promise.resolve(null);
    var pSent = graphOk ? src.customsFindSent(ivNo).catch(function () { return []; }) : Promise.resolve([]);
    /* customs_bl.json = エンジンの meta.customs_bl がある時だけ読む (無いエンジンに 404 を出さない) */
    var pBl = (a.S.customsBl === undefined && a.S.meta && a.S.meta.customs_bl ? src.getJson(String(a.S.meta.customs_bl)).then(function (x) { a.S.customsBl = x; }, function () { a.S.customsBl = null; }) : Promise.resolve())
      .then(function () { return graphOk ? buyerOf(ivNo) : ''; });
    /* v0.3.65 (R12Y · #361): 形態 · タイプ 空欄の枠 (CT が入った枠だけ · COMPASS GET だけ) — 読めない = null (送信を止める) */
    var pFt = C01.COMPASS && C01.COMPASS.form_bales ? (graphOk && iv.booking_guid ? dvGet('crcf9_container_informations?$select=crcf9_container_no,crcf9_type,_crcf9_form_value&$filter=' +
      encodeURIComponent('_crcf9_booking_id_value eq ' + iv.booking_guid)).then(function (j) {
      var cells = {}; (j.value || []).forEach(function (c, i) { cells[i] = c; }); return C01.compass.formTypeBlank(cells);
    }).catch(function () { return null; }) : Promise.resolve(null)) : Promise.resolve(0);
    Promise.all([pMail, pSent, pBl, pFt]).then(function (r) {
      if (!st || st.iv !== ivNo) return;
      st.mail = r[0]; st.sent = r[1] || []; st.buyer = r[2] || ''; st.ftBlank = r[3];
      var h = st.buyer ? blHistory(st.buyer, ivNo) : [];
      var pb = pickBl(h);
      st.bl = pb.v; st.blWhy = pb.why;
      st.prevCons = h.length ? (h[h.length - 1].cons || '') : null;
      var gs = brokerGuess(st.mail); st.broker = gs.broker; st.person = gs.person; st.brokerDom = gs.dom;
      st.step = 'D-03';
      draw();
      return makePdf();
    }).catch(function (e) { if (st && st.iv === ivNo) { st.err.push(e.message); st.step = '完了'; draw(); } });
  }
  function makePdf() {
    var ivNo = st.iv;
    st.step = 'D-03'; st.d03 = null; draw();
    var o = { iv: ivNo, bl: st.bl, blWhy: st.blWhy };
    if (st.prevCons != null) o.prevCons = st.prevCons;
    Object.keys(st.over).forEach(function (k) { o[k] = st.over[k]; });
    return runD03(o).then(function (r) {
      if (!st || st.iv !== ivNo) return;
      st.d03 = r; st.step = '完了';
      if (st.pdfUrl) URL.revokeObjectURL(st.pdfUrl);
      st.pdfUrl = null;
      if (r && r.ok) {
        var bin = atob(r.pdf_b64), u8 = new Uint8Array(bin.length);
        for (var i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
        st.pdfUrl = URL.createObjectURL(new Blob([u8], { type: 'application/pdf' }));
      }
      draw();
    }).catch(function (e) { if (st && st.iv === ivNo) { st.d03 = { ok: false, error: e.message }; st.step = '完了'; draw(); } });
  }
  function recips() {
    var me = String((api().S.me || {}).email || '').toLowerCase();
    var L = st.mail && st.mail.last;
    if (!L) return { to: [], cc: [] };
    var seen = {};
    var pick = function (xs) { return xs.filter(function (x) { var k = x.a; if (!k || k === me || seen[k]) return false; seen[k] = 1; return true; }); };
    var to = pick([{ a: L.from, n: L.from_name }].concat(L.to || []));
    var cc = pick(L.cc || []);
    return { to: to, cc: cc };
  }
  function subject() {
    var s1 = st.mail && st.mail.s1;
    var base = s1 ? s1.subject.replace(/^\s*((re|fw|fwd|返信|転送)\s*[:：]\s*)+/i, '').trim() : '';
    return (testMode() ? '[test] ' : '') + '【通関書類送付_' + st.iv + '】Re: ' + base;
  }
  /* 送れない理由 (送信ボタンを止める) */
  function blockers() {
    var a = api(), out = [];
    var r = st.d03;
    if (!a.graphMode() || !(a.S.me && a.S.me.email) || typeof a.S.src.customsSend !== 'function') out.push('Microsoft 365 でログインした職員だけ送信できます');
    if (!st.mail) out.push('通関依頼メールが見つかりません（あなたのメールボックスに ① 通関依頼 がありません）');
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
    if (st.mail && !rc.to.length) out.push('宛先がありません');
    if (/（通関業者の会社名）|（担当者名）/.test(st.body || '')) out.push('本文の （通関業者の会社名） · （担当者名） を書き換えてください');
    if (/このメールは担当者確認後に送信してください/.test(st.body || '')) out.push('本文に 下書きの案内文 が残っています');
    if ((lastLive(a.ivById(st.iv)) || st.sent.some(function (x) { return !x.test; })) && !st.again) out.push('送付済みです — 再送付する時は 「もう一度送る」 にチェック');
    var red = r && r.ok ? r.warnings.filter(function (w) { return w.red; }) : [];
    if (red.length && !st.ack) out.push('赤の警告を確認してチェックしてください');
    if (st.busy) out.push('送信中');
    return out;
  }
  function draw() {
    var a = api(), esc = a.esc;
    if (!st || !a.S.modal || a.S.modal.kind !== 'customs') return;
    var iv = a.ivById(st.iv) || {};
    var r = st.d03, ready = st.step === '完了';
    var h = '<div class="c01-mh"><b>通関書類送付</b><span class="mono">' + esc(st.iv) + '</span><span class="t2">BKG ' + esc(iv.bkg_no || '') + ' · CY ' + esc(a.md(iv.cy_cut)) + '</span>' +
      (testMode() ? '<span class="c01-trial" data-ctrial>試験モード（宛先 = あなた 1 人だけ · 件名 [test] · 通関業者には送りません）</span>' : '<span class="c01-trial c01-live">本番（押した職員のメールから通関業者へ送ります）</span>') +
      '<span class="c01-flex"></span><button class="c01-btn-ghost2" data-close>閉じる</button></div><div class="c01-mbody c01-cbody">';
    if (!ready) {
      h += '<p class="c01-cstep">' + (st.step === 'D-03' ? '⟳ D-03 で IV・PL・SI を作成中…（COMPASS を読むだけ）' : '⟳ ① 通関依頼 メール · 送付記録 を確認中…') + '</p>';
    }
    st.err.forEach(function (e) { h += '<p class="c01-warn2">' + esc(e) + '</p>'; });
    // 送付済み
    var l = lastLive(iv), sentMail = st.sent.filter(function (x) { return !x.test; });
    if (l || sentMail.length) {
      h += '<div class="c01-cbox c01-cred"><b>送付済み</b> ' + (l ? esc(String(l.at).slice(0, 16).replace('T', ' ')) + ' · ' + esc(a.staffName(l.by)) + '（記録）' : '') +
        (sentMail.length ? ' · メール ' + sentMail.length + ' 通（' + esc(String(sentMail[0].at).slice(0, 16).replace('T', ' ')) + ' · ' + esc(sentMail[0].from_name || sentMail[0].from) + '）' : '') +
        '<label class="t2"><input type="checkbox" data-cagain' + (st.again ? ' checked' : '') + '> もう一度送る（再送付）</label></div>';
    }
    // 宛先
    var rc = recips();
    h += '<section class="c01-csec"><h4>宛先（① 通関依頼 の会話の一番新しいメールに 全員に返信）</h4>';
    if (!st.mail) {
      h += ready ? '<p class="c01-warn2">通関依頼メールが見つかりません — 送れません（自動の送信はしません）。① がほかの人のメールボックスにある時は その人が送ってください。</p>' + suggest() : '<p class="t2">確認中…</p>';
    } else {
      h += '<table class="c01-ctab"><tr><th>To</th><td>' + rc.to.map(function (x) { return esc(x.n ? x.n + ' <' + x.a + '>' : x.a); }).join('<br>') + '</td></tr>' +
        '<tr><th>CC</th><td>' + (rc.cc.map(function (x) { return esc(x.n ? x.n + ' <' + x.a + '>' : x.a); }).join('<br>') || '—') + '</td></tr>' +
        '<tr><th>返信先</th><td class="t2">' + esc(String(st.mail.last.at).slice(0, 16).replace('T', ' ')) + ' · ' + esc(st.mail.last.from_name || st.mail.last.from) + ' · 会話 ' + st.mail.n_conv + ' 通</td></tr></table>';
      if (testMode()) h += '<p class="c01-trial">試験モード: 実際は ' + esc((a.S.me || {}).email || '') + ' だけに送ります（上の宛先には送りません）</p>';
    }
    h += '</section>';
    // 件名 · 本文
    if (st.body == null && st.mail) st.body = bodyText(st);
    h += '<section class="c01-csec"><h4>件名</h4><div class="mono c01-csubj">' + esc(st.mail ? subject() : '—') + '</div>' +
      '<h4>本文（直せます · 下に 返信の元のメールが付きます）</h4><textarea class="c01-cbodytxt" data-cbody rows="12">' + esc(st.body || '') + '</textarea></section>';
    // 選んだ値
    h += '<section class="c01-csec"><h4>D-03 の選択（既定と理由 · 変えると PDF を作り直します）</h4>';
    if (r && r.ok) {
      var P = r.picks, av = r.si_avail || [];
      var sel = function (k, cur) { return '<select data-cpick="' + k + '">' + av.map(function (n) { return '<option value="' + n + '"' + (n === cur ? ' selected' : '') + '>S/I' + '①②③④'[n - 1] + '</option>'; }).join('') + '</select>'; };
      h += '<table class="c01-ctab">' +
        '<tr><th>S/I (IV·PL)</th><td>' + sel('ivSino', P.ivSino.v) + '</td><td class="t2' + (P.ivSino.red ? ' c01-cr' : '') + '">' + esc(P.ivSino.why) + '</td></tr>' +
        '<tr><th>S/I (SI)</th><td>' + sel('siSino', P.siSino.v) + '</td><td class="t2' + (P.siSino.red ? ' c01-cr' : '') + '">' + esc(P.siSino.why) + '</td></tr>' +
        '<tr><th>POD</th><td>' + [1, 2, 3].map(function (n) { return '<label><input type="checkbox" data-cpod="' + n + '"' + (P.pod.v.indexOf(n) >= 0 ? ' checked' : '') + '> ' + n + '</label>'; }).join(' ') + '</td><td class="t2' + (P.pod.red ? ' c01-cr' : '') + '">' + esc(P.pod.why) + '</td></tr>' +
        '<tr><th>FOB 運賃</th><td><label><input type="checkbox" data-cfreight' + (P.freight.v ? ' checked' : '') + '> 表示</label></td><td class="t2' + (P.freight.red ? ' c01-cr' : '') + '">' + esc(P.freight.why) + '</td></tr>' +
        '<tr><th>B/L 形態</th><td><select data-cbl><option value=""' + (!P.bl.v ? ' selected' : '') + '>（選んでください）</option>' +
        ['original', 'waybill', 'surrender'].map(function (k) { return '<option value="' + k + '"' + (P.bl.v === k ? ' selected' : '') + '>' + BL_LABEL[k] + '</option>'; }).join('') + '</select></td><td class="t2' + (!P.bl.v ? ' c01-cr' : '') + '">' + esc(st.blWhy) + '</td></tr></table>';
      // 警告
      var W = r.warnings || [];
      var cmp = cmpCompass(st.g, r.info);
      if (W.length || cmp.length) {
        h += '<ul class="c01-cwarn">' + W.map(function (w) { return '<li class="' + (w.red ? 'c01-cr' : 'c01-cy') + '">' + esc(w.item) + ': ' + esc(w.text) + '</li>'; }).join('') +
          cmp.map(function (x) { return '<li class="c01-cr">COMPASS ≠ 実況表: ' + esc(x) + '</li>'; }).join('') + '</ul>';
        if (W.some(function (w) { return w.red; })) h += '<label class="c01-cack"><input type="checkbox" data-cack' + (st.ack ? ' checked' : '') + '> 赤の警告を確認しました</label>';
      }
    } else if (r && !r.ok) {
      h += '<p class="c01-warn2">D-03: ' + esc(r.error || '失敗') + '</p>';
    } else h += '<p class="t2">作成中…</p>';
    h += '</section>';
    // PDF
    h += '<section class="c01-csec"><h4>添付 ' + (r && r.ok ? '<span class="mono">' + esc(r.file) + '</span> · ' + r.pages + ' ページ · ' + Math.round(r.bytes / 1024) + ' KB' : '') + '</h4>' +
      (st.pdfUrl ? '<iframe class="c01-cpdf" title="PDF" src="' + st.pdfUrl + '"></iframe>' : '<p class="t2">—</p>') + '</section>';
    h += '</div>';
    var bl = ready ? blockers() : ['準備中'];
    h += '<div class="c01-mf"><span class="t2 c01-cwhy" data-cwhy>' + esc(bl.length ? '送れません: ' + bl[0] + (bl.length > 1 ? '（ほか ' + (bl.length - 1) + '）' : '') : '送信できます') + '</span><span class="c01-flex"></span>' +
      '<button class="c01-btn-pri" data-csendgo' + (bl.length ? ' disabled' : '') + '>' + (testMode() ? '送信（試験 · 自分あて）' : '送信') + '</button></div>';
    a.showModal(h, 'c01-customs');
    bind();
  }
  function suggest() {
    /* #352: ① が無い時 = 「同じ港へ最近送った宛先」 を提案として出すだけ (自動の送信はしない) */
    var a = api(), esc = a.esc, iv = a.ivById(st.iv) || {}, seen = {}, out = [];
    ((a.S.jik && a.S.jik.ivs) || []).forEach(function (x) {
      if (x.pol !== iv.pol || x.iv_no === iv.iv_no) return;
      records(x).forEach(function (r) { if (!r.value.test) (r.value.to || []).concat(r.value.cc || []).forEach(function (m) { if (!seen[m]) { seen[m] = 1; out.push(m); } }); });
    });
    return out.length ? '<p class="t2">参考（同じ港 ' + esc(iv.pol || '') + ' へ最近送った宛先 · 提案だけ）: ' + out.slice(0, 8).map(esc).join(' · ') + '</p>' : '<p class="t2">参考: 同じ港へ最近送った記録はありません</p>';
  }
  function bind() {
    var m = document.getElementById('c01-modal');
    if (!m) return;
    var q = function (s) { return m.querySelector(s); };
    var ta = q('[data-cbody]');
    if (ta) ta.oninput = function () {
      st.body = ta.value;
      var bl = blockers(), go = q('[data-csendgo]'), w = q('[data-cwhy]');
      if (go) go.disabled = bl.length > 0;
      if (w) w.textContent = bl.length ? '送れません: ' + bl[0] + (bl.length > 1 ? '（ほか ' + (bl.length - 1) + '）' : '') : '送信できます';
    };
    var ag = q('[data-cagain]');
    if (ag) ag.onchange = function () { st.again = ag.checked; draw(); };
    var ak = q('[data-cack]');
    if (ak) ak.onchange = function () { st.ack = ak.checked; draw(); };
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
  function send() {
    var a = api();
    if (blockers().length) return;
    var r = st.d03, rc = recips(), iv = a.ivById(st.iv), test = testMode();
    var again = !!(lastLive(iv) || st.sent.some(function (x) { return !x.test; }));
    var subj = subject();
    var msg = (test ? '【試験】 あなた (' + a.S.me.email + ') だけに送ります。' : st.iv + ' の通関書類を 宛先 ' + rc.to.length + ' 件 · CC ' + rc.cc.length + ' 件 に送ります（あなたのメールから）。') +
      '\n件名: ' + subj + '\n添付: ' + r.file + '（' + r.pages + ' ページ）\nよろしいですか？';
    if (!window.confirm(msg)) return;
    if (again && !window.confirm('この IV はすでに送付済みです。本当にもう一度送りますか？')) return;
    st.busy = true; draw();
    var ivNo = st.iv;
    a.S.src.customsSend({ replyToId: st.mail.last.id, conv: null, subject: subj, html: bodyHtml(st.body || ''), pdf_b64: r.pdf_b64, file: r.file,
      to: rc.to.map(function (x) { return x.a; }), cc: rc.cc.map(function (x) { return x.a; }) }).then(function (res) {
      return a.writeAction(a.mkAction('customs_sent', { iv: ivNo, ct: null, field: null, source: null,
        value: { test: res.test, again: again, subject: subj, to: res.to, cc: res.cc, to_n: res.to.length, cc_n: res.cc.length,
          internet_message_id: res.internet_message_id, file: r.file, pages: r.pages, pdf_sha256: r.sha256, d03: r.version,
          picks: { ivSino: r.picks.ivSino.v, siSino: r.picks.siSino.v, pod: r.picks.pod.v, freight: r.picks.freight.v },
          bl: r.picks.bl.v, buyer_id: (r.info || {}).buyer_id || st.buyer || '', consignee: (r.info || {}).consignee || '',
          red: (r.warnings || []).filter(function (w) { return w.red; }).map(function (w) { return w.item; }),
          real_to_n: rc.to.length, real_cc_n: rc.cc.length, broker_dom: st.brokerDom || '', broker_line: String(st.body || '').split(/\r?\n/)[0].trim() } }));
    }).then(function () {
      a.toast((test ? '試験送信しました（あなた宛て）' : '送信しました') + ' — ' + ivNo, 'ok');
      st = null; a.closeModal(); a.render();
    }).catch(function (e) {
      if (st) { st.busy = false; draw(); }
      a.toast('送信できませんでした: ' + e.message, 'error');
    });
  }
  return { headerBtn: headerBtn, open: open, lacks: lacks, records: records, _pickBl: pickBl, _cmp: cmpCompass, _blockers: function () { return st ? blockers() : null; } };
})();
