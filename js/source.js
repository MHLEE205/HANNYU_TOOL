/* ✦ Powered by LEENAI Automation System — データの読み先 (local / graph)
   HTML・JS にデータは入れない。データは選んだフォルダ (local) または SharePoint PHOTO_V2 (graph, R7) から読む。
   共通インターフェース:
     init()                → {mode, today, label}
     getJson(rel)          → _data/ 以下の JSON (rel = 'jikkyou.json' など)
     fileUrl(rel)          → 写真・原本を表示する URL (rel = PHOTO_V2 ルートからの相対パス)
     listActions(days)     → [{file, done, action}]  (_actions/{day}/*.json)
     writeAction(a)        → 1 件書く (_actions/{YYYY-MM-DD}/{action_id}.json)
     getStaff()            → pol_staff マスター (local: フォルダの _masters/pol_staff.json)
     listAsks(days)        → [{ask, reply|null}]  (v0.3.25 · {C01.ASK.base}/ask/{day}/*.json + ask_reply/{id}.json)
     writeAsk(a)           → 質問 1 件 ({base}/ask/{YYYY-MM-DD}/{ask_id}.json) */
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
  /* v0.3.30 (R8U): 画面 · エラーに出す場所の名前 (spLabel · 無ければ spRoot) */
  function spName() { return (C01.SOURCE && (C01.SOURCE.spLabel || C01.SOURCE.spRoot)) || ''; }
  function askBase() { return String((C01.ASK && C01.ASK.base) || '_actions').split('/').filter(Boolean); }
  function askOk(a) { return a && /^[A-Za-z0-9_-]{6,64}$/.test(String(a.ask_id)) && /^\d{4}-\d{2}-\d{2}/.test(String(a.at)); }

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
  LocalServer.prototype.listAsks = function (days) {
    var q = (days || []).map(function (d) { return 'day=' + encodeURIComponent(d); }).join('&');
    return jget('/api/ask' + (q ? '?' + q : '')).then(function (r) { return r.items || []; });
  };
  LocalServer.prototype.writeAsk = function (a) {
    return fetch('/api/ask', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(a) })
      .then(function (r) { if (!r.ok) throw new Error('送信失敗 (' + r.status + ')'); return r.json(); });
  };
  LocalServer.prototype.sendMailTest = function () { return Promise.reject(new Error('ローカルプレビューでは送信しません')); };   /* v0.3.22 (R7V Part B) */
  LocalServer.prototype.sendMailLive = function () { return Promise.reject(new Error('ローカルプレビューでは送信しません')); };   /* v0.3.37 (R9K Part B-0) */

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
  Folder.prototype._readJson = function (dirParts, name) {
    return this._dir(dirParts).then(function (d) { return d.getFileHandle(name); }).then(function (fh) { return fh.getFile(); })
      .then(function (f) { return f.text(); }).then(JSON.parse);
  };
  Folder.prototype.listAsks = function (days) {
    var self = this, base = askBase(), out = [];
    return Promise.all((days || []).map(function (day) {
      return self._dir(base.concat(['ask', day])).then(function (d) {
        var names = [], it = d.values();
        function next() { return it.next().then(function (r) { if (r.done) return; names.push(r.value.name); return next(); }); }
        return next().then(function () {
          return Promise.all(names.filter(function (n) { return /^[A-Za-z0-9_-]+\.json$/.test(n); }).map(function (n) {
            return self._readJson(base.concat(['ask', day]), n).then(function (a) {
              return self._readJson(base.concat(['ask_reply']), n).catch(function () { return null; }).then(function (rp) { out.push({ ask: a, reply: rp }); });
            }).catch(function () {});
          }));
        });
      }).catch(function () {});
    })).then(function () { return out; });
  };
  Folder.prototype.writeAsk = function (a) {
    var day = String(a.at).slice(0, 10);
    return this._dir(askBase().concat(['ask', day]), true).then(function (d) {
      return d.getFileHandle(a.ask_id + '.json', { create: true });
    }).then(function (fh) { return fh.createWritable(); }).then(function (w) {
      return w.write(JSON.stringify(a, null, 1) + '\n').then(function () { return w.close(); });
    }).then(function () { return { file: day + '/' + a.ask_id + '.json' }; });
  };
  Folder.prototype.getStaff = function () {
    return this._file('_masters/pol_staff.json').then(function (f) { return f.text(); }).then(JSON.parse);
  };

  /* ── graph (R7A): SharePoint ドキュメント / HANNYU_TOOL (PHOTO_V2) を職員のログイン (LEENAI_COMMON の Graph トークン) で読む・書く ──
     読む: _data/*.json · 写真・原本 (blob URL) · _actions/{日付}/ (一覧 + 中身、eTag が同じなら読み直さない)
     書く: _actions/{日付}/{action_id}.json だけ (同じ名前があれば書かない = conflictBehavior fail)。
     v0.3.83 (R12Y55): + 通関依頼済 の記録 (_actions/clearance_shadow/) と clearance_status.json (試験用コピー · 本番は live の時だけ) — 下の clearancePathOk */
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
      if (r.status === 403) throw new Error('SharePoint (' + spName() + ') を読む権限がありません (403)');
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
      return { mode: 'graph', today: m.today, label: 'SharePoint ' + spName(), files: String(st.graphError || '').indexOf('files:') === 0 ? 'narrow' : 'ok' };
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
      if (r.status === 403) throw new Error('SharePoint (' + spName() + ') に書く権限がありません (403)');
      if (r.status === 409) throw new Error('同じ記録がすでにあります (409)');
      if (!r.ok) throw new Error('書き込み失敗 (' + r.status + ')');
      return { file: day + '/' + a.action_id + '.json' };
    });
  };
  /* v0.3.25 (R7Z Part A · #207): AI 相談 — 質問一覧 (今日 · 昨日) と 答え (ask_reply · eTag が同じ答えは読み直さない) · 書く = 質問 1 件だけ */
  Graph.prototype.listAsks = function (days) {
    var self = this, base = askBase().join('/'), out = [];
    self.askCache = self.askCache || {}; self.replyCache = self.replyCache || {};
    var replies = self._children(base + '/ask_reply').then(function (xs) { var m = {}; (xs || []).forEach(function (x) { m[x.name] = x.eTag; }); return m; }).catch(function () { return {}; });
    return replies.then(function (rm) {
      return Promise.all((days || []).map(function (day) {
        return self._children(base + '/ask/' + day).then(function (items) {
          return Promise.all((items || []).filter(function (x) { return !x.folder && /^[A-Za-z0-9_-]+\.json$/.test(x.name); }).map(function (x) {
            var k = day + '/' + x.name;
            var pa = self.askCache[k] ? Promise.resolve(self.askCache[k]) : self._json(base + '/ask/' + k).then(function (a) { self.askCache[k] = a; return a; });
            return pa.then(function (a) {
              if (!rm[x.name]) { out.push({ ask: a, reply: null }); return null; }
              var c = self.replyCache[x.name];
              var pr = c && c.eTag === rm[x.name] ? Promise.resolve(c.reply) : self._json(base + '/ask_reply/' + x.name).then(function (r) { self.replyCache[x.name] = { eTag: rm[x.name], reply: r }; return r; });
              return pr.then(function (r) { out.push({ ask: a, reply: r }); }, function () { out.push({ ask: a, reply: null }); });
            }).catch(function () {});
          }));
        }).catch(function () {});
      }));
    }).then(function () { return out; });
  };
  Graph.prototype.writeAsk = function (a) {
    if (!askOk(a)) return Promise.reject(new Error('質問の日付・id が不正'));
    var rel = askBase().join('/') + '/ask/' + String(a.at).slice(0, 10) + '/' + a.ask_id + '.json';
    return this._fetch(this._item(rel) + '/content?@microsoft.graph.conflictBehavior=fail',
      { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(a, null, 1) + '\n' }).then(function (r) {
      if (r.status === 403) throw new Error('SharePoint (' + spName() + ') に書く権限がありません (403)');
      if (!r.ok) throw new Error('送信失敗 (' + r.status + ')');
      return { file: rel };
    });
  };
  /* v0.3.83 (R12Y55 · 決定 #401): 通関依頼済 の自動記録 (js/clearance.js) — 読む · 書くのは 2 か所だけ:
     試験用コピー (C01.CLEARANCE.copyPath) と 本番 (livePath · live = true の時だけ · 呼ぶ側も エンジン meta.clearance.mode 'live' を確かめる)。
     書き方 = If-Match (eTag) 付き PUT (PORTAL v4.10 と同じ) · 412 は呼ぶ側が読み直す。記録 = _actions/clearance_shadow/{日付}/ に新しいファイルだけ */
  function clearancePathOk(path, live) {
    var c = C01.CLEARANCE || {};
    if (!c.enabled || typeof path !== 'string' || !path) return false;
    if (path === c.copyPath && /\/D-00\/doc_tool_v024\/portal_test\/clearance_status_copy\.json$/.test(path)) return true;
    return live === true && c.live === true && path === c.livePath;
  }
  Graph.prototype._abs = function (path) { return GRAPH + 'drives/' + LEENAI.SP.DRIVE_ID + '/root:/' + enc(path) + ':'; };
  Graph.prototype.clearanceRead = function (path, live) {
    var self = this, c = C01.CLEARANCE || {};
    if (!(clearancePathOk(path, live) || (c.enabled && path === c.livePath))) return Promise.reject(new Error('この場所は読みません'));   /* 本番は 読むだけ なら いつでも */
    return this._fetch(this._abs(path) + '?$select=id,eTag').then(function (m) {
      if (!m.ok) throw new Error('読込失敗 ' + m.status);
      return m.json().then(function (j) {
        var eTag = j.eTag || '';
        return self._fetch(self._abs(path) + '/content').then(function (r) {
          if (!r.ok) throw new Error('読込失敗 ' + r.status);
          return r.text().then(function (t) {
            var obj = JSON.parse(t.charCodeAt(0) === 0xfeff ? t.slice(1) : t);
            if (!obj || typeof obj !== 'object' || Array.isArray(obj)) throw new Error('clearance_status.json の形が違います');
            return { obj: obj, eTag: eTag };
          });
        });
      });
    });
  };
  Graph.prototype.clearancePut = function (path, text, eTag, live) {
    if (!clearancePathOk(path, live)) return Promise.reject(new Error('この場所には書きません'));
    if (!eTag) return Promise.reject(new Error('eTag がありません (丸ごとの上書きはしません)'));
    return this._fetch(this._abs(path) + '/content', { method: 'PUT', headers: { 'Content-Type': 'application/json', 'If-Match': eTag }, body: text })
      .then(function (r) { return r.status; });
  };
  Graph.prototype.writeClearanceShadow = function (rec) {
    var day = String(rec && rec.at).slice(0, 10);
    if (!/^\d{4}-\d{2}-\d{2}$/.test(day)) return Promise.reject(new Error('記録の日付が不正'));
    var id = String(rec.at).replace(/[^0-9]/g, '').slice(0, 14) + '_' + Math.random().toString(36).slice(2, 8);
    var rel = '_actions/clearance_shadow/' + day + '/' + id + '.json';
    return this._fetch(this._item(rel) + '/content?@microsoft.graph.conflictBehavior=fail',
      { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(rec, null, 1) + '\n' }).then(function (r) {
      if (!r.ok) throw new Error('記録失敗 (' + r.status + ')');
      return { file: rel };
    });
  };
  /* v0.3.22 (R7V Part B · 決定 #191 · #135): 催促の試験送信 — Graph /me/sendMail (ログインした職員のメール)。2 番目の鍵: 宛先は 1 件 = 試験用アドレス
     (エンジン remind.json send_mode.to) · 件名は [test] で始まる · CC · BCC なし。それ以外は送らない (実際の宛先へ送るコードは無い) */
  Graph.prototype.sendMailTest = function (m) {
    var mode = (C01.state && C01.state.remind && C01.state.remind.send_mode) || {};
    if (!(C01.SEND && C01.SEND.remindTest !== false) || mode.test !== true || !m || m.to !== mode.to || !/^\[test\] /.test(m.subject || '')) {
      return Promise.reject(new Error('試験モードの宛先ではありません — 送信しません'));
    }
    var body = { message: { subject: m.subject, body: { contentType: 'HTML', content: m.html || '' }, toRecipients: [{ emailAddress: { address: mode.to } }] },
      saveToSentItems: true };
    return this._fetch(GRAPH + 'me/sendMail', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }).then(function (r) {
      if (r.status === 403) throw new Error('メール送信の権限がありません (403)');
      if (r.status !== 202 && !r.ok) throw new Error('送信失敗 (' + r.status + ')');
      return { ok: true };
    });
  };
  /* v0.3.37 (R9K Part B-0 · 決定 #270): 催促の本番送信 — Graph /me/sendMail (押した職員のメール)。二重の鍵: ① エンジン send_mode {test: false, live: true}
     + C01.SEND.remindLive ② 送る直前に C01.remindCheck (下書き allow · 固定 CC) で To · CC をもう一度確かめ、渡された宛先が下書きと同じ集合であること。BCC なし */
  Graph.prototype.sendMailLive = function (m) {
    var mode = (C01.state && C01.state.remind && C01.state.remind.send_mode) || {};
    if (!(C01.SEND && C01.SEND.remind && C01.SEND.remindLive === true) || mode.test !== false || mode.live !== true || !m || !m.draft) {
      return Promise.reject(new Error('本番送信ではありません — 送信しません'));
    }
    var bad = C01.remindCheck(m.draft, m.unOk);
    if (bad.length) return Promise.reject(new Error(bad[0]));
    var low = function (a) { return String(a || '').trim().toLowerCase(); };
    var want = [].concat(m.draft.to || [], m.draft.cc || [], m.unOk ? [].concat(m.draft.to_unreceived || [], m.draft.cc_unreceived || []) : []).map(low);
    var got = [].concat(m.to || [], m.cc || []).map(low);
    if (!(m.to || []).length || got.some(function (a) { return want.indexOf(a) < 0; }) || want.some(function (a) { return got.indexOf(a) < 0; })) {
      return Promise.reject(new Error('宛先が下書きと違います — 送信しません'));
    }
    var rcp = function (xs) { return (xs || []).map(function (a) { return { emailAddress: { address: a } }; }); };
    var body = { message: { subject: m.subject, body: { contentType: 'HTML', content: m.html || '' }, toRecipients: rcp(m.to), ccRecipients: rcp(m.cc) },
      saveToSentItems: true };
    return this._fetch(GRAPH + 'me/sendMail', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }).then(function (r) {
      if (r.status === 403) throw new Error('メール送信の権限がありません (403)');
      if (r.status !== 202 && !r.ok) throw new Error('送信失敗 (' + r.status + ')');
      return { ok: true };
    });
  };
  /* ── v0.3.63 (決定 #359 · #302 · #352): 通関書類送付 — 押した職員のメールボックスだけ (/me) · 読むのは GET · 送るのは 「送信」 を押した時の 1 通だけ ── */
  function oursDom() { return String((C01.CUSTOMS && C01.CUSTOMS.ourDomain) || 'leenearcorp.com').toLowerCase(); }
  function addrOf(r) { return String(((r || {}).emailAddress || {}).address || '').trim().toLowerCase(); }
  function nameOf(r) { return String(((r || {}).emailAddress || {}).name || '').trim(); }
  var MSG_SEL = '$select=id,subject,conversationId,sentDateTime,receivedDateTime,from,toRecipients,ccRecipients,isDraft,internetMessageId';
  function stripRe(s) { return String(s || '').replace(/^\s*((re|fw|fwd|返信|転送)\s*[:：]\s*)+/i, '').trim(); }
  /* ① 通関依頼 の件名 = 원조토르 6 か月調査 mail_lib.kind と同じ: 件名 (RE: を除く) で一番前に出た語の種類が ① の時だけ
     (本船変更 · 本数追加 · 通関書類 · 許可書 などが先にあれば ① ではない = 別の会話に返信しない) */
  var KW_ORDER = [['④', /本登録/], ['ACL訂正', /ACL\s*訂正|ACL\s*確認/], ['DR訂正', /DR\s*訂正|D\/R\s*訂正/],
    ['変更', /本船変更|CUT\s*変更|OPEN-CUT|本数(変更|追加)|VOYA/], ['②', /通関書類/], ['③', /許可書|仮\s*ACL|E\/D\s*添付|D\/R\s*添付|D\/R,\s*E\/D/],
    ['①', /通関\s*[＆&、・]?\s*(ドレージ)?(の)?(ご)?依頼|通関\s*[+＋]\s*ドレージ\s*(申請|依頼)|ドレージ\s*[、・＆&]?\s*通関|新規ドレージ(の)?(ご)?依頼/],
    ['業者', /ブッキング情報のご案内/]];   /* ブッキング情報のご案内 = 圧縮業者あて (① ではない · 実メール 2 週 21 件で確認) */
  /* v0.3.85 (R12Y60 · #405): 新規通関依頼 = B-03 P/O 発注ツール の決まった件名 「新規(輸出)通関依頼 · 新規通関+ドレージ申請 … : BKG#{BKG}」 (本文 「I/V NO {IV}」)。
     エンジン customs_s1.B03_HEAD · b03 · b03_orig · iv_line と同じ決まり (変える時は両方) */
  var B03_HEAD = /新規\s*(輸出)?\s*通関\s*((の)?(ご)?依頼|[+＋＆&]\s*ドレージ\s*(申請|依頼))/;
  var REPLY_ANY = /(^|[^A-Za-z])(re|fw|fwd)\s*[:：]|返信\s*[:：]|転送\s*[:：]/i;
  function normAN(s) { return String(s || '').toUpperCase().replace(/[^A-Z0-9]/g, ''); }
  function b03(s, bkg) {
    var b = normAN(bkg), re = /BKG\s*(NO\.?)?\s*[#＃:：]?\s*([A-Za-z0-9\-]+)/gi, m;
    if (!B03_HEAD.test(String(s || '')) || b.length < 6) return false;
    while ((m = re.exec(String(s || '')))) if (normAN(m[2]) === b) return true;
    return false;
  }
  function b03Orig(s, bkg) { return b03(s, bkg) && !REPLY_ANY.test(String(s || '')); }
  function ivLine(t, iv) {
    if (!iv || !t) return false;
    var e = String(iv).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    return new RegExp('I\\s*/\\s*V\\s*NO\\.?\\s*[:：]?\\s*' + e + '(?![0-9A-Za-z]|-[0-9])', 'i').test(String(t));
  }
  function isS1Subject(s) {
    var h = stripRe(s), best = null;
    KW_ORDER.forEach(function (k) { var m = k[1].exec(h); if (m && (best === null || m.index < best[0])) best = [m.index, k[0]]; });
    return !!best && best[1] === '①';
  }
  Graph.prototype._b03 = { b03: b03, b03Orig: b03Orig, ivLine: ivLine, isS1Subject: function (s) { return isS1Subject(s); } };   /* 試験用 */
  Graph.prototype._mailGet = function (path) {
    return this._fetch(GRAPH + path).then(function (r) {
      if (r.status === 403) throw new Error('メールを読む権限がありません (403)');
      if (!r.ok) throw new Error('メールの検索に失敗 (' + r.status + ')');
      return r.json();
    });
  };
  /* ① = 件名に BKG があり ① の件名の、自社から送ったメール (一番新しいもの) → その会話の一番新しいメール (下書き除く) */
  /* v0.3.85 (R12Y60 · #405): 自社の ① のうち B-03 の件名の元のメール (RE · FW なし) があれば それだけ (後の [P/O送付] Re: などは会話のメールとして) ·
     件名に BKG が無い = IV 番号で探して 本文の先頭 「I/V NO {IV}」 の B-03 の元のメール (how = b03 | old | iv_body) */
  Graph.prototype.customsFindS1 = function (bkg, ivNo) {
    var self = this;
    var raw = String(bkg || '').trim().toUpperCase();
    var b = raw.replace(/[^A-Z0-9]/g, '');
    if (b.length < 6) return Promise.resolve(null);
    /* 件名の英数字だけをつないだ文字列に BKG があり、すぐ後ろが数字でない (長い番号の一部ではない) */
    var hasBkg = function (s) {
      var ns = String(s || '').toUpperCase().replace(/[^A-Z0-9]/g, ''), i = ns.indexOf(b);
      while (i >= 0) { if (!/[0-9]/.test(ns.charAt(i + b.length))) return true; i = ns.indexOf(b, i + 1); }
      return false;
    };
    var byNew = function (x, y) { return String(y.sentDateTime || '').localeCompare(String(x.sentDateTime || '')); };
    var how = 'old';
    return self._mailGet('me/messages?$search=' + encodeURIComponent('"' + raw.replace(/"/g, '') + '"') + '&$top=50&' + MSG_SEL).then(function (j) {
      var xs = (j.value || []).filter(function (m) {
        return !m.isDraft && addrOf(m.from).split('@')[1] === oursDom() && isS1Subject(m.subject) && hasBkg(m.subject);
      }).sort(byNew);
      var b3 = xs.filter(function (m) { return b03Orig(m.subject, raw); });
      if (b3.length) { xs = b3; how = 'b03'; }
      if (xs.length || !ivNo) return xs;
      return self._mailGet('me/messages?$search=' + encodeURIComponent('"' + String(ivNo).replace(/"/g, '') + '"') + '&$top=50&' + MSG_SEL + ',bodyPreview').then(function (k) {
        how = 'iv_body';
        return (k.value || []).filter(function (m) {
          return !m.isDraft && addrOf(m.from).split('@')[1] === oursDom() && B03_HEAD.test(String(m.subject || '')) && !REPLY_ANY.test(String(m.subject || '')) && ivLine(m.bodyPreview, ivNo);
        }).sort(byNew);
      });
    }).then(function (xs) {
      if (!xs.length) return null;
      var s1 = xs[0];
      return self._mailGet('me/messages?$filter=' + encodeURIComponent("conversationId eq '" + s1.conversationId.replace(/'/g, "''") + "'") + '&$top=100&' + MSG_SEL + ',bodyPreview').then(function (c) {
        var L = (c.value || []).filter(function (m) { return !m.isDraft; }).sort(function (x, y) {
          return String(x.sentDateTime || x.receivedDateTime || '').localeCompare(String(y.sentDateTime || y.receivedDateTime || ''));
        });
        var last = L.length ? L[L.length - 1] : s1;
        var pack = function (m) { return { id: m.id, subject: m.subject || '', at: m.sentDateTime || m.receivedDateTime || '', from: addrOf(m.from), from_name: nameOf(m.from),
          to: (m.toRecipients || []).map(function (r) { return { a: addrOf(r), n: nameOf(r) }; }), cc: (m.ccRecipients || []).map(function (r) { return { a: addrOf(r), n: nameOf(r) }; }),
          preview: String(m.bodyPreview || '') }; };
        /* v0.3.66 (R12Y3 · #366 ②): conv = 会話の全メール (古い順 · 本文の先頭 bodyPreview 付き) — 宛名 (会社名 · 担当者) を ① の会話から探す */
        return { s1: pack(s1), last: pack(last), n_conv: L.length, s1_count: xs.length, conv: L.map(pack), how: how };
      });
    });
  };
  /* v0.3.66 (R12Y3 · #366 ②): 通関業者のメール 1 通の本文 (返信の引用を除いた部分 · 文字) — 署名の会社名を探す (GET だけ) */
  Graph.prototype.customsMailText = function (id) {
    return this._fetch(GRAPH + 'me/messages/' + encodeURIComponent(id) + '?$select=uniqueBody', { headers: { Prefer: 'outlook.body-content-type="text"' } }).then(function (r) {
      if (!r.ok) throw new Error('メールを読めません (' + r.status + ')');
      return r.json();
    }).then(function (j) { return String(((j || {}).uniqueBody || {}).content || ''); });
  };
  /* 送付済みの確認: 件名に 「通関書類送付_{IV}」 がある自社のメール (自分のメールボックスに見える分 · [test] は別に数える) */
  Graph.prototype.customsFindSent = function (iv) {
    var v = String(iv || '').trim();
    if (!v) return Promise.resolve([]);
    return this._mailGet('me/messages?$search=' + encodeURIComponent('"通関書類送付_' + v + '"') + '&$top=25&' + MSG_SEL).then(function (j) {
      return (j.value || []).filter(function (m) {
        return !m.isDraft && addrOf(m.from).split('@')[1] === oursDom() && String(m.subject || '').indexOf('通関書類送付_' + v) >= 0 && !/^\s*(re|fw|fwd)\s*[:：]/i.test(m.subject || '');
      }).map(function (m) { return { at: m.sentDateTime || m.receivedDateTime || '', from: addrOf(m.from), from_name: nameOf(m.from), test: /^\s*\[test\]/i.test(m.subject || '') }; });
    });
  };
  /* 送信 (担当者が確認窓で 「送信」 を押した時だけ): ① 会話の一番新しいメールに createReplyAll → 宛先を確認窓の通りに · 件名 · 本文 · PDF → send。
     鍵: ① C01.CUSTOMS.enabled ② 試験モード (C01.CUSTOMS.sendTest !== false) = 宛先は押した本人 1 人だけ · 件名は [test] で始まる
         ③ 送る直前に下書きをもう一度読んで 宛先 · 件名 · 添付 1 つ を確かめる (違えば送らない · 下書きは 下書き フォルダに残る) */
  Graph.prototype.customsSend = function (m) {
    var self = this;
    var C = C01.CUSTOMS || {};
    /* v0.3.76 (R12Y37 · #380 ③): forceTest = 管理者の 「写真・搬入票リンクの試験」 (設定が実際の送付でも 自分 1 人 · [test]) */
    var test = C.sendTest !== false || !!(m && m.forceTest);
    var low = function (a) { return String(a || '').trim().toLowerCase(); };
    if (!C.enabled || !m || !(m.replyToId || m.newMail) || (m.replyToId && m.newMail) || !m.pdf_b64 || !m.file) return Promise.reject(new Error('送信の条件がそろっていません — 送信しません'));
    var me = low((LEENAI.user || {}).email);
    var to = (m.to || []).map(low).filter(Boolean), cc = (m.cc || []).map(low).filter(Boolean);
    if (test) { to = [me]; cc = []; if (!/^\[test\] /.test(m.subject || '')) return Promise.reject(new Error('試験モードの件名ではありません — 送信しません')); }
    if (!me || !to.length) return Promise.reject(new Error('宛先がありません — 送信しません'));
    if (!/^[A-Z]{1,4}\d{4}-\d{1,3}_IV_PL_SI\.pdf$/.test(m.file) || m.subject.indexOf('通関書類送付_' + m.file.split('_')[0] + '】') < 0) return Promise.reject(new Error('件名の IV と添付の IV が違います — 送信しません'));
    var rcp = function (xs) { return xs.map(function (a) { return { emailAddress: { address: a } }; }); };
    var J = function (method, path, body) {
      return self._fetch(GRAPH + path, { method: method, headers: { 'Content-Type': 'application/json' }, body: body == null ? undefined : JSON.stringify(body) }).then(function (r) {
        if (r.status === 403) throw new Error('メールの権限がありません (403 · Mail.ReadWrite / Mail.Send)');
        if (!r.ok && r.status !== 202) throw new Error(method + ' ' + path.split('/').slice(0, 4).join('/') + ' 失敗 (' + r.status + ')');
        return r.status === 202 || r.status === 204 ? {} : r.json();
      });
    };
    var draft = null;
    var bytes = Math.floor(m.pdf_b64.length * 3 / 4);
    /* v0.3.68 (R12Y7 · #367 Part 2): newMail = ① が自分のメールボックスに無い時 — 新しい下書き (me/messages) · 本文 = 確認窓の本文 (+ ① の引用は呼ぶ側が html に入れる) */
    var first = m.newMail ? J('POST', 'me/messages', { subject: m.subject, body: { contentType: 'HTML', content: '<html><body><div>' + m.html + '</div></body></html>' },
      toRecipients: rcp(to), ccRecipients: rcp(cc), bccRecipients: [] }).then(function (d) { draft = d; })
      : J('POST', 'me/messages/' + encodeURIComponent(m.replyToId) + '/createReplyAll', {}).then(function (d) {
        draft = d;
        var html = String((d.body || {}).content || '');
        var mine = '<div>' + m.html + '</div>';
        html = /<body[^>]*>/i.test(html) ? html.replace(/<body[^>]*>/i, function (x) { return x + mine; }) : mine + html;
        return J('PATCH', 'me/messages/' + encodeURIComponent(d.id), { subject: m.subject, body: { contentType: 'HTML', content: html }, toRecipients: rcp(to), ccRecipients: rcp(cc), bccRecipients: [] });
      });
    return first.then(function () {
      if (bytes <= 2900000) {
        return J('POST', 'me/messages/' + encodeURIComponent(draft.id) + '/attachments', { '@odata.type': '#microsoft.graph.fileAttachment', name: m.file, contentType: 'application/pdf', contentBytes: m.pdf_b64 });
      }
      /* 3MB 超 = アップロード セッション (4MB ごと · アップロード先 URL には認証ヘッダーを付けない) */
      return J('POST', 'me/messages/' + encodeURIComponent(draft.id) + '/attachments/createUploadSession', { AttachmentItem: { attachmentType: 'file', name: m.file, size: bytes, contentType: 'application/pdf' } }).then(function (us) {
        var bin = atob(m.pdf_b64), u8 = new Uint8Array(bin.length);
        for (var i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
        var CH = 4 * 1024 * 1024 - 320 * 1024, pos = 0;
        var next = function () {
          if (pos >= u8.length) return Promise.resolve();
          var end = Math.min(pos + CH, u8.length);
          return fetch(us.uploadUrl, { method: 'PUT', headers: { 'Content-Range': 'bytes ' + pos + '-' + (end - 1) + '/' + u8.length, 'Content-Type': 'application/octet-stream' }, body: u8.slice(pos, end) }).then(function (r) {
            if (!r.ok) throw new Error('添付のアップロード失敗 (' + r.status + ')');
            pos = end; return next();
          });
        };
        return next();
      });
    }).then(function () {
      return Promise.all([J('GET', 'me/messages/' + encodeURIComponent(draft.id) + '?$select=subject,toRecipients,ccRecipients,bccRecipients,internetMessageId,conversationId'),
        J('GET', 'me/messages/' + encodeURIComponent(draft.id) + '/attachments?$select=name,size,isInline,contentType')]);
    }).then(function (r) {
      var d = r[0], at = r[1].value || [];
      var got = function (xs) { return (xs || []).map(addrOf).sort().join(','); };
      if (d.subject !== m.subject) throw new Error('下書きの件名が違います — 送信しません（下書きは 下書き フォルダに残っています）');
      if (got(d.toRecipients) !== to.slice().sort().join(',') || got(d.ccRecipients) !== cc.slice().sort().join(',') || (d.bccRecipients || []).length) {
        throw new Error('下書きの宛先が確認窓と違います — 送信しません（下書きは 下書き フォルダに残っています）');
      }
      /* v0.3.66 (R12Y3 · #366 ③): 全員に返信 の下書きには 元のメール本文の画像 (署名ロゴ · 貼り付け画像) が isInline=true の添付で付く (Graph の通常の動き) →
         本文の表示用なのでそのまま残す (消すと引用本文の画像が壊れる)。確かめるのは 「isInline=false の添付 = ちょうど 1 つ · 名前 = 送る PDF」 */
      var files = at.filter(function (x) { return x.isInline !== true; });
      if (files.length !== 1 || files[0].name !== m.file) {
        var other = files.filter(function (x) { return x.name !== m.file; }).map(function (x) { return x.name; });
        throw new Error('添付ファイルが ' + m.file + ' 1 つではありません（' + (files.some(function (x) { return x.name === m.file; }) ? '' : m.file + ' がありません' + (other.length ? ' · ' : '')) +
          (other.length ? 'ほかの添付: ' + other.join(' / ') : '') + '）— 送信しません（下書きは 下書き フォルダに残っています）');
      }
      if (m.conv && d.conversationId && d.conversationId !== m.conv) throw new Error('① の会話ではありません — 送信しません');
      /* v0.3.76 (R12Y37 · #380 ②): 「下書きで保存」 = ここまで同じ (宛先 · 件名 · 添付を確かめた下書き) · 送らない → Outlook で開くリンク (webLink) */
      if (m.draftOnly) {
        return J('GET', 'me/messages/' + encodeURIComponent(draft.id) + '?$select=webLink').then(function (w) {
          return { ok: true, draft: true, test: test, draft_id: draft.id, web_link: (w && w.webLink) || '', internet_message_id: d.internetMessageId || '', to: to, cc: cc };
        });
      }
      return J('POST', 'me/messages/' + encodeURIComponent(draft.id) + '/send', null).then(function () {
        return { ok: true, test: test, internet_message_id: d.internetMessageId || '', to: to, cc: cc };
      });
    });
  };
  /* v0.3.76 (R12Y37 · #380 ③): 写真 · 搬入票 の 1 ファイル (PHOTO_V2 の相対パス · GET だけ) → Uint8Array */
  Graph.prototype.customsFileBytes = function (rel) {
    return this._fetch(this._item(rel) + '/content').then(function (r) {
      if (!r.ok) throw new Error(rel.split('/').pop() + ' を読めません (' + r.status + ')');
      return r.arrayBuffer();
    }).then(function (b) { return new Uint8Array(b); });
  };
  /* v0.3.76 (R12Y37 · #380 ③ · Part 3B): 写真 · 搬入票 zip を 会社の SharePoint (PHOTO_V2/_customs_share/{IV}/{時刻}/) に置き、
     「リンクを知っている全員」 · 見るだけ · 期限つきのリンクを作る (押した職員のログイン)。
     鍵: 置き場所 = _customs_share/{IV}/{時刻}/ の下だけ · 名前 = PHOTO.zip / 搬入票.zip だけ · 同じ名前があれば失敗 (上書きしない) ·
         リンクの範囲が anonymous でなければ 失敗 (通関業者が開けないリンクを送らない) · 期限が返らなければ 失敗 */
  var SHARE_TOP = '_customs_share';
  var SHARE_NAMES = ['PHOTO.zip', '搬入票.zip'];
  Graph.prototype.customsShareUpload = function (ivNo, stamp, zips, expiresIso) {
    var self = this;
    if (!/^[A-Z]{1,4}\d{4}-\d{1,3}$/.test(String(ivNo || '')) || !/^\d{8}-\d{6}$/.test(String(stamp || ''))) return Promise.reject(new Error('置き場所の名前が違います'));
    if (!(zips || []).length || zips.some(function (z) { return SHARE_NAMES.indexOf(z.name) < 0 || !(z.bytes instanceof Uint8Array) || !z.bytes.length; })) return Promise.reject(new Error('zip の名前 · 中身が違います'));
    var J = function (method, url, body) {
      return self._fetch(url, { method: method, headers: { 'Content-Type': 'application/json' }, body: body == null ? undefined : JSON.stringify(body) }).then(function (r) {
        if (r.status === 403) throw new Error('SharePoint の権限がありません (403)');
        if (!r.ok) return r.text().then(function (x) { var c = ''; try { c = (JSON.parse(x).error || {}).code || ''; } catch (e) { c = ''; } throw new Error(method + ' 失敗 (' + r.status + (c ? ' ' + c : '') + ')'); });
        return r.json();
      });
    };
    var out = [];
    var one = function (z) {
      var rel = SHARE_TOP + '/' + ivNo + '/' + stamp + '/' + z.name;
      return J('POST', self._item(rel) + '/createUploadSession', { item: { '@microsoft.graph.conflictBehavior': 'fail' } }).then(function (us) {
        var u8 = z.bytes, CH = 320 * 1024 * 10, pos = 0, last = null;
        var next = function () {
          if (pos >= u8.length) return Promise.resolve(last);
          var end = Math.min(pos + CH, u8.length);
          return fetch(us.uploadUrl, { method: 'PUT', headers: { 'Content-Range': 'bytes ' + pos + '-' + (end - 1) + '/' + u8.length }, body: u8.slice(pos, end) }).then(function (r) {
            if (!r.ok) throw new Error(z.name + ' のアップロード失敗 (' + r.status + ')');
            pos = end;
            return (end >= u8.length ? r.json() : Promise.resolve(null)).then(function (j) { last = j; return next(); });
          });
        };
        return next();
      }).then(function (item) {
        if (!item || !item.id || item.size !== z.bytes.length) throw new Error(z.name + ' の大きさが合いません');
        return J('POST', GRAPH + 'drives/' + LEENAI.SP.DRIVE_ID + '/items/' + encodeURIComponent(item.id) + '/createLink', { type: 'view', scope: 'anonymous', expirationDateTime: expiresIso }).then(function (lk) {
          var L = (lk && lk.link) || {};
          if (L.scope !== 'anonymous' || !L.webUrl) throw new Error('「リンクを知っている全員」 のリンクを作れません（範囲 = ' + (L.scope || '不明') + '）');
          if (!lk.expirationDateTime) throw new Error('リンクの期限を付けられません');
          out.push({ name: z.name, item_id: item.id, path: rel, size: item.size, n: z.n, url: L.webUrl, expires: lk.expirationDateTime, perm_id: lk.id || '' });
        });
      });
    };
    return zips.reduce(function (p, z) { return p.then(function () { return one(z); }); }, Promise.resolve()).then(function () { return out; });
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
