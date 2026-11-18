/* ✦ Powered by LEENAI Automation System — C-01 搬入票 TOOL 写真ページ (photo.html · v0.3.13 · R7L Part E · D-65)
   - 実況表 · 確認・入力 で 写真 を押す → 同じウィンドウの新しいタブ (名前 = 'c01-photo-' + 行キーのハッシュ · アドレスは ?k=ハッシュ だけ)
   - ログインしない · Graph を呼ばない: 元の画面 (window.opener = 同じオリジンの TOOL) に postMessage で頼み、見出しと写真 (Blob) を受け取る
     (LEENAI_COMMON のトークンは元のタブのメモリだけ — 新しいタブとは共有されないため)
   - 見出し = IV · CT · 業者 · 枚数 / 写真を大きく + サムネイル帯 + ← → キー · 写真の種類 · 4 テーマ (leenai_theme)
   - v0.3.51 (R10V · #308): 「拡大・補正」 = 押した時だけ この画面 (canvas) で作る確認用の画像。番号の枠 (エンジン box · 無ければ写真全体) を切って
     まっすぐにし、明るさ · コントラスト (CLAHE · clip 1.5) だけ。数字の形を変える処理 (生成 AI · 超解像 · ぼけ戻し) はしない。
     鮮明化は 0 (R10V 20 枚の測定: clip 2.0 + 鮮明化 0.5 = 刻印の地の模様が強まり 読み取りが 3 枚で変わった · clip 1.5 + 鮮明化 0 = 数字の違い 0)
     原本は常に横に並べる · 「補正画像 · 判断は原本と搬入票で」 · 元のファイルは変えない · AI 費用 0
   - v0.3.55 (R10Y · ZHAN 提案 · #313): 大きい写真 · 拡大・補正 の 2 枚 = 拡大 (ホイール · ＋− · ダブルクリック 2.5 倍 · 指 2 本 · 1〜6 倍) + 引っ張って移動 ·
     矢印キー (拡大中 = 移動 · 1 倍 = 前へ / 次へ) · 「全体表示」 · 次の写真へ = 元の大きさ (js/zoompan.js · CSS transform だけ)。2 枚は同じ倍率 · 同じ位置 */
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

  var P = { k: '', idx: 0, head: null, imgs: {}, errs: {}, tries: 0, timer: null, scale: 1, gone: false, enh: -1, enhMs: 0, zp: null, zs: null };
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
      '<span class="c01-pv-name">' + esc(ph.label && !k.text ? ph.label : '') + '</span>' +
      (C01.zoomBar ? C01.zoomBar('pv-z') : '') +
      '<button class="c01-pv-enhbtn' + (P.enh === i ? ' on' : '') + '" id="pv-enh"' + (P.imgs[i] ? '' : ' disabled') + ' title="番号の所を切って明るさ・コントラストだけ整えた確認用の画像（原本と並べて表示 · 元のファイルは変えない）">拡大・補正</button></div>' +
      '<div class="c01-pv-stage-row"><button class="c01-pv-nav" id="pv-prev" aria-label="前の写真">‹</button>' +
      (P.enh === i ? '<div class="c01-pv-stage enh" id="pv-stage">' + imgOrMsg(i, 'c01-pv-img c01-pv-src0') +       /* 拡大・補正 中 = 大きい写真の所に 原本 · 補正 を並べる (元の img は隠して canvas の元に使う) */
        '<div class="c01-pv-enh" id="pv-enhbox"><div class="c01-pv-enhpair">' +
        '<figure class="c01-pv-enhfig"><figcaption>原本</figcaption><canvas id="pv-enh-orig"></canvas></figure>' +
        '<figure class="c01-pv-enhfig enh"><figcaption>補正画像 · 判断は原本と搬入票で</figcaption><div class="c01-pv-enhwrap"><canvas id="pv-enh-out"></canvas>' +
        '<span class="c01-pv-enhmark">補正画像 · 判断は原本と搬入票で</span></div></figure></div>' + valsTable(h.vals) + '</div></div>'
        : '<div class="c01-pv-stage" id="pv-stage">' + imgOrMsg(i, 'c01-pv-img') + '</div>') +
      '<button class="c01-pv-nav" id="pv-next" aria-label="次の写真">›</button></div>' +
      '<div class="c01-pv-strip">' + h.photos.map(function (q, j) {
        var kk = photoKind(q);
        return '<button class="c01-pv-th' + (j === i ? ' on' : '') + '" data-go="' + j + '" title="' + esc((j + 1) + (kk.text ? ' · ' + kk.text : '')) + '">' +
          imgOrMsg(j, 'c01-pv-thimg') + chip(kk) + '</button>';
      }).join('') + '</div>';
    P.scale = 1;
    $('pv-enh').onclick = function () { P.enh = P.enh === P.idx ? -1 : P.idx; P.zs = null; render(); };
    if (P.enh === i) drawEnh(i);
    $('pv-prev').onclick = function () { go(P.idx - 1); };
    $('pv-next').onclick = function () { go(P.idx + 1); };
    document.querySelectorAll('[data-go]').forEach(function (b) { b.onclick = function () { go(+b.getAttribute('data-go')); }; });
    /* v0.3.55 (R10Y · #313): 拡大 · 移動 — 写真が届いて描き直しても 同じ写真 · 同じ表示なら倍率 · 位置を保つ (次の写真 · 閉じる = 元の大きさ) */
    var img = document.querySelector('.c01-pv-img'), zkey = (P.enh === i ? 'e' : 'p') + i;
    var zst = P.enh === i ? document.querySelector('#pv-enhbox .c01-pv-enhpair') : $('pv-stage');
    var ztg = P.enh === i ? [$('pv-enh-orig'), $('pv-enh-out')] : [img];
    var keep = P.zs && P.zs.key === zkey ? P.zs : null;
    P.zp = null;
    if (C01.ZoomPan && zst && ztg.filter(Boolean).length) {
      P.zp = new C01.ZoomPan(zst, ztg, { onSwipe: function (d) { go(P.idx + d); }, onChange: function (s) { P.zs = { key: zkey, s: s, fx: P.zp ? P.zp.fx : 0, fy: P.zp ? P.zp.fy : 0 }; } });
      if (keep) { P.zp.s = keep.s; P.zp.fx = keep.fx; P.zp.fy = keep.fy; }
      C01.zoomBind(P.zp, 'pv-z');
    }
    var on = document.querySelector('.c01-pv-th.on');
    if (on && on.scrollIntoView) on.scrollIntoView({ block: 'nearest', inline: 'nearest' });
  }
  function go(i) { P.idx = i; P.enh = -1; P.zs = null; render(); }

  /* ── v0.3.51 (R10V · #308) 拡大・補正 ── */
  var ENH = { MAX_EDGE: 1600, ZOOM_MAX: 3, MARGIN: 0.25, MIN_PAD: 12, TILES: 8, CLIP: 1.5, SHARP: 0 };
  /* 切る範囲 (エンジン field_box と同じ 千分率 x0..x1 · y0..y1 · 余白 25%) · 無ければ全体 */
  function cropRect(w, h, box) {
    if (!box || box.found === false) return { x: 0, y: 0, w: w, h: h, rot: 0, whole: true };
    var c = function (v) { return Math.max(0, Math.min(1000, +v || 0)); };
    var x0 = c(box.x0) * w / 1000, x1 = c(box.x1) * w / 1000, y0 = c(box.y0) * h / 1000, y1 = c(box.y1) * h / 1000;
    if (x1 - x0 < 3 || y1 - y0 < 3) return { x: 0, y: 0, w: w, h: h, rot: 0, whole: true };
    var px = Math.max(ENH.MIN_PAD, (x1 - x0) * ENH.MARGIN), py = Math.max(ENH.MIN_PAD, (y1 - y0) * ENH.MARGIN);
    var a = Math.max(0, Math.floor(x0 - px)), b = Math.max(0, Math.floor(y0 - py));
    var rr = +box.text_rotation || +box.rot || 0, rot = [0, 90, 180, 270].indexOf(rr) >= 0 ? rr : 0;
    return { x: a, y: b, w: Math.min(w, Math.ceil(x1 + px)) - a, h: Math.min(h, Math.ceil(y1 + py)) - b, rot: rot, whole: false };
  }
  /* 切った範囲 → canvas (まっすぐに · 大きさ = 長い辺 MAX_EDGE まで · 切った時は 3 倍まで拡大) */
  function drawCrop(cv, img, r) {
    var sc = Math.min(r.whole ? 1 : ENH.ZOOM_MAX, ENH.MAX_EDGE / Math.max(r.w, r.h));
    var dw = Math.max(1, Math.round(r.w * sc)), dh = Math.max(1, Math.round(r.h * sc));
    var turn = r.rot % 180 !== 0;
    cv.width = turn ? dh : dw; cv.height = turn ? dw : dh;
    var g = cv.getContext('2d');
    g.save();
    g.translate(cv.width / 2, cv.height / 2);
    g.rotate(-r.rot * Math.PI / 180);                /* 文字の回り (text_rotation) を戻す */
    g.imageSmoothingEnabled = true; g.imageSmoothingQuality = 'high';
    g.drawImage(img, r.x, r.y, r.w, r.h, -dw / 2, -dh / 2, dw, dh);
    g.restore();
    return g;
  }
  /* 明るさ (Y) だけ: CLAHE (タイル 8×8 · clip 1.5 · 双線形) → 鮮明化 (3×3 ぼかしとの差 × SHARP · 今は 0 = しない) · 色は Y の比で戻す。形を作る処理なし */
  function enhanceData(d, w, h) {
    var n = w * h, Y = new Float32Array(n), i, j;
    for (i = 0; i < n; i++) Y[i] = 0.299 * d[i * 4] + 0.587 * d[i * 4 + 1] + 0.114 * d[i * 4 + 2];
    var T = ENH.TILES, tw = w / T, th = h / T, maps = [];
    for (var ty = 0; ty < T; ty++) for (var tx = 0; tx < T; tx++) {
      var xa = Math.floor(tx * tw), xb = Math.max(xa + 1, Math.floor((tx + 1) * tw)), ya = Math.floor(ty * th), yb = Math.max(ya + 1, Math.floor((ty + 1) * th));
      var hist = new Float32Array(256), cnt = 0;
      for (j = ya; j < Math.min(yb, h); j++) for (i = xa; i < Math.min(xb, w); i++) { hist[Math.min(255, Y[j * w + i] | 0)]++; cnt++; }
      var lim = Math.max(1, ENH.CLIP * cnt / 256), ex = 0;
      for (i = 0; i < 256; i++) if (hist[i] > lim) { ex += hist[i] - lim; hist[i] = lim; }
      var add = ex / 256, m = new Float32Array(256), acc = 0;
      for (i = 0; i < 256; i++) { acc += hist[i] + add; m[i] = cnt ? acc * 255 / cnt : i; }
      maps.push(m);
    }
    var Z = new Float32Array(n);
    for (j = 0; j < h; j++) {
      var gy = Math.min(T - 1, Math.max(0, j / th - 0.5)), y0 = Math.floor(gy), y1 = Math.min(T - 1, y0 + 1), fy = gy - y0;
      for (i = 0; i < w; i++) {
        var gx = Math.min(T - 1, Math.max(0, i / tw - 0.5)), x0 = Math.floor(gx), x1 = Math.min(T - 1, x0 + 1), fx = gx - x0, v = Math.min(255, Y[j * w + i] | 0);
        Z[j * w + i] = (maps[y0 * T + x0][v] * (1 - fx) + maps[y0 * T + x1][v] * fx) * (1 - fy) + (maps[y1 * T + x0][v] * (1 - fx) + maps[y1 * T + x1][v] * fx) * fy;
      }
    }
    for (j = 0; j < h; j++) for (i = 0; i < w; i++) {
      var s = 0, c = 0;
      for (var dy = -1; dy <= 1; dy++) for (var dx = -1; dx <= 1; dx++) {
        var yy = j + dy, xx = i + dx;
        if (yy >= 0 && yy < h && xx >= 0 && xx < w) { s += Z[yy * w + xx]; c++; }
      }
      var k = j * w + i, o = Math.max(0, Math.min(255, Z[k] + ENH.SHARP * (Z[k] - s / c))), f = Y[k] > 0.5 ? o / Y[k] : 0;
      for (var ch = 0; ch < 3; ch++) d[k * 4 + ch] = Y[k] > 0.5 ? Math.max(0, Math.min(255, d[k * 4 + ch] * f)) : o;
    }
    return d;
  }
  C01.photoEnhance = { cropRect: cropRect, enhanceData: enhanceData, drawCrop: drawCrop, ENH: ENH };
  function drawEnh(i) {
    var src = document.querySelector('.c01-pv-img'), a = $('pv-enh-orig'), b = $('pv-enh-out');
    if (!src || !a || !b) return;
    var run = function () {
      var now = function () { return (window.performance && performance.now) ? performance.now() : Date.now(); };
      var t0 = now();
      var ph = (P.head.photos || [])[i] || {}, r = cropRect(src.naturalWidth, src.naturalHeight, ph.box);
      drawCrop(a, src, r);
      var g = drawCrop(b, src, r), im = g.getImageData(0, 0, b.width, b.height);
      enhanceData(im.data, b.width, b.height);
      g.putImageData(im, 0, 0);
      P.enhMs = Math.round(now() - t0);
      var bx = $('pv-enhbox');
      if (bx) { bx.setAttribute('data-ms', P.enhMs); bx.setAttribute('data-whole', r.whole ? '1' : '0'); bx.setAttribute('data-done', '1'); }
    };
    if (src.complete && src.naturalWidth) run(); else src.onload = run;
  }
  /* 値の並び: エンジンの値 · 出処 (搬入票 · 写真 …) — エンジンの値と違う文字だけ赤 */
  function diffHtml(v, base) {
    v = String(v || ''); base = String(base || '');
    if (!base) return esc(v);
    var out = '';
    for (var q = 0; q < v.length; q++) out += v[q] === base[q] ? esc(v[q]) : '<b class="c01-pv-dif">' + esc(v[q]) + '</b>';
    return out;
  }
  function valsTable(vals) {
    if (!vals) return '';
    var rows = [['ct', 'CT'], ['seal', 'シール']].filter(function (x) { return vals[x[0]] && (vals[x[0]].engine || (vals[x[0]].srcs || []).length); });
    if (!rows.length) return '<p class="c01-pv-enhnote">値の比較はありません（エンジンの値なし）</p>';
    return '<table class="c01-pv-vals"><tbody>' + rows.map(function (x) {
      var v = vals[x[0]];
      return '<tr><th>' + x[1] + '</th><td><span class="c01-pv-src">エンジン</span><span class="mono">' + esc(v.engine || '—') + '</span></td>' +
        (v.srcs || []).map(function (s) { return '<td><span class="c01-pv-src">' + esc(s.src) + '</span><span class="mono">' + diffHtml(s.value, v.engine) + '</span></td>'; }).join('') + '</tr>';
    }).join('') + '</tbody></table>';
  }
  C01.photoValsTable = valsTable;

  document.addEventListener('keydown', function (e) {
    if (!P.head) return;
    if (P.zp && P.zp.keyHandled(e)) return;                            /* v0.3.55: 拡大中の矢印 = 移動 */
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
