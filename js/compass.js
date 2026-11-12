/* ✦ Powered by LEENAI Automation System — Compass入力 (v0.2.1 · R6.6): DRY 比較表 · PATCH 本文 (送らない) · 実行の枠 (既定オフ)
   規則 = エンジン engine/compass_input/rules.py と同じ (決定 #1 · #2 · #3 · #91 · Compass入力点検 v1.1 §3)。交差試験 tests/test_compass_cross.py。
   - 入れる項目: CT · シール · 正味 · 総重量 (= 正味) · 風袋 · ベール数 · 形態。作業日は入れない。
   - 形態 (#1): 今が 45R ならそのまま、ほかは 45GP。今が 42GP · 22GP なら警告 TYPE_42_22 (既定では PATCH に入れない — 担当者が判断)。
   - 数字 (#3): 整数に変換。できなければその行は入力しない + NUM_INVALID。警告だけ (#2): PACKER_DIFF · ITEM_DIFF · OFFICE_DIFF · EXISTING_DIFF · CT_DUP。
   - ct_id なし = スキップ (新しい行は作らない)。同じ値 = SAME (PATCH に入れない)。
   - 「全台 OK」 (自動OK · 確認済) の IV だけ送信ボタンが有効 (設計 §6)。R6 はローカル DRY — 送信は常に無効。
   - v0.2.1 (R6.6 · D-11 (가) 準備 · 既定オフ): opts.follow_same_cond_slot (設定 C01.COMPASS の 1 か所)。入れる CT が v2 の枠に無く、同じブッキングの
     別の枠 1 つだけにあり、その枠が同一条件 (#26 — 枠の _cond) なら、その枠で比較・入力 (SLOT_FOLLOWED · 行に slot_from)。条件が違う枠 = CT_DUP_OTHER_COND ·
     同じ CT の枠が 2 つ以上 = CT_DUP_MULTI · 枠に別の CT が入っている = OTHER_CT_IN_SLOT (いずれも警告 + 入力しない)。別の枠に無ければ v2 の枠のまま。
     エンジン engine/compass_input/rules.py の follow_target と同じ。オフなら結果は v0.2.0 と同じ。 */
'use strict';
(function (root) {
  var RULES_VERSION = '1.0.0';
  var FIELDS = [['ct', 'crcf9_container_no', false], ['seal', 'crcf9_seal_no', false], ['n_w', 'crcf9_n_w', true], ['g_w', 'crcf9_g_w', true],
    ['t_w', 'crcf9_t_w', true], ['bales', 'crcf9_quantity', true], ['type', 'crcf9_type', false]];
  var OK_STATUSES = ['自動OK', '確認済'];
  var WARN_CODES = ['PACKER_DIFF', 'ITEM_DIFF', 'OFFICE_DIFF', 'EXISTING_DIFF', 'CT_DUP', 'TYPE_42_22', 'NUM_INVALID',
    'SLOT_FOLLOWED', 'CT_DUP_OTHER_COND', 'CT_DUP_MULTI', 'OTHER_CT_IN_SLOT'];   /* 後ろ 4 つ = v0.2.1 follow_same_cond_slot (オンの時だけ) */
  var FOLLOW_OPT = 'follow_same_cond_slot';
  var STATES = ['SAME', 'FILL', 'DIFF', 'KEEP'];
  /* v0.3.24 (R7X Part D · #214 · 형님 実入力試験 OK 後): opts.plan_fill = COMPASS の CT が空の枠の 数値 (ブッキング予定値 例 23,000) は 「予定値 → 入力」 (PLAN · 警告なし · before は記録) ·
     opts.type_input === false = 形態 (crcf9_type) は入力しない (NOINPUT · PATCH から外す)。opts なし = エンジン rules.py と同じ (交差試験) */
  var PLAN_FIELDS = ['n_w', 'g_w', 't_w', 'bales'];

  function NumInvalid(v) { this.value = v; }

  /* Python to_int と同じ */
  function toInt(v) {
    if (v === null || v === undefined) return null;
    if (typeof v === 'boolean') throw new NumInvalid(v);
    if (typeof v === 'number') {
      if (!isFinite(v) || Math.floor(v) !== v) throw new NumInvalid(v);
      return v;
    }
    var s = String(v).trim().replace(/,/g, '');
    if (s === '') return null;
    if (/^[+-]?\d+$/.test(s)) return parseInt(s, 10);
    if (/^[+-]?\d+\.0+$/.test(s)) return parseInt(s.split('.')[0], 10);
    throw new NumInvalid(s);
  }
  function normText(v) {
    if (v === null || v === undefined) return null;
    var s = String(v).replace(/[\s\-　]/g, '').toUpperCase();
    return s || null;
  }
  function putText(v, upper) {
    if (v === null || v === undefined) return null;
    var s = String(v).trim();
    if (upper) s = s.replace(/\s/g, '').toUpperCase();
    return s || null;
  }
  function normCode(v) {
    if (v === null || v === undefined) return '';
    return String(v).toUpperCase().split('').filter(function (ch) { return /[\p{L}\p{N}]/u.test(ch); }).join('');
  }
  function nowValue(field, raw) {
    if (raw === null || raw === undefined || raw === '') return null;
    if (['n_w', 'g_w', 't_w', 'bales'].indexOf(field) >= 0) {
      try { return toInt(raw); } catch (e) { if (e instanceof NumInvalid) return String(raw); throw e; }
    }
    if (field === 'type') return String(raw).trim().toUpperCase() || null;
    return normText(raw);
  }
  function targetType(nowType) {
    var t = String(nowType || '').trim().toUpperCase();
    if (t === '45R') return ['45R', null];
    if (t === '42GP' || t === '22GP') return ['45GP', 'TYPE_42_22'];
    return ['45GP', null];
  }
  function uniqSorted(xs, order) {
    var seen = {};
    var out = xs.filter(function (x) { if (seen[x]) return false; seen[x] = 1; return true; });
    return out.sort(function (a, b) { return order.indexOf(a) - order.indexOf(b); });
  }

  function compareRow(row, cell, dupCts, opts) {
    var out = { container_id: row.container_id === undefined ? null : row.container_id, ct: row.ct === undefined ? null : row.ct,
      ct_id: row.ct_id === undefined ? null : row.ct_id, etag: null, status: row.status === undefined ? null : row.status, skip: null,
      warnings: [], cells: [], patch: {} };
    if (OK_STATUSES.indexOf(row.status) < 0) { out.skip = 'NOT_OK'; return out; }
    if (!row.ct_id) { out.skip = 'NO_CT_ID'; return out; }
    if (cell === null || cell === undefined) { out.skip = 'NOT_FOUND'; return out; }
    out.etag = cell['@odata.etag'] === undefined ? null : cell['@odata.etag'];
    var warns = [];
    if (cell._packer && normCode(row.packer) !== normCode(cell._packer)) warns.push('PACKER_DIFF');
    if (row.item && cell._item && normCode(row.item) !== normCode(cell._item)) warns.push('ITEM_DIFF');
    if (row.plant && cell._plant && normCode(row.plant) !== normCode(cell._plant)) warns.push('OFFICE_DIFF');
    var put;
    try {
      put = { ct: putText(row.ct, true), seal: putText(row.seal), n_w: toInt(row.n_w), t_w: toInt(row.t_w), bales: toInt(row.bales) };
    } catch (e) {
      if (!(e instanceof NumInvalid)) throw e;
      out.skip = 'NUM_INVALID';
      out.warnings = uniqSorted(warns.concat(['NUM_INVALID']), WARN_CODES);
      return out;
    }
    put.g_w = put.n_w;
    var tt = targetType(cell.crcf9_type);
    put.type = tt[0];
    if (put.ct && dupCts && dupCts.indexOf(normText(put.ct)) >= 0) warns.push('CT_DUP');
    FIELDS.forEach(function (f) {
      var name = f[0], dv = f[1];
      var nv = nowValue(name, cell[dv]);
      var pv = put[name] === undefined ? null : put[name];
      var pc = (name === 'ct' || name === 'seal') ? normText(pv) : pv;
      var cw = [], state, inp;
      if (name === 'type' && opts && opts.type_input === false) { state = 'NOINPUT'; inp = false; }
      else if (pv === null) { state = 'KEEP'; inp = false; }
      else if (nv === null) { state = 'FILL'; inp = true; }
      else if (opts && opts.plan_fill && PLAN_FIELDS.indexOf(name) >= 0 && !normText(cell.crcf9_container_no) && nv !== pc) { state = 'PLAN'; inp = true; }
      else if (nv === pc) { state = 'SAME'; inp = false; }
      else {
        state = 'DIFF'; inp = true;
        if (name === 'type') { if (tt[1]) { cw.push(tt[1]); inp = false; } }
        else cw.push('EXISTING_DIFF');
      }
      out.cells.push({ field: name, dv_field: dv, now: cell[dv] === undefined ? null : cell[dv], put: pv, state: state, in_patch: inp, warnings: cw });
      if (inp) out.patch[dv] = pv;
      warns = warns.concat(cw);
    });
    out.warnings = uniqSorted(warns, WARN_CODES);
    return out;
  }

  function ivAllOk(rows) {
    if (!rows || !rows.length) return [false, 'コンテナがありません'];
    var bad = rows.filter(function (r) { return OK_STATUSES.indexOf(r.status) < 0; });
    if (bad.length) return [false, '未確認 ' + bad.length + ' 本 (自動OK・確認済 以外)'];
    return [true, null];
  }

  /* 2 つの枠が同一条件 (#26) か: 両方に _cond (営業所・品目・条件・タイプ・業者・単価・購買契約) があり同じ。分からなければ false */
  function canon(x) {
    if (Array.isArray(x)) return x.map(canon);
    if (x && typeof x === 'object') { var o = {}; Object.keys(x).sort().forEach(function (k) { o[k] = canon(x[k]); }); return o; }
    return x;
  }
  function isObj(x) { return !!x && typeof x === 'object' && !Array.isArray(x); }
  function sameCond(a, b) {
    var ca = (a || {})._cond, cb = (b || {})._cond;
    return isObj(ca) && isObj(cb) && JSON.stringify(canon(ca)) === JSON.stringify(canon(cb));
  }
  /* D-11 (가): その行を比較・入力する枠。戻り値 [ct_id, スキップコード or null, 移した?] — Python follow_target と同じ */
  function followTarget(row, cells) {
    cells = cells || {};
    var cid = row.ct_id === undefined ? null : row.ct_id;
    var own = cid ? cells[cid] : null;
    var k = normText(putText(row.ct, true));
    if (OK_STATUSES.indexOf(row.status) < 0 || own === null || own === undefined || !k) return [cid, null, false];
    if (normText(own.crcf9_container_no) === k) return [cid, null, false];
    var others = Object.keys(cells).filter(function (g) { return g !== cid && normText((cells[g] || {}).crcf9_container_no) === k; });
    if (!others.length) return [cid, normText(own.crcf9_container_no) ? 'OTHER_CT_IN_SLOT' : null, false];
    if (others.length > 1) return [cid, 'CT_DUP_MULTI', false];
    if (!sameCond(own, cells[others[0]])) return [cid, 'CT_DUP_OTHER_COND', false];
    return [others[0], null, true];
  }

  function compareIv(iv, rows, cells, dups, opts) {
    var ok = ivAllOk(rows);
    var follow = !!(opts && opts[FOLLOW_OPT]);
    var outRows = (rows || []).map(function (r) {
      if (!follow) {
        var cell = r.ct_id ? (cells || {})[r.ct_id] : null;
        return compareRow(r, cell === undefined ? null : cell, (dups || {})[r.ct_id] || null, opts);
      }
      var ft = followTarget(r, cells), tgt = ft[0], o;
      if (ft[1]) {
        o = { container_id: r.container_id === undefined ? null : r.container_id, ct: r.ct === undefined ? null : r.ct, ct_id: tgt, etag: null,
          status: r.status === undefined ? null : r.status, skip: ft[1], warnings: [ft[1]], cells: [], patch: {} };
      } else {
        var r2 = {}; Object.keys(r).forEach(function (k2) { r2[k2] = r[k2]; }); r2.ct_id = tgt;
        var c2 = tgt ? (cells || {})[tgt] : null;
        o = compareRow(r2, c2 === undefined ? null : c2, (dups || {})[tgt] || null, opts);
        if (ft[2]) o.warnings = uniqSorted(o.warnings.concat(['SLOT_FOLLOWED']), WARN_CODES);
      }
      o.slot_from = ft[2] ? r.ct_id : null;
      return o;
    });
    var cnt = { SAME: 0, FILL: 0, DIFF: 0, KEEP: 0 }, warn = {}, skip = {};
    if (opts && opts.plan_fill) cnt.PLAN = 0;
    if (opts && opts.type_input === false) cnt.NOINPUT = 0;
    outRows.forEach(function (r) {
      r.cells.forEach(function (c) { if (cnt[c.state] !== undefined) cnt[c.state] += 1; });
      r.warnings.forEach(function (w) { warn[w] = (warn[w] || 0) + 1; });
      if (r.skip) skip[r.skip] = (skip[r.skip] || 0) + 1;
    });
    var patches = outRows.filter(function (r) { return !r.skip && Object.keys(r.patch).length; })
      .map(function (r) { return { ct_id: r.ct_id, if_match: r.etag, body: r.patch }; });
    var res = { schema_version: 1, rules_version: RULES_VERSION, mode: 'dry', iv_no: iv, all_ok: ok[0],
      button: { enabled: ok[0] && patches.length > 0, reason: !ok[0] ? ok[1] : (patches.length ? null : '入力する値がありません') },
      rows: outRows, count: { cells: cnt, warnings: warn, skip: skip, patch_rows: patches.length }, patches: patches };
    if (follow) { res.options = {}; res.options[FOLLOW_OPT] = true; }
    return res;
  }

  /* ── 実行の枠 (graph モード · R7 以降): 職員トークン GET → If-Match PATCH → もう一度 GET → compass_done。
     既定オフ。enabled=true と fetchFn を両方渡したときだけ PATCH を送る (R6 はどこからも渡さない — 試験は偽 HTTP)。 ── */
  function Writer(opts) {
    opts = opts || {};
    this.base = String(opts.baseUrl || '').replace(/\/$/, '') + '/api/data/v9.2/';
    this.fetch = opts.fetchFn || null;
    this.token = opts.token || null;
    this.enabled = !!(opts.enabled && this.fetch);
    this.calls = [];
  }
  Writer.prototype._url = function (id) { return this.base + 'crcf9_container_informations(' + id + ')'; };
  Writer.prototype._hdr = function (extra) {
    var h = { Accept: 'application/json' };
    if (this.token) h.Authorization = 'Bearer ' + this.token;
    Object.keys(extra || {}).forEach(function (k) { h[k] = extra[k]; });
    return h;
  };
  Writer.prototype.getCell = function (id) {
    var self = this;
    if (!this.fetch) return Promise.reject(new Error('DRY — 送信しません'));
    this.calls.push(['GET', id]);
    var sel = 'crcf9_container_informationid,' + FIELDS.map(function (f) { return f[1]; }).join(',');
    return this.fetch(this._url(id) + '?$select=' + sel, { method: 'GET', headers: this._hdr() }).then(function (r) {
      return r.status === 200 ? r.json() : null;
    }).catch(function () { return null; }).then(function (x) { self.last = x; return x; });
  };
  Writer.prototype.apply = function (p) {
    var self = this;
    if (!this.enabled) return Promise.reject(new Error('DRY — 送信しません'));
    var body = p.body;
    return this.getCell(p.ct_id).then(function (before) {
      if (!before) return { result: 'ERROR', ct_id: p.ct_id, error: 'GET 失敗' };
      if (p.if_match && before['@odata.etag'] !== p.if_match) return { result: 'PRECONDITION_FAILED', ct_id: p.ct_id, before: before };
      self.calls.push(['PATCH', p.ct_id]);
      return self.fetch(self._url(p.ct_id), { method: 'PATCH', headers: self._hdr({ 'If-Match': p.if_match || before['@odata.etag'] || '*', 'Content-Type': 'application/json' }),
        body: JSON.stringify(body) }).then(function (r) {
        if (r.status === 412) return { result: 'PRECONDITION_FAILED', ct_id: p.ct_id, before: before };
        if (r.status !== 200 && r.status !== 204) return { result: 'ERROR', ct_id: p.ct_id, error: 'PATCH ' + r.status, before: before };
        return self.getCell(p.ct_id).then(function (after) {
          if (!after) return { result: 'REREAD_DIFF', ct_id: p.ct_id, before: before };
          var names = {};
          FIELDS.forEach(function (f) { names[f[1]] = f[0]; });
          var bad = Object.keys(body).filter(function (dv) {
            var f = names[dv], a = nowValue(f, after[dv]);
            var want = (f === 'ct' || f === 'seal') ? normText(body[dv]) : (f === 'type' ? String(body[dv]).toUpperCase() : body[dv]);
            return a !== want;
          });
          if (bad.length) return { result: 'REREAD_DIFF', ct_id: p.ct_id, before: before, after: after, field: bad[0] };
          var pick = function (o) { var x = {}; Object.keys(body).forEach(function (k) { x[k] = o[k] === undefined ? null : o[k]; }); return x; };
          return { result: 'OK', ct_id: p.ct_id, cell: { ct_id: p.ct_id, fields: Object.keys(body).sort(), before: pick(before), after: pick(after) } };
        });
      });
    });
  };
  function compassDoneAction(actionId, iv, by, at, cells) {
    return { schema_version: 1, action_id: actionId, action: 'compass_done', iv: iv, ct: null, field: null,
      value: { cells: cells, rules_version: RULES_VERSION, mode: 'graph' }, source: null, by: by, at: at, queue_id: null };
  }

  var api = { RULES_VERSION: RULES_VERSION, FIELDS: FIELDS, STATES: STATES, WARN_CODES: WARN_CODES, toInt: toInt, normText: normText,
    putText: putText, normCode: normCode, nowValue: nowValue, targetType: targetType, compareRow: compareRow, ivAllOk: ivAllOk,
    compareIv: compareIv, followTarget: followTarget, sameCond: sameCond, FOLLOW_OPT: FOLLOW_OPT, Writer: Writer, compassDoneAction: compassDoneAction, NumInvalid: NumInvalid };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.C01 = root.C01 || {};
  root.C01.compass = api;
})(typeof window !== 'undefined' ? window : globalThis);
