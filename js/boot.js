/* ✦ Powered by LEENAI Automation System — 起動 (LEENAI_COMMON を読むだけ・変更しない)
   - LEENAI.init にバージョン (C01.TOOL_INFO) を渡す = 表示はこの 1 か所から
   - local モード: Pages アドレスがなくログイン (PKCE) できないので、ログインカードに「ローカルプレビューで開く」を足す
     (127.0.0.1 サーバー or フォルダ選択)。graph モード (R7A) は LEENAI の onReady (ログイン後) から始める (C01.SOURCE.graphEnabled) */
'use strict';
(function () {
  var I = C01.TOOL_INFO;

  function buildHeader() {
    /* LEENAI_COMMON のヘッダーと同じ部品 (ln-*) — ログイン無しのローカル版なのでログアウトの代わりに「閉じる」 */
    if (document.getElementById('ln-header')) return;
    var h = document.createElement('header');
    h.className = 'ln-header'; h.id = 'ln-header';
    h.innerHTML = '<div class="ln-logo">LEEN<span>AI</span></div><span class="ln-sys">' + I.sys + '</span><div class="ln-hdr-sep"></div>' +
      '<span class="ln-hdr-name">' + I.name + '</span><span class="ln-hdr-ver">v' + I.version + ' · ' + I.date + '</span>' +
      '<div class="ln-hdr-right"><span class="ln-user"><span class="ln-avatar" id="ln-avatar">--</span><span id="ln-username"></span>' +
      '<span class="ln-dot" title="ローカル (SharePoint 未接続)" style="background:var(--warn)"></span></span>' +
      '<button class="ln-btn-ghost" data-ln="themeBtn" id="c01-theme">🌙 ダーク</button>' +
      '<button class="ln-btn-ghost" id="c01-close" title="ローカルプレビューを閉じる">閉じる</button></div>';
    var app = document.getElementById('app');
    app.insertBefore(h, app.firstChild);
    document.getElementById('c01-theme').onclick = function () {
      if (window.LEENAI && LEENAI._toggleTheme) LEENAI._toggleTheme(); else localToggle();
    };
    document.getElementById('c01-close').onclick = function () { location.reload(); };
    var th = 'dark';
    try { th = localStorage.getItem('leenai_theme') || 'dark'; } catch (e) { /* なし */ }
    if (!(window.LEENAI && LEENAI._toggleTheme)) applyLocal(th);
    else document.querySelectorAll('[data-ln="themeBtn"]').forEach(function (b) { b.textContent = LABEL[document.documentElement.getAttribute('data-theme') || th]; });
  }
  var THEMES = ['dark', 'light', 'leenai', 'focus'];
  var LABEL = { dark: '🌙 ダーク', light: '☀️ ライト', leenai: '🌿 LEENAI', focus: '🎯 FOCUS' };
  function applyLocal(t) {
    document.documentElement.setAttribute('data-theme', t);
    document.querySelectorAll('[data-ln="themeBtn"]').forEach(function (b) { b.textContent = LABEL[t]; });
  }
  function localToggle() {
    var cur = document.documentElement.getAttribute('data-theme') || 'dark';
    var next = THEMES[(THEMES.indexOf(cur) + 1) % THEMES.length];
    try { localStorage.setItem('leenai_theme', next); } catch (e) { /* なし */ }
    applyLocal(next);
  }

  function openApp(src) {
    var sp = document.getElementById('ln-splash');
    if (sp) sp.style.display = 'none';
    var app = document.getElementById('app');
    app.style.display = '';
    buildHeader();
    C01.app.start(src);
  }

  function addLocalButtons() {
    var card = document.querySelector('#ln-splash .ln-splash-card');
    if (!card || document.getElementById('c01-local-box')) return;
    var box = document.createElement('div');
    box.id = 'c01-local-box';
    box.className = 'c01-local-box';
    var server = location.protocol.indexOf('http') === 0 && (location.hostname === '127.0.0.1' || location.hostname === 'localhost');
    box.innerHTML = '<div class="c01-local-title">ローカルプレビュー（ログインなし · データは選んだフォルダから）</div>' +
      (server ? '<button class="ln-login-btn c01-local-btn" id="c01-open-server">ローカルプレビューで開く</button>' : '') +
      '<button class="ln-btn-ghost c01-local-btn2" id="c01-open-folder">フォルダを選んで開く（_data があるフォルダ）</button>' +
      '<div class="ln-login-note">' + (C01.SOURCE.graphEnabled ? '本番データは上の「Microsoft 365 でログイン」から (SharePoint ' + (C01.SOURCE.spLabel || C01.SOURCE.spRoot) + ')' : 'Microsoft 365 ログイン (SharePoint) は無効です') + '</div>';
    card.insertBefore(box, card.querySelector('.ln-splash-theme'));
    var bs = document.getElementById('c01-open-server');
    if (bs) bs.onclick = function () { openApp(new C01.sources.LocalServer()); };
    document.getElementById('c01-open-folder').onclick = function () {
      C01.sources.Folder.pick().then(openApp).catch(function (e) { alert(e.message); });
    };
    var lb = document.getElementById('ln-login-btn');
    if (lb && !C01.SOURCE.graphEnabled) { lb.disabled = true; lb.title = '無効 (C01.SOURCE.graphEnabled)'; lb.classList.add('c01-disabled'); }
  }

  function fallbackSplash(msg) {
    /* 共通ファイルを読めない時 (DOC-Z-05 §2-4): メッセージ + ローカルプレビューだけ */
    var d = document.createElement('div');
    d.id = 'ln-splash'; d.className = 'ln-splash c01-fallback';
    d.innerHTML = '<div class="ln-splash-card"><div class="ln-logo">LEEN<span>AI</span></div><div class="ln-splash-meta"><span class="ln-sys">' + I.sys +
      '</span><span class="ln-splash-ver">v' + I.version + ' · ' + I.date + '</span></div><div class="ln-splash-name">' + I.name + '</div>' +
      '<p class="c01-err">' + msg + '</p><div class="ln-splash-theme"></div></div><div class="ln-footer">✦ Powered by LEENAI Automation System</div>';
    document.body.insertBefore(d, document.body.firstChild);
    document.getElementById('app').style.display = 'none';
    document.title = 'LEENAI ' + I.sys + ' ' + I.name + ' v' + I.version;
    var th = 'dark';
    try { th = localStorage.getItem('leenai_theme') || 'dark'; } catch (e) { /* なし */ }
    applyLocal(th);
    addLocalButtons();
  }

  window.addEventListener('DOMContentLoaded', function () {
    if (!window.LEENAI || !LEENAI.init) { fallbackSplash('共通ファイルの読み込みに失敗しました'); return; }
    LEENAI.init({
      sys: I.sys, name: I.name, version: I.version, date: I.date, desc: I.desc,
      needGraph: true,
      onReady: function () {
        /* graph モード (R7A): ログイン後 SharePoint C01.SOURCE.spRoot (v0.3.30 = PHOTO_V2) から読む (ヘッダーは LEENAI_COMMON) */
        if (C01.SOURCE.graphEnabled) { var b = document.getElementById('c01-local-box'); if (b) b.style.display = 'none'; C01.app.start(new C01.sources.Graph()); }
      }
    });
    addLocalButtons();
  });
})();
