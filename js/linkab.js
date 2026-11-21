/* ✦ Powered by LEENAI Automation System — v0.3.67 (R12Y5 · 決定 #356 穴 3): 「IVに連結」 の 「この書類は どれ？」 — 画面なしの計算だけ (node で試験)
   (a) 既にある行の追加書類 = 行のおすすめ順 (読んだ CT · シール · 重量 が近い順 · CT の読み違いでも シール · 重量 で上に来る)
   (b) 新しいコンテナ = 枠の状態 (空き / 使用中 · 入力済) · 使用中の枠なら 今の行を移す空き枠 (必須) · 入力済の行は動かせない · 空き枠が無ければ連結しない
   エンジン engine/actions/apply.py link_iv_ab · engine/actions/slot_pick.py と同じ規則 (最後の検査はエンジン · ここは画面の案内)。
   値の出どころにはしない: (a) は 「参考の書類」 として付くだけ (値 · 判定は変わらない · #239)。 */
(function (root) {
  'use strict';
  var W = { ct: 3, seal: 2, n_w: 1, t_w: 1, bales: 0.5 };
  var LABEL = { ct: 'CT', seal: 'シール', n_w: 'N/W', t_w: 'T/W', bales: '個数' };

  function txt(v) { return String(v == null ? '' : v).toUpperCase().replace(/[\s\-‐－]/g, ''); }
  function num(v) {
    if (v == null || v === '') return null;
    var t = String(v).replace(/[,，\s]/g, '').replace(/KG$/i, '');
    if (!/^-?\d+(\.\d+)?$/.test(t)) return null;
    return parseFloat(t);
  }
  /* 編集距離 (挿入 · 削除 · 置換 = 1) */
  function lev(a, b) {
    var m = a.length, n = b.length, prev = [], cur, i, j;
    for (j = 0; j <= n; j++) prev[j] = j;
    for (i = 1; i <= m; i++) {
      cur = [i];
      for (j = 1; j <= n; j++) cur[j] = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a.charAt(i - 1) === b.charAt(j - 1) ? 0 : 1));
      prev = cur;
    }
    return prev[n];
  }
  /* 文字の近さ 0〜1 (null = どちらか無い) */
  function strSim(a, b) {
    a = txt(a); b = txt(b);
    if (!a || !b) return null;
    if (a === b) return 1;
    return Math.max(0, 1 - lev(a, b) / Math.max(a.length, b.length));
  }
  /* 数の近さ 0〜1: 同じ = 1 · 2% 以内 = 0.8 · 5% 以内 = 0.5 · それ以外 = 0 */
  function numSim(a, b) {
    a = num(a); b = num(b);
    if (a == null || b == null) return null;
    if (a === b) return 1;
    var d = Math.abs(a - b) / Math.max(Math.abs(a), Math.abs(b), 1);
    return d <= 0.02 ? 0.8 : d <= 0.05 ? 0.5 : 0;
  }
  function pair(rd, row) {
    var s = 0, why = [];
    Object.keys(W).forEach(function (f) {
      var x = f === 'ct' || f === 'seal' ? strSim(rd[f], row[f]) : numSim(rd[f], row[f]);
      if (x == null) return;
      s += W[f] * x;
      if (x === 1) why.push(LABEL[f] + ' 同じ');
      else if (x >= 0.5) why.push(LABEL[f] + ' 近い');
    });
    return { score: Math.round(s * 1000) / 1000, why: why };
  }
  /* (a) おすすめ順 — reads = 書類で読んだ行 [{ct, seal, n_w, t_w, bales}] · rows = IV の行 (CT のある行だけ 付けられる)
     読んだ行ごとに一番近い行を 1 つずつ (近い組から先に · 同じ行を 2 回使わない) = おすすめ · 残りは近い順。
     戻り = [{row, score, why, rec (おすすめ), read (何番目の読んだ行)}] */
  function rank(reads, rows) {
    reads = (reads || []).filter(function (x) { return x && (x.ct || x.seal || x.n_w || x.t_w); });
    var cand = (rows || []).map(function (r, i) { return { row: r, i: i }; }).filter(function (x) { return x.row && x.row.ct; });
    var pairs = [];
    reads.forEach(function (rd, k) {
      cand.forEach(function (c) { var p = pair(rd, c.row); pairs.push({ k: k, c: c, score: p.score, why: p.why }); });
    });
    pairs.sort(function (a, b) { return b.score - a.score || a.c.i - b.c.i || a.k - b.k; });
    var usedR = {}, usedC = {}, out = [], best = {};
    pairs.forEach(function (p) {
      if (!best[p.c.i] || best[p.c.i].score < p.score) best[p.c.i] = p;
      if (usedR[p.k] || usedC[p.c.i] || p.score < 2) return;        /* 弱すぎる組 (重量 1 つだけ 等) は おすすめにしない */
      usedR[p.k] = usedC[p.c.i] = 1;
      out.push({ row: p.c.row, score: p.score, why: p.why, rec: true, read: p.k });
    });
    cand.filter(function (c) { return !usedC[c.i]; }).map(function (c) {
      var b = best[c.i];
      return { row: c.row, score: b ? b.score : 0, why: b ? b.why : [], rec: false, read: b ? b.k : null, i: c.i };
    }).sort(function (a, b) { return b.score - a.score || a.i - b.i; }).forEach(function (x) { delete x.i; out.push(x); });
    return out;
  }
  /* 枠の条件の違い (エンジン slot_pick.COND_KEYS と同じ · 単価 = エンジンの枠データに無い → 出さない) */
  var COND = [['plant', '営業所'], ['item', '品目'], ['work_date', '作業予定日'], ['incoterms', '条件'], ['type', 'タイプ']];
  function condDiff(a, b) {
    if (!a || !b) return [];
    return COND.filter(function (k) { return (a[k[0]] || '') !== (b[k[0]] || ''); }).map(function (k) { return k[1]; });
  }
  /* (b) 使用中の枠の行を移す 空き枠 = 同じ IV の空き枠で 業者 = 選んだ枠の業者 または その行の業者 (エンジン link_iv_ab と同じ) */
  function moveTargets(slots, used, from, row) {
    return (slots || []).filter(function (s) {
      return s.slot_guid !== from.slot_guid && !used[s.slot_guid] && (s.packer === from.packer || (row && row.packer && s.packer === row.packer));
    });
  }
  /* 一つの案 — 画面 · 「確認して次へ」 · 記録 が同じ判断を使う。
     in = {ab: 'a'|'b'|null, rowId, slot, move, scopeAll, slots, used (slot_guid → 行), rows, frozen (container_id → true)}
     戻り = {mode, slot_guid, container_id, move_to_slot, block (止める理由 · null = 進める), need (まだ選んでいないもの)} */
  function plan(x) {
    var slots = x.slots || [], used = x.used || {};
    if (x.ab !== 'a' && x.ab !== 'b') return { need: 'ab' };
    if (x.ab === 'a') {
      var r = (x.rows || []).filter(function (y) { return y.container_id === x.rowId; })[0];
      if (!r) return { mode: 'attach', need: 'row' };
      if (!r.ct) return { mode: 'attach', block: 'この行は CT がありません — 先に CT を確認してください' };
      var rs = slots.filter(function (s) { return s.slot_guid === r.slot_guid; })[0];
      if (!rs) return { mode: 'attach', block: '枠のない行には付けられません — 新しいコンテナなら (b)' };
      return { mode: 'attach', slot_guid: rs.slot_guid, container_id: r.container_id };
    }
    var sl = slots.filter(function (s) { return s.slot_guid === x.slot; })[0];
    if (!sl) return { mode: 'new', need: 'slot' };
    var u = used[sl.slot_guid];
    if (!u || x.scopeAll) return { mode: 'new', slot_guid: sl.slot_guid };
    if ((x.frozen || {})[u.container_id]) return { mode: 'new', slot_guid: sl.slot_guid, block: '入力済みの行は動かせません — 追加書類なら (a) を選んでください' };
    var tg = moveTargets(slots, used, sl, u);
    if (!tg.length) return { mode: 'new', slot_guid: sl.slot_guid, block: '空き枠がありません — このIVは枠がいっぱいです。新しいコンテナなら 枠外 になります（担当 · 社長に連絡）。追加書類なら (a) を選んでください' };
    if (!x.move || !tg.some(function (s) { return s.slot_guid === x.move; })) return { mode: 'new', slot_guid: sl.slot_guid, need: 'move', targets: tg };
    return { mode: 'new', slot_guid: sl.slot_guid, move_to_slot: x.move, move_ct: u.ct || null, targets: tg };
  }
  root.linkAb = { rank: rank, pair: pair, strSim: strSim, numSim: numSim, condDiff: condDiff, moveTargets: moveTargets, plan: plan };
})(typeof window !== 'undefined' ? (window.C01 = window.C01 || {}) : module.exports);
