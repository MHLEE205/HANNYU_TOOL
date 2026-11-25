/* ✦ Powered by LEENAI Automation System — 通関依頼済 の自動記録 (v0.3.83 · R12Y55 · 決定 #401 · D-00 要請)
   通関書類を送った (エンジン iv.customs_done = TOOL の送付 · 職員の 「通関書類送付_{IV}」 メール の早い方 · 試験 · 下書き は除く) IV を
   PORTAL の clearance_status.json の records[{IV}] に 「tsukan_irai: true · tsukan_irai_at: 送付の時刻 (UTC)」 で書く (D-00 書類ツール の Deposit 期限)。
   - 書き方 = PORTAL v4.10 · 書類ツール と同じ 欄単位 (書く直前に読み直す → その IV の その欄だけ → eTag 条件 PUT · 412 = 読み直して最大 3 回)。
     他の欄 (tsukan_status · cotecna · shipping) · 他の IV · ファイル丸ごとの上書き = しない。updated_by = 'C-01'。
   - 決まり (D-00 R3 回答): 人がチェック済みで日付が空 = 日付だけ · 日付あり = そのまま · 人が外した (tsukan_irai_off_at) より前の送付 = 書かない ·
     リブッキングの前の IV = 書かない (新しい IV には customs_done が無い) · updated_by / updated_at で人の変更を判断しない。
   - 書く時: ① 「送信（通関業者へ）」 が成功した直後 ② TOOL を開いた時 · 10 分ごと。
   - 影 (shadow · 今): 本番ファイルは 読むだけ → 「書くもの一覧」 を _actions/clearance_shadow/{日付}/ に記録 (一覧が変わった時だけ) ·
     同じ書き方の試験 = D-00 の 試験用コピー (portal_test/clearance_status_copy.json) にだけ PUT。
   - 本番 (live) = エンジン meta.clearance.mode 'live' と C01.CLEARANCE.live の 両方が true の時だけ (형님 の決定の後)。
   エンジン engine/output/customs_done.py と同じ決まり · 同じ試験例 (tests/clearance_cases.json)。 */
'use strict';
window.C01 = window.C01 || {};

C01.clearance = (function () {
  var DEF = { tsukan_irai: false, tsukan_status: '未', tsukan_irai_at: '' };
  var TRIES = 3;
  var st = { busy: false, timer: null, last: null, sent: {} };

  function cfg() { return C01.CLEARANCE || {}; }
  function jstDay(iso) { var t = Date.parse(iso); return isNaN(t) ? '' : new Date(t + 9 * 3600e3).toISOString().slice(0, 10); }
  function clone(o) { return JSON.parse(JSON.stringify(o)); }

  /* ── 決まり (エンジン customs_done.plan_one と同じ) ── */
  function planOne(rec, done, oldIv, m) {
    var r = Object.assign({}, DEF, (rec && typeof rec === 'object' && !Array.isArray(rec)) ? rec : {});
    var now = { tsukan_irai: r.tsukan_irai === true, tsukan_irai_at: String(r.tsukan_irai_at || ''), tsukan_irai_off_at: String(r.tsukan_irai_off_at || ''),
      row: !!(rec && typeof rec === 'object' && !Array.isArray(rec)) };
    var at = done.at;
    if (jstDay(at) < ((m && m.backfill_from) || '2026-11-24')) return { kind: 'old', now: now, set: {} };
    if (oldIv) return { kind: 'rebook_old', now: now, set: {} };
    var off = now.tsukan_irai_off_at;
    if (off && !isNaN(Date.parse(off)) && Date.parse(at) < Date.parse(off)) return { kind: 'human_off', now: now, set: {} };
    if (now.tsukan_irai) {
      if (!now.tsukan_irai_at) return { kind: 'fill_at', now: now, set: { tsukan_irai_at: at } };
      return { kind: jstDay(now.tsukan_irai_at) === jstDay(at) ? 'same' : 'human_date', now: now, set: {} };
    }
    return { kind: 'write', now: now, set: { tsukan_irai: true, tsukan_irai_at: at } };
  }
  /* done = {IV: {at, source}} · olds = {前の IV: 1} · known = {今の IV: 1} (null = 調べない) */
  function plan(obj, done, olds, known, m) {
    var recs = (obj && obj.records) || {};
    return Object.keys(done).sort().map(function (iv) {
      var d = done[iv], p = planOne(recs[iv], d, !!(olds && olds[iv]), m);
      if (known && !known[iv] && p.kind !== 'old' && p.kind !== 'rebook_old') p = { kind: 'no_booking', now: p.now, set: {} };
      return { iv: iv, kind: p.kind, now: p.now, set: p.set, at: d.at, source: d.source, backfill: jstDay(d.at) < ((m && m.shadow_from) || '2026-11-26') };
    });
  }
  function merge(obj, rows, nowIso) {
    if (!obj.records || typeof obj.records !== 'object' || Array.isArray(obj.records)) obj.records = {};
    var done = [];
    rows.forEach(function (x) {
      if (!x.set || !Object.keys(x.set).length) return;
      var e = obj.records[x.iv];
      if (!e || typeof e !== 'object' || Array.isArray(e)) e = Object.assign({}, DEF);
      Object.keys(x.set).forEach(function (k) { e[k] = x.set[k]; });
      e.updated_by = 'C-01';
      e.updated_at = nowIso;
      obj.records[x.iv] = e;
      done.push(x.iv);
    });
    if (done.length) obj.last_updated = nowIso;
    return done;
  }
  function counts(rows) {
    var k = {};
    rows.forEach(function (x) { k[x.kind] = (k[x.kind] || 0) + 1; });
    return { write_n: (k.write || 0) + (k.fill_at || 0), same_n: (k.fill_at || 0) + (k.same || 0), diff_n: (k.write || 0) + (k.human_date || 0) + (k.human_off || 0),
      backfill_n: rows.filter(function (x) { return x.backfill && Object.keys(x.set || {}).length; }).length, kinds: k };
  }

  /* ── エンジンの _data から 送付の確認 · 前の IV · 今の IV ── */
  function inputs(S) {
    var done = {}, olds = {}, known = {};
    ((S.jik && S.jik.ivs) || []).forEach(function (iv) {
      known[iv.iv_no] = 1;
      if (iv.customs_done && iv.customs_done.at) done[iv.iv_no] = { at: iv.customs_done.at, source: iv.customs_done.source };
      (iv.iv_changed_from || []).forEach(function (o) { olds[o] = 1; });
    });
    /* 送った直後 (エンジンがまだ customs_done を出していない) = この画面の送付 (試験は除く) — 早い方 */
    Object.keys(st.sent).forEach(function (iv) {
      var d = st.sent[iv];
      if (!done[iv] || Date.parse(d.at) < Date.parse(done[iv].at)) done[iv] = d;
    });
    return { done: done, olds: olds, known: known };
  }
  function mode(S) {
    var m = S.meta && S.meta.clearance;
    if (!m || !cfg().enabled) return null;
    if (m.mode === 'live' && cfg().live === true && m.live_path === cfg().livePath) return 'live';
    if ((m.mode === 'shadow' || m.mode === 'live') && m.copy_path === cfg().copyPath) return 'shadow';
    return null;
  }

  /* ── 欄単位の保存 (PORTAL saveStatusJson と同じ流れ) — path は source.js が許した 2 か所だけ ── */
  function fieldSave(src, path, inp, m, live) {
    var n = 0, tries = [];
    function once() {
      n += 1;
      return src.clearanceRead(path, live).then(function (L) {
        var rows = plan(L.obj, inp.done, inp.olds, inp.known, m);
        var nowIso = new Date().toISOString();
        var obj = L.obj;
        var wrote = merge(obj, rows, nowIso);
        if (!wrote.length) { tries.push('nothing'); return { status: 'nothing', wrote: [], rows: rows, tries: tries }; }
        return src.clearancePut(path, JSON.stringify(obj, null, 2), L.eTag, live).then(function (code) {
          tries.push(code);
          if (code === 412 && n < TRIES) return once();
          if (code === 412) return { status: '412x' + TRIES, wrote: [], rows: rows, tries: tries };
          return { status: code >= 200 && code < 300 ? 'ok' : 'http' + code, wrote: code >= 200 && code < 300 ? wrote : [], rows: rows, tries: tries };
        });
      });
    }
    return once();
  }
  function slimRows(rows) {
    return rows.filter(function (x) { return x.kind !== 'old'; }).map(function (x) {
      return { iv: x.iv, kind: x.kind, now: x.now, set: x.set, at: x.at, source: x.source, backfill: x.backfill };
    });
  }
  /* 同じ一覧 = 記録しない (本番の一覧 · 書いた結果)。コピーに書いた · 失敗した時は いつも記録 */
  function sigOf(rec) { return JSON.stringify([rec.mode, rec.live && (rec.live.rows || rec.live.status), rec.live && rec.live.wrote]); }
  function mustRecord(rec) { return !!((rec.copy && rec.copy.status !== 'nothing') || (rec.live && rec.live.wrote && rec.live.wrote.length) || (rec.live && /error|412|http/.test(String(rec.live.status)))); }

  /* 1 回 (開いた時 · 10 分ごと · 送った直後) */
  function run(reason) {
    var A = C01.app && C01.app._api && C01.app._api(), S = A && A.S;
    if (!S || st.busy) return Promise.resolve(null);
    var md = mode(S), src = S.src;
    if (!md || !src || typeof src.clearanceRead !== 'function' || !(A.graphMode && A.graphMode())) return Promise.resolve(null);
    var m = S.meta.clearance, inp = inputs(S);
    if (!Object.keys(inp.done).length) return Promise.resolve(null);
    st.busy = true;
    var rec = { schema_version: 1, kind: 'clearance_shadow', at: A.jstNow(), by: (S.me && S.me.email) || '', reason: reason || '', mode: md,
      tool_version: ((C01.TOOL_INFO || {}).version || ''), live: null, copy: null };
    var p;
    if (md === 'live') {
      p = fieldSave(src, cfg().livePath, inp, m, true).then(function (r) {
        rec.live = { path: cfg().livePath, counts: counts(r.rows), rows: slimRows(r.rows), wrote: r.wrote, status: r.status, tries: r.tries };
      });
    } else {
      p = src.clearanceRead(cfg().livePath, false).then(function (L) {
        var rows = plan(L.obj, inp.done, inp.olds, inp.known, m);
        rec.live = { path: cfg().livePath, counts: counts(rows), rows: slimRows(rows), wrote: [], status: 'read_only' };
      }, function (e) { rec.live = { path: cfg().livePath, status: 'read_error', msg: String(e.message || e).slice(0, 200) }; }).then(function () {
        return fieldSave(src, cfg().copyPath, inp, m, false).then(function (r) {
          rec.copy = { path: cfg().copyPath, wrote: r.wrote, status: r.status, tries: r.tries };
        }, function (e) { rec.copy = { path: cfg().copyPath, wrote: [], status: 'error', msg: String(e.message || e).slice(0, 200) }; });
      });
    }
    return p.then(function () {
      var sig = sigOf(rec), key = 'c01_clearance_sig_' + String(rec.at).slice(0, 10);
      var prev = null;
      try { prev = window.localStorage.getItem(key); } catch (e) { prev = null; }
      st.last = rec;
      if (prev === sig && reason !== 'sent' && !mustRecord(rec)) return rec;   /* 一覧が変わらない = 記録しない */
      return src.writeClearanceShadow(rec).then(function () {
        try { window.localStorage.setItem(key, sig); } catch (e) { /* 記録できなくても次回 */ }
        return rec;
      });
    }).catch(function (e) {
      if (window.console && console.warn) console.warn('[C01] 通関依頼済 の記録:', e && e.message);
      return null;
    }).then(function (x) { st.busy = false; return x; });
  }
  /* 送信 (試験でない) の直後 — その IV をすぐ (エンジンの次の出力を待たない) */
  function sent(ivNo, atIso) {
    if (ivNo && atIso) st.sent[ivNo] = { at: new Date(Date.parse(atIso)).toISOString(), source: 'tool_sent' };
    return run('sent');
  }
  function start() {
    if (st.timer) clearInterval(st.timer);
    st.timer = setInterval(function () { run('timer'); }, Math.max(1, +cfg().everyMin || 10) * 60000);
    return run('open');
  }
  return { planOne: planOne, plan: plan, merge: merge, counts: counts, jstDay: jstDay, run: run, sent: sent, start: start, _st: st, _inputs: inputs, _mode: mode, _clone: clone };
})();
