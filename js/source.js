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
    ['①', /通関\s*[＆&、・]?\s*(ドレージ)?(の)?(ご)?依頼|ドレージ\s*[、・＆&]?\s*通関|新規ドレージ(の)?(ご)?依頼/],
    ['業者', /ブッキング情報のご案内/]];   /* ブッキング情報のご案内 = 圧縮業者あて (① ではない · 実メール 2 週 21 件で確認) */
  function isS1Subject(s) {
    var h = stripRe(s), best = null;
    KW_ORDER.forEach(function (k) { var m = k[1].exec(h); if (m && (best === null || m.index < best[0])) best = [m.index, k[0]]; });
    return !!best && best[1] === '①';
  }
  Graph.prototype._mailGet = function (path) {
    return this._fetch(GRAPH + path).then(function (r) {
      if (r.status === 403) throw new Error('メールを読む権限がありません (403)');
      if (!r.ok) throw new Error('メールの検索に失敗 (' + r.status + ')');
      return r.json();
    });
  };
  /* ① = 件名に BKG があり ① の件名の、自社から送ったメール (一番新しいもの) → その会話の一番新しいメール (下書き除く) */
  Graph.prototype.customsFindS1 = function (bkg) {
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
    return self._mailGet('me/messages?$search=' + encodeURIComponent('"' + raw.replace(/"/g, '') + '"') + '&$top=50&' + MSG_SEL).then(function (j) {
      var xs = (j.value || []).filter(function (m) {
        return !m.isDraft && addrOf(m.from).split('@')[1] === oursDom() && isS1Subject(m.subject) && hasBkg(m.subject);
      }).sort(function (x, y) { return String(y.sentDateTime || '').localeCompare(String(x.sentDateTime || '')); });
      if (!xs.length) return null;
      var s1 = xs[0];
      return self._mailGet('me/messages?$filter=' + encodeURIComponent("conversationId eq '" + s1.conversationId.replace(/'/g, "''") + "'") + '&$top=100&' + MSG_SEL).then(function (c) {
        var L = (c.value || []).filter(function (m) { return !m.isDraft; }).sort(function (x, y) {
          return String(x.sentDateTime || x.receivedDateTime || '').localeCompare(String(y.sentDateTime || y.receivedDateTime || ''));
        });
        var last = L.length ? L[L.length - 1] : s1;
        var pack = function (m) { return { id: m.id, subject: m.subject || '', at: m.sentDateTime || m.receivedDateTime || '', from: addrOf(m.from), from_name: nameOf(m.from),
          to: (m.toRecipients || []).map(function (r) { return { a: addrOf(r), n: nameOf(r) }; }), cc: (m.ccRecipients || []).map(function (r) { return { a: addrOf(r), n: nameOf(r) }; }) }; };
        return { s1: pack(s1), last: pack(last), n_conv: L.length, s1_count: xs.length };
      });
    });
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
    var test = C.sendTest !== false;
    var low = function (a) { return String(a || '').trim().toLowerCase(); };
    if (!C.enabled || !m || !m.replyToId || !m.pdf_b64 || !m.file) return Promise.reject(new Error('送信の条件がそろっていません — 送信しません'));
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
    return J('POST', 'me/messages/' + encodeURIComponent(m.replyToId) + '/createReplyAll', {}).then(function (d) {
      draft = d;
      var html = String((d.body || {}).content || '');
      var mine = '<div>' + m.html + '</div>';
      html = /<body[^>]*>/i.test(html) ? html.replace(/<body[^>]*>/i, function (x) { return x + mine; }) : mine + html;
      return J('PATCH', 'me/messages/' + encodeURIComponent(d.id), { subject: m.subject, body: { contentType: 'HTML', content: html }, toRecipients: rcp(to), ccRecipients: rcp(cc), bccRecipients: [] });
    }).then(function () {
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
        J('GET', 'me/messages/' + encodeURIComponent(draft.id) + '/attachments?$select=name,size')]);
    }).then(function (r) {
      var d = r[0], at = r[1].value || [];
      var got = function (xs) { return (xs || []).map(addrOf).sort().join(','); };
      if (d.subject !== m.subject) throw new Error('下書きの件名が違います — 送信しません（下書きは 下書き フォルダに残っています）');
      if (got(d.toRecipients) !== to.slice().sort().join(',') || got(d.ccRecipients) !== cc.slice().sort().join(',') || (d.bccRecipients || []).length) {
        throw new Error('下書きの宛先が確認窓と違います — 送信しません（下書きは 下書き フォルダに残っています）');
      }
      if (at.length !== 1 || at[0].name !== m.file) throw new Error('添付が ' + m.file + ' 1 つではありません — 送信しません（下書きは 下書き フォルダに残っています）');
      if (m.conv && d.conversationId && d.conversationId !== m.conv) throw new Error('① の会話ではありません — 送信しません');
      return J('POST', 'me/messages/' + encodeURIComponent(draft.id) + '/send', null).then(function () {
        return { ok: true, test: test, internet_message_id: d.internetMessageId || '', to: to, cc: cc };
      });
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
