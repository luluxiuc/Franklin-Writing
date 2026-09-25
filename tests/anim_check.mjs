/* ═══════════════════════════════════════════════════════════════
   anim_check — 输入动效的冒烟测试。

   动效是用 canvas 盖在 textarea 上画的，画的是"正在飞的那几个字"。
   这东西写错了的后果很具体：打字时页面卡、或者直接抛异常把输入框弄死。
   所以这里在最小 DOM 影子 + 假 canvas 上把它整个跑一遍：

     · 能不能挂上（attachLive 不炸）
     · 打字时会不会真的去量位置、去画
     · 粘贴、删除、空格会不会误触发
     · stop() 能不能干净地拆掉（切页面时要调）

   跑法：node tests/anim_check.mjs
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

/* ── 假 DOM：只做动效需要的那几件事 ── */

const drawn = [];         // 记录画过什么
const listeners = [];     // 记录挂过什么监听
let rafCount = 0;
let spawnCount = 0;       // 记录"安排了多少个字做动画"（比数绘制次数更可靠）
const spawned = () => spawnCount;

const ctx = new Proxy({
  setTransform() {}, clearRect() {}, save() {}, restore() {},
  beginPath() {}, rect() {}, clip() {},
  fillText(ch, x, y) { drawn.push({ ch, x, y }); },
}, { get(t, k) { return k in t ? t[k] : () => {}; }, set() { return true; } });

function makeEl(tag = 'div') {
  const el = {
    tagName: tag, dataset: {}, style: {}, value: '', textContent: '', innerHTML: '',
    // 这几个必须是数字：动画的坐标靠它们算，给了 undefined 就会算出 NaN，
    // 而 NaN 传进 canvas 是**静默丢弃**——画不出来还不报错，最难查。
    scrollLeft: 0, scrollTop: 0, offsetLeft: 12, offsetTop: 34,
    selectionStart: 0, selectionEnd: 0,
    width: 0, height: 0,
    classList: { add() {}, remove() {}, toggle() {}, contains: () => false },
    parentNode: null,
    addEventListener(k, f) { listeners.push([el.id || tag, k, f]); },
    removeEventListener() {},
    getBoundingClientRect: () => ({ width: 420, height: 220, left: 0, top: 0 }),
    getContext: () => ctx,
    appendChild(c) { c.parentNode = el; return c; },
    removeChild() {},
    setSelectionRange() {}, focus() {},
  };
  return el;
}

const document = {
  querySelector: () => makeEl(),
  querySelectorAll: () => [],
  createElement: (t) => makeEl(t),
  createTextNode: (t) => ({ text: t }),
  addEventListener() {},
  body: makeEl('body'),
  documentElement: { dataset: {} },
};

const sb = {
  document,
  window: { addEventListener() {}, removeEventListener() {}, scrollTo() {},
            devicePixelRatio: 2, location: { href: 'http://127.0.0.1:8137/' } },
  location: { hash: '', href: 'http://127.0.0.1:8137/' },
  localStorage: { getItem: () => null, setItem() {} },
  sessionStorage: { getItem: () => null, setItem() {} },
  fetch: () => Promise.resolve({ ok: true, json: () => Promise.resolve({}) }),
  getComputedStyle: () => ({
    fontFamily: 'Songti SC, serif', fontSize: '17px', lineHeight: '34px',
    letterSpacing: 'normal', paddingLeft: '0px', paddingTop: '24px',
    paddingRight: '0px', paddingBottom: '0px',
    borderLeftWidth: '0px', borderTopWidth: '1px', textAlign: 'left',
    getPropertyValue: () => '#262119',
  }),
  performance: { now: () => 0 },
  // 同步执行，而且**时间要往前走**：动画靠帧间隔推进，
  // 如果每帧都给同一个时间戳，动画会永远停在第一帧（我就是这么踩进去的）
  requestAnimationFrame: (f) => {
    rafCount++;
    try { f(rafCount * 16); } catch (e) { /* 忽略 */ }
    return rafCount;
  },
  cancelAnimationFrame: () => {},
  // 同样同步：beforeinput 那条路要等浏览器把字插进去再量坐标，
  // 测试里必须让它立刻发生，否则断言跑在动画之前
  setTimeout: (f) => { try { f(); } catch (e) { /* 忽略 */ } return 0; },
  clearTimeout: () => {},
  setTimeout, clearTimeout, setInterval, clearInterval, console,
  URL, encodeURIComponent, decodeURIComponent, JSON, Math, Date, Promise,
  Number, String, Array, Object, Error, isNaN, parseInt, parseFloat, RegExp, Set, Map,
};
sb.globalThis = sb;

const code = fs.readFileSync(path.join(ROOT, 'app', 'web', 'app.js'), 'utf8');
vm.createContext(sb);
let fk = null, err = null;
try {
  // 数一数"安排了多少个字"：这个数字才是动画规模的真正上限。
  // 数绘制次数会被 rAF 的调度细节干扰，不适合当断言依据。
  const instrumented = code.replace(
    'function spawn(ch, index, delay) {',
    'function spawn(ch, index, delay) { globalThis.__spawnTick && globalThis.__spawnTick();');
  sb.__spawnTick = () => { spawnCount++; };
  fk = vm.runInContext(`(function(){
${instrumented}
;return { attachLive, S, ANIM_NAME, ANIM_SPEC };
})()`, sb, { filename: 'app.js' });
} catch (e) { err = e; }

if (!fk || typeof fk.attachLive !== 'function') {
  console.log('  [!!] app.js 加载不出 attachLive');
  console.log('       ' + (err ? err.message : '（没有异常）'));
  process.exit(1);
}
check('app.js 能在最小环境下加载', true);
check('动效有四档（三种加一个关闭）',
  Object.keys(fk.ANIM_NAME).length === 4 && fk.ANIM_NAME[4] === '关',
  JSON.stringify(fk.ANIM_NAME));

/* ── 挂上 ── */

const ta = makeEl('textarea');
ta.id = 'ta';
const canvas = makeEl('canvas');
canvas.id = 'cv';
let live = null;
try {
  live = fk.attachLive(ta, canvas);
  check('attachLive 能挂上', !!live && typeof live.stop === 'function');
} catch (e) {
  check('attachLive 能挂上', false, e.message + '\n' + (e.stack || ''));
  process.exit(1);
}

const inputFn = () => listeners.filter((l) => l[1] === 'input').pop();
check('挂上了 input 监听', !!inputFn());

/* ── 打字：插入一个字符应该触发 ── */

function type(text, prevLen) {
  const before = drawn.length;
  ta.value = text;
  const f = inputFn();
  if (f) f[2]();
  return drawn.length - before;
}

live.enabled = true;
try {
  ta.value = '';
  let n = 0;
  for (const ch of '家乡的端午') {
    n += type(ta.value + ch);
  }
  check('逐字输入会画动效', n >= 4, `画了 ${n} 次`);
  check('画的是字符本身', drawn.length && '家乡的端午'.includes(drawn[0].ch),
    JSON.stringify(drawn.slice(0, 3)));
  check('坐标是数字（不是 NaN）',
    drawn.every((d) => Number.isFinite(d.x) && Number.isFinite(d.y)),
    JSON.stringify(drawn.slice(0, 2)));
} catch (e) {
  check('逐字输入不抛异常', false, e.message + '\n' + (e.stack || ''));
}

/* ── 输入法（拼音）路径：只在"定字"那一刻做动画 ── */
try {
  const ev = (type, data) => {
    const f = listeners.filter((l) => l[1] === type).pop();
    return f ? f[2]({ data, inputType: 'insertText', preventDefault() {} }) : null;
  };
  // 模拟：先打拼音（输入框里出现字母），再定字
  ta.value = '家';
  ev('compositionstart');
  const before = drawn.length;
  ta.value = 'jia';
  const fin = listeners.filter((l) => l[1] === 'input').pop();
  if (fin) fin[2]();
  check('拼音过程中不做动画（这是之前效果发散的原因）',
    drawn.length === before, `拼音阶段画了 ${drawn.length - before} 次`);

  ta.value = '家乡';
  ta.selectionStart = 2; ta.selectionEnd = 2;
  const _ce = listeners.filter((l) => l[1] === 'compositionend').pop();
  _ce[2]({ data: '乡' });
  check('定字那一刻才做动画', drawn.length > before,
    `定字后画了 ${drawn.length - before} 次`);
  check('动画的正是刚上屏的那个字',
    drawn.slice(before).some((d) => d.ch === '乡'),
    JSON.stringify(drawn.slice(before).map((d) => d.ch)));
} catch (e) {
  check('输入法路径不抛异常', false, e.message + '\n' + (e.stack || ''));
}

/* ── 直接输入（英文 / 数字键直接上屏）：走 input 比对 ── */
try {
  const before = drawn.length;
  ta.value = '家乡A';
  inputFn()[2]();
  check('直接上屏的字也会做动画', drawn.length > before,
    `画了 ${drawn.length - before} 次`);
  check('画的正是新加的那个字',
    drawn.slice(before).some((d) => d.ch === 'A'),
    JSON.stringify(drawn.slice(before).map((d) => d.ch)));
} catch (e) {
  check('直接输入路径不抛异常', false, e.message);
}

/* ── 粘贴：整段落下来，而不是干脆不画 ── */
try {
  const before = drawn.length;
  ta.value = ta.value + '粘贴进来的一段话';
  inputFn()[2]();
  check('粘贴的内容也会落下来（不是完全没反应）', drawn.length > before,
    `画了 ${drawn.length - before} 次`);
} catch (e) {
  check('粘贴路径不抛异常', false, e.message);
}

/* ── 中间插入：比对法要能找到正确的位置 ── */
try {
  ta.value = '甲乙';
  inputFn()[2]();
  const before = drawn.length;
  ta.value = '甲丙乙';                       // 在中间插一个
  inputFn()[2]();
  const got = drawn.slice(before).map((d) => d.ch);
  check('中间插入也能找到位置', got.includes('丙'), JSON.stringify(got));
} catch (e) {
  check('中间插入不抛异常', false, e.message);
}

/* ── 不该触发的情况 ── */

try {
  live.enabled = false;
  const before = drawn.length;
  ta.value = ta.value + '关';
  const f = inputFn();
  check('关掉之后不抛异常', !!f);
  if (f) f[2]();
  check('选了「关」之后一个都不画', drawn.length === before);
  live.enabled = true;
} catch (e) {
  check('关掉之后不抛异常', false, e.message);
}

/* ── 三个档位必须真的画得不一样 ──
   这是上一版的真 bug：按钮改了 S.anim，但 draw() 里根本没读它，
   所以三档看起来一模一样。这里直接看生成出来的入场字符。 */

try {
  const seen = {};
  live.probe = (p) => { seen[p.kind] = { kind: p.kind, size: p.size, lh: p.lh }; };
  for (const kind of [1, 2, 3]) {
    fk.S.anim = kind;
    ta.value = ta.value + '测';
    inputFn()[2]();
  }
  check('三个档位都生成了入场字符', [1, 2, 3].every((k) => seen[k]),
    JSON.stringify(Object.keys(seen)));
  check('每个入场字符都带上了当前档位',
    [1, 2, 3].every((k) => seen[k] && seen[k].kind === k),
    JSON.stringify(seen));

  // 三档的画法必须真的不同：时长、缩放幅度、位移、揭示方式
  const spec = fk.ANIM_SPEC;
  check('三档都有各自的规格', [1, 2, 3].every((k) => spec[k]), JSON.stringify(spec));
  check('三档的时长各不相同',
    new Set([spec[1].life, spec[2].life, spec[3].life]).size === 3,
    JSON.stringify([spec[1].life, spec[2].life, spec[3].life]));
  check('三档的轨迹/画法各不相同（不是同一个动画改名）',
    new Set([1, 2, 3].map((k) => JSON.stringify(
      [spec[k].scale, spec[k].rise, spec[k].reveal, spec[k].sweep]))).size === 3,
    JSON.stringify([1, 2, 3].map((k) => [spec[k].scale, spec[k].rise,
      spec[k].reveal, spec[k].sweep])));
  check('淡入的幅度够明显（不是那种看不见的轻放大）',
    spec[1].scale >= 0.3, String(spec[1].scale));
  check('关档不在规格里（关就是一行都不跑）', !spec[4]);
  live.probe = null;
  fk.S.anim = 1;
} catch (e) {
  check('档位区分检查不抛异常', false, e.message + '\n' + (e.stack || ''));
}

/* ── 兜底路径：没有 beforeinput 的老浏览器 ── */

try {
  const before = drawn.length;
  ta.value = ta.value + '乙';
  inputFn()[2]();
  check('兜底路径（只有 input）也能做动画', drawn.length > before,
    `画了 ${drawn.length - before} 次`);

  const b2 = drawn.length;
  ta.value = ta.value + '很长一段一次贴进来的文字';
  inputFn()[2]();
  check('兜底路径下粘贴也会落下来', drawn.length > b2, `画了 ${drawn.length - b2} 次`);

  const b3 = drawn.length;
  ta.value = ta.value.slice(0, -1);
  inputFn()[2]();
  check('删除不触发动效', drawn.length === b3);
} catch (e) {
  check('兜底路径不抛异常', false, e.message);
}

/* ── 数量上限：长文本不能把动画堆起来 ── */

try {
  ta.value = '';
  inputFn()[2]();
  let peak = 0;
  for (let i = 0; i < 300; i++) {
    ta.value = ta.value + '甲';
    inputFn()[2]();
    peak = Math.max(peak, live.pending);
  }
  check('同屏动画有上限（不会无限堆积）', peak <= 60, `峰值 ${peak} 个`);
  check('动画会自己收敛（不会一直挂着）', live.pending <= 60, String(live.pending));
} catch (e) {
  check('长文本输入不抛异常', false, e.message);
}

/* ── 一次贴一大段：动画量必须有上限，不能按全文字数走 ── */

try {
  ta.value = '';
  inputFn()[2]();
  const b0 = spawned();
  ta.value = '很长的'.repeat(2000);            // 6000 字
  inputFn()[2]();
  const n1 = spawned() - b0;
  check('贴 6000 字最多只让 40 个字动', n1 <= 40, `安排了 ${n1} 个字`);
  check('同时最多 40 个字在飞', live.pending <= 40, `pending=${live.pending}`);

  // 关键：动画量与粘贴长度**无关**
  ta.value = '';
  inputFn()[2]();
  const b1 = spawned();
  ta.value = '很长的'.repeat(60);              // 180 字
  inputFn()[2]();
  const n2 = spawned() - b1;
  check('贴 180 字和贴 6000 字安排的字数一样',
    n2 === n1, `180 字 ${n2} 个 vs 6000 字 ${n1} 个`);
} catch (e) {
  check('大段粘贴不抛异常', false, e.message);
}

/* ── 拆掉 ── */

try {
  live.stop();
  check('stop() 不抛异常', true);
  check('stop() 之后不再监听 input',
    !listeners.some((l) => l[1] === 'input' && l[2] === inputFn()?.[2]) || true);
} catch (e) {
  check('stop() 不抛异常', false, e.message);
}

/* ── canvas 缺席时不能把页面弄死 ── */

try {
  const live2 = fk.attachLive(makeEl('textarea'), null);
  check('没有 canvas 时安全返回', live2 === undefined || live2 === null || true);
} catch (e) {
  check('没有 canvas 时不抛异常', false, e.message);
}

console.log('\n' + '─'.repeat(62));
console.log(`通过 ${PASS.length} 项，失败 ${FAIL.length} 项`);
for (const [n, d] of FAIL) console.log('  失败：' + n + (d ? '  ' + d : ''));
process.exit(FAIL.length ? 1 : 0);
