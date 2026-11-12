/* ✦ Powered by LEENAI Automation System — C-01 搬入票 TOOL 書類ページ (doc.html · v0.3.23 · R7W Part B · photo.html と同じ方式 D-65)
   - 実況表 の 「📄」 を押す → 同じウィンドウの新しいタブ (名前 = 'c01-doc-' + 行キーのハッシュ · アドレスは ?k=ハッシュ だけ)
   - ログインしない · Graph を呼ばない: 元の画面 (window.opener = 同じオリジンの TOOL) に postMessage で頼み、見出しと書類 (Blob) を受け取る
   - 書類 = エンジンの rows[].docs (その行の値の出典 · ファイル + ページ) — PDF は その行のページだけ · 画像はそのまま · Excel は SharePoint で開く
   - 並び: 搬入票 → 計量伝票 → 納品書 · その他 → EIR → Excel (タブ) */
'use strict';
window.C01 = window.C01 || {};

(function () {
  var THEMES = ['dark', 'light', 'leenai', 'focus'];
  var LABEL = { dark: '🌙 ダーク', light: '☀️ ライト', leenai: '🌿 LEENAI', focus: '🎯 FOCUS' };
  var P = { k: '', head: null, idx: 0, files: {}, errs: {}, tries: 0, timer: null, gone: false, scale: 1, pdf: null };

  function $(id) { return document.getElementById(id); }
  function esc(s) { return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); }
  function origin() { return location.origin && location.origin !== 'null' ? location.origin : '*'; }
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

  function msg(text) { $('pv-main').innerHTML = '<div class="c01-pv-msg">' + esc(text) + '</div>'; }
  function setHead() {
    var h = P.head;
    $('pv-head').innerHTML = '<span class="mono c01-pv-iv">' + esc(h.iv) + '</span><span class="mono c01-pv-ct">' + esc(h.ct || '（CT 不明）') + '</span>' +
      '<span class="c01-pv-pk">' + esc([h.packer, h.plant].filter(function (x) { return x && x !== '—'; }).join(' ')) + '</span><span class="c01-pv-n">書類 ' + (h.docs || []).length + '</span>';
    document.title = '書類 ' + (h.ct || '') + ' · ' + h.iv + ' — LEENAI C-01';
  }
  function loadPdfJs() {
    if (window.pdfjsLib) return Promise.resolve(window.pdfjsLib);
    if (P.pdf) return P.pdf;
    P.pdf = new Promise(function (res, rej) {
      var sc = document.createElement('script');
      sc.src = (C01.PDF || {}).lib;
      sc.onload = function () { if (!window.pdfjsLib) return rej(new Error('pdf.js なし')); window.pdfjsLib.GlobalWorkerOptions.workerSrc = C01.PDF.worker; res(window.pdfjsLib); };
      sc.onerror = function () { rej(new Error('pdf.js を読めませんでした')); };
      document.head.appendChild(sc);
    });
    P.pdf.catch(function () { P.pdf = null; });
    return P.pdf;
  }
  function renderPdf(i, d) {
    var box = $('dv-stage');
    loadPdfJs().then(function (lib) { return lib.getDocument({ url: P.files[i] }).promise; }).then(function (doc) {
      var pg = Math.min(Math.max(+d.page || 1, 1), doc.numPages);
      return doc.getPage(pg).then(function (page) {
        if (P.idx !== i) return;
        var rot = ((+d.rot || 0) + (page.rotate || 0)) % 360;
        var vp1 = page.getViewport({ scale: 1, rotation: rot });
        var w = Math.max(320, box.clientWidth - 16), h = Math.max(240, box.clientHeight - 16);
        var sc = Math.min(w / vp1.width, h / vp1.height) * 2;
        var vp = page.getViewport({ scale: sc, rotation: rot });
        var cv = document.createElement('canvas');
        cv.width = vp.width; cv.height = vp.height; cv.className = 'c01-pv-img';
        cv.style.maxWidth = '100%'; cv.style.maxHeight = '100%';
        return page.render({ canvasContext: cv.getContext('2d'), viewport: vp }).promise.then(function () {
          if (P.idx !== i) return;
          box.innerHTML = ''; box.appendChild(cv);
          var n = $('dv-pg'); if (n) n.textContent = 'p' + pg + (doc.numPages > 1 ? ' / ' + doc.numPages + '（この行のページ）' : '');
        });
      });
    }).catch(function (e) { if (P.idx === i) box.innerHTML = '<span class="c01-filemiss">' + esc('表示できませんでした: ' + e.message) + '</span>'; });
  }
  function stage(i, d) {
    if (P.errs[i]) return '<span class="c01-filemiss">' + esc(P.errs[i]) + '</span>';
    if (d.ext === 'xlsx' || d.ext === 'xls' || d.ext === 'xlsm' || d.ext === 'csv') {
      return '<div class="c01-pv-msg">Excel はこのタブでは表示できません<br>' +
        (d.web ? '<a class="ln-btn-ghost" href="' + esc(d.web) + '" target="_blank" rel="noopener">SharePoint で開く</a>' : '') +
        (P.files[i] ? ' <a class="ln-btn-ghost" href="' + P.files[i] + '" download="' + esc(d.name) + '">ダウンロード</a>' : '') + '</div>';
    }
    if (!P.files[i]) return '<span class="c01-pv-load">…</span>';
    if (d.ext === 'pdf') return '<span class="c01-pv-load">読み込み中…</span>';
    return '<img class="c01-pv-img" src="' + P.files[i] + '" alt="書類" style="transform: rotate(' + (+d.rot || 0) + 'deg)">';
  }
  function render() {
    var h = P.head;
    if (!h) return;
    setHead();
    var n = (h.docs || []).length;
    if (!n) { msg('この行の出典書類はありません'); return; }
    var i = ((P.idx % n) + n) % n;
    P.idx = i;
    var d = h.docs[i];
    $('pv-main').innerHTML =
      '<div class="c01-pv-bar c01-dv-tabs">' + h.docs.map(function (x, j) {
        return '<button class="c01-pv-kind' + (j === i ? ' big on' : '') + '" data-go="' + j + '" title="' + esc(x.name) + '">' + esc(x.kindText) + (x.page ? ' p' + x.page : '') + '</button>';
      }).join(' ') + '<span class="c01-pv-name">' + esc(d.name) + '</span><span class="t2" id="dv-pg"></span>' +
      (d.fields && d.fields.length ? '<span class="t2">値: ' + esc(d.fields.join('・')) + '</span>' : '') + '</div>' +
      '<div class="c01-pv-stage-row"><button class="c01-pv-nav" id="pv-prev" aria-label="前の書類">‹</button>' +
      '<div class="c01-pv-stage" id="dv-stage">' + stage(i, d) + '</div>' +
      '<button class="c01-pv-nav" id="pv-next" aria-label="次の書類">›</button></div>';
    P.scale = 1;
    $('pv-prev').onclick = function () { go(P.idx - 1); };
    $('pv-next').onclick = function () { go(P.idx + 1); };
    document.querySelectorAll('[data-go]').forEach(function (b) { b.onclick = function () { go(+b.getAttribute('data-go')); }; });
    $('dv-stage').onwheel = function (e) {
      var el = $('dv-stage').firstElementChild;
      e.preventDefault(); P.scale = Math.max(1, Math.min(4, P.scale * (e.deltaY < 0 ? 1.15 : 1 / 1.15)));
      if (el && el.tagName !== 'DIV') el.style.transform = 'scale(' + P.scale + ')' + (el.tagName === 'IMG' ? ' rotate(' + (+d.rot || 0) + 'deg)' : '');
    };
    if (d.ext === 'pdf' && P.files[i] && !P.errs[i]) renderPdf(i, d);
  }
  function go(i) { P.idx = i; render(); }
  document.addEventListener('keydown', function (e) {
    if (!P.head) return;
    if (e.key === 'ArrowLeft') { go(P.idx - 1); e.preventDefault(); }
    if (e.key === 'ArrowRight') { go(P.idx + 1); e.preventDefault(); }
  });

  /* ── 元の画面とのやりとり (photo.js と同じ) ── */
  function ask() {
    if (P.head || P.gone) return;
    var op = null;
    try { op = window.opener; } catch (e) { op = null; }
    if (!op || op.closed) { P.gone = true; msg('元の画面 (実況表) が見つかりません — 実況表 から 📄 を押して開いてください（このタブではログインしません）'); return; }
    if (P.tries++ > 30) { msg('元の画面から書類を受け取れませんでした — 実況表 から 📄 をもう一度押してください'); return; }
    try { op.postMessage({ t: 'c01-doc-req', k: P.k }, origin()); } catch (e) { /* なし */ }
    P.timer = setTimeout(ask, 1000);
  }
  window.addEventListener('message', function (e) {
    var d = e.data;
    var op = null;
    try { op = window.opener; } catch (x) { op = null; }
    if (!d || typeof d !== 'object' || e.source !== op || e.origin !== location.origin || d.k !== P.k) return;
    if (d.t === 'c01-doc-wait') return;
    if (d.t === 'c01-doc-err') { clearTimeout(P.timer); P.gone = true; msg(d.msg || '書類を表示できません'); return; }
    if (d.t === 'c01-doc-head') {
      clearTimeout(P.timer);
      Object.keys(P.files).forEach(function (i) { try { URL.revokeObjectURL(P.files[i]); } catch (x) { /* なし */ } });
      P.head = d.head || { docs: [] }; P.files = {}; P.errs = {};
      render();
      return;
    }
    if (d.t === 'c01-doc-file' && P.head) {
      var i = +d.i;
      if (d.blob && typeof Blob !== 'undefined' && d.blob instanceof Blob) P.files[i] = URL.createObjectURL(d.blob);
      else P.errs[i] = d.err || '読めませんでした';
      if (d.web && P.head.docs[i]) P.head.docs[i].web = d.web;
      if (i === P.idx) render();
      return;
    }
    if (d.t === 'c01-doc-go' && P.head) go(+d.i || 0);
  });
  window.addEventListener('DOMContentLoaded', function () {
    var I = C01.TOOL_INFO || {};
    $('pv-ver').textContent = I.version ? 'v' + I.version : '';
    $('pv-sys').textContent = (I.sys || 'C-01') + ' 書類';
    $('pv-theme').onclick = nextTheme;
    applyTheme(curTheme());
    var q = new URLSearchParams(location.search);
    P.k = String(q.get('k') || '').replace(/[^0-9a-f]/g, '').slice(0, 8);
    if (!P.k) { msg('書類の指定がありません — 実況表 から 📄 を押して開いてください'); return; }
    ask();
  });
})();
