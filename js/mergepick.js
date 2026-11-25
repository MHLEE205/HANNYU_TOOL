/* ✦ Powered by LEENAI Automation System — v0.3.80 (R12Y51 · 決定 #399): 「他の行とまとめる」 — 画面なしの計算だけ (node で試験)
   ・ボタンを出す行: 枠外 (枠なし) · SLOT_CONFLICT · 受信中 · 書類だけの行 · 写真だけの行 (入力済 の行は出さない)
   ・まとめる相手の候補: 同じ IV · 同じ業者 (エンジン meta.merge_pick.allow = slot_allow の業者も)
     おすすめ順 = N/W 同じ · シールの数字 同じ (前の文字だけ違う · 1 文字違い は印) · CT 1〜3 文字違い (自動補正の行は 直す前に読んだ CT でも) · 作業日 同じ
   ・まとめ方: エンジンの merge_rows (書類だけの行 → 相手の行に 参考 として付く · 相手の値と状態はそのまま · 「まとめを元に戻す」)
     まとめ先 = 枠のある行 (行が 2 つとも 書類だけ の時) / 写真のある行 (片方だけ 書類だけ の時)。写真のある行どうし = まとめられない
   ・まとめた後 (決定 #399): まとめ先が 自動OK = 自動OK のまま (値の違いは 情報だけ) · 確認済 = その値のまま · 再確認 = まとめた行の値と 一緒に 1 枚で確認
   ・入力済 (Compass入力 で固定) の行は まとめる側にできない (#307)。値の出どころにはしない (#239 · 最後の検査はエンジン)。 */
(function (root) {
  'use strict';
  var FIELDS = ['ct', 'seal', 'n_w', 't_w', 'bales', 'work_date'];
  var WARN = ['seal', 'n_w', 't_w'];

  function txt(v) { return String(v == null ? '' : v).toUpperCase().replace(/[\s\-‐－]/g, ''); }
  function num(v) {
    if (v == null || v === '') return null;
    var t = String(v).replace(/[,，\s]/g, '').replace(/KG$/i, '');
    return /^-?\d+(\.\d+)?$/.test(t) ? parseFloat(t) : null;
  }
  function digits(v) { return String(v == null ? '' : v).replace(/\D/g, ''); }
  /* 同じ長さ = 違う文字の数 · 長さ違い = 大きい数 */
  function hdist(a, b) {
    if (!a || !b) return 99;
    if (a.length !== b.length) return 99;
    var d = 0;
    for (var i = 0; i < a.length; i++) if (a.charAt(i) !== b.charAt(i)) d++;
    return d;
  }
  function same(fd, a, b) {
    if (a == null || a === '' || b == null || b === '') return null;
    if (fd === 'n_w' || fd === 't_w' || fd === 'g_w' || fd === 'bales') { var x = num(a), y = num(b); return x != null && y != null ? x === y : txt(a) === txt(b); }
    return txt(a) === txt(b);
  }
  function photosOf(r) { return !!(r.has_photos || r.photos); }
  function docOnly(r) { return !!r.has_docs && !photosOf(r); }

  /* opts: { st: function(r) → 表示の状態, vals: function(r) → {ct, seal, ...} (人の値を含む), frozen: function(r) → bool } */
  function eligible(r, opts) {
    if (!r || !r.container_id || (opts.frozen && opts.frozen(r))) return false;
    var st = opts.st(r);
    return !r.slot_guid || (r.reasons || []).indexOf('SLOT_CONFLICT') >= 0 || st === '受信中' ||
      (!!r.has_docs !== photosOf(r));
  }
  function packerOk(a, b, allow) {
    if (!a || !b) return a === b;
    if (a === b) return true;
    return ((allow || {})[a] || []).indexOf(b) >= 0 || ((allow || {})[b] || []).indexOf(a) >= 0;
  }
  function score(row, y, opts) {
    var a = opts.vals(row), b = opts.vals(y), s = 0, marks = [];
    if (same('n_w', a.n_w, b.n_w)) { s += 3; marks.push('nw'); }
    var da = digits(a.seal), db = digits(b.seal);
    if (da && db) {
      if (da === db) { s += 3; marks.push(txt(a.seal) === txt(b.seal) ? 'seal' : 'seal_prefix'); }
      else if (hdist(da, db) === 1) { s += 1.5; marks.push('seal1'); }
    }
    var cts = [txt(a.ct)].concat((row.ct_read || []).map(txt)), ctb = [txt(b.ct)].concat((y.ct_read || []).map(txt));
    var best = 99;
    cts.forEach(function (x) { ctb.forEach(function (z) { if (x && z) best = Math.min(best, hdist(x, z)); }); });
    if (best >= 1 && best <= 3) { s += 4 - best; marks.push('ct' + best); }
    if (best === 0) { s += 3; marks.push('ct0'); }
    if (same('work_date', a.work_date, b.work_date)) { s += 1; marks.push('wd'); }
    return { score: s, marks: marks, ctDist: best };
  }
  /* 候補 (おすすめ順) — 同じ IV · 同じ業者 (slot_allow 含む) · 自分以外 */
  function candidates(iv, row, opts) {
    var out = [];
    (iv.rows || []).forEach(function (y, i) {
      if (!y.container_id || y.container_id === row.container_id) return;
      if (opts.hidden && opts.hidden(y)) return;
      if (!packerOk(row.packer, y.packer, opts.allow)) return;
      var sc = score(row, y, opts);
      out.push({ r: y, no: y.no || (i + 1), score: sc.score, marks: sc.marks, ctDist: sc.ctDist, idx: i });
    });
    out.sort(function (p, q) { return q.score - p.score || p.idx - q.idx; });
    return out;
  }
  /* まとめ方: from (書類だけ · 消える方) → into (残る方) · block = まとめられない理由 · warn = 別のコンテナかもしれない (無いと押せない チェック) */
  function plan(row, y, opts) {
    var a = opts.vals(row), b = opts.vals(y), from = null, into = null, block = [];
    var dr = docOnly(row), dy = docOnly(y);
    if (dr && !dy) { from = row; into = y; }
    else if (dy && !dr) { from = y; into = row; }
    else if (dr && dy) {
      if (row.slot_guid && !y.slot_guid) { from = y; into = row; } else { from = row; into = y; }
    } else block.push('photos_both');
    if (from && opts.frozen && opts.frozen(from)) block.push('frozen');
    if (opts.frozen && opts.frozen(row) && opts.frozen(y) && block.indexOf('frozen') < 0) block.push('frozen');
    if (into && !into.ct) block.push('no_ct');
    var diff = FIELDS.filter(function (fd) { return same(fd, a[fd], b[fd]) === false; });
    var warn = diff.filter(function (fd) { return WARN.indexOf(fd) >= 0; });
    var ist = into ? opts.st(into) : null;
    var after = ist === '自動OK' ? 'auto' : ist === '確認済' ? 'human' : ist === '再確認' ? 'check' : ist ? 'wait' : null;
    return { from: from, into: into, block: block, diff: diff, warn: warn, intoSt: ist, after: after };
  }
  var MARK_TEXT = { nw: 'N/W 同じ', seal: 'シール 同じ', seal_prefix: 'シールの数字 同じ（前の文字が違う）', seal1: 'シールの数字 1 文字違い',
    ct0: 'CT 同じ', ct1: 'CT 1 文字違い', ct2: 'CT 2 文字違い', ct3: 'CT 3 文字違い', wd: '作業日 同じ' };
  var api = { eligible: eligible, candidates: candidates, plan: plan, score: score, packerOk: packerOk, docOnly: docOnly, FIELDS: FIELDS, MARK_TEXT: MARK_TEXT };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (root) { root.C01 = root.C01 || {}; root.C01.mergePick = api; }
})(typeof window !== 'undefined' ? window : null);
