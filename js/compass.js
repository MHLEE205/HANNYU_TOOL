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
    'SLOT_FOLLOWED', 'CT_DUP_OTHER_COND', 'CT_DUP_MULTI', 'OTHER_CT_IN_SLOT', 'TYPE_CHOOSE'];   /* TYPE_CHOOSE = v0.3.65 type_mode (オンの時だけ) */   /* 後ろ 4 つ = v0.2.1 follow_same_cond_slot (オンの時だけ) */
  var FOLLOW_OPT = 'follow_same_cond_slot';
  var STATES = ['SAME', 'FILL', 'DIFF', 'KEEP'];
  /* v0.3.24 (R7X Part D · #214 · 형님 実入力試験 OK 後): opts.plan_fill = COMPASS の CT が空の枠の 数値 (ブッキング予定値 例 23,000) は 「予定値 → 入力」 (PLAN · 警告なし · before は記録) ·
     opts.type_input === false = 形態 (crcf9_type) は入力しない (NOINPUT · PATCH から外す)。opts なし = エンジン rules.py と同じ (交差試験) */
  var PLAN_FIELDS = ['n_w', 'g_w', 't_w', 'bales'];
  /* v0.3.65 (R12Y Part 001 · 決定 #361): 形態 = COMPASS crcf9_form (Lookup → crcf9_packer_types · 1 行 「BALES」)。
     opts.form_bales = { guid, name } の時だけ: 空欄 → BALES (crcf9_form の odata.bind) · 値あり → そのまま。
     opts.type_mode === 'fill_empty' の時 タイプ (crcf9_type): 値あり → そのまま · 空欄 → 45GP (決定 #1 · 旧 Compass入力 test_jikjin_compass_v1.py:289-298 と同じ)。
     ただし 行の type_hint (45R の船社 · 同じブッキングの他の枠が 45R/42GP/22GP · 書類 · 写真のサイズ根拠 size_hint) があれば 黄色の警告 TYPE_CHOOSE +
     担当者が opts.type_choices (45GP / 45R / 42GP) から選ぶ (選ぶまで入れない · row.type_pick)。opts なし = エンジン rules.py と同じ (交差試験)。 */
  var FORM_DV = '_crcf9_form_value', FORM_BIND = 'crcf9_form' + '@' + 'odata.bind', FORM_SET = 'crcf9_packer_types', FORM_NAV = 'crcf9_form';
  function formBind(guid) { return '/' + FORM_SET + '(' + guid + ')'; }
  function bindGuid(v) { var m = /\(([^)]+)\)/.exec(String(v || '')); return m ? m[1].toLowerCase() : null; }
  function recKey(k) { return k === FORM_BIND ? FORM_DV : k; }

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
      if (name === 'type' && opts && opts.type_mode === 'fill_empty') {
        if (nv !== null) { state = 'KEEPNOW'; inp = false; pv = null; }
        else if (row.type_hint) {
          cw.push('TYPE_CHOOSE');
          var tp = row.type_pick && (opts.type_choices || ['45GP', '45R', '42GP']).indexOf(row.type_pick) >= 0 ? row.type_pick : null;
          state = 'CHOOSE'; inp = !!tp; pv = tp;
        } else { state = 'FILL'; inp = true; pv = '45GP'; }
        out.cells.push({ field: name, dv_field: dv, now: cell[dv] === undefined ? null : cell[dv], put: pv, state: state, in_patch: inp, warnings: cw,
          hint: state === 'CHOOSE' ? row.type_hint : undefined });
        if (inp) out.patch[dv] = pv;
        warns = warns.concat(cw);
        return;
      }
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
    if (opts && opts.form_bales && opts.form_bales.guid) {
      /* v0.3.65 (#361): 形態 — 空欄だけ BALES (値ありはそのまま · 比較表 「形態: (空) → BALES」) */
      var fg = String(opts.form_bales.guid).toLowerCase(), fn = cell[FORM_DV] ? String(cell[FORM_DV]).toLowerCase() : null;
      var fst = fn === null ? 'FILL' : (fn === fg ? 'SAME' : 'KEEPNOW');
      out.cells.push({ field: 'form', dv_field: FORM_DV, now: fn === null ? null : (fn === fg ? (opts.form_bales.name || 'BALES') : (cell[FORM_DV + '@OData.Community.Display.V1.FormattedValue'] || fn)),
        put: fst === 'FILL' ? (opts.form_bales.name || 'BALES') : null, state: fst, in_patch: fst === 'FILL', warnings: [] });
      if (fst === 'FILL') out.patch[FORM_BIND] = formBind(opts.form_bales.guid);
    }
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
    if (opts && opts.type_input === false && opts.type_mode !== 'fill_empty') cnt.NOINPUT = 0;
    if (opts && (opts.type_mode === 'fill_empty' || opts.form_bales)) { cnt.KEEPNOW = 0; cnt.CHOOSE = 0; }
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
    var sel = 'crcf9_container_informationid,' + FIELDS.map(function (f) { return f[1]; }).join(',') + ',' + FORM_DV;   /* v0.3.65: 形態 も読む */
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
            if (dv === FORM_BIND) return (after[FORM_DV] ? String(after[FORM_DV]).toLowerCase() : null) !== bindGuid(body[dv]);   /* v0.3.65: 形態 = 読み直した guid */
            if (body[dv] === null) return after[dv] !== null && after[dv] !== undefined && after[dv] !== '';                   /* 元に戻す (空へ) */
            var f = names[dv], a = nowValue(f, after[dv]);
            var want = (f === 'ct' || f === 'seal') ? normText(body[dv]) : (f === 'type' ? String(body[dv]).toUpperCase() : body[dv]);
            return a !== want;
          });
          if (bad.length) return { result: 'REREAD_DIFF', ct_id: p.ct_id, before: before, after: after, field: bad[0] };
          var pick = function (o) { var x = {}; Object.keys(body).forEach(function (k) { var rk = recKey(k); x[rk] = o[rk] === undefined ? null : o[rk]; }); return x; };
          return { result: 'OK', ct_id: p.ct_id, cell: { ct_id: p.ct_id, fields: Object.keys(body).map(recKey).sort(), before: pick(before), after: pick(after) } };
        });
      });
    });
  };
  /* v0.3.65 (R12Y Part 001): 形態 (Lookup) を空に戻す = DELETE …/crcf9_form/$ref → もう一度 GET で空を確認 (元に戻す だけが使う) */
  Writer.prototype.clearForm = function (id, ifMatch) {
    var self = this;
    if (!this.enabled) return Promise.reject(new Error('DRY — 送信しません'));
    return this.getCell(id).then(function (before) {
      if (!before) return { result: 'ERROR', ct_id: id, error: 'GET 失敗' };
      if (ifMatch && before['@odata.etag'] !== ifMatch) return { result: 'PRECONDITION_FAILED', ct_id: id, before: before };
      self.calls.push(['DELETE_REF', id]);
      return self.fetch(self._url(id) + '/' + FORM_NAV + '/$ref', { method: 'DELETE', headers: self._hdr({ 'If-Match': before['@odata.etag'] || '*' }) }).then(function (r) {
        if (r.status === 412) return { result: 'PRECONDITION_FAILED', ct_id: id, before: before };
        if (r.status !== 200 && r.status !== 204) return { result: 'ERROR', ct_id: id, error: 'DELETE ' + r.status, before: before };
        return self.getCell(id).then(function (after) {
          if (!after || after[FORM_DV]) return { result: 'REREAD_DIFF', ct_id: id, before: before, after: after || null, field: FORM_DV };
          return { result: 'OK', ct_id: id, cell: { ct_id: id, fields: [FORM_DV], before: { _crcf9_form_value: before[FORM_DV] || null }, after: { _crcf9_form_value: null } } };
        });
      });
    });
  };
  /* v0.3.65: 形態 · タイプ が空欄の行の数 (CT が入った枠だけ · 通関書類送付 の条件 · 記録 formtype_blank) */
  function formTypeBlank(cells) {
    var n = 0;
    Object.keys(cells || {}).forEach(function (g) {
      var c = cells[g] || {};
      if (normText(c.crcf9_container_no) && (!c[FORM_DV] || !String(c.crcf9_type || '').trim())) n += 1;
    });
    return n;
  }
  /* v0.3.65: タイプを選ばせる理由 (行ごと) — 45R の船社 · 同じブッキングの他の枠のタイプ · 書類 · 写真のサイズ根拠 (エンジン size_hint · あれば) */
  function typeHint(row, ctx) {
    ctx = ctx || {};
    var why = [];
    if (ctx.carrier45r === true) why.push('45R を使う船社 (' + (ctx.carrier || '') + ')');
    if (ctx.carrier45r === null) why.push('船社を読めません');
    var ot = (ctx.otherTypes || []).filter(function (t) { return t && t !== '45GP'; });
    if (ot.length) why.push('同じブッキングの他の枠 ' + ot.join('・'));
    if (row && row.size_hint) why.push('書類・写真のサイズ ' + row.size_hint);
    return why.length ? why.join(' · ') : null;
  }
  /* v0.3.50 (R10Q · #176): compass_done 記録の trial — cfg.trialUntil (JST の日時 · 例 '2026-11-24T00:00:00+09:00') から false。
     nowMs = Date.now() (端末の時間帯に関係なし)。trial が false · trialUntil が読めない時 = cfg.trial のまま (記録だけ · 入力の動きは同じ) */
  function trialAt(cfg, nowMs) {
    cfg = cfg || {};
    if (!cfg.trial) return false;
    var until = Date.parse(cfg.trialUntil || '');
    if (isNaN(until) || typeof nowMs !== 'number' || isNaN(nowMs)) return true;
    return nowMs < until;
  }
  /* v0.3.68 (R12Y7 · #367 Part 0): COMPASS が もう実況表と同じ IV (他の道で入力済) = 「COMPASS と一致を確認（入力済にする）」。
     条件: 全員 自動OK・確認済 (all_ok) · スキップ行 0 · PATCH 0 · 警告 0 · DIFF/CHOOSE/FILL/PLAN 0 · 各行 SAME 1 つ以上 (CT は SAME)。
     checked = 行ごとの SAME の項目 (before = after = 今の COMPASS の値) → エンジンは 入力の時と同じく 行を固定 (#307) · cells は [] (PATCH なし) */
  var VERIFY_BAD = ['DIFF', 'CHOOSE', 'FILL', 'PLAN'];
  function verifyPlan(res) {
    var rows = (res && res.rows) || [];
    if (!res || !res.all_ok) return { ok: false, why: (res && res.button && res.button.reason) || '自動OK・確認済 でない行があります', checked: [] };
    if (!rows.length) return { ok: false, why: '行がありません', checked: [] };
    var checked = [], why = null;
    rows.forEach(function (r) {
      if (why) return;
      if (r.skip) { why = 'COMPASS と比べられない行があります'; return; }
      if (Object.keys(r.patch || {}).length) { why = '入力する値があります'; return; }
      if ((r.warnings || []).length) { why = '警告のある行があります'; return; }
      if (r.cells.some(function (c) { return VERIFY_BAD.indexOf(c.state) >= 0; })) { why = 'COMPASS と違う値・空欄があります'; return; }
      var same = r.cells.filter(function (c) { return c.state === 'SAME'; });
      if (!same.some(function (c) { return c.field === 'ct'; })) { why = 'CT が COMPASS と同じではありません'; return; }
      var v = {};
      same.forEach(function (c) { v[c.dv_field] = c.now === undefined ? null : c.now; });
      checked.push({ ct_id: r.ct_id, fields: Object.keys(v).sort(), before: JSON.parse(JSON.stringify(v)), after: v });
    });
    if (why) return { ok: false, why: why, checked: [] };
    checked.sort(function (a, b) { return String(a.ct_id).localeCompare(String(b.ct_id)); });
    return { ok: true, why: null, checked: checked };
  }
  /* 確認した値の sha (記録用 · 16 桁 · crypto.subtle が無い時は FNV-1a 64) */
  function shaText(text) {
    var s = String(text);
    var C = (typeof crypto !== 'undefined' && crypto.subtle) ? crypto : null;
    if (C && typeof TextEncoder !== 'undefined') {
      return C.subtle.digest('SHA-256', new TextEncoder().encode(s)).then(function (buf) {
        return Array.prototype.map.call(new Uint8Array(buf), function (x) { return ('0' + x.toString(16)).slice(-2); }).join('').slice(0, 16);
      });
    }
    var h1 = 0x811c9dc5, h2 = 0x01000193;
    for (var i = 0; i < s.length; i++) { h1 = Math.imul(h1 ^ s.charCodeAt(i), 0x01000193) >>> 0; h2 = Math.imul(h2 ^ s.charCodeAt(i), 0x85ebca6b) >>> 0; }
    return Promise.resolve(('00000000' + h1.toString(16)).slice(-8) + ('00000000' + h2.toString(16)).slice(-8));
  }
  function verifyAction(actionId, iv, by, at, checked, sha) {
    var a = compassDoneAction(actionId, iv, by, at, []);
    a.value.verify_only = true; a.value.checked = checked; a.value.compass_sha = sha;
    return a;
  }
  function compassDoneAction(actionId, iv, by, at, cells) {
    return { schema_version: 1, action_id: actionId, action: 'compass_done', iv: iv, ct: null, field: null,
      value: { cells: cells, rules_version: RULES_VERSION, mode: 'graph' }, source: null, by: by, at: at, queue_id: null };
  }

  var api = { RULES_VERSION: RULES_VERSION, FIELDS: FIELDS, STATES: STATES, WARN_CODES: WARN_CODES, toInt: toInt, normText: normText,
    putText: putText, normCode: normCode, nowValue: nowValue, targetType: targetType, compareRow: compareRow, ivAllOk: ivAllOk,
    compareIv: compareIv, followTarget: followTarget, sameCond: sameCond, FOLLOW_OPT: FOLLOW_OPT, Writer: Writer, compassDoneAction: compassDoneAction, verifyPlan: verifyPlan, verifyAction: verifyAction, shaText: shaText, trialAt: trialAt, NumInvalid: NumInvalid,
    FORM_DV: FORM_DV, FORM_BIND: FORM_BIND, formBind: formBind, bindGuid: bindGuid, formTypeBlank: formTypeBlank, typeHint: typeHint };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.C01 = root.C01 || {};
  root.C01.compass = api;
})(typeof window !== 'undefined' ? window : globalThis);
