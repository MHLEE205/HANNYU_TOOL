/* ✦ Powered by LEENAI Automation System — データの読み先 (local / graph)
   HTML・JS にデータは入れない。データは選んだフォルダ (local) または SharePoint PHOTO_V2 (graph, R7) から読む。
   共通インターフェース:
     init()                → {mode, today, label}
     getJson(rel)          → _data/ 以下の JSON (rel = 'jikkyou.json' など)
     fileUrl(rel)          → 写真・原本を表示する URL (rel = PHOTO_V2 ルートからの相対パス)
     listActions(days)     → [{file, done, action}]  (_actions/{day}/*.json)
     writeAction(a)        → 1 件書く (_actions/{YYYY-MM-DD}/{action_id}.json)
     getStaff()            → pol_staff マスター (local: フォルダの _masters/pol_staff.json) */
'use strict';
window.C01 = window.C01 || {};

C01.sources = (function () {
  function jget(url) {
    return fetch(url, { cache: 'no-store' }).then(function (r) {
      if (!r.ok) throw new Error(url + ' → ' + r.status);
      return r.json();
    });
  }
  function enc(rel) { return rel.split('/').map(encodeURIComponent).join('/'); }

  /* ── local ①: 127.0.0.1 の serve_local.py ── */
  function LocalServer() {}
  LocalServer.prototype.init = function () {
    return jget('/api/config').then(function (c) { return { mode: 'local-server', today: c.today, label: c.root_name }; });
  };
  LocalServer.prototype.getJson = function (rel) { return jget('/data/_data/' + enc(rel)); };
  LocalServer.prototype.fileUrl = function (rel) { return rel ? '/data/' + enc(rel) : ''; };
  LocalServer.prototype.listActions = function (days) {
    var q = (days || []).map(function (d) { return 'day=' + encodeURIComponent(d); }).join('&');
    return jget('/api/actions' + (q ? '?' + q : '')).then(function (r) { return r.items || []; });
  };
  LocalServer.prototype.writeAction = function (a) {
    return fetch('/api/actions', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(a) })
      .then(function (r) { if (!r.ok) throw new Error('書き込み失敗 (' + r.status + ')'); return r.json(); });
  };
  LocalServer.prototype.getStaff = function () { return jget('/api/staff'); };

  /* ── local ②: フォルダ選択 (File System Access API · Chrome/Edge) ── */
  function Folder(handle) { this.root = handle; this.urls = {}; }
  Folder.pick = function () {
    if (!window.showDirectoryPicker) return Promise.reject(new Error('このブラウザはフォルダ選択に対応していません (Chrome / Edge)'));
    return window.showDirectoryPicker({ mode: 'readwrite' }).then(function (h) { return new Folder(h); });
  };
  Folder.prototype._dir = function (parts, create) {
    var p = Promise.resolve(this.root);
    parts.forEach(function (name) { p = p.then(function (d) { return d.getDirectoryHandle(name, { create: !!create }); }); });
    return p;
  };
  Folder.prototype._file = function (rel) {
    var parts = rel.split('/');
    var name = parts.pop();
    return this._dir(parts).then(function (d) { return d.getFileHandle(name); }).then(function (fh) { return fh.getFile(); });
  };
  Folder.prototype.init = function () {
    var self = this;
    return this._file('_data/meta.json').then(function (f) { return f.text(); }).then(function (t) {
      var m = JSON.parse(t);
      return { mode: 'local-folder', today: m.today, label: self.root.name };
    });
  };
  Folder.prototype.getJson = function (rel) {
    return this._file('_data/' + rel).then(function (f) { return f.text(); }).then(JSON.parse);
  };
  Folder.prototype.fileUrl = function (rel) {
    /* 同期では URL を作れないので、表示時に resolveUrl を使う */
    return this.urls[rel] || '';
  };
  Folder.prototype.resolveUrl = function (rel) {
    var self = this;
    if (!rel) return Promise.resolve('');
    if (self.urls[rel]) return Promise.resolve(self.urls[rel]);
    return this._file(rel).then(function (f) { self.urls[rel] = URL.createObjectURL(f); return self.urls[rel]; }).catch(function () { return ''; });
  };
  Folder.prototype.listActions = function (days) {
    var self = this;
    return this._dir(['_actions']).then(function (base) {
      var out = [];
      var ds = days || [];
      return Promise.all(ds.map(function (day) {
        return base.getDirectoryHandle(day).then(function (d) {
          var names = [];
          var it = d.values();
          function next() {
            return it.next().then(function (r) {
              if (r.done) return;
              names.push(r.value.name);
              return next();
            });
          }
          return next().then(function () {
            var jsons = names.filter(function (n) { return /\.json$/.test(n); }).sort();
            return Promise.all(jsons.map(function (n) {
              return d.getFileHandle(n).then(function (fh) { return fh.getFile(); }).then(function (f) { return f.text(); }).then(function (t) {
                out.push({ file: day + '/' + n, done: names.indexOf(n + '.done') >= 0, action: JSON.parse(t) });
              }).catch(function () {});
            }));
          });
        }).catch(function () {});
      })).then(function () { return out; });
    }).catch(function () { return []; });
  };
  Folder.prototype.writeAction = function (a) {
    var day = String(a.at).slice(0, 10);
    return this._dir(['_actions', day], true).then(function (d) {
      return d.getFileHandle(a.action_id + '.json', { create: true });
    }).then(function (fh) { return fh.createWritable(); }).then(function (w) {
      return w.write(JSON.stringify(a, null, 1) + '\n').then(function () { return w.close(); });
    }).then(function () { return { file: day + '/' + a.action_id + '.json' }; });
  };
  Folder.prototype.getStaff = function () {
    return this._file('_masters/pol_staff.json').then(function (f) { return f.text(); }).then(JSON.parse);
  };

  /* ── graph (R7): SharePoint PHOTO_V2 を職員トークンで読む・書く — 枠だけ。C01.SOURCE.graphEnabled=false の間は呼び出し 0 ── */
  function Graph() {}
  function off() { return Promise.reject(new Error('graph モードは R7 で有効になります')); }
  Graph.prototype.init = function () {
    if (!C01.SOURCE.graphEnabled) return off();
    /* R7: LEENAI.auth.token('graph') → PHOTO_V2 drive の _data を読む */
    return off();
  };
  Graph.prototype.getJson = off;
  Graph.prototype.fileUrl = function () { return ''; };
  Graph.prototype.listActions = off;
  Graph.prototype.writeAction = off;
  Graph.prototype.getStaff = function () {
    /* R7: LEENAI.master.get('pol_staff') */
    return off();
  };

  return { LocalServer: LocalServer, Folder: Folder, Graph: Graph };
})();
