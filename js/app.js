/* ✦ Powered by LEENAI Automation System — C-01 搬入票 TOOL 本体 (実況表 · 確認・入力 · 写真)
   画面の基準 = 試案 (relay\design\試案_実況表_Main / 試案_確認入力_Input)。データは C01.sources から読む (HTML・JS にデータなし)。 */
'use strict';
window.C01 = window.C01 || {};

(function () {
  var FIELD_LABEL = { ct: 'CT番号', seal: 'シール番号', n_w: '正味重量', t_w: '風袋重量', bales: 'ベール数', work_date: '作業日' };
  var FIELD_SHORT = { ct: 'CT', seal: 'シール', n_w: '正味', t_w: '風袋', bales: 'ベール', work_date: '作業日' };
  var REASON_SHORT = { SOURCE_MISMATCH: '値の違い', RANGE: '範囲外', MISSING_FIELD: '未読', NO_SLOT: '枠なし', SLOT_VANISHED: '枠なし',
    SLOT_CANDIDATES: '枠候補', SAME_COND_NOT_ELIGIBLE: '枠候補', UNIT_PRICE_DIFF: '単価', AUTO_CORRECTED: '自動補正', GROUP_HOLD: '写真', CT_INVALID: 'CT', SEAL_FORMAT: 'シール',
    WORK_DATE: '作業日', MIN_SOURCES: '確認1つ', SAME_CT_TWO_CONTAINERS: 'CT重複', BALES_UNSEEN: 'ベール数', WEIGHT_MISMATCH: '重量', TW_MISSING: '風袋',
    SLOT_CONFLICT: '枠の重なり', NEAR_DUP: '似たCT', NOT_IN_LIST: 'リスト外', LAYOUT_UNAPPROVED: '新しい書式', FIELD_RULE_NO_AUTO: '手確認', BKG_CONFLICT: 'BKG',
    UNREGISTERED_SENDER: '送信元', 'CUT後受信': 'CUT後',   /* v0.3.24 (R7X Part B · #212): 理由文言 v0.1 の短い表 */
    CONTRACT_MONTH_CONFLICT: '契約月', NW_OVER_LIMIT: '重量',   // R6M7: 사유 코드 27 (#115) · 28 (#125) — 문장은 엔진 reason_text
    PHOTO_SET_INCOMPLETE: '写真不足', PACKER_AUTOSTOP: '停止中' };   // R6M11: 사유 코드 29 (#129·#131) · 30 (#118) — 문장은 엔진 reason_text
  // R6M11 (#129 「実況表 줄に足りない写真の種類」): 사유 29 줄의 빠진 종류 (엔진 row.photo_missing) — 문장의 {없는 종류} 를 바꿈
  function reasonTexts(r) {
    var miss = r.photo_missing || '';
    return (r.reason_text || []).map(function (t) { return String(t).split('{없는 종류}').join(miss || '—'); });
  }
  /* v0.3.24 (R7X Part B · #212 · relay/design/理由文言_v0_1.md): 説明 1 行 (見える) · やること 1 行 (hover / クリック) — {A}{B} = 写真・搬入票・FAX・Excel・EIR・計量票・納品書 · {項目} = 項目名 */
  var REASON_TEXT = {
    SOURCE_MISMATCH: ['{A}と{B}で{項目}が違います。', '原本を見て正しい方を選んでください。'],
    MIN_SOURCES: ['{項目}を確かめた書類が{A}の1つだけです。', '{A}を見て値が合っていれば「確認する」。'],
    BALES_UNSEEN: ['ベール数がいつもの数と大きく違います。', '搬入票のベール数を確認してください。'],
    WEIGHT_MISMATCH: ['正味＋風袋が総重量と合いません。', '搬入票の3つの重量を確認してください。'],
    NW_OVER_LIMIT: ['正味重量が26,000kgを超えています。', '総重量を正味に書いた可能性 — 搬入票を確認。'],
    TW_MISSING: ['風袋重量が読めませんでした。', '搬入票か写真の風袋を入力してください。'],
    MISSING_FIELD: ['{項目}が読めませんでした。', '原本を見て入力してください。'],
    RANGE: ['{項目}がいつもの範囲の外です。', '原本の値を確認してください。'],
    CT_INVALID: ['CT番号の最後の数字（チェック）が合いません。', '写真のCTを見て直してください。'],
    SEAL_FORMAT: ['シール番号の形がこの船会社と違います。', '写真のシールを見て確認してください。'],
    AUTO_CORRECTED: ['読み違いを自動で直した値があります。', '直した値が原本と合うか見てください。'],
    WORK_DATE: ['作業日が受信日と大きく離れています。', '原本の作業日を見て ✎ 修正。'],
    NO_SLOT: ['この行が入る COMPASS 枠が見つかりません。', 'COMPASS の枠を確認してください。'],
    SLOT_CANDIDATES: ['入る枠の候補が2つ以上あります。', '「スロット変更」で枠を選んでください。'],
    SAME_COND_NOT_ELIGIBLE: ['同じ条件の枠が2つ以上あり選べません。', '「スロット変更」で枠を選んでください。'],
    SLOT_VANISHED: ['入っていた COMPASS 枠がなくなりました。', 'COMPASS の枠を確認してください。'],
    SLOT_CONFLICT: ['同じ枠に別のコンテナも入りそうです。', 'どちらの枠か選んでください。'],
    UNIT_PRICE_DIFF: ['同じ条件で単価・契約が違う枠があります。', '正しい契約の枠を選んでください。'],
    CONTRACT_MONTH_CONFLICT: ['メール件名の月とExcelの契約月が違います。', '契約月を確認して枠を選んでください。'],
    SAME_CT_TWO_CONTAINERS: ['同じCTの行が2つあります。', '同じコンテナなら「合わせる」。'],
    NEAR_DUP: ['1字だけ違うCTの行があります。', '写真のCTを見て確認してください。'],
    NOT_IN_LIST: ['業者のExcelにないCTです。', '写真のCTを確認してください。'],
    GROUP_HOLD: ['写真のまとまりがはっきりしません。', '写真を見て同じコンテナか確認。'],
    PHOTO_SET_INCOMPLETE: ['通関用写真が足りません（{ない種類}）。', '写真を見て「写真OK」か催促。'],
    PACKER_AUTOSTOP: ['この業者は自動OKを一時止めています。', '値を原本で確認してください。'],
    LAYOUT_UNAPPROVED: ['まだ確認していない書式の書類です。', '値を原本で確認してください。'],
    FIELD_RULE_NO_AUTO: ['この項目は人が確認する設定です。', '原本で確認してください。'],
    BKG_CONFLICT: ['書類によってBKG番号が違います。', '正しいBKGを確認してください。'],
    UNREGISTERED_SENDER: ['登録されていない送信元のメールです。', '当社の書類か確認してください。'],
    'CUT後受信': ['CYカット後の受信です。船会社に確認してください。', '']
  };
  /* 理由コード → {code, short, desc, todo} ({A}{B}{項目} を その行 · 項目の出典で埋める — 分からない時は 「書類」 「値」) */
  function reasonInfo(code, r, qs) {
    var t = REASON_TEXT[code];
    if (!t) return null;
    var item = '', A = '', B = '';
    (qs || []).forEach(function (q) {
      if (!item && q.field && FIELD_LABEL[q.field]) item = FIELD_LABEL[q.field];
      if (!A && q.values) { var ks = Object.keys(q.values); if (ks.length >= 2) { A = ks[0]; B = ks[1]; } else if (ks.length === 1) { A = B = ks[0]; } }
      if (code === 'MIN_SOURCES' && q.field_sources) {
        var one = [];
        Object.keys(q.field_sources).forEach(function (f) {
          var ag = (q.field_sources[f] || []).filter(function (x) { return x.agree; });
          if (ag.length === 1 && ['seal', 'n_w', 't_w', 'bales'].indexOf(f) >= 0) { one.push(FIELD_LABEL[f]); if (!A) A = ag[0].src; }
        });
        if (one.length && !item) item = one.join('・');
      }
    });
    var fill = function (x) { return String(x).split('{A}').join(A || '書類').split('{B}').join(B || '別の書類').split('{項目}').join(item || '値').split('{ない種類}').join((r && r.photo_missing) || '—'); };
    return { code: code, short: REASON_SHORT[code] || code, desc: fill(t[0]), todo: fill(t[1]) };
  }
  function reasonInfos(r, qs) {
    var rt = reasonTexts(r);
    return (r.reasons || []).map(function (c, i) { return reasonInfo(c, r, qs) || { code: c, short: REASON_SHORT[c] || c, desc: rt[i] || c, todo: '' }; });
  }
  /* 説明 1 行 + 「?」 (やること: hover = title · クリック / タッチ = その横に 1 行) */
  function reasonLine(ri) {
    return '<span class="c01-rdesc" data-rcode="' + esc(ri.code) + '">' + esc(ri.desc) + (ri.todo ? ' <button class="c01-rq" type="button" data-todo="' + esc(ri.todo) + '" title="' + esc(ri.todo) + '" aria-label="やること">?</button>' : '') + '</span>';
  }
  function reasonTitle(ris) { return ris.map(function (x) { return x.desc + (x.todo ? ' → ' + x.todo : ''); }).join('\n'); }
  document.addEventListener('click', function (e) {
    var b = e.target && e.target.closest ? e.target.closest('.c01-rq') : null;
    if (!b) return;
    e.preventDefault(); e.stopPropagation();
    var nx = b.parentNode.querySelector('.c01-rtodo');
    if (nx) { nx.parentNode.removeChild(nx); return; }
    var sp = document.createElement('span'); sp.className = 'c01-rtodo'; sp.textContent = '→ ' + b.getAttribute('data-todo');
    b.parentNode.appendChild(sp);
  }, true);
  var KIND = {
    '値の違い': { key: 'diff', color: 'var(--c-diff)' },
    '手入力': { key: 'manual', color: 'var(--c-manual)' },
    '写真のCT': { key: 'photo', color: 'var(--c-photo)', label: '写真の CT' },
    '未分類FAX': { key: 'fax', color: 'var(--c-fax)', label: '未分類 FAX' },
    '写真不足': { key: 'photo', color: 'var(--c-photo)' },    /* R6M13 (エンジン out_queue_photo_set): 理由 29 の行 — 写真を見て 確認する */
    '業者・IV未定': { key: 'hold', color: 'var(--c-fax)', label: '業者・IV 未定' },   /* v0.3.11 (R7J Part C · エンジン out_queue_hold): 保留中のメールの書類 */
    '他社搬入票候補': { key: 'foreign', color: 'var(--c-fax)', label: '他社搬入票候補' },   /* v0.3.20 (R7U Part D · 決定 #202 · エンジン s3_foreign_doc_v2): 他の会社の書類らしい */
    '同一候補': { key: 'same', color: 'var(--c-photo)', label: '同一コンテナ候補' },   /* v0.3.12 (R7K Part C · 決定 #150): FAX の行 ↔ 写真の行 (エンジン same_cand) */
    '値の確認': { key: 'diff', color: 'var(--c-diff)', label: '値の確認' }   /* v0.3.24 (R7X Part A · エンジン out_queue_value_check): 再確認 なのに他の項目が無い行 — 値を見て 確認する */
  };
  var VCHK = '値の確認';
  var SAME = '同一候補';
  var HOLD = '業者・IV未定';
  var FOREIGN = '他社搬入票候補';
  var FOREIGN_WHY = { '荷主': '荷主がリニアではない', '船社': '船社がこのブッキングと違う', '品目': '品目が古紙ではない', 'シール形式': 'シールの形がこの船社と違う' };
  function foreignWhy(q) {
    var s = String(q.note || ''), i = s.indexOf(':');
    var ws = (i >= 0 ? s.slice(i + 1) : s).split('・').filter(Boolean);
    return 'BKG が当社のどのブッキングにもない' + (ws.length ? ' · ' + ws.map(function (w) { return FOREIGN_WHY[w] || w; }).join(' · ') : '');
  }
  var HOLD_TEXT = { PACKER_MISMATCH: '業者が合いません', PACKER_MULTI: '業者が複数', BKG_MULTI: 'BKG が複数', BKG_UNKNOWN: 'BKG が見つかりません',
    NO_BKG: 'BKG が読めません', UNREGISTERED_SENDER: '送信元が未登録' };
  /* v0.3.11 (R7J Part A): 確認・入力 = コンテナ 1 台 = 1 枚 (CT が分からない項目は 書類 1 つ = 1 枚) */
  var VALUE_KINDS = { '値の違い': 1, '手入力': 1 };
  var DOC_KINDS = { '値の違い': 1, '手入力': 1, '未分類FAX': 1, '業者・IV未定': 1, '他社搬入票候補': 1 };
  var PHOTO_SET = '写真不足';
  function photoSetAction(q, ct) {     /* R6M13: 値はそのまま (CT を確認) — エンジンが「写真不足 OK」実績を記録 (#131 ③) */
    return mkAction('confirm_value', { iv: q.iv_no, ct: ct, field: 'ct', value: ct, source: '写真', queue_id: q.queue_id });
  }
  var VALUE_FIELDS = ['seal', 'n_w', 't_w', 'bales'];

  var S = {
    src: null, info: null, jik: null, queue: null, photos: {}, staff: null, me: null,
    view: 'main', port: 'mine', ports: [], filter: 'all', showUnarrived: true,
    sel: null, picks: {}, panelInput: '', lb: null,
    actions: [], mine: [], lastPoll: null, lastLoad: null,
    qkind: 'all', qiv: null, qsel: null, qvals: {}, qchoice: {}, qfocus: null, zoom: 100, rot: 0, qmsg: {}, pdfPage: {}, showOldFax: false, qfile: {},
    timer: null, remind: null, modal: null,
    asks: [], askOpen: {}, askDraft: {}, askTimer: null     /* v0.3.25 (R7Z Part A): AI 相談 */
  };
  C01.state = S;

  /* ── ユーティリティ ── */
  function esc(s) { return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); }
  function num(v) { return v == null || v === '' ? '' : (typeof v === 'number' ? v.toLocaleString('en-US') : esc(v)); }
  function md(d) { return d ? String(d).slice(5).replace('-', '/') : ''; }
  /* v0.3.12 (R7K Part G · 決定 #153): 作業日 — 搬入票の値はそのまま (黒) · 無い時 (メール未着の枠 · 搬入票待ちの行) は 枠の COMPASS 予定日を 灰色 ·
     今日以前は 太字の赤 (旧 実況表と同じ)。予定日は表示だけ — Compass入力 · 判定 · 値の比較には使わない (#103) */
  function slotPlan(iv, guid) { var sl = (iv.slots || []).filter(function (x) { return guid && x.slot_guid === guid; })[0]; return sl && sl.work_date ? sl.work_date : null; }
  /* v0.3.22 (R7V F-2 · 決定 #188): エンジン info 「作業日要確認」 = 枠は作業日なしで決まった行 — 作業日はカードにせず 灰色 「?」 だけ */
  function wdDoubt(r) { return ((r && r.info) || []).filter(function (x) { return String(x).indexOf('作業日要確認') === 0; })[0] || ''; }
  function wdCell(v, plan, doubt) {
    if (v && doubt) return '<td><span class="c01-wddoubt" title="' + esc('作業日が読み違いの可能性があります（枠は作業日なしで決まっています · 入力・判定には使いません） · ' + doubt) + '">' + esc(md(v)) + '?</span></td>';
    if (v) return '<td>' + esc(md(v)) + '</td>';
    if (!plan) return '<td></td>';
    var today = (S.info && S.info.today) || jstNow().slice(0, 10);
    var past = String(plan).slice(0, 10) <= today;
    return '<td><span class="c01-wdplan' + (past ? ' past' : '') + '" title="' + esc('COMPASS の予定日（表示のみ · 入力・判定には使いません）' + (past ? ' · 予定日を過ぎています' : '')) + '">' + esc(md(plan)) + '</span></td>';
  }
  function $(id) { return document.getElementById(id); }
  /* v0.3.21 (R7V F-1): 상단 공통 바 (.ln-header · sticky z-index 50) 높이 → 옆 패널 top · height. 바가 없으면 0 */
  function setHdrH() {
    var h = document.querySelector('.ln-header'), b = 0;
    if (h) { var rc = h.getBoundingClientRect(); b = Math.max(0, Math.round(rc.bottom)); }
    document.documentElement.style.setProperty('--c01-hdr-h', b + 'px');
    return b;
  }
  window.addEventListener('resize', function () { if (document.querySelector('.c01-side')) setHdrH(); });
  function jstNow() {
    var d = new Date(Date.now() + 9 * 3600 * 1000);
    return d.toISOString().slice(0, 19) + '+09:00';
  }
  function actionId() { return 'a' + Date.now().toString(36) + Math.random().toString(36).slice(2, 10); }
  function rowKey(iv, r) { return iv.iv_no + '|' + (r.ct || r.container_id) + '|' + (r.packer || iv.packer || ''); }
  function addDays(iso, n) { var d = new Date(iso + 'T00:00:00Z'); d.setUTCDate(d.getUTCDate() + n); return d.toISOString().slice(0, 10); }
  /* 写真・原本を非同期で読む読み先 (local フォルダ選択 · graph) は data-rel + resolveUrl で表示 */
  function isFolder() { return !!(S.src && typeof S.src.resolveUrl === 'function'); }
  function imgTag(rel, cls, alt) {
    if (!rel) return '';
    if (isFolder()) return '<img class="' + cls + '" data-rel="' + esc(rel) + '" alt="' + esc(alt || '') + '">';
    return '<img class="' + cls + '" src="' + esc(S.src.fileUrl(rel)) + '" alt="' + esc(alt || '') + '">';
  }
  /* v0.3.3 (R7C): 読めなかった理由 (graph) → 画面の文 (空白のままにしない) */
  function fileErrText(rel) {
    var e = S.src && typeof S.src.fileError === 'function' ? S.src.fileError(rel) : '';
    if (e === 'notfound') return 'SharePoint にまだありません';
    if (e === 'forbidden') return '見る権限がありません (403)';
    if (e === 'network') return '通信できませんでした';
    return '読めませんでした' + (e ? ' (' + e.replace('http', '') + ')' : '');
  }
  /* v0.3.15 (R7N Part F): 描き直し = 変わった所だけ差し替え (スクロール位置 · 開いたカード · 描いた PDF · 読んだ画像はそのまま)。
     要素ごとに 元の HTML (_h) と 開始タグ (_a) を覚え、新しい HTML と同じなら残す · 開始タグが同じなら中だけ比べる (depth 段まで) · 違えば差し替え */
  function markH(el, depth) {
    el._h = el.outerHTML;
    el._a = el.cloneNode(false).outerHTML;
    if (depth > 0) for (var c = el.firstElementChild; c; c = c.nextElementSibling) markH(c, depth - 1);
  }
  function patchKids(oldP, newP, depth) {
    var ok = [].slice.call(oldP.childNodes), nk = [].slice.call(newP.childNodes);
    var same = ok.length === nk.length && ok.every(function (o, i) {
      var n = nk[i];
      return o.nodeType === n.nodeType && (o.nodeType !== 1 || (o.tagName === n.tagName && o._h !== undefined));
    });
    if (!same) {
      nk.forEach(function (n) { if (n.nodeType === 1) markH(n, Math.max(0, depth - 1)); });
      while (oldP.firstChild) oldP.removeChild(oldP.firstChild);
      nk.forEach(function (n) { oldP.appendChild(n); });
      return;
    }
    nk.forEach(function (n, i) {
      var o = ok[i];
      if (n.nodeType !== 1) { if (o.nodeValue !== n.nodeValue) o.nodeValue = n.nodeValue; return; }
      var nh = n.outerHTML;
      if (o._h === nh) return;
      if (depth > 1 && o._a === n.cloneNode(false).outerHTML) { patchKids(o, n, depth - 1); o._h = nh; return; }
      markH(n, Math.max(0, depth - 1));
      oldP.replaceChild(n, o);
    });
  }
  function setHtml(root, html, depth) {
    var t = document.createElement('template');
    t.innerHTML = html;
    patchKids(root, t.content, depth || 5);
  }
  function hydrate(root) {
    (root || document).querySelectorAll('[data-pdf]').forEach(function (el) { if (el._hyd) return; el._hyd = 1; drawPdf(el); });
    (root || document).querySelectorAll('.c01-doc.img').forEach(function (box) {        /* v0.3.18: 読み済みの画像 (キャッシュ) は今 合わせる */
      var im = box.querySelector('img.c01-docimg');
      if (im && im.complete && im.naturalWidth) docFit(box);
    });
    if (!isFolder()) return;
    (root || document).querySelectorAll('[data-rel]').forEach(function (el) {
      if (el._hyd) return;
      el._hyd = 1;
      var rel = el.getAttribute('data-rel');
      S.src.resolveUrl(rel).then(function (u) {
        if (u) { el.src = u; return; }
        el.setAttribute('data-missing', '1');                       /* 画像の代わりに理由を出す */
        var sp = document.createElement('span');
        sp.className = 'c01-filemiss';
        sp.textContent = fileErrText(rel);
        if (el.parentNode) el.parentNode.insertBefore(sp, el);
        el.style.display = 'none';
      });
    });
  }

  /* ── v0.3.2 (R7B): PDF は pdf.js で画面の中に描く (ブラウザの PDF ビューアーが無効でも見える) ──
     読み先 = graph / フォルダ選択 は blob URL · ローカルサーバーは URL。pdf.js が読めない時は従来の iframe に戻る。 */
  var PDF = { lib: null, docs: {} };
  function loadPdfJs() {
    if (window.pdfjsLib) return Promise.resolve(window.pdfjsLib);
    if (PDF.lib) return PDF.lib;
    PDF.lib = new Promise(function (res, rej) {
      var sc = document.createElement('script');
      sc.src = C01.PDF.lib;
      sc.onload = function () {
        if (!window.pdfjsLib) return rej(new Error('pdf.js なし'));
        window.pdfjsLib.GlobalWorkerOptions.workerSrc = C01.PDF.worker;
        res(window.pdfjsLib);
      };
      sc.onerror = function () { rej(new Error('pdf.js を読めませんでした')); };
      document.head.appendChild(sc);
    });
    PDF.lib.catch(function () { PDF.lib = null; });
    return PDF.lib;
  }
  function pdfUrl(rel) { return isFolder() ? S.src.resolveUrl(rel) : Promise.resolve(S.src.fileUrl(rel)); }
  /* v0.3.3 (R7C): 「別タブで開く」 — クリックの中で先に空のタブを開く (ポップアップブロック対策 · 旧版は読み込み後に window.open で止められていた)
     graph = SharePoint の表示画面 (webUrl) · ローカル = ファイル URL。開けない時はタブを閉じて理由を出す */
  function openTab(rel) {
    if (!rel) return;
    var w = window.open('about:blank', '_blank');
    if (!w) { toast('ブラウザがポップアップを止めました — このサイトのポップアップを許可してください', 'warn'); return; }
    try { w.opener = null; w.document.title = '開いています…'; w.document.body.textContent = '開いています…'; } catch (e) { /* 別オリジンなら何もしない */ }
    var p = (S.src && typeof S.src.webUrl === 'function') ? S.src.webUrl(rel) : pdfUrl(rel);
    p.then(function (u) {
      if (u) { w.location.href = u; return; }
      try { w.close(); } catch (e) { /* なし */ }
      toast('開けませんでした: ' + fileErrText(rel), 'error');
    });
  }
  function pdfDoc(rel) {
    if (PDF.docs[rel]) return PDF.docs[rel];
    var p = Promise.all([loadPdfJs(), pdfUrl(rel)]).then(function (x) {
      if (!x[1]) throw new Error('原本を読めませんでした');
      return x[0].getDocument({ url: x[1] }).promise;
    });
    PDF.docs[rel] = p;
    p.catch(function () { delete PDF.docs[rel]; });
    return p;
  }
  /* v0.3.15 (R7N Part G-3): エンジンが判読の時に見つけた ページの向き (時計回り 0 · 90 · 180 · 270) — 最初から正しい向きで表示
     形 (どちらでも): files[] / docs[] の rotation = 数 (その項目の page のページ · page が無い = 全ページ · 画像) または { "ページ番号": 角度 } */
  /* v0.3.24 (R7X Part G-3 · 형님 18:0x): 人が ⟳ で回した角度を覚える (ファイル sha16 + ページ · このブラウザ) — エンジンの向きに足す · 確認・入力 · 📄 タブ */
  var ROTMEM_KEY = 'c01_rotmem';
  function rotMemAll() { try { return JSON.parse(localStorage.getItem(ROTMEM_KEY) || '{}') || {}; } catch (e) { return {}; } }
  function rotMemKey(sha, page) { return sha ? String(sha) + '#' + (page || 1) : null; }
  function rotMemGet(k) { var m = rotMemAll(); return k && m[k] ? (+m[k] || 0) % 360 : 0; }
  function rotMemSet(k, v) {
    if (!k) return;
    var m = rotMemAll();
    if (v % 360) m[k] = v % 360; else delete m[k];
    var ks = Object.keys(m);
    if (ks.length > 500) ks.slice(0, ks.length - 500).forEach(function (x) { delete m[x]; });
    try { localStorage.setItem(ROTMEM_KEY, JSON.stringify(m)); } catch (e) { /* 保存できない時は覚えない */ }
  }
  function normRot(v) { v = Math.round(+v || 0); v = ((v % 360) + 360) % 360; return v % 90 === 0 ? v : 0; }
  function rotMap(f) {
    var r = f && f.rotation, m = {};
    if (r == null) return m;
    if (typeof r === 'object') { Object.keys(r).forEach(function (k) { var v = normRot(r[k]); if (v) m[String(k)] = v; }); return m; }
    var v = normRot(r);
    if (v) m[f.page ? String(f.page) : '*'] = v;
    return m;
  }
  function rotOf(m, page) { return m[String(page || 1)] !== undefined ? m[String(page || 1)] : (m['*'] || 0); }
  /* v0.3.18 (R7S #1 · #2): 見ているページの記憶 = 項目 + ファイル + 項目のページ ごと (前は ファイルごと → 1 つの PDF に何台もある搬入票で
     別のコンテナの項目を開いても 前に見たページ (1 ページ目) のまま)。項目のページ (files[].page) で開き、ほかのページも ‹ › で見られる */
  function pdfKey(q, f) { return (q && q.queue_id ? q.queue_id : '') + '|' + (f && f.path || '') + '#' + (f && f.page || ''); }
  /* v0.3.18 (R7S #3): 画像の回転 (左上を軸に回して 箱の左上へ戻す) — 0 · 90 · 180 · 270 */
  var DOC_TF = { 0: 'none', 90: 'rotate(90deg) translateY(-100%)', 180: 'rotate(180deg) translate(-100%, -100%)', 270: 'rotate(270deg) translateX(-100%)' };
  function docFit(box) {
    if (!box || !box.classList || !box.classList.contains('img')) return;
    var inner = box.querySelector('.c01-docrot'), img = box.querySelector('img.c01-docimg');
    if (!inner || !img) return;
    var r = +box.getAttribute('data-rot') || 0, w = +box.getAttribute('data-w') || inner.offsetWidth;
    var h = img.style.display === 'none' ? 0 : inner.offsetHeight;      /* 回す前の高さ (transform は offset に入らない) */
    if (!h) return;
    if (r % 180) { box.style.width = h + 'px'; box.style.height = w + 'px'; } else { box.style.width = w + 'px'; box.style.height = h + 'px'; }
    box.setAttribute('data-fit', r + ':' + w + 'x' + h);
  }
  document.addEventListener('load', function (e) {
    var t = e.target;
    if (t && t.tagName === 'IMG' && t.classList.contains('c01-docimg')) docFit(t.closest('.c01-doc'));
  }, true);
  function pdfTag(rel, page, thumb, rots, pkey, bw) {
    var rj = rots && Object.keys(rots).length ? JSON.stringify(rots) : '';
    return '<div class="c01-pdf' + (thumb ? ' thumb' : '') + '" data-pdf="' + esc(rel) + '" data-page="' + (+page || 1) + '"' + (thumb ? ' data-thumb="1"' : '') +
      (pkey ? ' data-pkey="' + esc(pkey) + '"' : '') + (bw && bw !== 640 ? ' data-bw="' + (+bw) + '"' : '') +
      (rj ? ' data-rots="' + esc(rj) + '"' : '') + (thumb ? '' : ' data-view="' + S.zoom + ':' + S.rot + '"') +
      '><canvas></canvas><span class="c01-pdfmsg">' + (thumb ? '' : '読み込み中…') + '</span></div>';
  }
  function drawPdf(el) {
    var rel = el.getAttribute('data-pdf'), thumb = el.getAttribute('data-thumb') === '1';
    var want = +el.getAttribute('data-page') || 1;
    var rots = {};
    try { rots = JSON.parse(el.getAttribute('data-rots') || '{}') || {}; } catch (e) { rots = {}; }
    pdfDoc(rel).then(function (doc) {
      var n = doc.numPages, pg = Math.min(Math.max(1, want), n);
      el.setAttribute('data-pages', n);
      if (!thumb) { S.pdfPage[el.getAttribute('data-pkey') || rel] = pg; var lab = $('pdf-pg'); if (lab) lab.textContent = 'p.' + pg + ' / ' + n; }
      return doc.getPage(pg).then(function (page) {
        var base = rotOf(rots, pg);
        var rot = (thumb ? 0 : S.rot) + base;
        el.setAttribute('data-base-rot', base);
        var r = (page.rotate + rot) % 360;
        var v1 = page.getViewport({ scale: 1, rotation: r });
        var cssW = thumb ? 150 : Math.round((+el.getAttribute('data-bw') || 640) * S.zoom / 100);
        var dpr = window.devicePixelRatio || 1;
        var vp = page.getViewport({ scale: cssW / v1.width * dpr, rotation: r });
        var cv = el.querySelector('canvas');
        cv.width = Math.round(vp.width); cv.height = Math.round(vp.height);
        cv.style.width = cssW + 'px'; cv.style.height = Math.round(vp.height / dpr) + 'px';
        return page.render({ canvasContext: cv.getContext('2d'), viewport: vp }).promise.then(function () {
          el.setAttribute('data-drawn', pg + ':' + rot);
          var m = el.querySelector('.c01-pdfmsg'); if (m) m.remove();
        });
      });
    }).catch(function () {
      /* pdf.js が使えない → 従来の iframe (ブラウザの PDF ビューアー)。v0.3.3: ファイル自体が読めない時は iframe にせず理由を出す */
      pdfUrl(rel).then(function (u) {
        if (!u) {
          el.setAttribute('data-missing', '1');
          el.innerHTML = thumb ? '<span class="c01-pdfmsg">PDF ' + esc(fileErrText(rel)) + '</span>' : '<p class="c01-filemiss big">原本: ' + esc(fileErrText(rel)) + '</p>';
          return;
        }
        if (thumb) { el.innerHTML = '<span class="c01-pdfmsg">PDF</span>'; return; }
        el.setAttribute('data-fallback', '1');
        el.innerHTML = '<iframe class="c01-docpdf" src="' + esc(u) + (want > 1 ? '#page=' + want : '') + '" title="原本"></iframe>';
      });
    });
  }
  function toast(msg, type) {
    if (window.LEENAI && LEENAI.toast) LEENAI.toast(msg, type || 'info');
    else console.log(msg);
  }

  /* ── 担当港 (決定 #95: pol_staff の 担当・補助、マスターにない港 = '*' 行) ── */
  function staffList() {
    var m = S.staff || {};
    return m.staff || [];
  }
  /* v0.3.18 (R7S #16): pol_staff の 担当・補助 の値 = 職員コード · メール · 名前 (name_ja) のどれでも · 1 つの欄に複数 (; , 、 / 改行 空白) でも合う。
     比べる形 = NFKC (全角 → 半角) · 空白 (全角空白も) を除く · 大文字小文字を区別しない */
  function normWho(s) {
    s = String(s == null ? '' : s);
    if (s.normalize) s = s.normalize('NFKC');
    return s.replace(/[\s\u3000]+/g, '').toLowerCase();
  }
  function whoTokens(v) {
    var out = {};
    var add = function (x) { var n = normWho(x); if (n) out[n] = 1; };
    [].concat(v == null ? [] : v).forEach(function (cell) {
      if (cell == null || typeof cell === 'object') return;
      var s = String(cell);
      if (s.normalize) s = s.normalize('NFKC');
      add(s);                                                          /* 欄全体 (名前の中の空白は除いて比べる) */
      s.split(/[;,、，；\/／\r\n]+/).forEach(function (part) {
        add(part);
        var w = part.split(/[\s\u3000]+/).filter(Boolean);
        w.forEach(add);                                                /* 空白区切りの複数 */
        for (var i = 0; i + 1 < w.length; i++) add(w[i] + w[i + 1]);   /* 姓 名 の間に空白がある名前 */
      });
    });
    return out;
  }
  function isAdmin() {
    if (!S.me) return false;
    if (S.me.admin) return true;
    var me = S.me;
    return staffList().some(function (s) { return s.admin && ((me.code && s.code === me.code) || (me.email && String(s.email || '').toLowerCase() === String(me.email).toLowerCase())); });
  }
  function myIds() {
    var ids = {};
    var add = function (x) { var n = normWho(x); if (n && n !== normWho('職員マスター未登録')) ids[n] = 1; };
    var me = S.me || {};
    add(me.code); add(me.email); if (!me.unregistered) add(me.name);
    var em = String(me.email || '').toLowerCase();
    staffList().forEach(function (s) {
      if ((me.code && s.code === me.code) || (em && String(s.email || '').toLowerCase() === em)) { add(s.code); add(s.email); add(s.name); add(s.name_ja); add(s.name_en); }
    });
    ((window.LEENAI && LEENAI.STAFF) || []).forEach(function (s) {               /* 共通ファイルの職員一覧の名前でも */
      if (s && ((me.code && s.staffCode === me.code) || (em && String(s.email || '').toLowerCase() === em))) { add(s.name); add(s.staffCode); add(s.email); }
    });
    return ids;
  }
  function myPorts() {
    if (!S.me) return null;
    /* v0.3.20 (R7U Part F-1 · 決定 #201): 管理者 (職員マスター portal_admin) = 「自分の担当」 の代わりに全港 · 職員は今までどおり */
    if (isAdmin()) return { ports: [], star: false, known: [], why: '', all: true, admin: true };
    if (!S.staff || S.staff.polError) return { ports: [], star: false, known: [], why: 'read', all: true };   /* 読めない = これまでどおり全港 */
    var items = S.staff.items || [];
    var mine = [], star = false, ids = myIds();
    items.forEach(function (it) {
      /* v0.3.16 (R7O Part D): 共通マスター pol_staff の列 = staff (担当) · assist (補助) — 前は main/sub だけ見ていて 「自分の担当（なし）」 */
      var who = whoTokens([].concat(it.staff || it.main || it['担当'] || [], it.assist || it.sub || it['補助'] || []));
      var hit = Object.keys(who).some(function (x) { return ids[x]; });
      if (!hit) return;
      if (it.pol === '*') star = true; else if (mine.indexOf(it.pol) < 0) mine.push(it.pol);
    });
    return { ports: mine, star: star, known: items.map(function (it) { return it.pol; }).filter(function (p) { return p !== '*'; }),
      why: mine.length || star ? '' : (items.length ? 'nohit' : 'empty') };
  }
  /* v0.3.7 (R7D Part U-2): 担当港 = 複数選択 (港ボタンをトグル) · 「全港」 = 全部 · 「自分の担当」 = マスター 担当・補助 ·
     選んだ組み合わせはブラウザに記憶 (localStorage c01_ports · 使えない環境では記憶しないだけ) */
  var PORT_KEY = 'c01_ports';
  function savePorts() {
    try { localStorage.setItem(PORT_KEY, JSON.stringify({ port: S.port, ports: S.ports || [] })); } catch (e) { /* なし */ }
  }
  function loadPorts() {
    var j = null;
    try { j = JSON.parse(localStorage.getItem(PORT_KEY) || 'null'); } catch (e) { j = null; }
    if (!j || ['mine', 'all', 'set'].indexOf(j.port) < 0) return false;
    if (j.port === 'mine' && !S.me) return false;
    S.port = j.port;
    S.ports = Array.isArray(j.ports) ? j.ports.filter(function (x) { return typeof x === 'string'; }) : [];
    if (S.port === 'set' && !S.ports.length) S.port = 'all';
    return true;
  }
  function pickPort(p) {
    if (p === 'all' || p === 'mine') { S.port = p; S.ports = []; }
    else {
      var cur = S.port === 'set' ? (S.ports || []).slice() : [];
      var i = cur.indexOf(p);
      if (i >= 0) cur.splice(i, 1); else cur.push(p);
      S.ports = cur;
      S.port = cur.length ? 'set' : 'all';
    }
    savePorts();
  }
  function portOn(p) { return p === 'all' || p === 'mine' ? S.port === p : (S.port === 'set' && (S.ports || []).indexOf(p) >= 0); }
  function portOk(pol) {
    if (S.port === 'all') return true;
    if (S.port === 'set') return (S.ports || []).indexOf(pol) >= 0;
    if (S.port === 'mine') {
      var mp = myPorts();
      if (!mp || mp.all) return true;
      if (mp.ports.indexOf(pol) >= 0) return true;
      return mp.star && mp.known.indexOf(pol) < 0;
    }
    return pol === S.port;
  }

  /* ── _actions 重ね表示 (他の人 = 30 秒ごと · 自分 = すぐ) ── */
  function allActions() {
    var seen = {}, out = [];
    S.actions.concat(S.mine).forEach(function (x) {
      var a = x.action || x;
      if (!a || !a.action_id || seen[a.action_id]) return;
      seen[a.action_id] = 1;
      out.push(a);
    });
    out.sort(function (a, b) { return a.at < b.at ? -1 : a.at > b.at ? 1 : 0; });
    return out;
  }
  function overlay() {
    var byQueue = {}, byCell = {}, rejected = {}, bySlot = {}, excl = {};
    var qById = {};
    ((S.queue && S.queue.items) || []).forEach(function (q) { qById[q.queue_id] = q; });
    /* v0.3.11 (R7J Part B): 「元に戻す」 (undo) された 「搬入票ではない」 は無かったことに */
    var undone = {};
    allActions().forEach(function (a) { if (a.action === 'undo' && a.value && a.value.action_id) undone[a.value.action_id] = a; });
    allActions().forEach(function (a) {
      if (a.action === 'undo' || undone[a.action_id]) return;
      if (a.action === 'not_hannyuhyo' && a.value && a.value.sha16) a.value.sha16.forEach(function (h) { excl[h] = { queue_id: a.queue_id, action_id: a.action_id }; });
      var q = a.queue_id ? qById[a.queue_id] : null;
      if (a.queue_id) {
        if (!byQueue[a.queue_id]) byQueue[a.queue_id] = { win: a, later: [] };
        else byQueue[a.queue_id].later.push(a);
      }
      if (a.action === 'slot_change' && a.value && a.value.slot_guid) {
        bySlot[a.iv + '|' + a.ct] = a;                 /* #109 ②: 同じ CT の後の変更が上書き */
        if (a.value.swap_ct) bySlot[a.iv + '|' + a.value.swap_ct] = { action_id: a.action_id, action: a.action, iv: a.iv, ct: a.value.swap_ct, by: a.by, at: a.at,
          value: { slot_guid: a.value.slot_before, slot_before: a.value.slot_guid, swap_ct: a.ct } };   /* 入れ替え相手 = 前の枠へ (1 件の記録で 2 台) */
      }
      if (a.action === 'confirm_value' || a.action === 'manual_input') {
        var cid = q && q.container_id ? q.container_id : null;
        var key = (cid || (a.iv + '|' + a.ct)) + '|' + a.field;
        if (!byCell[key] || a.mode === 'edit') byCell[key] = a;           /* v0.3.23 (R7W Part A): 修正 (mode edit) = 後の値が勝つ */
        else if (a.queue_id && byQueue[a.queue_id] && byQueue[a.queue_id].win !== a) rejected[a.action_id] = 1;
      }
    });
    return { byQueue: byQueue, byCell: byCell, bySlot: bySlot, excl: excl, undone: undone };
  }
  function sameDone(pid, ov) { var w = ov && ov.byQueue ? ov.byQueue[pid] : null; return !!(w && !(ov.undone && ov.undone[w.win.action_id])); }
  function queueState(q, ov) {
    /* → {done, by, mineLost, engine, act, aid} (act · aid = 完了にした処理 — 「元に戻す」 に使う) */
    if (q.resolved && !(ov.undone && ov.undone[q.resolved.action_id])) return { done: true, by: q.resolved.by, engine: true, act: q.resolved.action, aid: q.resolved.action_id,
      mineLost: q.superseded && S.me && q.superseded.some(function (x) { return x.by === S.me.email; }) && q.resolved.by !== S.me.email };
    var w = ov.byQueue[q.queue_id];
    if (!w) return { done: false };
    var lost = S.me && w.win.by !== S.me.email && w.later.some(function (a) { return a.by === S.me.email; });
    return { done: true, by: w.win.by, engine: false, mineLost: lost, act: w.win.action, aid: w.win.action_id };
  }
  /* v0.3.11 (R7J Part B): 「搬入票ではない」 を押したファイルだけの別の項目は出さない (押した項目は 完了 に残る) */
  function exclHidden(q, ov) {
    var fs = (q.files || []).filter(function (f) { return f && f.sha16; });
    if (!fs.length || !ov.excl) return false;
    return fs.every(function (f) { return ov.excl[f.sha16] && ov.excl[f.sha16].queue_id !== q.queue_id; });
  }
  function cardKey(q) {
    if (q.kind === FOREIGN) return 'q:' + q.queue_id;
    if (q.container_id) return 'c:' + q.container_id;
    if (q.kind === '未分類FAX' || q.kind === HOLD) return 'q:' + q.queue_id;
    var f0 = (q.files || [])[0];
    return 'f:' + ((f0 && f0.sha16) || q.queue_id);
  }
  function buildCards(items, ov) {
    var by = {}, out = [];
    items.forEach(function (q) {
      var k = cardKey(q);
      if (!by[k]) { by[k] = { key: k, items: [] }; out.push(by[k]); }
      by[k].items.push(q);
    });
    out.forEach(function (cd) {
      cd.kinds = [];
      cd.items.forEach(function (q) { if (cd.kinds.indexOf(q.kind) < 0) cd.kinds.push(q.kind); });
      cd.open = cd.items.filter(function (q) { return !queueState(q, ov).done; });
      cd.done = cd.open.length === 0;
    });
    return out;
  }
  function cardOf(cards, qid) { return (cards || []).filter(function (cd) { return cd.items.some(function (q) { return q.queue_id === qid; }); })[0] || null; }
  function cardIv(cd) {
    var s = {};
    cd.items.forEach(function (q) { if (q.iv_no) s[q.iv_no] = 1; (q.kind === HOLD ? q.candidates || [] : []).forEach(function (x) { s[x] = 1; }); });
    return Object.keys(s);
  }
  /* 確認・入力 の項目 (港 · 古い FAX · 搬入票ではない を除く) と カード */
  /* v0.3.12 (R7K Part C · 決定 #150): 実況表の same_cand (FAX の行 ↔ 写真の行) = 確認・入力 の 1 枚 (queue_id = pair_id) · 自動では合わせない */
  function sameItems() {
    var out = [];
    ((S.jik && S.jik.ivs) || []).forEach(function (iv) {
      iv.rows.forEach(function (r) {
        var sc = r.same_cand;
        if (!sc || sc.role !== 'fax') return;
        var p = iv.rows.filter(function (y) { return y.container_id === sc.partner; })[0];
        if (!p) return;
        out.push({ queue_id: sc.pair_id, kind: SAME, iv_no: iv.iv_no, ct: p.ct, field: null, container_id: null, files: [], cy_cut: iv.cy_cut,
          same: { fax: r, photo: p, ct_diff: sc.ct_diff, seal_diff: sc.seal_diff } });
      });
    });
    return out;
  }
  /* v0.3.15 (R7N Part G): IV · 行 を引く (データが変わった時だけ作り直す) */
  function ivIndex() {
    if (S._ivIdxFor !== S.jik) {
      var m = {}, rm = {};
      ((S.jik && S.jik.ivs) || []).forEach(function (iv) { m[iv.iv_no] = iv; (iv.rows || []).forEach(function (r) { if (r.container_id) rm[r.container_id] = { iv: iv, r: r }; }); });
      S._ivIdx = m; S._rowIdx = rm; S._ivIdxFor = S.jik;
    }
    return S._ivIdx;
  }
  function rowByCid(cid) { ivIndex(); return cid ? S._rowIdx[cid] || null : null; }
  function qItems() { return (S.queue && S.queue.items) || []; }
  /* G-2: この行と結び付いた書類 = 項目のファイル + 同じコンテナの別の項目のファイル (IV の書類全部は出さない — G-2-0) */
  function linkedFiles(q) {
    var out = [], seen = {};
    var add = function (f, sib) {
      if (!f || !f.path) return;
      var k = f.path + '#' + (f.page || '');
      if (seen[k]) return;
      seen[k] = 1;
      out.push(sib ? Object.assign({}, f, { sib: true }) : f);
    };
    (q.files || []).forEach(function (f) { add(f, false); });
    if (q.container_id) qItems().forEach(function (y) { if (y !== q && y.container_id === q.container_id && DOC_KINDS[y.kind]) (y.files || []).forEach(function (f) { add(f, true); }); });
    return out;
  }
  /* G-1: 搬入票がまだ届いていない行 (受信中 · has_docs なし · 書類なし) の 手入力 は カードにしない — 実況表 「搬入票待ち」 · 催促の対象だけ。
     同一候補がある行は 「同一コンテナ候補」 のカードで案内 (sameItems) */
  function noDocWait(q) {
    if (q.kind !== '手入力') return false;
    if (linkedFiles(q).length) return false;
    var x = rowByCid(q.container_id);
    if (!x) return true;                                   /* 行も書類も無い 手入力 = 原本を見られない */
    return x.r.status === '受信中' && (x.r.has_docs === false || x.r.has_docs === 0);
  }
  function queueCards(ov) {
    var all = qItems().concat(sameItems()).filter(function (q) { return queuePortOk(q) && !faxHidden(q) && !exclHidden(q, ov) && !noDocWait(q); });
    return { all: all, cards: buildCards(all, ov) };
  }

  /* ── 実況表のデータ組み立て ── */
  function statusOf(r, iv, ov) {
    var st = r.status;
    var human = Object.assign({}, r.human || {});
    var edited = false;
    VALUE_FIELDS.concat(['ct', 'work_date']).forEach(function (f) {
      if (human[f] && ov.undone && ov.undone[human[f].action_id]) delete human[f];     /* v0.3.23 (R7W): 元に戻した値 (エンジン反映前) */
      var a = ov.byCell[r.container_id + '|' + f] || ov.byCell[iv.iv_no + '|' + r.ct + '|' + f];
      var newer = a && human[f] && a.mode === 'edit' && a.action_id !== human[f].action_id && String(a.at || '') > String(human[f].at || '');
      if (a && (!human[f] || newer)) human[f] = { value: a.value, source: a.source, by: a.by, at: a.at, action_id: a.action_id, overlay: true, override: a.override || null, mode: a.mode || null };
      if (human[f] && human[f].overlay && human[f].source === '手入力' && String(human[f].value) !== String(r[f] == null ? '' : r[f])) edited = true;
    });
    if (st === '自動OK' && (edited || (r.info || []).some(function (s) { return /^AUTO_OK_EDITED\(/.test(s); }))) st = '確認済';   /* v0.3.23 (R7W Part A): 自動OK を人が修正 = 確認済（手入力） */
    if (st === '再確認') {
      var open = ((S.queue && S.queue.items) || []).filter(function (q) { return q.container_id === r.container_id && !queueState(q, ov).done; });
      var had = ((S.queue && S.queue.items) || []).some(function (q) { return q.container_id === r.container_id; });
      if (had && !open.length && Object.keys(human).length) st = '確認済';
    }
    return { st: st, human: human };
  }
  /* v0.3.9: 枠 GUID → 並び順 (COMPASS seq が全部あれば seq · 無ければ slots の並び) */
  function slotSeq(iv) {
    var m = {}, sl = iv.slots || [];
    var allSeq = sl.length > 0 && sl.every(function (s) { return typeof s.seq === 'number'; });
    sl.forEach(function (s, i) { if (s.slot_guid) m[s.slot_guid] = allSeq ? s.seq : i; });
    (iv.mail_missing || []).forEach(function (mm, i) { if (mm.slot_guid && m[mm.slot_guid] === undefined) m[mm.slot_guid] = typeof mm.seq === 'number' ? mm.seq : 1e6 + i; });
    return m;
  }
  function buildGroups() {
    var ov = overlay();
    var out = [], cnt = { check: 0, compass: 0, remind: 0 }, no = 0;
    var today = (S.info && S.info.today) || '';
    var ivs = ((S.jik && S.jik.ivs) || []).filter(function (iv) { return portOk(iv.pol) && ivLive(iv); })
      .slice().sort(function (a, b) { return (a.cy_cut || '') < (b.cy_cut || '') ? -1 : (a.cy_cut || '') > (b.cy_cut || '') ? 1 : (a.iv_no < b.iv_no ? -1 : 1); });
    ivs.forEach(function (iv) {
      var rows = iv.rows.map(function (r) {
        var x = statusOf(r, iv, ov);
        var vals = {};
        ['ct', 'seal', 'n_w', 't_w', 'bales', 'work_date'].forEach(function (f) { vals[f] = x.human[f] ? x.human[f].value : r[f]; });
        var openQ = ((S.queue && S.queue.items) || []).filter(function (q) { return q.container_id === r.container_id && !queueState(q, ov).done; });
        var short = openQ.length && openQ[0].field ? FIELD_SHORT[openQ[0].field] : (REASON_SHORT[(r.reasons || [])[0]] || (r.reasons || [])[0] || '');
        var rTitle = x.st === '再確認' ? reasonTitle(reasonInfos(r, openQ)) : '';    /* v0.3.24 (R7X Part B): 説明 → やること (hover) */
        var photoMiss = (r.reasons || []).indexOf('PHOTO_SET_INCOMPLETE') >= 0 && r.photo_missing ? r.photo_missing : '';
        if (photoMiss && !(openQ.length && openQ[0].field)) short = REASON_SHORT.PHOTO_SET_INCOMPLETE + '（' + photoMiss + '）';
        var wait = '';
        if (x.st === '受信中') {
          wait = r.has_docs === false ? '搬入票待ち' : r.has_photos === false ? '写真待ち' : photoMiss ? '写真待ち（' + photoMiss + '）' : '受信待ち';
          if (r.work_date && today && r.work_date < today) wait += ' · ' + Math.round((Date.parse(today) - Date.parse(r.work_date)) / 86400000) + '日';
        }
        /* v0.3.10 (R7I Part D): 足りない半分が受信済みメール (保留 · 対象外 · 別の束) にありそう = 「受信中・候補あり」 (本当に未着とは分けて表示 · 催促しない) */
        var cand = x.st === '受信中' && r.cand ? r.cand : null;
        if (cand) wait = '受信中・候補あり' + (cand.level === 'bkg' ? '（BKG）' : '') + ' · ' + wait;
        var candTitle = cand ? (cand.level === 'ct' ? '同じ CT' : '同じ BKG') + 'の' + (r.has_docs === false ? '搬入票' : '写真') + 'らしいファイルが受信済みメールにあります（' +
          (cand.where || []).join(' / ') + (cand.recv && cand.recv.length ? ' · ' + cand.recv.join(' / ') : '') + '）— 未着ではない可能性 · 催促の対象外' : '';
        return { kind: 'row', key: rowKey(iv, r), r: r, st: x.st, human: x.human, vals: vals, short: short, rTitle: rTitle, wait: wait, openQ: openQ, candTitle: candTitle };
      });
      var unarr = (iv.mail_missing || []).map(function (m) {
        return { kind: 'missing', key: iv.iv_no + '|missing|' + m.slot_guid, m: m, st: 'メール未着', vals: { work_date: m.work_date }, wait: 'メール未着' };
      });
      var isOk = function (x) { return x.st === '自動OK' || x.st === '確認済'; };
      var allOk = rows.length > 0 && rows.filter(isOk).length === rows.length && !unarr.length;
      var hasCheck = rows.some(function (x) { return x.st === '再確認'; });
      /* v0.2.0: 催促 = エンジンの催促下書き (remind.json — 現行リマインダーの基準) がある IV。remind.json が無い時は R5 と同じ (受信中・メール未着) */
      var remind = S.remind ? (remindsOf(iv.iv_no).length > 0 || !!((S.remind.cand || {})[iv.iv_no])) : (rows.some(function (x) { return x.st === '受信中'; }) || unarr.length > 0);
      var compassDone = compassIsDone(iv);                  /* v0.3.19: 最後の記録が「元に戻す」なら未入力 */
      cnt.check += rows.filter(function (x) { return x.st === '再確認'; }).length;
      if (allOk && !compassDone) cnt.compass += 1;
      if (remind) cnt.remind += 1;
      var onlyUn = rows.length === 0 && unarr.length > 0;
      if (onlyUn && !S.showUnarrived) return;
      if (S.filter === 'check' && !hasCheck) return;
      if (S.filter === 'compass' && !(allOk && !compassDone)) return;
      if (S.filter === 'remind' && !remind) return;
      /* v0.3.9 (R7E 形님 ②): 行の順 = COMPASS 枠の順 (slots[].seq · 無ければ slots の並び)。枠が決まった行はその枠の位置 · メール未着の枠も同じ位置 ·
         枠のない行 (未割当) はそのブッキングの一番下。台数 = 枠の数 (未割当の行を別に数えない · 二重に数えない)。No = ブッキングごとに 1 から (D-42) */
      var seqOf = slotSeq(iv);
      var slotted = [], free = [];
      rows.forEach(function (x) { (x.r.slot_guid && seqOf[x.r.slot_guid] !== undefined ? slotted : free).push(x); });
      free.forEach(function (x) { x.unassigned = true; });
      /* v0.3.15 (R7N Part H-4 · 決定 #166): 台数 N = COMPASS の枠の数そのまま (エンジン slots = booking_cache の枠 · TOOL で増やさない)。
         v0.3.18 (R7S #15 · 決定 #182): 表示する行 (枠のある行 + 枠のない行) が COMPASS の枠の数より多い = 枠のない行 (未割当) を 全部 「COMPASS 枠外」 (赤) ·
         空き枠が残っていても同じ (前の 「空き枠があれば 未割当 は赤にしない · 超えた数だけ赤」 はやめた)。行 ≤ 枠 = 枠外なし */
      /* v0.3.20 (R7U Part A-3 · 決定 #195): 同じ IV で同じ CT · 同じシールの行 = 赤 「CT重複」 · 「シール重複」 (人の値を含む · 空は数えない) */
      var dupOf = function (f) {
        var m = {};
        rows.forEach(function (x) { var k = String(x.vals[f] || '').replace(/[\s-]/g, '').toUpperCase(); if (k) (m[k] = m[k] || []).push(x); });
        Object.keys(m).forEach(function (k) { if (m[k].length > 1) m[k].forEach(function (x) { x['dup_' + f] = m[k].filter(function (y) { return y !== x; }); }); });
      };
      dupOf('ct'); dupOf('seal');
      var nSlots = (iv.slots && iv.slots.length) || iv.slots_n || 0;
      var over = nSlots && rows.length > nSlots ? free.length : 0;
      if (over) free.forEach(function (x) { x.over = true; });
      var freeIn = free.filter(function (x) { return !x.over; }), freeOver = free.filter(function (x) { return x.over; });
      /* v0.3.11 (R7J Part C-2): 同じブッキングに枠の決まっていない行があれば、空き枠は「未着」ではなく「割当待ち」 (行の数まで · 枠外の行は数えない) */
      unarr.slice(0, freeIn.length).forEach(function (x) { x.st = '割当待ち'; x.wait = '割当待ち'; x.waitTitle = 'このブッキングに枠の決まっていない行（未割当）があります — メールは届いている可能性'; });
      var shownUn = S.showUnarrived ? unarr : [];
      var bySeq = slotted.concat(shownUn).map(function (x, i) { return { x: x, k: seqOf[x.kind === 'missing' ? x.m.slot_guid : x.r.slot_guid], i: i }; })
        .sort(function (a, b) { var ka = a.k === undefined ? 1e9 : a.k, kb = b.k === undefined ? 1e9 : b.k; return ka - kb || a.i - b.i; })
        .map(function (e) { return e.x; });
      var list = bySeq.concat(freeIn).concat(freeOver);
      var ivNo = 0;
      list.forEach(function (x) { ivNo += 1; x.no = ivNo; no += 1; });
      var okN = rows.filter(function (x) { return isOk(x) && !x.over; }).length;
      var total = nSlots || rows.length + unarr.length;
      out.push({ iv: iv, rows: list, okN: okN, total: total, over: over, nFree: free.length, allOk: allOk, onlyUn: onlyUn, remind: remind, compassDone: compassDone });
    });
    return { groups: out, cnt: cnt, ov: ov };
  }

  /* ── 描画: ナビ ── */
  function renderNav() {
    var open = queueCards(overlay()).cards.filter(function (cd) { return !cd.done; }).length;     /* v0.3.11: 枚数 (コンテナ 1 台 = 1 枚) */
    var t = (S.info && S.info.today) || '';
    var upd = S.lastLoad ? S.lastLoad.toTimeString().slice(0, 5) : '--:--';
    var staffOpts = '<option value="">担当者を選ぶ</option>' + staffList().map(function (s) {
      return '<option value="' + esc(s.code) + '"' + (S.me && S.me.code === s.code ? ' selected' : '') + '>' + esc(s.name || s.code) + '</option>';
    }).join('');
    setHtml($('c01-nav'),
      '<nav class="c01-tabs" aria-label="画面">' +
      '<button id="tab-main" class="c01-tab' + (S.view === 'main' ? ' on' : '') + '">実況表</button>' +
      '<button id="tab-input" class="c01-tab' + (S.view === 'input' ? ' on' : '') + '">確認・入力 <span class="c01-badge" id="badge-open">' + open + '</span></button>' +
      '</nav>' +
      '<span class="c01-sub">' + esc(t) + ' 時点 · 最終更新 <span id="c01-upd">' + upd + '</span>（自動更新）</span>' +
      '<span class="c01-flex"></span>' +
      '<button id="help-open" class="c01-btn-sub c01-helpbtn" title="この TOOL の使い方（並行期間中の注意）">使い方</button>' +
      (graphMode()
        ? '<span class="c01-local c01-sp" title="SharePoint ドキュメント / ' + esc(C01.SOURCE.spRoot) + ' から読んでいます (ログインした人の権限)">SharePoint · ' + esc(C01.SOURCE.spRoot) + '</span>' +
          '<span class="c01-me' + (S.me && S.me.unregistered ? ' c01-warn' : '') + '" id="me-name"' + (S.me && S.me.unregistered ? ' title="ログインしたメール (' + esc(S.me.email) + ') が職員マスター (staff) にありません — マスターの確認が必要"' : '') + '>担当者 ' + esc(S.me ? S.me.name : '?') + '</span>'
        : '<span class="c01-local" title="データは選んだフォルダから読んでいます (SharePoint には接続しません)">ローカルプレビュー · ' + esc(S.info ? S.info.label : '') + '</span>' +
          '<label class="c01-me">担当者 <select id="me-select" aria-label="担当者">' + staffOpts + '</select></label>'), 3);
    $('tab-main').onclick = function () { S.view = 'main'; render(); };
    $('tab-input').onclick = function () { S.view = 'input'; if (!S.qsel) { var f = openQueue()[0]; S.qsel = f ? f.queue_id : null; } render(); };
    $('help-open').onclick = openHelp;
    if ($('me-select')) $('me-select').onchange = function (e) {
      var s = staffList().filter(function (x) { return x.code === e.target.value; })[0] || null;
      S.me = s ? { code: s.code, name: s.name || s.code, email: s.email } : null;
      try { localStorage.setItem('c01_local_me', S.me ? S.me.code : ''); } catch (er) { /* なし */ }
      S.port = S.me ? 'mine' : 'all';
      S.ports = [];
      savePorts();
      updateUserChip();
      render();
    };
  }
  function graphMode() { return !!(S.info && S.info.mode === 'graph'); }
  function updateUserChip() {
    if (graphMode()) return;                                         /* graph: ヘッダーは LEENAI_COMMON (ログインした人) */
    var un = $('ln-username'), av = $('ln-avatar');
    if (un) un.textContent = S.me ? S.me.name : '（担当者未選択）';
    if (av) av.textContent = S.me ? S.me.code.slice(0, 2) : '--';
  }

  /* ── 描画: 実況表 ── */
  function renderMain() {
    var b = buildGroups();
    var mp = myPorts();
    var ports = [['mine', '自分の担当' + (mp ? (mp.admin ? '（全港 · 管理者）' : '（' + (mp.ports.join(' · ') || 'なし') + (mp.star ? ' · *' : '') + '）') : '（担当者未選択）')], ['all', '全港']];
    /* v0.3.18 (R7S #16): 「なし」 の理由 (小さく) — マスターに該当なし / マスターを読めない (この時は これまでどおり全港を表示) */
    var MP_WHY = { nohit: '担当港マスターに該当なし', empty: '担当港マスターが空です', read: '担当港マスターを読めません（全港を表示）' };
    var mpWhy = mp && mp.why ? MP_WHY[mp.why] : '';
    var pols = {};
    ((S.jik && S.jik.ivs) || []).forEach(function (iv) { if (iv.pol) pols[iv.pol] = 1; });
    /* 港チップの順: pol_staff に順番の列 (order) があればその順、無ければ名前順 (v0.2.0 — 今のマスターには順番の列なし) */
    var ord = {};
    (((S.staff && S.staff.items) || [])).forEach(function (it) { if (it.order !== undefined && it.order !== null && it.order !== '') ord[it.pol] = +it.order; });
    Object.keys(pols).sort(function (a, b) {
      var oa = ord[a] !== undefined ? ord[a] : Infinity, ob = ord[b] !== undefined ? ord[b] : Infinity;
      return oa !== ob ? oa - ob : (a < b ? -1 : a > b ? 1 : 0);
    }).forEach(function (p) { ports.push([p, p]); });
    var html = '<div class="c01-bar">' +
      '<span class="c01-lab">担当港</span>' +
      ports.map(function (p) {
        return '<button class="c01-chip' + (portOn(p[0]) ? ' on' : '') + '" data-port="' + esc(p[0]) + '" aria-pressed="' + (portOn(p[0]) ? 'true' : 'false') + '">' + esc(p[1]) +
          (p[0] === 'mine' && mpWhy ? ' <small class="c01-mpwhy" id="mp-why" title="' + esc(mpWhy + ' — ⚙ マスター「POL 担当」の 担当・補助 に 職員コード · メール · 名前 のどれかが必要') + '">' + esc(mpWhy) + '</small>' : '') + '</button>';
      }).join('') +
      '<span class="c01-hint">（港は複数選べます · 自分の担当 = ⚙ マスター「POL 担当」の 担当・補助 · 選んだ組み合わせは記憶）</span>' +
      '<span class="c01-flex"></span>' +
      '<div class="c01-filters">' +
      '<button class="c01-f c01-f-check' + (S.filter === 'check' ? ' on' : '') + '" data-filter="check">要確認 ' + b.cnt.check + '台</button>' +
      '<button class="c01-f c01-f-compass' + (S.filter === 'compass' ? ' on' : '') + '" data-filter="compass">Compass入力待ち ' + b.cnt.compass + '件</button>' +
      '<button class="c01-f c01-f-remind' + (S.filter === 'remind' ? ' on' : '') + '" data-filter="remind">催促候補 ' + b.cnt.remind + '件</button>' +
      '<label class="c01-chk"><input type="checkbox" id="show-unarrived"' + (S.showUnarrived ? ' checked' : '') + '>メール未着も表示</label>' +
      '</div></div>';
    /* v0.3.2 (R7B): 横スクロール 0 — 列幅は colgroup (table-layout: fixed) · 長い列 (品目・圧縮業者・Plant) は 2 行まで + title で全文 */
    html += '<div class="c01-tablewrap" id="jikkyou-wrap"><table class="c01-table" id="jikkyou-table"><colgroup>' +
      '<col class="w-no"><col class="w-cy"><col class="w-iv"><col class="w-item"><col class="w-ct"><col class="w-seal"><col class="w-nw"><col class="w-tw"><col class="w-bl">' +
      '<col class="w-wd"><col class="w-inc"><col class="w-pk"><col class="w-pl"><col class="w-ph"><col class="w-st"></colgroup><thead><tr>' +
      '<th class="c-no">No</th><th>CYカット</th><th>Invoice番号</th><th>品目</th><th>CT番号</th><th>シール番号</th>' +
      '<th class="r">正味重量</th><th class="r">風袋重量</th><th class="r">ベール数</th><th>作業日</th><th>条件</th><th>圧縮業者</th><th>Plant</th><th>写真</th><th>状況</th>' +
      '</tr></thead>';
    b.groups.forEach(function (g) {
      var iv = g.iv;
      html += '<tbody data-iv="' + esc(iv.iv_no) + '"><tr class="c01-ivrow"><td colspan="15"><div class="c01-ivhead">' +
        '<span class="b">▼ CY ' + esc(md(iv.cy_cut)) + '</span>' +
        '<span class="pol">' + esc(iv.pol || '') + '</span>' +
        '<span class="mono">' + esc(iv.iv_no) + '</span>' +
        '<span class="t2">BKG ' + esc(iv.bkg_no || '') + '</span>' +
        '<span class="t2">' + (g.onlyUn ? '0/' + g.total + '台 · メール未着' : g.okN + '/' + g.total + '台') + '</span>' +
        (g.over ? '<span class="c01-overhead" title="行が COMPASS の枠 ' + g.total + ' より多い — 枠のない行 ' + g.over + ' 行 = 間違って作られた行 · 割り当ての間違いの可能性（赤の行）">枠外 ' + g.over + '</span>' : '') +
        '<span class="c01-flex"></span>' +
        (iv.hold_docs ? '<button class="c01-btn-sub c01-holdlink" data-holdiv="' + esc(iv.iv_no) + '" title="保留中のメールにこの IV の書類らしいファイルがあります（確認・入力「業者・IV 未定」）">候補書類あり (' + (+iv.hold_docs) + ')</button>' : '') +
        (g.remind ? '<button class="c01-btn-sub" data-remind="' + esc(iv.iv_no) + '">✉ 催促</button>' : '') +
        (g.compassDone ? '<button class="c01-done" data-compass="' + esc(iv.iv_no) + '" title="Compass入力の記録 · 元に戻す">✓ 入力済</button>' :
          g.allOk ? '<button class="c01-btn-pri" data-compass="' + esc(iv.iv_no) + '">⬇ Compass入力</button>' :
            (!g.onlyUn ? '<button class="c01-blocked" data-compass="' + esc(iv.iv_no) + '" title="全台が 自動OK / 確認済 になると入力できます（比較表だけ見られます）">Compass入力（未完了あり）</button>' : '')) +
        '</div></td></tr>';
      g.rows.forEach(function (x) {
        var cls = x.st === '自動OK' || x.st === '確認済' ? 'ok' : x.st === '再確認' ? 'check' : 'wait';
        if (S.sel === x.key) cls += ' sel';
        if (x.kind === 'missing') {
          html += '<tr class="c01-row wait missing" data-key="' + esc(x.key) + '"><td class="c-no">' + x.no + '</td><td>' + esc(iv.cy_cut || '') + '</td>' + c1(iv.iv_no, 'mono') +
            cv(rowVal(iv, x.m, 'item')) + '<td></td><td></td><td></td><td></td><td></td>' + wdCell(null, x.m.work_date) + cv(rowVal(iv, x.m, 'incoterms'), true) +
            cv(rowVal(iv, x.m, 'packer')) + cv(rowVal(iv, x.m, 'plant')) + '<td></td><td class="c-st"><span class="st-wait"' + (x.waitTitle ? ' title="' + esc(x.waitTitle) + '"' : '') + '>' + esc(x.wait || 'メール未着') + '</span></td></tr>';
          return;
        }
        var r = x.r, v = x.vals;
        var photos = r.photos || 0;
        var ctCell = photos > 0 ? '<button class="c01-ctlink" data-photos="' + esc(x.key) + '" title="クリックで写真を新しいタブに表示 (Shift+クリック = この画面で表示)">' + esc(v.ct || '') + '</button>' : '<span class="mono">' + esc(v.ct || '') + '</span>';
        var hmark = function (f) { return x.human[f] ? ' <span class="c01-hm" title="確認済 ' + esc(x.human[f].by || '') + '">✓</span>' : ''; };
        var stCell = (x.st === '自動OK' || x.st === '確認済') && valueEditOn() ? '<button class="st-ok c01-okedit" data-okedit="' + esc(x.key) + '" title="クリックで値を修正（確認済（手入力）に変わります）">' + x.st + '</button>' :
          x.st === '自動OK' || x.st === '確認済' ? '<span class="st-ok">' + x.st + '</span>' :
          x.st === '再確認' ? '<button class="c01-checkbtn" data-sel="' + esc(x.key) + '"' + (x.rTitle ? ' title="' + esc(x.rTitle) + '"' : '') + '>⚠ 要確認 · ' + esc(x.short) + '</button>' :
            '<span class="st-wait' + (x.candTitle ? ' c01-cand' : '') + '"' + (x.candTitle ? ' title="' + esc(x.candTitle) + '"' : '') + '>' + esc(x.wait) + '</span>';
        if (x.dup_seal) stCell = '<span class="c01-over" title="' + esc('同じシール番号の行があります（' + x.dup_seal.map(function (y) { return y.no + '行目'; }).join(' · ') + '）— 入力の間違い · 読み違いの可能性') + '">シール重複</span> ' + stCell;
        if (x.dup_ct) stCell = '<span class="c01-over" title="' + esc('同じ CT 番号の行があります（' + x.dup_ct.map(function (y) { return y.no + '行目'; }).join(' · ') + '）— 同じコンテナの再送 · 読み違いの可能性') + '">CT重複</span> ' + stCell;
        if (x.over) stCell = '<span class="c01-over" title="行が COMPASS の枠の数より多く、この行には枠がありません — 間違って作られた行・割り当ての間違いの可能性があります（台数には数えません）">COMPASS 枠外</span> ' + stCell;
        else if (x.unassigned) stCell = '<span class="c01-unassigned" title="COMPASS の枠がまだ決まっていない行（台数は枠の数で数えます）">未割当</span> ' + stCell;
        if (r.same_cand && !sameDone(r.same_cand.pair_id, b.ov)) stCell += ' <button class="c01-samebadge" data-same="' + esc(r.same_cand.pair_id) + '" title="' +
          esc(r.same_cand.role === 'fax' ? '写真の行と同じコンテナかもしれません（FAX の CT・シールの読み違い）— クリックで確認' : 'FAX の行と同じコンテナかもしれません — クリックで確認') + '">同一候補</button>';
        stCell += rowInfo(iv, r, x, b.ov) + (canSlotChange() && r.ct ? ' <button class="c01-slotbtn" data-slot="' + esc(x.key) + '" title="スロット変更">⇄</button>' : '');
        html += '<tr class="c01-row ' + cls + (x.unassigned ? ' unassigned' : '') + (x.over ? ' over' : '') + '" data-key="' + esc(x.key) + '" data-status="' + esc(x.st) + '"><td class="c-no">' + x.no + '</td><td>' + esc(iv.cy_cut || '') +
          '</td>' + c1(iv.iv_no, 'mono') + cv(rowVal(iv, r, 'item')) + '<td class="c-cut">' + ctCell + '</td><td class="mono c-cut" title="' + esc(v.seal || '') + '">' + esc(v.seal || '') + hmark('seal') +
          '</td><td class="r num">' + num(v.n_w) + hmark('n_w') + '</td><td class="r num">' + num(v.t_w) + hmark('t_w') + '</td><td class="r num">' + num(v.bales) + hmark('bales') +
          '</td>' + wdCell(v.work_date, x.st === '受信中' && r.has_docs === false ? slotPlan(iv, slotOf(iv, r, b.ov) || r.slot_guid) : null, x.human.work_date ? '' : wdDoubt(r)) +
          cv(rowVal(iv, r, 'incoterms'), true) + cv(rowVal(iv, r, 'packer')) + cv(rowVal(iv, r, 'plant')) + '<td' +
          (photoAlert(photos, rowVal(iv, r, 'packer').v) ? ' class="c-ph c01-ph-alert" title="' + esc(photoAlertText(photos, rowVal(iv, r, 'packer').v)) + '"' : ' class="c-ph"') + '>' +
          (photos > 0 ? '<button class="c01-phbtn" data-photos="' + esc(x.key) + '" title="新しいタブで写真を表示 (Shift+クリック = この画面で表示)">📷 ' + photos + '枚</button>' : '0枚') +
          docCell(r, x.key) + '</td><td class="c-st">' + stCell + '</td></tr>';
      });
      html += '</tbody>';
    });
    if (!b.groups.length) html += '<tbody><tr><td colspan="15" class="c01-empty">表示する IV がありません（担当港・絞り込みを確認してください）</td></tr></tbody>';
    html += '</table></div>';
    html += '<div class="c01-legend"><span><i class="lg ok"></i>自動OK / 確認済</span><span><i class="lg check"></i>要確認</span><span><i class="lg wait"></i>受信待ち · メール未着</span>' +
      (b.groups.some(function (g) { return g.over; }) ? '<span><i class="lg over"></i>COMPASS 枠外（行が枠の数より多い時の 枠のない行）</span>' : '') +
      '<span class="c01-flex"></span><span>✦ Powered by LEENAI Automation System</span></div>';
    setHtml($('c01-main'), html, 5);                               /* v0.3.15 (R7N F): 変わった行だけ差し替え (スクロール位置そのまま) */
    var root = $('c01-main');
    root.querySelectorAll('[data-port]').forEach(function (el) { el.onclick = function () { pickPort(el.getAttribute('data-port')); render(); }; });
    root.querySelectorAll('[data-filter]').forEach(function (el) { el.onclick = function () { var f = el.getAttribute('data-filter'); S.filter = S.filter === f ? 'all' : f; render(); }; });
    $('show-unarrived').onchange = function () { S.showUnarrived = !S.showUnarrived; render(); };
    root.querySelectorAll('[data-photos]').forEach(function (el) { el.onclick = function (ev) { openPhotos(ev, el.getAttribute('data-photos'), 0); }; });
    root.querySelectorAll('[data-docs]').forEach(function (el) { el.onclick = function (ev) { ev.stopPropagation(); openDocs(el.getAttribute('data-docs')); }; });
    root.querySelectorAll('[data-compass]').forEach(function (el) { el.onclick = function (ev) { ev.stopPropagation(); openCompass(el.getAttribute('data-compass')); }; });
    root.querySelectorAll('[data-remind]').forEach(function (el) { el.onclick = function (ev) { ev.stopPropagation(); openRemind(el.getAttribute('data-remind')); }; });
    root.querySelectorAll('[data-same]').forEach(function (el) {
      el.onclick = function (ev) { ev.stopPropagation(); S.view = 'input'; S.qkind = SAME; S.qiv = null; S.qsel = el.getAttribute('data-same'); render(); };
    });
    root.querySelectorAll('[data-holdiv]').forEach(function (el) {
      el.onclick = function (ev) { ev.stopPropagation(); S.view = 'input'; S.qkind = HOLD; S.qiv = el.getAttribute('data-holdiv'); S.qsel = null; render(); };
    });
    root.querySelectorAll('[data-sel]').forEach(function (el) { el.onclick = function () { S.sel = el.getAttribute('data-sel'); S.editRow = null; S.picks = {}; S.panelInput = ''; render(); }; });
    root.querySelectorAll('[data-okedit]').forEach(function (el) {
      el.onclick = function (ev) {
        ev.stopPropagation();
        var f = findRow(el.getAttribute('data-okedit'));
        if (f) okEditConfirm(f.iv, f.r, el.textContent);
      };
    });
    root.querySelectorAll('[data-slot]').forEach(function (el) { el.onclick = function (ev) { ev.stopPropagation(); openSlot(el.getAttribute('data-slot')); }; });
    renderPanel(b);
    fitTable();
  }
  /* v0.3.2 (R7B): 実況表の箱 = 窓の高さに合わせる (見出し固定 · 箱の下端が窓の外に出ない) */
  function fitTable() {
    var w = $('jikkyou-wrap');
    if (!w) return;
    var lg = w.nextElementSibling;
    var top = w.getBoundingClientRect().top + (window.scrollY || 0);
    var below = (lg ? lg.getBoundingClientRect().height + 12 : 0) + 16;
    w.style.maxHeight = Math.max(240, Math.floor(window.innerHeight - top - below)) + 'px';
  }
  window.addEventListener('resize', function () { if (S.view === 'main') fitTable(); });

  /* ── v0.2.0 Compass入力 DRY 窓 (設計 §6 · 決定 #1~#3 · #91) — 比較表だけ。送信は無効「DRY — 送信しません」 ── */
  var STATE_LABEL = { SAME: '同じ', FILL: '空欄→入力', DIFF: '違う値', KEEP: '値なし（そのまま）', PLAN: '予定値 → 入力（CT が空の枠 · 前の値は記録）', NOINPUT: '入力しない（保留）' };
  var WARN_LABEL = { PACKER_DIFF: '業者が違う', ITEM_DIFF: '品目が違う', OFFICE_DIFF: '営業所が違う', EXISTING_DIFF: 'COMPASS に別の値', CT_DUP: 'CT が別の枠にもある',
    TYPE_42_22: '形態 42GP/22GP — 担当者が判断', NUM_INVALID: '数字にできない — この行は入力しない',
    /* v0.2.1 (D-11 (가) 準備 · C01.COMPASS.follow_same_cond_slot · 既定オフ) */
    SLOT_FOLLOWED: '同じ CT がある同一条件の枠で比較', CT_DUP_OTHER_COND: '同じ CT が条件の違う枠にある', CT_DUP_MULTI: '同じ CT が 2 つ以上の枠にある',
    OTHER_CT_IN_SLOT: '枠に別の CT が入っている' };
  var SKIP_LABEL = { NO_CT_ID: '枠 (ct_id) なし — 入力しない', NOT_FOUND: 'COMPASS の枠が見つからない', NOT_OK: '対象外（自動OK・確認済 以外）', NUM_INVALID: '数字にできない値がある',
    CT_DUP_OTHER_COND: '同じ CT が条件の違う枠にある — 入力しない', CT_DUP_MULTI: '同じ CT が 2 つ以上の枠にある — 入力しない',
    OTHER_CT_IN_SLOT: '枠に別の CT が入っている — 上書きしない' };
  var CF_LABEL = { ct: 'CT', seal: 'シール', n_w: '正味', g_w: '総重量(=正味)', t_w: '風袋', bales: 'ベール', type: '形態' };
  function ivById(ivNo) { return ((S.jik && S.jik.ivs) || []).filter(function (x) { return x.iv_no === ivNo; })[0] || null; }
  function compassInput(iv) {
    var ov = overlay();
    return iv.rows.map(function (r) {
      var x = statusOf(r, iv, ov);
      var v = function (f) { return x.human[f] ? x.human[f].value : r[f]; };
      return { container_id: r.container_id, ct: v('ct'), seal: v('seal'), n_w: v('n_w'), t_w: v('t_w'), bales: v('bales'), status: x.st,
        packer: r.packer, plant: r.plant, item: r.item, ct_id: r.slot_guid || null };
    });
  }
  function closeModal() { var m = $('c01-modal'); if (m) { m.hidden = true; m.innerHTML = ''; } S.modal = null; }
  function showModal(html, cls) {
    var m = $('c01-modal');
    m.innerHTML = '<div class="c01-mbg" id="m-bg"></div><div class="c01-modal' + (cls ? ' ' + cls : '') + '" role="dialog" aria-modal="true">' + html + '</div>';
    m.hidden = false;
    $('m-bg').onclick = closeModal;
    m.querySelectorAll('[data-close]').forEach(function (el) { el.onclick = closeModal; });
  }
  /* ── v0.3.19 (R7T 決定 #190): Compass入力 = 実際に入力 (ログインした人の権限 · 試験運用中)。
     graph モード + C01.SEND.compass + C01.COMPASS.dvUrl の時だけ COMPASS (Dataverse) を職員トークンで GET → 比較表 → チェックした行だけ
     If-Match PATCH → もう一度 GET で確認 (js/compass.js Writer) → _actions に compass_done (前の値 · 後の値 · 誰 · いつ)。
     「元に戻す」 = その IV の最後の入力を 前の値 に戻す (今の値 = その時入れた値 の項目だけ · 他の人が変えた項目は戻さない)。
     警告のある行は最初チェックなし。失敗 (412 他の人が先に変更 · エラー · 読み直しが違う) は その行だけ赤 · 他の行は続ける。作業日は入れない。 ── */
  function compassLiveOn() {
    var C = C01.COMPASS || {};
    return graphMode() && !!(C01.SEND && C01.SEND.compass) && !!C.dvUrl && !!(window.LEENAI && LEENAI.auth && LEENAI.auth.token);
  }
  function dvFetch(url, opt) {
    return LEENAI.auth.token('dataverse').then(function (tok) {
      if (!tok) throw new Error('COMPASS のトークンがありません (再ログインしてください)');
      var o = Object.assign({ cache: 'no-store' }, opt || {});
      o.headers = Object.assign({ 'OData-MaxVersion': '4.0', 'OData-Version': '4.0' }, (opt && opt.headers) || {}, { Authorization: 'Bearer ' + tok });
      return fetch(url, o);
    });
  }
  function dvBase() { return String((C01.COMPASS || {}).dvUrl || '').replace(/\/$/, ''); }
  function compassLive(iv) {
    var sel = 'crcf9_container_informationid,' + C01.compass.FIELDS.map(function (f) { return f[1]; }).join(',');
    var url = dvBase() + '/api/data/v9.2/crcf9_container_informations?$select=' + sel + '&$filter=' + encodeURIComponent('_crcf9_booking_id_value eq ' + iv.booking_guid);
    return dvFetch(url, { method: 'GET', headers: { Accept: 'application/json' } }).then(function (r) {
      if (!r.ok) throw new Error('COMPASS を読めません (' + r.status + ')');
      return r.json();
    }).then(function (j) {
      var sl = {};
      (iv.slots || []).forEach(function (s) { if (s.slot_guid) sl[s.slot_guid] = s; });
      var cells = {};
      (j.value || []).forEach(function (r) {
        var s = sl[r.crcf9_container_informationid] || {};
        r._packer = s.packer || null; r._item = s.item || null; r._plant = s.plant || null;
        cells[r.crcf9_container_informationid] = r;
      });
      var dups = {};
      Object.keys(cells).forEach(function (g) {
        dups[g] = Object.keys(cells).filter(function (h) { return h !== g; }).map(function (h) { return C01.compass.normText(cells[h].crcf9_container_no); }).filter(Boolean);
      });
      return { cells: cells, dups: dups, live: true };
    });
  }
  function compassWriter() {
    return new C01.compass.Writer({ baseUrl: dvBase(), enabled: true, fetchFn: function (url, opt) { return dvFetch(url, opt); } });
  }
  /* その IV の Compass入力 記録 (エンジン反映済 + 自分の画面の未反映) — 新しい順 */
  function compassRecords(iv) {
    var xs = (iv.compass_input || []).map(function (x) { return { action_id: x.action_id, by: x.by, at: x.at, value: x.value || {} }; });
    (S.mine || []).forEach(function (m) {
      var a = m.action;
      if (a.action === 'compass_done' && a.iv === iv.iv_no && !xs.some(function (x) { return x.action_id === a.action_id; })) xs.push({ action_id: a.action_id, by: a.by, at: a.at, value: a.value || {} });
    });
    return xs.sort(function (a, b) { return String(b.at).localeCompare(String(a.at)); });
  }
  function compassIsDone(iv) {
    var last = compassRecords(iv)[0];
    return !!last && !last.value.undo_of;
  }
  function openCompass(ivNo) {
    var iv = ivById(ivNo);
    if (!iv) return;
    S.modal = { kind: 'compass', iv: ivNo };
    var live = compassLiveOn();
    var getSnap = live ? compassLive(iv).catch(function (e) { return { error: e.message }; })
      : S.src.getJson('compass_now/' + ivNo + '.json').then(function (snap) { return snap; }).catch(function () { return null; });
    getSnap.then(function (snap) {
      if (!S.modal || S.modal.iv !== ivNo) return;
      var html = '<div class="c01-mh"><b>Compass入力' + (live ? '' : ' — 比較表') + '</b><span class="mono">' + esc(ivNo) + '</span><span class="t2">BKG ' + esc(iv.bkg_no || '') + ' · CY ' + esc(md(iv.cy_cut)) + '</span>' +
        (live ? ((C01.COMPASS || {}).trial ? '<span class="c01-trial" data-trial>試験運用中</span>' : '')
          : '<span class="c01-trial" data-trial>試験表示（並行期間中は送信・入力しません）</span>') +
        '<span class="c01-flex"></span><button class="c01-btn-ghost2" data-close>閉じる</button></div>';
      if (!snap || snap.error) {
        html += '<div class="c01-mb"><p class="c01-err">' + (snap && snap.error ? esc(snap.error) : 'COMPASS の今の値がありません（ローカルプレビュー: compass_now/' + esc(ivNo) + '.json なし）') + '</p></div>';
        showModal(html);
        return;
      }
      var res = C01.compass.compareIv(ivNo, compassInput(iv), snap.cells || {}, snap.dups || {}, C01.COMPASS || null);
      S.modal.res = res; S.modal.live = live; S.modal.cells = snap.cells || {};
      S.modal.pick = {};
      res.rows.forEach(function (r) { if (!r.skip && Object.keys(r.patch).length) S.modal.pick[r.ct_id] = r.warnings.length === 0; });
      html += '<div class="c01-mb"><div class="c01-csum">' +
        '<span class="c01-cst SAME">同じ ' + res.count.cells.SAME + '</span><span class="c01-cst FILL">空欄→入力 ' + res.count.cells.FILL + '</span>' +
        (res.count.cells.PLAN !== undefined ? '<span class="c01-cst PLAN">予定値→入力 ' + res.count.cells.PLAN + '</span>' : '') +
        '<span class="c01-cst DIFF">違う値 ' + res.count.cells.DIFF + '</span><span class="c01-cst KEEP">値なし ' + res.count.cells.KEEP + '</span>' +
        (res.count.cells.NOINPUT !== undefined ? '<span class="c01-cst NOINPUT">形態は入力しない</span>' : '') +
        '<span class="t2">PATCH 対象 ' + res.count.patch_rows + '行 · 作業日は入れません</span></div>' +
        (res.all_ok ? '' : '<p class="c01-warnline" id="cmp-reason">' + esc(res.button.reason || '') + (live ? ' — 自動OK・確認済 の行だけ入力できます' : ' — 比較表だけ表示します') + '</p>') +
        '<table class="c01-ctable" id="compass-table"><thead><tr>' + (live ? '<th title="入力する行"><label class="c01-call" title="警告のない行を全て選ぶ（警告のある行は 1 行ずつ確認して選ぶ）"><input type="checkbox" id="compass-all"> 全て選択</label></th>' : '') + '<th>CT</th>' +
        C01.compass.FIELDS.map(function (f) { return '<th>' + CF_LABEL[f[0]] + '</th>'; }).join('') + '<th>警告・理由</th></tr></thead><tbody>';
      res.rows.forEach(function (r) {
        var can = !r.skip && Object.keys(r.patch).length > 0;
        html += '<tr data-crow="' + esc(r.container_id || '') + '"' + (r.ct_id ? ' data-ctid="' + esc(r.ct_id) + '"' : '') + '>' +
          (live ? '<td class="c01-cpick">' + (can ? '<input type="checkbox" data-cpick="' + esc(r.ct_id) + '"' + (S.modal.pick[r.ct_id] ? ' checked' : '') + ' title="' + (r.warnings.length ? '警告あり — 確認して入れる時だけチェック' : 'この行を入力') + '">' : '') + '</td>' : '') +
          '<td class="mono">' + esc(r.ct || '—') + '</td>';
        if (r.skip) {
          html += '<td colspan="' + C01.compass.FIELDS.length + '" class="c01-skip">' + esc(SKIP_LABEL[r.skip] || r.skip) + '</td>';
        } else {
          r.cells.forEach(function (c) {
            html += '<td class="c01-cell ' + c.state + (c.in_patch ? ' in' : '') + '" title="' + esc(STATE_LABEL[c.state]) + '" data-state="' + c.state + '">' +
              (c.state === 'NOINPUT' ? '<div class="now">' + esc(c.now == null ? '（空）' : c.now) + '</div><div class="t2">入力しない</div>' :
              '<div class="now">' + (c.state === 'PLAN' ? '<span class="t2">予定 </span>' : '') + esc(c.now == null ? '（空）' : c.now) + '</div>' + (c.state === 'SAME' || c.state === 'KEEP' ? '' : '<div class="put">→ ' + esc(c.put == null ? '' : c.put) + '</div>')) + '</td>';
          });
        }
        html += '<td>' + r.warnings.map(function (w) { return '<span class="c01-wchip" data-warn="' + w + '">' + esc(WARN_LABEL[w] || w) + '</span>'; }).join('') +
          '<span class="c01-cres" data-cres="' + esc(r.ct_id || '') + '"></span></td></tr>';
      });
      html += '</tbody></table><details class="c01-patch"><summary>PATCH 本文' + (live ? '' : '（送りません）') + '</summary><pre id="compass-patch">' +
        esc(JSON.stringify(res.patches, null, 1)) + '</pre></details>';
      var recs = live ? compassRecords(iv) : [];
      var last = recs[0];
      if (recs.length) {
        html += '<div class="c01-chist" id="compass-hist"><b>入力の記録</b>' + recs.slice(0, 5).map(function (x) {
          return '<div>' + esc(String(x.at || '').slice(5, 16).replace('T', ' ')) + ' · ' + esc(staffName(x.by)) + ' · ' + (x.value.undo_of ? '元に戻した ' : '入力 ') +
            ((x.value.cells || []).length) + '行' + (x.value.failed && x.value.failed.length ? ' · 失敗 ' + x.value.failed.length + '行' : '') + '</div>';
        }).join('') + '</div>';
      }
      html += '</div><div class="c01-mf">';
      if (live) {
        html += '<span class="t2">チェックした行を COMPASS に入力（If-Match → もう一度読んで確認 → 記録）· 入力する人 = ' + esc((S.me && S.me.name) || '') + '</span><span class="c01-flex"></span>' +
          (last && !last.value.undo_of && (last.value.cells || []).length ? '<button id="compass-undo" class="c01-btn-ghost2" title="この IV の最後の入力を 前の値 に戻します">元に戻す</button>' : '') +
          '<button id="compass-send" class="c01-btn-pri">Compass に入力 (<span id="compass-n">0</span>行)</button>';
      } else {
        html += '<span class="t2">If-Match (etag) 付きで入力 → もう一度読んで確認 → compass_done を記録（R7 以降・職員ログイン）</span><span class="c01-flex"></span>' +
          '<button id="compass-send" class="c01-btn-pri" disabled aria-disabled="true" title="R6 はローカル DRY">DRY — 送信しません</button>';
      }
      html += '</div>';
      showModal(html, 'c01-compass');
      if (!live) return;
      var upd = function () {
        var n = Object.keys(S.modal.pick).filter(function (k) { return S.modal.pick[k]; }).length;
        $('compass-n').textContent = n;
        var b = $('compass-send'); b.disabled = n === 0 || !!S.modal.busy; b.setAttribute('aria-disabled', b.disabled ? 'true' : 'false');
      };
      document.querySelectorAll('[data-cpick]').forEach(function (el) {
        el.onchange = function () { S.modal.pick[el.getAttribute('data-cpick')] = el.checked; upd(); };
      });
      /* v0.3.24 (R7X Part D-3): 全て選択 = 警告のない行だけ (CT が別の枠にもある · COMPASS に別の値 (予定値でない) 等の行は外す — 1 行ずつ確認) */
      var noWarn = {};
      res.rows.forEach(function (r) { if (!r.skip && Object.keys(r.patch).length && !r.warnings.length) noWarn[r.ct_id] = 1; });
      if ($('compass-all')) $('compass-all').onchange = function () {
        var on = $('compass-all').checked;
        document.querySelectorAll('[data-cpick]').forEach(function (el) {
          var id = el.getAttribute('data-cpick');
          if (noWarn[id]) { el.checked = on; S.modal.pick[id] = on; }
        });
        upd();
      };
      $('compass-send').onclick = function () { compassSend(ivNo); };
      if ($('compass-undo')) $('compass-undo').onclick = function () { compassUndo(ivNo, last); };
      upd();
    });
  }
  function cres(ctId, text, cls) {
    var el = document.querySelector('[data-cres="' + (window.CSS && CSS.escape ? CSS.escape(ctId) : ctId) + '"]');
    if (el) { el.textContent = text; el.className = 'c01-cres ' + (cls || ''); }
  }
  var CRES_LABEL = { OK: '入力済 ✓', PRECONDITION_FAILED: '他の人が先に変更 — 入力していません', REREAD_DIFF: '読み直した値が違う — 確認してください', ERROR: 'エラー — 入力できませんでした' };
  function compassSend(ivNo) {
    var m = S.modal;
    if (!m || m.kind !== 'compass' || !m.live || m.busy) return;
    var pick = m.res.patches.filter(function (p) { return m.pick[p.ct_id]; });
    if (!pick.length) return;
    if (!window.confirm('COMPASS に ' + pick.length + ' 行を入力します（' + ((S.me && S.me.name) || '') + '）。よろしいですか？')) return;
    m.busy = true;
    $('compass-send').disabled = true;
    var w = compassWriter(), results = [], chain = Promise.resolve();
    pick.forEach(function (p) {
      chain = chain.then(function () {
        cres(p.ct_id, '入力中…', '');
        return w.apply(p).catch(function (e) { return { result: 'ERROR', ct_id: p.ct_id, error: e.message }; }).then(function (r) {
          results.push(r);
          cres(p.ct_id, (CRES_LABEL[r.result] || r.result) + (r.error ? ' (' + r.error + ')' : ''), r.result === 'OK' ? 'ok' : 'ng');
        });
      });
    });
    chain.then(function () {
      var ok = results.filter(function (r) { return r.result === 'OK'; });
      var bad = results.filter(function (r) { return r.result !== 'OK'; }).map(function (r) { return { ct_id: r.ct_id, result: r.result, error: r.error || null }; });
      if (!ok.length && !bad.length) return;
      var a = C01.compass.compassDoneAction(actionId(), ivNo, S.me.email, jstNow(), ok.map(function (r) { return r.cell; }));
      a.value.failed = bad;
      a.value.trial = !!(C01.COMPASS || {}).trial;
      return (ok.length ? writeAction(a) : Promise.resolve()).then(function () {
        m.busy = false;
        toast('COMPASS 入力: 成功 ' + ok.length + '行' + (bad.length ? ' · 失敗 ' + bad.length + '行（赤の行）' : ''), bad.length ? 'warn' : 'success');
        if (!bad.length) { closeModal(); render(); }
      });
    }).catch(function (e) { m.busy = false; toast('COMPASS 入力: ' + e.message, 'error'); });
  }
  function compassUndo(ivNo, last) {
    var m = S.modal;
    if (!m || m.busy || !last) return;
    var cells = last.value.cells || [];
    if (!window.confirm('この IV の最後の入力 (' + cells.length + '行 · ' + staffName(last.by) + ') を 前の値 に戻します。よろしいですか？')) return;
    m.busy = true;
    var w = compassWriter(), done = [], bad = [], chain = Promise.resolve();
    var names = {};
    C01.compass.FIELDS.forEach(function (f) { names[f[1]] = f[0]; });
    cells.forEach(function (c) {
      chain = chain.then(function () {
        return w.getCell(c.ct_id).then(function (now) {
          if (!now) { bad.push({ ct_id: c.ct_id, result: 'ERROR', error: 'GET 失敗' }); return; }
          var body = {};
          Object.keys(c.after || {}).forEach(function (dv) {
            var f = names[dv];
            if (C01.compass.nowValue(f, now[dv]) === C01.compass.nowValue(f, c.after[dv])) body[dv] = c.before ? c.before[dv] : null;   /* 今 = 入れた値 の項目だけ戻す */
          });
          if (!Object.keys(body).length) { bad.push({ ct_id: c.ct_id, result: 'CHANGED', error: '他の値に変わっています — 戻しません' }); return; }
          return w.apply({ ct_id: c.ct_id, if_match: now['@odata.etag'] || null, body: body }).then(function (r) {
            if (r.result === 'OK') done.push(r.cell); else bad.push({ ct_id: c.ct_id, result: r.result, error: r.error || null });
          });
        }).catch(function (e) { bad.push({ ct_id: c.ct_id, result: 'ERROR', error: e.message }); });
      });
    });
    chain.then(function () {
      var a = C01.compass.compassDoneAction(actionId(), ivNo, S.me.email, jstNow(), done);
      a.value.undo_of = last.action_id;
      a.value.failed = bad;
      return (done.length ? writeAction(a) : Promise.resolve()).then(function () {   /* 戻せた行が 0 = 記録しない (エンジン schema: cells 1 行以上) */
        m.busy = false;
        toast('元に戻しました: ' + done.length + '行' + (bad.length ? ' · 戻せなかった ' + bad.length + '行' : ''), bad.length ? 'warn' : 'success');
        closeModal(); render();
      });
    }).catch(function (e) { m.busy = false; toast('元に戻す: ' + e.message, 'error'); });
  }
  /* ── v0.2.0 催促 プレビュー窓 (設計 §7 · 決定 #97) — 下書きだけ。送信は無効「下書きのみ」 ── */
  /* ── #109 行の情報表示 · スロット変更 (全職員 · 入れ替え確認 · _actions に 誰・いつ・前→後 · 元に戻す) ── */
  var INFO_TEXT = { CT_CHECKDIGIT_OVERRIDE: 'チェックディジット不一致を確認して保存（確認済 · 自動OK にしない）',
    AI_GROUP_DIFF: 'AI 区分が異なる — 写真はフォルダ · ファイル名 · 業者ルールでまとめました（AI の写真の区分とは違います · 情報だけ）' };
  function canSlotChange() {
    var R = C01.RULES || {};
    if (R.slotChange === 'all') return true;
    return !!(S.me && (R.adminUsers || []).indexOf(S.me.email) >= 0);
  }
  function slotOf(iv, r, ov) { var a = ov.bySlot[iv.iv_no + '|' + r.ct]; return a ? a.value.slot_guid : (r.slot_guid || null); }
  function slotLabel(iv, guid) {
    var ss = iv.slots || [];
    for (var i = 0; i < ss.length; i++) {
      if (ss[i].slot_guid === guid) return '枠' + (i + 1) + ' · ' + [ss[i].packer, ss[i].plant, ss[i].item, ss[i].type].filter(Boolean).join(' ');
    }
    return guid ? '（一覧にない枠）' : '（枠なし）';
  }
  function slotInfo(iv, r, ov) {
    var a = ov.bySlot[iv.iv_no + '|' + r.ct];
    if (a) return { action_id: a.action_id, by: a.by, at: a.at, before: a.value.slot_before || null, after: a.value.slot_guid, swap_ct: a.value.swap_ct || null };
    return r.slot_change || null;
  }
  function staffName(email) { var s = staffList().filter(function (x) { return x.email === email; })[0]; return s ? (s.name || s.code) : (email || ''); }
  function slotInfoText(iv, si) {
    return 'スロット変更 · ' + staffName(si.by) + ' · ' + String(si.at || '').slice(0, 16).replace('T', ' ') + ' · ' + slotLabel(iv, si.before) + ' → ' + slotLabel(iv, si.after) +
      (si.swap_ct ? ' · 入れ替え ' + si.swap_ct : '');
  }
  function c2(v, t) { return '<td class="c-wrap"><span class="c01-clamp" title="' + esc(t !== undefined ? t : (v || '')) + '">' + esc(v || '') + '</span></td>'; }
  function c1(v, cls, t) { return '<td class="c-cut' + (cls ? ' ' + cls : '') + '" title="' + esc(t !== undefined ? t : (v || '')) + '">' + esc(v || '') + '</td>'; }
  /* v0.3.7 (R7D Part U-1): 行の 品目 · 条件 · 圧縮業者 · Plant — IV の候補枠を「・」で全部つなげない。
     枠に割り当て済み = その枠 (slot_guid) の値 1 つ · 未割り当て = コンテナの値 → 候補枠の値が 1 種類ならそれ → それ以外「—」(マウスで候補一覧) */
  function slotOfRow(iv, r) {
    var ss = (iv && iv.slots) || [], g = r && r.slot_guid;
    if (!g) return null;
    for (var i = 0; i < ss.length; i++) if (ss[i].slot_guid === g) return ss[i];
    return null;
  }
  function rowVal(iv, r, key) {
    var s = slotOfRow(iv, r);
    var own = r ? r[key] : null;
    if (key === 'packer' && own) return { v: own, t: own };              /* 圧縮業者 = エンジンのコンテナ値が先 (rowKey と同じ) */
    /* v0.3.24 (R7X Part C · 형님 16:5x): 枠が決まった行 = その枠の値だけ (枠に無ければ 行の値 · どちらも無ければ空欄) — IV の他の枠の値で埋めない */
    if (s) { var sv = s[key] || own || ''; return { v: sv, t: sv }; }
    if (own) return { v: own, t: own };
    var u = [];
    ((iv && iv.slots) || []).forEach(function (x) { if (x[key] && u.indexOf(x[key]) < 0) u.push(x[key]); });
    if (u.length) return { v: '—', t: '枠が未定 · 候補: ' + u.join(' / ') };   /* 候補が 1 つでも埋めない (枠が決まってから) */
    var f = (iv && iv[key]) || '';
    return f ? { v: '—', t: '枠が未定 · 候補: ' + String(f).split('・').join(' / ') } : { v: '', t: '' };
  }
  var ACT_MARK = '<!--c01-acts-->';
  function qAiDiff(q, iv) {
    var row = iv && q.container_id ? (iv.rows || []).filter(function (r) { return r.container_id === q.container_id; })[0] : null;
    return !!(row && (row.info || []).indexOf('AI_GROUP_DIFF') >= 0);
  }
  function qPackerPlant(q, iv) {
    var row = q.container_id ? (iv.rows || []).filter(function (r) { return r.container_id === q.container_id; })[0] : null;
    return rowVal(iv, row, 'packer').v + ' ' + rowVal(iv, row, 'plant').v;
  }
  function cv(o, one, cls) { return one ? c1(o.v, cls, o.t) : c2(o.v, o.t); }
  /* ── v0.3.15 (R7N Part G-4): 値の 「修正」 (✎) — 写真だけで決まった値 (写真のみ) も含め すべての値の欄。
     保存 = _actions manual_input (source 手入力) → エンジンが human_value に入れる (決定 #109: 人の値が優先)。
     queue_id = この行 · 項目から作る 16 桁 (queue に無い id → エンジンは IV + CT で行を探す · apply.py container_by)。
     すでに人の値がある欄 = エンジンは先に入った人の値を残す (apply.py: 同じ行 · 項目の human_value が先勝ち) → ここでは押せない (理由を表示) */
  var EDIT_FIELDS = ['ct', 'seal', 'n_w', 't_w', 'bales', 'work_date'];
  /* v0.3.23 (R7W Part A · 形님 15:3x): 自動OK · 確認済 の行も 修正 (警告 1 回 → 修正フォーム) · 人の値があっても新しい値 (mode edit) · 元に戻す */
  function valueEditOn() { return !!(C01.RULES || {}).valueEdit; }
  function okEditConfirm(iv, r, st) {
    var cdone = compassIsDone(iv);
    var html = '<h3>この行は ' + esc(st) + ' です</h3>' +
      '<p>値を変えると <b>確認済（手入力）</b>に変わり、記録されます。修正しますか？</p>' +
      (cdone ? '<p class="c01-warn2">COMPASS には入力済み — 修正後に Compass入力 をもう一度</p>' : '') +
      '<p class="t2 mono">' + esc((r.ct || '（CT 不明）') + ' · ' + iv.iv_no) + '</p>' +
      '<div class="c01-mbtns"><button class="c01-btn-pri" id="okedit-go">修正する</button><button class="c01-btn-ghost2" data-close>やめる</button></div>';
    showModal(html, 'c01-modal-okedit');
    $('okedit-go').onclick = function () { closeModal(); S.sel = rowKey(iv, r); S.editRow = rowKey(iv, r); S.picks = {}; S.panelInput = ''; render(); };
  }
  /* v0.3.24 (R7X Part A · 형님 17:1x): 再確認 の行 = 「このまま確認（OK）」 — 値は変えずに 確認済 (今の値で confirm_value · queue_id = その項目 ·
     元に戻す = 各項目の 「元に戻す」)。空欄 · CT 不明 · 他の種類の項目が残っている時は できない理由を出す */
  var KEEP_SRC = { '搬入票': 1, '写真': 1, 'Excel': 1 };
  function keepSrc(q, fd, val) {
    var s0 = null;
    Object.keys((q && q.values) || {}).forEach(function (k) { if (!s0 && (q.values[k] || []).some(function (v) { return String(v) === String(val); })) s0 = k; });
    if (!s0) (((q && q.field_sources) || {})[fd] || []).forEach(function (x) { if (!s0 && x.agree) s0 = x.src; });
    return KEEP_SRC[s0] ? s0 : '搬入票';
  }
  function keepPlan(iv, r, ov) {
    var x = statusOf(r, iv, ov), acts = [], block = [];
    var cur = function (fd) { return x.human[fd] ? x.human[fd].value : r[fd]; };
    var open = qItems().filter(function (q) { return q.container_id === r.container_id && !queueState(q, ov).done; });
    var ctq = function (q, qid) {
      var v = cur('ct');
      if (!v) { block.push('CT が分かりません — 先に CT を確認してください'); return; }
      acts.push({ iv: iv.iv_no, ct: r.ct, field: 'ct', value: String(v), source: q ? keepSrc(q, 'ct', v) : (r.photos ? '写真' : '搬入票'), queue_id: qid });
    };
    open.forEach(function (q) {
      if (q.kind === '値の違い' && q.field) {
        var v = cur(q.field);
        if (v == null || v === '') { block.push(FIELD_LABEL[q.field] + ' が空欄 — 値を選ぶか入力してください'); return; }
        acts.push({ iv: iv.iv_no, ct: r.ct, field: q.field, value: v, source: keepSrc(q, q.field, v), queue_id: q.queue_id });
      } else if (q.kind === '手入力') block.push(FIELD_LABEL[q.field] + ' が空欄 — 原本を見て入力してください');
      else if (q.kind === '写真のCT') block.push('写真の CT が分かりません — 確認・入力 で選んでください');
      else if (q.kind === PHOTO_SET || q.kind === VCHK) ctq(q, q.queue_id);
      else block.push(kindLabel(q.kind) + ' を先に処理してください');
    });
    if (!open.length) ctq(null, editQid(r, 'ct'));
    return { acts: acts, block: block };
  }
  function keepRow(iv, r, after) {
    if (!S.me) { toast('担当者を選んでください（右上）', 'warn'); return; }
    var pl = keepPlan(iv, r, overlay());
    if (pl.block.length || !pl.acts.length) { toast('このままでは確認できません: ' + (pl.block[0] || '確認する項目がありません'), 'warn'); return; }
    var vals = EDIT_FIELDS.map(function (fd) { var v = statusOf(r, iv, overlay()).human[fd]; v = v ? v.value : r[fd]; return FIELD_SHORT[fd] + ' ' + (v == null || v === '' ? '—' : (typeof v === 'number' ? v.toLocaleString('en-US') : v)); });
    var html = '<h3>このまま確認（OK）</h3><p>値を変えずに <b>確認済</b> にします（記録されます · 各項目の 「元に戻す」 で戻せます）。</p>' +
      '<p class="t2 mono">' + esc((r.ct || '（CT 不明）') + ' · ' + iv.iv_no) + '</p><p class="mono c01-keepvals">' + esc(vals.join(' · ')) + '</p>' +
      (compassIsDone(iv) ? '<p class="c01-warn2">COMPASS には入力済み</p>' : '') +
      '<div class="c01-mbtns"><button class="c01-btn-pri" id="keep-go">確認済にする</button><button class="c01-btn-ghost2" data-close>やめる</button></div>';
    showModal(html, 'c01-modal-keep');
    $('keep-go').onclick = function () {
      closeModal();
      var chain = Promise.resolve();
      pl.acts.forEach(function (f) { chain = chain.then(function () { return writeAction(mkAction('confirm_value', f)); }); });
      chain.then(function () { toast('このまま確認しました（確認済）', 'success'); if (after) after(); else render(); });
    };
  }
  /* 修正した値の 「元に戻す」 (manual_input · confirm_value の undo — エンジンが前の人の値 · エンジンの値に戻す) */
  function undoValue(iv, row, fd, h) {
    if (!S.me) { toast('担当者を選んでください（右上）', 'warn'); return; }
    if (!window.confirm(FIELD_LABEL[fd] + ' の修正（' + String(h.value) + '）を元に戻しますか？')) return;
    var a = mkAction('undo', { iv: iv.iv_no, ct: row.ct || null, field: null, value: { action_id: h.action_id }, source: null, queue_id: null });
    writeAction(a).then(function () { render(); toast(FIELD_LABEL[fd] + ' を元に戻しました', 'success'); });
  }
  function editKey(row, fd) { return row.container_id + '|' + fd; }
  function editQid(row, fd) { var k = 'edit|' + row.container_id + '|' + fd; return hkey(k) + hkey(k + '|2'); }
  function editCell(iv, row, fd, src, ov) {
    var x = statusOf(row, iv, ov);
    var h = x.human[fd];
    var v = h ? h.value : row[fd];
    var ed = S.qedit && S.qedit.key === editKey(row, fd);
    var why = h && !valueEditOn() ? 'すでに人が確認した値です（' + staffName(h.by) + '）— エンジンは先に入った人の値を残すため、ここからは直せません' :
      !row.ct ? 'CT が分からない行は 先に CT を確認・入力してください' : '';
    var lab = '<label><b>' + FIELD_LABEL[fd] + '</b><span class="c01-flex"></span>' +
      (src ? '<span class="c01-src" data-src-field="' + fd + '">' + esc(src) + '</span>' : '') +
      (h ? '<span class="c01-hm2" title="' + esc('人の値 · ' + staffName(h.by) + ' · ' + String(h.at || '').slice(0, 16).replace('T', ' ')) + '">✓ ' + (h.source === '手入力' ? '修正' : '確認') + '</span>' : '') +
      (ed ? '' : '<button class="c01-edit" data-edit="' + esc(editKey(row, fd)) + '"' + (why ? ' disabled title="' + esc(why) + '"' : ' title="この値を修正（人の値が優先 · 決定 #109）"') + '>✎ 修正</button>') +
      (!ed && h && valueEditOn() && h.action_id && !h.pending ? '<button class="c01-undo2" data-vundo="' + esc(fd) + '" title="この人の値を取り消して前の値に戻す（記録が残ります）">元に戻す</button>' : '') + '</label>';
    if (!ed) return '<div class="c01-field ro" data-ef="' + fd + '">' + lab + '<div class="mono rov">' + (v == null || v === '' ? '<span class="t2">—</span>' : num(v)) + '</div></div>';
    return '<div class="c01-field ro editing" data-ef="' + fd + '">' + lab + '<div class="c01-editrow"><input id="edit-in" class="q-in" value="' + esc(S.qedit.value) + '" placeholder="正しい値" aria-label="' + FIELD_LABEL[fd] + ' を修正">' +
      '<button class="c01-btn-pri" id="edit-save">保存</button><button class="c01-btn-ghost2" id="edit-cancel">やめる</button></div>' +
      (S.qedit.err ? '<p class="c01-err" id="edit-err">' + esc(S.qedit.err) + '</p>' : '') + '<span class="hint">' + esc(hintOf(fd)) + ' · 人の値が優先（決定 #109）</span></div>';
  }
  function bindEdits(root, iv, row) {
    root.querySelectorAll('[data-edit]').forEach(function (b) {
      b.onclick = function () {
        var key = b.getAttribute('data-edit'), fd = key.split('|').pop();
        var h = statusOf(row, iv, overlay()).human[fd];
        var v = h ? h.value : row[fd];
        S.qedit = { key: key, value: v == null ? '' : String(v), err: '' };
        render();
        var i = $('edit-in');
        if (i) { i.focus(); i.select(); }
      };
    });
    root.querySelectorAll('[data-vundo]').forEach(function (b) {
      b.onclick = function () { var fd = b.getAttribute('data-vundo'); var h = statusOf(row, iv, overlay()).human[fd]; if (h) undoValue(iv, row, fd, h); };
    });
    var ei = $('edit-in');
    if (ei) {
      ei.oninput = function () { if (S.qedit) S.qedit.value = ei.value; };
      ei.onkeydown = function (e) { if (e.key === 'Enter') saveEdit(iv, row); if (e.key === 'Escape') { S.qedit = null; render(); } };
    }
    if ($('edit-save')) $('edit-save').onclick = function () { saveEdit(iv, row); };
    if ($('edit-cancel')) $('edit-cancel').onclick = function () { S.qedit = null; render(); };
  }
  /* v0.3.20 (R7U Part A-4): 入れる CT が同じ IV の別の行にある → 保存前に 「このCTは n行目にあります」 (止めない · OK で保存) */
  function ctDupWarn(ivNo, ct, selfCid) {
    var k = String(ct || '').replace(/[\s-]/g, '').toUpperCase();
    if (!k) return true;
    var b = buildGroups(), hit = null;
    b.groups.forEach(function (g) {
      if (g.iv.iv_no !== ivNo) return;
      g.rows.forEach(function (x) { if (!hit && x.kind === 'row' && x.r.container_id !== selfCid && String(x.vals.ct || '').toUpperCase() === k) hit = x; });
    });
    if (!hit) {
      var iv = ((S.jik && S.jik.ivs) || []).filter(function (y) { return y.iv_no === ivNo; })[0];
      var r2 = iv && iv.rows.filter(function (y) { return y.container_id !== selfCid && String(y.ct || '').toUpperCase() === k; })[0];
      if (!r2) return true;
      return window.confirm('このCTは同じ IV の別の行にあります（' + (r2.packer || '') + '）。同じコンテナの再送かもしれません。このまま保存しますか？');
    }
    return window.confirm('このCTは' + hit.no + '行目にあります（' + (hit.r.packer || '') + ' · ' + hit.st + '）。同じコンテナの再送かもしれません。このまま保存しますか？');
  }
  function saveEdit(iv, row) {
    if (!S.qedit || S.qedit.key.indexOf(row.container_id + '|') !== 0) return;
    if (!S.me) { S.qedit.err = '担当者を選んでください（右上）'; render(); return; }
    var fd = S.qedit.key.split('|').pop();
    var v = C01.validate.field(fd, S.qedit.value);
    if (!v.ok) { S.qedit.err = FIELD_LABEL[fd] + ': ' + v.error; render(); return; }
    if (v.warn && !window.confirm(v.warn)) { S.qedit.err = v.warn; render(); return; }   /* #109 ③ と同じ確認窓 */
    if (fd === 'ct' && !ctDupWarn(iv.iv_no, v.value, row.container_id)) { S.qedit.err = 'このCTは同じ IV の別の行にあります'; render(); return; }
    var x = statusOf(row, iv, overlay());
    var old = x.human[fd] ? x.human[fd].value : row[fd];
    if (String(old == null ? '' : old) === String(v.value)) {
      S.qedit = null;
      if (x.st === '再確認') { keepRow(iv, row); return; }              /* v0.3.24 (R7X Part A ③): 変更なしで保存 = このまま確認 */
      render(); toast('値は変わっていません', 'info'); return;
    }
    var a = mkAction('manual_input', { iv: iv.iv_no, ct: row.ct, field: fd, value: v.value, source: '手入力', queue_id: editQid(row, fd), override: v.override,
      mode: valueEditOn() ? 'edit' : null });
    S.qedit = null;
    writeAction(a).then(function () { render(); toast(FIELD_LABEL[fd] + ' を修正しました（人の値が優先）', 'success'); });
  }
  var REREAD_TEXT = { '再判読(CT):候補外': 'CT を原本からもう一度読みました — 候補のどれとも違います',
    '再判読(CT):読めず': 'CT を原本からもう一度読みましたが読めませんでした', '再判読(CT):候補重複': 'CT をもう一度読みました — 同じ候補に 2 行が当たるため合わせていません',
    'REREAD_MERGE(写真のみ行)': '搬入票の CT をもう一度読み、写真の行と同じ CT だったので 1 行に合わせました',
    'REREAD_SEAL(搬入票シール→写真シール)': '搬入票のシールをもう一度読むと写真のシールと同じでした（値はそのまま — シールを確認してください）',
    'REREAD_MERGE(CT重複・再送)': '再送の搬入票（同じ CT · シール · 正味）を 1 行に合わせました（値は変わりません）' };
  function rereadText(s) {
    if (REREAD_TEXT[s]) return REREAD_TEXT[s];
    if (/^CT重複候補/.test(s)) return 'CT が同じ行の再送かもしれません — もう一度読んだ ' + (s.indexOf('seal') >= 0 ? 'シール' : '正味重量') + ' が違うため合わせていません';
    if (/^再判読\(写真CT\)/.test(s)) return '写真の CT をもう一度読みました — ' + (s.slice(-1) === '≠' ? '違う番号' : '読めず');
    if (/^再判読\(書類CT\)/.test(s)) return '搬入票の CT をもう一度読みました — ' + (s.slice(-1) === '≠' ? '違う番号' : '読めず');
    return s;
  }
  function rowInfo(iv, r, x, ov) {
    var out = '';
    var diffs = (r.info || []).filter(function (s) { return /^human_vs_engine_diff\(/.test(s); });
    if (diffs.length && (C01.RULES || {}).humanVsEngine === 'keep_info') {
      out += ' <span class="c01-ibadge" data-info="human_vs_engine" title="確認した値を表示しています（エンジンの判定し直しの値と違います: ' +
        esc(diffs.map(function (s) { return FIELD_LABEL[s.slice(22, -1)] || s; }).join('・')) + '）">ⓘ</span>';
    }
    var ovr = (r.info || []).indexOf('CT_CHECKDIGIT_OVERRIDE') >= 0 || Object.keys(x.human || {}).some(function (f) { return (x.human[f].override || []).indexOf('CT_CHECKDIGIT_OVERRIDE') >= 0; });
    if (ovr) out += ' <span class="c01-ibadge" data-info="CT_CHECKDIGIT_OVERRIDE" title="' + esc(INFO_TEXT.CT_CHECKDIGIT_OVERRIDE) + '">CD</span>';
    if ((r.info || []).indexOf('AI_GROUP_DIFF') >= 0)        /* v0.3.8 (R7D Part A · 決定 #139 ①): 構造 (フォルダ · ファイル名 · 業者ルール) でまとめた写真 — AI の写真区分とは違う (情報だけ) */
      out += ' <span class="c01-ibadge" data-info="AI_GROUP_DIFF" title="' + esc(INFO_TEXT.AI_GROUP_DIFF) + '">AI区分</span>';
    /* v0.3.20 (R7U Part A · F-2): エンジンの再判読 (候補から選ぶ) の結果 · 合わせた行 */
    var rr = (r.info || []).filter(function (s) { return /^(再判読|REREAD_MERGE|REREAD_SEAL|CT重複候補)/.test(s); });
    if (rr.length) out += ' <span class="c01-ibadge" data-info="reread" title="' + esc(rr.map(rereadText).join(' / ')) + '">再判読</span>';
    var si = slotInfo(iv, r, ov);
    if (si) out += ' <span class="c01-ibadge" data-info="slot_change" title="' + esc(slotInfoText(iv, si)) + '">⇄ 枠変更</span>';
    return out;
  }
  function openSlot(key) {
    var f = findRow(key);
    if (!f) return;
    var iv = f.iv, r = f.r, ov = overlay();
    var cur = slotOf(iv, r, ov);
    S.modal = { kind: 'slot', key: key, pick: null };
    var si = slotInfo(iv, r, ov);
    var html = '<div class="c01-mh"><b>スロット変更</b><span class="mono">' + esc(r.ct) + '</span><span class="t2">' + esc(iv.iv_no) + '</span>' +
      '<span class="c01-flex"></span><button class="c01-btn-ghost2" data-close>閉じる</button></div><div class="c01-mb">' +
      '<p class="t2">いまの枠: <b id="slot-cur">' + esc(slotLabel(iv, cur)) + '</b></p><div class="c01-slotlist">' +
      (iv.slots || []).map(function (s, i) {
        var occ = iv.rows.filter(function (y) { return y.container_id !== r.container_id && y.ct && slotOf(iv, y, ov) === s.slot_guid; }).map(function (y) { return y.ct; });
        return '<button class="c01-choice' + (s.slot_guid === cur ? ' on' : '') + '" data-slotpick="' + esc(s.slot_guid) + '"' + (s.slot_guid === cur ? ' disabled' : '') + '>' +
          '<span>' + esc(slotLabel(iv, s.slot_guid)) + '</span><span class="s mono">' + esc(s.slot_guid === cur ? 'いまの枠' : occ.length ? occ.join(', ') : '空き') + '</span></button>';
      }).join('') + '</div>' +
      (si ? '<div class="c01-rpast" id="slot-hist"><b>変更の記録</b><p>' + esc(slotInfoText(iv, si)) + '</p>' +
        (si.before ? '<button class="c01-btn-ghost2" id="slot-undo">元に戻す</button>' : '') + '</div>' : '') +
      '</div><div class="c01-mf"><span class="t2">記録: ' + esc(S.me ? S.me.name : '（担当者を選んでください）') + ' · 誰・いつ・前→後 を _actions に記録</span><span class="c01-flex"></span>' +
      '<button id="slot-apply" class="c01-btn-pri" disabled>この枠に変更</button></div>';
    showModal(html);
    var m = $('c01-modal');
    m.querySelectorAll('[data-slotpick]').forEach(function (el) {
      el.onclick = function () {
        S.modal.pick = el.getAttribute('data-slotpick');
        m.querySelectorAll('[data-slotpick]').forEach(function (e2) { e2.classList.toggle('on', e2 === el); });
        $('slot-apply').disabled = false;
      };
    });
    $('slot-apply').onclick = function () { if (S.modal && S.modal.pick) changeSlot(iv, r, S.modal.pick); };
    var u = $('slot-undo');
    if (u) u.onclick = function () { changeSlot(iv, r, si.before, true); };
  }
  function changeSlot(iv, r, target, undo) {
    if (!S.me) { toast('担当者を選んでください', 'warn'); return; }
    var ov = overlay();
    var cur = slotOf(iv, r, ov);
    if (!target || target === cur) return;
    var occ = iv.rows.filter(function (y) { return y.container_id !== r.container_id && y.ct && slotOf(iv, y, ov) === target; })[0] || null;
    if (occ) {
      if (!cur) { toast('入れ替え先の枠がありません（いまの枠なし）', 'error'); return; }
      if (!window.confirm(occ.ct + ' が入っています。入れ替えますか')) return;
    }
    /* 入れ替えは 1 件 (swap_ct) — エンジンが 2 台を一度に反映 (片方だけ反映されることはない) */
    var act = mkAction('slot_change', { iv: iv.iv_no, ct: r.ct, field: null, value: { slot_guid: target, slot_before: cur, swap_ct: occ ? occ.ct : null }, source: null, queue_id: null });
    writeAction(act).then(function () { closeModal(); render(); toast(undo ? '元に戻しました' : (occ ? '入れ替えました' : 'スロットを変更しました'), 'success'); });
  }

  var SIGN_PLACEHOLDER = '(送信者のメールアドレス)';   /* エンジン engine/notify/remind.py SIGN_PLACEHOLDER と同じ (#112) */
  function signed(t) { return S.me && S.me.email ? String(t).split(SIGN_PLACEHOLDER).join(S.me.email) : t; }
  function remindsOf(ivNo) { return ((S.remind && S.remind.ivs) || {})[ivNo] || []; }
  function openRemind(ivNo) {
    var iv = ivById(ivNo);
    var ds = remindsOf(ivNo);
    S.modal = { kind: 'remind', iv: ivNo };
    var STAGE = { d2: 'CY カット 2 営業日前', d1: 'CY カット 前営業日', workdate_passed: '作業日を過ぎて未着', overdue: '期限超過' };
    var html = '<div class="c01-mh"><b>催促メール — プレビュー</b><span class="mono">' + esc(ivNo) + '</span><span class="t2">BKG ' + esc(iv ? iv.bkg_no : '') + '</span>' +
      (remindTest() ? '<span class="c01-trial" data-trial>試験送信（[test] · 試験用アドレスだけ · 業者には送りません）</span>' :
        '<span class="c01-trial" data-trial>試験表示（並行期間中は送信・入力しません）</span>') +
      '<span class="c01-flex"></span><button class="c01-btn-ghost2" data-close>閉じる</button></div><div class="c01-mb">';
    var cand = ((S.remind && S.remind.cand) || {})[ivNo] || {};
    Object.keys(cand).forEach(function (pk) {
      var m = cand[pk];
      html += '<p class="c01-note2 c01-rcand">候補書類あり — 催促前に確認（' + esc(pk) + ' · ' + ((m.ct || 0) + (m.bkg || 0)) + '台' +
        (m.bkg ? ' · うち BKG だけ一致 ' + m.bkg + '台' : '') + '）— 受信済みのメールに書類・写真らしいファイルがあるため この行は催促の対象外</p>';
    });
    if (!ds.length) html += '<p class="c01-note2">催促の対象はありません</p>';
    ds.forEach(function (d, i) {
      html += '<section class="c01-rmd" data-rmd="' + i + '"><div class="c01-rmeta">' +
        '<div><span class="k">宛先</span><span class="mono">' + esc((d.to || []).join(', ') || '（送信先未登録）') + '</span></div>' +
        '<div><span class="k">CC</span><span class="mono">' + esc((d.cc || []).join(', ')) + '</span></div>' +
        '<div><span class="k">差出人</span><span>' + esc(S.me ? S.me.email || S.me.name : '（ログイン者）') + '</span></div>' +
        '<div><span class="k">件名</span><span class="rsub">' + esc(d.subject) + '</span></div>' +
        '<div><span class="k">回数</span><span>' + esc(d.round) + ' 回目 · ' + esc(STAGE[d.stage] || d.stage) + ' · ' + esc(d.packer) + '</span></div></div>' +
        /* v0.3.12 (R7K Part D ② · D-55 (나)): BKG だけ合う候補がある行も催促の対象 — 送る前に確認 */
        (d.cand_note ? '<p class="c01-note2 c01-rcand c01-rcand-bkg">' + esc(d.cand_note) + '（BKG ' + (+d.cand_bkg || 0) + '台）</p>' : '') +
        '<pre class="c01-rbody">' + esc(signed(d.body_text || '')) + '</pre>' + remindSendRow(iv, d, i) + '</section>';
    });
    var past = (iv && iv.reminders) || [];
    html += '<div class="c01-rpast"><b>これまでの催促</b>' + (past.length ? '<ul>' + past.map(function (p) {
      return '<li>' + esc(String(p.at || '').slice(0, 16).replace('T', ' ')) + ' · ' + esc(p.by || '') + (p.value && p.value.round ? ' · ' + esc(p.value.round) + '回目' : '') + '</li>';
    }).join('') + '</ul>' : '<span class="t2"> なし</span>') + '</div></div>' +
      '<div class="c01-mf"><span class="t2">送信は押した職員本人のメールから（決定 #97）· 回数・送信者を記録</span><span class="c01-flex"></span>' +
      (remindTest() ? '<span class="c01-trial" id="remind-testmode">試験モード: 件名に [test] · 宛先は試験用アドレスだけ（業者 · CC には送りません）</span>' :
        '<button id="remind-send" class="c01-btn-pri" disabled aria-disabled="true" title="試験モードではありません — 送信できません">送信できません</button>') + '</div>';
    showModal(html);
    $('c01-modal').querySelectorAll('[data-rsend]').forEach(function (b) {
      b.onclick = function () { sendRemindTest(ivNo, ds[+b.getAttribute('data-rsend')], b); };
    });
    $('c01-modal').querySelectorAll('[data-rskip]').forEach(function (c) {
      c.onchange = function () { var b = $('c01-modal').querySelector('[data-rsend="' + c.getAttribute('data-rskip') + '"]'); if (b && !b.hasAttribute('data-done')) b.disabled = c.checked || !remindCanSend(); };
    });
  }
  /* ── v0.3.22 (R7V Part B · 決定 #191 · #135): 催促 = エンジンの下書き → 担当者が「送信」。
     試験モード (11/16〜22 · 2 重の鍵): ① C01.SEND.remindTest (この画面のコード) ② エンジン remind.json send_mode.test。
     どちらかが試験でなければ 送信ボタンは出さない (実際の宛先へ送るコードはこの版に無い)。試験の宛先 = send_mode.to 1 件だけ · 件名の前に [test] · CC 0。
     送ったら _actions reminder_sent (誰 · いつ · 業者 · 回数 · 試験) · 同じ IV · 業者 · 回数 はもう送れない */
  function remindMode() { return (S.remind && S.remind.send_mode) || null; }
  function remindTest() {
    var m = remindMode();
    return !!(C01.SEND && C01.SEND.remind && C01.SEND.remindTest !== false && m && m.test === true && typeof m.to === 'string' && /^[^@\s]+@[^@\s]+$/.test(m.to));
  }
  function remindCanSend() { return remindTest() && graphMode() && !!(S.me && S.me.email); }
  function remindSent(iv, d) {
    var xs = ((iv && iv.reminders) || []).map(function (x) { return x.value || {}; });
    (S.actions || []).concat(S.mine || []).forEach(function (x) { var a = x.action || x; if (a.action === 'reminder_sent' && a.iv === d.iv_no) xs.push(a.value || {}); });
    return xs.filter(function (v) { return v.packer === d.packer && +v.round === +d.round; })[0] || null;
  }
  function remindSendRow(iv, d, i) {
    if (!remindTest()) return '';
    var sent = remindSent(iv, d);
    var ready = !d.ready_at || jstNow() >= d.ready_at;
    var why = sent ? '送信済（' + (sent.test ? '試験 · ' : '') + d.round + '回目）' : !ready ? String(d.ready_at).slice(11, 16) + ' から送信できます' :
      !remindCanSend() ? 'ログインした職員だけ送信できます' : '';
    return '<div class="c01-rsendrow"><label class="t2"><input type="checkbox" data-rskip="' + i + '"' + (sent ? ' disabled' : '') + '> この業者には送らない</label>' +
      '<span class="c01-flex"></span><span class="t2">' + esc(why) + '</span>' +
      '<button class="c01-btn-pri" data-rsend="' + i + '"' + (sent ? ' data-done disabled' : (!ready || !remindCanSend() ? ' disabled' : '')) + '>送信（試験）</button></div>';
  }
  function sendRemindTest(ivNo, d, btn) {
    var m = remindMode();
    var iv = ivById(ivNo);
    if (!remindCanSend() || !d || remindSent(iv, d)) return;
    var subj = '[test] ' + d.subject;
    var orig = '[test] 実際の宛先 To ' + (d.to || []).length + '件 · CC ' + (d.cc || []).length + '件（試験送信 · 業者には送っていません）';
    var html = '<p style="color:#888">' + esc(orig) + '</p>' + signed(d.body_html || ('<pre>' + esc(d.body_text || '') + '</pre>'));
    btn.disabled = true;
    btn.textContent = '送信中…';
    S.src.sendMailTest({ subject: subj, html: html, to: m.to }).then(function () {
      return writeAction(mkAction('reminder_sent', { iv: ivNo, ct: null, field: null, source: null,
        value: { packer: d.packer, round: +d.round, stage: d.stage, subject: subj, to: [m.to], cc: [], test: true } }));
    }).then(function () {
      toast('試験送信しました（' + d.packer + ' · ' + d.round + '回目 · 試験用アドレス）', 'ok');
      openRemind(ivNo);
    }).catch(function (e) {
      btn.disabled = false;
      btn.textContent = '送信（試験）';
      toast('送信できませんでした: ' + e.message, 'error');
    });
  }

  /* ── v0.3.17 (R7P · 決定 #175 · #176): 使い方 (1 画面) — 並行期間 (2026-11-16〜11-22) の職員向け。人の名前・メールは書かない ── */
  function openHelp() {
    S.modal = { kind: 'help' };
    var html = '<div class="c01-mh"><b>使い方</b><span class="t2">並行期間 2026-11-16〜11-22</span>' +
      '<span class="c01-flex"></span><button class="c01-btn-ghost2" data-close>閉じる</button></div><div class="c01-mb c01-help" id="help-body">' +
      '<p class="c01-help-lead">並行期間中は <b>これまでのシステムで仕事を続けてください</b>。この TOOL で使うのは <b>「見る」（実況表）</b> と <b>「確認・入力」</b> だけです。<br>' +
      '<span class="c01-trial">試験表示</span> 「催促」 は試験表示です — 業者には送りません（「送信（試験）」は試験用アドレスにだけ届きます · 業者への催促はこれまでどおりの方法で）。 ' +
      '「Compass入力」 は <span class="c01-trial">試験運用中</span> — ボタンを押すと COMPASS に入力します（試験用 · 職員の業務はこれまでどおりの方法で）。</p>' +
      '<div class="c01-help-grid">' +
      '<section><h4>1. 自分の担当を見る</h4><p>実況表の 「担当港」 で <b>「自分の担当」</b> を押すと、自分の港の IV だけが出ます。「全港」 = 全部。港の名前を押すとその港だけ（複数選べます）。</p></section>' +
      '<section><h4>2. 状況の意味</h4><ul>' +
      '<li><span class="st-ok">自動OK</span> — エンジンの値がそろっています（手で確かめる必要なし）</li>' +
      '<li><span class="st-ok">確認済</span> — 人が確認した値です</li>' +
      '<li><span class="c01-help-chk">再確認</span> — 「⚠ 要確認」 を押して値を確かめてください</li>' +
      '<li><span class="st-wait">受信中</span> / <span class="st-wait">メール未着</span> — 書類・写真がまだそろっていません（待ち）</li></ul></section>' +
      '<section><h4>3. 確認・入力</h4><ul>' +
      '<li>タブの数字 = 残りの枚数（コンテナ 1 台 = 1 枚）。原本を見て正しい値を選び 「確認して次へ」。</li>' +
      '<li>どの値も違う時は <b>「✎ 修正」</b> で入力 — 人が入れた値が優先されます。</li>' +
      '<li>搬入票でない書類は <b>「搬入票ではない」</b>（ファイルは消えません）。</li>' +
      '<li>間違えた時は <b>「元に戻す」</b>。わからない時は 「スキップ（あとで）」。</li></ul></section>' +
      '<section><h4>4. 更新・困った時</h4><ul>' +
      '<li>データは 30 秒ごとに自動で更新されます。TOOL が新しくなった時は <b>Ctrl+Shift+R</b> で読み直してください。</li>' +
      '<li>気づいた点は担当の管理者へ（画面の写真と IV 番号）。</li></ul></section>' +
      '</div></div>';
    showModal(html, 'c01-modal-help');
  }

  function findRow(key) {
    var found = null;
    ((S.jik && S.jik.ivs) || []).forEach(function (iv) { iv.rows.forEach(function (r) { if (rowKey(iv, r) === key) found = { iv: iv, r: r }; }); });
    return found;
  }

  /* ── 要確認 横パネル ── */
  function renderPanel(b) {
    var el = $('c01-panel');
    if (!S.sel) { el.innerHTML = ''; el.hidden = true; return; }
    var f = findRow(S.sel);
    if (!f) { S.sel = null; el.hidden = true; return; }
    var iv = f.iv, r = f.r, ov = b.ov;
    var qs = ((S.queue && S.queue.items) || []).filter(function (q) { return q.container_id === r.container_id; });
    var diffQ = {};
    qs.forEach(function (q) { if (q.field) diffQ[q.field] = q; });
    var doc = qs.map(function (q) { return (q.files || [])[0]; }).filter(Boolean)[0] ||
      rowDocs(r).slice().sort(function (a, b) { return DOC_KIND[docKind(a)][1] - DOC_KIND[docKind(b)][1]; })[0];     /* v0.3.23 (R7W Part B): 搬入票 が先 */     /* v0.3.18 (R7S #13): 項目が無くても 行の書類 (rows[].docs) */
    var ph = (S.photos[iv.iv_no] && (S.photos[iv.iv_no].containers || []).filter(function (c) { return c.container_id === r.container_id; })[0]) || null;
    var firstPhoto = ph && ph.photos && ph.photos[0];
    var editMode = S.editRow === S.sel;
    var fields = editMode ? EDIT_FIELDS.map(function (fd) { return '<div class="c01-pf c01-pf-edit">' + editCell(iv, r, fd, '', ov) + '</div>'; }).join('') : VALUE_FIELDS.map(function (fd) {
      var q = diffQ[fd];
      var st = q ? queueState(q, ov) : null;
      if (q && q.kind === '値の違い' && !st.done) {
        var alts = [];
        Object.keys(q.values || {}).forEach(function (src) { (q.values[src] || []).forEach(function (v) { alts.push([src, v]); }); });
        var pick = S.picks[fd];
        return '<div class="c01-pf"><span class="c01-pl">' + FIELD_LABEL[fd] + '</span><div class="c01-alts">' + alts.map(function (a, i) {
          var on = pick && pick[0] === a[0] && String(pick[1]) === String(a[1]);
          return '<button class="c01-alt' + (on ? ' on' : '') + '" data-pick="' + fd + '" data-i="' + i + '"><span class="s">' + esc(a[0]) + '</span><span class="mono v">' + esc(typeof a[1] === 'number' ? a[1].toLocaleString('en-US') : a[1]) + '</span></button>';
        }).join('') + '</div></div>';
      }
      if (q && q.kind === '手入力' && !st.done) {
        return '<div class="c01-pf"><span class="c01-pl">' + FIELD_LABEL[fd] + '</span><div class="c01-note2">読めませんでした — 確認・入力 で原本を見て入力してください</div></div>';
      }
      var note = st && st.done ? '確認済' + (st.by ? ' · ' + st.by : '') : '';
      return '<div class="c01-pf c01-pf-edit">' + editCell(iv, r, fd, note, ov) + '</div>';     /* v0.3.15 (R7N G-4): ✎ 修正 */
    }).join('');
    /* v0.3.22 (R7V F-2): 作業日の理由 (WORK_DATE) がある行 · 作業日要確認 の行 = 作業日 ✎ 修正 (他の値と同じ · 人の値が優先 #109 · 学習の記録) */
    var wdNeed = !editMode && ((r.reasons || []).indexOf('WORK_DATE') >= 0 || !!wdDoubt(r));
    if (wdNeed) fields += '<div class="c01-pf c01-pf-edit">' + editCell(iv, r, 'work_date', '', ov) + '</div>';
    var needPick = Object.keys(diffQ).filter(function (fd) { return diffQ[fd].kind === '値の違い' && !queueState(diffQ[fd], ov).done; });
    var psQ = qs.filter(function (q) { return q.kind === PHOTO_SET && !queueState(q, ov).done && r.ct; })[0] || null;
    var ready = needPick.length > 0 ? (needPick.every(function (fd) { return S.picks[fd]; }) || (needPick.length === 1 && S.panelInput.trim())) : !!psQ;
    var lostMsg = qs.some(function (q) { var s = queueState(q, ov); return s.mineLost; }) ? '<p class="c01-lost">他の人が先に確認しました</p>' : '';
    el.hidden = false;
    setHdrH();                                                    /* v0.3.21 (R7V F-1): 패널 = 상단 공통 바 밑에서 시작 */
    var phtml = '<div class="c01-overlay" id="panel-bg"></div><aside class="c01-side" role="dialog" aria-label="要確認の詳細">' +
      '<div class="c01-side-h"><div><div class="k">' + (editMode ? '修正（' + esc(statusOf(r, iv, ov).st) + '）' : '要確認') + '</div><div class="mono big">' + esc(r.ct || '（CT 不明）') + '</div><div class="t2">' +
      esc(iv.iv_no + ' · ' + (iv.pol || '') + ' · ' + rowVal(iv, r, 'packer').v + ' ' + rowVal(iv, r, 'plant').v) + '</div></div>' +
      '<button class="c01-x" id="panel-close" aria-label="閉じる">✕</button></div>' +
      '<div class="c01-side-b">' + lostMsg +
      (editMode ? '<p class="c01-reason">値を変えると 確認済（手入力）に変わり、記録されます（✎ 修正 · 元に戻す）' + (compassIsDone(iv) ? ' — <b>COMPASS には入力済み — 修正後に Compass入力 をもう一度</b>' : '') + '</p>' :
        '<p class="c01-reason">' + (reasonInfos(r, qs).map(reasonLine).join('<br>') || esc((r.reasons || []).join(' / '))) + '</p>') +
      '<div class="c01-thumbs"><button id="panel-doc" class="c01-thumb"' + (doc ? '' : ' disabled') + '>' + (doc ? (/\.pdf$/i.test(doc.path || '') ? pdfTag(doc.path, doc.page, true, rotMap(doc)) : imgTag(doc.path, 'c01-thimg', '原本')) : '') + '<span>' + (doc ? esc('原本 ' + (doc.name || '') + (doc.page ? ' p' + doc.page : '')) : '原本なし') + '</span></button>' +
      '<button id="panel-photo" class="c01-thumb"' + (firstPhoto ? '' : ' disabled') + '>' + (firstPhoto ? imgTag(firstPhoto.path, 'c01-thimg', '写真') : '') + '<span>' + (firstPhoto ? esc('写真 ' + (firstPhoto.label || '')) : '写真なし') + '</span></button></div>' +
      fields +
      (needPick.length === 1 ? '<label class="c01-direct">どちらも違う場合は直接入力<input id="panel-input" type="text" placeholder="正しい値" value="' + esc(S.panelInput) + '"></label>' : '') +
      (needPick.length || psQ || editMode ? '' : wdNeed ? '<p class="c01-note2">作業日を原本で確認し、違っていれば ✎ 修正 で直してください</p>' :
          statusOf(r, iv, ov).st === '再確認' ? '<p class="c01-note2">値が合っていれば 「このまま確認（OK）」 · 違っていれば ✎ 修正</p>' : '<p class="c01-note2">ここで確認できる項目はありません — 確認・入力 で処理してください</p>') +
      (!editMode && statusOf(r, iv, ov).st === '再確認' ? '<button id="panel-keep" class="c01-btn-ghost2 c01-keep" title="値を変えずに 確認済 にします（記録 · 元に戻す）">このまま確認（OK）</button>' : '') +
      '<div class="c01-side-btns"><button id="panel-ok" class="c01-btn-big' + (ready ? ' ready' : '') + '"' + (ready ? '' : ' disabled') + (editMode ? ' hidden' : '') + '>' + (ready ? '確認する' : '正しい値を選んでください') + '</button>' +
      '<button id="panel-later" class="c01-btn-ghost2">' + (editMode ? '閉じる' : 'あとで') + '</button></div>' +
      '<p class="c01-foot">記録: ' + esc(S.me ? S.me.name : '（担当者を選んでください）') + '</p>' +
      '</div></aside>';
    setHtml(el, phtml, 6);                                        /* v0.3.15 (R7N F): 変わった所だけ */
    hydrate(el);
    bindEdits(el, iv, r);
    $('panel-close').onclick = $('panel-later').onclick = $('panel-bg').onclick = function () { S.sel = null; S.editRow = null; S.qedit = null; render(); };
    if (doc) $('panel-doc').onclick = function () {
      if (!qs.length) { openTab(doc.path); return; }                 /* 確認・入力 の項目が無い行 = 原本を別タブで */
      S.view = 'input'; S.qsel = qs[0].queue_id; S.sel = null; render();
    };
    if (firstPhoto) $('panel-photo').onclick = function (ev) { openPhotos(ev, S.sel, 0); };
    if ($('panel-keep')) $('panel-keep').onclick = function () { keepRow(iv, r, function () { S.sel = null; S.picks = {}; S.panelInput = ''; render(); }); };
    el.querySelectorAll('[data-pick]').forEach(function (b2) {
      b2.onclick = function () {
        var fd = b2.getAttribute('data-pick'), i = +b2.getAttribute('data-i');
        var q = diffQ[fd], alts = [];
        Object.keys(q.values || {}).forEach(function (src) { (q.values[src] || []).forEach(function (v) { alts.push([src, v]); }); });
        S.picks[fd] = alts[i];
        S.panelInput = '';
        render();
      };
    });
    var pin = $('panel-input');
    if (pin) pin.oninput = function () { S.panelInput = pin.value; var btn = $('panel-ok'); var ok = !!pin.value.trim() || needPick.every(function (fd) { return S.picks[fd]; }); btn.disabled = !ok; btn.className = 'c01-btn-big' + (ok ? ' ready' : ''); btn.textContent = ok ? '確認する' : '正しい値を選んでください'; };
    $('panel-ok').onclick = function () {
      if (!S.me) { toast('担当者を選んでください', 'warn'); return; }
      var acts = [];
      for (var k = 0; k < needPick.length; k++) {
        var fd = needPick[k], q = diffQ[fd];
        var typed = needPick.length === 1 ? S.panelInput.trim() : '';
        var val = typed || S.picks[fd][1], src = typed ? '手入力' : S.picks[fd][0];
        var v = C01.validate.field(fd, val);
        if (!v.ok) { toast(FIELD_LABEL[fd] + ': ' + v.error, 'error'); return; }
        acts.push(mkAction('confirm_value', { iv: iv.iv_no, ct: r.ct, field: fd, value: v.value, source: src, queue_id: q.queue_id }));
      }
      if (psQ) acts.push(photoSetAction(psQ, r.ct));
      Promise.all(acts.map(writeAction)).then(function () { S.sel = null; S.picks = {}; S.panelInput = ''; render(); toast('確認しました', 'success'); });
    };
  }

  /* ── 写真 (大きく · 左右 · サムネイル帯) ── */
  function photosOf(key) {
    var f = findRow(key);
    if (!f) return null;
    var p = S.photos[f.iv.iv_no];
    var c = p && (p.containers || []).filter(function (x) { return x.container_id === f.r.container_id; })[0];
    return { title: f.iv.iv_no + ' / ' + (f.r.ct || ''), list: (c && c.photos) || [] };
  }
  function openLightbox(key, idx) {
    var f = findRow(key);
    var go = function () { S.lb = { key: key, idx: idx || 0 }; renderLightbox(); };
    if (f && !S.photos[f.iv.iv_no]) loadPhotos(f.iv.iv_no).then(go); else go();
  }
  /* ── v0.3.13 (R7L Part E · D-65): 写真 = 同じウィンドウの新しいタブ (photo.html) ──
     - クリックの中で window.open('', 名前) (ポップアップ窓にしない = 3 番目の引数なし · openTab と同じくクリックの中で先に開く)。
       名前 = 'c01-photo-' + 行キーのハッシュ (CT そのものは タブ名 · アドレスに入れない) → 同じコンテナをもう一度押すと そのタブへ (新しいタブを作らない)
     - 新しいタブはログインしない: LEENAI_COMMON のトークンはこのタブのメモリだけ (保存しない) → 写真はこのタブが読み (今と同じ Graph GET)、
       Blob を postMessage で渡す (トークンは渡さない · 同じオリジンの photo.html だけに答える)
     - Shift+クリック = これまでのライトボックス (この画面の上) */
  function hkey(s) {
    var h = 0x811c9dc5;
    s = String(s);
    for (var i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 0x01000193) >>> 0; }
    return ('0000000' + h.toString(16)).slice(-8);
  }
  function photoTabName(key) { return 'c01-photo-' + hkey(key); }
  function keyByHash(h) {
    var out = null;
    ((S.jik && S.jik.ivs) || []).forEach(function (iv) { (iv.rows || []).forEach(function (r) { var k = rowKey(iv, r); if (!out && hkey(k) === h) out = k; }); });
    return out;
  }
  /* ── v0.3.23 (R7W Part B · 形님 15:2x): 「📄」 = その行の値の出典書類 (rows[].docs) を 同じウィンドウの新しいタブ (doc.html · photo.html と同じ方式) ──
     並び: 搬入票 → 計量伝票 → 納品書 · その他 → EIR → Excel (エンジン doc_type · 無ければファイル名で) · 書類が無い行 = 「—」 */
  var DOC_KIND = { hannyuhyo: ['搬入票', 0], keiryo: ['計量伝票', 1], eir: ['EIR', 2], excel: ['Excel', 3], nouhin: ['納品書', 4], vanning_list: ['バンニング表', 4],
    other: ['書類', 5], inspection: ['検査', 9] };   /* v0.3.24 (R7X Part H ②): 検査書類 (COTECNA 等) は最後 · 📄 の数 = 開ける書類 (path あり) */
  function docKind(d) {
    var t = d.doc_type, n = String(d.name || d.path || '');
    if (!t || !DOC_KIND[t]) {
      if (/\.(xlsx|xlsm|xls|csv)$/i.test(n)) t = 'excel';
      else if (/計量/.test(n)) t = 'keiryo';
      else if (/納品/.test(n)) t = 'nouhin';
      else if (/EIR|機器受渡/i.test(n)) t = 'eir';
      else t = 'hannyuhyo';
    }
    return t;
  }
  function rowDocList(r) {
    var src = Array.isArray(r.docs) && r.docs.length ? r.docs : rowDocs(r);
    var seen = {}, out = [];
    src.forEach(function (d) {
      if (!d || !d.path) return;
      var k = d.path + '#' + (d.page || '');
      if (seen[k]) return;
      seen[k] = 1;
      var t = docKind(d), name = d.name || String(d.path).split('/').pop();
      var ext = (String(name).match(/\.([a-z0-9]+)$/i) || [])[1] || '';
      var rot = rotMap(d), pg = d.page || 1;
      out.push({ path: d.path, name: name, page: d.page || null, kind: t, kindText: DOC_KIND[t][0], order: DOC_KIND[t][1], ext: ext.toLowerCase(),
        rot: ((rot[String(pg)] || rot['*'] || 0) + rotMemGet(rotMemKey(d.sha16, pg))) % 360, fields: (d.fields || []).map(function (f) { return FIELD_LABEL[f] || f; }) });
    });
    return out.sort(function (a, b) { return a.order - b.order; });
  }
  function docCell(r, key) {
    var n = rowDocList(r).length;
    return n ? ' <button class="c01-docbtn" data-docs="' + esc(key) + '" title="この行の値の出典書類 ' + n + ' 件を新しいタブで表示（搬入票が先）">📄' + n + '</button>' : ' <span class="t2" title="出典書類なし">—</span>';
  }
  function openDocs(key) {
    var h = hkey(key);
    var w = window.open('', 'c01-doc-' + h);
    if (!w) { toast('ブラウザがポップアップを止めました — このサイトのポップアップを許可してください', 'warn'); return; }
    var same = false;
    try { same = /doc\.html$/.test(w.location.pathname) && w.location.search.indexOf('k=' + h) >= 0; } catch (e) { same = false; }
    if (!same) w.location.href = new URL('doc.html?k=' + h, location.href).href;
    try { w.focus(); } catch (e) { /* なし */ }
  }
  function serveDocs(win, h) {
    var send = function (m) { m.k = h; try { win.postMessage(m, msgOrigin()); } catch (e) { /* タブが閉じた */ } };
    if (!S.jik) { send({ t: 'c01-doc-wait' }); return; }
    var key = keyByHash(h);
    if (!key) { send({ t: 'c01-doc-err', msg: 'このコンテナは今の実況表にありません — 実況表から開き直してください' }); return; }
    var f = findRow(key);
    var list = rowDocList(f.r);
    send({ t: 'c01-doc-head', head: { iv: f.iv.iv_no, ct: f.r.ct || '', packer: rowVal(f.iv, f.r, 'packer').v || '', plant: rowVal(f.iv, f.r, 'plant').v || '',
      docs: list.map(function (d) { return { name: d.name, page: d.page, kind: d.kind, kindText: d.kindText, ext: d.ext, rot: d.rot, fields: d.fields }; }) } });
    var next = 0;
    function one() {
      var i = next++;
      if (i >= list.length) return Promise.resolve();
      var rel = list[i].path;
      var web = /^(xlsx|xlsm|xls|csv)$/.test(list[i].ext) && S.src && typeof S.src.webUrl === 'function' ? S.src.webUrl(rel).catch(function () { return ''; }) : Promise.resolve('');
      var pu = isFolder() ? S.src.resolveUrl(rel) : Promise.resolve(S.src.fileUrl(rel));
      return Promise.all([pu, web]).then(function (x) {
        if (!x[0]) return send({ t: 'c01-doc-file', i: i, err: fileErrText(rel), web: x[1] || '' });
        return fetch(x[0]).then(function (r) { if (!r.ok) throw new Error('http' + r.status); return r.blob(); })
          .then(function (b) { send({ t: 'c01-doc-file', i: i, blob: b, web: x[1] || '' }); });
      }).catch(function () { send({ t: 'c01-doc-file', i: i, err: fileErrText(rel) }); }).then(one);
    }
    return Promise.all([one(), one()]);
  }
  function openPhotos(ev, key, idx) {
    if (ev && ev.shiftKey) { if (ev.preventDefault) ev.preventDefault(); openLightbox(key, idx); return; }
    var h = hkey(key);
    var url = new URL('photo.html?k=' + h + (idx ? '&i=' + idx : ''), location.href).href;
    var w = window.open('', photoTabName(key));
    if (!w) { toast('ブラウザがポップアップを止めました — このサイトのポップアップを許可してください (この画面で表示します)', 'warn'); openLightbox(key, idx); return; }
    var same = false;
    try { same = /photo\.html$/.test(w.location.pathname) && w.location.search.indexOf('k=' + h) >= 0; } catch (e) { same = false; }
    if (same) { try { w.postMessage({ t: 'c01-photo-go', k: h, i: idx || 0 }, msgOrigin()); } catch (e) { /* なし */ } }
    else w.location.href = url;
    try { w.focus(); } catch (e) { /* なし */ }
    if (!S.photoTabs) S.photoTabs = {};
    S.photoTabs[h] = w;
  }
  function msgOrigin() { return location.origin && location.origin !== 'null' ? location.origin : '*'; }
  /* 写真タブ (photo.html) からの要求 → 見出し + 写真 (Blob) を順に返す */
  function photoKindSrc(p) { return { label: p.label || '', fill: p.fill || '', kind: p.kind || '' }; }
  function servePhotos(win, h) {
    var send = function (m) { m.k = h; try { win.postMessage(m, msgOrigin()); } catch (e) { /* タブが閉じた */ } };
    if (!S.jik) { send({ t: 'c01-photo-wait' }); return; }
    var key = keyByHash(h);
    if (!key) { send({ t: 'c01-photo-err', msg: 'このコンテナは今の実況表にありません — 実況表から開き直してください' }); return; }
    var f = findRow(key);
    var d0 = S.photos[f.iv.iv_no] ? (photosOf(key) || { list: [] }) : null;
    var stale = !d0 || ((f.r.photos || 0) > 0 && (d0.list || []).length !== (f.r.photos || 0));     /* v0.3.24 (R7X Part E ③) */
    (stale ? loadPhotos(f.iv.iv_no, f.iv.photos_sig || undefined) : Promise.resolve()).then(function () {
      var d = photosOf(key) || { list: [] };
      var list = d.list || [];
      send({ t: 'c01-photo-head', head: { iv: f.iv.iv_no, ct: f.r.ct || '', packer: rowVal(f.iv, f.r, 'packer').v || '', plant: rowVal(f.iv, f.r, 'plant').v || '',
        n: list.length, photos: list.map(function (p, i) { var o = photoKindSrc(p); o.no = p.no || i + 1; o.name = String(p.path || '').split('/').pop(); return o; }) } });
      var next = 0;
      function one() {
        var i = next++;
        if (i >= list.length) return Promise.resolve();
        var rel = list[i].path;
        var pu = isFolder() ? S.src.resolveUrl(rel) : Promise.resolve(S.src.fileUrl(rel));
        return pu.then(function (u) {
          if (!u) return send({ t: 'c01-photo-img', i: i, err: fileErrText(rel) });
          return fetch(u).then(function (r) { if (!r.ok) throw new Error('http' + r.status); return r.blob(); })
            .then(function (b) { send({ t: 'c01-photo-img', i: i, blob: b }); });
        }).catch(function () { send({ t: 'c01-photo-img', i: i, err: fileErrText(rel) }); }).then(one);
      }
      return Promise.all([one(), one(), one()]);
    });
  }
  window.addEventListener('message', function (e) {
    var d = e.data;
    if (!d || typeof d !== 'object' || (d.t !== 'c01-photo-req' && d.t !== 'c01-doc-req') || !e.source) return;
    if (e.origin !== location.origin) return;                         /* 同じオリジン (この TOOL) の photo.html · doc.html だけ */
    (d.t === 'c01-doc-req' ? serveDocs : servePhotos)(e.source, String(d.k || '').replace(/[^0-9a-f]/g, '').slice(0, 8));
  });
  function openLightboxList(title, list, idx) { S.lb = { title: title, list: list, idx: idx || 0 }; renderLightbox(); }
  function renderLightbox() {
    var el = $('c01-lb');
    if (!S.lb) { el.hidden = true; el.innerHTML = ''; return; }
    var d = S.lb.list ? { title: S.lb.title, list: S.lb.list } : photosOf(S.lb.key);
    if (!d || !d.list.length) { S.lb = null; el.hidden = true; el.innerHTML = ''; toast('このコンテナの写真はまだありません', 'warn'); return; }  /* v0.3.3: 何も起きないのをやめる */
    var n = d.list.length, i = ((S.lb.idx % n) + n) % n;
    S.lb.idx = i;
    var p = d.list[i];
    el.hidden = false;
    el.innerHTML = '<div class="c01-lb" role="dialog" aria-label="写真">' +
      '<div class="c01-lb-h"><span class="mono">' + esc(d.title) + '</span><span class="c">' + (i + 1) + ' / ' + n + ' · ' + esc(p.label || ('写真 ' + (i + 1))) + '</span>' +
      '<span class="c01-flex"></span><button class="c01-lb-x" id="lb-close" aria-label="閉じる">✕</button></div>' +
      '<div class="c01-lb-m"><button class="c01-lb-nav" id="lb-prev" aria-label="前の写真">‹</button>' +
      '<div class="c01-lb-img" id="lb-stage">' + imgTag(p.path, 'c01-lbimg', p.label) + '</div>' +
      '<button class="c01-lb-nav" id="lb-next" aria-label="次の写真">›</button></div>' +
      '<div class="c01-lb-strip">' + d.list.map(function (q, k) {
        return '<button class="c01-lb-th' + (k === i ? ' on' : '') + '" data-go="' + k + '" title="' + esc(q.label || '') + '">' + imgTag(q.path, 'c01-thimg', q.label) + '</button>';
      }).join('') + '</div></div>';
    hydrate(el);
    $('lb-close').onclick = function () { S.lb = null; renderLightbox(); };
    $('lb-prev').onclick = function () { S.lb.idx -= 1; renderLightbox(); };
    $('lb-next').onclick = function () { S.lb.idx += 1; renderLightbox(); };
    el.querySelectorAll('[data-go]').forEach(function (b) { b.onclick = function () { S.lb.idx = +b.getAttribute('data-go'); renderLightbox(); }; });
    var img = el.querySelector('.c01-lbimg'), scale = 1;
    $('lb-stage').onwheel = function (e) { e.preventDefault(); scale = Math.max(1, Math.min(4, scale * (e.deltaY < 0 ? 1.15 : 1 / 1.15))); if (img) img.style.transform = 'scale(' + scale + ')'; };
  }
  document.addEventListener('keydown', function (e) {
    if (!S.lb) return;
    if (e.key === 'ArrowLeft') { S.lb.idx -= 1; renderLightbox(); }
    if (e.key === 'ArrowRight') { S.lb.idx += 1; renderLightbox(); }
    if (e.key === 'Escape') { S.lb = null; renderLightbox(); }
  });

  /* ── 確認・入力 ── */
  function openQueue() {
    var ov = overlay();
    return qItems().filter(function (q) { return !queueState(q, ov).done && queuePortOk(q) && !faxHidden(q) && !exclHidden(q, ov) && !noDocWait(q); });
  }
  /* v0.3.2 (R7B): 未分類 FAX — 受信から C01.QUEUE.faxHideAfterDays 日を過ぎたものは既定で隠す (隠すだけ · 消さない) */
  function faxOld(q) {
    var n = (C01.QUEUE && +C01.QUEUE.faxHideAfterDays) || 0;
    var today = (S.info && S.info.today) || (S.jik && S.jik.today);
    if (!n || q.kind !== '未分類FAX' || !q.received_at || !today) return false;
    return addDays(String(q.received_at).slice(0, 10), n) < today;
  }
  function faxHidden(q) { return !S.showOldFax && faxOld(q); }
  function queuePortOk(q) {
    if (!q.iv_no) return true;
    var iv = ((S.jik && S.jik.ivs) || []).filter(function (x) { return x.iv_no === q.iv_no; })[0];
    return !iv || (portOk(iv.pol) && ivLive(iv));
  }
  /* v0.3.22 (R7V Part 0-2 · 決定 #194): 実況表 · 確認・入力 · 件数 = CY CUT ≥ 今日 (JST) の IV だけ (過ぎた IV は隠すだけ · データはそのまま)。
     今日 = _data info.today (エンジンが書いた日) · 無ければ この端末の JST 日付。旧 phase4_report.py:569 (cy_cut < today → 表示しない) と同じ。
     CY CUT が無い IV は表示 (旧は外す — 作業が残っている行を隠さないため) */
  function todayJst() {
    var t = (S.info && S.info.today) || (S.jik && S.jik.today);
    if (t) return String(t).slice(0, 10);
    return new Date(Date.now() + 9 * 3600 * 1000).toISOString().slice(0, 10);
  }
  function ivLive(iv) {
    var c = iv && iv.cy_cut ? String(iv.cy_cut).slice(0, 10) : '';
    return !c || c >= todayJst();
  }
  /* 写真枚数の色 (v0.3.10 · 決定 #143 · 表示だけ): 業者ごとの通常範囲 (エンジン meta.photo_range = 10〜90% の 下 −2 · 上 +3 · 週 1 回計算) の外。
     範囲のない業者 (台数 10 未満) · meta がない時 = 旧 実況表 (phase4_report.py · photo_count < 6 or >= 15) と同じ基準 */
  function photoRange(pk) {
    var pr = S.meta && S.meta.photo_range;
    var r = pr && pr.packers && pk ? pr.packers[String(pk).toUpperCase()] : null;
    return r && typeof r.lo === 'number' && typeof r.hi === 'number' ? r : null;
  }
  function photoAlert(n, pk) {
    n = +n || 0;
    var r = photoRange(pk);
    if (r) return n < r.lo || n > r.hi;
    return n <= 5 || n >= 15;
  }
  function photoRangeText(pk) {
    var r = photoRange(pk);
    return r ? 'この業者の通常 ' + r.lo + '〜' + r.hi + '枚の外' : '5枚以下・15枚以上';
  }
  function photoAlertText(n, pk) { return '写真 ' + (+n || 0) + '枚（' + photoRangeText(pk) + '）'; }
  function kindLabel(k) { return (KIND[k] && KIND[k].label) || k; }
  /* v0.3.3 (R7C) → v0.3.15 (R7N Part G-2 · G-2-0): 確認・入力 の原本 = この行と結び付いた書類だけ (項目のファイル + 同じコンテナの別の項目のファイル)。
     「この項目の原本の指定がないため IV の書類を表示」 (IV の書類全部) は やめた — 別の CT の搬入票が出て紛らわしいため。
     ほかの 自動OK · 確認済 の行に使われた書類 · ページは 外す。結び付いた書類が無い時だけ、どの行にも使われていない IV の書類を 「候補」 で 1〜2 件
     (エンジンが 行ごとの書類 rows[].doc_sha16 を出している IV だけ — 無いと 自動OK の行の書類が分からないので候補は出さない)。どれも無い = 「搬入票なし（待ち）」 */
  var CAND_MAX = 2;
  function okRowStatus(iv, r, ov) { var st = statusOf(r, iv, ov).st; return st === '自動OK' || st === '確認済'; }
  function usedByOthers(q, ov) {
    var used = {};
    var mine = q.container_id || null;
    qItems().forEach(function (y) {
      if (!y.container_id || y.container_id === mine) return;
      var x = rowByCid(y.container_id);
      if (!x || !okRowStatus(x.iv, x.r, ov)) return;
      (y.files || []).forEach(function (f) { if (f.sha16) used[f.sha16 + '#' + (f.page || '')] = 1; });     /* ページ単位 (page なし = ファイル全体) */
    });
    var iv = q.iv_no ? ivIndex()[q.iv_no] : null;
    ((iv && iv.rows) || []).forEach(function (r) {
      if (r.container_id === mine || !Array.isArray(r.doc_sha16) || !okRowStatus(iv, r, ov)) return;
      r.doc_sha16.forEach(function (h) { used[h + '#'] = 1; });
    });
    return used;
  }
  function docCands(q, ov) {
    var iv = q.iv_no ? ivIndex()[q.iv_no] : null;
    if (!iv || !(iv.rows || []).some(function (r) { return Array.isArray(r.doc_sha16); })) return { list: [], n: 0 };
    var ph = S.photos[q.iv_no];
    if (!ph) {
      if (!S.qload) S.qload = {};
      if (!S.qload[q.iv_no]) { S.qload[q.iv_no] = 1; loadPhotos(q.iv_no).then(function () { render(); }); }
      return { list: [], n: 0 };
    }
    var used = {};
    (iv.rows || []).forEach(function (r) { (r.doc_sha16 || []).forEach(function (h) { used[h] = 1; }); });
    qItems().forEach(function (y) { if (y.container_id) (y.files || []).forEach(function (f) { if (f.sha16) used[f.sha16] = 1; }); });
    var excl = (ov && ov.excl) || {};
    var left = (ph.docs || []).filter(function (d) {
      return d && d.path && d.sha16 && !used[d.sha16] && !excl[d.sha16] && !/(^|\/)thumbs\.db$|\.db$/i.test(d.path);
    });
    var list = left.length <= CAND_MAX ? left.map(function (d) {
      return { path: d.path, name: String(d.path).split('/').pop(), page: 1, sha16: d.sha16, rotation: d.rotation, cand: true,
        candWhy: 'この IV のどの行にも使われていない書類（' + left.length + '件）' };
    }) : [];
    return { list: list, n: left.length };
  }
  /* v0.3.18 (R7S #1 · #5 · #13): 行の書類 — エンジンの rows[].docs (次の版 · [{path, name, page, sha16, rotation}]) があればそれ ·
     無ければ その行 (container_id) の 確認・入力 項目のファイル。同一コンテナ候補 · 要確認の横パネル · 実況表の 「原本」 で使う */
  function rowDocs(r) {
    var out = [], seen = {};
    var add = function (f) {
      if (!f || !f.path) return;
      var k = f.path + '#' + (f.page || '');
      if (seen[k]) return;
      seen[k] = 1;
      out.push(f.name ? f : Object.assign({}, f, { name: String(f.path).split('/').pop() }));
    };
    if (!r) return out;
    (Array.isArray(r.docs) ? r.docs : []).forEach(add);
    if (r.container_id) qItems().forEach(function (y) { if (y.container_id === r.container_id && DOC_KINDS[y.kind]) (y.files || []).forEach(add); });
    return out;
  }
  /* 同一コンテナ候補の 写真の行 の写真から 扉 · 側面 CT · シール を (無ければ先頭から) 最大 4 枚 */
  var SAME_PH = [[/^(door|closed|door_closed)$|扉|ドア/i, '扉'], [/^side_ct$|側面/i, '側面 CT'], [/^seal$|シール|seal/i, 'シール']];
  function samePhotos(q) {
    var ph = q && q.same && S.photos[q.iv_no];
    if (!ph) return [];
    var c = (ph.containers || []).filter(function (x) { return x.container_id === q.same.photo.container_id; })[0];
    var list = (c && c.photos) || [];
    var out = [];
    SAME_PH.forEach(function (k) {
      list.forEach(function (p, i) {
        if (out.length >= 4 || out.some(function (o) { return o.i === i; })) return;
        if (k[0].test(String(p.kind || p.label || '')) || (k[1] === '扉' && /^door_closed$/.test(String(p.fill || '')))) out.push({ p: p, i: i, kind: k[1] });
      });
    });
    if (!out.length) list.slice(0, 3).forEach(function (p, i) { out.push({ p: p, i: i, kind: '' }); });
    return out;
  }
  function qFilesInfo(q) {
    if (q.kind === SAME) return { files: q.same ? rowDocs(q.same.fax) : [], cands: 0 };
    var own = (q.files || []).filter(function (f) { return f && f.path; });
    if (q.kind === '写真のCT' || q.kind === PHOTO_SET || q.kind === '未分類FAX' || q.kind === HOLD || !q.iv_no) return { files: own, cands: 0 };
    var ov = overlay();
    var used = usedByOthers(q, ov);
    var fs = linkedFiles(q).filter(function (f) { return !f.sib || !(f.sha16 && (used[f.sha16 + '#' + (f.page || '')] || used[f.sha16 + '#'])); });
    if (fs.length) return { files: fs, cands: 0 };
    var c = docCands(q, ov);
    return { files: c.list, cands: c.n };
  }
  function qFiles(q) { return qFilesInfo(q).files; }
  /* 選んでいなければ 画面に出せるファイル (PDF · 画像) を先に — 名前に「搬入」があればそれ (Excel などが先頭だと「表示できません」になるため) */
  function curFileIdx(q) {
    var fs = qFiles(q), n = fs.length;
    if (!n) return 0;
    if (S.qfile[q.queue_id] !== undefined) return Math.min(Math.max(0, +S.qfile[q.queue_id] || 0), n - 1);
    var showable = function (f) { return /\.(pdf|png|jpe?g|gif|svg|webp|bmp)$/i.test(f.path || ''); };
    for (var k = 0; k < n; k++) if (showable(fs[k]) && /搬入/.test(fs[k].name || fs[k].path || '')) return k;
    for (var j = 0; j < n; j++) if (showable(fs[j])) return j;
    return 0;
  }
  function renderInput() {
    var ov = overlay();
    var all0 = ((S.queue && S.queue.items) || []).filter(queuePortOk);
    var oldFaxN = all0.filter(faxOld).length;
    var qc = queueCards(ov);
    var all = qc.all, cards = qc.cards;
    S.cards = cards;
    /* v0.3.11 (R7J Part A · B): 一覧 = カード (コンテナ 1 台 = 1 枚) · 終わったカードは一覧から外れる (「完了」で見られる) · 進み具合 = 枚数 */
    var doneN = cards.filter(function (cd) { return cd.done; }).length;
    var ivOk = function (cd) { return !S.qiv || cardIv(cd).indexOf(S.qiv) >= 0; };
    var counts = { all: cards.filter(function (cd) { return !cd.done && ivOk(cd); }).length, done: doneN };
    Object.keys(KIND).forEach(function (k) { counts[k] = cards.filter(function (cd) { return ivOk(cd) && cd.open.some(function (q) { return q.kind === k; }); }).length; });
    var vis = cards.filter(function (cd) {
      if (!ivOk(cd)) return false;
      if (S.qkind === 'done') return cd.done;
      return !cd.done && (S.qkind === 'all' || cd.open.some(function (q) { return q.kind === S.qkind; }));
    });
    var firstOf = function (cd) { return (cd.open[0] || cd.items[0]).queue_id; };
    var inVis = function (id) { return vis.some(function (cd) { return cd.items.some(function (q) { return q.queue_id === id; }); }); };
    if (!S.qsel || !inVis(S.qsel)) { S.qsel = vis.length ? firstOf(vis[0]) : null; }
    var q = all.filter(function (x) { return x.queue_id === S.qsel; })[0] || null;
    var card = q ? cardOf(cards, q.queue_id) : null;
    var iv = q && q.iv_no ? ((S.jik && S.jik.ivs) || []).filter(function (x) { return x.iv_no === q.iv_no; })[0] : null;
    var html = '<div class="c01-input">';
    var kindKeys = Object.keys(KIND).filter(function (k) {
      if (k === FOREIGN) return all.some(function (y) { return y.kind === FOREIGN; });     /* v0.3.20: 他社搬入票候補 = ある時だけ */
      return (k !== PHOTO_SET && k !== HOLD && k !== SAME && k !== VCHK) || ((S.queue && S.queue.kinds) || []).indexOf(k) >= 0 || (k === SAME && all.some(function (y) { return y.kind === SAME; }));
    });
    html += '<aside class="c01-list" aria-label="作業リスト"><div class="c01-kinds">' +
      [['all', 'すべて']].concat(kindKeys.map(function (k) { return [k, kindLabel(k)]; })).concat([['done', '完了']]).map(function (k) {
        return '<button class="c01-chip' + (S.qkind === k[0] ? ' on' : '') + (k[0] === 'done' ? ' c01-chip-done' : '') + '" data-kind="' + esc(k[0]) + '">' + esc(k[1]) + ' ' + (counts[k[0]] || 0) + '</button>';
      }).join('') + '</div>' +
      (S.qiv ? '<div class="c01-qiv"><span class="t2">IV で絞り込み:</span> <span class="mono">' + esc(S.qiv) + '</span> <button class="c01-btn-ghost2" id="qiv-clear">解除</button></div>' : '') +
      (oldFaxN ? '<label class="c01-chk" id="fax-old-lab"><input type="checkbox" id="fax-old"' + (S.showOldFax ? ' checked' : '') + '>古い未分類 FAX も表示（受信 ' +
        C01.QUEUE.faxHideAfterDays + '日超 · ' + oldFaxN + '件）</label>' : '') +
      '<div class="c01-prog"><div class="bar"><div style="width:' + (cards.length ? Math.round(doneN / cards.length * 100) : 0) + '%"></div></div><span>' + doneN + ' / ' + cards.length + ' 完了</span></div>' +
      '<div class="c01-items">' + vis.map(function (cd) {
        var x = cd.open[0] || cd.items[0];
        var on = cd.items.some(function (y) { return y.queue_id === S.qsel; });
        var flds = [];
        cd.items.forEach(function (y) { if (y.field && VALUE_KINDS[y.kind] && flds.indexOf(FIELD_LABEL[y.field]) < 0) flds.push(FIELD_LABEL[y.field]); });
        var last = cd.items.map(function (y) { return queueState(y, ov); }).filter(function (st) { return st.done; })[0] || {};
        return '<button class="c01-item' + (on ? ' on' : '') + (cd.done ? ' done' : '') + '" data-q="' + esc(x.queue_id) + '" data-card="' + esc(cd.key) + '">' +
          '<span class="r1">' + cd.kinds.map(function (k) { return '<span class="k" style="color:' + KIND[k].color + '">' + esc(kindLabel(k)) + '</span>'; }).join('<span class="t2"> · </span>') +
          '<span class="c01-flex"></span><span class="cy">CY ' + esc(md(x.cy_cut) || '—') + '</span></span>' +
          '<span class="mono t">' + esc(x.kind === '写真のCT' ? 'CT 不明の写真 ' + (x.files || []).length + '枚' : (x.kind === '未分類FAX' || x.kind === HOLD) ? ((x.files || [])[0] || {}).name || 'FAX' : (x.ct || '（CT 不明）')) + '</span>' +
          '<span class="s">' + esc((x.iv_no ? x.iv_no + ' · ' : (x.kind === HOLD && (x.candidates || []).length ? '候補 ' + x.candidates.join(' / ') + ' · ' : '')) + flds.join('・') + (x.issuer ? ' · ' + x.issuer : '') +
            ((x.kind === '未分類FAX' || x.kind === HOLD) && x.received_at ? '受信 ' + md(String(x.received_at).slice(0, 10)) : '') + (cd.items.length > 1 ? ' · ' + cd.items.length + '項目' : '')) + '</span>' +
          (cd.done ? '<span class="d">' + (last.mineLost ? '他の人が先に確認しました' : (last.act === 'not_hannyuhyo' || last.act === 'not_ours' ? '搬入票ではない' : '完了') + (last.by ? ' · ' + esc(last.by) : '')) + '</span>' : '') + '</button>';
      }).join('') + (vis.length ? '' : '<p class="c01-empty">' + (S.qkind === 'done' ? '完了した作業はまだありません' : '作業はありません') + '</p>') + '</div></aside>';
    /* 原本 */
    html += '<section class="c01-orig" aria-label="原本">';
    var curF = null;
    if (q) {
      var isPhotos = q.kind === '写真のCT' || q.kind === PHOTO_SET;
      var fInfo = isPhotos ? { files: q.files || [], cands: 0 } : qFilesInfo(q);
      var files = fInfo.files;
      var fIdx = isPhotos ? 0 : curFileIdx(q);
      var f = files[fIdx] || {};
      curF = isPhotos ? null : f;
      var qrow = q.container_id && iv ? iv.rows.filter(function (r) { return r.container_id === q.container_id; })[0] : null;
      var qph = qrow ? (qrow.photos || 0) : null;
      var isPdfF = !isPhotos && /\.pdf$/i.test(f.path || '');
      var pdfPg = isPdfF ? (S.pdfPage[pdfKey(q, f)] || f.page || 1) : 0;
      var rots = isPhotos ? {} : rotMap(f);
      var rk = !isPhotos && f.sha16 ? rotMemKey(f.sha16, isPdfF ? pdfPg : f.page) : null;     /* v0.3.24 G-3: 別のファイル · ページに移った時 = 覚えた角度 (無ければ 0) */
      if (rk !== S.rotKey) { S.rotKey = rk; if (rk) S.rot = rotMemGet(rk); }
      var baseRot = isPhotos ? 0 : rotOf(rots, isPdfF ? pdfPg : f.page);
      html += '<div class="c01-orig-h"><span class="t2">' + (isPhotos ? '写真' : q.kind === '未分類FAX' ? 'FAX' : q.kind === HOLD ? '保留中の書類' : q.kind === SAME ? 'FAX の行の搬入票' : '搬入票') + '</span><span class="mono">' + esc(isPhotos ? files.length + '枚' : (f.name || '')) + '</span>' +
        (qph !== null ? '<span class="c01-phcount' + (photoAlert(qph, rowVal(iv, qrow, 'packer').v) ? ' c01-ph-alert' : '') + '" title="' + esc('このコンテナの写真枚数（' + photoRangeText(rowVal(iv, qrow, 'packer').v) + 'は色付き）') + '">写真 ' + qph + '枚</span>' : '') + '<span class="c01-flex"></span>' +
        (baseRot ? '<span class="c01-autorot" id="q-autorot" title="エンジンが判読の時に見つけたページの向きで表示しています（⟳ でさらに回せます）">向き補正 ' + baseRot + '°</span>' : '') +
        (!isPhotos && f.path ? '<button class="c01-tool" id="z-out" aria-label="縮小">−</button><span class="z">' + S.zoom + '%</span><button class="c01-tool" id="z-in" aria-label="拡大">+</button>' +
          '<button class="c01-tool" id="rot" aria-label="回転">⟳</button>' +
          (isPdfF ? '<button class="c01-tool" id="pdf-prev" aria-label="前のページ">‹</button><span class="t2" id="pdf-pg">p.' + pdfPg + '</span><button class="c01-tool" id="pdf-next" aria-label="次のページ">›</button>' +
            '' : '<span class="t2">' + (f.page ? 'p.' + f.page : '') + '</span>') : '') +
        (!isPhotos && f.path ? '<button class="c01-btn-sub" id="pdf-open" title="SharePoint で開く（別タブ）">別タブで開く</button>' : '') + '</div>';
      var anyCand = files.some(function (x) { return x.cand; });
      if (!isPhotos && (files.length > 1 || anyCand)) {
        html += '<div class="c01-qfiles" role="tablist" aria-label="原本ファイル">' + (anyCand ? '<span class="t2">この行の搬入票がまだ決まっていません — 候補:</span>' : '') + files.map(function (x, k) {
          return '<button class="c01-chip' + (k === fIdx ? ' on' : '') + (x.cand ? ' c01-candchip' : '') + '" data-qf="' + k + '"' + (x.cand ? ' data-cand="1"' : '') + ' title="' + esc((x.cand ? '候補 — ' + x.candWhy + ' · ' : '') + (x.name || '')) + '">' +
            (x.cand ? '候補 ' : (k + 1) + '. ') + esc(String(x.name || '').slice(0, 28)) + (x.page && !x.cand ? ' p' + x.page : '') + '</button>';
        }).join('') + '</div>';
      }
      if (!isPhotos && f.cand) html += '<p class="c01-candnote" id="q-candnote">候補 — ' + esc(f.candWhy) + '。この行の書類とは決まっていません。違う時は 「スキップ」 で 搬入票を待ってください。</p>';
      var isSame = q.kind === SAME && q.same;
      html += (isSame ? '<div class="c01-samerow">' : '') + '<div class="c01-orig-b">';
      if (isPhotos) {
        html += '<div class="c01-grid">' + files.map(function (pf, k) { return '<button class="c01-gph" data-gph="' + k + '">' + imgTag(pf.path, 'c01-gimg', pf.name) + '<span>' + esc(pf.name || '') + '</span></button>'; }).join('') + '</div>';
      } else if (f.path) {
        var isPdf = /\.pdf$/i.test(f.path), isImg = /\.(png|jpe?g|gif|svg|webp|bmp)$/i.test(f.path);
        var bw = isSame ? 440 : 640;                                  /* 同一候補 = 右に写真の列があるので 原本は少し小さく */
        var w = Math.round(bw * S.zoom / 100);
        if (isImg) {
          /* v0.3.18 (R7S #3): 画像の回転 — 前は 箱ごと CSS rotate だけで 90° · 270° の時 箱が回す前の大きさのまま (上が切れてスクロールできない · 下が空く)。
             いまは 箱 = 回した後の大きさ (90° · 270° = 幅 ↔ 高さ · 画像を読んだ後に合わせる docFit) · 中の画像 = 左上を軸に回して箱の中へ (translate) ·
             エンジンの向き (data-base-rot) + ⟳ · 拡大縮小も同じ */
          var tr = (S.rot + baseRot) % 360;
          html += '<div class="c01-doc img" data-base-rot="' + baseRot + '" data-rot="' + tr + '" data-w="' + w + '" style="width:' + w + 'px' + (tr % 180 ? ';height:' + w + 'px' : '') + '">' +
            '<div class="c01-docrot r' + tr + '" style="width:' + w + 'px;transform:' + DOC_TF[tr] + '">' + imgTag(f.path, 'c01-docimg', f.name);
          if (f.bbox && f.bbox.length === 4) {
            var bb = f.bbox;
            html += '<div class="c01-bbox" style="left:' + (bb[0] * 100) + '%;top:' + (bb[1] * 100) + '%;width:' + ((bb[2] - bb[0]) * 100) + '%;height:' + ((bb[3] - bb[1]) * 100) + '%"></div>';
          }
          html += '</div></div>';
        } else if (isPdf) {
          html += '<div class="c01-doc pdf">' + pdfTag(f.path, pdfPg, false, rots, pdfKey(q, f), bw) + '</div>';   /* v0.3.2: 回転・拡大は pdf.js の描画で (CSS 回転なし) · v0.3.15: エンジンの向き */
        } else {
          html += '<div class="c01-doc"><p class="c01-note2">このファイルは画面に表示できません（' + esc(f.name || '') + '）— 上の「別タブで開く」で SharePoint で開けます' + (/\.xls[xm]?$/i.test(f.path) ? ' (Excel)' : '') + '</p></div>';
        }
      } else if (q.kind === SAME) {
        html += '<p class="c01-note2 c01-nodoc" id="q-samenodoc">FAX の行の原本がまだ分かりません（エンジンの出力に この行の書類がありません）— 写真と 下の値で確認してください</p>';
      } else if (DOC_KINDS[q.kind] && q.kind !== '未分類FAX' && q.kind !== HOLD) {
        html += '<p class="c01-note2 c01-nodoc" id="q-nodoc">搬入票なし（待ち）' + (fInfo.cands > CAND_MAX ? ' — この IV に行の決まっていない書類が ' + fInfo.cands + '件あります（候補にしません）' : '') + '</p>';
      } else {
        html += '<p class="c01-note2">原本ファイルがありません</p>';
      }
      /* v0.3.18 (R7S #5): 同一コンテナ候補 = 左 FAX の原本 (そのページ) · 右 写真の行の 扉 · 側面 CT · シール の写真 (並べて見る) */
      if (isSame) {
        html += '</div>';                                           /* 原本 (スクロール) の右に 写真の列 (いつも見える) */
        if (!S.photos[q.iv_no]) { if (!S.qload) S.qload = {}; if (!S.qload[q.iv_no]) { S.qload[q.iv_no] = 1; loadPhotos(q.iv_no).then(function () { render(); }); } }
        var sps = samePhotos(q);
        html += '<div class="c01-samephs" id="q-samephs" aria-label="写真の行の写真"><div class="t2">写真の行 · ' + esc(q.same.photo.ct || '') + '</div>' +
          (sps.length ? sps.map(function (e) {
            return '<button class="c01-sameph" data-sameph="' + e.i + '" title="' + esc((e.kind || e.p.label || '写真') + ' — クリックで大きく') + '">' + imgTag(e.p.path, 'c01-samephimg', e.kind || e.p.label || '') +
              '<span>' + esc(e.kind || e.p.label || '') + '</span></button>';
          }).join('') : '<p class="c01-note2">写真がありません</p>') + '</div>';
      }
      html += '</div>';                                             /* .c01-orig-b (同一候補 = .c01-samerow) */
    }
    html += '</section>';
    /* 入力 */
    html += '<section class="c01-form" aria-label="入力">';
    var vItems = [];
    if (q) {
      var st = queueState(q, ov);
      var KC = KIND[q.kind];
      /* カードの中の項目 (値の確認 = 値の違い・手入力 をまとめて 1 つ · ほかは 1 つずつ) */
      var secs = [], seenV = false;
      card.items.forEach(function (y) {
        if (VALUE_KINDS[y.kind]) { if (!seenV) { seenV = true; secs.push({ id: y.queue_id, value: true }); } }
        else secs.push({ id: y.queue_id, value: false, q: y });
      });
      vItems = VALUE_KINDS[q.kind] ? card.items.filter(function (y) { return VALUE_KINDS[y.kind]; }) : [];
      var vOpen = vItems.filter(function (y) { return !queueState(y, ov).done; });
      if (VALUE_KINDS[q.kind]) st = vOpen.length ? { done: false } : queueState(vItems[0], ov);
      html += '<div class="c01-form-h"><span class="k" style="color:' + KC.color + '">' + esc(VALUE_KINDS[q.kind] ? card.kinds.filter(function (k) { return VALUE_KINDS[k]; }).map(kindLabel).join('・') : kindLabel(q.kind)) + '</span><span class="mono big">' +
        esc(q.kind === '写真のCT' ? 'CT 不明の写真 ' + (q.files || []).length + '枚' : (q.kind === '未分類FAX' || q.kind === HOLD) ? ((q.files || [])[0] || {}).name || '' : (q.ct || '（CT 不明）')) + '</span>' +
        (qAiDiff(q, iv) ? '<span class="c01-ibadge" data-info="AI_GROUP_DIFF" title="' + esc(INFO_TEXT.AI_GROUP_DIFF) + '">AI 区分が異なる</span>' : '') +
        '<span class="t2">' + esc(q.kind === '未分類FAX' ? '送信元 ' + (q.issuer || '不明') + (q.received_at ? ' · 受信 ' + md(String(q.received_at).slice(0, 10)) : '') :
          q.kind === HOLD ? (q.packer_guess ? '業者候補 ' + q.packer_guess + ' · ' : '') + (q.received_at ? '受信 ' + md(String(q.received_at).slice(0, 10)) : '') :
            (q.iv_no || '') + ' · ' + (iv ? qPackerPlant(q, iv) : '') + ' · CY ' + (md(q.cy_cut) || '—')) + '</span></div>';
      if (secs.length > 1) {
        html += '<div class="c01-csecs" role="tablist" aria-label="このカードの項目">' + secs.map(function (sc) {
          var y = sc.value ? null : sc.q;
          var on = sc.value ? !!VALUE_KINDS[q.kind] : y.queue_id === q.queue_id;
          var dn = sc.value ? vItems.length && card.items.filter(function (z) { return VALUE_KINDS[z.kind]; }).every(function (z) { return queueState(z, ov).done; }) : queueState(y, ov).done;
          var lab = sc.value ? '値の確認 ' + card.items.filter(function (z) { return VALUE_KINDS[z.kind]; }).length : kindLabel(y.kind);
          return '<button class="c01-chip' + (on ? ' on' : '') + (dn ? ' done' : '') + '" data-sec="' + esc(sc.id) + '">' + (dn ? '✓ ' : '') + esc(lab) + '</button>';
        }).join('') + '</div>';
      }
      html += ACT_MARK + '<div class="c01-form-b">';
      if (st.done) html += '<p class="' + (st.mineLost || (st.by && S.me && st.by !== S.me.email) ? 'c01-lost' : 'c01-okmsg') + '">' + (st.mineLost || (st.by && S.me && st.by !== S.me.email) ? '他の人が先に確認しました' :
        (st.act === 'not_hannyuhyo' || st.act === 'not_ours' ? '「搬入票ではない」にしました' : st.act === 'merge_same' ? '同じコンテナとして合わせました（次の判定で反映）' :
          st.act === 'not_same' ? '別のコンテナにしました' : st.act === 'link_iv' ? 'IV に連結しました（次の判定で反映 · 10 分ほど）' : '完了しました')) + (st.by ? '（' + esc(st.by) + '）' : '') + '</p>';
      html += '<p class="c01-qnote k-' + KC.key + '">' + esc(noteOf(q, vItems.length)) + '</p>';
      var msg = S.qmsg[q.queue_id];
      if (msg) html += '<p class="c01-err" id="q-err">' + esc(msg) + '</p>';
      if (VALUE_KINDS[q.kind]) {
        var editing = {};
        (vOpen.length ? vOpen : vItems).forEach(function (y, yi) {
          var fd = y.field;
          editing[fd] = 1;
          var alts = [];
          Object.keys(y.values || {}).forEach(function (src) { (y.values[src] || []).forEach(function (v) { alts.push([src, v]); }); });
          /* v0.3.18 (R7S #4): シール = 形式に合う候補を先 · 合わない候補は灰色 「形式不一致」 · 合う候補が 1 つだけなら 最初から選んでおく (_auto = 人が触っていない) */
          var sa = y.kind === '値の違い' ? sealAlts(y, alts) : { list: alts.map(function (a, i) { return { a: a, i: i, ok: null }; }), fmt: false, pick: null };
          if (sa.pick && S.qvals[y.queue_id] === undefined && !queueState(y, ov).done) {
            S.qvals[y.queue_id] = { _src: sa.pick.a[0], _auto: 1 };
            S.qvals[y.queue_id][fd] = String(sa.pick.a[1]);
          }
          var vals = S.qvals[y.queue_id] || {};
          var cur = vals[fd] !== undefined ? vals[fd] : '';
          html += '<div class="c01-field' + (queueState(y, ov).done ? ' ro' : '') + '" data-vq="' + esc(y.queue_id) + '"><label for="q-in-' + yi + '"><b>' + FIELD_LABEL[fd] + '</b> <span class="t2">' + esc(kindLabel(y.kind)) + '</span><span class="c01-flex"></span><span class="hint">' + esc(hintOf(fd)) + '</span></label>' +
            '<input id="q-in-' + yi + '" data-vin="' + esc(y.queue_id) + '" class="q-in' + (cur ? '' : ' need') + '" value="' + esc(cur) + '" placeholder="' + (y.kind === '手入力' ? '原本を見て入力' : '選ぶか入力') + '" aria-label="' + FIELD_LABEL[fd] + '">' +
            (alts.length && y.kind === '値の違い' ? '<div class="c01-alts2">' + sa.list.map(function (e) {
              var a = e.a, i = e.i;
              var bad = fd === 'ct' && C01.validate && !C01.validate.ctCheckOk(String(a[1]).replace(/[\s-]/g, '').toUpperCase());
              var ng = e.ok === false;
              return '<button class="c01-alt2' + (String(cur) === String(a[1]) ? ' on' : '') + (ng ? ' c01-fmtng' : e.ok === true ? ' c01-fmtok' : '') + '" data-alt="' + esc(y.queue_id) + '|' + i + '"' +
                (bad ? ' title="チェックデジットが合いません"' : ng ? ' title="船会社のシール番号の形式に合いません"' : '') + '>' + esc(a[0]) + ' <span class="mono">' + esc(a[1]) + '</span>' +
                (bad ? ' <span class="c01-bad">✗</span>' : '') + (ng ? ' <span class="c01-fmttag">形式不一致</span>' : '') + '</button>';
            }).join('') + (sa.pick && String(cur) === String(sa.pick.a[1]) && (S.qvals[y.queue_id] || {})._auto ? '<span class="c01-fmtpick t2" data-fmtpick="1">形式に合う候補が 1 つ — 選んであります（確かめてから確認）</span>' : '') + '</div>' : '') +
            '</div>';
        });
        var row = q.container_id && iv ? iv.rows.filter(function (r) { return r.container_id === q.container_id; })[0] : null;
        if (row) {
          var fst = q.field_source_text || {};      /* v0.2.0: エンジンの項目別出典一致 (field_sources) の文 — 無い時は値だけ */
          html += EDIT_FIELDS.filter(function (x) { return !editing[x]; }).map(function (x) { return editCell(iv, row, x, fst[x], ov); }).join('');
        }
      } else if (q.kind === '写真のCT') {
        var cands = photoCands(q, iv);
        html += '<fieldset class="c01-choices"><legend>どのコンテナの写真ですか</legend>' + cands.map(function (ct, i) {
          var r = iv ? iv.rows.filter(function (x) { return x.ct === ct; })[0] : null;
          return '<button class="c01-choice' + (S.qchoice[q.queue_id] === i ? ' on' : '') + '" data-choice="' + i + '"><span class="mono">' + esc(ct) + '</span><span class="s">' +
            esc(r ? (r.photos ? '写真あり ' + r.photos + '枚（重複の可能性）' : '写真待ち') + (r.seal ? ' · ' + r.seal : '') + (r.work_date ? ' · ' + md(r.work_date) : '') : '') + '</span></button>';
        }).join('') + (cands.length ? '' : '<p class="c01-note2">候補がありません</p>') +
          '<label class="c01-direct">CT 番号を入力して指定<input id="q-ct" placeholder="CT 番号" value="' + esc((S.qvals[q.queue_id] || {}).ct || '') + '"></label></fieldset>';
      } else if (q.kind === '未分類FAX') {
        var ivc = q.candidates || [];
        html += '<fieldset class="c01-choices"><legend>どのインボイスに連結しますか</legend>' + ivc.map(function (c, i) {
          return '<button class="c01-choice' + (S.qchoice[q.queue_id] === i ? ' on' : '') + '" data-choice="' + i + '"><span class="mono">' + esc(c) + '</span></button>';
        }).join('') + '<label class="c01-direct">IV 番号を入力して指定<input id="q-iv" placeholder="IV 番号" value="' + esc((S.qvals[q.queue_id] || {}).iv || '') + '"></label></fieldset>';
      } else if (q.kind === SAME && q.same) {
        var sf = q.same.fax, sp = q.same.photo;
        var dif = function (a, b) { return String(a == null ? '' : a) !== String(b == null ? '' : b); };
        html += '<table class="c01-same"><thead><tr><th></th><th>FAX（搬入票）</th><th>写真</th></tr></thead><tbody>' +
          [['ct', 'CT番号'], ['seal', 'シール番号'], ['n_w', '正味重量'], ['t_w', '風袋重量'], ['bales', 'ベール数'], ['work_date', '作業日']].map(function (fl) {
            var a = sf[fl[0]], b = sp[fl[0]];
            return '<tr' + (a != null && b != null && dif(a, b) ? ' class="d"' : '') + '><th>' + fl[1] + '</th><td class="mono">' + esc(a == null ? '—' : a) + '</td><td class="mono">' + esc(b == null ? '—' : b) + '</td></tr>';
          }).join('') +
          '<tr><th>写真</th><td>0枚</td><td>' + (sp.photos ? '<button class="c01-phbtn" id="same-ph">📷 ' + sp.photos + '枚</button>' : '0枚') + '</td></tr></tbody></table>' +
          '<p class="c01-note2">CT ' + (+q.same.ct_diff) + '字 · シール ' + (+q.same.seal_diff) + '字の違い。合わせると 写真の行の CT を使い、FAX の値は搬入票の出典になります（エンジンが次の判定で値をもう一度確かめます · 確認済にはなりません）。</p>';
      } else if (q.kind === VCHK) {
        /* v0.3.24 (R7X Part A ②): 値の確認 = 理由 (説明 1 行 + ?) · 今の値と出典 (✎ 修正可) · 「確認する」 = このまま確認 */
        var vrow = q.container_id && iv ? iv.rows.filter(function (r) { return r.container_id === q.container_id; })[0] : null;
        html += '<div class="c01-vchk"><p class="c01-reason">' + (vrow ? reasonInfos(vrow, [q]).map(reasonLine).join('<br>') : esc(q.note || '')) + '</p></div>';
        if (vrow) { var fsv = q.field_source_text || {}; html += EDIT_FIELDS.map(function (x) { return editCell(iv, vrow, x, fsv[x], ov); }).join(''); }
      } else if (q.kind === FOREIGN) {
        html += '<div class="c01-hold"><div><span class="k">根拠</span> ' + esc(foreignWhy(q)) + '</div>' +
          '<p class="c01-note2">他の会社の搬入票なら「他社の書類」（この書類の値を使いません · ファイルは消しません · 元に戻せます）。当社の書類なら「当社の書類」（値をもう一度使います）。写真はそのままです。</p></div>';
      } else if (q.kind === HOLD) {
        html += '<div class="c01-hold"><div><span class="k">保留の理由</span> ' + esc(String(q.hold_code || q.note || '').split(',').map(function (c) { return HOLD_TEXT[c] || c; }).join(' · ')) + '</div>' +
          '<div><span class="k">候補の IV</span> <span class="mono">' + esc((q.candidates || []).join(' / ') || '—') + '</span></div>' +
          (linkIvOn() && !st.done ? linkIvForm(q) :
            linkIvOn() ? '' : '<p class="c01-note2">IV への連結はエンジン側の次の版で入ります。今は 原本を確認して、搬入票でなければ「搬入票ではない」、あとで見るなら「スキップ」。</p>') + '</div>';
      }
      if (askOn() && q.kind !== '写真のCT') html += askBlock(q);          /* v0.3.25 (R7Z Part A · #210): 選択肢の一番下 · 普段は閉じている */
      html += '</div>';
      html += '<div class="c01-form-f"><span class="c01-foot">確認した内容は実況表にすぐ反映 · 記録: ' + esc(S.me ? S.me.name : '（担当者を選んでください）') + '</span></div>';
      /* v0.3.7 (R7D Part U-3): 判断ボタン = 右パネルの一番上 · v0.3.11 (R7J Part B): 「搬入票ではない」 = 書類のある全種類 · 完了 = 「元に戻す」 */
      var ready = readyOf(q);
      var canNot = DOC_KINDS[q.kind] && !st.done && (q.kind === '未分類FAX' || (curF && (curF.sha16 || (q.files || []).some(function (x) { return x.sha16; }))));
      var canUndo = st.done && !st.mineLost && (st.act === 'not_hannyuhyo' || st.act === 'not_ours' || st.act === 'merge_same' || st.act === 'not_same' || st.act === 'ours_doc' || st.act === 'link_iv') && st.aid;
      if (q.kind === FOREIGN) canNot = false;              /* v0.3.20: 他社搬入票候補 = 「他社の書類」 · 「当社の書類」 の 2 つだけ */
      var krow = q.container_id && iv ? iv.rows.filter(function (r) { return r.container_id === q.container_id; })[0] : null;
      var canKeep = !st.done && krow && q.kind !== VCHK && q.kind !== FOREIGN && q.kind !== SAME && statusOf(krow, iv, ov).st === '再確認' && !keepPlan(iv, krow, ov).block.length;   /* v0.3.24 (R7X Part A ①) */
      var acts = '<div class="c01-form-a"><button id="q-submit" class="c01-btn-big' + (ready || st.done ? ' ready' : '') + '"' + (ready || st.done ? '' : ' disabled') + '>' +
        (st.done ? '完了しました — 次へ' : q.kind === SAME ? '同じコンテナとして合わせる' : q.kind === FOREIGN ? '他社の書類' : ready ? '確認して次へ' : submitLabel(q)) + '</button>' +
        '<div class="row"><button id="q-skip" class="c01-btn-ghost2">スキップ（あとで）</button>' +
        (q.kind === FOREIGN && !st.done ? '<button id="q-ours" class="c01-btn-ghost2" title="当社の書類です（値をもう一度使います · 元に戻せます）">当社の書類</button>' : '') +
        (q.kind === SAME && !st.done ? '<button id="q-notsame" class="c01-btn-ghost2" title="この 2 行は別のコンテナです（候補を出さなくなります · 元に戻せます）">別のコンテナ</button>' : '') +
        (canNot ? '<button id="q-notours" class="c01-btn-ghost2 danger" title="この書類は搬入票ではありません（ファイルは消しません · 元に戻せます）">搬入票ではない</button>' : '') +
        (canUndo ? '<button id="q-undo" class="c01-btn-ghost2">元に戻す</button>' : '') +
        (canKeep ? '<button id="q-keep" class="c01-btn-ghost2 c01-keep" title="値を変えずに 確認済 にします（記録 · 元に戻す）">このまま確認（OK）</button>' : '') + '</div></div>';
      html = html.replace(ACT_MARK, acts);
    } else {
      html += '<p class="c01-empty">作業はありません</p>';
    }
    html += '</section></div><p class="c01-powered">✦ Powered by LEENAI Automation System</p>';
    setHtml($('c01-main'), html, 5);                               /* v0.3.15 (R7N F): 変わった所だけ (原本 · 入力中の値 · 一覧のスクロールはそのまま) */
    hydrate($('c01-main'));
    var root = $('c01-main');
    if ($('fax-old')) $('fax-old').onchange = function () { S.showOldFax = !S.showOldFax; render(); };
    if ($('qiv-clear')) $('qiv-clear').onclick = function () { S.qiv = null; S.qsel = null; render(); };
    root.querySelectorAll('[data-kind]').forEach(function (el) { el.onclick = function () { S.qkind = el.getAttribute('data-kind'); S.qsel = null; render(); }; });
    root.querySelectorAll('[data-q]').forEach(function (el) { el.onclick = function () { S.qsel = el.getAttribute('data-q'); S.zoom = 100; S.rot = 0; S.rotKey = null; render(); }; });
    root.querySelectorAll('[data-sec]').forEach(function (el) { el.onclick = function () { S.qsel = el.getAttribute('data-sec'); S.zoom = 100; S.rot = 0; S.rotKey = null; render(); }; });
    if (!q) return;
    var zi = $('z-in'), zo = $('z-out'), ro = $('rot');
    if (zi) zi.onclick = function () { S.zoom = Math.min(200, S.zoom + 20); render(); };
    if (zo) zo.onclick = function () { S.zoom = Math.max(60, S.zoom - 20); render(); };
    if (ro) ro.onclick = function () { S.rot = (S.rot + 90) % 360; rotMemSet(S.rotKey, S.rot); render(); };
    var pel = root.querySelector('.c01-orig [data-pdf]');
    if (pel) {
      var prel = pel.getAttribute('data-pkey') || pel.getAttribute('data-pdf');
      var turn = function (d) {
        var n = +pel.getAttribute('data-pages') || 1, cur = S.pdfPage[prel] || +pel.getAttribute('data-page') || 1, nx = Math.min(Math.max(1, cur + d), n);
        if (nx !== cur) { S.pdfPage[prel] = nx; render(); }
      };
      if ($('pdf-prev')) $('pdf-prev').onclick = function () { turn(-1); };
      if ($('pdf-next')) $('pdf-next').onclick = function () { turn(1); };
    }
    if ($('pdf-open')) $('pdf-open').onclick = function () { openTab((qFiles(q)[curFileIdx(q)] || {}).path || ''); };
    root.querySelectorAll('[data-qf]').forEach(function (el) { el.onclick = function () { S.qfile[q.queue_id] = +el.getAttribute('data-qf'); S.zoom = 100; S.rot = 0; S.rotKey = null; render(); }; });
    root.querySelectorAll('[data-gph]').forEach(function (el) {
      el.onclick = function () { openLightboxList('CT 不明の写真', (q.files || []).map(function (pf) { return { path: pf.path, label: pf.name }; }), +el.getAttribute('data-gph')); };
    });
    root.querySelectorAll('[data-vin]').forEach(function (el) {
      var qid = el.getAttribute('data-vin');
      var y = vItems.filter(function (z) { return z.queue_id === qid; })[0];
      el.oninput = function () { var o = {}; o[y.field] = el.value; S.qvals[qid] = Object.assign({}, S.qvals[qid], o); delete S.qvals[qid]._auto; delete S.qmsg[q.queue_id]; refreshSubmit(q); };
    });
    root.querySelectorAll('[data-alt]').forEach(function (el) {
      el.onclick = function () {
        var pr = el.getAttribute('data-alt').split('|');
        var y = vItems.filter(function (z) { return z.queue_id === pr[0]; })[0];
        if (!y) return;
        var alts = [];
        Object.keys(y.values || {}).forEach(function (src) { (y.values[src] || []).forEach(function (v) { alts.push([src, v]); }); });
        var a = alts[+pr[1]];
        var o = {}; o[y.field] = String(a[1]); o._src = a[0];
        S.qvals[y.queue_id] = o; delete S.qmsg[q.queue_id];
        render();
      };
    });
    root.querySelectorAll('[data-choice]').forEach(function (el) { el.onclick = function () { S.qchoice[q.queue_id] = +el.getAttribute('data-choice'); render(); }; });
    var qct = $('q-ct');
    if (qct) qct.oninput = function () { S.qvals[q.queue_id] = { ct: qct.value }; if (qct.value) delete S.qchoice[q.queue_id]; delete S.qmsg[q.queue_id]; refreshSubmit(q); };
    var qiv = $('q-iv');
    if (qiv) qiv.oninput = function () { S.qvals[q.queue_id] = { iv: qiv.value }; if (qiv.value) delete S.qchoice[q.queue_id]; refreshSubmit(q); };
    $('q-skip').onclick = function () { S.qsel = nextQueueId(q); render(); };
    var no = $('q-notours');
    if (no) no.onclick = function () { notHannyuhyo(q, curF); };
    var ud = $('q-undo');
    if (ud) ud.onclick = function () { undoAction(q); };
    var qo = $('q-ours');
    if (qo) qo.onclick = function () { foreignAction(q, 'ours_doc'); };
    var qk = $('q-keep');
    if (qk) qk.onclick = function () { var kr = iv && iv.rows.filter(function (r) { return r.container_id === q.container_id; })[0]; if (kr) keepRow(iv, kr, function () { S.qsel = nextQueueId(q); render(); }); };
    var ns = $('q-notsame');
    if (ns) ns.onclick = function () { sameAction(q, 'not_same'); };
    root.querySelectorAll('[data-sameph]').forEach(function (el) {
      el.onclick = function (ev) { var ivx = ivById(q.iv_no); if (ivx && q.same) openPhotos(ev, rowKey(ivx, q.same.photo), +el.getAttribute('data-sameph')); };
    });
    var sph = $('same-ph');
    if (sph && q.same) sph.onclick = function (ev) { var ivx = ivById(q.iv_no); if (ivx) openPhotos(ev, rowKey(ivx, q.same.photo), 0); };
    $('q-submit').onclick = function () { if (queueState(q, overlay()).done && !(VALUE_KINDS[q.kind] && openValueItems(q).length)) { S.qsel = nextQueueId(q); render(); } else submitQueue(q); };
    if (askOn()) askBind(q);
    if (q.kind === HOLD) bindLinkIv(q);                           /* v0.3.23 (R7W Part D) */
    var erow = q.container_id && iv ? iv.rows.filter(function (r) { return r.container_id === q.container_id; })[0] : null;
    if (erow && (VALUE_KINDS[q.kind] || q.kind === VCHK)) bindEdits(root, iv, erow);
  }
  /* 写真の CT の候補: エンジンの candidates → 無ければ同じ IV の CT がある行 (この行を除く) */
  function photoCands(q, iv) {
    if ((q.candidates || []).length) return q.candidates;
    if (!iv) return [];
    /* 安定キー IV + CT + 業者: この写真の行と同じ業者の行だけ (エンジン apply.container_by と同じ) */
    var me = iv.rows.filter(function (r) { return r.container_id === q.container_id; })[0];
    var pk = me ? (me.packer || iv.packer) : null;
    return iv.rows.filter(function (r) { return r.ct && r.container_id !== q.container_id && (!pk || (r.packer || iv.packer) === pk); }).map(function (r) { return r.ct; });
  }
  /* v0.3.11 (R7J Part A): 同じカードの 値の違い・手入力 で まだ終わっていない項目 */
  function openValueItems(q) {
    var cd = cardOf(S.cards, q.queue_id);
    if (!cd) return VALUE_KINDS[q.kind] ? [q] : [];
    var ov = overlay();
    return cd.items.filter(function (y) { return VALUE_KINDS[y.kind] && !queueState(y, ov).done; });
  }
  function submitLabel(q) {
    if (VALUE_KINDS[q.kind]) return '未入力の項目があります';
    if (q.kind === HOLD) return linkIvOn() ? 'IV と枠を選んでください' : 'IV 連結は準備中';
    return '選んでください';
  }
  function refreshSubmit(q) {
    var b = $('q-submit');
    var r = readyOf(q);
    b.disabled = !r;
    b.className = 'c01-btn-big' + (r ? ' ready' : '');
    b.textContent = r ? '確認して次へ' : submitLabel(q);
  }
  function readyOf(q) {
    var v = S.qvals[q.queue_id] || {};
    if (VALUE_KINDS[q.kind]) {
      var its = openValueItems(q);
      return its.length > 0 && its.every(function (y) { return !!String((S.qvals[y.queue_id] || {})[y.field] || '').trim(); });
    }
    if (q.kind === '写真のCT') return S.qchoice[q.queue_id] !== undefined || !!String(v.ct || '').trim();
    if (q.kind === PHOTO_SET) return !!q.ct;
    if (q.kind === VCHK) { var vr = rowByCid(q.container_id); return !!(vr && vr.r && (vr.r.ct || q.ct)); }
    if (q.kind === '未分類FAX') return S.qchoice[q.queue_id] !== undefined || !!String(v.iv || '').trim();
    if (q.kind === SAME) return !!q.same;
    if (q.kind === FOREIGN) return (q.files || []).some(function (f) { return f.sha16; });
    if (q.kind === HOLD) return linkIvOn() && !!linkIvOf(q) && !!v.slot && (q.files || []).some(function (f) { return f.sha16; });
    return false;
  }
  function noteOf(q, nv) {
    if (VALUE_KINDS[q.kind] && nv > 1) return 'このコンテナの ' + nv + ' 項目をまとめて確認します。原本を見て、正しい値を選ぶか入力してください。';
    if (q.kind === '値の違い') return FIELD_LABEL[q.field] + ' が出典によって違います。原本を見て、正しい方を選ぶか入力してください。';
    if (q.kind === '手入力') return FIELD_LABEL[q.field] + ' が読めませんでした。原本を見て入力してください。';
    if (q.kind === '写真のCT') return '写真から CT 番号が読めませんでした。写真を見て、どのコンテナか選んでください。';
    if (q.kind === PHOTO_SET) return q.reason_text || '通関用写真が不足しています';     /* エンジンの既存理由文 (reason_text) をそのまま */
    if (q.kind === VCHK) return '値に確かめ切れていない所があります。原本と写真を見て、合っていれば「確認する」（値はそのまま）· 違っていれば ✎ 修正。';
    if (q.kind === HOLD) return '受信したメールの書類ですが、どの業者・インボイスか判定できず保留になっています。';
    if (q.kind === SAME) return '写真のない FAX の行と、搬入票のない写真の行が 同じコンテナかもしれません（CT・シールの読み違い）。原本と写真を見て決めてください。';
    return 'どのインボイスの搬入票か判定できませんでした。';
  }
  /* v0.3.18 (R7S #4): シール候補の 船会社の形式 — エンジンが項目に付けた時だけ (無い時は これまでどおり)。
     ① seal_fmt_ok = { "候補の値": true | false } (エンジン Rules.seal_ok の結果そのまま · あればこれを使う)
     ② seal_format = { regex, prefixes: [..] または "A;B", digits: 8 または "6~7", prefix_required } (carrier マスターの列 · エンジン seal_ok と同じ規則で TOOL が判定)
     戻り = 関数 (値 → true 合う · false 合わない · null 分からない) · 形式の情報が無い = null */
  function sealFmtOf(y) {
    if (!y || y.field !== 'seal') return null;
    var mp = y.seal_fmt_ok && typeof y.seal_fmt_ok === 'object' ? y.seal_fmt_ok : null;
    var sf = y.seal_format && typeof y.seal_format === 'object' ? y.seal_format : null;
    if (!mp && !sf) return null;
    return function (v) {
      var raw = String(v == null ? '' : v);
      if (mp && Object.prototype.hasOwnProperty.call(mp, raw)) return mp[raw] === true ? true : mp[raw] === false ? false : null;
      if (!sf) return null;
      var t = raw.toUpperCase().replace(/[\s\-]/g, '');
      if (!t) return null;
      if (sf.regex) {
        try { return new RegExp('^(?:' + sf.regex + ')').test(t); } catch (e) { return null; }
      }
      var pre = (Array.isArray(sf.prefixes) ? sf.prefixes : String(sf.prefixes || '').split(/[;\/]/))
        .map(function (x) { return String(x || '').replace(/-/g, '').toUpperCase(); }).filter(Boolean);
      var dig = String(sf.digits == null ? '' : sf.digits);
      if (!pre.length && !dig) return null;
      var onlyDigits = /^\d+$/.test(t);
      if (pre.length && !pre.some(function (x) { return t.indexOf(x) === 0; }) && !(onlyDigits && sf.prefix_required === false)) return false;
      var nd = t.replace(/\D/g, '').length;
      if (/^\d+$/.test(dig) && nd !== +dig) return false;
      var m = /^(\d+)~(\d+)$/.exec(dig);
      if (m && !(+m[1] <= nd && nd <= +m[2])) return false;
      return true;
    };
  }
  /* 候補の並び (形式に合うものを先 · 同じなら元の順) と 印 — 元の番号 (i) はそのまま (クリックの data-alt · data-i) */
  function sealAlts(y, alts) {
    var fm = sealFmtOf(y);
    var list = alts.map(function (a, i) { return { a: a, i: i, ok: fm ? fm(a[1]) : null }; });
    if (!fm) return { list: list, fmt: false, pick: null };
    list.sort(function (p, q2) { var sp = p.ok === true ? 0 : p.ok === false ? 2 : 1, sq = q2.ok === true ? 0 : q2.ok === false ? 2 : 1; return sp - sq || p.i - q2.i; });
    var okVals = {};
    list.forEach(function (e) { if (e.ok === true) okVals[String(e.a[1])] = okVals[String(e.a[1])] || e; });
    var ks = Object.keys(okVals);
    return { list: list, fmt: true, pick: ks.length === 1 ? okVals[ks[0]] : null };
  }
  function hintOf(fd) {
    return fd === 'ct' ? '英字4 + 数字7 · チェックデジット' : fd === 'seal' ? '英数字（空白なし）' : fd === 'work_date' ? 'YYYY-MM-DD' : '正の整数';
  }
  /* v0.3.11: 次 = 同じカードのまだの項目 → 一覧の次のカード (終わっていないもの) */
  function nextQueueId(q) {
    var ov = overlay();
    var cards = queueCards(ov).cards;
    var cd = cardOf(cards, q.queue_id);
    if (cd) {
      var rest = cd.items.filter(function (y) { return y.queue_id !== q.queue_id && !queueState(y, ov).done && !(VALUE_KINDS[q.kind] && VALUE_KINDS[y.kind]); });
      if (rest.length) return rest[0].queue_id;
    }
    var i = cards.indexOf(cd);
    var after = cards.slice(i + 1).concat(cards.slice(0, Math.max(i, 0)));
    var n = after.filter(function (c) { return !c.done && c !== cd && (!S.qiv || cardIv(c).indexOf(S.qiv) >= 0); })[0];
    return n ? (n.open[0] || n.items[0]).queue_id : q.queue_id;
  }
  /* v0.3.11 (R7J Part B): 「搬入票ではない」 — ファイルは消さない · エンジンが その書類を出典から外す · 元に戻せる */
  /* v0.3.20 (R7U Part D): 他社搬入票候補 — 「他社の書類」 = not_hannyuhyo (その書類だけ使わない) · 「当社の書類」 = ours_doc (値をもう一度使う · 学習の記録) */
  function foreignAction(q, act) {
    if (!S.me) { S.qmsg[q.queue_id] = '担当者を選んでください（右上）'; render(); return; }
    var hs = (q.files || []).filter(function (x) { return x.sha16; }).map(function (x) { return x.sha16; });
    if (!hs.length) return;
    var a = mkAction(act, { iv: q.iv_no || null, ct: q.ct || null, field: null, value: { sha16: hs.filter(function (h, i) { return hs.indexOf(h) === i; }) }, source: null, queue_id: q.queue_id });
    writeAction(a).then(function () {
      S.qsel = nextQueueId(q); S.zoom = 100; S.rot = 0; S.rotKey = null; render();
      toast(act === 'ours_doc' ? '「当社の書類」にしました（完了 から 元に戻せます）' : '「他社の書類」にしました — この書類の値を使いません（完了 から 元に戻せます）', 'success');
    });
  }
  function notHannyuhyo(q, f) {
    if (!S.me) { S.qmsg[q.queue_id] = '担当者を選んでください（右上）'; render(); return; }
    if (!window.confirm('この書類を「搬入票ではない」にしますか？\n（ファイルは消しません · 同じファイルは確認リストに出なくなります · 完了 から 元に戻せます）')) return;
    var a;
    if (q.kind === '未分類FAX') a = mkAction('not_ours', { iv: null, ct: null, field: null, value: null, source: null, queue_id: q.queue_id });
    else {
      var hs = f && f.sha16 ? [f.sha16] : (q.files || []).filter(function (x) { return x.sha16; }).map(function (x) { return x.sha16; });
      if (!hs.length) return;
      a = mkAction('not_hannyuhyo', { iv: q.iv_no || null, ct: q.ct || null, field: null, value: { sha16: hs.filter(function (h, i) { return hs.indexOf(h) === i; }) }, source: null, queue_id: q.queue_id });
    }
    writeAction(a).then(function () { S.qsel = nextQueueId(q); S.zoom = 100; S.rot = 0; S.rotKey = null; render(); toast('「搬入票ではない」にしました（完了 から 元に戻せます）', 'success'); });
  }
  /* v0.3.12 (R7K Part C): 「同じコンテナとして合わせる」 (merge_same) · 「別のコンテナ」 (not_same) — 2 行の container_id を記録 · エンジンが次の判定で合わせる */
  function sameAction(q, act) {
    if (!S.me) { S.qmsg[q.queue_id] = '担当者を選んでください（右上）'; render(); return; }
    if (!q.same) return;
    if (act === 'merge_same' && !window.confirm('この 2 行を同じコンテナとして合わせますか？\n（写真の行の CT を使います · 完了 から 元に戻せます）')) return;
    var a = mkAction(act, { iv: q.iv_no, ct: q.same.photo.ct || null, field: null,
      value: { pair_id: q.queue_id, fax_container_id: q.same.fax.container_id, photo_container_id: q.same.photo.container_id }, source: null, queue_id: q.queue_id });
    writeAction(a).then(function () { S.qsel = nextQueueId(q); render(); toast(act === 'merge_same' ? '合わせました（次の判定で反映 · 完了 から 元に戻せます）' : '別のコンテナにしました', 'success'); });
  }
  function undoAction(q) {
    if (!S.me) { S.qmsg[q.queue_id] = '担当者を選んでください（右上）'; render(); return; }
    var st = queueState(q, overlay());
    if (!st.aid) return;
    var a = mkAction('undo', { iv: q.iv_no || null, ct: q.ct || null, field: null, value: { action_id: st.aid }, source: null, queue_id: null });
    writeAction(a).then(function () { render(); toast('元に戻しました', 'success'); });
  }
  /* ── v0.3.23 (R7W Part D · 決定 #206): 業者・IV 未定 = 「IVに連結」 — 担当者が BKG / IV を入れ (候補 · 前に連結した IV が上) → そのブッキングの枠を選ぶ (必須)
     安全: 無い BKG / IV = 選べない · 書類の業者 ≠ 枠の業者 = 確認窓 · もう行がある枠 = 確認窓 · 元に戻す · 人が選んだ枠 = エンジンが固定 (s2_human_link_iv) ── */
  function linkIvOn() { return !!(C01.RULES || {}).linkIv; }
  function ivByAny(t) {
    t = String(t || '').trim().toUpperCase().replace(/\s/g, '');
    if (!t) return null;
    return ((S.jik && S.jik.ivs) || []).filter(function (iv) {
      return String(iv.iv_no || '').toUpperCase() === t || String(iv.bkg_no || '').toUpperCase().replace(/\s/g, '') === t;
    })[0] || null;
  }
  function linkIvOf(q) { return ivByAny((S.qvals[q.queue_id] || {}).iv); }
  function linkIvRecs(q) {
    /* 前に連結した IV (同じファイル名 · 同じ業者候補) — 学習の記録 (_actions link_iv) */
    var names = (q.files || []).map(function (f) { return f.name; }).filter(Boolean);
    var out = [];
    allActions().forEach(function (a) {
      if (a.action !== 'link_iv' || !a.iv || out.indexOf(a.iv) >= 0) return;
      var v = a.value || {};
      if ((v.names || []).some(function (n) { return names.indexOf(n) >= 0; }) || (q.packer_guess && v.packer_guess === q.packer_guess)) out.push(a.iv);
    });
    return out;
  }
  function slotRows(iv) {
    var m = {};
    (iv.rows || []).forEach(function (r) { if (r.slot_guid) m[r.slot_guid] = r; });
    return m;
  }
  function linkIvForm(q) {
    var v = S.qvals[q.queue_id] || {};
    var recs = linkIvRecs(q), cands = (q.candidates || []).filter(function (x) { return recs.indexOf(x) < 0; });
    var live = ((S.jik && S.jik.ivs) || []).filter(function (iv) { return ivLive(iv); });
    var iv = linkIvOf(q);
    var h = '<div class="c01-linkiv"><div class="k">IVに連結</div>' +
      '<label class="c01-direct">BKG または IV<input id="link-iv" type="text" list="link-iv-list" placeholder="例: BKG 番号 / IV 番号" value="' + esc(v.iv || '') + '" autocomplete="off"></label>' +
      '<datalist id="link-iv-list">' + live.map(function (x) { return '<option value="' + esc(x.iv_no) + '">' + esc((x.bkg_no || '') + ' · ' + (x.packer || '')) + '</option>'; }).join('') + '</datalist>' +
      (recs.length || cands.length ? '<div class="c01-linkrec">' + recs.map(function (x) { return '<button class="c01-chip on" data-linkiv="' + esc(x) + '" title="前に同じファイル名 · 業者で連結した IV">★ ' + esc(x) + '</button>'; }).join('') +
        cands.map(function (x) { return '<button class="c01-chip" data-linkiv="' + esc(x) + '" title="エンジンの候補">' + esc(x) + '</button>'; }).join('') + '</div>' : '');
    if (v.iv && !iv) h += '<p class="c01-err">この BKG / IV は進行中のブッキングにありません（選べません）</p>';
    if (iv) {
      var used = slotRows(iv), seq = slotSeq(iv);
      var sl = (iv.slots || []).slice().sort(function (a, b) { return (seq[a.slot_guid] || 0) - (seq[b.slot_guid] || 0); });
      h += '<div class="c01-linkslots"><div class="t2">' + esc(iv.iv_no + ' · BKG ' + (iv.bkg_no || '') + ' · 枠 ' + sl.length) + ' — 枠を選んでください（必須）</div>' +
        sl.map(function (s, i) {
          var r = used[s.slot_guid];
          var on = v.slot === s.slot_guid;
          return '<label class="c01-slotopt' + (r ? ' used' : ' free') + (on ? ' on' : '') + '"><input type="radio" name="link-slot" value="' + esc(s.slot_guid) + '"' + (on ? ' checked' : '') + '>' +
            '<span>' + (i + 1) + '</span><span>' + esc(s.packer || '') + ' ' + esc(s.plant || '') + '</span><span class="t2">' + esc((s.item || '') + ' · ' + md(s.work_date || '')) + '</span>' +
            '<span class="' + (r ? 'c01-over' : 'c01-free') + '">' + (r ? '使用中 ' + esc(r.ct || '（CT 不明）') : '空き') + '</span></label>';
        }).join('') + '</div>';
      var sel = sl.filter(function (s) { return s.slot_guid === v.slot; })[0];
      if (sel && q.packer_guess && sel.packer && q.packer_guess.split('・').indexOf(sel.packer) < 0) h += '<p class="c01-warn2">書類の業者（' + esc(q.packer_guess) + '）と枠の業者（' + esc(sel.packer) + '）が違います</p>';
      if (sel && used[sel.slot_guid]) h += '<p class="c01-warn2">この枠にはもう行があります（' + esc(used[sel.slot_guid].ct || 'CT 不明') + '）</p>';
    }
    return h + '<p class="c01-note2">連結すると この書類は選んだ IV · 枠のものとして次の判定（10 分ほど）で読みます。元に戻せます。</p></div>';
  }
  function bindLinkIv(q) {
    var inp = $('link-iv');
    if (!inp) return;
    var setIv = function (t) {
      var v = S.qvals[q.queue_id] || (S.qvals[q.queue_id] = {});
      if (v.iv === t) return;                                      /* Enter → blur の change で 2 回描かない */
      v.iv = t; v.slot = null;
      setTimeout(render, 0);
    };
    inp.onchange = function () { setIv(inp.value); };
    inp.onkeydown = function (e) { if (e.key === 'Enter') setIv(inp.value); };
    document.querySelectorAll('[data-linkiv]').forEach(function (b) { b.onclick = function () { setIv(b.getAttribute('data-linkiv')); }; });
    document.querySelectorAll('input[name="link-slot"]').forEach(function (r) {
      r.onchange = function () { (S.qvals[q.queue_id] || (S.qvals[q.queue_id] = {})).slot = r.value; render(); };
    });
  }
  function linkIvAction(q) {
    var v = S.qvals[q.queue_id] || {};
    var iv = linkIvOf(q);
    if (!iv) { S.qmsg[q.queue_id] = 'この BKG / IV は進行中のブッキングにありません'; render(); return; }
    var sl = (iv.slots || []).filter(function (s) { return s.slot_guid === v.slot; })[0];
    if (!sl) { S.qmsg[q.queue_id] = '枠を選んでください'; render(); return; }
    var warn = [];
    if (q.packer_guess && sl.packer && q.packer_guess.split('・').indexOf(sl.packer) < 0) {
      if (!window.confirm('書類の業者（' + q.packer_guess + '）と枠の業者（' + sl.packer + '）が違います。この枠に連結しますか？')) return;
      warn.push('packer');
    }
    var used = slotRows(iv)[sl.slot_guid];
    if (used) {
      if (!window.confirm('この枠にはもう行があります（' + (used.ct || 'CT 不明') + '）。この枠に連結しますか？')) return;
      warn.push('slot_used');
    }
    var hs = (q.files || []).map(function (f) { return f.sha16; }).filter(function (h, i, a) { return h && a.indexOf(h) === i; });
    var a = mkAction('link_iv', { iv: iv.iv_no, ct: null, field: null, source: null, queue_id: q.queue_id,
      value: { sha16: hs, slot_guid: sl.slot_guid, bkg: iv.bkg_no || null, names: (q.files || []).map(function (f) { return f.name; }).filter(Boolean),
        packer_guess: q.packer_guess || null, warn: warn } });
    writeAction(a).then(function () { toast('IV に連結しました（次の判定で反映）', 'success'); S.qsel = nextQueueId(q); render(); });
  }
  function submitQueue(q, special) {
    if (!S.me) { S.qmsg[q.queue_id] = '担当者を選んでください（右上）'; render(); return; }
    var acts = [];
    if (special === 'not_ours') { notHannyuhyo(q, null); return; }
    if (q.kind === SAME) { sameAction(q, 'merge_same'); return; }
    if (q.kind === FOREIGN) { foreignAction(q, 'not_hannyuhyo'); return; }
    if (q.kind === HOLD) { if (linkIvOn()) linkIvAction(q); return; }
    if (q.kind === VCHK) {                                       /* v0.3.24 (R7X Part A ②): 値の確認 = このまま確認 */
      var vx = rowByCid(q.container_id);
      if (vx && vx.r) keepRow(vx.iv, vx.r, function () { S.qsel = nextQueueId(q); S.zoom = 100; S.rot = 0; S.rotKey = null; render(); });
      return;
    }
    if (VALUE_KINDS[q.kind]) {
      var its = openValueItems(q);
      for (var k = 0; k < its.length; k++) {
        var y = its[k];
        var vals = S.qvals[y.queue_id] || {};
        var v = C01.validate.field(y.field, vals[y.field]);
        if (!v.ok) { S.qmsg[q.queue_id] = FIELD_LABEL[y.field] + ': ' + v.error; render(); return; }
        if (v.warn && !window.confirm(v.warn)) { S.qmsg[q.queue_id] = v.warn; render(); return; }   /* #109 ③ 確認窓 (文言そのまま) → OK なら保存 */
        if (y.field === 'ct' && !ctDupWarn(y.iv_no, v.value, y.container_id)) { S.qmsg[q.queue_id] = 'このCTは同じ IV の別の行にあります'; render(); return; }
        var src = y.kind === '手入力' ? '手入力' : (vals._src && String(vals[y.field]) === String(((y.values || {})[vals._src] || []).filter(function (x) { return String(x) === String(vals[y.field]); })[0]) ? vals._src : '手入力');
        acts.push(mkAction(y.kind === '手入力' ? 'manual_input' : 'confirm_value', { iv: y.iv_no, ct: y.ct, field: y.field, value: v.value, source: src, queue_id: y.queue_id, override: v.override }));
      }
    } else if (q.kind === '写真のCT') {
      var typedCt = String((S.qvals[q.queue_id] || {}).ct || '').trim();
      var ct = typedCt ? null : photoCands(q, ((S.jik && S.jik.ivs) || []).filter(function (x) { return x.iv_no === q.iv_no; })[0])[S.qchoice[q.queue_id]];
      if (typedCt) {
        var vc = C01.validate.field('ct', typedCt);
        if (!vc.ok) { S.qmsg[q.queue_id] = vc.error; render(); return; }
        if (vc.warn && !window.confirm(vc.warn)) { S.qmsg[q.queue_id] = vc.warn; render(); return; }
        ct = vc.value;
      }
      acts.push(mkAction('assign_photos', { iv: q.iv_no, ct: ct, field: null, value: { paths: (q.files || []).map(function (f) { return f.path; }) }, source: null, queue_id: q.queue_id }));
    } else if (q.kind === PHOTO_SET) {
      if (!q.ct) return;
      acts.push(photoSetAction(q, q.ct));
    } else if (q.kind === '未分類FAX') {
      var typed = String((S.qvals[q.queue_id] || {}).iv || '').trim().toUpperCase();
      var ivn = typed || (q.candidates || [])[S.qchoice[q.queue_id]];
      acts.push(mkAction('link_fax', { iv: ivn, ct: null, field: null, value: null, source: null, queue_id: q.queue_id }));
    }
    if (!acts.length) return;
    var chain = Promise.resolve();
    acts.forEach(function (a) { chain = chain.then(function () { return writeAction(a); }); });
    chain.then(function () {
      var lost = queueState(q, overlay()).mineLost;
      if (lost) { toast('他の人が先に確認しました', 'warn'); render(); return; }
      S.qsel = nextQueueId(q); S.zoom = 100; S.rot = 0; S.rotKey = null; render();
    });
  }

  /* ── v0.3.25 (R7Z Part A · 決定 #207 · #209 · #210 · #211): その他（AIに相談）
     質問 = {base}/ask/{日付}/{ask_id}.json (カード: IV · CT · 行 · 項目 · 今開いている原本と頁) → RPA PC のエンジンが答える ({base}/ask_reply/) ·
     会話はカード単位 (他の担当者も見える) · 答えのボタン = この画面の今のボタン (押すのは担当者 · 記録 · 元に戻す は今のまま) ·
     Compass入力 · 催促 送信 = 案内の文だけ · 業者 · 別名 · 連絡先の登録 = 「管理者の承認依頼」 だけ · 削除 · 原本の移動 = できない */
  var ASK_QUICK = ['どの値が正しい？', 'この書類は違う', '写真が見えない'];
  var ASK_ACT = { pick_value: 1, fix_value: 1, merge_same: 1, not_same: 1, link_iv: 1, not_hannyuhyo: 1, not_ours: 1, reload_view: 1 };
  function askOn() { return !!(C01.ASK && C01.ASK.enabled && S.src && typeof S.src.listAsks === 'function'); }
  function askKey(q) { return (q.iv_no || '') + '|' + cardKey(q); }
  function askId() { return 'k' + Date.now().toString(36) + Math.random().toString(36).slice(2, 10); }
  function loadAsks(days) {
    return S.src.listAsks(days).then(function (xs) {
      var mine = (S.asks || []).filter(function (x) { return x.local && !xs.some(function (y) { return y.ask && y.ask.ask_id === x.ask.ask_id; }); });
      var sig = function (l) { return (l || []).map(function (x) { return x.ask.ask_id + (x.reply ? '+' : '-'); }).sort().join(','); };
      var changed = sig(S.asks) !== sig(xs.concat(mine));
      S.asks = xs.concat(mine);
      askSchedule();
      if (changed && S.view === 'input' && !busy()) render({ auto: true });     /* 答えが来た · 他の人の質問 = 描き直す (入力中は後で) */
    }).catch(function () { /* 読めない時は次回 */ });
  }
  function askPending() { return (S.asks || []).some(function (x) { return !x.reply; }); }
  function askSchedule() {
    if (S.askTimer || !askPending()) return;
    S.askTimer = setTimeout(function () {
      S.askTimer = null;
      var t = jstNow().slice(0, 10);
      loadAsks([addDays(t, -1), t]).then(function () { render(); });
    }, (C01.ASK && C01.ASK.pollMs) || 10000);
  }
  function askThread(q) {
    var k = askKey(q);
    return (S.asks || []).filter(function (x) { return x.ask && x.ask.card && x.ask.card.key === k; })
      .sort(function (a, b) { return String(a.ask.at) < String(b.ask.at) ? -1 : 1; });
  }
  function askBlock(q) {
    var th = askThread(q), k = askKey(q);
    var open = !!S.askOpen[k];
    var h = '<details class="c01-ask" id="ask-box"' + (open ? ' open' : '') + '><summary>その他（AIに相談）' +
      (C01.ASK.trial ? ' <span class="c01-trialtag">試験表示</span>' : '') + (th.length ? ' <span class="t2">' + th.length + '件</span>' : '') + '</summary>';
    h += '<div class="c01-ask-log">' + th.map(function (x) {
      var a = x.ask, r = x.reply;
      var who = esc(a.by_name || a.by || '') + ' · ' + esc(String(a.at || '').slice(11, 16));
      var body = '<div class="c01-ask-q"><span class="t2">' + who + '</span> ' + esc(a.question) + '</div>';
      if (!r) return body + '<div class="c01-ask-a wait">回答待ち…</div>';
      var sug = (r.suggestions || []).filter(function (s) { return ASK_ACT[s.action]; });
      return body + '<div class="c01-ask-a">' + esc(r.answer || '') +
        (r.approval_request ? '<div class="c01-ask-apr">管理者の承認依頼として記録しました: ' + esc(r.approval_request) + '</div>' : '') +
        (sug.length ? '<div class="c01-ask-sug">' + sug.map(function (s, i) {
          var ok = askCan(q, s);
          return '<button class="c01-btn-ghost2" data-asksug="' + esc(a.ask_id) + '|' + i + '"' + (ok ? '' : ' disabled title="この画面では使えません"') + '>' +
            esc(s.label || s.action) + (s.value ? ' <span class="mono">' + esc(s.value) + '</span>' : '') + (s.iv ? ' <span class="mono">' + esc(s.iv) + '</span>' : '') + '</button>';
        }).join('') + '<span class="t2">押すと この画面の今のボタンと同じ (記録 · 元に戻す)</span></div>' : '') + '</div>';
    }).join('') + '</div>';
    h += '<div class="c01-ask-quick">' + ASK_QUICK.map(function (t, i) { return '<button class="c01-chip" data-askq="' + i + '">' + esc(t) + '</button>'; }).join('') + '</div>';
    h += '<div class="c01-ask-in"><input id="ask-in" placeholder="質問を入力 (日本語 · 한국어)" value="' + esc(S.askDraft[k] || '') + '" aria-label="AI への質問">' +
      '<button id="ask-send" class="c01-btn-ghost2">送信</button></div></details>';
    return h;
  }
  /* 答えのボタンが この画面で使えるか (今の画面にそのボタン · 欄があるか) */
  function askCan(q, s) {
    if (s.action === 'pick_value' || s.action === 'fix_value') return VALUE_KINDS[q.kind] && openValueItems(q).some(function (y) { return y.field === s.field; });
    if (s.action === 'merge_same') return q.kind === SAME;
    if (s.action === 'not_same') return !!$('q-notsame');
    if (s.action === 'not_hannyuhyo') return !!$('q-notours');
    if (s.action === 'not_ours') return q.kind === FOREIGN || !!$('q-notours');
    if (s.action === 'link_iv') return !!$('q-iv') || q.kind === HOLD;
    return s.action === 'reload_view';
  }
  function askApply(q, s) {
    if (!askCan(q, s)) { toast('この画面では使えません', 'warn'); return; }
    if (s.action === 'pick_value' || s.action === 'fix_value') {
      var y = openValueItems(q).filter(function (z) { return z.field === s.field; })[0];
      var src = null;
      if (s.action === 'pick_value') Object.keys(y.values || {}).forEach(function (k) { (y.values[k] || []).forEach(function (v) { if (String(v) === String(s.value)) src = src || k; }); });
      var o = {}; o[y.field] = String(s.value); if (src) o._src = src;
      S.qvals[y.queue_id] = o; delete S.qmsg[q.queue_id];
      render(); toast('値を入れました — 原本で確かめてから「確認して次へ」', 'success'); return;
    }
    if (s.action === 'merge_same') { $('q-submit').click(); return; }
    if (s.action === 'not_same') { $('q-notsame').click(); return; }
    if (s.action === 'not_hannyuhyo') { $('q-notours').click(); return; }
    if (s.action === 'not_ours') { (q.kind === FOREIGN ? $('q-submit') : $('q-notours')).click(); return; }
    if (s.action === 'link_iv') {
      var el = $('q-iv');
      if (el) { el.value = s.iv; el.dispatchEvent(new Event('input')); toast('IV を入れました — 確かめてから連結', 'success'); }
      return;
    }
    if (s.action === 'reload_view') { S.photoSig = {}; loadAll().then(function () { render(); toast('画面を作り直しました', 'success'); }); }
  }
  function askSend(q, text) {
    text = String(text || '').trim();
    if (!text) return;
    if (!S.me || !S.me.email) { toast('担当者を選んでください', 'warn'); return; }
    var f = (q.kind === '写真のCT' || q.kind === PHOTO_SET) ? null : qFiles(q)[curFileIdx(q)];
    var a = { schema_version: 1, ask_id: askId(), at: jstNow(), by: S.me.email, by_name: S.me.name || '', lang: /[가-힣]/.test(text) ? 'ko' : 'ja', question: text.slice(0, 1000),
      card: { key: askKey(q), queue_id: q.queue_id, iv: q.iv_no || null, ct: q.ct || null, container_id: q.container_id || null, kind: q.kind, field: q.field || null,
        open: f && f.path ? { file: f.path, page: S.pdfPage[f.path] || 1 } : {} } };
    S.asks.push({ ask: a, reply: null, local: true });
    S.askDraft[askKey(q)] = '';
    S.askOpen[askKey(q)] = true;
    render();
    S.src.writeAsk(a).then(function () { askSchedule(); }).catch(function (e) {
      S.asks = S.asks.filter(function (x) { return x.ask.ask_id !== a.ask_id; });
      toast('送信できませんでした: ' + e.message, 'error'); render();
    });
  }
  function askBind(q) {
    var box = $('ask-box');
    if (!box) return;
    var k = askKey(q);
    box.addEventListener('toggle', function () { S.askOpen[k] = box.open; });
    var inp = $('ask-in');
    if (inp) {
      inp.oninput = function () { S.askDraft[k] = inp.value; };
      inp.onkeydown = function (ev) { if (ev.key === 'Enter' && !ev.isComposing) { ev.preventDefault(); askSend(q, inp.value); } };
    }
    if ($('ask-send')) $('ask-send').onclick = function () { askSend(q, inp && inp.value); };
    box.querySelectorAll('[data-askq]').forEach(function (el) { el.onclick = function () { askSend(q, ASK_QUICK[+el.getAttribute('data-askq')]); }; });
    box.querySelectorAll('[data-asksug]').forEach(function (el) {
      el.onclick = function () {
        var pr = el.getAttribute('data-asksug').split('|');
        var x = (S.asks || []).filter(function (y) { return y.ask.ask_id === pr[0]; })[0];
        var s = x && x.reply && (x.reply.suggestions || []).filter(function (z) { return ASK_ACT[z.action]; })[+pr[1]];
        if (s) askApply(q, s);
      };
    });
  }

  /* ── _actions 書き込み (設計 §5 の形) ── */
  function mkAction(action, f) {
    var a = { schema_version: 1, action_id: actionId(), action: action, iv: f.iv == null ? null : f.iv, ct: f.ct == null ? null : f.ct,
      field: f.field == null ? null : f.field, value: f.value === undefined ? null : f.value, source: f.source == null ? null : f.source,
      by: S.me.email, at: jstNow(), queue_id: f.queue_id || null };
    if (f.override) a.override = [f.override];                 /* #109 ③ CT_CHECKDIGIT_OVERRIDE */
    if (f.mode) a.mode = f.mode;                               /* v0.3.23 (R7W Part A): 'edit' = 人の値があっても新しい値 (エンジン actions_value_edit) */
    return a;
  }
  function writeAction(a) {
    S.mine.push({ action: a, pending: true });          /* 本人の画面はすぐ反映 (決定 #100) */
    render();
    return S.src.writeAction(a).then(function () { return a; }).catch(function (e) {
      S.mine = S.mine.filter(function (x) { return x.action.action_id !== a.action_id; });
      toast('保存できませんでした: ' + e.message, 'error');
      render();
      throw e;
    });
  }

  /* ── 読み込み · 30 秒ごとの更新 ── */
  /* v0.3.24 (R7X Part E · 형님 17:4x): 写真の一覧 — 読めなかった時は 前の一覧をそのまま (前は空にして 「0枚」 が一瞬出た) · 失敗コードはコンソール ·
     エンジンの指紋 (iv.photos_sig) が前と同じ IV は読まない (30 秒ごとの GET ≈ 0) */
  S.photoSig = {}; S.photoStat = { get: 0, fail: 0, codes: {} };
  function loadPhotos(iv, sig) {
    S.photoStat.get++;
    return S.src.getJson('photos/' + iv + '.json').then(function (p) { S.photos[iv] = p; if (sig !== undefined) S.photoSig[iv] = sig; }).catch(function (e) {
      S.photoStat.fail++;
      var code = String((e && (e.status || e.message)) || 'error');
      S.photoStat.codes[code] = (S.photoStat.codes[code] || 0) + 1;
      if (window.console && console.warn) console.warn('[C01] 写真一覧を読めませんでした (前の一覧のまま):', iv, code);
      if (!S.photos[iv]) S.photos[iv] = { containers: [], unassigned: [], docs: [], _failed: true };
    });
  }
  function loadAll() {
    return Promise.all([S.src.getJson('jikkyou.json'), S.src.getJson('queue.json').catch(function () { return { items: [] }; }),
      S.src.getJson('remind.json').catch(function () { return null; }), S.src.getJson('meta.json').catch(function () { return null; })]).then(function (r) {
      S.jik = r[0]; S.queue = r[1]; S.remind = r[2]; S.meta = r[3]; S.lastLoad = new Date();
      var seen = {};
      return Promise.all(((S.jik && S.jik.ivs) || []).map(function (iv) {
        if (seen[iv.iv_no]) return null;
        seen[iv.iv_no] = 1;
        var sig = iv.photos_sig;
        if (sig && S.photos[iv.iv_no] && !S.photos[iv.iv_no]._failed && S.photoSig[iv.iv_no] === sig) return null;   /* 指紋が同じ = 読まない */
        return loadPhotos(iv.iv_no, sig || undefined);
      }));
    });
  }
  C01.photoStat = function () { return S.photoStat; };
  function poll() {
    var t = (S.info && S.info.today) || new Date().toISOString().slice(0, 10);
    var days = [addDays(t, -1), t];
    var nowDay = jstNow().slice(0, 10);
    if (days.indexOf(nowDay) < 0) days.push(nowDay);
    if (askOn()) loadAsks(days);                       /* v0.3.25 (R7Z Part A): AI 相談 (失敗しても他は続ける) */
    return S.src.listActions(days).then(function (items) {
      S.actions = items;
      var ids = {};
      items.forEach(function (x) { ids[x.action.action_id] = 1; });
      S.mine = S.mine.filter(function (x) { return !ids[x.action.action_id]; });
      S.lastPoll = new Date();
    }).catch(function () { /* 読めない時は次回 */ });
  }
  /* v0.3.15 (R7N Part F): 30 秒ごとの更新 — データ (実況表 · queue · 催促 · meta · 写真 · _actions) が変わらなければ 描き直さない (「最終更新」 の時刻だけ)。
     入力中 (入力欄にカーソル · 書きかけの値 · ✎ 修正中 · 選んだ候補) なら 描き直しを後に回す (入力欄から出た時 · 次の更新で)。
     描き直す時も 変わった行 · 欄だけ差し替え (setHtml) — スクロール位置 · 開いたカード · 入力中の値はそのまま */
  function dataSig() {
    try {
      return JSON.stringify([S.jik, S.queue, S.remind, S.meta, S.photos, (S.actions || []).map(function (x) { return (x.action || x).action_id; }).sort()]);
    } catch (e) { return String(Date.now()); }
  }
  function updateStamp() {
    var el = $('c01-upd');
    if (el && S.lastLoad) el.textContent = S.lastLoad.toTimeString().slice(0, 5);
  }
  function typingNow() {
    var a = document.activeElement;
    if (!a || !/^(INPUT|TEXTAREA|SELECT)$/.test(a.tagName) || /^(checkbox|radio|button)$/i.test(a.type || '')) return false;
    return !!(a.closest && a.closest('#c01-main, #c01-panel'));
  }
  function unsavedNow() {
    if (S.qedit) return true;
    if (S.sel && (String(S.panelInput || '').trim() || Object.keys(S.picks || {}).length)) return true;
    if (S.view !== 'input' || !S.qsel) return false;
    var ov = overlay();
    var cd = cardOf(S.cards, S.qsel);
    var its = cd ? cd.items : qItems().filter(function (y) { return y.queue_id === S.qsel; });
    return its.some(function (y) {
      if (queueState(y, ov).done) return false;
      var v = S.qvals[y.queue_id];
      if (v && v._auto) return false;                         /* v0.3.18: TOOL が選んでおいただけ (人の入力ではない) */
      return S.qchoice[y.queue_id] !== undefined || !!(v && Object.keys(v).some(function (k) { return k !== '_src' && String(v[k] == null ? '' : v[k]).trim(); }));
    });
  }
  function busy() { return typingNow() || unsavedNow(); }
  function tick() {
    return Promise.all([poll(), loadAll().catch(function () {})]).then(function () {
      var sg = dataSig();
      if (sg !== S.sig) { S.sig = sg; S.dirty = true; }
      updateStamp();
      if (!S.dirty) return;                      /* 変わっていない = 描き直さない */
      if (busy()) { S.held = (S.held || 0) + 1; return; }    /* 入力中 = 後で */
      render({ auto: true });
    });
  }
  document.addEventListener('focusout', function () {
    setTimeout(function () { if (S.dirty && S.jik && !busy()) render({ auto: true }); }, 0);
  });

  function render(opt) {
    if (!S.jik) return;
    var auto = !!(opt && opt.auto);
    S.dirty = false;
    var keep = {};
    ['jikkyou-wrap'].forEach(function (id) { var e = $(id); if (e) keep[id] = [e, e.scrollTop, e.scrollLeft]; });
    var lst = document.querySelector('.c01-items'), ob = document.querySelector('.c01-orig-b');
    var lstY = lst ? lst.scrollTop : 0, obY = ob ? ob.scrollTop : 0, obX = ob ? ob.scrollLeft : 0;
    var wy = window.scrollY || 0, view0 = S.lastView;
    renderNav();
    if (S.view === 'main') renderMain(); else { $('c01-panel').hidden = true; renderInput(); }
    /* 差し替えで箱が新しくなった時も 同じ画面ならスクロール位置を戻す */
    if (view0 === S.view) {
      Object.keys(keep).forEach(function (id) { var e = $(id); if (e && e !== keep[id][0]) { e.scrollTop = keep[id][1]; e.scrollLeft = keep[id][2]; } });
      var l2 = document.querySelector('.c01-items'), o2 = document.querySelector('.c01-orig-b');
      if (lst && l2 && l2 !== lst) l2.scrollTop = lstY;
      if (ob && o2 && o2 !== ob) { o2.scrollTop = obY; o2.scrollLeft = obX; }
      if ((window.scrollY || 0) !== wy) window.scrollTo(window.scrollX || 0, wy);
    }
    S.lastView = S.view;
    if (!(auto && S.lb)) renderLightbox();                /* 自動更新では 開いている写真を描き直さない */
    S.renders = (S.renders || 0) + 1;
    document.body.setAttribute('data-c01-ready', '1');
  }

  /* ── 開始 ── */
  function start(src) {
    S.src = src;
    return src.init().then(function (info) {
      S.info = info;
      return src.getStaff().then(function (s) { S.staff = s; }).catch(function () { S.staff = null; });
    }).then(function () {
      var saved = null;
      try { saved = localStorage.getItem('c01_local_me'); } catch (e) { /* なし */ }
      var s = staffList().filter(function (x) { return x.code === saved; })[0];
      S.me = s ? { code: s.code, name: s.name || s.code, email: s.email } : null;
      if (typeof src.me === 'function') S.me = src.me(S.staff);          /* graph: ログインした人 (選ばない) */
      S.port = S.me ? 'mine' : 'all';
      S.ports = [];
      loadPorts();                                                        /* v0.3.7: 記憶した 担当港 の組み合わせ (なければ既定) */
      updateUserChip();
      return loadAll();
    }).then(poll).then(function () {
      S.sig = dataSig();
      render();
      if (S.timer) clearInterval(S.timer);
      S.timer = setInterval(tick, C01.SOURCE.pollMs);
    }).catch(function (e) {
      $('c01-main').innerHTML = '<div class="c01-fatal"><b>データを読めませんでした</b><p>' + esc(e.message) + '</p><p>_data フォルダ (jikkyou.json · queue.json) があるフォルダを選んでください。</p></div>';
    });
  }
  C01.app = { start: start, render: render, tick: tick, poll: poll, photoTabName: photoTabName, busy: busy, _rot: rotMap, ctDupWarn: ctDupWarn };
})();
