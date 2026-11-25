/* ✦ Powered by LEENAI Automation System — v0.3.80 (R12Y51 · #399) js/mergepick.js の計算の試験 (仮の値だけ · 実番号 0)
   node tests/mergepick_cases.js → 「ok n」 */
'use strict';
var MP = require('../js/mergepick.js');
var n = 0;
function eq(a, b, m) { var x = JSON.stringify(a), y = JSON.stringify(b); if (x !== y) { console.error('NG ' + m + ': ' + x + ' != ' + y); process.exit(1); } n++; }

function opts(extra) {
  var o = { st: function (r) { return r.st; }, vals: function (r) { return r; }, frozen: function (r) { return !!r.input_frozen; }, allow: { PKA: ['PKB'] } };
  Object.keys(extra || {}).forEach(function (k) { o[k] = extra[k]; });
  return o;
}
/* 写真の行 (枠あり · 自動OK) · 書類だけの再送の行 (枠なし) */
var A = { container_id: 'C-A', no: 1, ct: 'TSTU1234565', seal: 'AB123456', n_w: '20,010', t_w: 2000, bales: 21, work_date: '2026-11-20', packer: 'PKA', slot_guid: 'S1', has_photos: true, photos: 12, has_docs: true, st: '自動OK' };
var D = { container_id: 'C-D', no: 2, ct: 'TSTU1234556', seal: 'AB-123456', n_w: 20010, t_w: 2000, bales: 21, work_date: '2026-11-20', packer: 'PKA', slot_guid: null, has_photos: false, photos: 0, has_docs: true, st: '再確認', reasons: ['SLOT_CONFLICT'] };
var X = { container_id: 'C-X', no: 3, ct: 'ZZZU9999990', seal: 'QQ999999', n_w: 18000, t_w: 1900, bales: 18, work_date: '2026-11-21', packer: 'PKA', slot_guid: 'S2', has_photos: true, photos: 10, has_docs: true, st: '自動OK' };
var O = { container_id: 'C-O', no: 4, ct: 'TSTU1234565', seal: 'AB123456', n_w: 20010, packer: 'PKZ', slot_guid: 'S3', has_photos: true, has_docs: true, st: '自動OK' };
var B = { container_id: 'C-B', no: 5, ct: 'TSTU1234000', seal: 'AB123456', n_w: 20010, packer: 'PKB', slot_guid: 'S4', has_photos: true, has_docs: false, st: '受信中' };
var iv = { rows: [A, D, X, O, B] };

/* ボタンを出す行 */
eq(MP.eligible(D, opts()), true, '枠外 · 書類だけ');
eq(MP.eligible(A, opts()), false, '自動OK · 枠あり · 写真と書類 = 出さない');
eq(MP.eligible(B, opts()), true, '写真だけ · 受信中');
eq(MP.eligible(Object.assign({}, D, { input_frozen: true }), opts()), false, '入力済 = 出さない');

/* 候補 · おすすめ順 */
var cs = MP.candidates(iv, D, opts());
eq(cs.map(function (c) { return c.r.container_id; }), ['C-A', 'C-B', 'C-X'], '同じ業者 + slot_allow (PKB) · 他業者 PKZ なし · おすすめ順');
eq(cs[0].marks, ['nw', 'seal', 'ct2', 'wd'], 'N/W 同じ · シール 同じ (ハイフンは無視) · CT 2 文字違い · 作業日');
eq(MP.score(Object.assign({}, D, { seal: 'XY123456' }), A, opts()).marks.indexOf('seal_prefix') >= 0, true, 'シールの前の文字だけ違う = 印');
eq(MP.score(Object.assign({}, D, { seal: 'AB123457' }), A, opts()).marks.indexOf('seal1') >= 0, true, 'シール数字 1 文字違い = 印');
/* 自動補正 の行 = 直す前の CT でも近さを見る */
var D2 = Object.assign({}, D, { ct: 'TSTU7777770', ct_read: ['TSTU1234566'] });
eq(MP.candidates(iv, D2, opts())[0].marks.indexOf('ct1') >= 0, true, '直す前の CT で 1 文字違い');

/* まとめ方 */
var p = MP.plan(D, A, opts());
eq([p.from.container_id, p.into.container_id, p.block, p.warn, p.after], ['C-D', 'C-A', [], [], 'auto'], '自動OK 相手 = 書類だけの行 → 写真の行 · 自動OK のまま');
eq(p.diff, ['ct'], 'CT だけ違う (シール ハイフン · 重量 カンマ = 同じ)');
var p2 = MP.plan(A, D, opts());
eq([p2.from.container_id, p2.into.container_id], ['C-D', 'C-A'], '写真の行から押しても 書類だけの行が まとめる側');
eq(MP.plan(D, Object.assign({}, A, { st: '再確認' }), opts()).after, 'check', '再確認 相手 = 一緒に確認');
eq(MP.plan(D, Object.assign({}, A, { st: '確認済' }), opts()).after, 'human', '確認済 相手 = その値');
eq(MP.plan(D, X, opts()).warn, ['seal', 'n_w', 't_w'], '重量 · シール 違う = 警告 (チェックが要る)');
eq(MP.plan(B, A, opts()).block, ['photos_both'], '写真のある行どうし = まとめない');
eq(MP.plan(Object.assign({}, D, { input_frozen: true }), A, opts()).block, ['frozen'], '入力済 の行 = まとめる側にできない');
eq(MP.plan(Object.assign({}, A, { input_frozen: true }), Object.assign({}, D, { input_frozen: true }), opts()).block, ['frozen'], '入力済 どうし = 止める');
eq(MP.plan(D, Object.assign({}, A, { ct: '' }), opts()).block, ['no_ct'], 'まとめ先 CT なし');
/* 書類だけ 2 行: 枠のある方が残る */
var E = Object.assign({}, D, { container_id: 'C-E', slot_guid: 'S5', st: '再確認' });
var p3 = MP.plan(D, E, opts());
eq([p3.from.container_id, p3.into.container_id], ['C-D', 'C-E'], '書類だけ 2 行 = 枠のある行に');
var p4 = MP.plan(E, D, opts());
eq([p4.from.container_id, p4.into.container_id], ['C-D', 'C-E'], '枠のある行から押しても 同じ');
console.log('ok ' + n);
