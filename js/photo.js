/* ✦ Powered by LEENAI Automation System — C-01 搬入票 TOOL 写真ページ (photo.html · v0.3.13 · R7L Part E · D-65)
   - 実況表 · 確認・入力 で 写真 を押す → 同じウィンドウの新しいタブ (名前 = 'c01-photo-' + 行キーのハッシュ · アドレスは ?k=ハッシュ だけ)
   - ログインしない · Graph を呼ばない: 元の画面 (window.opener = 同じオリジンの TOOL) に postMessage で頼み、見出しと写真 (Blob) を受け取る
     (LEENAI_COMMON のトークンは元のタブのメモリだけ — 新しいタブとは共有されないため)
   - 見出し = IV · CT · 業者 · 枚数 / 写真を大きく + サムネイル帯 + ← → キー · 写真の種類 · 4 テーマ (leenai_theme) */
'use strict';
window.C01 = window.C01 || {};

(function () {
  var THEMES = ['dark', 'light', 'leenai', 'focus'];
  var LABEL = { dark: '🌙 ダーク', light: '☀️ ライト', leenai: '🌿 LEENAI', focus: '🎯 FOCUS' };
  /* 写真の種類 (エンジン photo.kind = G4 の種類 · 将来 fill = 積込の読み取り) → 表示。分からない種類は出さない (空) */
  var KIND_TEXT = { empty: '空コンテナ', partial: '積込中', full: 'FULL', closed: '扉閉め', door: '扉', seal: 'SEAL', cotecna: 'COTECNA',
    tare: 'TARE', side: '側面 CT', doc: '書類', insp: '検査', other: 'その他' };
  var G4 = { interior: 'empty', cargo: 'partial', door: 'door', seal: 'seal', cotecna: 'cotecna', tare_plate: 'tare', side_ct: 'side',
    doc_eir: 'doc', doc_weight: 'doc', doc_other: 'doc', radiation: 'insp', inspection: 'insp', other: 'other' };
  var FILL = { empty: 'empty', partial: 'partial', full: 'full', door_closed: 'closed', closed: 'closed', door_open: 'door' };
  function photoKind(p) {
    p = p || {};
    var f = String(p.fill || '').toLowerCase();
    var k = FILL[f] || '';
    if (!k) {
      var l = String(p.kind || p.label || '');
      var ll = l.toLowerCase();
      k = G4[ll] || '';
      if (!k && l) {                                   /* 日本語のラベル (旧 PHOTO · 試験データ) */
        if (/cotecna/i.test(l)) k = 'cotecna';
        else if (/シール|seal/i.test(l)) k = 'seal';
        else if (/100\s*%|full/i.test(l)) k = 'full';
        else if (/積込|積み込み/.test(l)) k = 'partial';
        else if (/空|床/.test(l)) k = 'empty';
        else if (/扉.*閉|閉.*扉/.test(l)) k = 'closed';
        else if (/扉|ドア/.test(l)) k = 'door';
        else if (/tare/i.test(l)) k = 'tare';
      }
    }
    return k ? { key: k, text: KIND_TEXT[k] } : { key: '', text: '' };
  }
  C01.photoKind = photoKind;

  var P = { k: '', idx: 0, head: null, imgs: {}, errs: {}, tries: 0, timer: null, scale: 1, gone: false };
  C01.photoPage = P;

  function $(id) { return document.getElementById(id); }
  function esc(s) { return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); }
  function origin() { return location.origin && location.origin !== 'null' ? location.origin : '*'; }

  /* ── テーマ (LEENAI_COMMON と同じ localStorage leenai_theme · 他のタブで変えたら追う) ── */
  function curTheme() { var t = 'dark'; try { t = localStorage.getItem('leenai_theme') || 'dark'; } catch (e) { /* なし */ } return THEMES.indexOf(t) >= 0 ? t : 'dark'; }
  function applyTheme(t) { document.documentElement.setAttribute('data-theme', t); var b = $('pv-theme'); if (b) b.textContent = LABEL[t]; }
  function nextTheme() {
    var cur = document.documentElement.getAttribute('data-theme') || 'dark';
    var nx = THEMES[(THEMES.indexOf(cur) + 1) % THEMES.length];
    try { localStorage.setItem('leenai_theme', nx); } catch (e) { /* なし */ }
    applyTheme(nx);
  }
  applyTheme(curTheme());
  window.addEventListener('storage', function (e) { if (e.key === 'leenai_theme') applyTheme(curTheme()); });

  function msg(text) {
    $('pv-main').innerHTML = '<div class="c01-pv-msg">' + esc(text) + '</div>';
  }
  function setHead() {
    var h = P.head;
    if (!h) return;
    $('pv-head').innerHTML = '<span class="mono c01-pv-iv">' + esc(h.iv) + '</span><span class="mono c01-pv-ct">' + esc(h.ct || '（CT 不明）') + '</span>' +
      '<span class="c01-pv-pk">' + esc([h.packer, h.plant].filter(function (x) { return x && x !== '—'; }).join(' ')) + '</span><span class="c01-pv-n">' + (+h.n || 0) + '枚</span>';
    document.title = '写真 ' + (h.ct || '') + ' · ' + h.iv + ' — LEENAI C-01';
  }
  function chip(k, cls) { return k.text ? '<span class="c01-pv-kind k-' + k.key + (cls ? ' ' + cls : '') + '">' + esc(k.text) + '</span>' : ''; }
  function imgOrMsg(i, cls) {
    if (P.imgs[i]) return '<img class="' + cls + '" src="' + P.imgs[i] + '" alt="写真 ' + (i + 1) + '">';
    if (P.errs[i]) return '<span class="c01-filemiss">' + esc(P.errs[i]) + '</span>';
    return '<span class="c01-pv-load">…</span>';
  }
  function render() {
    var h = P.head;
    if (!h) return;
    setHead();
    var n = (h.photos || []).length;
    if (!n) { msg('このコンテナの写真はまだありません'); return; }
    var i = ((P.idx % n) + n) % n;
    P.idx = i;
    var ph = h.photos[i], k = photoKind(ph);
    $('pv-main').innerHTML =
      '<div class="c01-pv-bar"><span class="c01-pv-pos" id="pv-pos">' + (i + 1) + ' / ' + n + '</span>' + chip(k, 'big') +
      '<span class="c01-pv-name">' + esc(ph.label && !k.text ? ph.label : '') + '</span></div>' +
      '<div class="c01-pv-stage-row"><button class="c01-pv-nav" id="pv-prev" aria-label="前の写真">‹</button>' +
      '<div class="c01-pv-stage" id="pv-stage">' + imgOrMsg(i, 'c01-pv-img') + '</div>' +
      '<button class="c01-pv-nav" id="pv-next" aria-label="次の写真">›</button></div>' +
      '<div class="c01-pv-strip">' + h.photos.map(function (q, j) {
        var kk = photoKind(q);
        return '<button class="c01-pv-th' + (j === i ? ' on' : '') + '" data-go="' + j + '" title="' + esc((j + 1) + (kk.text ? ' · ' + kk.text : '')) + '">' +
          imgOrMsg(j, 'c01-pv-thimg') + chip(kk) + '</button>';
      }).join('') + '</div>';
    P.scale = 1;
    $('pv-prev').onclick = function () { go(P.idx - 1); };
    $('pv-next').onclick = function () { go(P.idx + 1); };
    document.querySelectorAll('[data-go]').forEach(function (b) { b.onclick = function () { go(+b.getAttribute('data-go')); }; });
    var img = document.querySelector('.c01-pv-img');
    $('pv-stage').onwheel = function (e) { e.preventDefault(); P.scale = Math.max(1, Math.min(4, P.scale * (e.deltaY < 0 ? 1.15 : 1 / 1.15))); if (img) img.style.transform = 'scale(' + P.scale + ')'; };
    var on = document.querySelector('.c01-pv-th.on');
    if (on && on.scrollIntoView) on.scrollIntoView({ block: 'nearest', inline: 'nearest' });
  }
  function go(i) { P.idx = i; render(); }

  document.addEventListener('keydown', function (e) {
    if (!P.head) return;
    if (e.key === 'ArrowLeft') { go(P.idx - 1); e.preventDefault(); }
    if (e.key === 'ArrowRight') { go(P.idx + 1); e.preventDefault(); }
  });

  /* ── 元の画面とのやりとり ── */
  function ask() {
    if (P.head || P.gone) return;
    var op = null;
    try { op = window.opener; } catch (e) { op = null; }
    if (!op || op.closed) { P.gone = true; msg('元の画面 (実況表) が見つかりません — 実況表 から 写真 を押して開いてください（このタブではログインしません）'); return; }
    if (P.tries++ > 30) { msg('元の画面から写真を受け取れませんでした — 実況表 から 写真 をもう一度押してください'); return; }
    try { op.postMessage({ t: 'c01-photo-req', k: P.k }, origin()); } catch (e) { /* なし */ }
    P.timer = setTimeout(ask, 1000);
  }
  window.addEventListener('message', function (e) {
    var d = e.data;
    var op = null;
    try { op = window.opener; } catch (x) { op = null; }
    if (!d || typeof d !== 'object' || e.source !== op || e.origin !== location.origin || d.k !== P.k) return;   /* 元の画面からだけ */
    if (d.t === 'c01-photo-wait') return;                              /* 実況表がまだ読み込み中 → ask が続ける */
    if (d.t === 'c01-photo-err') { clearTimeout(P.timer); P.gone = true; msg(d.msg || '写真を表示できません'); return; }
    if (d.t === 'c01-photo-head') {
      clearTimeout(P.timer);
      Object.keys(P.imgs).forEach(function (i) { try { URL.revokeObjectURL(P.imgs[i]); } catch (x) { /* なし */ } });
      P.head = d.head || { photos: [] }; P.imgs = {}; P.errs = {};
      render();
      return;
    }
    if (d.t === 'c01-photo-img' && P.head) {
      var i = +d.i;
      if (d.blob && typeof Blob !== 'undefined' && d.blob instanceof Blob) P.imgs[i] = URL.createObjectURL(d.blob);
      else P.errs[i] = d.err || '読めませんでした';
      render();
      return;
    }
    if (d.t === 'c01-photo-go' && P.head) { go(+d.i || 0); }
  });

  window.addEventListener('DOMContentLoaded', function () {
    var I = C01.TOOL_INFO || {};
    $('pv-ver').textContent = I.version ? 'v' + I.version : '';
    $('pv-sys').textContent = (I.sys || 'C-01') + ' 写真';
    $('pv-theme').onclick = nextTheme;
    applyTheme(curTheme());
    var q = new URLSearchParams(location.search);
    P.k = String(q.get('k') || '').replace(/[^0-9a-f]/g, '').slice(0, 8);
    P.idx = +(q.get('i') || 0) || 0;
    if (!P.k) { msg('写真の指定がありません — 実況表 から 写真 を押して開いてください'); return; }
    ask();
  });
})();
