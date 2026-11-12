# -*- coding: utf-8 -*-
"""فایل‌های استاتیک ادغام: widget.js (چت‌بات قابل نصب در سایر سامانه‌ها) + صفحه آزمایش

widget.js با یک خط به هر سامانه‌ای (پژوهشیار، برنامه‌ریز، پرتال، LMS، ...) اضافه می‌شود:

  <script src="http://HOST/api/v1/integration/widget.js"
          data-key="d360_..."
          data-url="http://HOST"
          data-title="دستیار آیین‌نامه‌ای"></script>

پیکربندی اختیاری: data-position (left/right)، data-student (JSON پروفایل دانشجو)
و یا متغیر جهانی window.DastyarStudent (پروفایل پویا از سامانه میزبان).
"""

WIDGET_JS = r"""/*!
 * DastyarAmoozeshi Embeddable Assistant Widget v0.3.0
 * دستیار آموزشی و آیین‌نامه‌ای دانشجو۳۶۰ — چت‌بات قابل نصب در سایر سامانه‌ها
 * تمام پاسخ‌ها «مستند و مستند-نمونه» است؛ هیچ پاسخی بدون استناد ارائه نمی‌شود.
 */
(function () {
  'use strict';
  if (window.__Dastyar360WidgetLoaded) return;
  window.__Dastyar360WidgetLoaded = true;

  var script = document.currentScript || (function () {
    var s = document.getElementsByTagName('script');
    return s[s.length - 1];
  })();

  function attr(name, def) {
    var v = script && script.getAttribute && script.getAttribute('data-' + name);
    return (v === null || v === undefined || v === '') ? def : v;
  }

  var KEY = attr('key', '');
  var TITLE = attr('title', 'دستیار آیین‌نامه‌ای');
  var SUBTITLE = attr('subtitle', 'دانشجو۳۶۰ · پاسخ مستند با استناد');
  var POS = attr('position', 'left') === 'right' ? 'right' : 'left';

  var BASE = attr('url', '');
  if (!BASE && script && script.src) { try { BASE = new URL(script.src).origin; } catch (e) {} }
  if (!BASE) BASE = location.origin;
  BASE = String(BASE).replace(/\/+$/, '');

  var GW = null;
  try { GW = new URLSearchParams(location.search).get('XTransformPort'); } catch (e) {}

  function api(path) {
    return BASE + path + (GW ? (path.indexOf('?') >= 0 ? '&' : '?') + 'XTransformPort=' + GW : '');
  }

  function hostStudent() {
    if (window.DastyarStudent) return window.DastyarStudent;
    try { return JSON.parse(attr('student', '{}') || '{}'); } catch (e) { return {}; }
  }

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  var CSS = ''
    + "@font-face{font-family:'VazirmatnW';src:url(" + BASE + "/fonts/vazirmatn-400.woff2) format('woff2');font-weight:400;font-display:swap;}"
    + "@font-face{font-family:'VazirmatnW';src:url(" + BASE + "/fonts/vazirmatn-700.woff2) format('woff2');font-weight:700;font-display:swap;}"
    + ":host{all:initial;}"
    + "*{box-sizing:border-box;font-family:'VazirmatnW',Vazirmatn,'Segoe UI',Tahoma,sans-serif;}"
    + ".d360-launcher{position:fixed;bottom:22px;__POS__:22px;width:60px;height:60px;border-radius:22px;"
    + "border:none;cursor:pointer;z-index:2147483000;display:flex;align-items:center;justify-content:center;"
    + "background:linear-gradient(135deg,#7c3aed,#6366f1 55%,#0ea5e9);box-shadow:0 14px 38px -8px rgba(124,58,237,.65);"
    + "transition:transform .25s ease,box-shadow .25s ease;}"
    + ".d360-launcher:hover{transform:translateY(-3px) scale(1.04);box-shadow:0 20px 46px -8px rgba(124,58,237,.8);}"
    + ".d360-launcher svg{width:28px;height:28px;}"
    + ".d360-pulse{position:absolute;inset:0;border-radius:22px;border:2px solid rgba(167,139,250,.55);animation:d360p 2.2s ease-out infinite;}"
    + "@keyframes d360p{0%{transform:scale(1);opacity:.8;}100%{transform:scale(1.45);opacity:0;}}"
    + ".d360-panel{position:fixed;bottom:96px;__POS__:22px;width:392px;max-width:calc(100vw - 24px);"
    + "height:min(600px,calc(100vh - 130px));border-radius:22px;overflow:hidden;z-index:2147483000;"
    + "display:none;flex-direction:column;direction:rtl;color:#e2e8f0;"
    + "background:rgba(8,11,23,.94);border:1px solid rgba(255,255,255,.12);"
    + "box-shadow:0 30px 80px -20px rgba(0,0,0,.75),0 0 0 1px rgba(124,58,237,.15);"
    + "backdrop-filter:blur(22px) saturate(150%);-webkit-backdrop-filter:blur(22px) saturate(150%);"
    + "animation:d360in .3s ease both;}"
    + ".d360-panel.open{display:flex;}"
    + "@keyframes d360in{from{opacity:0;transform:translateY(16px) scale(.97);}to{opacity:1;transform:none;}}"
    + ".d360-head{padding:14px 16px;background:linear-gradient(135deg,rgba(124,58,237,.35),rgba(14,165,233,.22));"
    + "border-bottom:1px solid rgba(255,255,255,.1);display:flex;align-items:center;gap:11px;}"
    + ".d360-avatar{width:40px;height:40px;border-radius:14px;flex-shrink:0;display:flex;align-items:center;justify-content:center;"
    + "background:linear-gradient(135deg,#7c3aed,#0ea5e9);box-shadow:0 8px 20px -6px rgba(124,58,237,.7);}"
    + ".d360-avatar svg{width:21px;height:21px;}"
    + ".d360-head-t{flex:1;min-width:0;}"
    + ".d360-head-t b{display:block;font-size:14px;color:#fff;}"
    + ".d360-head-t span{display:block;font-size:10.5px;color:#a5b4fc;margin-top:2px;}"
    + ".d360-badge{font-size:9px;font-weight:700;color:#fcd34d;border:1px solid rgba(245,158,11,.4);"
    + "background:rgba(245,158,11,.12);border-radius:99px;padding:2px 8px;white-space:nowrap;}"
    + ".d360-close{background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.14);color:#cbd5e1;"
    + "width:28px;height:28px;border-radius:9px;cursor:pointer;font-size:14px;line-height:1;flex-shrink:0;}"
    + ".d360-close:hover{background:rgba(255,255,255,.13);}"
    + ".d360-body{flex:1;overflow-y:auto;padding:14px;display:flex;flex-direction:column;gap:10px;}"
    + ".d360-body::-webkit-scrollbar{width:8px;}"
    + ".d360-body::-webkit-scrollbar-thumb{background:rgba(148,163,184,.25);border-radius:99px;}"
    + ".d360-welcome{background:rgba(255,255,255,.045);border:1px solid rgba(255,255,255,.1);border-radius:14px;padding:11px 13px;font-size:12.5px;line-height:1.9;color:#cbd5e1;}"
    + ".d360-welcome b{color:#c4b5fd;}"
    + ".d360-msg{max-width:88%;padding:9px 13px;border-radius:14px;font-size:12.5px;line-height:1.9;animation:d360m .3s ease both;white-space:pre-wrap;word-break:break-word;}"
    + "@keyframes d360m{from{opacity:0;transform:translateY(10px);}to{opacity:1;transform:none;}}"
    + ".d360-user{align-self:flex-start;background:linear-gradient(135deg,#7c3aed,#6366f1);color:#fff;border-bottom-left-radius:5px;box-shadow:0 8px 22px -10px rgba(124,58,237,.8);}"
    + ".d360-bot{align-self:flex-end;background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.1);border-bottom-right-radius:5px;max-width:100%;width:100%;}"
    + ".d360-warn{background:rgba(245,158,11,.1);border:1px solid rgba(245,158,11,.35);color:#fcd34d;border-radius:10px;padding:7px 10px;font-size:11px;line-height:1.8;margin:6px 0;}"
    + ".d360-h{font-size:11px;font-weight:700;color:#a78bfa;margin:9px 0 4px;display:flex;align-items:center;gap:5px;}"
    + ".d360-h::before{content:'';width:6px;height:6px;border-radius:99px;background:linear-gradient(135deg,#a78bfa,#22d3ee);}"
    + ".d360-short{font-size:12.5px;line-height:1.9;}"
    + ".d360-li{font-size:11.5px;line-height:1.9;color:#cbd5e1;padding-inline-start:14px;position:relative;margin:2px 0;}"
    + ".d360-li::before{content:'•';position:absolute;right:0;color:#818cf8;}"
    + ".d360-li-num{padding-inline-start:18px;counter-increment:d360s;}"
    + ".d360-li-num::before{content:counter(d360s) '.';color:#818cf8;font-weight:700;}"
    + ".d360-ol{margin:0;padding:0;list-style:none;counter-reset:d360s;}"
    + ".d360-state{display:flex;align-items:center;gap:7px;font-size:11.5px;margin:5px 0;background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.07);border-radius:10px;padding:6px 9px;flex-wrap:wrap;}"
    + ".d360-tag{font-size:9.5px;font-weight:700;border-radius:99px;padding:2px 8px;white-space:nowrap;}"
    + ".d360-ok{background:rgba(16,185,129,.14);color:#6ee7b7;border:1px solid rgba(16,185,129,.35);}"
    + ".d360-no{background:rgba(244,63,94,.13);color:#fda4af;border:1px solid rgba(244,63,94,.4);}"
    + ".d360-info{background:rgba(245,158,11,.13);color:#fcd34d;border:1px solid rgba(245,158,11,.4);}"
    + ".d360-rev{background:rgba(14,165,233,.13);color:#7dd3fc;border:1px solid rgba(14,165,233,.4);}"
    + ".d360-src{background:rgba(124,58,237,.08);border:1px solid rgba(139,92,246,.3);border-radius:11px;padding:8px 10px;margin:5px 0;}"
    + ".d360-src b{display:flex;align-items:center;gap:6px;font-size:11px;color:#c4b5fd;flex-wrap:wrap;}"
    + ".d360-src .ref{background:rgba(167,139,250,.2);border-radius:6px;padding:0 6px;font-size:10px;color:#ddd6fe;}"
    + ".d360-src p{margin:5px 0 0;font-size:11px;line-height:1.9;color:#e2e8f0;white-space:pre-wrap;}"
    + ".d360-src .meta{font-size:9.5px;color:#94a3b8;margin-top:4px;}"
    + ".d360-foot{font-size:9.5px;color:#64748b;line-height:1.8;margin-top:8px;border-top:1px dashed rgba(255,255,255,.1);padding-top:7px;}"
    + ".d360-chips{display:flex;gap:6px;flex-wrap:wrap;padding:0 14px 8px;}"
    + ".d360-chip{font-size:10.5px;color:#c4b5fd;background:rgba(124,58,237,.12);border:1px solid rgba(139,92,246,.35);"
    + "border-radius:99px;padding:4px 11px;cursor:pointer;transition:all .2s;}"
    + ".d360-chip:hover{background:rgba(124,58,237,.3);color:#fff;}"
    + ".d360-inputrow{display:flex;gap:8px;padding:11px 14px;border-top:1px solid rgba(255,255,255,.09);background:rgba(5,7,15,.6);}"
    + ".d360-inp{flex:1;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.14);border-radius:12px;"
    + "padding:9px 13px;color:#e2e8f0;font-size:12.5px;outline:none;transition:border-color .2s;}"
    + ".d360-inp:focus{border-color:rgba(167,139,250,.65);box-shadow:0 0 0 3px rgba(124,58,237,.16);}"
    + ".d360-inp::placeholder{color:#64748b;}"
    + ".d360-send{width:42px;height:42px;border-radius:12px;border:none;cursor:pointer;flex-shrink:0;"
    + "background:linear-gradient(135deg,#7c3aed,#0ea5e9);color:#fff;display:flex;align-items:center;justify-content:center;"
    + "box-shadow:0 8px 22px -8px rgba(124,58,237,.7);transition:transform .2s;}"
    + ".d360-send:hover:not(:disabled){transform:translateY(-2px);}"
    + ".d360-send:disabled{opacity:.55;cursor:not-allowed;}"
    + ".d360-send svg{width:18px;height:18px;transform:scaleX(-1);}"
    + ".d360-typing{display:inline-flex;gap:4px;align-items:center;padding:4px 0;}"
    + ".d360-dot{width:6px;height:6px;border-radius:99px;background:#a78bfa;animation:d360t 1.1s infinite;}"
    + ".d360-dot:nth-child(2){animation-delay:.18s;}.d360-dot:nth-child(3){animation-delay:.36s;}"
    + "@keyframes d360t{0%,100%{opacity:.3;}50%{opacity:1;}}"
    + "@media (max-width:480px){.d360-panel{bottom:86px;}}";

  var ICON_BOT = '<svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3l9 4.9-9 4.9-9-4.9L12 3z"/><path d="M5 10.5v4.6c0 1.6 3.1 3.4 7 3.4s7-1.8 7-3.4v-4.6"/></svg>';
  var ICON_SEND = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 2L11 13"/><path d="M22 2l-7 20-4-9-9-4 20-7z"/></svg>';

  var host = document.createElement('div');
  host.id = 'dastyar360-widget-root';
  document.documentElement.appendChild(host);
  var root = host.attachShadow ? host.attachShadow({ mode: 'open' }) : host;

  var style = document.createElement('style');
  style.textContent = CSS.split('__POS__').join(POS === 'right' ? 'right' : 'left');
  root.appendChild(style);

  var panel = document.createElement('div');
  panel.className = 'd360-panel';
  panel.innerHTML =
    '<div class="d360-head">'
    + '<div class="d360-avatar">' + ICON_BOT + '</div>'
    + '<div class="d360-head-t"><b>' + esc(TITLE) + '</b><span>' + esc(SUBTITLE) + '</span></div>'
    + '<span class="d360-badge">نمونه</span>'
    + '<button class="d360-close" title="بستن">✕</button>'
    + '</div>'
    + '<div class="d360-body" id="d360body"></div>'
    + '<div class="d360-chips" id="d360chips"></div>'
    + '<div class="d360-inputrow">'
    + '<input class="d360-inp" id="d360inp" placeholder="پرسش خود را بنویسید…" />'
    + '<button class="d360-send" id="d360send" title="ارسال">' + ICON_SEND + '</button>'
    + '</div>';
  root.appendChild(panel);

  var launcher = document.createElement('button');
  launcher.className = 'd360-launcher';
  launcher.title = 'دستیار آموزشی و آیین‌نامه‌ای';
  launcher.innerHTML = '<span class="d360-pulse"></span>' + ICON_BOT;
  root.appendChild(launcher);

  var body = panel.querySelector('#d360body');
  var inp = panel.querySelector('#d360inp');
  var sendBtn = panel.querySelector('#d360send');
  var chipsBox = panel.querySelector('#d360chips');
  var busy = false;

  var CHIPS = ['شرایط ثبت‌نام کارورزی چیست؟', 'سقف واحد ترم بعد چند واحد است؟', 'مهلت‌های پیشِ رو کدام‌اند؟'];

  function addHTML(html, cls) {
    var d = document.createElement('div');
    d.className = cls;
    d.innerHTML = html;
    body.appendChild(d);
    body.scrollTop = body.scrollHeight;
    return d;
  }

  function welcome() {
    if (body.children.length) return;
    addHTML('<b>سلام 👋</b><br>من دستیار مستند آیین‌نامه‌های آموزشی هستم. پاسخ‌ها فقط بر اساس اسناد ثبت‌شده در سامانه و <b>همراه با استناد</b> ارائه می‌شود. اگر پرسش شما در اسناد نباشد، صادقانه «یافت نشد» می‌گویم.', 'd360-welcome');
    CHIPS.forEach(function (c) {
      var b = document.createElement('span');
      b.className = 'd360-chip';
      b.textContent = c;
      b.onclick = function () { ask(c); };
      chipsBox.appendChild(b);
    });
  }

  function setBusy(v) {
    busy = v;
    sendBtn.disabled = v;
    inp.disabled = v;
  }

  var STATE_CLS = { satisfied: 'd360-ok', not_satisfied: 'd360-no', insufficient_info: 'd360-info', needs_review: 'd360-rev' };
  var STATE_FA = { satisfied: 'برقرار', not_satisfied: 'برقرار نیست', insufficient_info: 'اطلاعات ناکافی', needs_review: 'نیازمند بررسی کارشناس' };

  function renderAnswer(a) {
    var h = '';
    (a.warnings || []).forEach(function (w) { h += '<div class="d360-warn">⚠ ' + esc(w) + '</div>'; });
    if (a.no_result) {
      h += '<div class="d360-short">' + esc(a.note || 'موردی یافت نشد.') + '</div>';
    } else {
      if (a.short) h += '<div class="d360-short">' + esc(a.short) + '</div>';
      if ((a.conditions || []).length) {
        h += '<div class="d360-h">شرایط مهم</div>';
        a.conditions.forEach(function (c) { h += '<div class="d360-li">' + esc(c) + '</div>'; });
      }
      if ((a.status_rows || []).length) {
        h += '<div class="d360-h">وضعیت شما (ارزیابی قطعی)</div>';
        a.status_rows.forEach(function (r) {
          h += '<div class="d360-state"><span class="d360-tag ' + (STATE_CLS[r.state] || 'd360-info') + '">'
            + esc(r.state_fa || STATE_FA[r.state] || r.state) + '</span><span>' + esc(r.title) + '</span>'
            + (r.detail ? '<span style="width:100%;font-size:10.5px;color:#94a3b8;">' + esc(r.detail) + '</span>' : '')
            + '</div>';
        });
      }
      if ((a.next_steps || []).length) {
        h += '<div class="d360-h">اقدام بعدی پیشنهادی</div><div class="d360-ol">';
        a.next_steps.forEach(function (s) { h += '<div class="d360-li d360-li-num">' + esc(s) + '</div>'; });
        h += '</div>';
      }
      if ((a.sources || []).length) {
        h += '<div class="d360-h">منبع رسمی (متن سند)</div>';
        a.sources.forEach(function (s) {
          h += '<div class="d360-src"><b><span class="ref">' + esc(s.ref) + '</span>' + esc(s.doc_title)
            + (s.clause_ref ? '<span>' + esc(s.clause_ref) + '</span>' : '') + '</b>'
            + '<p>' + esc(s.excerpt) + '</p>'
            + '<div class="meta">نسخه ' + esc(s.version_no) + ' · ' + esc(s.status_fa) + (s.page_no ? ' · صفحه ' + esc(s.page_no) : '') + (s.url ? ' · ' + esc(s.url) : '') + '</div></div>';
        });
      }
      if ((a.confirmations || []).length) {
        h += '<div class="d360-h">نیازمند تأیید کارشناس</div>';
        a.confirmations.forEach(function (c) { h += '<div class="d360-li">' + esc(c) + '</div>'; });
      }
    }
    h += '<div class="d360-foot">پاسخ‌ها راهنمای خودکارند و جایگزین حکم رسمی دانشگاه نیستند · موتور: ' + esc(a.provider_name || 'قالبی') + '</div>';
    addHTML(h, 'd360-msg d360-bot');
  }

  function ask(q) {
    q = (q || '').trim();
    if (!q || busy) return;
    addHTML(esc(q), 'd360-msg d360-user');
    inp.value = '';
    setBusy(true);
    var t = addHTML('<span class="d360-typing"><span class="d360-dot"></span><span class="d360-dot"></span><span class="d360-dot"></span></span>', 'd360-msg d360-bot');
    var payload = JSON.stringify({ question: q, student: hostStudent(), source_page: String(location.href).slice(0, 300) });
    fetch(api('/api/v1/integration/v1/ask'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-API-Key': KEY },
      body: payload,
    }).then(function (r) {
      return r.json().then(function (j) { return { ok: r.ok, j: j }; });
    }).then(function (res) {
      t.remove();
      if (!res.ok) {
        addHTML('<div class="d360-warn">⚠ ' + esc((res.j && res.j.detail) || 'خطا در ارتباط با سامانه') + '</div>', 'd360-msg d360-bot');
      } else {
        renderAnswer(res.j.answer || {});
      }
      setBusy(false);
      inp.focus();
    }).catch(function () {
      t.remove();
      addHTML('<div class="d360-warn">⚠ ارتباط با سرور برقرار نشد.</div>', 'd360-msg d360-bot');
      setBusy(false);
    });
  }

  launcher.addEventListener('click', function () {
    panel.classList.toggle('open');
    if (panel.classList.contains('open')) { welcome(); setTimeout(function () { inp.focus(); }, 250); }
  });
  panel.querySelector('.d360-close').addEventListener('click', function () { panel.classList.remove('open'); });
  sendBtn.addEventListener('click', function () { ask(inp.value); });
  inp.addEventListener('keydown', function (e) { if (e.key === 'Enter') ask(inp.value); });
})();
"""

DEMO_HTML = r"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>صفحه آزمایشی سامانه پژوهشیار — نصب ویجت دستیار</title>
<style>
  * { box-sizing: border-box; font-family: 'Vazirmatn', 'Segoe UI', Tahoma, sans-serif; }
  body { margin: 0; background: #05070f; color: #e2e8f0; min-height: 100vh;
    background-image: radial-gradient(50rem 26rem at 85% -5%, rgba(124,58,237,.16), transparent 60%),
      radial-gradient(40rem 24rem at 0% 25%, rgba(6,182,212,.12), transparent 55%); }
  header { padding: 20px 28px; border-bottom: 1px solid rgba(255,255,255,.09);
    background: rgba(13,17,33,.8); backdrop-filter: blur(18px);
    display: flex; align-items: center; gap: 14px; }
  .logo { width: 42px; height: 42px; border-radius: 14px; display: flex; align-items: center; justify-content: center;
    background: linear-gradient(135deg,#059669,#0ea5e9); font-weight: 700; font-size: 18px; color: #fff; }
  h1 { font-size: 16px; margin: 0; } header p { margin: 2px 0 0; font-size: 11px; color: #94a3b8; }
  .badge { margin-inline-start: auto; font-size: 10px; color: #fcd34d; border: 1px solid rgba(245,158,11,.4);
    background: rgba(245,158,11,.1); border-radius: 99px; padding: 4px 12px; }
  main { max-width: 860px; margin: 0 auto; padding: 26px 20px 80px; }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 14px; margin-top: 18px; }
  .card { background: rgba(255,255,255,.045); border: 1px solid rgba(255,255,255,.1); border-radius: 18px;
    padding: 16px; backdrop-filter: blur(16px); }
  .card h3 { margin: 0 0 6px; font-size: 13.5px; color: #c4b5fd; }
  .card p { margin: 0; font-size: 11.5px; color: #94a3b8; line-height: 1.9; }
  .note { margin-top: 26px; background: rgba(124,58,237,.08); border: 1px solid rgba(139,92,246,.3);
    border-radius: 16px; padding: 14px 18px; font-size: 12.5px; line-height: 2; color: #cbd5e1; }
  code { background: rgba(255,255,255,.07); border-radius: 6px; padding: 1px 7px; font-size: 11px; direction: ltr; display: inline-block; }
</style>
</head>
<body>
<header>
  <div class="logo">پ</div>
  <div>
    <h1>سامانه پژوهشیار (صفحه آزمایشی)</h1>
    <p>نمونه‌ای از یک سامانه دیگر که چت‌بات دستیار آیین‌نامه‌ای در آن نصب شده است — غیررسمی</p>
  </div>
  <span class="badge">نمونه و غیررسمی</span>
</header>
<main>
  <div class="grid">
    <div class="card"><h3>پروپوزال پژوهشی</h3><p>دو پیش‌نویس در حال بررسی، یک مورد نیازمند اصلاح بودجه.</p></div>
    <div class="card"><h3>مقالات در انتظار داوری</h3><p>سه مقاله ارسالی در جریان داوری همتا.</p></div>
    <div class="card"><h3>طرح‌های پژوهشی دانشجویی</h3><p>پنج طرح فعال، دو طرح در مرحله تصویب.</p></div>
    <div class="card"><h3>کارورزی و ارتباط با آموزش</h3><p>سؤال آیین‌نامه‌ای دارید؟ از چت‌بات گوشه صفحه استفاده کنید.</p></div>
  </div>
  <div class="note">
    💬 <b>آزمایش چت‌بات:</b> روی دکمه شناور گوشه صفحه کلیک کنید. این ویجت دقیقاً همان چیزی است که
    سامانه‌های دیگر با افزودن تگ <code>&lt;script src=".../api/v1/integration/widget.js" data-key="..."&gt;</code>
    به صفحات خود نصب می‌کنند؛ پاسخ‌ها از سرویس <code>POST /api/v1/integration/v1/ask</code> با کلید همین سامانه
    و همراه با استناد به اسناد (نمونه و غیررسمی) دریافت می‌شود.
  </div>
</main>
<script src="/api/v1/integration/widget.js" data-key="__KEY__" data-title="دستیار آیین‌نامه‌ای در پژوهشیار" data-position="left"></script>
</body>
</html>"""
