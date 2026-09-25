/* ═══════════════════════════════════════════════════════════════
   富兰克林写作 — 前端

   流程：书架 → 打开书 → 读原文 → 搁几分钟 → 看逐句提示写（原文不在）
        → 交稿 → 一句一句对着看

   富兰克林的原话是 "made short hints of the sentiment of each sentence"：
   先把每句话的要旨记成短提示，搁几天，再看着这些提示把整篇写回来。
   所以这里提示的单位是**句子**，一句原文配一条提示。
   ═══════════════════════════════════════════════════════════════ */
'use strict';

/* ───────────────── 基础 ───────────────── */

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));

const esc = (s) => String(s == null ? '' : s)
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
const escNL = (s) => esc(s).replace(/\n/g, '<br>');
const plainLen = (s) => String(s || '')
  .replace(/[，。！？；：、“”"'（）《》…—\s]/g, '').length;

function fmtClock(sec) {
  sec = Math.max(0, Math.round(sec));
  return String(Math.floor(sec / 60)).padStart(2, '0') + ':' +
         String(sec % 60).padStart(2, '0');
}
function fmtDur(sec) {
  if (!sec) return '—';
  sec = Math.max(0, Math.round(sec));
  const m = Math.floor(sec / 60);
  return m ? `${m} 分 ${sec % 60} 秒` : `${sec} 秒`;
}
function fmtWhen(s) { return s ? s.slice(5, 16) : '—'; }

async function api(path, opts = {}) {
  const url = new URL('/api/' + path, location.href).href;
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    method: opts.method || (opts.body ? 'POST' : 'GET'),
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  let data = null;
  try { data = await res.json(); } catch (e) { /* 文件下载 */ }
  if (!res.ok) {
    const err = new Error((data && data.error) || `请求失败（${res.status}）`);
    err.status = res.status;
    err.hint = data && data.hint;
    throw err;
  }
  return data;
}

let toastTimer = null;
function toast(msg, warn) {
  const t = $('#toast');
  t.textContent = msg;
  t.className = 'toast on' + (warn ? ' warn' : '');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { t.className = 'toast'; }, warn ? 4200 : 2400);
}

function modal(html, mount) {
  $('#modal-box').innerHTML = html;
  $('#modal').classList.remove('hidden');
  if (mount) mount($('#modal-box'));
}
function closeModal() {
  $('#modal').classList.add('hidden');
  $('#modal-box').innerHTML = '';
}
$('#modal').addEventListener('click', (e) => { if (e.target.id === 'modal') closeModal(); });
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeModal(); });

/* ───────────────── 状态 ───────────────── */

const S = {
  shelf: null, settings: null, book: null, chapter: null, practice: null,
  timer: null, saveTimer: null, prepTimer: null, drill: null, live: null,
  anim: 1,          // 输入动效：1 淡入 / 2 升起 / 3 书写 / 4 关
};

function stopTimers() { clearInterval(S.timer); S.timer = null; clearTimeout(S.prepTimer); }

/* 输入动效的档位。**必须声明在 setAnim 之前**——放到文件后面会踩暂时性死区：
   setAnim 里那句 FONTS_ANIM.includes(...) 会抛异常，于是档位永远换不了、也关不掉，
   而且界面上一点提示都没有。这个 bug 真发过一次，所以这里写死一条规矩：
   凡是 setAnim 用到的常量，都在它上面。 */
const ANIM_NAME = { 1: '淡入', 2: '升起', 3: '书写', 4: '关' };
const FONTS_ANIM = [1, 2, 3, 4];

/** 输入动效的四个档位：淡入 / 升起 / 书写 / 关。选择存在本地。 */
function bindAnimPick() {
  const btns = $$('[data-anim]');
  btns.forEach((b) => {
    b.onclick = () => setAnim(parseInt(b.dataset.anim, 10));
  });
}

/** 换一个动效档位。
 *
 *  这里同时做三件事：改状态、改 localStorage、改所有按钮上的高亮标记。
 *  高亮加在**每个按钮自己**身上，不依赖重绘——所以点下去立刻能看到哪个是当前档。
 *  另外立刻把 toast 打出来，这样"有没有生效"是眼睛能确认的，不用去猜。
 */
/** 动效现在开不开。
 *
 *  注意 S.anim === 4 表示**关**——它的编号是 4，不是 0。
 *  之前这里写成 !!S.anim，于是"关"这个档位算出来是 true，动效反而被打开了，
 *  现象就是"这个按钮关不掉"。所以判断"开没开"只走这一个函数，别处不许再手写。 */
function animOn() {
  return S.anim !== 4 && FONTS_ANIM.includes(S.anim);
}

function setAnim(n) {
  S.anim = FONTS_ANIM.includes(n) ? n : 1;
  try { localStorage.setItem('fk-anim', String(S.anim)); } catch (e) { /* 隐私模式 */ }
  if (S.live) S.live.enabled = animOn();
  $$('[data-anim]').forEach((x) => {
    const on = parseInt(x.dataset.anim, 10) === S.anim;
    if (x.classList) x.classList.toggle('on', on);
  });
  const cur = $('#anim-cur');
  if (cur) cur.textContent = '当前：' + (ANIM_NAME[S.anim] || '关');
  toast(animOn() ? '输入动效：' + ANIM_NAME[S.anim] : '输入动效已关');
}
function go(hash) { location.hash = hash; }

function setView(name) {
  stopTimers();
  $$('.view').forEach((v) => v.classList.toggle('on', v.id === 'view-' + name));
  $$('.navlink').forEach((t) => t.classList.toggle('on', t.dataset.view === name));
  const wide = (name === 'practice' || name === 'read');
  $('#nav').style.display = wide ? 'none' : 'flex';
  document.body.classList.remove('booting');
  window.scrollTo({ top: 0 });
}

const STAGE = {
  unread: '未读', read: '搁着', ready: '可以写', wrote: '看对照', done: '已练完',
};

/* 功能字：只用来把一句话切成"实义串"。和服务端 fk_server.FUNC 保持一致，
   否则单句里的"你抓住了哪些词"会和整段对照对不上。 */
const FUNC = new Set((
  '的了在是我他她它们和与及或但而就不都很也还又把被从对为以之其此这那' +
  '上下来去时么呢吧啊呀吗着过要会能可所因然于并且如若则把让给向从当' +
  '一二三四五六七八九十百千万两有些个只种样条张支又再才更没'
).split(''));

/* 三种效果各自的画法。参数就是规格，测试直接对着它验——
   因为出过一次"三个按钮改的是同一个变量、画的是同一种动画"的事故。 */
const ANIM_SPEC = {
  // 淡入：先把原字盖掉，再把字放大着落下来——这一版的手感比"轻轻放大"明显得多
  1: { name: '淡入', life: 400, scale: 0.42, rise: 0.30, reveal: false, sweep: true, cover: true },
  // 升起：从下方浮上来，末尾一道底线扫过
  2: { name: '升起', life: 420, scale: 0.24, rise: 0.62, reveal: false, sweep: false, cover: false },
  // 书写：从下往上擦出来，带一道跟着走的笔尖
  3: { name: '书写', life: 460, scale: 0, rise: 0, reveal: true, sweep: true, cover: true },
};

/* ── 输入时的入场动效 ──
 *
 * 三个关键决定，都是踩过坑才定下来的：
 *
 * 一、**只对"落定的字"做动画，不管用什么输入法。**
 *     中文打字时，输入框里会先出现拼音字母或者候选词，然后才定成一个汉字。
 *     如果跟着每一次 input 事件做动画，动效就散在一堆中间状态上，看着乱、也不明显。
 *     所以这里等 compositionend 和 beforeinput 的 insertText —— 那是"字真的上屏了"。
 *
 * 二、**动画的就是输入框里那一个字本身**，不是另画一个影子。
 *     做法：先把那一个字盖住（用纸色画一小块），再把它放大着落下来。
 *     读者看到的是"这个字刚刚被写上去"，而不是旁边多冒出来一个字。
 *
 * 三、**不碰 textarea 里的文字。** canvas 盖在上面，字号字体从输入框上量。
 *     给每个字包一个元素会毁掉中文输入法、选区和撤销，而且写到一千字就卡。
 */
function attachLive(ta, canvas) {
  if (S.live) { S.live.stop(); S.live = null; }
  if (!canvas || !canvas.getContext) return null;
  const ctx = canvas.getContext('2d');
  const parts = [];
  const MAX = 60;
  let raf = null, last = performance.now(), composing = false, pending = false;
  let probe = null;              // 测试用：观察每个入场字符

  const dt = getComputedStyle(document.documentElement);
  const colorOf = (name, fallback) => (dt.getPropertyValue(name) || fallback).trim();

  let M = null;           // 从输入框上量来的排版参数
  function measure() {
    const cs = getComputedStyle(ta);
    M = {
      pl: parseFloat(cs.paddingLeft) || 0,
      pt: parseFloat(cs.paddingTop) || 0,
      bl: parseFloat(cs.borderLeftWidth) || 0,
      bt: parseFloat(cs.borderTopWidth) || 0,
      pr: parseFloat(cs.paddingRight) || 0,
      family: cs.fontFamily, size: parseFloat(cs.fontSize) || 17,
      lh: parseFloat(cs.lineHeight) || parseFloat(cs.fontSize) * 2 || 34,
      ink: colorOf('--ink', '#262119'),
      accent: colorOf('--accent', '#1f5548'),
      // 盖住原字用的纸色。取不到就退回一个接近底色值，宁可盖得略有色差，
      // 也不能算出 NaN——NaN 传进 canvas 是静默丢弃。
      paper: colorOf('--paper', '') || '#f4f0e8',
    };
  }

  let dpr = 1;
  function fit() {
    measure();
    const r = ta.getBoundingClientRect();
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.max(1, Math.round(r.width * dpr));
    canvas.height = Math.max(1, Math.round(r.height * dpr));
    canvas.style.width = r.width + 'px';
    canvas.style.height = r.height + 'px';
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  /** 量一个字符在输入框里的坐标：镜像一个同款排版的隐藏 div，插标记量它。
   *  断行、缩进、标点挤压都交给浏览器，不自己算。 */
  let mirror = null, marker = null;
  function ensureMirror() {
    if (mirror) return;
    mirror = document.createElement('div');
    Object.assign(mirror.style, {
      position: 'absolute', left: '-99999px', top: '0', visibility: 'hidden',
      pointerEvents: 'none', boxSizing: 'content-box', width: '0px',
      fontFamily: M.family, fontSize: M.size + 'px', lineHeight: M.lh + 'px',
      letterSpacing: getComputedStyle(ta).letterSpacing || 'normal',
      wordBreak: 'break-word', whiteSpace: 'pre-wrap',
      textAlign: getComputedStyle(ta).textAlign || 'left',
    });
    marker = document.createElement('span');
    marker.textContent = '\u200b';
    document.body.appendChild(mirror);
  }

  function posOf(index) {
    ensureMirror();
    const r = ta.getBoundingClientRect();
    mirror.style.width = Math.max(1, r.width - M.pl - M.pr - M.bl - M.bt) + 'px';
    mirror.textContent = '';
    mirror.appendChild(document.createTextNode(ta.value.slice(0, index)));
    mirror.appendChild(marker);
    // 坐标必须是有限数字。任何一项是 undefined（比如某些环境下没给 scrollLeft），
    // NaN 传进 canvas 会被静默丢掉——画不出来还不报错，最难查。
    const sl = Number(ta.scrollLeft) || 0;
    const st = Number(ta.scrollTop) || 0;
    const ox = Number(marker.offsetLeft) || 0;
    const oy = Number(marker.offsetTop) || 0;
    const x = M.pl + ox - sl;
    const y = M.pt + oy - st + M.lh * 0.78;
    if (!Number.isFinite(x) || !Number.isFinite(y)) return null;
    return { x, y };
  }

  function spawn(ch, index, delay) {
    if (parts.length >= MAX) parts.shift();
    const p = posOf(index);
    if (!p) return;
    parts.push({
      ch, x: p.x, y: p.y, t: -(delay || 0),
      size: M.size, lh: M.lh, family: M.family,
      color: M.ink, kind: S.anim,
      // 每八个字里有一个用强调色，看起来像笔尖换了墨
      accent: (index % 8 === 3),
    });
    if (probe) probe(parts[parts.length - 1]);
    kick();
  }

  function kick() {
    // 用**显式的标志**判断有没有排帧，而不是看 raf 那个 id。
    // raf 的返回值是不是"还在等"并不确定：某些环境下回调同步执行完，
    // raf 仍是个真值，于是下一次 kick 会以为已经有帧在等而不排新的——
    // 表现就是"有时候打字完全没动画"，最难查的一类 bug。
    if (pending) return;
    pending = true;
    last = performance.now();
    raf = requestAnimationFrame(draw);
  }

  /* 三种效果按 ANIM_SPEC 各画各的 */

  function draw(now) {
    pending = false;
    const t = now || performance.now();
    const step = Math.min(40, t - last);
    last = t;
    const w = canvas.width / dpr, h = canvas.height / dpr;
    ctx.clearRect(0, 0, w, h);

    for (let i = parts.length - 1; i >= 0; i--) {
      const p = parts[i];
      p.t += step;
      if (p.t < 0) continue;                       // 还没轮到它
      const spec = ANIM_SPEC[p.kind] || ANIM_SPEC[1];
      const k = p.t / spec.life;
      if (k >= 1) { parts.splice(i, 1); continue; }

      // 前段快速落定、后段极短收尾：这一版的手感比线性淡入明显
      const e = k < 0.45 ? Math.pow(k / 0.45, 0.62) : 1;
      const fade = k < 0.7 ? 1 : 1 - (k - 0.7) / 0.3;
      const color = p.accent ? M.accent : p.color;

      ctx.save();
      // 先把底下的原字盖掉——动画才有"这个字是刚写上去的"感觉
      if (spec.cover) {
        ctx.globalAlpha = 1;
        ctx.fillStyle = M.paper;
        ctx.fillRect(p.x - 2, p.y - p.lh * 0.82, p.size * 1.4, p.lh * 0.94);
      }
      ctx.globalAlpha = Math.max(0, Math.min(1, fade));
      ctx.fillStyle = color;
      ctx.font = `${p.size}px ${p.family}`;
      ctx.textBaseline = 'alphabetic';

      if (spec.reveal) {
        // 书写：从下往上擦出来
        ctx.beginPath();
        const rv = e * (p.lh * 1.05);
        ctx.rect(p.x - 2, p.y - rv, p.size * 1.3, rv + 3);
        ctx.clip();
        ctx.fillText(p.ch, p.x, p.y);
        ctx.restore();
        if (spec.sweep) {
          ctx.save();
          ctx.globalAlpha = Math.max(0, Math.min(0.5, (1 - k) * 1.1));
          ctx.fillStyle = color;
          ctx.fillRect(p.x - 1, p.y - rv, p.size * 0.9, 1.4);
        }
      } else {
        ctx.translate(p.x, p.y);
        const sc = 1 + (1 - e) * spec.scale;
        ctx.scale(sc, sc);
        ctx.fillText(p.ch, 0, -(1 - e) * p.lh * spec.rise);
        ctx.restore();
        if (spec.sweep) {
          ctx.save();
          ctx.globalAlpha = Math.max(0, Math.min(0.5, (1 - k) * 1.3));
          ctx.fillStyle = color;
          ctx.fillRect(p.x, p.y + 2, p.size * Math.min(1, e * 1.3), 1.6);
        }
      }
      ctx.restore();
    }
    if (parts.length) { pending = true; raf = requestAnimationFrame(draw); }
    else { pending = false; raf = null; ctx.clearRect(0, 0, w, h); }
  }  /** 把 [from, to) 这段新上屏的字逐个做动画。 */
  function animateRange(from, to, stagger) {
    const text = ta.value;
    let n = 0;
    const BLOCK = 40;              // 一次最多让这么多个字落下来
    for (let i = from; i < to && n < BLOCK; i++) {
      const ch = text[i];
      if (ch === '\n' || ch === undefined) continue;
      spawn(ch, i, n * (stagger == null ? 26 : stagger));
      n++;
    }
  }

  // ① 输入法：定字的那一刻才知道"上了哪几个字"
  const onCompStart = () => { composing = true; };
  const onCompEnd = (e) => {
    composing = false;
    if (!live.enabled) return;
    const data = (e && e.data) || '';
    const caret = num(ta.selectionStart, ta.value.length);
    if (data) animateRange(Math.max(0, caret - data.length), caret, 34);
    else if (caret > 0) animateRange(caret - 1, caret, 0);
  };

  // ② 直接输入和粘贴：值已经落地了，比对"改之前"和"现在"就知道插了什么。
  //
  //    为什么不用 beforeinput：那时候字还没进输入框，量不到坐标，
  //    得先把值推测出来再等一拍——多一层时序，还容易和输入法打架。
  //    比对法没有这个窗口期：算出来的区间一定对得上屏幕上的字。
  let prevValue = ta.value;
  const onInput = () => {
    const now = ta.value;
    const old = prevValue;
    prevValue = now;
    if (!live.enabled || composing) return;

    // 从两端往中间收，剩下的就是被替换掉的那一段
    let s = 0;
    const maxS = Math.min(old.length, now.length);
    while (s < maxS && old[s] === now[s]) s++;
    let e = 0;
    while (e < maxS - s && old[old.length - 1 - e] === now[now.length - 1 - e]) e++;
    const from = s;
    const to = now.length - e;
    const added = to - from;
    if (added <= 0) return;                       // 删除、或者只是移动光标

    // 短输入逐字落下来；一次贴一大段就让它成块落下，别排到下个世纪
    animateRange(from, to, added > 4 ? 14 : 28);
  };

  fit();
  ta.addEventListener('compositionstart', onCompStart);
  ta.addEventListener('compositionend', onCompEnd);
  ta.addEventListener('input', onInput);
  window.addEventListener('resize', fit);
  ta.addEventListener('scroll', () => { parts.length = 0; });

  const live = {
    enabled: animOn(),
    // 仅供测试观察：当前正在飞的字符
    get pending() { return parts.length; },
    get rafPending() { return pending; },
    // 测试用：每个入场字符生成时回调一次，用来确认"不同档位真的画得不一样"
    set probe(fn) { probe = fn; },
    stop() {
      ta.removeEventListener('compositionstart', onCompStart);
      ta.removeEventListener('compositionend', onCompEnd);
      ta.removeEventListener('input', onInput);
      window.removeEventListener('resize', fit);
      if (raf != null) cancelAnimationFrame(raf);
      raf = null; pending = false;
      parts.length = 0;
      if (mirror && mirror.parentNode) mirror.parentNode.removeChild(mirror);
      mirror = null; marker = null;
      try { ctx.clearRect(0, 0, canvas.width, canvas.height); } catch (e) { /* 忽略 */ }
    },
  };
  S.live = live;
  return live;
}

/** 拿一个一定是数字的值。undefined/NaN 会一路传到 canvas 上被静默丢掉。 */
function num(v, fallback) {
  const n = Number(v);
  return Number.isFinite(n) ? n : fallback;
}

/* ───────────────── 书架 ───────────────── */

async function loadShelf() {
  const [sh, st] = await Promise.all([api('shelf'), api('settings')]);
  S.shelf = sh; S.settings = st;
  setView('shelf');
  $('#shelf-lead').textContent = shelfLead(sh);
  const box = $('#shelf');
  box.outerHTML = shelfHTML(sh, box.id);
  $('#btn-add').onclick = openImport;
  bindShelf();
}

function shelfLead(sh) {
  if (!sh.counts.passages) return '书架是空的。导入一本书，或者把一段文章粘进来。';
  let s = `${sh.counts.books} 本，${sh.counts.passages} 段可练，练完 ${sh.counts.done} 段。`;
  if (sh.counts.written > sh.counts.done) {
    s += `另有 ${sh.counts.written - sh.counts.done} 段写完没看对照。`;
  }
  if (!sh.settings.has_key) s += '提示需要先在「设置」里填一个 API Key；不填也能练。';
  return s;
}

/** 纯函数：书架。不碰 DOM，测试里直接跑。 */
function shelfHTML(sh, boxId) {
  const id = boxId || 'shelf';
  if (!sh.books.length) {
    return `<div id="${id}"><div class="blank">
      <h2>先放一本书进来</h2>
      <p>整本的 txt 可以，在网页上读到的一段好文章也可以——复制粘贴进来就行。</p>
      <p class="muted small">导入后会自动切成节和段。练的时候一段一段来：
        读完原文，搁几分钟，看着每句话的提示把它写回来，再一句一句对着看。</p>
      <button class="btn" id="btn-add2">导入第一本</button>
    </div></div>`;
  }
  const rows = sh.books.map((b) => {
    const c = b.counts;
    const pct = c.total ? Math.round((c.done / c.total) * 100) : 0;
    return `<div class="book" data-id="${esc(b.id)}">
      <button class="book-del" data-del="${esc(b.id)}" title="从书架移除">移除</button>
      <div class="book-title">${esc(b.title)}</div>
      <div class="book-author">${esc(b.author)}</div>
      <div class="book-stats">${b.chars} 字　${b.chapters} 节<br>练完 ${c.done} / ${c.total} 段${
        c.wrote ? `　待看 ${c.wrote}` : ''}</div>
      <div class="book-bar"><i style="width:${pct}%"></i></div>
    </div>`;
  }).join('');
  return `<div id="${id}" class="shelf">${rows}</div>`;
}

function bindShelf() {
  $$('.book').forEach((b) => {
    b.onclick = (e) => {
      if (e.target.dataset.del) return;
      go('#/book/' + b.dataset.id);
    };
  });
  $$('[data-del]').forEach((btn) => {
    btn.onclick = (e) => { e.stopPropagation(); askDelete(btn.dataset.del); };
  });
  const b2 = $('#btn-add2');
  if (b2) b2.onclick = openImport;
}

function askDelete(bookId) {
  const b = S.shelf.books.find((x) => x.id === bookId);
  if (!b) return;
  modal(`<h3>把《${esc(b.title)}》拿走？</h3>
    <p class="muted">原文、写过的稿子、那些观察，会一起删掉，找不回来。</p>
    <p class="muted small">只是想清理的话，先去「记录」把想留的那几轮导出。</p>
    <div class="row"><button class="btn-quiet" id="no">算了</button>
      <span class="right"></span>
      <button class="btn-warn" id="yes">删除</button></div>`, (box) => {
    $('#no', box).onclick = closeModal;
    $('#yes', box).onclick = async () => {
      try {
        await api(`books/${encodeURIComponent(bookId)}?confirm=${encodeURIComponent(bookId)}`,
          { method: 'DELETE' });
        closeModal();
        toast('已移除。');
        go('#/shelf');
        loadShelf();
      } catch (e) { toast(e.message, true); }
    };
  });
}

function openImport() {
  modal(`<h3>导入</h3>
    <p class="muted small">整本 txt 最好；也可以直接粘一段。
      导入后按段落切节，每节再切成约 300 字的练习段。</p>
    <div class="field"><label>书名</label>
      <input id="f-title" placeholder="留空就用文件名或第一句"></div>
    <div class="cols">
      <div class="field"><label>作者</label><input id="f-author" placeholder="可留空"></div>
      <div class="field"><label>每段大约多少字</label>
        <select id="f-size">
          <option value="150">150 字</option>
          <option value="300" selected>300 字</option>
          <option value="500">500 字</option>
        </select></div>
    </div>
    <div class="field"><label>本地文件路径</label>
      <input id="f-file" placeholder="D:\\书\\某本书.txt"></div>
    <div class="field"><label>或者粘贴原文</label>
      <textarea id="f-text" placeholder="把文章粘在这里"></textarea>
      <div class="hint" id="f-count">0 字</div></div>
    <div class="row"><button class="btn-quiet" id="no">取消</button>
      <span class="right"></span><button class="btn" id="yes">导入</button></div>`,
    (box) => {
      const ta = $('#f-text', box);
      ta.addEventListener('input', () => {
        $('#f-count', box).textContent = plainLen(ta.value) + ' 字';
      });
      ta.focus();
      $('#no', box).onclick = closeModal;
      $('#yes', box).onclick = async (e) => {
        const btn = e.target;
        btn.disabled = true;
        btn.innerHTML = '<span class="spin"></span> 切分中';
        try {
          const r = await api('books', { body: {
            title: $('#f-title', box).value.trim(),
            author: $('#f-author', box).value.trim(),
            passage_chars: parseInt($('#f-size', box).value, 10),
            file: $('#f-file', box).value.trim(),
            text: ta.value,
          } });
          closeModal();
          const n = r.book.counts.total;
          toast(`《${r.book.title}》上架，${r.book.chapters.length} 节 ${n} 段。`);
          await loadShelf();
          go('#/book/' + r.book.id);
        } catch (err) {
          toast(err.message, true);
          btn.disabled = false;
          btn.textContent = '导入';
        }
      };
    });
}

/* ───────────────── 书内目录 ───────────────── */

async function loadBook(id) {
  S.book = await api('books/' + encodeURIComponent(id));
  setView('book');
  $('#brand-sub').textContent = S.book.title;
  $('#book').innerHTML = bookHTML(S.book);
  const b = S.book;
  $('#b-read').onclick = () => go(`#/read/${b.id}/1`);
  $('#b-next').onclick = () => {
    const t = nextTarget(b);
    if (t) go(`#/practice/${b.id}/${t.ch}/${t.p}`);
    else toast('这本书每一段都练完了。');
  };
  $$('.toc-row').forEach((el) => {
    el.onclick = () => go(`#/read/${b.id}/${el.dataset.ch}`);
  });
  loadPrep(b.id);
  loadNotes(b.id);
}

/** 这本书的全部笔记。逐句的和整段的都在这里，只有一个入口。 */
async function loadNotes(bookId) {
  const slot = $('#notes-slot');
  if (!slot) return;
  let r;
  try { r = await api(`books/${encodeURIComponent(bookId)}/notes`); }
  catch (e) { slot.innerHTML = ''; return; }
  if (!S.book || S.book.id !== bookId) return;

  const sentCount = r.notes.filter((n) => n.scope === 'sentence').length;
  const passCount = r.notes.length - sentCount;

  if (!r.count) {
    slot.innerHTML = `<div class="notes-block collapsed" id="notes-block">
      <div class="notes-head" id="notes-toggle">
        <h2>这本书的笔记</h2>
        <span class="muted small">还没有。单句练完对照、或者整段写完对照，都能往里记一条。</span>
      </div>
    </div>`;
    return;
  }
  slot.innerHTML = `<div class="notes-block" id="notes-block">
    <div class="notes-head" id="notes-toggle">
      <h2>这本书的笔记</h2>
      <span class="muted small">${r.count} 条（逐句 ${sentCount}　整段 ${passCount}）
        　按时间倒序　点这里收起</span>
      <span class="right"></span>
      <button class="btn-quiet" id="notes-export">导出全部笔记</button>
    </div>
    <div class="notes-body">
      ${r.notes.map((n) => `
        <div class="note-card" data-note="${esc(n.id)}">
          <div class="note-meta">
            <span class="tag ${n.scope === 'passage' ? 'wide' : ''}">${
              n.scope === 'passage' ? '整段' : '第 ' + n.sent_no + ' 句'}</span>
            <span>第 ${n.chapter} 节第 ${n.passage} 段</span>
            <span class="when">${esc(fmtStamp(n.at))}</span>
            <span class="right"></span>
            <button class="linkbtn" data-del-note="${esc(n.id)}">删掉</button>
          </div>
          ${n.hint ? `<div class="note-hint">提示：${esc(n.hint)}</div>` : ''}
          ${n.sentence ? `<div class="note-pair">
            <div><span class="lbl">原文</span><span class="ptext">${esc(n.sentence)}</span></div>
            ${n.mine ? `<div><span class="lbl">你写的</span><span class="ptext mine">${
              highlight(n.mine, factSheetLocal(n.sentence, n.mine).hit)}</span></div>` : ''}
          </div>` : ''}
          <div class="note-text">${escNL(n.text)}</div>
        </div>`).join('')}
    </div>
  </div>`;

  const head = $('#notes-toggle');
  head.onclick = () => $('#notes-block').classList.toggle('collapsed');
  $('#notes-export').onclick = () => exportNotes(r);
  $$('[data-del-note]').forEach((btn) => {
    btn.onclick = async (e) => {
      e.stopPropagation();
      const id = btn.dataset.delNote;
      if (String(id).startsWith('obs-')) {
        toast('这条是旧存档里的观察，暂时不能在界面上删。', true);
        return;
      }
      try {
        await api(`books/${encodeURIComponent(bookId)}/notes/${encodeURIComponent(id)}`,
          { method: 'DELETE' });
        toast('删掉了。');
        loadNotes(bookId);
      } catch (err) { toast(err.message, true); }
    };
  });
}

function fmtStamp(ts) {
  if (!ts) return '';
  try {
    return new Date(ts * 1000).toISOString().slice(5, 16).replace('T', ' ');
  } catch (e) { return ''; }
}

function exportNotes(r) {
  const lines = [`# ${r.book.title}　练习笔记`, '',
    `共 ${r.count} 条。逐句的和整段的都在这里。`, ''];
  r.notes.slice().reverse().forEach((n) => {
    const where = n.scope === 'passage' ? '整段' : `第 ${n.sent_no} 句`;
    lines.push(`## 第 ${n.chapter} 节第 ${n.passage} 段　${where}　${fmtStamp(n.at)}`);
    if (n.hint) lines.push('', `提示：${n.hint}`);
    if (n.sentence) lines.push('', `原文：${n.sentence}`);
    if (n.mine) lines.push('', `我写的：${n.mine}`);
    lines.push('', n.text, '');
  });
  const blob = new Blob([lines.join('\n')], { type: 'text/markdown;charset=utf-8' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `${r.book.title} 笔记.md`;
  a.click();
  URL.revokeObjectURL(a.href);
}

function bookHTML(b) {
  const c = b.counts;
  return `
    <div class="book-title-block">
      <h1>${esc(b.title)}</h1>
      ${b.author ? `<div class="by">${esc(b.author)}</div>` : ''}
      <div class="facts">
        <span><b>${b.chars}</b> 字</span>
        <span><b>${b.chapters.length}</b> 节</span>
        <span><b>${c.total}</b> 段</span>
        <span>练完 <b>${c.done}</b></span>
        ${c.wrote ? `<span>待看 <b>${c.wrote}</b></span>` : ''}
        ${c.reading ? `<span>搁着 <b>${c.reading}</b></span>` : ''}
      </div>
      <div class="book-btns">
        <button class="btn" id="b-read">从第一节开始读</button>
        <button class="btn-quiet" id="b-next">${esc(nextLabel(b))}</button>
      </div>
      <div id="prepare-slot"></div>
    </div>
    <div id="notes-slot"></div>
    ${b.chapters.map((ch) => `
      <div class="toc-section">
        <div class="toc-head">
          <h2>${esc(ch.title)}</h2>
          <span class="meta">第 ${ch.no} 节　${ch.chars} 字　${ch.passages.length} 段</span>
        </div>
        <div class="toc">
          ${ch.passages.map((p) => `
            <button class="toc-row" data-ch="${ch.no}" data-p="${p.no}">
              <span class="no">${String(p.no).padStart(2, '0')}</span>
              <span class="len">${p.chars} 字</span>
              <span class="state ${p.stage}">${STAGE[p.stage] || p.stage}</span>
              <span class="right">${p.stage === 'read' && p.remaining
                ? '还要等 ' + fmtClock(p.remaining)
                : (p.draft_chars ? p.draft_chars + ' 字稿' : '')}</span>
            </button>`).join('')}
        </div>
      </div>`).join('')}`;
}

function nextLabel(b) {
  const t = nextTarget(b);
  return t ? `继续第 ${t.ch} 节第 ${t.p} 段` : '已全部练完';
}

function nextTarget(b) {
  for (const want of ['wrote', 'ready', 'unread']) {
    for (const ch of b.chapters) {
      for (const p of ch.passages) if (p.stage === want) return { ch: ch.no, p: p.no };
    }
  }
  return null;
}

/* ── 提示的批量准备 ── */

async function loadPrep(bookId) {
  const slot = $('#prepare-slot');
  if (!slot) return;
  let plan;
  try { plan = await api(`books/${encodeURIComponent(bookId)}/summaries/plan`); }
  catch (e) { slot.innerHTML = ''; return; }
  if (!S.book || S.book.id !== bookId) return;

  const pct = plan.total ? Math.round((plan.cached / plan.total) * 100) : 0;
  const job = plan.job;
  const running = job && job.state === 'running';

  slot.innerHTML = `<div class="hints-prep">
    <div class="row">
      <span>逐句提示</span>
      <span class="muted">${plan.cached} / ${plan.total} 段已备好${
        plan.todo ? `，还差 ${plan.todo} 段` : '，全部就绪'}</span>
      <span class="right"></span>
      ${running
        ? '<button class="btn-quiet" id="prep-cancel">停下</button>'
        : (plan.ready
            ? (plan.todo ? '<button class="btn-quiet" id="prep-go">提前备好</button>'
                         : '<button class="btn-quiet" id="prep-refresh">刷新</button>')
            : '<button class="btn-quiet" id="prep-set">去设置</button>')}
    </div>
    <div class="hints-bar"><i style="width:${pct}%"></i></div>
    <div class="muted small">${
      running
        ? `正在生成 ${job.finished} / ${plan.total}　成功 ${job.done}${
            job.failed ? `　失败 ${job.failed}` : ''}`
        : (plan.ready
            ? (plan.todo
                ? `提前备好之后，练的时候不用等模型。这次大约 ${plan.est_tokens.toLocaleString()} token（估算）。`
                : '不用再花 token 了。')
            : '还没配置模型。填一个 Key 就能给每句话生成提示。')}</div>
    ${job && job.last_error ? `<div class="small bad" style="margin-top:8px">${
      esc(job.last_error)}</div>` : ''}
    ${!running && plan.ready && plan.todo ? `<div class="muted small"
      style="margin-top:6px">同一段文字只生成一次；换模型或改提示词才会重做。</div>` : ''}
  </div>`;

  const goBtn = $('#prep-go');
  if (goBtn) {
    goBtn.onclick = () => {
      if (plan.est_tokens > 4000) {
        modal(`<h3>提前备好</h3>
          <p class="muted">还有 ${plan.todo} 段没有提示，大约 ${plan.est_tokens.toLocaleString()}
            token（估算）。已经在缓存里的 ${plan.cached} 段不会重复花钱。</p>
          <p class="muted small">估算只是给你个大概，真实用量以服务商账单为准，
            生成后记在设置页。</p>
          <div class="row"><button class="btn-quiet" id="no">算了</button>
          <span class="right"></span><button class="btn" id="yes">开始</button></div>`,
          (box) => {
            $('#no', box).onclick = closeModal;
            $('#yes', box).onclick = () => { closeModal(); startPrep(bookId); };
          });
      } else startPrep(bookId);
    };
  }
  const setBtn = $('#prep-set');
  if (setBtn) setBtn.onclick = () => go('#/settings');
  const rf = $('#prep-refresh');
  if (rf) rf.onclick = () => loadPrep(bookId);
  const cc = $('#prep-cancel');
  if (cc) {
    cc.onclick = async () => {
      await api(`books/${encodeURIComponent(bookId)}/summaries/cancel`, { body: {} });
      toast('已请求停下。正在跑的那几条会做完。');
      loadPrep(bookId);
    };
  }
  if (running) S.prepTimer = setTimeout(() => loadPrep(bookId), 1200);
}

async function startPrep(bookId) {
  try {
    await api(`books/${encodeURIComponent(bookId)}/summaries/warm`, { body: {} });
    toast('开始在后台生成，你可以先去读。');
    loadPrep(bookId);
  } catch (e) {
    toast(e.message + (e.hint ? '　' + e.hint : ''), true);
  }
}

/* ───────────────── 读书 ───────────────── */

async function loadRead(bookId, chapterNo) {
  const c = await api(`books/${encodeURIComponent(bookId)}/chapters/${chapterNo}`);
  S.chapter = c;
  setView('read');
  $('#brand-sub').textContent = c.book.title;
  $('#read-title').textContent = `${c.book.title}　第 ${c.chapter.no} 节`;
  const key = `fk-read-${c.book.id}-${c.chapter.no}`;
  const t0 = parseInt(sessionStorage.getItem(key) || '0', 10) || Date.now();
  sessionStorage.setItem(key, String(t0));
  $('#reader').innerHTML = readerHTML(c);

  $('#read-back').onclick = () => go('#/book/' + c.book.id);
  $('#read-prev').onclick = () => {
    if (c.chapter.no > 1) go(`#/read/${c.book.id}/${c.chapter.no - 1}`);
    else toast('已经是第一节。');
  };
  $('#read-next').onclick = () => {
    if (c.chapter.no < c.chapter.total) go(`#/read/${c.book.id}/${c.chapter.no + 1}`);
    else toast('已经是最后一节。');
  };
  const secs = () => Math.round((Date.now() - t0) / 1000);
  $('#r-done').onclick = () => go(`#/practice/${c.book.id}/${c.chapter.no}/1?read=${secs()}`);
  $$('[data-p]').forEach((el) => {
    el.onclick = () => go(`#/practice/${c.book.id}/${c.chapter.no}/${el.dataset.p}?read=${secs()}`);
  });
}

/** 纯函数：读书页。整节原文都在这里——这是唯一能看到原文的地方。 */
function readerHTML(c) {
  return `<div class="reader">
    <h1>${esc(c.chapter.title)}</h1>
    <div class="sub">第 ${c.chapter.no} 节 / 共 ${c.chapter.total} 节　${c.chapter.chars} 字　${c.passages.length} 段</div>
    <div class="reader-body">${escNL(c.text)}</div>
    <div class="reader-foot">
      <span class="note">读完就合上。搁几分钟再回来写——刚读完就写，
        写出来的是眼睛里的字，不是记住的字。</span>
      <span class="right"></span>
      <button class="btn" id="r-done">读完了，去写第 1 段</button>
    </div>
  </div>
  <div class="reader" style="padding-top:0">
    <div class="toc">
      ${c.passages.map((p) => `
        <button class="toc-row" data-p="${p.no}">
          <span class="no">${String(p.no).padStart(2, '0')}</span>
          <span class="len">${p.chars} 字</span>
          <span class="right" style="margin-left:auto">写这一段</span>
        </button>`).join('')}
    </div>
  </div>`;
}

/* ───────────────── 练习台 ───────────────── */

async function openPractice(bookId, chNo, pNo, readSeconds) {
  setView('practice');
  $('#practice').innerHTML = '<div class="loading"><span class="spin"></span> 准备中</div>';
  try {
    await api(`practice/${encodeURIComponent(bookId)}/${chNo}/${pNo}/start`,
      { body: { read_seconds: readSeconds || 0 } });
    await renderPractice(bookId, chNo, pNo, true);
  } catch (e) {
    $('#practice').innerHTML = errorBlock(e);
  }
}

function errorBlock(e) {
  return `<div class="cmp"><div class="block">
    <h2>打不开这一段</h2>
    <p class="muted">${esc(e.message)}</p>
    ${e.hint ? `<p class="muted small">${esc(e.hint)}</p>` : ''}
    <div class="row"><button class="btn-quiet" onclick="location.hash='#/shelf'">回书架</button></div>
  </div></div>`;
}

async function renderPractice(bookId, chNo, pNo, autoHint) {
  stopTimers();
  $('#prac-back').onclick = () => go(`#/book/${bookId}`);
  let d;
  try {
    d = await api(`practice/${encodeURIComponent(bookId)}/${chNo}/${pNo}/write`);
  } catch (e) {
    $('#practice').innerHTML = errorBlock(e);
    return;
  }
  S.practice = d;
  $('#prac-title').textContent =
    `${d.book.title}　第 ${d.chapter.no} 节　第 ${d.passage.no} 段`;
  $('#prac-meta').textContent = `${d.passage.chars} 字　${d.passage.sentences} 句`;

  if (d.source) { renderCompare(d); return; }
  if (d.remaining > 0) { renderWait(d, bookId, chNo, pNo); return; }
  renderDesk(d, bookId, chNo, pNo, autoHint);
}

/* ── 等待 ── */

function renderWait(d, bookId, chNo, pNo) {
  const total = Math.max(1, (d.delay_min || 3) * 60);
  let left = d.remaining;
  $('#practice').innerHTML = `<div class="wait">
    <div class="kicker">原文已合上</div>
    <div class="big" id="cd">${fmtClock(left)}</div>
    <div class="rule"><i id="bar" style="width:0%"></i></div>
    <p class="note">这几分钱不是罚站。刚放下原文时它还在眼睛的余像里，
      这时候写，写出来的是刚才扫过的那几行；等它落下去，写出来的才是你的。</p>
    <div class="acts">
      <button class="btn-quiet" id="w-reread">回去再读一遍</button>
      <button class="btn-quiet" id="w-other">去练别的段</button>
      <button class="btn-quiet" id="w-skip">不等了，现在写</button>
    </div>
    <div class="stats">
      <span>你的稿子 ${d.draft ? plainLen(d.draft) + ' 字' : '还没写'}</span>
      <span>原文 ${d.passage.chars} 字</span>
      <span>提示 ${d.has_hints ? d.hints.length + ' 条已备好' : '还没做'}</span>
    </div>
  </div>`;

  $('#w-reread').onclick = () => go(`#/read/${bookId}/${chNo}`);
  $('#w-other').onclick = () => go(`#/book/${bookId}`);
  $('#w-skip').onclick = async () => {
    await api(`practice/${encodeURIComponent(bookId)}/${chNo}/${pNo}/skip-wait`, { body: {} });
    stopTimers();
    renderPractice(bookId, chNo, pNo, true);
  };
  S.timer = setInterval(() => {
    left -= 1;
    const cd = $('#cd');
    if (!cd) { clearInterval(S.timer); return; }
    cd.textContent = fmtClock(left);
    $('#bar').style.width = Math.min(100, ((total - left) / total) * 100) + '%';
    if (left <= 0) {
      clearInterval(S.timer);
      toast('可以写了。');
      renderPractice(bookId, chNo, pNo, true);
    }
  }, 1000);
}

/* ── 写作台：左边逐句提示，右边稿纸 ── */

function renderDesk(d, bookId, chNo, pNo, autoHint) {
  const started = Date.now();
  let usedHint = !!d.has_hints;

  const shell = () => `<div class="desk">
    <aside class="desk-hints" id="hint-panel"></aside>
    <div class="desk-write"><div class="inner">
      <div class="desk-lede">
        <span>原文已合上。凭记忆把这一段写回来，一句一句来。</span>
        <span class="right"><span id="wc">0 字</span>　原文 ${d.passage.chars} 字</span>
      </div>
      <div class="write-wrap">
        <textarea class="editor" id="draft" spellcheck="false"
          placeholder="从这里开始写"></textarea>
        <canvas class="anim-layer" id="anim"></canvas>
      </div>
      <div class="desk-foot">
        <span id="save-state">自动保存</span>
        <span class="right"></span>
        <span class="anim-pick">
          <span class="anim-label">输入动效</span>
          ${FONTS_ANIM.map((n) => `<button type="button" class="seg${S.anim === n ? ' on' : ''}"
            data-anim="${n}">${ANIM_NAME[n]}</button>`).join('')}
          <span class="anim-cur" id="anim-cur">当前：${ANIM_NAME[S.anim] || '关'}</span>
        </span>
        <button class="btn-quiet" id="reread">回去再读一遍</button>
        <button class="btn" id="submit">写完了，看对照</button>
      </div>
    </div></div>
  </div>`;

  $('#practice').innerHTML = shell();
  paintHints(d);
  const ta = $('#draft');
  ta.value = d.draft || '';
  const upd = () => { $('#wc').textContent = plainLen(ta.value) + ' 字'; };
  upd();
  ta.focus();
  ta.setSelectionRange(ta.value.length, ta.value.length);
  attachLive(ta, $('#anim'));
  bindAnimPick();

  ta.addEventListener('input', () => {
    upd();
    $('#save-state').textContent = '正在存';
    clearTimeout(S.saveTimer);
    S.saveTimer = setTimeout(async () => {
      try {
        await api(`practice/${encodeURIComponent(bookId)}/${chNo}/${pNo}/draft`,
          { method: 'PUT', body: { text: ta.value } });
        $('#save-state').textContent = '已存';
      } catch (e) { $('#save-state').textContent = '没存上：' + e.message; }
    }, 1200);
  });

  function paintHints(cur) {
    const panel = $('#hint-panel');
    if (!panel) return;
    const hints = cur.hints || [];
    if (hints.length) {
      panel.innerHTML = `<h3>逐句提示</h3>
        <p class="note">一共 ${hints.length} 条，对应原文的 ${cur.passage.sentences} 句。
          写的时候可以扫一眼，别照着它造句。</p>
        <button class="btn drill-cta" id="hint-single">一句一句单独练 →</button>
        <ol class="hint-list">${hints.map((h) => `<li>
          <span class="hno">${h.no}</span><span class="htxt">${esc(h.hint)}</span>
        </li>`).join('')}</ol>
        <div class="foot">
          <button class="btn-quiet" id="hint-again">重新生成提示</button>
          <button class="btn-quiet" id="hint-off">不用提示，凭记忆写</button>
        </div>`;
    } else if (cur.dropped_echoes && cur.dropped_echoes.length) {
      // 模型给的提示全都在照抄原文，与其把原文塞回给你，不如一条不给
      panel.innerHTML = `<h3>逐句提示</h3>
        <p class="note">这个模型给的提示全都在照搬原文的句子，已经全部弃用。
          给原文的句子等于让你抄，那样练了也没用。</p>
        <div class="foot">
          <button class="btn" id="hint-make">再试一次</button>
        </div>`;
    } else if (cur.llm_ready) {
      panel.innerHTML = `<h3>逐句提示</h3>
        <p class="note">还没有提示。要给每一句配一条提示，需要调用一次模型
          （同一段文字只生成一次）。</p>
        <div class="foot">
          <button class="btn" id="hint-make">生成逐句提示</button>
        </div>`;
    } else {
      panel.innerHTML = `<h3>逐句提示</h3>
        <p class="note">还没配置模型，所以没有提示。直接凭记忆写——
          富兰克林最初也是自己记提示的。</p>
        <div class="foot">
          <button class="btn-quiet" id="hint-set">去设置里填 Key</button>
        </div>`;
    }
    const again = $('#hint-again');
    if (again) again.onclick = () => fetchHints(true);
    const make = $('#hint-make');
    if (make) make.onclick = () => fetchHints(false);
    const off = $('#hint-off');
    if (off) {
      off.onclick = () => {
        usedHint = false;
        cur = { ...cur, hints: [] };
        paintHints(cur);
      };
    }
    const st = $('#hint-set');
    if (st) st.onclick = () => go('#/settings');
    const sg = $('#hint-single');
    if (sg) {
      sg.onclick = async () => {
        // 没提示也能一句一句练：现场补一次（缓存命中的话不花钱）
        let target = cur;
        if (!(cur.hints || []).length) {
          if (!cur.llm_ready) { go('#/settings'); return; }
          target = await fetchHints(false);
          if (!target || !(target.hints || []).length) return;
        }
        startDrill(target);
      };
    }
  }

  async function fetchHints(force) {
    const panel = $('#hint-panel');
    if (force && !confirm('重新生成会再调用一次模型（这一段已经做过的不再花钱）。继续？')) {
      return;
    }
    panel.innerHTML = `<h3>逐句提示</h3>
      <p class="note"><span class="spin"></span> 正在为每一句配提示</p>`;
    try {
      const r = await api(`practice/${encodeURIComponent(bookId)}/${chNo}/${pNo}/hints`,
        { body: { force: !!force } });
      usedHint = true;
      const next = { ...d, hints: r.hints, has_hints: (r.hints || []).length > 0,
                     dropped_echoes: r.dropped_echoes || [] };
      paintHints(next);
      if ((r.dropped_echoes || []).length) {
        toast(`有 ${r.dropped_echoes.length} 条提示在照抄原文，已弃用。`, true);
      }
      return next;
    } catch (e) {
      toast(e.message + (e.hint ? '　' + e.hint : ''), true);
      paintHints(d);
      return null;
    }
  }

  if (autoHint && !d.has_hints && d.llm_ready) fetchHints(false);

  const submit = async () => {
    const text = ta.value;
    if (plainLen(text) < 5) { toast('还没写。写完再交。', true); return; }
    const btn = $('#submit');
    btn.disabled = true;
    try {
      const r = await api(`practice/${encodeURIComponent(bookId)}/${chNo}/${pNo}/submit`,
        { body: { draft: text, prompt_used: usedHint,
                  write_seconds: Math.round((Date.now() - started) / 1000) } });
      renderCompare(r);
    } catch (err) {
      if (err.status === 423) {
        toast(err.message, true);
        await renderPractice(bookId, chNo, pNo, false);
      } else {
        toast(err.message, true);
        btn.disabled = false;
      }
    }
  };
  $('#submit').onclick = submit;
  ta.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') { e.preventDefault(); submit(); }
  });
  $('#reread').onclick = () => {
    modal(`<h3>回去再读一遍？</h3>
      <p class="muted">可以。读完这一段从头算起，等待时间也重新计。
        已经写下的字不会丢。</p>
      <div class="row"><button class="btn-quiet" id="no">不用了</button>
      <span class="right"></span><button class="btn" id="yes">去读原文</button></div>`,
      (box) => {
        $('#no', box).onclick = closeModal;
        $('#yes', box).onclick = async () => {
          closeModal();
          await api(`practice/${encodeURIComponent(bookId)}/${chNo}/${pNo}/start`,
            { body: { reread: true } });
          go(`#/read/${bookId}/${chNo}`);
        };
      });
  };
}

/* ── 单句练习：一句一条提示，只写这一句 ── */

function startDrill(d) {
  const hints = d.hints || [];
  if (!hints.length) {
    toast('要练单句得先有逐句提示。', true);
    return;
  }
  S.drill = { d, i: 0, lv: 0 };
  paintDrill();
}

function paintDrill() {
  const { d, i, lv } = S.drill;
  const hints = d.hints;
  const cur = hints[i];
  const yes = lv === 1 ? (S.drill.wrote || '') : '';
  const src = S.drill.src || '';
  // 只拿"原文这一句里也有、你也写到了"的词来标——
  // 这是单句模式最有用的东西：一眼看出哪几个词你抓住了。
  const hit = lv === 1 ? S.drill.hit || [] : [];
  const no = FONTS_ANIM.map((n) => `<button type="button"
      class="seg${S.anim === n ? ' on' : ''}"
      data-anim="${n}">${ANIM_NAME[n]}</button>`).join('');

  $('#practice').innerHTML = `<div class="drill">
    <div class="drill-bar">
      <span class="sno">第 ${cur.no} / ${hints.length} 句</span>
      <span class="right"></span>
      <span class="anim-pick">
        <span class="anim-label">输入动效</span>${no}
        <span class="anim-cur" id="anim-cur">当前：${ANIM_NAME[S.anim] || '关'}</span>
      </span>
      <button class="btn-quiet" id="d-back">回到整段</button>
    </div>
    <div class="hint">${esc(cur.hint)}</div>
    ${lv === 0
      ? `<div class="write-wrap">
           <textarea class="editor" id="d-write" spellcheck="false"
             placeholder="按这条提示，写一句"></textarea>
           <canvas class="anim-layer" id="anim"></canvas>
         </div>
         <div class="desk-foot">
           <span id="d-wc">0 字</span>
           <span class="right"></span>
           <button class="btn-quiet" id="d-prev"${i === 0 ? ' disabled' : ''}>上一句</button>
           <button class="btn" id="d-next">${i === hints.length - 1 ? '看这一句' : '下一句'}</button>
         </div>`
      : `<div class="pair-cols">
           <div><div class="lbl">原文这一句</div>
             <div class="ptext">${esc(src)}</div></div>
           <div><div class="lbl">你写的
             ${hit.length ? `<span class="hitnote">底色是原文里也有、你也写到的词</span>` : ''}</div>
             <div class="ptext mine">${yes
               ? highlight(yes, hit)
               : '<span class="ptext absent">（没写）</span>'}</div></div>
         </div>
         ${hit.length ? `<div class="hitrow"><span class="lbl">你抓住的词</span>
           <span class="wordwrap">${hit.map((w) => `<span>${esc(w)}</span>`).join('')}</span></div>` : ''}
         <div class="note-box">
           <div class="lbl">这一句的笔记</div>
           <textarea class="note-ta" id="note-ta"
             placeholder="你看到什么差别就写什么。比如：我把因果省了 / 短句被我连成长句 / 这个词记成了另一个">${esc(S.drill.note != null ? S.drill.note : '')}</textarea>
           <div class="row" style="margin-top:12px">
             <button class="btn" id="note-save">记下来</button>
             <span class="note-saved" id="note-saved">${
               S.drill.noteSaved ? '已记在这本书的笔记里' : ''}</span>
             <span class="right"></span>
             <button class="btn-quiet" id="d-prev"${i === 0 ? ' disabled' : ''}>上一句</button>
             <button class="btn-quiet" id="d-next">${
               i === hints.length - 1 ? '练完了' : '下一句'}</button>
           </div>
         </div>`}
  </div>`;

  $('#d-back').onclick = () => renderPractice(d.book.id, d.chapter.no, d.passage.no, false);
  bindAnimPick();
  const prev = $('#d-prev');
  if (prev) {
    prev.onclick = () => {
      if (i > 0) {
        S.drill.i = i - 1; S.drill.lv = 0;
        S.drill.note = null; S.drill.noteSaved = false;
        S.drill.wrote = ''; S.drill.wroteFor = -1;   // 回上一句也从头写
        paintDrill();
      }
    };
  }
  const next = $('#d-next');

  if (lv === 0) {
    const ta = $('#d-write');
    // 每一句都要干干净净地开始。这里以前会把上一句的内容填回来——明显的 bug。
    ta.value = (S.drill.wrote && S.drill.wroteFor === i) ? S.drill.wrote : '';
    ta.focus();
    ta.setSelectionRange(ta.value.length, ta.value.length);
    const upd = () => { $('#d-wc').textContent = plainLen(ta.value) + ' 字'; };
    upd();
    attachLive(ta, $('#anim'));
    ta.addEventListener('input', upd);
    ta.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') { e.preventDefault(); next.click(); }
    });
    next.onclick = async () => {
      S.drill.wrote = ta.value;
      S.drill.wroteFor = i;
      try {
        const r = await api(
          `practice/${encodeURIComponent(d.book.id)}/${d.chapter.no}/${d.passage.no}/sentence/${cur.no}`,
          { body: { text: ta.value } });
        S.drill.src = r.sentence;
        S.drill.hit = (factSheetLocal(r.sentence, ta.value)).hit;
      } catch (e) {
        S.drill.src = '（取不到原文）';
        S.drill.hit = [];
      }
      S.drill.lv = 1;
      S.drill.note = null;
      S.drill.noteSaved = false;
      paintDrill();
    };
  } else {
    const ta = $('#note-ta');
    if (ta) ta.focus();
    $('#note-save').onclick = async () => {
      const text = ta.value.trim();
      if (!text) { toast('笔记是空的。一句话就行。', true); return; }
      try {
        await api(`practice/${encodeURIComponent(d.book.id)}/${d.chapter.no}/${d.passage.no}/note`,
          { body: { text, sent_no: cur.no, sentence: src, mine: yes, hint: cur.hint } });
        S.drill.noteSaved = true;
        S.drill.note = text;
        $('#note-saved').textContent = '已记在这本书的笔记里';
        toast('记下了。这本书的目录页能看到全部笔记。');
      } catch (e) { toast(e.message, true); }
    };
    next.onclick = () => {
      if (i + 1 < hints.length) {
        S.drill.i = i + 1; S.drill.lv = 0;
        S.drill.note = null; S.drill.noteSaved = false;
        S.drill.wrote = ''; S.drill.wroteFor = -1;   // 下一句从空白开始
        paintDrill();
      } else {
        toast('单句练完了。整段还等着你写。');
        renderPractice(d.book.id, d.chapter.no, d.passage.no, false);
      }
    };
  }
}

/** 本地算一份"原文这一句里有哪些词你也写到了"。
 *  服务端算的是整段范围的，单句对照要的是这一句范围的。 */
function factSheetLocal(source, draft) {
  const runs = (t) => {
    const body = String(t || '').replace(/[，。！？；：、“”"'（）《》…—\s\dA-Za-z]/g, ' ');
    const out = [];
    body.split(' ').forEach((seg) => {
      let cur = '';
      for (const ch of seg) {
        if (FUNC.has(ch)) { if (cur) out.push(cur); cur = ''; } else cur += ch;
      }
      if (cur) out.push(cur);
    });
    return out;
  };
  const seen = new Set();
  const all = runs(source).filter((w) => {
    if (w.length < 2 || w.length > 8 || seen.has(w)) return false;
    seen.add(w); return true;
  });
  const hit = all.filter((w) => String(draft || '').includes(w));
  const miss = all.filter((w) => !String(draft || '').includes(w));
  return { hit, miss, hit_count: hit.length, miss_count: miss.length, total: all.length };
}

/* ── 对照：一句一句对着看 ── */

function renderCompare(d) {
  stopTimers();
  S.practice = d;
  setView('practice');
  $('#prac-title').textContent =
    `${d.book.title}　第 ${d.chapter.no} 节　第 ${d.passage.no} 段`;
  $('#prac-meta').textContent =
    `读 ${fmtDur(d.read_seconds)}　写 ${fmtDur(d.write_seconds)}　${
      d.prompt_used ? '用了提示' : '凭记忆'}`;
  $('#practice').innerHTML = compareHTML(d);

  const done = !!d.seen_at;
  $('#export').onclick = () => {
    location.href = new URL(
      `/api/export/${encodeURIComponent(d.book.id)}/${d.chapter.no}/${d.passage.no}`,
      location.href).href;
  };
  $('#back').onclick = () => go('#/book/' + d.book.id);
  if (done) {
    const nx = $('#next');
    if (nx) {
      nx.onclick = async () => {
        await loadBook(d.book.id);
        const t = nextTarget(S.book);
        if (t) go(`#/practice/${d.book.id}/${t.ch}/${t.p}`);
        else { toast('这本书每一段都练完了。'); go('#/book/' + d.book.id); }
      };
    }
    return;
  }
  $('#obs-save').onclick = async () => {
    const obs = $('#obs').value.trim();
    if (!obs) { toast('留一句吧，一句就够。', true); return; }
    try {
      await api(`practice/${encodeURIComponent(d.book.id)}/${d.chapter.no}/${d.passage.no}/observe`,
        { body: { observation: obs } });
      toast('这一轮完成。');
      await loadBook(d.book.id);
      const t = nextTarget(S.book);
      if (!t) { go('#/book/' + d.book.id); return; }
      modal(`<h3>这一轮完成</h3>
        <p class="muted">接着练第 ${t.ch} 节第 ${t.p} 段？</p>
        <div class="row"><button class="btn-quiet" id="later">先歇会儿</button>
        <span class="right"></span>
        <button class="btn" id="go">继续</button></div>`, (box) => {
        $('#later', box).onclick = () => { closeModal(); go('#/book/' + d.book.id); };
        $('#go', box).onclick = () => {
          closeModal();
          go(`#/practice/${d.book.id}/${t.ch}/${t.p}`);
        };
      });
    } catch (e) { toast(e.message, true); }
  };
}

/** 把原文和稿子按句对齐。
 *
 * 不能简单地"第 n 句对第 n 句"：你漏写一句，后面全都会错位，
 * 对照页显示的就是假信息——比不显示更糟。
 * 所以用最长公共子序列来对齐：多写的、漏写的单独标出来，其余各就各位。
 */
function pairUp(source, draft) {
  const a = splitSents(source);
  const b = splitSents(draft);
  const key = (s) => String(s).replace(/[，。！？；：、“”"'（）《》…—\s]/g, '');
  const A = a.map(key), B = b.map(key);

  // 先算 LCS，再回溯出对齐关系
  const n = A.length, m = B.length;
  const dp = Array.from({ length: n + 1 }, () => new Int32Array(m + 1));
  for (let i = n - 1; i >= 0; i--) {
    for (let j = m - 1; j >= 0; j--) {
      dp[i][j] = A[i] === B[j]
        ? dp[i + 1][j + 1] + 1
        : Math.max(dp[i + 1][j], dp[i][j + 1]);
    }
  }
  const out = [];
  let i = 0, j = 0;
  while (i < n || j < m) {
    if (i < n && j < m && A[i] === B[j]) {
      out.push({ no: i + 1, src: a[i], mine: b[j], same: true });
      i++; j++;
    } else if (i < n && (j >= m || dp[i + 1][j] >= dp[i][j + 1])) {
      out.push({ no: i + 1, src: a[i], mine: '', same: false, missing: true });
      i++;
    } else {
      out.push({ no: null, src: '', mine: b[j], same: false, extra: true });
      j++;
    }
  }
  return out;
}

function splitSents(t) {
  const out = [];
  let cur = '';
  for (const ch of String(t || '')) {
    cur += ch;
    if ('。！？'.includes(ch)) { if (cur.trim()) out.push(cur.trim()); cur = ''; }
  }
  if (cur.trim()) out.push(cur.trim());
  return out;
}

function compareHTML(d) {
  const f = d.facts || { segments: [], hit: [], miss: [], note: '' };
  const done = !!d.seen_at;
  const pairs = pairUp(d.source, d.draft);
  const hintOf = {};
  (d.hints || []).forEach((h) => { hintOf[h.no] = h.hint; });

  return `<div class="cmp">
    <div class="cmp-head">
      <h2>${done ? '这一轮练完了' : '对照'}</h2>
      <span class="right">原文 ${plainLen(d.source)} 字　你写的 ${plainLen(d.draft)} 字</span>
    </div>

    <div class="pairs">
      ${pairs.map((p) => `
        <div class="pair${p.extra ? ' extra' : ''}">
          <div class="pair-hint">
            <span class="hno">${p.no == null ? '＋' : p.no}</span>
            <span>${p.no != null
              ? (hintOf[p.no] ? esc(hintOf[p.no]) : '<span class="muted">（这一句当时没有提示）</span>')
              : '<span class="muted">原文里没有对应的一句</span>'}</span>
          </div>
          <div class="pair-cols">
            <div>
              <div class="lbl">原文</div>
              <div class="ptext">${p.no != null ? esc(p.src)
                : '<span class="ptext absent">（没有）</span>'}</div>
            </div>
            <div>
              <div class="lbl">你写的</div>
              <div class="ptext mine">${p.mine
                ? highlight(p.mine, f.hit || [])
                : '<span class="ptext absent">（这一句没写）</span>'}</div>
            </div>
          </div>
        </div>`).join('')}
    </div>

    <div class="miss">
      <h3>原文里有、你没写到的片段</h3>
      <ul class="miss-list">
        ${(f.segments || []).map((s) => `<li>${esc(s)}</li>`).join('')
          || '<li class="muted">没有。能比对的片段你都写到了。</li>'}
      </ul>
      <p class="cmp-note">${esc(f.note || '')}</p>
      <details class="words">
        <summary>按词看：原文 ${f.total || 0} 条片段，写到 ${f.hit_count || 0} 条，没写到 ${f.miss_count || 0} 条</summary>
        <div class="wordwrap">${(f.hit || []).map((w) => `<span>${esc(w)}</span>`).join('')
          || '<span class="muted">（无）</span>'}</div>
        <div class="wordwrap miss">${(f.miss || []).map((w) => `<span>${esc(w)}</span>`).join('')
          || '<span class="muted">（无）</span>'}</div>
      </details>
    </div>

    <div class="observe">
      <h3>${done ? '这一段的笔记' : '最后一步：记一条笔记'}</h3>
      ${done
        ? `${d.observation ? `<div class="obs-saved">${escNL(d.observation)}</div>`
             : '<p class="muted small">这一轮没有记笔记。下次可以留一句。</p>'}
           <p class="muted small">这条笔记已经收进《${esc(d.book.title)}》的笔记里，
             在目录页能看到全部。</p>
           <div class="cmp-actions">
             <button class="btn-quiet" id="export">导出这一轮</button>
             <button class="btn-quiet" id="back">回目录</button>
             <span class="right"></span>
             <button class="btn" id="next">练下一段</button>
           </div>`
        : `<p class="note">一句就够。比如"第二句我把因果省了"、"我把三个短句连成了一个长句"、
             "有个词我记成了另一个"。这条会收进这本书的笔记，随时能翻。</p>
           <textarea class="obs-ta" id="obs" placeholder="我看到的差别是"></textarea>
           <div class="cmp-actions">
             <button class="btn" id="obs-save">记下，结束这一轮</button>
             <span class="right"></span>
             <button class="btn-quiet" id="export">导出这一轮</button>
             <button class="btn-quiet" id="back">回目录</button>
           </div>`}
    </div>
  </div>`;
}

/** 把原文里也有、你也写出来的词标出来。 */
function highlight(text, words) {
  const used = new Array(text.length).fill(false);
  const marks = [];
  (words || []).forEach((w) => {
    if (!w) return;
    let i = text.indexOf(w);
    while (i >= 0) {
      let free = true;
      for (let k = i; k < i + w.length; k++) if (used[k]) { free = false; break; }
      if (free) {
        for (let k = i; k < i + w.length; k++) used[k] = true;
        marks.push([i, i + w.length]);
      }
      i = text.indexOf(w, i + 1);
    }
  });
  marks.sort((a, b) => a[0] - b[0]);
  let out = '', cur = 0;
  marks.forEach(([a, b]) => {
    if (a < cur) return;
    out += esc(text.slice(cur, a)) + '<mark>' + esc(text.slice(a, b)) + '</mark>';
    cur = b;
  });
  return out + esc(text.slice(cur));
}

/* ───────────────── 记录 ───────────────── */

async function loadRecords() {
  const r = await api('records');
  setView('records');
  S.records = r;
  $('#records-lead').textContent = r.counts.records
    ? `练过 ${r.counts.records} 段，其中 ${r.counts.done} 段看完对照写下了观察。`
    : '还没有记录。练完一段、写下观察，这里会留下那一轮的提示、原文、你的稿子和你说的话。';

  if (!r.rows.length) {
    $('#records').innerHTML = `<div class="blank">
      <h2>还没有练习记录</h2><p>从书架上打开一本，读一段，再写回来。</p></div>`;
    return;
  }
  $('#records').innerHTML = r.rows.map((row, i) => `
    <div class="rec" data-i="${i}">
      <div class="rec-head">
        <span class="rec-book">${esc(row.book)}</span>
        <span class="rec-when">第 ${row.chapter} 节第 ${row.passage} 段　${
          esc(fmtWhen(row.wrote_at || row.read_at))}</span>
        <span class="rec-stats">
          <span>${row.chars} 字</span>
          <span>写 ${fmtDur(row.write_seconds)}</span>
          <span>${row.prompt_used ? '用提示' : '凭记忆'}</span>
          <span>${row.stage === 'done' ? '已看完' : '待看对照'}</span>
        </span>
      </div>
      <div class="rec-body hidden" id="rec-${i}"></div>
    </div>`).join('');

  $$('.rec-head').forEach((h) => {
    h.onclick = async () => {
      const i = h.parentElement.dataset.i;
      const body = $('#rec-' + i);
      const row = r.rows[parseInt(i, 10)];
      if (!body.classList.contains('hidden')) { body.classList.add('hidden'); return; }
      body.classList.remove('hidden');
      if (body.dataset.filled) return;
      body.dataset.filled = '1';
      body.innerHTML = '<div class="loading"><span class="spin"></span> 取原文</div>';
      let data;
      try {
        data = await api(`practice/${encodeURIComponent(row.book_id)}/${row.chapter}/${row.passage}/compare`);
      } catch (e) {
        body.innerHTML = `<p class="muted small">取不到这一轮的原文：${esc(e.message)}</p>`;
        return;
      }
      const pairs = pairUp(data.source, row.draft);
      const hintOf = {};
      (row.hints || data.hints || []).forEach((x) => { hintOf[x.no] = x.hint; });
      body.innerHTML = `
        ${Object.keys(hintOf).length ? `<h4>当时给的逐句提示</h4>
          <ul class="rec-hints">${(row.hints || data.hints || []).map((x) => `<li>
            <span class="hno">${x.no}</span><span>${esc(x.hint)}</span></li>`).join('')}</ul>` : ''}
        ${pairs.map((p) => `
          <h4>${p.extra ? '多写的一句' : '第 ' + p.no + ' 句'}</h4>
          <div class="pair-cols">
            <div><div class="lbl">原文</div><div class="rec-text">${
              p.no != null ? esc(p.src) : '<span class="muted">（没有）</span>'}</div></div>
            <div><div class="lbl">你写的</div><div class="rec-text">${
              esc(p.mine) || '<span class="muted">（没写）</span>'}</div></div>
          </div>`).join('')}
        ${row.observation ? `<h4>我的观察</h4>
          <div class="rec-text">${escNL(row.observation)}</div>` : ''}
        <div class="row" style="margin-top:20px">
          <button class="btn-quiet" data-export="${esc(row.book_id)}|${row.chapter}|${row.passage}">
            导出这一轮</button>
        </div>`;
      $$('[data-export]', body).forEach((b) => {
        b.onclick = () => {
          const [bid, ch, p] = b.dataset.export.split('|');
          location.href = new URL(`/api/export/${encodeURIComponent(bid)}/${ch}/${p}`,
            location.href).href;
        };
      });
    };
  });
}

/* ───────────────── 设置 ───────────────── */

async function loadSettings() {
  const st = await api('settings');
  S.settings = st;
  setView('settings');
  const c = st.cache || { cached: 0, calls: 0, hits: 0, tokens_in: 0, tokens_out: 0 };

  $('#settings').innerHTML = `
    <div class="block">
      <h2>模型</h2>
      <p class="note">只在「给每一句配一条提示」这一步用到。你读原文、写稿子、
        看对照，全程不经过模型。</p>
      <div class="field"><label>服务商</label>
        <select id="s-provider">
          ${(st.presets || []).map((p) => `<option value="${esc(p.id)}"${
            p.id === st.provider ? ' selected' : ''}>${esc(p.name)}</option>`).join('')}
        </select><div class="hint" id="key-hint"></div></div>
      <div class="cols">
        <div class="field"><label>接口地址</label>
          <input id="s-base" value="${esc(st.base_url)}" placeholder="https://api.deepseek.com/v1"></div>
        <div class="field"><label>模型名</label>
          <input id="s-model" value="${esc(st.model)}" placeholder="deepseek-chat"></div>
      </div>
      <div class="field"><label>API Key</label>
        <input id="s-key" type="password" placeholder="${
          st.has_key ? '已填 ' + esc(st.key_hint) + '，留空则不改' : '粘贴你的 Key'}">
        <div class="hint">只存在这台机器的 app/data/index.json 里，不会上传，也不写日志。</div>
      </div>
      <div class="row">
        <button class="btn" id="s-save">保存</button>
        <button class="btn-quiet" id="s-test">测试连接</button>
        ${st.has_key ? '<button class="btn-quiet" id="s-clear">清掉 Key</button>' : ''}
        <span class="right"></span><span id="s-status"></span>
      </div>
    </div>

    <div class="block">
      <h2>提示的用量</h2>
      <p class="note">同一段文字只生成一次，不管它出现在哪本书里。
        下面是服务商回传的真实数字——拿不到就记 0，不估算。</p>
      <div class="stats-grid">
        <div><span class="k">缓存里</span><span class="v">${c.cached}</span></div>
        <div><span class="k">调用过</span><span class="v">${c.calls}</span></div>
        <div><span class="k">命中缓存</span><span class="v">${c.hits}</span></div>
        <div><span class="k">输入 token</span><span class="v">${(c.tokens_in || 0).toLocaleString()}</span></div>
        <div><span class="k">输出 token</span><span class="v">${(c.tokens_out || 0).toLocaleString()}</span></div>
        <div><span class="k">模型用时</span><span class="v">${(c.seconds || 0).toFixed(1)}s</span></div>
      </div>
      ${c.without_usage ? `<p class="muted small">其中 ${c.without_usage} 次服务商没有回传用量，
        那几次没有计入。</p>` : ''}
      <p class="muted small">缓存文件 <span class="mono">${esc(c.file || '')}</span>。
        换模型或改提示词会让旧缓存失效（不同模型的说法不一样）。删掉它不影响原文和稿子。</p>
      <div class="row"><button class="btn-quiet" id="s-clear-cache">清空提示缓存</button></div>
    </div>

    <div class="block">
      <h2>节奏</h2>
      <p class="note">读完原文之后，隔多久才让你开始写。</p>
      <div class="cols">
        <div class="field"><label>间隔（分钟）</label>
          <input id="s-delay" type="number" min="0" max="240" step="1" value="${st.delay_min}">
          <div class="hint">0 表示读完立刻能写。建议 3 到 10 分钟。</div></div>
        <div class="field"><label>新导入的书每段多少字</label>
          <input id="s-size" type="number" min="80" max="2000" step="50" value="${st.passage_chars}">
          <div class="hint">只影响之后导入的书。</div></div>
      </div>
      <div class="row"><button class="btn" id="s-save2">保存</button></div>
    </div>

    <div class="block">
      <h2>数据</h2>
      <p class="note">全部在这台机器上：<span class="mono">${esc(st.data_dir)}</span></p>
      <p class="muted small">index.json 是书目、稿子、观察；texts/ 是每本书的原文；
        summaries.json 是提示缓存。都是纯文本，可以直接打开、复制、备份。</p>
    </div>`;

  const prov = $('#s-provider');
  const fill = () => {
    const p = (st.presets || []).find((x) => x.id === prov.value);
    if (!p) return;
    if (p.base_url) $('#s-base').value = p.base_url;
    if (p.model) $('#s-model').value = p.model;
    $('#key-hint').innerHTML = p.key_url
      ? `申请地址 <a href="${esc(p.key_url)}" target="_blank" rel="noreferrer">${esc(p.key_url)}</a>`
      : '本地服务不需要 Key。';
  };
  prov.onchange = fill;
  fill();

  const save = async () => {
    const body = {
      provider: prov.value,
      base_url: $('#s-base').value.trim(),
      model: $('#s-model').value.trim(),
      delay_min: parseFloat($('#s-delay').value),
      passage_chars: parseInt($('#s-size').value, 10),
    };
    const k = $('#s-key').value.trim();
    if (k) body.api_key = k;
    try { await api('settings', { body }); toast('已保存。'); loadSettings(); }
    catch (e) { toast(e.message, true); }
  };
  $('#s-save').onclick = save;
  $('#s-save2').onclick = save;

  $('#s-test').onclick = async () => {
    const el = $('#s-status');
    el.className = ''; el.innerHTML = '<span class="spin"></span> 测试中';
    try {
      const body = {
        provider: prov.value, base_url: $('#s-base').value.trim(),
        model: $('#s-model').value.trim(),
      };
      const k = $('#s-key').value.trim();
      if (k) body.api_key = k;
      await api('settings', { body });
      const r = await api('llm/test', { body: {} });
      el.className = 'ok';
      el.textContent = `通了，${r.model} 用了 ${r.seconds} 秒。`;
      loadSettings();
    } catch (e) {
      el.className = 'bad';
      el.textContent = e.message + (e.hint ? '　' + e.hint : '');
    }
  };
  const clr = $('#s-clear');
  if (clr) {
    clr.onclick = async () => {
      await api('settings', { body: { clear_key: true } });
      toast('Key 已清掉。');
      loadSettings();
    };
  }
  $('#s-clear-cache').onclick = async () => {
    const r = await api('summaries/clear', { body: {} });
    toast(`清掉 ${r.removed} 段提示。原文和稿子都没动。`);
    loadSettings();
  };
}

/* ───────────────── 路由 ───────────────── */

async function route() {
  const raw = location.hash.replace(/^#\/?/, '');
  const [pathPart, queryPart] = raw.split('?');
  const q = new URLSearchParams(queryPart || '');
  const parts = pathPart.split('/').filter(Boolean);
  const page = parts[0] || 'shelf';
  try {
    if (page === 'shelf') await loadShelf();
    else if (page === 'book' && parts[1]) await loadBook(parts[1]);
    else if (page === 'read' && parts[1]) await loadRead(parts[1], parseInt(parts[2] || '1', 10));
    else if (page === 'practice' && parts[1]) {
      await openPractice(parts[1], parseInt(parts[2], 10), parseInt(parts[3], 10),
        parseInt(q.get('read') || '0', 10));
    } else if (page === 'records') await loadRecords();
    else if (page === 'settings') await loadSettings();
    else go('#/shelf');
  } catch (e) {
    toast(e.message, true);
    if (page !== 'shelf') go('#/shelf');
  }
  document.body.classList.remove('booting');
}

/* ───────────────── 启动 ───────────────── */

const FONTS = ['song', 'kai', 'hei'];
function initTheme() {
  const t = localStorage.getItem('fk-theme');
  if (t) document.documentElement.dataset.theme = t;
  const f = localStorage.getItem('fk-font');
  if (f && FONTS.includes(f)) document.documentElement.dataset.font = f;
}
$('#btn-theme').onclick = () => {
  const cur = document.documentElement.dataset.theme;
  const next = cur === 'night' ? 'paper' : 'night';
  document.documentElement.dataset.theme = next;
  localStorage.setItem('fk-theme', next);
};
$('#btn-font').onclick = () => {
  const cur = document.documentElement.dataset.font || 'song';
  const next = FONTS[(FONTS.indexOf(cur) + 1) % FONTS.length];
  document.documentElement.dataset.font = next;
  localStorage.setItem('fk-font', next);
  toast({ song: '宋体', kai: '楷体', hei: '黑体' }[next]);
};

window.addEventListener('hashchange', route);
window.addEventListener('DOMContentLoaded', () => {
  initTheme();
  if (!location.hash) location.hash = '#/shelf';
  route();
});

/* 测试挂钩：Node 下跑渲染测试时用（tests/render_check.mjs） */
if (typeof document === 'undefined') {
  globalThis.__fk = { S, esc, escNL, plainLen, fmtClock, fmtDur,
                      shelfHTML, shelfLead, bookHTML, readerHTML, compareHTML,
                      pairUp, splitSents, highlight, STAGE };
}
