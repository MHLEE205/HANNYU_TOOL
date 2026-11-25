// ✦ Powered by LEENAI Automation System — v0.3.83 (R12Y55 · 決定 #401 · D-00 要請) js/clearance.js 試験 (node · 仮名の値だけ · 実際の番号 0 · 通信 0)
// ① エンジン customs_done.py と同じ例 (tests/clearance_cases.json) ② 欄単位 · eTag · 412 読み直し (最大 3) ③ 書く場所は 2 か所だけ ④ 影 = 本番は読むだけ
'use strict';
const path = require('path');
const fs = require('fs');
global.window = global;
const store = {};
global.localStorage = { getItem: k => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = String(v); } };
window.localStorage = global.localStorage;
require(path.join(__dirname, '..', 'js', 'config.js'));
require(path.join(__dirname, '..', 'js', 'source.js'));
require(path.join(__dirname, '..', 'js', 'clearance.js'));
const CL = C01.clearance;
let ok = 0; const bad = [];
function t(name, cond, got) { if (cond) ok += 1; else bad.push(name + ' — ' + JSON.stringify(got)); }
const eq = (a, b) => JSON.stringify(a) === JSON.stringify(b);

// ① 同じ例
const cases = JSON.parse(fs.readFileSync(path.join(__dirname, 'clearance_cases.json'), 'utf8'));
t('例の数 ≥ 11', cases.length >= 11, cases.length);
cases.forEach(c => {
  const g = CL.planOne(c.rec ? JSON.parse(JSON.stringify(c.rec)) : null, { at: c.at, source: 'tool_sent' }, c.old, null);
  t('例: ' + c.name, g.kind === c.kind && eq(g.set, c.set), g);
});
const engCases = path.join(__dirname, '..', '..', 'engine_r12y55', 'engine', 'output', 'customs_done.py');
t('jstDay: UTC 15:30 = 翌日 (JST)', CL.jstDay('2026-11-23T15:30:00.000Z') === '2026-11-24', CL.jstDay('2026-11-23T15:30:00.000Z'));

// ② 仮の Graph (ファイル内容 · eTag · If-Match が違えば 412)
const LIVE = C01.CLEARANCE.livePath, COPY = C01.CLEARANCE.copyPath;
function fakeGraph(files, opt) {
  opt = opt || {};
  const calls = [];
  global.LEENAI = { SP: { DRIVE_ID: 'DRV' }, auth: { token: () => Promise.resolve('tok'), status: { graph: 'ok' } } };
  global.fetch = function (url, o) {
    o = o || {};
    const m = o.method || 'GET';
    const dec = decodeURIComponent(url);
    const f = Object.keys(files).find(p => dec.indexOf('/root:/' + p + ':') >= 0) || (dec.indexOf('_actions/clearance_shadow/') >= 0 ? '_shadow' : null);
    calls.push({ m, f, h: o.headers || {}, url: dec });
    const res = (status, body) => Promise.resolve({ ok: status >= 200 && status < 300, status, json: () => Promise.resolve(JSON.parse(body)), text: () => Promise.resolve(body) });
    if (f === '_shadow') { files._shadowRecs = (files._shadowRecs || []).concat([JSON.parse(o.body)]); return res(201, '{}'); }
    if (!f) return res(404, '{}');
    const F = files[f];
    if (m === 'GET' && dec.indexOf('?$select=') >= 0) return res(200, JSON.stringify({ id: 'x', eTag: F.eTag }));
    if (m === 'GET') {
      if (opt.beforeContent && f === COPY) { opt.beforeContent(F); opt.beforeContent = null; }
      return res(200, F.text);
    }
    if (m === 'PUT') {
      if (opt.force412 && opt.force412 > 0) { opt.force412 -= 1; return res(412, '{}'); }
      if ((o.headers || {})['If-Match'] !== F.eTag) return res(412, '{}');
      F.text = o.body; F.n += 1; F.eTag = '"{E},' + F.n + '"';
      return res(200, '{}');
    }
    return res(405, '{}');
  };
  return calls;
}
function file(obj) { return { text: JSON.stringify(obj, null, 2), eTag: '"{E},1"', n: 1 }; }
const base = () => ({ last_updated: 'x', records: {
  'TST0001-01': { tsukan_irai: false, tsukan_status: '未', updated_by: 'p', updated_at: 'y' },
  'TST0002-01': { tsukan_irai: true, tsukan_status: 'ED未', updated_by: 'p', updated_at: 'y' },
  'TST0004-01': { tsukan_irai: false, tsukan_status: '未', updated_by: 'p', updated_at: 'y', memo: 'keep' } },
  cotecna: { 'TST0001-01|X|1': { report_status: '未' } }, shipping: { 'TST0001-01': { dep: '確認', fd_date: '' } }, extra: [1] });
function state(meta) {
  const S = { info: { mode: 'graph' }, me: { email: 'user1@example.invalid' }, meta: meta ? { clearance: meta } : null,
    jik: { ivs: [
      { iv_no: 'TST0001-01', customs_done: { at: '2026-11-26T01:00:00.000Z', source: 'tool_sent', by: 'u', n: 1 } },
      { iv_no: 'TST0002-01', customs_done: { at: '2026-11-25T01:00:00.000Z', source: 'staff_mail', by: 'u', n: 2 } },
      { iv_no: 'TST0003-01', customs_done: { at: '2026-11-20T01:00:00.000Z', source: 'staff_mail', by: 'u', n: 1 } },
      { iv_no: 'TST0004-01' },
      { iv_no: 'TST0006-01', iv_changed_from: ['TST0005-01'] }] } };
  S.src = new (C01.sources.Graph)();
  C01.app = { _api: () => ({ S, graphMode: () => true, jstNow: () => '2026-11-26T10:00:00+09:00' }) };
  return S;
}
const META = { mode: 'shadow', live_path: LIVE, copy_path: COPY, backfill_from: '2026-11-24', shadow_from: '2026-11-26' };

(async function () {
  // 影: 本番 = 読むだけ · 試験用コピー = 欄単位で書く
  let files = { [LIVE]: file(base()), [COPY]: file(base()) };
  let calls = fakeGraph(files);
  state(META);
  const liveBefore = files[LIVE].text;
  let rec = await CL.run('open');
  t('影: 本番 PUT 0', !calls.some(c => c.m === 'PUT' && c.f === LIVE) && files[LIVE].text === liveBefore, calls.map(c => c.m + ' ' + c.f));
  t('影: コピー PUT 1 (If-Match 付き)', calls.filter(c => c.m === 'PUT' && c.f === COPY).length === 1 && calls.filter(c => c.m === 'PUT' && c.f === COPY)[0].h['If-Match'] === '"{E},1"', calls.filter(c => c.m === 'PUT'));
  const cp = JSON.parse(files[COPY].text), b0 = base();
  t('コピー: 書く IV の 2 欄 + updated_by C-01', cp.records['TST0001-01'].tsukan_irai === true && cp.records['TST0001-01'].tsukan_irai_at === '2026-11-26T01:00:00.000Z' && cp.records['TST0001-01'].updated_by === 'C-01' && cp.records['TST0001-01'].tsukan_status === '未', cp.records['TST0001-01']);
  t('コピー: 人のチェック済 = 日付だけ', cp.records['TST0002-01'].tsukan_irai_at === '2026-11-25T01:00:00.000Z' && cp.records['TST0002-01'].tsukan_status === 'ED未', cp.records['TST0002-01']);
  t('コピー: 送付なし IV · 11/24 前 = そのまま', eq(cp.records['TST0004-01'], b0.records['TST0004-01']) && !cp.records['TST0003-01'], cp.records['TST0004-01']);
  t('コピー: cotecna · shipping · extra · 順 そのまま', eq([cp.cotecna, cp.shipping, cp.extra, Object.keys(cp)], [b0.cotecna, b0.shipping, b0.extra, Object.keys(b0)]), Object.keys(cp));
  t('コピー: 2 字下げ (PORTAL と同じ)', files[COPY].text.indexOf('{\n  "last_updated"') === 0, files[COPY].text.slice(0, 20));
  t('記録: _actions/clearance_shadow 1 件 · 一覧 = 書く 2 + 日付だけ', (files._shadowRecs || []).length === 1 && rec.live.counts.write_n === 2 && rec.live.counts.kinds.fill_at === 1 && rec.live.status === 'read_only', rec && rec.live);
  t('記録: old は一覧に入れない', !rec.live.rows.some(r => r.kind === 'old'), rec.live.rows.map(r => r.kind));
  t('記録: copy.wrote = 2 IV', eq(rec.copy.wrote, ['TST0001-01', 'TST0002-01']) && rec.copy.status === 'ok', rec.copy);
  // 2 回目 = 同じ一覧 · コピーは書くもの無し → PUT 0 · 記録 0
  const n1 = calls.length;
  rec = await CL.run('timer');
  t('2 回目: PUT 0 · 記録 増えない', !calls.slice(n1).some(c => c.m === 'PUT') && files._shadowRecs.length === 1, calls.slice(n1).map(c => c.m + ' ' + c.f));

  // 412 1 回 → 読み直し → 成功 (その間に他の人が別の IV を保存)
  files = { [LIVE]: file(base()), [COPY]: file(base()) };
  calls = fakeGraph(files, { beforeContent: F => { const o = JSON.parse(F.text); o.records['TST0004-01'].tsukan_status = 'ED未'; F.text = JSON.stringify(o, null, 2); F.n += 1; F.eTag = '"{E},' + F.n + '"'; } });
  for (const k in store) delete store[k];
  state(META);
  rec = await CL.run('open');
  const puts = calls.filter(c => c.m === 'PUT' && c.f === COPY);
  const cp2 = JSON.parse(files[COPY].text);
  t('412 → 読み直して 2 回目で成功', puts.length >= 1 && rec.copy.status === 'ok', rec.copy);
  t('他の人の変更 (別 IV) が残る', cp2.records['TST0004-01'].tsukan_status === 'ED未', cp2.records['TST0004-01']);
  // 412 が 3 回 = あきらめ (ファイルそのまま)
  files = { [LIVE]: file(base()), [COPY]: file(base()) };
  const before3 = files[COPY].text;
  calls = fakeGraph(files, { force412: 5 });
  for (const k in store) delete store[k];
  state(META);
  rec = await CL.run('open');
  t('412 × 3 = 書かない · PUT 3 回', rec.copy.status === '412x3' && calls.filter(c => c.m === 'PUT' && c.f === COPY).length === 3 && files[COPY].text === before3, rec.copy);

  // 書く場所の制限
  const g = new (C01.sources.Graph)();
  fakeGraph({ [LIVE]: file(base()), [COPY]: file(base()), 'other/x.json': file(base()) });
  let e1 = null; try { await g.clearancePut(LIVE, '{}', '"{E},1"', true); } catch (e) { e1 = e.message; }
  t('本番 PUT = C01.CLEARANCE.live false なら拒否', !!e1, e1);
  let e2 = null; try { await g.clearancePut('other/x.json', '{}', '"{E},1"', false); } catch (e) { e2 = e.message; }
  t('他の場所 = 拒否', !!e2, e2);
  let e3 = null; try { await g.clearancePut(COPY, '{}', '', false); } catch (e) { e3 = e.message; }
  t('eTag なし = 拒否 (丸ごとの上書きなし)', !!e3, e3);
  let e4 = null; try { await g.clearanceRead('other/x.json', false); } catch (e) { e4 = e.message; }
  t('他の場所は 読まない', !!e4, e4);

  // エンジン meta が無い · コピーの場所が違う = 何もしない
  files = { [LIVE]: file(base()), [COPY]: file(base()) };
  calls = fakeGraph(files);
  state(null);
  t('meta.clearance 無し = 通信 0', (await CL.run('open')) === null && calls.length === 0, calls.length);
  state(Object.assign({}, META, { copy_path: 'x/y.json' }));
  t('コピーの場所が設定と違う = 通信 0', (await CL.run('open')) === null && calls.length === 0, calls.length);
  // meta が live でも TOOL の live: false = 影のまま
  state(Object.assign({}, META, { mode: 'live' }));
  for (const k in store) delete store[k];
  rec = await CL.run('open');
  t('meta live + TOOL live false = 影 (本番 PUT 0)', rec.mode === 'shadow' && !calls.some(c => c.m === 'PUT' && c.f === LIVE), rec && rec.mode);

  // 送った直後 (エンジンの customs_done まだ) = その IV を書く (影 = コピー)
  files = { [LIVE]: file(base()), [COPY]: file(base()) };
  calls = fakeGraph(files);
  const S2 = state(META);
  S2.jik.ivs = [{ iv_no: 'TST0004-01' }];
  rec = await CL.sent('TST0004-01', '2026-11-26T05:00:00.000Z');
  t('送った直後: その IV を書く', eq(rec.copy.wrote, ['TST0004-01']) && JSON.parse(files[COPY].text).records['TST0004-01'].memo === 'keep', rec.copy);

  console.log('== ' + ok + '/' + (ok + bad.length) + ' OK');
  if (bad.length) { bad.forEach(b => console.log('NG ' + b)); process.exit(1); }
})().catch(e => { console.log('ERR ' + (e && e.stack)); process.exit(1); });
