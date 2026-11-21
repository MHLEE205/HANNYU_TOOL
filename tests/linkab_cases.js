// ✦ Powered by LEENAI Automation System — v0.3.67 (R12Y5 · 決定 #356 穴 3) js/linkab.js 試験 (node · 仮名の値だけ · 実際の番号 0)
// (a) おすすめ順 (CT の読み違いでも シール · 重量で上) · (b) 空き枠必須 · 入力済は動かせない · 空き枠なし = 止める · 条件の違い
'use strict';
const path = require('path');
const L = require(path.join(__dirname, '..', 'js', 'linkab.js')).linkAb;
let ok = 0; const bad = [];
function t(name, cond, got) { if (cond) ok += 1; else bad.push(name + ' — ' + JSON.stringify(got)); }

// 5 枠 · 5 行 · 同じ条件 · CT / シール 連番 · 重量ほぼ同じ (R12W の形を仮名で)
const S = ['s1', 's2', 's3', 's4', 's5'].map((g, i) => ({ slot_guid: g, packer: 'PK', plant: 'P1', item: 'IT', work_date: '2026-01-10', incoterms: '店頭', type: '45GP', seq: i + 1 }));
const R = [
  { container_id: 'c1', ct: 'ZZZU1000017', seal: 'SL0010001', n_w: 21000, t_w: 3750, bales: 24, slot_guid: 's1' },
  { container_id: 'c2', ct: 'ZZZU1000022', seal: 'SL0010002', n_w: 21010, t_w: 3740, bales: 24, slot_guid: 's2' },
  { container_id: 'c3', ct: 'ZZZU1000038', seal: 'SL0010003', n_w: 20990, t_w: 3750, bales: 23, slot_guid: 's3' },
  { container_id: 'c4', ct: 'ZZZU1000043', seal: 'SL0010004', n_w: 21000, t_w: 3760, bales: 24, slot_guid: 's4' },
  { container_id: 'c5', ct: 'ZZZU1000059', seal: 'SL0010005', n_w: 21000, t_w: 3750, bales: 24, slot_guid: 's5' }
];
const used = {}; R.forEach(r => { used[r.slot_guid] = r; });
// 読んだ行 1 = c5 (CT 4 文字読み違い · シール 1 文字目違い) · 読んだ行 2 = c1 (CT 同じ · シール 1 文字目違い)
const reads = [{ ct: 'XYWU1000759', seal: 'TL0010005', n_w: '21,000', t_w: '3,750', bales: 24 }, { ct: 'ZZZU1000017', seal: 'TL0010001', n_w: 21000, t_w: 3750, bales: 24 }];
const rk = L.rank(reads, R);
t('rank: 上位 2 = 読んだ 2 行の行 (c1 · c5)', rk.slice(0, 2).map(x => x.row.container_id).sort().join() === 'c1,c5', rk.map(x => [x.row.container_id, x.score]));
t('rank: おすすめ = 2 つだけ', rk.filter(x => x.rec).length === 2, rk.map(x => x.rec));
t('rank: 全部の行が出る (5)', rk.length === 5, rk.length);
t('rank: 理由に シール · N/W', rk[0].why.some(w => w.indexOf('N/W') === 0), rk[0].why);
// 読んだ値なし = 行の順 · おすすめ 0
const rk0 = L.rank([], R);
t('rank: 読んだ値なし = 行の順 · おすすめ 0', rk0.map(x => x.row.container_id).join() === 'c1,c2,c3,c4,c5' && !rk0.some(x => x.rec), rk0.map(x => x.row.container_id));
// CT の無い行は 付けられない
const rk1 = L.rank(reads, R.concat([{ container_id: 'c6', ct: null, seal: null, slot_guid: null }]));
t('rank: CT 無し行は出ない', !rk1.some(x => x.row.container_id === 'c6'), rk1.length);
// 重量だけ近い (弱い) = おすすめにしない
const rk2 = L.rank([{ n_w: 21000 }], R);
t('rank: 重量 1 つだけ = おすすめ 0', !rk2.some(x => x.rec), rk2.map(x => x.score));
// 数 · 文字の近さ
t('numSim 2% 以内 0.8 · 同じ 1 · 遠い 0', L.numSim('21,000', 21000) === 1 && L.numSim(21000, 21300) === 0.8 && L.numSim(21000, 15000) === 0, null);
t('strSim 同じ 1 · 無い null', L.strSim('ab c', 'ABC') === 1 && L.strSim(null, 'A') === null, null);

// plan
const base = { slots: S, used: used, rows: R, frozen: {} };
t('plan: まだ (a)/(b) なし = need ab', L.plan(Object.assign({}, base)).need === 'ab', null);
t('plan: (a) 行なし = need row', L.plan(Object.assign({ ab: 'a' }, base)).need === 'row', null);
const pa = L.plan(Object.assign({ ab: 'a', rowId: 'c3', slot: 's1' }, base));
t('plan: (a) = attach · 行の枠 (選んだ枠より行の枠)', pa.mode === 'attach' && pa.container_id === 'c3' && pa.slot_guid === 's3' && !pa.block && !pa.need, pa);
const pa2 = L.plan({ ab: 'a', rowId: 'c9', slots: S, used: {}, rows: [{ container_id: 'c9', ct: 'ZZZU1000064', slot_guid: null }], frozen: {} });
t('plan: (a) 枠のない行 = 止める', !!pa2.block, pa2);
t('plan: (a) 入力済の行にも付けられる (値は変わらない)', !L.plan(Object.assign({ ab: 'a', rowId: 'c2' }, base, { frozen: { c2: 1 } })).block, null);
t('plan: (b) 枠なし = need slot', L.plan(Object.assign({ ab: 'b' }, base)).need === 'slot', null);
const pb0 = L.plan(Object.assign({ ab: 'b', slot: 's2' }, base));
t('plan: (b) 使用中 · 空き枠なし = 止める (空き枠がありません)', /空き枠がありません/.test(pb0.block || ''), pb0);
const pbf = L.plan(Object.assign({ ab: 'b', slot: 's2' }, base, { frozen: { c2: 1 } }));
t('plan: (b) 入力済の行 = 止める (入力済みの行は動かせません)', /入力済みの行は動かせません/.test(pbf.block || ''), pbf);
const S6 = S.concat([{ slot_guid: 's6', packer: 'PK', plant: 'P1', item: 'IT', work_date: '2026-01-11', incoterms: '店頭', type: '45GP', seq: 6 },
  { slot_guid: 's7', packer: 'OTHER', plant: 'P9', item: 'IT', work_date: '2026-01-10', incoterms: '店頭', type: '45GP', seq: 7 }]);
const b6 = { slots: S6, used: used, rows: R, frozen: {} };
const pbn = L.plan(Object.assign({ ab: 'b', slot: 's2' }, b6));
t('plan: (b) 使用中 · 空き枠あり = need move · 候補 = 同じ業者の空き (s6 だけ)', pbn.need === 'move' && pbn.targets.map(s => s.slot_guid).join() === 's6', pbn);
const pbm = L.plan(Object.assign({ ab: 'b', slot: 's2', move: 's6' }, b6));
t('plan: (b) 移す枠を選んだ = move_to_slot', pbm.move_to_slot === 's6' && pbm.slot_guid === 's2' && pbm.mode === 'new' && !pbm.need && !pbm.block, pbm);
t('plan: (b) 候補でない枠 (他の業者) = まだ need move', L.plan(Object.assign({ ab: 'b', slot: 's2', move: 's7' }, b6)).need === 'move', null);
const pbe = L.plan(Object.assign({ ab: 'b', slot: 's6' }, b6));
t('plan: (b) 空き枠 = そのまま (移動なし)', pbe.slot_guid === 's6' && !pbe.move_to_slot && !pbe.need && !pbe.block, pbe);
t('plan: (b) 業者の空き枠すべて = 移動なし', !L.plan(Object.assign({ ab: 'b', slot: 's2', scopeAll: true }, b6)).need, null);
// 条件の違い
t('condDiff: 作業予定日', L.condDiff(S6[1], S6[5]).join() === '作業予定日', L.condDiff(S6[1], S6[5]));
t('condDiff: 営業所 (同じ条件 = 0)', L.condDiff(S6[1], S6[6]).join() === '営業所' && L.condDiff(S6[0], S6[1]).length === 0, L.condDiff(S6[1], S6[6]));
t('moveTargets: 行の業者の空き枠も', L.moveTargets(S6, used, S6[1], { packer: 'OTHER' }).map(s => s.slot_guid).join() === 's6,s7', null);

console.log(JSON.stringify({ checks: ok + bad.length, ok: ok, ng: bad.length, bad: bad.slice(0, 10) }));
process.exit(bad.length ? 1 : 0);
