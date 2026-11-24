/* ✦ Powered by LEENAI Automation System — C-01 搬入票 TOOL 書類の表示と向き (v0.3.77 · R12Y38 · #382 朴 改善依頼 ① ②)
   - photo.html (写真 + 搬入票 を並べる) · doc.html (📄) で使う 1 か所の書類表示: PDF (その行のページ · pdf.js) · 画像 · Excel (SharePoint で開く)
   - 向き: 「⟲ 90°」 「⟳ 90°」 「180°」 = 画面だけ (原本 · PDF ファイルは変えない · Graph 書き込み 0)。人が回した角度は このブラウザに覚える
     (localStorage 'c01_rotmem' · キー = ファイル sha16 + ページ · 確認・入力 の ⟳ と同じ場所)。保存できない時は覚えないだけで動く
   - 表示の角度 = エンジンの向き (rows[].docs[].rotation · 時計回り) + 人が回した角度 */
'use strict';
window.C01 = window.C01 || {};

(function () {
  var ROTMEM_KEY = 'c01_rotmem';
  function all() { try { return JSON.parse(localStorage.getItem(ROTMEM_KEY) || '{}') || {}; } catch (e) { return {}; } }
  function key(sha, page) { return sha ? String(sha) + '#' + (page || 1) : null; }
  var MEM = {};                                         /* 保存できない時も このページを開いている間は回した角度を使う */
  function get(k) {
    if (!k) return 0;
    if (Object.prototype.hasOwnProperty.call(MEM, k)) return MEM[k];
    var m = all(); return m[k] ? (+m[k] || 0) % 360 : 0;
  }
  function set(k, v) {
    if (!k) return false;
    v = ((Math.round(+v || 0) % 360) + 360) % 360;
    MEM[k] = v;
    var m = all();
    if (v) m[k] = v; else delete m[k];
    var ks = Object.keys(m);
    if (ks.length > 500) ks.slice(0, ks.length - 500).forEach(function (x) { delete m[x]; });
    try { localStorage.setItem(ROTMEM_KEY, JSON.stringify(m)); return true; } catch (e) { return false; }   /* 保存できない時 = 覚えない (画面は回る) */
  }
  C01.rotMem = { key: key, get: get, set: set, KEY: ROTMEM_KEY };

  function esc(s) { return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); }
  var pdfP = null;
  function loadPdfJs() {
    if (window.pdfjsLib) return Promise.resolve(window.pdfjsLib);
    if (pdfP) return pdfP;
    pdfP = new Promise(function (res, rej) {
      var sc = document.createElement('script');
      sc.src = (C01.PDF || {}).lib;
      sc.onload = function () { if (!window.pdfjsLib) return rej(new Error('pdf.js なし')); window.pdfjsLib.GlobalWorkerOptions.workerSrc = C01.PDF.worker; res(window.pdfjsLib); };
      sc.onerror = function () { rej(new Error('pdf.js を読めませんでした')); };
      document.head.appendChild(sc);
    });
    pdfP.catch(function () { pdfP = null; });
    return pdfP;
  }
  C01.loadPdfJs = loadPdfJs;

  /* 角度: エンジン (base) + 人 (覚えた角度) */
  function rotOf(d) { return (((+d.baseRot || 0) + get(key(d.sha16, d.page || 1))) % 360 + 360) % 360; }
  /* 「⟲ 90°」 「⟳ 90°」 「180°」 — 押したら 人の角度を変えて覚える · 戻り値 = 新しい表示角度 */
  function turn(d, delta) {
    var k = key(d.sha16, d.page || 1);
    var cur = get(k);
    var nx = (((cur + delta) % 360) + 360) % 360;
    if (k) set(k, nx);
    else d.memRot = (((+d.memRot || 0) + delta) % 360 + 360) % 360;     /* sha が無い書類 = このページを開いている間だけ */
    return rotOf(d) + (k ? 0 : (+d.memRot || 0));
  }
  function shownRot(d) { return (rotOf(d) + (d.sha16 ? 0 : (+d.memRot || 0))) % 360; }
  function rotBar(id, d) {
    var r = shownRot(d);
    return '<span class="c01-rotbar" id="' + id + '">' +
      '<button class="c01-tool" data-rot="-90" title="左に 90° 回す（画面だけ · 原本は変えない）">⟲ 90°</button>' +
      '<button class="c01-tool" data-rot="90" title="右に 90° 回す（画面だけ · 原本は変えない）">⟳ 90°</button>' +
      '<button class="c01-tool" data-rot="180" title="180° 回す（上下逆さまの時 · 画面だけ）">180°</button>' +
      '<span class="t2 c01-rotnow" title="エンジンの向き + 回した角度（このブラウザに覚えます）">' + (r ? r + '°' : '') + '</span></span>';
  }
  function bindRot(id, d, redraw) {
    var bar = document.getElementById(id);
    if (!bar) return;
    bar.querySelectorAll('[data-rot]').forEach(function (b) { b.onclick = function () { turn(d, +b.getAttribute('data-rot')); redraw(); }; });
  }

  /* box に 1 件を描く。d = { name, ext, page, sha16, baseRot, kindText } · url = blob: (無ければ読み込み中) · err = 読めない理由 */
  function draw(box, d, url, err) {
    if (!box) return;
    var ext = String(d.ext || '').toLowerCase();
    if (err) { box.innerHTML = '<span class="c01-filemiss">' + esc(err) + '</span>'; return; }
    if (/^(xlsx|xlsm|xls|csv)$/.test(ext)) {
      box.innerHTML = '<div class="c01-pv-msg">Excel はここでは表示できません' + (d.row ? '（' + esc(d.row) + ' 行目）' : '') + '<br>' +
        (d.web ? '<a class="ln-btn-ghost" href="' + esc(d.web) + '" target="_blank" rel="noopener">SharePoint で開く</a>' : '') +
        (url ? ' <a class="ln-btn-ghost" href="' + url + '" download="' + esc(d.name) + '">ダウンロード</a>' : '') + '</div>';
      return;
    }
    if (!url) { box.innerHTML = '<span class="c01-pv-load">…</span>'; return; }
    var rot = shownRot(d);
    if (ext === 'pdf') {
      var tok = (box.__tok = (box.__tok || 0) + 1);
      if (!box.firstElementChild || box.firstElementChild.tagName !== 'CANVAS') box.innerHTML = '<span class="c01-pv-load">読み込み中…</span>';
      loadPdfJs().then(function (lib) { return lib.getDocument({ url: url }).promise; }).then(function (doc) {
        var pg = Math.min(Math.max(+d.page || 1, 1), doc.numPages);
        return doc.getPage(pg).then(function (page) {
          if (box.__tok !== tok) return;
          var r = ((rot + (page.rotate || 0)) % 360 + 360) % 360;
          var vp1 = page.getViewport({ scale: 1, rotation: r });
          var w = Math.max(240, box.clientWidth - 16), h = Math.max(240, box.clientHeight - 16);
          var sc = Math.min(w / vp1.width, h / vp1.height) * 2;
          var vp = page.getViewport({ scale: sc, rotation: r });
          var cv = document.createElement('canvas');
          cv.width = vp.width; cv.height = vp.height; cv.className = 'c01-pv-img c01-sd-img';
          cv.setAttribute('data-rot', String(rot));
          cv.style.maxWidth = '100%'; cv.style.maxHeight = '100%';
          return page.render({ canvasContext: cv.getContext('2d'), viewport: vp }).promise.then(function () {
            if (box.__tok !== tok) return;
            box.innerHTML = ''; box.appendChild(cv);
            box.setAttribute('data-pages', String(doc.numPages));
            box.setAttribute('data-page', String(pg));
          });
        });
      }).catch(function (e) { if (box.__tok === tok) box.innerHTML = '<span class="c01-filemiss">' + esc('表示できませんでした: ' + e.message) + '</span>'; });
      return;
    }
    /* 画像: 90° · 270° は幅と高さが入れ替わるので 箱に合わせて縮める */
    box.innerHTML = '<img class="c01-pv-img c01-sd-img" src="' + url + '" alt="書類" data-rot="' + rot + '" style="transform: rotate(' + rot + 'deg)">';
    var im = box.firstElementChild;
    var fit = function () {
      if (!im.naturalWidth) return;
      if (rot % 180) {
        var bw = box.clientWidth || 1, bh = box.clientHeight || 1;
        var s = Math.min(bw / im.naturalHeight, bh / im.naturalWidth, 1);
        im.style.maxWidth = 'none'; im.style.maxHeight = 'none';
        im.style.width = Math.round(im.naturalWidth * s) + 'px'; im.style.height = Math.round(im.naturalHeight * s) + 'px';
      }
    };
    if (im.complete) fit(); else im.onload = fit;
  }
  C01.SideDoc = { draw: draw, rotBar: rotBar, bindRot: bindRot, turn: turn, shownRot: shownRot, esc: esc };
})();
