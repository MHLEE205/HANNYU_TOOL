/* ✦ Powered by LEENAI Automation System — 入力の形チェック (エンジン engine/actions/apply.py norm_value と同じ規則) */
'use strict';
window.C01 = window.C01 || {};

C01.validate = (function () {
  var LETTER = {};
  var vals = [10, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 34, 35, 36, 37, 38];
  var CHECKDIGIT_MSG = 'チェックディジットが合いません。もう一度確認してください';
  'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('').forEach(function (c, i) { LETTER[c] = vals[i]; });

  /* ISO 6346 チェックデジット (engine/classify/text.py iso6346_ok と同じ計算) */
  function ctCheckOk(ct) {
    if (!/^[A-Z]{4}\d{7}$/.test(ct)) return false;
    var s = 0;
    for (var i = 0; i < 10; i++) {
      var ch = ct.charAt(i);
      s += (/[A-Z]/.test(ch) ? LETTER[ch] : parseInt(ch, 10)) * Math.pow(2, i);
    }
    return (s % 11) % 10 === parseInt(ct.charAt(10), 10);
  }

  /* → {ok, value, error, warn}  field = ct · seal · n_w · t_w · bales · work_date */
  function field(name, raw, rules) {
    rules = rules || (C01.RULES || {});
    var s = String(raw == null ? '' : raw).trim();
    if (name === 'n_w' || name === 't_w' || name === 'bales') {
      s = s.replace(/,/g, '');
      if (!/^\d{1,6}$/.test(s) || parseInt(s, 10) <= 0) return { ok: false, error: '正の整数で入力してください（6桁まで）' };
      return { ok: true, value: parseInt(s, 10) };
    }
    if (name === 'ct') {
      s = s.replace(/[\s-]/g, '').toUpperCase();
      if (!/^[A-Z]{4}\d{7}$/.test(s)) return { ok: false, error: 'CT 番号は 英字4 + 数字7 です' };
      if (!ctCheckOk(s)) {
        /* #109 ③: 確認窓 (CHECKDIGIT_MSG) → OK なら override: CT_CHECKDIGIT_OVERRIDE で保存 (確認済 · 自動OK にしない) */
        if (rules.ctCheckDigitWrong === 'warn') return { ok: true, value: s, warn: CHECKDIGIT_MSG, override: 'CT_CHECKDIGIT_OVERRIDE' };
        return { ok: false, error: 'チェックデジットが合いません — 原本を確認してください' };
      }
      return { ok: true, value: s };
    }
    if (name === 'seal') {
      s = s.replace(/\s/g, '').toUpperCase();
      if (!s) return { ok: false, error: 'シール番号を入力してください' };
      return { ok: true, value: s };
    }
    if (name === 'work_date') {
      if (!/^\d{4}-\d{2}-\d{2}$/.test(s) || isNaN(Date.parse(s + 'T00:00:00Z'))) return { ok: false, error: '作業日は YYYY-MM-DD で入力してください' };
      return { ok: true, value: s };
    }
    return { ok: false, error: '不明な項目: ' + name };
  }

  return { ctCheckOk: ctCheckOk, field: field, CHECKDIGIT_MSG: CHECKDIGIT_MSG };
})();
