/* ✦ Powered by LEENAI Automation System — C-01 搬入票 TOOL 本体 (実況表 · 確認・入力 · 写真)
   画面の基準 = 試案 (relay\design\試案_実況表_Main / 試案_確認入力_Input)。データは C01.sources から読む (HTML・JS にデータなし)。 */
'use strict';
window.C01 = window.C01 || {};

(function () {
  var FIELD_LABEL = { ct: 'CT番号', seal: 'シール番号', n_w: '正味重量', t_w: '風袋重量', bales: 'ベール数', work_date: '作業日' };
  var FIELD_SHORT = { ct: 'CT', seal: 'シール', n_w: '正味', t_w: '風袋', bales: 'ベール', work_date: '作業日' };
  var REASON_SHORT = { SOURCE_MISMATCH: '値の違い', RANGE: '範囲外', MISSING_FIELD: '未読', NO_SLOT: 'スロット', SLOT_VANISHED: 'スロット',
    SLOT_CANDIDATES: 'スロット', UNIT_PRICE_DIFF: '単価', AUTO_CORRECTED: '補正', GROUP_HOLD: '写真', CT_INVALID: 'CT', SEAL_FORMAT: 'シール',
    WORK_DATE: '作業日', MIN_SOURCES: '出典', SAME_CT_TWO_CONTAINERS: '重複',
    CONTRACT_MONTH_CONFLICT: '契約月', NW_OVER_LIMIT: '重量',   // R6M7: 사유 코드 27 (#115) · 28 (#125) — 문장은 엔진 reason_text
    PHOTO_SET_INCOMPLETE: '写真不足', PACKER_AUTOSTOP: '停止中' };   // R6M11: 사유 코드 29 (#129·#131) · 30 (#118) — 문장은 엔진 reason_text
  // R6M11 (#129 「実況表 줄に足りない写真の種類」): 사유 29 줄의 빠진 종류 (엔진 row.photo_missing) — 문장의 {없는 종류} 를 바꿈
  function reasonTexts(r) {
    var miss = r.photo_missing || '';
    return (r.reason_text || []).map(function (t) { return String(t).split('{없는 종류}').join(miss || '—'); });
  }
  var KIND = {
    '値の違い': { key: 'diff', color: 'var(--c-diff)' },
    '手入力': { key: 'manual', color: 'var(--c-manual)' },
    '写真のCT': { key: 'photo', color: 'var(--c-photo)', label: '写真の CT' },
    '未分類FAX': { key: 'fax', color: 'var(--c-fax)', label: '未分類 FAX' },
    '写真不足': { key: 'photo', color: 'var(--c-photo)' },    /* R6M13 (エンジン out_queue_photo_set): 理由 29 の行 — 写真を見て 確認する */
    '業者・IV未定': { key: 'hold', color: 'var(--c-fax)', label: '業者・IV 未定' },   /* v0.3.11 (R7J Part C · エンジン out_queue_hold): 保留中のメールの書類 */
    '同一候補': { key: 'same', color: 'var(--c-photo)', label: '同一コンテナ候補' }   /* v0.3.12 (R7K Part C · 決定 #150): FAX の行 ↔ 写真の行 (エンジン same_cand) */
  };
  var SAME = '同一候補';
  var HOLD = '業者・IV未定';
  var HOLD_TEXT = { PACKER_MISMATCH: '業者が合いません', PACKER_MULTI: '業者が複数', BKG_MULTI: 'BKG が複数', BKG_UNKNOWN: 'BKG が見つかりません',
    NO_BKG: 'BKG が読めません', UNREGISTERED_SENDER: '送信元が未登録' };
  /* v0.3.11 (R7J Part A): 確認・入力 = コンテナ 1 台 = 1 枚 (CT が分からない項目は 書類 1 つ = 1 枚) */
  var VALUE_KINDS = { '値の違い': 1, '手入力': 1 };
  var DOC_KINDS = { '値の違い': 1, '手入力': 1, '未分類FAX': 1, '業者・IV未定': 1 };
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
    timer: null, remind: null, modal: null
  };
  C01.state = S;

  /* ── ユーティリティ ── */
  function esc(s) { return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); }
  function num(v) { return v == null || v === '' ? '' : (typeof v === 'number' ? v.toLocaleString('en-US') : esc(v)); }
  function md(d) { return d ? String(d).slice(5).replace('-', '/') : ''; }
  /* v0.3.12 (R7K Part G · 決定 #153): 作業日 — 搬入票の値はそのまま (黒) · 無い時 (メール未着の枠 · 搬入票待ちの行) は 枠の COMPASS 予定日を 灰色 ·
     今日以前は 太字の赤 (旧 実況表と同じ)。予定日は表示だけ — Compass入力 · 判定 · 値の比較には使わない (#103) */
  function slotPlan(iv, guid) { var sl = (iv.slots || []).filter(function (x) { return guid && x.slot_guid === guid; })[0]; return sl && sl.work_date ? sl.work_date : null; }
  function wdCell(v, plan) {
    if (v) return '<td>' + esc(md(v)) + '</td>';
    if (!plan) return '<td></td>';
    var today = (S.info && S.info.today) || jstNow().slice(0, 10);
    var past = String(plan).slice(0, 10) <= today;
    return '<td><span class="c01-wdplan' + (past ? ' past' : '') + '" title="' + esc('COMPASS の予定日（表示のみ · 入力・判定には使いません）' + (past ? ' · 予定日を過ぎています' : '')) + '">' + esc(md(plan)) + '</span></td>';
  }
  function $(id) { return document.getElementById(id); }
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
  function hydrate(root) {
    (root || document).querySelectorAll('[data-pdf]').forEach(drawPdf);
    if (!isFolder()) return;
    (root || document).querySelectorAll('[data-rel]').forEach(function (el) {
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
  function pdfTag(rel, page, thumb) {
    return '<div class="c01-pdf' + (thumb ? ' thumb' : '') + '" data-pdf="' + esc(rel) + '" data-page="' + (+page || 1) + '"' + (thumb ? ' data-thumb="1"' : '') +
      '><canvas></canvas><span class="c01-pdfmsg">' + (thumb ? '' : '読み込み中…') + '</span></div>';
  }
  function drawPdf(el) {
    var rel = el.getAttribute('data-pdf'), thumb = el.getAttribute('data-thumb') === '1';
    var want = +el.getAttribute('data-page') || 1;
    pdfDoc(rel).then(function (doc) {
      var n = doc.numPages, pg = Math.min(Math.max(1, want), n);
      el.setAttribute('data-pages', n);
      if (!thumb) { S.pdfPage[rel] = pg; var lab = $('pdf-pg'); if (lab) lab.textContent = 'p.' + pg + ' / ' + n; }
      return doc.getPage(pg).then(function (page) {
        var rot = thumb ? 0 : S.rot;
        var r = (page.rotate + rot) % 360;
        var v1 = page.getViewport({ scale: 1, rotation: r });
        var cssW = thumb ? 150 : Math.round(640 * S.zoom / 100);
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
  function myPorts() {
    if (!S.me || !S.staff) return null;
    var items = S.staff.items || [];
    var mine = [], star = false;
    items.forEach(function (it) {
      var main = it.main || it['担当'] || '', sub = it.sub || it['補助'] || '';
      var hit = [main, sub].some(function (x) { return x && (x === S.me.code || x === S.me.email); });
      if (!hit) return;
      if (it.pol === '*') star = true; else mine.push(it.pol);
    });
    return { ports: mine, star: star, known: items.map(function (it) { return it.pol; }).filter(function (p) { return p !== '*'; }) };
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
      if (!mp) return true;
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
        if (!byCell[key]) byCell[key] = a; else if (a.queue_id && byQueue[a.queue_id] && byQueue[a.queue_id].win !== a) rejected[a.action_id] = 1;
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
  function queueCards(ov) {
    var all = ((S.queue && S.queue.items) || []).concat(sameItems()).filter(function (q) { return queuePortOk(q) && !faxHidden(q) && !exclHidden(q, ov); });
    return { all: all, cards: buildCards(all, ov) };
  }

  /* ── 実況表のデータ組み立て ── */
  function statusOf(r, iv, ov) {
    var st = r.status;
    var human = Object.assign({}, r.human || {});
    VALUE_FIELDS.concat(['ct', 'work_date']).forEach(function (f) {
      var a = ov.byCell[r.container_id + '|' + f] || ov.byCell[iv.iv_no + '|' + r.ct + '|' + f];
      if (a && !human[f]) human[f] = { value: a.value, source: a.source, by: a.by, at: a.at, action_id: a.action_id, overlay: true, override: a.override || null };
    });
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
    var ivs = ((S.jik && S.jik.ivs) || []).filter(function (iv) { return portOk(iv.pol); })
      .slice().sort(function (a, b) { return (a.cy_cut || '') < (b.cy_cut || '') ? -1 : (a.cy_cut || '') > (b.cy_cut || '') ? 1 : (a.iv_no < b.iv_no ? -1 : 1); });
    ivs.forEach(function (iv) {
      var rows = iv.rows.map(function (r) {
        var x = statusOf(r, iv, ov);
        var vals = {};
        ['ct', 'seal', 'n_w', 't_w', 'bales', 'work_date'].forEach(function (f) { vals[f] = x.human[f] ? x.human[f].value : r[f]; });
        var openQ = ((S.queue && S.queue.items) || []).filter(function (q) { return q.container_id === r.container_id && !queueState(q, ov).done; });
        var short = openQ.length && openQ[0].field ? FIELD_SHORT[openQ[0].field] : (REASON_SHORT[(r.reasons || [])[0]] || (r.reasons || [])[0] || '');
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
        return { kind: 'row', key: rowKey(iv, r), r: r, st: x.st, human: x.human, vals: vals, short: short, wait: wait, openQ: openQ, candTitle: candTitle };
      });
      var unarr = (iv.mail_missing || []).map(function (m) {
        return { kind: 'missing', key: iv.iv_no + '|missing|' + m.slot_guid, m: m, st: 'メール未着', vals: { work_date: m.work_date }, wait: 'メール未着' };
      });
      var okN = rows.filter(function (x) { return x.st === '自動OK' || x.st === '確認済'; }).length;
      var allOk = rows.length > 0 && okN === rows.length && !unarr.length;
      var hasCheck = rows.some(function (x) { return x.st === '再確認'; });
      /* v0.2.0: 催促 = エンジンの催促下書き (remind.json — 現行リマインダーの基準) がある IV。remind.json が無い時は R5 と同じ (受信中・メール未着) */
      var remind = S.remind ? (remindsOf(iv.iv_no).length > 0 || !!((S.remind.cand || {})[iv.iv_no])) : (rows.some(function (x) { return x.st === '受信中'; }) || unarr.length > 0);
      var compassDone = (iv.compass_input || []).length > 0;
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
      /* v0.3.11 (R7J Part C-2): 同じブッキングに枠の決まっていない行があれば、空き枠は「未着」ではなく「割当待ち」 (行の数まで) */
      unarr.slice(0, free.length).forEach(function (x) { x.st = '割当待ち'; x.wait = '割当待ち'; x.waitTitle = 'このブッキングに枠の決まっていない行（未割当）があります — メールは届いている可能性'; });
      var shownUn = S.showUnarrived ? unarr : [];
      var bySeq = slotted.concat(shownUn).map(function (x, i) { return { x: x, k: seqOf[x.kind === 'missing' ? x.m.slot_guid : x.r.slot_guid], i: i }; })
        .sort(function (a, b) { var ka = a.k === undefined ? 1e9 : a.k, kb = b.k === undefined ? 1e9 : b.k; return ka - kb || a.i - b.i; })
        .map(function (e) { return e.x; });
      var list = bySeq.concat(free);
      var ivNo = 0;
      list.forEach(function (x) { ivNo += 1; x.no = ivNo; no += 1; });
      var nSlots = (iv.slots && iv.slots.length) || iv.slots_n || 0;
      var total = nSlots ? Math.max(nSlots, rows.length - Math.min(free.length, unarr.length) + unarr.length) : rows.length + unarr.length;
      out.push({ iv: iv, rows: list, okN: okN, total: total, nFree: free.length, allOk: allOk, onlyUn: onlyUn, remind: remind, compassDone: compassDone });
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
    $('c01-nav').innerHTML =
      '<nav class="c01-tabs" aria-label="画面">' +
      '<button id="tab-main" class="c01-tab' + (S.view === 'main' ? ' on' : '') + '">実況表</button>' +
      '<button id="tab-input" class="c01-tab' + (S.view === 'input' ? ' on' : '') + '">確認・入力 <span class="c01-badge" id="badge-open">' + open + '</span></button>' +
      '</nav>' +
      '<span class="c01-sub">' + esc(t) + ' 時点 · 最終更新 ' + upd + '（自動更新）</span>' +
      '<span class="c01-flex"></span>' +
      (graphMode()
        ? '<span class="c01-local c01-sp" title="SharePoint ドキュメント / ' + esc(C01.SOURCE.spRoot) + ' から読んでいます (ログインした人の権限)">SharePoint · ' + esc(C01.SOURCE.spRoot) + '</span>' +
          '<span class="c01-me" id="me-name">担当者 ' + esc(S.me ? S.me.name : '?') + '</span>'
        : '<span class="c01-local" title="データは選んだフォルダから読んでいます (SharePoint には接続しません)">ローカルプレビュー · ' + esc(S.info ? S.info.label : '') + '</span>' +
          '<label class="c01-me">担当者 <select id="me-select" aria-label="担当者">' + staffOpts + '</select></label>');
    $('tab-main').onclick = function () { S.view = 'main'; render(); };
    $('tab-input').onclick = function () { S.view = 'input'; if (!S.qsel) { var f = openQueue()[0]; S.qsel = f ? f.queue_id : null; } render(); };
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
    var ports = [['mine', '自分の担当' + (mp ? '（' + (mp.ports.join(' · ') || 'なし') + (mp.star ? ' · *' : '') + '）' : '（担当者未選択）')], ['all', '全港']];
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
      ports.map(function (p) { return '<button class="c01-chip' + (portOn(p[0]) ? ' on' : '') + '" data-port="' + esc(p[0]) + '" aria-pressed="' + (portOn(p[0]) ? 'true' : 'false') + '">' + esc(p[1]) + '</button>'; }).join('') +
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
        '<span class="c01-flex"></span>' +
        (iv.hold_docs ? '<button class="c01-btn-sub c01-holdlink" data-holdiv="' + esc(iv.iv_no) + '" title="保留中のメールにこの IV の書類らしいファイルがあります（確認・入力「業者・IV 未定」）">候補書類あり (' + (+iv.hold_docs) + ')</button>' : '') +
        (g.remind ? '<button class="c01-btn-sub" data-remind="' + esc(iv.iv_no) + '">✉ 催促</button>' : '') +
        (g.compassDone ? '<span class="c01-done">✓ 入力済</span>' :
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
        var ctCell = photos > 0 ? '<button class="c01-ctlink" data-photos="' + esc(x.key) + '" title="クリックで写真を表示">' + esc(v.ct || '') + '</button>' : '<span class="mono">' + esc(v.ct || '') + '</span>';
        var hmark = function (f) { return x.human[f] ? ' <span class="c01-hm" title="確認済 ' + esc(x.human[f].by || '') + '">✓</span>' : ''; };
        var stCell = x.st === '自動OK' || x.st === '確認済' ? '<span class="st-ok">' + x.st + '</span>' :
          x.st === '再確認' ? '<button class="c01-checkbtn" data-sel="' + esc(x.key) + '">⚠ 要確認 · ' + esc(x.short) + '</button>' :
            '<span class="st-wait' + (x.candTitle ? ' c01-cand' : '') + '"' + (x.candTitle ? ' title="' + esc(x.candTitle) + '"' : '') + '>' + esc(x.wait) + '</span>';
        if (x.unassigned) stCell = '<span class="c01-unassigned" title="COMPASS の枠がまだ決まっていない行（台数は枠の数で数えます）">未割当</span> ' + stCell;
        if (r.same_cand && !sameDone(r.same_cand.pair_id, b.ov)) stCell += ' <button class="c01-samebadge" data-same="' + esc(r.same_cand.pair_id) + '" title="' +
          esc(r.same_cand.role === 'fax' ? '写真の行と同じコンテナかもしれません（FAX の CT・シールの読み違い）— クリックで確認' : 'FAX の行と同じコンテナかもしれません — クリックで確認') + '">同一候補</button>';
        stCell += rowInfo(iv, r, x, b.ov) + (canSlotChange() && r.ct ? ' <button class="c01-slotbtn" data-slot="' + esc(x.key) + '" title="スロット変更">⇄</button>' : '');
        html += '<tr class="c01-row ' + cls + (x.unassigned ? ' unassigned' : '') + '" data-key="' + esc(x.key) + '" data-status="' + esc(x.st) + '"><td class="c-no">' + x.no + '</td><td>' + esc(iv.cy_cut || '') +
          '</td>' + c1(iv.iv_no, 'mono') + cv(rowVal(iv, r, 'item')) + '<td class="c-cut">' + ctCell + '</td><td class="mono c-cut" title="' + esc(v.seal || '') + '">' + esc(v.seal || '') + hmark('seal') +
          '</td><td class="r num">' + num(v.n_w) + hmark('n_w') + '</td><td class="r num">' + num(v.t_w) + hmark('t_w') + '</td><td class="r num">' + num(v.bales) + hmark('bales') +
          '</td>' + wdCell(v.work_date, x.st === '受信中' && r.has_docs === false ? slotPlan(iv, slotOf(iv, r, b.ov) || r.slot_guid) : null) +
          cv(rowVal(iv, r, 'incoterms'), true) + cv(rowVal(iv, r, 'packer')) + cv(rowVal(iv, r, 'plant')) + '<td' +
          (photoAlert(photos, rowVal(iv, r, 'packer').v) ? ' class="c01-ph-alert" title="' + esc(photoAlertText(photos, rowVal(iv, r, 'packer').v)) + '"' : '') + '>' +
          (photos > 0 ? '<button class="c01-phbtn" data-photos="' + esc(x.key) + '">📷 ' + photos + '枚</button>' : '0枚') + '</td><td class="c-st">' + stCell + '</td></tr>';
      });
      html += '</tbody>';
    });
    if (!b.groups.length) html += '<tbody><tr><td colspan="15" class="c01-empty">表示する IV がありません（担当港・絞り込みを確認してください）</td></tr></tbody>';
    html += '</table></div>';
    html += '<div class="c01-legend"><span><i class="lg ok"></i>自動OK / 確認済</span><span><i class="lg check"></i>要確認</span><span><i class="lg wait"></i>受信待ち · メール未着</span>' +
      '<span class="c01-flex"></span><span>✦ Powered by LEENAI Automation System</span></div>';
    $('c01-main').innerHTML = html;
    var root = $('c01-main');
    root.querySelectorAll('[data-port]').forEach(function (el) { el.onclick = function () { pickPort(el.getAttribute('data-port')); render(); }; });
    root.querySelectorAll('[data-filter]').forEach(function (el) { el.onclick = function () { var f = el.getAttribute('data-filter'); S.filter = S.filter === f ? 'all' : f; render(); }; });
    $('show-unarrived').onchange = function () { S.showUnarrived = !S.showUnarrived; render(); };
    root.querySelectorAll('[data-photos]').forEach(function (el) { el.onclick = function () { openLightbox(el.getAttribute('data-photos'), 0); }; });
    root.querySelectorAll('[data-compass]').forEach(function (el) { el.onclick = function (ev) { ev.stopPropagation(); openCompass(el.getAttribute('data-compass')); }; });
    root.querySelectorAll('[data-remind]').forEach(function (el) { el.onclick = function (ev) { ev.stopPropagation(); openRemind(el.getAttribute('data-remind')); }; });
    root.querySelectorAll('[data-same]').forEach(function (el) {
      el.onclick = function (ev) { ev.stopPropagation(); S.view = 'input'; S.qkind = SAME; S.qiv = null; S.qsel = el.getAttribute('data-same'); render(); };
    });
    root.querySelectorAll('[data-holdiv]').forEach(function (el) {
      el.onclick = function (ev) { ev.stopPropagation(); S.view = 'input'; S.qkind = HOLD; S.qiv = el.getAttribute('data-holdiv'); S.qsel = null; render(); };
    });
    root.querySelectorAll('[data-sel]').forEach(function (el) { el.onclick = function () { S.sel = el.getAttribute('data-sel'); S.picks = {}; S.panelInput = ''; render(); }; });
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
  var STATE_LABEL = { SAME: '同じ', FILL: '空欄→入力', DIFF: '違う値', KEEP: '値なし（そのまま）' };
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
  function showModal(html) {
    var m = $('c01-modal');
    m.innerHTML = '<div class="c01-mbg" id="m-bg"></div><div class="c01-modal" role="dialog" aria-modal="true">' + html + '</div>';
    m.hidden = false;
    $('m-bg').onclick = closeModal;
    m.querySelectorAll('[data-close]').forEach(function (el) { el.onclick = closeModal; });
  }
  function openCompass(ivNo) {
    var iv = ivById(ivNo);
    if (!iv) return;
    S.modal = { kind: 'compass', iv: ivNo };
    S.src.getJson('compass_now/' + ivNo + '.json').then(function (snap) { return snap; }).catch(function () { return null; }).then(function (snap) {
      if (!S.modal || S.modal.iv !== ivNo) return;
      var html = '<div class="c01-mh"><b>Compass入力 — 比較表</b><span class="mono">' + esc(ivNo) + '</span><span class="t2">BKG ' + esc(iv.bkg_no || '') + ' · CY ' + esc(md(iv.cy_cut)) + '</span>' +
        '<span class="c01-flex"></span><button class="c01-btn-ghost2" data-close>閉じる</button></div>';
      if (!snap) {
        html += '<div class="c01-mb"><p class="c01-err">COMPASS の今の値がありません（ローカルプレビュー: compass_now/' + esc(ivNo) + '.json なし）</p></div>';
        showModal(html);
        return;
      }
      var res = C01.compass.compareIv(ivNo, compassInput(iv), snap.cells || {}, snap.dups || {}, C01.COMPASS || null);
      S.modal.res = res;
      html += '<div class="c01-mb"><div class="c01-csum">' +
        '<span class="c01-cst SAME">同じ ' + res.count.cells.SAME + '</span><span class="c01-cst FILL">空欄→入力 ' + res.count.cells.FILL + '</span>' +
        '<span class="c01-cst DIFF">違う値 ' + res.count.cells.DIFF + '</span><span class="c01-cst KEEP">値なし ' + res.count.cells.KEEP + '</span>' +
        '<span class="t2">PATCH 対象 ' + res.count.patch_rows + '行 · 作業日は入れません</span></div>' +
        (res.all_ok ? '' : '<p class="c01-warnline" id="cmp-reason">' + esc(res.button.reason || '') + ' — 比較表だけ表示します</p>') +
        '<table class="c01-ctable" id="compass-table"><thead><tr><th>CT</th>' + C01.compass.FIELDS.map(function (f) { return '<th>' + CF_LABEL[f[0]] + '</th>'; }).join('') +
        '<th>警告・理由</th></tr></thead><tbody>';
      res.rows.forEach(function (r) {
        html += '<tr data-crow="' + esc(r.container_id || '') + '"><td class="mono">' + esc(r.ct || '—') + '</td>';
        if (r.skip) {
          html += '<td colspan="' + C01.compass.FIELDS.length + '" class="c01-skip">' + esc(SKIP_LABEL[r.skip] || r.skip) + '</td>';
        } else {
          r.cells.forEach(function (c) {
            html += '<td class="c01-cell ' + c.state + (c.in_patch ? ' in' : '') + '" title="' + esc(STATE_LABEL[c.state]) + '" data-state="' + c.state + '">' +
              '<div class="now">' + esc(c.now == null ? '（空）' : c.now) + '</div>' + (c.state === 'SAME' || c.state === 'KEEP' ? '' : '<div class="put">→ ' + esc(c.put == null ? '' : c.put) + '</div>') + '</td>';
          });
        }
        html += '<td>' + r.warnings.map(function (w) { return '<span class="c01-wchip" data-warn="' + w + '">' + esc(WARN_LABEL[w] || w) + '</span>'; }).join('') + '</td></tr>';
      });
      html += '</tbody></table><details class="c01-patch"><summary>PATCH 本文（送りません）</summary><pre id="compass-patch">' +
        esc(JSON.stringify(res.patches, null, 1)) + '</pre></details></div>' +
        '<div class="c01-mf"><span class="t2">If-Match (etag) 付きで入力 → もう一度読んで確認 → compass_done を記録（R7 以降・職員ログイン）</span><span class="c01-flex"></span>' +
        '<button id="compass-send" class="c01-btn-pri" disabled aria-disabled="true" title="R6 はローカル DRY">DRY — 送信しません</button></div>';
      showModal(html);
    });
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
    if (s && s[key]) return { v: s[key], t: s[key] };
    if (own) return { v: own, t: own };
    var u = [];
    ((iv && iv.slots) || []).forEach(function (x) { if (x[key] && u.indexOf(x[key]) < 0) u.push(x[key]); });
    if (u.length === 1) return { v: u[0], t: u[0] };
    if (u.length > 1) return { v: '—', t: '候補: ' + u.join(' / ') };
    var f = (iv && iv[key]) || '';
    return String(f).indexOf('・') >= 0 ? { v: '—', t: '候補: ' + String(f).split('・').join(' / ') } : { v: f, t: f };
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
        '<pre class="c01-rbody">' + esc(signed(d.body_text || '')) + '</pre></section>';
    });
    var past = (iv && iv.reminders) || [];
    html += '<div class="c01-rpast"><b>これまでの催促</b>' + (past.length ? '<ul>' + past.map(function (p) {
      return '<li>' + esc(String(p.at || '').slice(0, 16).replace('T', ' ')) + ' · ' + esc(p.by || '') + (p.value && p.value.round ? ' · ' + esc(p.value.round) + '回目' : '') + '</li>';
    }).join('') + '</ul>' : '<span class="t2"> なし</span>') + '</div></div>' +
      '<div class="c01-mf"><span class="t2">送信は押した職員本人のメールから（決定 #97）· 回数・送信者を記録</span><span class="c01-flex"></span>' +
      '<button id="remind-send" class="c01-btn-pri" disabled aria-disabled="true" title="R6 は下書きだけ">下書きのみ</button></div>';
    showModal(html);
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
    var doc = qs.map(function (q) { return (q.files || [])[0]; }).filter(Boolean)[0];
    var ph = (S.photos[iv.iv_no] && (S.photos[iv.iv_no].containers || []).filter(function (c) { return c.container_id === r.container_id; })[0]) || null;
    var firstPhoto = ph && ph.photos && ph.photos[0];
    var fields = VALUE_FIELDS.map(function (fd) {
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
      var v = r[fd];
      var note = st && st.done ? '確認済' + (st.by ? ' · ' + st.by : '') : '';
      return '<div class="c01-pf"><span class="c01-pl">' + FIELD_LABEL[fd] + '</span><div class="c01-same"><span class="mono">' + num(v) + '</span><span class="ok">' + esc(note) + '</span></div></div>';
    }).join('');
    var needPick = Object.keys(diffQ).filter(function (fd) { return diffQ[fd].kind === '値の違い' && !queueState(diffQ[fd], ov).done; });
    var psQ = qs.filter(function (q) { return q.kind === PHOTO_SET && !queueState(q, ov).done && r.ct; })[0] || null;
    var ready = needPick.length > 0 ? (needPick.every(function (fd) { return S.picks[fd]; }) || (needPick.length === 1 && S.panelInput.trim())) : !!psQ;
    var lostMsg = qs.some(function (q) { var s = queueState(q, ov); return s.mineLost; }) ? '<p class="c01-lost">他の人が先に確認しました</p>' : '';
    el.hidden = false;
    el.innerHTML = '<div class="c01-overlay" id="panel-bg"></div><aside class="c01-side" role="dialog" aria-label="要確認の詳細">' +
      '<div class="c01-side-h"><div><div class="k">要確認</div><div class="mono big">' + esc(r.ct || '（CT 不明）') + '</div><div class="t2">' +
      esc(iv.iv_no + ' · ' + (iv.pol || '') + ' · ' + rowVal(iv, r, 'packer').v + ' ' + rowVal(iv, r, 'plant').v) + '</div></div>' +
      '<button class="c01-x" id="panel-close" aria-label="閉じる">✕</button></div>' +
      '<div class="c01-side-b">' + lostMsg +
      '<p class="c01-reason">' + esc(reasonTexts(r).join(' / ') || (r.reasons || []).join(' / ')) + '</p>' +
      '<div class="c01-thumbs"><button id="panel-doc" class="c01-thumb"' + (doc ? '' : ' disabled') + '>' + (doc ? (/\.pdf$/i.test(doc.path || '') ? pdfTag(doc.path, doc.page, true) : imgTag(doc.path, 'c01-thimg', '原本')) : '') + '<span>' + (doc ? esc('原本 ' + (doc.name || '') + (doc.page ? ' p' + doc.page : '')) : '原本なし') + '</span></button>' +
      '<button id="panel-photo" class="c01-thumb"' + (firstPhoto ? '' : ' disabled') + '>' + (firstPhoto ? imgTag(firstPhoto.path, 'c01-thimg', '写真') : '') + '<span>' + (firstPhoto ? esc('写真 ' + (firstPhoto.label || '')) : '写真なし') + '</span></button></div>' +
      fields +
      (needPick.length === 1 ? '<label class="c01-direct">どちらも違う場合は直接入力<input id="panel-input" type="text" placeholder="正しい値" value="' + esc(S.panelInput) + '"></label>' : '') +
      (needPick.length || psQ ? '' : '<p class="c01-note2">ここで確認できる項目はありません — 確認・入力 で処理してください</p>') +
      '<div class="c01-side-btns"><button id="panel-ok" class="c01-btn-big' + (ready ? ' ready' : '') + '"' + (ready ? '' : ' disabled') + '>' + (ready ? '確認する' : '正しい値を選んでください') + '</button>' +
      '<button id="panel-later" class="c01-btn-ghost2">あとで</button></div>' +
      '<p class="c01-foot">記録: ' + esc(S.me ? S.me.name : '（担当者を選んでください）') + '</p>' +
      '</div></aside>';
    hydrate(el);
    $('panel-close').onclick = $('panel-later').onclick = $('panel-bg').onclick = function () { S.sel = null; render(); };
    if (doc) $('panel-doc').onclick = function () { S.view = 'input'; S.qsel = qs[0].queue_id; S.sel = null; render(); };
    if (firstPhoto) $('panel-photo').onclick = function () { openLightbox(S.sel, 0); };
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
    return ((S.queue && S.queue.items) || []).filter(function (q) { return !queueState(q, ov).done && queuePortOk(q) && !faxHidden(q) && !exclHidden(q, ov); });
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
    return !iv || portOk(iv.pol);
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
  /* v0.3.3 (R7C): 確認・入力 の原本 — 項目のファイル (複数なら切り替え)。ファイルの指定が無い項目 (手入力 など) は その IV の書類 (photos/{IV}.json docs) を出す */
  function qFiles(q) {
    var fs = (q.files || []).filter(function (f) { return f && f.path; });
    if (fs.length || q.kind === '写真のCT' || q.kind === PHOTO_SET || q.kind === '未分類FAX' || q.kind === HOLD || !q.iv_no) return fs;
    var ph = S.photos[q.iv_no];
    if (!ph) {
      if (!S.qload) S.qload = {};
      if (!S.qload[q.iv_no]) { S.qload[q.iv_no] = 1; loadPhotos(q.iv_no).then(function () { render(); }); }
      return [];
    }
    return (ph.docs || []).filter(function (d) { return d && d.path && !/(^|\/)thumbs\.db$|\.db$/i.test(d.path); }).map(function (d) {
      return { path: d.path, name: String(d.path).split('/').pop(), page: 1, ivdoc: true, sha16: d.sha16 || '' };
    });
  }
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
      return (k !== PHOTO_SET && k !== HOLD && k !== SAME) || ((S.queue && S.queue.kinds) || []).indexOf(k) >= 0 || (k === SAME && all.some(function (y) { return y.kind === SAME; }));
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
      var files = isPhotos ? (q.files || []) : qFiles(q);
      var fIdx = isPhotos ? 0 : curFileIdx(q);
      var f = files[fIdx] || {};
      curF = isPhotos ? null : f;
      var qrow = q.container_id && iv ? iv.rows.filter(function (r) { return r.container_id === q.container_id; })[0] : null;
      var qph = qrow ? (qrow.photos || 0) : null;
      var isPdfF = !isPhotos && /\.pdf$/i.test(f.path || '');
      var pdfPg = isPdfF ? (S.pdfPage[f.path] || f.page || 1) : 0;
      html += '<div class="c01-orig-h"><span class="t2">' + (isPhotos ? '写真' : q.kind === '未分類FAX' ? 'FAX' : q.kind === HOLD ? '保留中の書類' : '搬入票') + '</span><span class="mono">' + esc(isPhotos ? files.length + '枚' : (f.name || '')) + '</span>' +
        (qph !== null ? '<span class="c01-phcount' + (photoAlert(qph, rowVal(iv, qrow, 'packer').v) ? ' c01-ph-alert' : '') + '" title="' + esc('このコンテナの写真枚数（' + photoRangeText(rowVal(iv, qrow, 'packer').v) + 'は色付き）') + '">写真 ' + qph + '枚</span>' : '') + '<span class="c01-flex"></span>' +
        (!isPhotos ? '<button class="c01-tool" id="z-out" aria-label="縮小">−</button><span class="z">' + S.zoom + '%</span><button class="c01-tool" id="z-in" aria-label="拡大">+</button>' +
          '<button class="c01-tool" id="rot" aria-label="回転">⟳</button>' +
          (isPdfF ? '<button class="c01-tool" id="pdf-prev" aria-label="前のページ">‹</button><span class="t2" id="pdf-pg">p.' + pdfPg + '</span><button class="c01-tool" id="pdf-next" aria-label="次のページ">›</button>' +
            '' : '<span class="t2">' + (f.page ? 'p.' + f.page : '') + '</span>') : '') +
        (!isPhotos && f.path ? '<button class="c01-btn-sub" id="pdf-open" title="SharePoint で開く（別タブ）">別タブで開く</button>' : '') + '</div>';
      if (!isPhotos && files.length > 1) {
        html += '<div class="c01-qfiles" role="tablist" aria-label="原本ファイル">' + (f.ivdoc ? '<span class="t2">この項目の原本の指定がないため IV の書類を表示:</span>' : '') + files.map(function (x, k) {
          return '<button class="c01-chip' + (k === fIdx ? ' on' : '') + '" data-qf="' + k + '" title="' + esc(x.name || '') + '">' + (k + 1) + '. ' + esc(String(x.name || '').slice(0, 28)) + '</button>';
        }).join('') + '</div>';
      } else if (!isPhotos && f.ivdoc) {
        html += '<div class="c01-qfiles"><span class="t2">この項目の原本の指定がないため IV の書類を表示</span></div>';
      }
      html += '<div class="c01-orig-b">';
      if (isPhotos) {
        html += '<div class="c01-grid">' + files.map(function (pf, k) { return '<button class="c01-gph" data-gph="' + k + '">' + imgTag(pf.path, 'c01-gimg', pf.name) + '<span>' + esc(pf.name || '') + '</span></button>'; }).join('') + '</div>';
      } else if (f.path) {
        var isPdf = /\.pdf$/i.test(f.path), isImg = /\.(png|jpe?g|gif|svg|webp|bmp)$/i.test(f.path);
        var w = Math.round(640 * S.zoom / 100);
        html += isPdf ? '<div class="c01-doc pdf">' : '<div class="c01-doc" style="width:' + w + 'px;transform:rotate(' + S.rot + 'deg)">';
        if (isImg) html += imgTag(f.path, 'c01-docimg', f.name);
        else if (isPdf) html += pdfTag(f.path, pdfPg);                 /* v0.3.2: 回転・拡大は pdf.js の描画で (CSS 回転なし) */
        else html += '<p class="c01-note2">このファイルは画面に表示できません（' + esc(f.name || '') + '）— 上の「別タブで開く」で SharePoint で開けます' + (/\.xls[xm]?$/i.test(f.path) ? ' (Excel)' : '') + '</p>';
        if (f.bbox && f.bbox.length === 4 && isImg) {
          var bb = f.bbox;
          html += '<div class="c01-bbox" style="left:' + (bb[0] * 100) + '%;top:' + (bb[1] * 100) + '%;width:' + ((bb[2] - bb[0]) * 100) + '%;height:' + ((bb[3] - bb[1]) * 100) + '%"></div>';
        }
        html += '</div>';
      } else {
        html += '<p class="c01-note2">原本ファイルがありません</p>';
      }
      html += '</div>';
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
          st.act === 'not_same' ? '別のコンテナにしました' : '完了しました')) + (st.by ? '（' + esc(st.by) + '）' : '') + '</p>';
      html += '<p class="c01-qnote k-' + KC.key + '">' + esc(noteOf(q, vItems.length)) + '</p>';
      var msg = S.qmsg[q.queue_id];
      if (msg) html += '<p class="c01-err" id="q-err">' + esc(msg) + '</p>';
      if (VALUE_KINDS[q.kind]) {
        var editing = {};
        (vOpen.length ? vOpen : vItems).forEach(function (y, yi) {
          var fd = y.field;
          editing[fd] = 1;
          var vals = S.qvals[y.queue_id] || {};
          var cur = vals[fd] !== undefined ? vals[fd] : '';
          var alts = [];
          Object.keys(y.values || {}).forEach(function (src) { (y.values[src] || []).forEach(function (v) { alts.push([src, v]); }); });
          html += '<div class="c01-field' + (queueState(y, ov).done ? ' ro' : '') + '" data-vq="' + esc(y.queue_id) + '"><label for="q-in-' + yi + '"><b>' + FIELD_LABEL[fd] + '</b> <span class="t2">' + esc(kindLabel(y.kind)) + '</span><span class="c01-flex"></span><span class="hint">' + esc(hintOf(fd)) + '</span></label>' +
            '<input id="q-in-' + yi + '" data-vin="' + esc(y.queue_id) + '" class="q-in' + (cur ? '' : ' need') + '" value="' + esc(cur) + '" placeholder="' + (y.kind === '手入力' ? '原本を見て入力' : '選ぶか入力') + '" aria-label="' + FIELD_LABEL[fd] + '">' +
            (alts.length && y.kind === '値の違い' ? '<div class="c01-alts2">' + alts.map(function (a, i) {
              var bad = fd === 'ct' && C01.validate && !C01.validate.ctCheckOk(String(a[1]).replace(/[\s-]/g, '').toUpperCase());
              return '<button class="c01-alt2' + (String(cur) === String(a[1]) ? ' on' : '') + '" data-alt="' + esc(y.queue_id) + '|' + i + '"' + (bad ? ' title="チェックデジットが合いません"' : '') + '>' + esc(a[0]) + ' <span class="mono">' + esc(a[1]) + '</span>' + (bad ? ' <span class="c01-bad">✗</span>' : '') + '</button>';
            }).join('') + '</div>' : '') +
            '</div>';
        });
        var row = q.container_id && iv ? iv.rows.filter(function (r) { return r.container_id === q.container_id; })[0] : null;
        if (row) {
          var fst = q.field_source_text || {};      /* v0.2.0: エンジンの項目別出典一致 (field_sources) の文 — 無い時は値だけ */
          html += VALUE_FIELDS.filter(function (x) { return !editing[x]; }).map(function (x) {
            return '<div class="c01-field ro"><label><b>' + FIELD_LABEL[x] + '</b><span class="c01-flex"></span>' +
              (fst[x] ? '<span class="c01-src" data-src-field="' + x + '">' + esc(fst[x]) + '</span>' : '') +
              '</label><div class="mono rov">' + num(row[x]) + '</div></div>';
          }).join('');
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
      } else if (q.kind === HOLD) {
        html += '<div class="c01-hold"><div><span class="k">保留の理由</span> ' + esc(String(q.hold_code || q.note || '').split(',').map(function (c) { return HOLD_TEXT[c] || c; }).join(' · ')) + '</div>' +
          '<div><span class="k">候補の IV</span> <span class="mono">' + esc((q.candidates || []).join(' / ') || '—') + '</span></div>' +
          '<p class="c01-note2">IV への連結はエンジン側の次の版で入ります。今は 原本を確認して、搬入票でなければ「搬入票ではない」、あとで見るなら「スキップ」。</p></div>';
      }
      html += '</div>';
      html += '<div class="c01-form-f"><span class="c01-foot">確認した内容は実況表にすぐ反映 · 記録: ' + esc(S.me ? S.me.name : '（担当者を選んでください）') + '</span></div>';
      /* v0.3.7 (R7D Part U-3): 判断ボタン = 右パネルの一番上 · v0.3.11 (R7J Part B): 「搬入票ではない」 = 書類のある全種類 · 完了 = 「元に戻す」 */
      var ready = readyOf(q);
      var canNot = DOC_KINDS[q.kind] && !st.done && (q.kind === '未分類FAX' || (curF && (curF.sha16 || (q.files || []).some(function (x) { return x.sha16; }))));
      var canUndo = st.done && !st.mineLost && (st.act === 'not_hannyuhyo' || st.act === 'not_ours' || st.act === 'merge_same' || st.act === 'not_same') && st.aid;
      var acts = '<div class="c01-form-a"><button id="q-submit" class="c01-btn-big' + (ready || st.done ? ' ready' : '') + '"' + (ready || st.done ? '' : ' disabled') + '>' +
        (st.done ? '完了しました — 次へ' : q.kind === SAME ? '同じコンテナとして合わせる' : ready ? '確認して次へ' : submitLabel(q)) + '</button>' +
        '<div class="row"><button id="q-skip" class="c01-btn-ghost2">スキップ（あとで）</button>' +
        (q.kind === SAME && !st.done ? '<button id="q-notsame" class="c01-btn-ghost2" title="この 2 行は別のコンテナです（候補を出さなくなります · 元に戻せます）">別のコンテナ</button>' : '') +
        (canNot ? '<button id="q-notours" class="c01-btn-ghost2 danger" title="この書類は搬入票ではありません（ファイルは消しません · 元に戻せます）">搬入票ではない</button>' : '') +
        (canUndo ? '<button id="q-undo" class="c01-btn-ghost2">元に戻す</button>' : '') + '</div></div>';
      html = html.replace(ACT_MARK, acts);
    } else {
      html += '<p class="c01-empty">作業はありません</p>';
    }
    html += '</section></div><p class="c01-powered">✦ Powered by LEENAI Automation System</p>';
    $('c01-main').innerHTML = html;
    hydrate($('c01-main'));
    var root = $('c01-main');
    if ($('fax-old')) $('fax-old').onchange = function () { S.showOldFax = !S.showOldFax; render(); };
    if ($('qiv-clear')) $('qiv-clear').onclick = function () { S.qiv = null; S.qsel = null; render(); };
    root.querySelectorAll('[data-kind]').forEach(function (el) { el.onclick = function () { S.qkind = el.getAttribute('data-kind'); S.qsel = null; render(); }; });
    root.querySelectorAll('[data-q]').forEach(function (el) { el.onclick = function () { S.qsel = el.getAttribute('data-q'); S.zoom = 100; S.rot = 0; render(); }; });
    root.querySelectorAll('[data-sec]').forEach(function (el) { el.onclick = function () { S.qsel = el.getAttribute('data-sec'); S.zoom = 100; S.rot = 0; render(); }; });
    if (!q) return;
    var zi = $('z-in'), zo = $('z-out'), ro = $('rot');
    if (zi) zi.onclick = function () { S.zoom = Math.min(200, S.zoom + 20); render(); };
    if (zo) zo.onclick = function () { S.zoom = Math.max(60, S.zoom - 20); render(); };
    if (ro) ro.onclick = function () { S.rot = (S.rot + 90) % 360; render(); };
    var pel = root.querySelector('.c01-orig [data-pdf]');
    if (pel) {
      var prel = pel.getAttribute('data-pdf');
      var turn = function (d) {
        var n = +pel.getAttribute('data-pages') || 1, cur = S.pdfPage[prel] || +pel.getAttribute('data-page') || 1, nx = Math.min(Math.max(1, cur + d), n);
        if (nx !== cur) { S.pdfPage[prel] = nx; render(); }
      };
      if ($('pdf-prev')) $('pdf-prev').onclick = function () { turn(-1); };
      if ($('pdf-next')) $('pdf-next').onclick = function () { turn(1); };
    }
    if ($('pdf-open')) $('pdf-open').onclick = function () { openTab((qFiles(q)[curFileIdx(q)] || {}).path || ''); };
    root.querySelectorAll('[data-qf]').forEach(function (el) { el.onclick = function () { S.qfile[q.queue_id] = +el.getAttribute('data-qf'); S.zoom = 100; S.rot = 0; render(); }; });
    root.querySelectorAll('[data-gph]').forEach(function (el) {
      el.onclick = function () { openLightboxList('CT 不明の写真', (q.files || []).map(function (pf) { return { path: pf.path, label: pf.name }; }), +el.getAttribute('data-gph')); };
    });
    root.querySelectorAll('[data-vin]').forEach(function (el) {
      var qid = el.getAttribute('data-vin');
      var y = vItems.filter(function (z) { return z.queue_id === qid; })[0];
      el.oninput = function () { var o = {}; o[y.field] = el.value; S.qvals[qid] = Object.assign({}, S.qvals[qid], o); delete S.qmsg[q.queue_id]; refreshSubmit(q); };
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
    var ns = $('q-notsame');
    if (ns) ns.onclick = function () { sameAction(q, 'not_same'); };
    var sph = $('same-ph');
    if (sph && q.same) sph.onclick = function () { var ivx = ivById(q.iv_no); if (ivx) openLightbox(rowKey(ivx, q.same.photo), 0); };
    $('q-submit').onclick = function () { if (queueState(q, overlay()).done && !(VALUE_KINDS[q.kind] && openValueItems(q).length)) { S.qsel = nextQueueId(q); render(); } else submitQueue(q); };
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
    if (q.kind === HOLD) return 'IV 連結は準備中';
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
    if (q.kind === '未分類FAX') return S.qchoice[q.queue_id] !== undefined || !!String(v.iv || '').trim();
    if (q.kind === SAME) return !!q.same;
    return false;
  }
  function noteOf(q, nv) {
    if (VALUE_KINDS[q.kind] && nv > 1) return 'このコンテナの ' + nv + ' 項目をまとめて確認します。原本を見て、正しい値を選ぶか入力してください。';
    if (q.kind === '値の違い') return FIELD_LABEL[q.field] + ' が出典によって違います。原本を見て、正しい方を選ぶか入力してください。';
    if (q.kind === '手入力') return FIELD_LABEL[q.field] + ' が読めませんでした。原本を見て入力してください。';
    if (q.kind === '写真のCT') return '写真から CT 番号が読めませんでした。写真を見て、どのコンテナか選んでください。';
    if (q.kind === PHOTO_SET) return q.reason_text || '通関用写真が不足しています';     /* エンジンの既存理由文 (reason_text) をそのまま */
    if (q.kind === HOLD) return '受信したメールの書類ですが、どの業者・インボイスか判定できず保留になっています。';
    if (q.kind === SAME) return '写真のない FAX の行と、搬入票のない写真の行が 同じコンテナかもしれません（CT・シールの読み違い）。原本と写真を見て決めてください。';
    return 'どのインボイスの搬入票か判定できませんでした。';
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
    writeAction(a).then(function () { S.qsel = nextQueueId(q); S.zoom = 100; S.rot = 0; render(); toast('「搬入票ではない」にしました（完了 から 元に戻せます）', 'success'); });
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
  function submitQueue(q, special) {
    if (!S.me) { S.qmsg[q.queue_id] = '担当者を選んでください（右上）'; render(); return; }
    var acts = [];
    if (special === 'not_ours') { notHannyuhyo(q, null); return; }
    if (q.kind === SAME) { sameAction(q, 'merge_same'); return; }
    if (VALUE_KINDS[q.kind]) {
      var its = openValueItems(q);
      for (var k = 0; k < its.length; k++) {
        var y = its[k];
        var vals = S.qvals[y.queue_id] || {};
        var v = C01.validate.field(y.field, vals[y.field]);
        if (!v.ok) { S.qmsg[q.queue_id] = FIELD_LABEL[y.field] + ': ' + v.error; render(); return; }
        if (v.warn && !window.confirm(v.warn)) { S.qmsg[q.queue_id] = v.warn; render(); return; }   /* #109 ③ 確認窓 (文言そのまま) → OK なら保存 */
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
      S.qsel = nextQueueId(q); S.zoom = 100; S.rot = 0; render();
    });
  }

  /* ── _actions 書き込み (設計 §5 の形) ── */
  function mkAction(action, f) {
    var a = { schema_version: 1, action_id: actionId(), action: action, iv: f.iv == null ? null : f.iv, ct: f.ct == null ? null : f.ct,
      field: f.field == null ? null : f.field, value: f.value === undefined ? null : f.value, source: f.source == null ? null : f.source,
      by: S.me.email, at: jstNow(), queue_id: f.queue_id || null };
    if (f.override) a.override = [f.override];                 /* #109 ③ CT_CHECKDIGIT_OVERRIDE */
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
  function loadPhotos(iv) {
    return S.src.getJson('photos/' + iv + '.json').then(function (p) { S.photos[iv] = p; }).catch(function () { S.photos[iv] = { containers: [], unassigned: [], docs: [] }; });
  }
  function loadAll() {
    return Promise.all([S.src.getJson('jikkyou.json'), S.src.getJson('queue.json').catch(function () { return { items: [] }; }),
      S.src.getJson('remind.json').catch(function () { return null; }), S.src.getJson('meta.json').catch(function () { return null; })]).then(function (r) {
      S.jik = r[0]; S.queue = r[1]; S.remind = r[2]; S.meta = r[3]; S.lastLoad = new Date();
      return Promise.all(((S.jik && S.jik.ivs) || []).map(function (iv) { return loadPhotos(iv.iv_no); }));
    });
  }
  function poll() {
    var t = (S.info && S.info.today) || new Date().toISOString().slice(0, 10);
    var days = [addDays(t, -1), t];
    var nowDay = jstNow().slice(0, 10);
    if (days.indexOf(nowDay) < 0) days.push(nowDay);
    return S.src.listActions(days).then(function (items) {
      S.actions = items;
      var ids = {};
      items.forEach(function (x) { ids[x.action.action_id] = 1; });
      S.mine = S.mine.filter(function (x) { return !ids[x.action.action_id]; });
      S.lastPoll = new Date();
    }).catch(function () { /* 読めない時は次回 */ });
  }
  function tick() {
    return Promise.all([poll(), loadAll().catch(function () {})]).then(render);
  }

  function render() {
    if (!S.jik) return;
    renderNav();
    if (S.view === 'main') renderMain(); else { $('c01-panel').hidden = true; renderInput(); }
    renderLightbox();
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
      render();
      if (S.timer) clearInterval(S.timer);
      S.timer = setInterval(tick, C01.SOURCE.pollMs);
    }).catch(function (e) {
      $('c01-main').innerHTML = '<div class="c01-fatal"><b>データを読めませんでした</b><p>' + esc(e.message) + '</p><p>_data フォルダ (jikkyou.json · queue.json) があるフォルダを選んでください。</p></div>';
    });
  }
  C01.app = { start: start, render: render, tick: tick, poll: poll };
})();
