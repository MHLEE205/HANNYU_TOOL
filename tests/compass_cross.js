// ✦ Powered by LEENAI Automation System — Compass入力 交差試験 (node): tests/compass_cases.json の input → js/compass.js → expected と比較
// cases = R6 の 26 件 (opts なし) · cases_v058 = v0.2.1 follow_same_cond_slot (input.opts) — 引数に別の JSON を渡すとそれを読む (実データ写し · レポ外)
'use strict';
const fs = require('fs');
const path = require('path');
const C = require(path.join(__dirname, '..', 'js', 'compass.js'));
const file = process.argv[2] || path.join(__dirname, 'compass_cases.json');
if (!fs.existsSync(file)) { console.error('compass_cases.json なし — 먼저 python tools/make_test_data.py (레포에 넣지 않는 가명 시험 데이터)'); process.exit(2); }
const data = JSON.parse(fs.readFileSync(file, 'utf8'));
const cases = (data.cases || []).concat(data.cases_v058 || []);
function canon(x) {
  if (Array.isArray(x)) return x.map(canon);
  if (x && typeof x === 'object') { const o = {}; Object.keys(x).sort().forEach(k => { o[k] = canon(x[k]); }); return o; }
  return x;
}
let ok = 0; const bad = [];
for (const c of cases) {
  const got = C.compareIv(c.input.iv, c.input.rows, c.input.cells, c.input.dups, c.input.opts || null);
  if (JSON.stringify(canon(got)) === JSON.stringify(canon(c.expected))) ok += 1; else bad.push(c.name);
}
console.log(JSON.stringify({ cases: cases.length, r6: (data.cases || []).length, v058: (data.cases_v058 || []).length, same: ok, different: bad.slice(0, 20), different_n: bad.length }));
process.exit(bad.length ? 1 : 0);
