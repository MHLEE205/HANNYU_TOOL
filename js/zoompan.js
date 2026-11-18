/* ✦ Powered by LEENAI Automation System — C-01 搬入票 TOOL 写真の拡大 · 移動 (v0.3.55 · R10Y · ZHAN 提案 · 決定 #313)
   写真タブ (photo.html) · この画面の写真 (ライトボックス) · 「拡大・補正」 の 2 枚 — 同じ部品を使う。
   - ホイール (Ctrl なし) = カーソルの所を中心に 1〜6 倍 · Ctrl + ホイール = ブラウザの拡大 (止めない)
   - 拡大中 = 引っ張って移動 (マウス · 指 1 本) · 指 2 本 = 拡大縮小 · ダブルクリック = 2.5 倍 ↔ 元の大きさ
   - 矢印キー = 拡大中だけ移動 (呼ぶ側が keyHandled で確かめる · 1 倍の時は 前へ / 次へ のまま)
   - 1 倍の時だけ 指で左右に払う = 前へ / 次へ (onSwipe) — 拡大中の引っ張りと重ならない
   - 動かすのは CSS transform だけ (canvas に描き直さない · 12MP でも軽い) · 元のファイルは変えない
   - targets が複数 (拡大・補正 の 原本 · 補正画像) = 同じ倍率 · 同じ位置 (同じ所を比べる)。位置は要素の大きさに対する割合で持つ */
'use strict';
window.C01 = window.C01 || {};

(function () {
  var MIN = 1, MAX = 6, STEP = 1.15, DBL = 2.5, KEY_STEP = 0.1, SWIPE_PX = 60;

  function ZoomPan(stage, targets, opt) {
    this.stage = stage;
    this.targets = (targets || []).filter(Boolean);
    this.opt = opt || {};
    this.s = 1; this.fx = 0; this.fy = 0;
    this.ptrs = {}; this.drag = null; this.pinch = null; this.swipe = null;
    this.targets.forEach(function (t) { t.style.transformOrigin = '0 0'; t.style.transition = 'none'; t.style.willChange = 'transform'; t.draggable = false; });
    this.stage.classList.add('c01-zp');
    this._bind();
    this.apply();
  }
  ZoomPan.prototype.box = function (t) {           /* 拡大前の要素の大きさ (画面 px) */
    var r = (t || this.targets[0]).getBoundingClientRect();
    return { left: r.left, top: r.top, w: r.width / this.s, h: r.height / this.s };
  };
  ZoomPan.prototype.clamp = function () {
    this.s = Math.max(MIN, Math.min(MAX, this.s));
    if (this.s <= MIN + 1e-6) { this.s = 1; this.fx = 0; this.fy = 0; return; }
    this.fx = Math.min(0, Math.max(1 - this.s, this.fx));     /* 拡大した写真が元の枠を必ず覆う (はみ出して空が見えない) */
    this.fy = Math.min(0, Math.max(1 - this.s, this.fy));
  };
  ZoomPan.prototype.apply = function () {
    this.clamp();
    var tf = this.s === 1 ? '' : 'translate(' + (this.fx * 100).toFixed(3) + '%,' + (this.fy * 100).toFixed(3) + '%) scale(' + this.s.toFixed(4) + ')';
    this.targets.forEach(function (t) { t.style.transform = tf; });
    this.stage.setAttribute('data-zoom', this.s.toFixed(2));
    this.stage.classList.toggle('c01-zp-on', this.s > 1);
    if (this.opt.onChange) this.opt.onChange(this.s);
  };
  /* 画面の点 (cx, cy) を動かさずに倍率 ns へ (t = その点の下の要素) */
  ZoomPan.prototype.zoomAt = function (ns, cx, cy, t) {
    var b = this.box(t);
    var px = b.w ? (cx - b.left) / (b.w * this.s) : 0.5, py = b.h ? (cy - b.top) / (b.h * this.s) : 0.5;   /* 要素内の割合 (拡大前の座標) */
    px = Math.max(0, Math.min(1, px)); py = Math.max(0, Math.min(1, py));
    ns = Math.max(MIN, Math.min(MAX, ns));
    this.fx += px * (this.s - ns); this.fy += py * (this.s - ns);
    this.s = ns;
    this.apply();
  };
  ZoomPan.prototype.center = function () {         /* 枠の見えている真ん中 */
    var r = this.stage.getBoundingClientRect();
    return [r.left + r.width / 2, r.top + r.height / 2];
  };
  ZoomPan.prototype.zoomBy = function (k) { var c = this.center(); this.zoomAt(this.s * k, c[0], c[1]); };
  ZoomPan.prototype.reset = function () { this.s = 1; this.fx = 0; this.fy = 0; this.apply(); };
  ZoomPan.prototype.panPx = function (dx, dy, t) {
    var b = this.box(t);
    if (b.w) this.fx += dx / b.w;
    if (b.h) this.fy += dy / b.h;
    this.apply();
  };
  /* 矢印キー: 拡大中だけ移動して true · 1 倍なら false (呼ぶ側が 前へ / 次へ) */
  ZoomPan.prototype.keyHandled = function (e) {
    if (this.s <= 1) return false;
    var m = { ArrowLeft: [1, 0], ArrowRight: [-1, 0], ArrowUp: [0, 1], ArrowDown: [0, -1] }[e.key];
    if (!m) return false;
    this.fx += m[0] * KEY_STEP * this.s / 2; this.fy += m[1] * KEY_STEP * this.s / 2;
    this.apply();
    if (e.preventDefault) e.preventDefault();
    return true;
  };
  ZoomPan.prototype.targetAt = function (el) {
    for (var i = 0; i < this.targets.length; i++) if (this.targets[i] === el || this.targets[i].contains(el)) return this.targets[i];
    return this.targets[0];
  };
  ZoomPan.prototype._bind = function () {
    var self = this, st = this.stage;
    st.addEventListener('wheel', function (e) {
      if (e.ctrlKey || e.metaKey) return;                         /* Ctrl + ホイール = ブラウザの拡大 (止めない) */
      e.preventDefault();                                          /* この枠の中だけ (外のスクロールはそのまま) */
      self.zoomAt(self.s * (e.deltaY < 0 ? STEP : 1 / STEP), e.clientX, e.clientY, self.targetAt(e.target));
    }, { passive: false });
    st.addEventListener('dblclick', function (e) {
      e.preventDefault();
      if (self.s > 1) self.reset(); else self.zoomAt(DBL, e.clientX, e.clientY, self.targetAt(e.target));
    });
    st.addEventListener('pointerdown', function (e) {
      if (e.button !== undefined && e.button !== 0) return;
      if (e.target && e.target.closest && e.target.closest('button,a,input,select,textarea')) return;
      self.ptrs[e.pointerId] = { x: e.clientX, y: e.clientY, t: self.targetAt(e.target) };
      try { st.setPointerCapture(e.pointerId); } catch (x) { /* なし */ }
      var ids = Object.keys(self.ptrs);
      if (ids.length === 2) {
        var a = self.ptrs[ids[0]], b = self.ptrs[ids[1]];
        self.pinch = { d: Math.hypot(a.x - b.x, a.y - b.y) || 1, s: self.s };
        self.drag = null; self.swipe = null;
      } else if (ids.length === 1) {
        if (self.s > 1) self.drag = { x: e.clientX, y: e.clientY, t: self.ptrs[e.pointerId].t };
        else if (e.pointerType && e.pointerType !== 'mouse') self.swipe = { x: e.clientX, y: e.clientY };
      }
    });
    st.addEventListener('pointermove', function (e) {
      var p = self.ptrs[e.pointerId];
      if (!p) return;
      p.x = e.clientX; p.y = e.clientY;
      var ids = Object.keys(self.ptrs);
      if (self.pinch && ids.length >= 2) {
        var a = self.ptrs[ids[0]], b = self.ptrs[ids[1]];
        var d = Math.hypot(a.x - b.x, a.y - b.y) || 1;
        self.zoomAt(self.pinch.s * d / self.pinch.d, (a.x + b.x) / 2, (a.y + b.y) / 2, a.t);
        e.preventDefault();
        return;
      }
      if (self.drag) {
        self.panPx(e.clientX - self.drag.x, e.clientY - self.drag.y, self.drag.t);
        self.drag.x = e.clientX; self.drag.y = e.clientY;
        st.classList.add('c01-zp-drag');
        e.preventDefault();
      }
    });
    function up(e) {
      var sw = self.swipe;
      delete self.ptrs[e.pointerId];
      if (Object.keys(self.ptrs).length < 2) self.pinch = null;
      if (!Object.keys(self.ptrs).length) { self.drag = null; st.classList.remove('c01-zp-drag'); }
      self.swipe = null;
      if (sw && self.s <= 1 && e.type === 'pointerup' && self.opt.onSwipe) {   /* 1 倍の時だけ 払う = 前へ / 次へ */
        var dx = e.clientX - sw.x, dy = e.clientY - sw.y;
        if (Math.abs(dx) >= SWIPE_PX && Math.abs(dx) > Math.abs(dy) * 1.5) self.opt.onSwipe(dx < 0 ? 1 : -1);
      }
    }
    st.addEventListener('pointerup', up);
    st.addEventListener('pointercancel', up);
  };
  ZoomPan.MIN = MIN; ZoomPan.MAX = MAX; ZoomPan.DBL = DBL;
  C01.ZoomPan = ZoomPan;
  /* 拡大の ボタン (− · 倍率 · ＋ · 全体表示) — 呼ぶ側が HTML を置き、ここで結ぶ */
  C01.zoomBar = function (idp) {
    return '<span class="c01-zp-bar" id="' + idp + '-bar"><button type="button" class="c01-zp-b" id="' + idp + '-out" aria-label="縮小" title="縮小">−</button>' +
      '<span class="c01-zp-v" id="' + idp + '-v">100%</span>' +
      '<button type="button" class="c01-zp-b" id="' + idp + '-in" aria-label="拡大" title="拡大（ホイール · ダブルクリック · 指 2 本でも）">＋</button>' +
      '<button type="button" class="c01-zp-b c01-zp-fit" id="' + idp + '-fit" title="全体を表示（元の大きさ）">全体表示</button></span>';
  };
  C01.zoomBind = function (zp, idp) {
    var g = function (s) { return document.getElementById(idp + '-' + s); };
    if (g('in')) g('in').onclick = function () { zp.zoomBy(1.5); };
    if (g('out')) g('out').onclick = function () { zp.zoomBy(1 / 1.5); };
    if (g('fit')) g('fit').onclick = function () { zp.reset(); };
    var prev = zp.opt.onChange;
    zp.opt.onChange = function (s) { var v = g('v'); if (v) v.textContent = Math.round(s * 100) + '%'; if (prev) prev(s); };
    zp.apply();
    return zp;
  };
})();
