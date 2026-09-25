/* ═══════════════════════════════════════════════════════════════
   ui_check — 按钮点得动、点了有变化。

   为什么单独一个文件：出过两次这样的事故——
     · 动效三档看起来一模一样（按钮改了变量，但画的时候没读它）
     · 用户反馈"这个按钮还是没用，换不了也关不掉"

   静态检查看不出这类问题，肉眼也难。所以这里把页面的内层 HTML 收下来，
   找出模板里真的渲染出来的 button[data-anim]，调它们的 onclick，
   再看状态和界面标记有没有跟着变。

   跑法：node tests/ui_check.mjs
   ═══════════════════════════════════════════════════════════════ */
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.join(HERE, '..');

const PASS = [], FAIL = [];
function check(name, ok, detail = '') {
  (ok ? PASS : FAIL).push([name, detail]);
  console.log((ok ? '  [OK] ' : '  [!!] ') + name + (!ok && detail ? '  — ' + detail : ''));
}

/* ── 一个能"记住渲染结果"的假 DOM ──
   这是关键：innerHTML 一被赋值，就把里面的 id 和 button 收下来，
   这样后面才找得到模板真正渲染出来的那些按钮。 */
const store = new Map();          // id -> element
const buttons = [];               // 模板渲染出来的 button（带 data-anim 的）

function makeEl(tag = 'div', id = '') {
  const el = {
    tagName: tag, id, dataset: {}, style: {}, value: '', textContent: '',
    scrollLeft: 0, scrollTop: 0, offsetLeft: 12, offsetTop: 34,
    selectionStart: 0, selectionEnd: 0, parentNode: null,
    _on: {},
    classList: {
      _s: new Set(),
      add(...c) { c.forEach((x) => this._s.add(x)); },
      remove(...c) { c.forEach((x) => this._s.delete(x)); },
      toggle(c, on) {
        if (on === undefined) on = !this._s.has(c);
        on ? this._s.add(c) : this._s.delete(c);
        return on;
      },
      contains(c) { return this._s.has(c); },
    },
    get innerHTML() { return this._html || ''; },
    set innerHTML(v) { index(String(v)); this._html = String(v); },
    addEventListener(k, f) { (this._on[k] = this._on[k] || []).push(f); },
    removeEventListener() {},
    getBoundingClientRect: () => ({ width: 420, height: 220, left: 0, top: 0 }),
    getContext: () => ctx,
    appendChild(c) { c.parentNode = el; return c; },
    removeChild() {},
    setSelectionRange() {}, focus() {},
  };
  return el;
}

// 从 HTML 文本里收集 id 与带 data-anim 的按钮
function index(html) {
  for (const m of html.matchAll(/id="([^"]+)"/g)) {
    if (!store.has(m[1])) store.set(m[1], makeEl('div', m[1]));
  }
  for (const m of html.matchAll(/<button\b([^>]*)>([^<]*)<\/button>/g)) {
    const attrs = m[1];
    const am = attrs.match(/data-anim="(\d+)"/);
    if (!am) continue;
    const idm = attrs.match(/id="([^"]+)"/);
    const b = makeEl('button', idm ? idm[1] : '');
    b.dataset.anim = am[1];
    b._label = m[2].trim();
    const cm = attrs.match(/class="([^"]*)"/);
    if (cm) cm[1].split(/\s+/).filter(Boolean).forEach((c) => b.classList.add(c));
    if (!buttons.some((x) => x === b)) buttons.push(b);
  }
}

const ctx = new Proxy({}, { get: () => () => {}, set: () => true });
const document = {
  querySelector: (s) => (s.startsWith('#') ? (store.get(s.slice(1)) || makeEl()) : makeEl()),
  querySelectorAll: (s) => (s === '[data-anim]' ? buttons.slice() : []),
  createElement: (t) => makeEl(t),
  createTextNode: (t) => ({ text: t }),
  addEventListener() {},
  body: makeEl('body'),
  documentElement: { dataset: {} },
};

const sb = {
  document,
  window: { addEventListener() {}, removeEventListener() {}, scrollTo() {},
            devicePixelRatio: 1, location: { href: 'http://127.0.0.1:8137/' } },
  location: { hash: '', href: 'http://127.0.0.1:8137/' },
  localStorage: {
    _m: new Map(),
    getItem(k) { return this._m.has(k) ? this._m.get(k) : null; },
    setItem(k, v) { this._m.set(k, String(v)); },
  },
  sessionStorage: { getItem: () => null, setItem() {} },
  fetch: () => Promise.resolve({ ok: true, json: () => Promise.resolve({}) }),
  getComputedStyle: () => ({
    fontFamily: 'Songti SC, serif', fontSize: '17px', lineHeight: '34px',
    letterSpacing: 'normal', paddingLeft: '0px', paddingTop: '24px',
    paddingRight: '0px', paddingBottom: '0px',
    borderLeftWidth: '0px', borderTopWidth: '1px', textAlign: 'left',
    getPropertyValue: () => '#262114',
  }),
  performance: { now: () => 0 },
  requestAnimationFrame: (f) => { try { f(16); } catch (e) { /* 忽略 */ } return 1; },
  cancelAnimationFrame: () => {},
  setTimeout: (f) => { try { f(); } catch (e) { /* 忽略 */ } return 0; },
  clearTimeout: () => {}, setInterval: () => 0, clearInterval: () => {},
  console, URL, encodeURIComponent, decodeURIComponent, JSON, Math, Date, Promise,
  Number, String, Array, Object, Error, isNaN, parseInt, parseFloat, RegExp, Set, Map,
};
sb.globalThis = sb;

const code = fs.readFileSync(path.join(ROOT, 'app', 'web', 'app.js'), 'utf8');
vm.createContext(sb);
let fk = null, err = null;
try {
  fk = vm.runInContext(`(function(){
${code}
;return { S, ANIM_NAME, ANIM_SPEC, FONTS_ANIM, renderDesk, setAnim, bindAnimPick };
})()`, sb, { filename: 'app.js' });
} catch (e) { err = e; }

if (!fk || typeof fk.renderDesk !== 'function') {
  console.log('  [!!] app.js 加载不出 renderDesk');
  console.log('       ' + (err ? err.message : '（没有异常）'));
  process.exit(1);
}
check('app.js 能在最小环境下加载', true);

/* ── 渲染写作台，看动效按钮有没有真的出现在页面里 ── */

const practice = store.get('practice') || makeEl('div', 'practice');
store.set('practice', practice);
store.set('prac-title', makeEl('div', 'prac-title'));
store.set('prac-meta', makeEl('div', 'prac-meta'));
store.set('prac-back', makeEl('button', 'prac-back'));

const fakeData = {
  book: { id: 'bk-1', title: '测试书' },
  chapter: { no: 1 },
  passage: { no: 1, chars: 300, sentences: 9 },
  stage: 'ready', delay_min: 3, remaining: 0,
  hints: [{ no: 1, hint: '第一句讲什么' }], has_hints: true,
  llm_ready: true, draft: '',
};

try {
  fk.renderDesk(fakeData, 'bk-1', 1, 1, false);
  check('写作台渲染成功', practice.innerHTML.includes('draft'));
} catch (e) {
  check('写作台渲染成功', false, e.message + '\n' + (e.stack || ''));
}

check('模板真的渲染出了动效按钮', buttons.length >= 4,
  `找到 ${buttons.length} 个 button[data-anim]`);
check('四个档位都在（淡入/升起/书写/关）',
  buttons.length === 4 && buttons.map((b) => b.dataset.anim).join(',') === '1,2,3,4',
  JSON.stringify(buttons.map((b) => b.dataset.anim)));
check('按钮上有文字标签',
  buttons.every((b) => b._label && b._label.length), 
  JSON.stringify(buttons.map((b) => b._label)));

/* ── 核心：点按钮要真的有反应 ── */

check('按钮都挂上了 onclick', buttons.every((b) => typeof b.onclick === 'function'),
  JSON.stringify(buttons.map((b) => typeof b.onclick)));

// 逐个点一遍：每点一次都要满足"状态变了、这一颗亮、别的灭"。
// 每次只验这一件事，不要在循环外面再断言最后一次的状态——那样很容易
// 写成"最后点的那个才作数"，反而掩盖问题。
const bad = [];
for (const n of [2, 3, 4, 1]) {
  const btn = buttons.find((b) => b.dataset.anim === String(n));
  try { btn.onclick(); } catch (e) { bad.push(`点${n} 抛异常：${e.message}`); continue; }
  if (fk.S.anim !== n) bad.push(`点${n} 之后 S.anim=${fk.S.anim}`);
  if (!btn.classList.contains('on')) bad.push(`点${n} 之后这一颗没亮`);
  if (buttons.some((b) => b !== btn && b.classList.contains('on'))) {
    bad.push(`点${n} 之后还有别的按钮亮着`);
  }
  if (sb.localStorage.getItem('fk-anim') !== String(n)) {
    bad.push(`点${n} 之后没存进本地`);
  }
  if (n === 4 && fk.S.live && fk.S.live.enabled) {
    bad.push(`点了「关」但动效还是开着的（S.anim=${fk.S.anim}，`
      + `enabled=${fk.S.live.enabled}）`);
  }
}
check('四个按钮点了都真的生效（状态 / 高亮 / 存盘 / 关档）', bad.length === 0,
  bad.join('；'));

check('关档能把动效真的关掉',
  (() => { fk.setAnim(4); return fk.S.anim === 4 && sb.localStorage.getItem('fk-anim') === '4'; })(),
  `${fk.S.anim} / ${sb.localStorage.getItem('fk-anim')}`);

try { fk.setAnim(1); } catch (e) { check('setAnim 能单独调用', false, e.message); }
check('setAnim 能单独调用', fk.S.anim === 1 && sb.localStorage.getItem('fk-anim') === '1',
  `${fk.S.anim} / ${sb.localStorage.getItem('fk-anim')}`);

/* ── "当前是哪个"要写在界面上，不用靠猜 ── */

try {
  fk.setAnim(2);
  const cur = store.get('anim-cur');
  check('界面上写着当前是哪一档',
    cur && cur.textContent.includes('升起'), cur ? cur.textContent : '（没有这个元素）');
  fk.setAnim(4);
  check('关掉之后界面上也说的是关',
    store.get('anim-cur').textContent.includes('关'),
    store.get('anim-cur').textContent);
  fk.setAnim(1);
} catch (e) { check('当前档位显示', false, e.message); }

/* ── 三档的画法必须真的不同（这条以前踩过坑） ── */

const spec = fk.ANIM_SPEC;
check('三档的时长各不相同',
  new Set([spec[1].life, spec[2].life, spec[3].life]).size === 3,
  JSON.stringify([spec[1].life, spec[2].life, spec[3].life]));
check('三档的画法参数各不相同',
  new Set([1, 2, 3].map((k) => JSON.stringify(
    [spec[k].scale, spec[k].rise, spec[k].reveal, spec[k].sweep, spec[k].cover]))).size === 3,
  JSON.stringify([1, 2, 3].map((k) => [spec[k].scale, spec[k].rise,
    spec[k].reveal, spec[k].sweep, spec[k].cover])));
check('淡入的幅度回到了明显的手感（不是那种看不见的轻放大）',
  spec[1].scale >= 0.3, String(spec[1].scale));
check('共有四档可选', fk.FONTS_ANIM.length === 4, JSON.stringify(fk.FONTS_ANIM));

console.log('\n' + '─'.repeat(62));
console.log(`通过 ${PASS.length} 项，失败 ${FAIL.length} 项`);
for (const [n, d] of FAIL) console.log('  失败：' + n + (d ? '  ' + d : ''));
process.exit(FAIL.length ? 1 : 0);
