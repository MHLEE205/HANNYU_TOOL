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

  /* ── graph (R7A): SharePoint ドキュメント / HANNYU_TOOL (PHOTO_V2) を職員のログイン (LEENAI_COMMON の Graph トークン) で読む・書く ──
     読む: _data/*.json · 写真・原本 (blob URL) · _actions/{日付}/ (一覧 + 中身、eTag が同じなら読み直さない)
     書く: _actions/{日付}/{action_id}.json だけ (同じ名前があれば書かない = conflictBehavior fail)。ほかの場所への書き込みコード無し */
  var GRAPH = 'https://graph.microsoft.com/v1.0/';
  function Graph() { this.urls = {}; this.acts = {}; }
  function off() { return Promise.reject(new Error('graph モードは無効です (C01.SOURCE.graphEnabled)')); }
  Graph.prototype._item = function (rel) {
    return GRAPH + 'drives/' + LEENAI.SP.DRIVE_ID + '/root:/' + enc(C01.SOURCE.spRoot + '/' + rel) + ':';
  };
  Graph.prototype._fetch = function (url, opt, retried) {
    var self = this;
    return LEENAI.auth.token('graph').then(function (tok) {
      if (!tok) throw new Error('Graph トークンがありません (再ログインしてください)');
      var o = Object.assign({ cache: 'no-store' }, opt || {});
      o.headers = Object.assign({ Authorization: 'Bearer ' + tok }, (opt && opt.headers) || {});
      return fetch(url, o);
    }).then(function (r) {
      if (r.status === 401 && !retried) return self._fetch(url, opt, true);
      return r;
    });
  };
  Graph.prototype._json = function (rel) {
    return this._fetch(this._item(rel) + '/content').then(function (r) {
      if (r.status === 403) throw new Error('SharePoint (HANNYU_TOOL) を読む権限がありません (403)');
      if (!r.ok) throw new Error(rel + ' → ' + r.status);
      return r.json();
    });
  };
  Graph.prototype.init = function () {
    if (!C01.SOURCE.graphEnabled) return off();
    if (!(window.LEENAI && LEENAI.auth && LEENAI.SP && LEENAI.SP.DRIVE_ID)) return Promise.reject(new Error('共通ファイル (LEENAI_COMMON) がありません'));
    var st = LEENAI.auth.status || {};
    if (st.graph !== 'ok') return Promise.reject(new Error('Microsoft 365 (Graph) に接続できませんでした: ' + (st.graphError || st.graph)));
    return this._json('_data/meta.json').then(function (m) {
      return { mode: 'graph', today: m.today, label: 'SharePoint ' + C01.SOURCE.spRoot, files: String(st.graphError || '').indexOf('files:') === 0 ? 'narrow' : 'ok' };
    });
  };
  Graph.prototype.getJson = function (rel) { return this._json('_data/' + rel); };
  Graph.prototype.fileUrl = function (rel) { return this.urls[rel] || ''; };
  /* v0.3.3 (R7C): 読めなかった理由を残す (画面に「SharePoint にまだありません」などを出すため) — fileError(rel) */
  Graph.prototype.fileError = function (rel) { return (this.errs || {})[rel] || ''; };
  Graph.prototype.resolveUrl = function (rel) {
    var self = this;
    if (!rel) return Promise.resolve('');
    if (self.urls[rel]) return Promise.resolve(self.urls[rel]);
    self.errs = self.errs || {};
    return this._fetch(this._item(rel) + '/content').then(function (r) {
      if (!r.ok) { self.errs[rel] = r.status === 404 ? 'notfound' : r.status === 403 ? 'forbidden' : 'http' + r.status; return ''; }
      return r.blob().then(function (b) {
        if (/\.pdf$/i.test(rel) && b.type !== 'application/pdf') b = new Blob([b], { type: 'application/pdf' });
        self.urls[rel] = URL.createObjectURL(b);
        delete self.errs[rel];
        return self.urls[rel];
      });
    }).catch(function () { self.errs[rel] = 'network'; return ''; });
  };
  /* v0.3.3 (R7C): 「別タブで開く」 = SharePoint の表示画面 (webUrl)。PC のブラウザ設定 (PDF を外部アプリで開く) でも開ける · GET だけ */
  Graph.prototype.webUrl = function (rel) {
    var self = this;
    if (!rel) return Promise.resolve('');
    self.web = self.web || {};
    if (self.web[rel]) return Promise.resolve(self.web[rel]);
    return this._fetch(this._item(rel) + '?$select=webUrl').then(function (r) {
      if (!r.ok) { self.errs = self.errs || {}; self.errs[rel] = r.status === 404 ? 'notfound' : r.status === 403 ? 'forbidden' : 'http' + r.status; return ''; }
      /* v0.3.6: webUrl はファイルそのもの (開くとダウンロード) → ?web=1 で SharePoint の表示画面 (PDF ビューアー · Excel Online) */
      return r.json().then(function (j) { var u = String(j.webUrl || ''); if (/^https:\/\//.test(u)) self.web[rel] = u + (u.indexOf('?') >= 0 ? '&' : '?') + 'web=1'; return self.web[rel] || ''; });
    }).catch(function () { return ''; });
  };
  Graph.prototype._children = function (rel) {
    var self = this;
    var out = [];
    function page(url) {
      return self._fetch(url).then(function (r) {
        if (r.status === 404) return null;
        if (!r.ok) throw new Error('一覧 ' + r.status);
        return r.json().then(function (j) {
          (j.value || []).forEach(function (x) { out.push({ name: x.name, eTag: x.eTag, folder: !!x.folder }); });
          return j['@odata.nextLink'] ? page(j['@odata.nextLink']) : out;
        });
      });
    }
    return page(this._item(rel) + '/children?$select=name,eTag,folder&$top=500');
  };
  Graph.prototype.listActions = function (days) {
    var self = this;
    var out = [];
    return Promise.all((days || []).map(function (day) {
      return self._children('_actions/' + day).then(function (items) {
        if (!items) return;
        var names = items.map(function (x) { return x.name; });
        return Promise.all(items.filter(function (x) { return !x.folder && /\.json$/.test(x.name); }).map(function (x) {
          var key = day + '/' + x.name;
          var c = self.acts[key];
          var p = (c && c.eTag === x.eTag) ? Promise.resolve(c.action) : self._json('_actions/' + key).then(function (a) {
            self.acts[key] = { eTag: x.eTag, action: a };
            return a;
          });
          return p.then(function (a) { out.push({ file: key, done: names.indexOf(x.name + '.done') >= 0, action: a }); }).catch(function () {});
        }));
      }).catch(function () {});
    })).then(function () {
      out.sort(function (a, b) { return a.file < b.file ? -1 : a.file > b.file ? 1 : 0; });
      return out;
    });
  };
  Graph.prototype.writeAction = function (a) {
    var day = String(a.at).slice(0, 10);
    if (!/^\d{4}-\d{2}-\d{2}$/.test(day) || !/^[A-Za-z0-9_-]+$/.test(String(a.action_id))) return Promise.reject(new Error('action の日付・id が不正'));
    var rel = '_actions/' + day + '/' + a.action_id + '.json';
    return this._fetch(this._item(rel) + '/content?@microsoft.graph.conflictBehavior=fail',
      { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(a, null, 1) + '\n' }).then(function (r) {
      if (r.status === 403) throw new Error('SharePoint (HANNYU_TOOL) に書く権限がありません (403)');
      if (r.status === 409) throw new Error('同じ記録がすでにあります (409)');
      if (!r.ok) throw new Error('書き込み失敗 (' + r.status + ')');
      return { file: day + '/' + a.action_id + '.json' };
    });
  };
  Graph.prototype.getStaff = function () {
    /* 担当港 = 共通マスター pol_staff (SharePoint · 列 staff = 担当 · assist = 補助 · 値 = 職員コード)
       職員 = 共通マスター staff (code · email · name_ja) — v0.3.16 (R7O Part D): LEENAI.STAFF (共通ファイルに書かれた一覧) ではなくマスター。
       staff マスターが読めないときだけ LEENAI.STAFF */
    if (!(LEENAI.master && LEENAI.master.get)) return Promise.reject(new Error('マスターなし'));
    /* v0.3.18 (R7S #16): pol_staff が読めなくても 職員マスター (担当者の名前) は使う · 読めなかったことは polError で画面に出す */
    var pol = LEENAI.master.get('pol_staff').then(function (x) { return x; }, function () { return null; });
    var sm = LEENAI.master.get('staff').then(function (x) { return x; }, function () { return null; });
    return Promise.all([pol, sm]).then(function (r) {
      var items = Array.isArray(r[0]) ? r[0] : [], rows = r[1];
      var polError = !Array.isArray(r[0]);
      var staff = (rows && rows.length)
        ? rows.filter(function (s) { return s && s.code && s.active !== false; }).map(function (s) {
          return { code: s.code, name: s.name_ja || s.name_en || s.code, name_en: s.name_en || '', email: s.email || '', admin: s.portal_admin === true };
        })
        : (LEENAI.STAFF || []).map(function (s) { return { code: s.staffCode, name: s.name, email: s.email }; });
      return { staff: staff, items: items, from: (rows && rows.length) ? 'master' : 'common', polError: polError };
    });
  };
  Graph.prototype.me = function (staff) {
    /* v0.3.16 (R7O Part D): ログインした人 (LEENAI_COMMON の LEENAI.user = ヘッダーと同じ人) を職員マスターで探す
       (メール → 職員コード の順) · 名前 = 職員マスターの名前。見つからなければ Microsoft の名前を使わず 「職員マスター未登録」 */
    var u = LEENAI.user || {};
    var em = String(u.email || '').toLowerCase();
    var list = (staff && staff.staff) || [];
    var s = list.filter(function (x) { return em && String(x.email || '').toLowerCase() === em; })[0] ||
      list.filter(function (x) { return u.staffCode && x.code === u.staffCode; })[0];
    if (s) return { code: s.code, name: s.name || s.code, email: s.email || u.email, admin: !!s.admin };   /* v0.3.20 (#201): 職員マスター portal_admin */
    return u.email ? { code: u.staffCode || u.email, name: '職員マスター未登録', email: u.email, unregistered: true } : null;
  };

  return { LocalServer: LocalServer, Folder: Folder, Graph: Graph };
})();
