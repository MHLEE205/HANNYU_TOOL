/* ✦ Powered by LEENAI Automation System — 無圧縮 ZIP (STORE) を作る小さな関数 (v0.3.76 · R12Y37 · #380 ③)
   - 写真 (JPEG) · 搬入票 (PDF · 画像) はもう圧縮されているので 無圧縮 で十分 (大きさはほぼ同じ · 速い · 外部ライブラリ 0)
   - 名前は UTF-8 (一般フラグ bit 11) · Windows の 「すべて展開」 · 7-Zip · Mac で日本語名のまま開ける
   - C01.zipStore(files) : files = [{ name: 'CT/xxx.jpg', data: Uint8Array, date: Date }] → Uint8Array (ZIP 全体) */
'use strict';
window.C01 = window.C01 || {};

(function () {
  var T = null;
  function table() {
    if (T) return T;
    T = new Uint32Array(256);
    for (var n = 0; n < 256; n++) {
      var c = n;
      for (var k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1;
      T[n] = c >>> 0;
    }
    return T;
  }
  function crc32(u8) {
    var t = table(), c = 0xFFFFFFFF;
    for (var i = 0; i < u8.length; i++) c = t[(c ^ u8[i]) & 0xFF] ^ (c >>> 8);
    return (c ^ 0xFFFFFFFF) >>> 0;
  }
  function dosTime(d) {
    d = d || new Date();
    return {
      time: ((d.getHours() << 11) | (d.getMinutes() << 5) | (Math.floor(d.getSeconds() / 2))) & 0xFFFF,
      date: ((((d.getFullYear() - 1980) & 0x7F) << 9) | ((d.getMonth() + 1) << 5) | d.getDate()) & 0xFFFF
    };
  }
  function utf8(s) { return new TextEncoder().encode(String(s)); }

  C01.zipStore = function (files) {
    var parts = [], central = [], off = 0, seen = {};
    (files || []).forEach(function (f) {
      var name = String(f.name || '').replace(/\\/g, '/').replace(/^\/+/, '');
      if (!name || seen[name]) throw new Error('ZIP: 名前が空 · 重複 (' + name + ')');
      seen[name] = 1;
      var nb = utf8(name), data = f.data instanceof Uint8Array ? f.data : new Uint8Array(f.data || []);
      if (data.length >= 0xFFFFFFFF || off >= 0xFFFFFFFF) throw new Error('ZIP: 4GB を超えます');
      var crc = crc32(data), dt = dosTime(f.date);
      var lh = new DataView(new ArrayBuffer(30));
      lh.setUint32(0, 0x04034b50, true); lh.setUint16(4, 20, true); lh.setUint16(6, 0x0800, true); lh.setUint16(8, 0, true);
      lh.setUint16(10, dt.time, true); lh.setUint16(12, dt.date, true); lh.setUint32(14, crc, true);
      lh.setUint32(18, data.length, true); lh.setUint32(22, data.length, true); lh.setUint16(26, nb.length, true); lh.setUint16(28, 0, true);
      parts.push(new Uint8Array(lh.buffer), nb, data);
      var ch = new DataView(new ArrayBuffer(46));
      ch.setUint32(0, 0x02014b50, true); ch.setUint16(4, 20, true); ch.setUint16(6, 20, true); ch.setUint16(8, 0x0800, true); ch.setUint16(10, 0, true);
      ch.setUint16(12, dt.time, true); ch.setUint16(14, dt.date, true); ch.setUint32(16, crc, true);
      ch.setUint32(20, data.length, true); ch.setUint32(24, data.length, true); ch.setUint16(28, nb.length, true);
      ch.setUint16(30, 0, true); ch.setUint16(32, 0, true); ch.setUint16(34, 0, true); ch.setUint16(36, 0, true); ch.setUint32(38, 0, true); ch.setUint32(42, off, true);
      central.push(new Uint8Array(ch.buffer), nb);
      off += 30 + nb.length + data.length;
    });
    var cdSize = central.reduce(function (s, x) { return s + x.length; }, 0);
    var end = new DataView(new ArrayBuffer(22));
    end.setUint32(0, 0x06054b50, true); end.setUint16(8, files.length, true); end.setUint16(10, files.length, true);
    end.setUint32(12, cdSize, true); end.setUint32(16, off, true);
    var all = parts.concat(central, [new Uint8Array(end.buffer)]);
    var n = all.reduce(function (s, x) { return s + x.length; }, 0), out = new Uint8Array(n), p = 0;
    all.forEach(function (x) { out.set(x, p); p += x.length; });
    return out;
  };
  C01.zipStore._crc32 = crc32;
})();
