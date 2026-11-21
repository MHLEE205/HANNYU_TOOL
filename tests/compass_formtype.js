/* ✦ Powered by LEENAI Automation System — v0.3.65 (R12Y Part 001 · 決定 #361) 形態 BALES · タイプ 시험 (node · 가짜 COMPASS · 실제 호출 0)
   사용: node tests/compass_formtype.js  (출력 마지막 줄 JSON · ng 0 이면 통과) */
'use strict';
var C = require('../js/compass.js');
var G = '64f45d9f-383c-f011-8c4e-6045bd62e122';
var OPTS = { plan_fill: true, type_input: false, form_bales: { guid: G, name: 'BALES' }, type_mode: 'fill_empty', type_choices: ['45GP', '45R', '42GP'] };
var res = [], ng = 0;
function ok(name, cond, got) { res.push((cond ? 'OK  ' : 'NG  ') + name + (cond ? '' : ' — ' + JSON.stringify(got))); if (!cond) ng += 1; }
function row(x) { return Object.assign({ container_id: 'C-1', ct: 'TSTU0000001', ct_id: 'g1', status: '自動OK', seal: 'S1', n_w: 21000, t_w: 3800, bales: 40, packer: 'P', item: 'I', plant: 'X' }, x || {}); }
function cell(x) { return Object.assign({ '@odata.etag': 'W/"1"', crcf9_container_no: null, crcf9_seal_no: null, crcf9_n_w: null, crcf9_g_w: null, crcf9_t_w: null, crcf9_quantity: null, crcf9_type: null, _crcf9_form_value: null }, x || {}); }
function st(r, f) { return (r.cells.filter(function (c) { return c.field === f; })[0] || {}).state; }

/* 1. 빈칸 → BALES · 45GP */
var r1 = C.compareRow(row(), cell(), [], OPTS);
ok('빈칸: 形態 FILL BALES · タイプ FILL 45GP · PATCH 두 칸', st(r1, 'form') === 'FILL' && st(r1, 'type') === 'FILL' && r1.patch[C.FORM_BIND] === '/crcf9_packer_types(' + G + ')' && r1.patch.crcf9_type === '45GP' && !r1.warnings.length, r1.patch);
/* 2. 이미 값 → 그대로 */
var r2 = C.compareRow(row(), cell({ crcf9_type: '45R', _crcf9_form_value: G.toUpperCase() }), [], OPTS);
ok('이미 값: 形態 SAME (같은 guid · 대소문자 무관) · タイプ 45R KEEPNOW · PATCH 에 두 칸 없음', st(r2, 'form') === 'SAME' && st(r2, 'type') === 'KEEPNOW' && !(C.FORM_BIND in r2.patch) && !('crcf9_type' in r2.patch), r2.cells);
var r2b = C.compareRow(row(), cell({ crcf9_type: '42GP', _crcf9_form_value: '11111111-2222-3333-4444-555555555555' }), [], OPTS);
ok('다른 形態 · 42GP: 둘 다 KEEPNOW (덮어쓰지 않음 · TYPE_42_22 경고도 없음)', st(r2b, 'form') === 'KEEPNOW' && st(r2b, 'type') === 'KEEPNOW' && !Object.keys(r2b.patch).some(function (k) { return k === 'crcf9_type' || k.indexOf('form') >= 0; }), r2b.patch);
/* 3. 45R 선사 → 경고 + 고르기 */
var h3 = C.typeHint(row(), { carrier: 'ONE', carrier45r: true, otherTypes: [] });
var r3 = C.compareRow(row({ type_hint: h3 }), cell(), [], OPTS);
ok('45R 선사: タイプ CHOOSE · TYPE_CHOOSE 경고 · PATCH 에 タイプ 없음 (形態 는 들어감)', st(r3, 'type') === 'CHOOSE' && r3.warnings.indexOf('TYPE_CHOOSE') >= 0 && !('crcf9_type' in r3.patch) && !!r3.patch[C.FORM_BIND] && /45R/.test(h3), [h3, r3.patch]);
var r3b = C.compareRow(row({ type_hint: h3, type_pick: '45R' }), cell(), [], OPTS);
ok('고른 뒤: タイプ = 고른 값 (45R) PATCH · 경고는 남음 (행 체크는 담당자)', st(r3b, 'type') === 'CHOOSE' && r3b.patch.crcf9_type === '45R' && r3b.warnings.indexOf('TYPE_CHOOSE') >= 0, r3b.patch);
var r3c = C.compareRow(row({ type_hint: h3, type_pick: '20GP' }), cell(), [], OPTS);
ok('목록 밖 값 (20GP) = 안 넣음', !('crcf9_type' in r3c.patch), r3c.patch);
/* 4. 42 근거 → 경고 */
var h4 = C.typeHint(row({ size_hint: '42GP' }), { carrier: 'CARRIERX', carrier45r: false, otherTypes: [] });
var h4b = C.typeHint(row(), { carrier: 'CARRIERX', carrier45r: false, otherTypes: ['42GP', '45GP'] });
var h4c = C.typeHint(row(), { carrier: 'CARRIERX', carrier45r: false, otherTypes: ['45GP'] });
ok('42 근거: 서류·사진 size_hint · 같은 부킹 다른 칸 42GP = 이유 · 다른 칸 45GP 뿐 = 이유 없음', /42GP/.test(h4) && /42GP/.test(h4b) && h4c === null, [h4, h4b, h4c]);
ok('42 근거 행 = CHOOSE', st(C.compareRow(row({ type_hint: h4 }), cell(), [], OPTS), 'type') === 'CHOOSE');
var h5 = C.typeHint(row(), { carrier: '', carrier45r: null, otherTypes: [] });
ok('선사 못 읽음 = 고르게 함 (안전 쪽)', /船社を読めません/.test(h5) && st(C.compareRow(row({ type_hint: h5 }), cell(), [], OPTS), 'type') === 'CHOOSE', h5);
/* 5. opts 없음 = 예전 그대로 (엔진 rules.py 교차와 같음) */
var r5 = C.compareRow(row(), cell(), [], null);
ok('opts 없음: 形態 칸 없음 · タイプ FILL 45GP (예전 규칙)', !st(r5, 'form') && r5.patch.crcf9_type === '45GP' && !(C.FORM_BIND in r5.patch), r5.patch);
var r5b = C.compareRow(row(), cell(), [], { plan_fill: true, type_input: false });
ok('type_mode 없음 + type_input false = NOINPUT (예전 실전 설정 그대로)', st(r5b, 'type') === 'NOINPUT' && !st(r5b, 'form'), r5b.cells.map(function (c) { return c.state; }));
/* 6. compareIv 셈 */
var iv = C.compareIv('TST', [row(), row({ container_id: 'C-2', ct_id: 'g2', ct: 'TSTU0000002', type_hint: h3 })], { g1: cell(), g2: cell() }, {}, OPTS);
ok('compareIv: CHOOSE 1 · KEEPNOW 칸 셈 · PATCH 2 행', iv.count.cells.CHOOSE === 1 && iv.count.cells.KEEPNOW === 0 && iv.count.patch_rows === 2, iv.count);
/* 7. formTypeBlank */
ok('formTypeBlank: CT 있는 칸 중 形態 또는 タイプ 빈칸만', C.formTypeBlank({ a: cell({ crcf9_container_no: 'X1', crcf9_type: '45GP', _crcf9_form_value: G }), b: cell({ crcf9_container_no: 'X2', crcf9_type: '45GP' }),
  c: cell({ crcf9_container_no: 'X3', _crcf9_form_value: G }), d: cell() }) === 2);

/* 8. Writer: 다시 GET 확인 · 실패 · 元に戻す ($ref) */
function fakeServer(opt) {
  opt = opt || {};
  var db = { g1: cell({ '@odata.etag': 'W/"1"' }) }, log = [];
  var fetchFn = function (url, o) {
    log.push([o.method, url]);
    var m = /crcf9_container_informations\(([^)]+)\)(\/crcf9_form\/\$ref)?/.exec(url), c = db[m[1]];
    var resp = function (status, body) { return Promise.resolve({ status: status, ok: status < 300, json: function () { return Promise.resolve(body); } }); };
    if (o.method === 'GET') { if (opt.getFail && log.filter(function (x) { return x[0] === 'GET'; }).length > 1) return resp(500, {}); return resp(200, JSON.parse(JSON.stringify(c))); }
    if (o.method === 'PATCH') {
      var b = JSON.parse(o.body);
      if (b[C.FORM_BIND] && !opt.dropForm) c._crcf9_form_value = C.bindGuid(b[C.FORM_BIND]);
      delete b[C.FORM_BIND];
      Object.assign(c, b); c['@odata.etag'] = 'W/"2"'; return resp(204, {});
    }
    if (o.method === 'DELETE' && m[2]) { c._crcf9_form_value = null; c['@odata.etag'] = 'W/"3"'; return resp(204, {}); }
    return resp(405, {});
  };
  return { db: db, log: log, w: new C.Writer({ baseUrl: 'https://dv.example.invalid', enabled: true, fetchFn: fetchFn }) };
}
var p1 = r1.patches || { ct_id: 'g1', if_match: 'W/"1"', body: r1.patch };
var chain = [];
var s1 = fakeServer();
chain.push(s1.w.apply({ ct_id: 'g1', if_match: 'W/"1"', body: r1.patch }).then(function (r) {
  ok('入力: OK · 기록 fields 에 _crcf9_form_value · 전 null · 후 BALES guid · GET→PATCH→GET', r.result === 'OK' && r.cell.fields.indexOf('_crcf9_form_value') >= 0 && r.cell.before._crcf9_form_value === null
    && r.cell.after._crcf9_form_value === G && r.cell.after.crcf9_type === '45GP' && s1.log.map(function (x) { return x[0]; }).join(',') === 'GET,PATCH,GET', [r.cell, s1.log]);
  return s1.w.clearForm('g1').then(function (r2) {
    ok('元に戻す 形態: DELETE …/crcf9_form/$ref → 다시 GET 빈칸 · 기록 전 guid 후 null', r2.result === 'OK' && s1.db.g1._crcf9_form_value === null && r2.cell.before._crcf9_form_value === G
      && /\/crcf9_form\/\$ref$/.test(s1.log[s1.log.length - 2][1]) && s1.log[s1.log.length - 2][0] === 'DELETE', [r2, s1.log.slice(-3)]);
  });
}));
var s2 = fakeServer({ dropForm: true });
chain.push(s2.w.apply({ ct_id: 'g1', if_match: 'W/"1"', body: r1.patch }).then(function (r) {
  ok('다시 GET 값 다름 (形態 안 들어감) = REREAD_DIFF (field = 形態 odata.bind)', r.result === 'REREAD_DIFF' && r.field === C.FORM_BIND, r.result);
}));
var s3 = fakeServer({ getFail: true });
chain.push(s3.w.apply({ ct_id: 'g1', if_match: 'W/"1"', body: r1.patch }).then(function (r) {
  ok('다시 GET 실패 = REREAD_DIFF (성공으로 안 셈)', r.result === 'REREAD_DIFF', r.result);
}));
var s4 = fakeServer();
s4.db.g1.crcf9_type = '45GP';
chain.push(s4.w.apply({ ct_id: 'g1', if_match: 'W/"1"', body: { crcf9_type: null } }).then(function (r) {
  ok('元に戻す タイプ (전 빈칸) = PATCH null → 다시 GET 빈칸 확인', r.result === 'OK' && s4.db.g1.crcf9_type === null, [r.result, s4.db.g1.crcf9_type]);
}));
Promise.all(chain).then(function () {
  res.forEach(function (x) { console.log(x); });
  console.log(JSON.stringify({ n: res.length, ng: ng }));
  process.exit(ng ? 1 : 0);
}).catch(function (e) { console.log('ERROR ' + e.stack); process.exit(2); });
