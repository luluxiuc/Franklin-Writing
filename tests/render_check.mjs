/* ═══════════════════════════════════════════════════════════════
   render_check — 在 Node 里真正执行前端渲染代码。

   静态检查（tests/test_frontend.py）只看得出"元素名对不对"，
   看不出渲染函数会不会抛异常。而前端一旦抛异常，用户看到的就是一张白卡片，
   只有控制台里有一条红字。这里用最小 DOM 影子把 app.js 跑起来，
   拿**真实服务返回的数据**把每个页面各渲染一遍。

   重点检查：
     · 写作阶段的数据和页面里，原文一个字都不许有
     · 逐句提示：一句原文一条提示，条数与句数对得上
     · 对照页是逐句配对的（原文一句 / 你写的那一句）

   用法：node tests/render_check.mjs [http://127.0.0.1:8137]
   需要服务在跑（python app/fk_server.py --no-browser --quiet）
   ═══════════════════════════════════════════════════════════════ */
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.join(HERE, '..');
const BASE = process.argv[2] || 'http://127.0.0.1:8137';

const PASS = [], FAIL = [];
function check(name, ok, detail = '') {
  (ok ? PASS : FAIL).push([name, detail]);
  console.log((ok ? '  [OK] ' : '  [!!] ') + name + (!ok && detail ? '  — ' + detail : ''));
}

/* ─────────────── 最小 DOM 影子 ─────────────── */

const html = fs.readFileSync(path.join(ROOT, 'app', 'web', 'index.html'), 'utf8');
const ids = new Set([...html.matchAll(/id="([^"]+)"/g)].map((m) => m[1]));
const classes = new Set([...html.matchAll(/class="([^"]+)"/g)]
  .flatMap((m) => m[1].split(/\s+/)).filter(Boolean));

const missing = [];
const created = new Map();

function makeEl(id = '') {
  const kids = new Map();
  const el = {
    id, dataset: {}, style: {}, value: '', children: [],
    classList: {
      _s: new Set(),
      add(...c) { c.forEach((x) => this._s.add(x)); },
      remove(...c) { c.forEach((x) => this._s.delete(x)); },
      toggle(c, on) { if (on === undefined) on = !this._s.has(c); on ? this._s.add(c) : this._s.delete(c); },
      contains(c) { return this._s.has(c); },
    },
    _html: '',
    get innerHTML() { return this._html; },
    set innerHTML(v) {
      this._html = String(v);
      for (const m of String(v).matchAll(/id="([^"]+)"/g)) {
        if (!kids.has(m[1])) kids.set(m[1], makeEl(m[1]));
        created.set(m[1], kids.get(m[1]));
      }
    },
    get textContent() { return this._text || ''; },
    set textContent(v) { this._text = String(v); },
    setAttribute() {}, getAttribute() { return null; },
    appendChild(c) { this.children.push(c); return c; },
    querySelector(sel) { return pick(sel, this) || makeEl(); },
    querySelectorAll() { return []; },
    addEventListener() {}, removeEventListener() {},
    setSelectionRange() {}, focus() {}, closest() { return null; },
    getBoundingClientRect() { return { top: 0, left: 0, width: 0, height: 0 }; },
  };
  return new Proxy(el, {
    get(t, k) {
      if (k in t) return t[k];
      if (k === 'scrollTop' || k === 'scrollHeight' || k === 'offsetTop') return 0;
      return function () { return null; };   // 未知方法给空实现，别让影子 DOM 误报
    },
    set(t, k, v) { t[k] = v; return true; },
  });
}

const byId = new Map([...ids].map((i) => [i, makeEl(i)]));

function pick(sel, root) {
  if (typeof sel !== 'string') return null;
  if (sel.startsWith('#')) {
    const id = sel.slice(1);
    if (root && root.id === id) return root;
    let found = byId.get(id) || created.get(id);
    if (!found && ids.has(id)) { found = makeEl(id); byId.set(id, found); }
    if (!found) { missing.push(sel); return null; }
    return found;
  }
  if (sel.startsWith('.')) {
    if (!classes.has(sel.slice(1))) missing.push(sel);
    return makeEl();
  }
  return makeEl();
}

const document = {
  querySelector: (s) => pick(s, null),
  querySelectorAll: () => [],
  createElement: () => makeEl(),
  getElementById: (i) => byId.get(i) || created.get(i) || null,
  addEventListener() {},
  body: makeEl('body'),
  documentElement: Object.assign(makeEl('html'), { dataset: {} }),
};

const store = new Map();
// host 必须跟着 BASE 走：runner 会在首选端口被占用时自动换端口，
// 写死 8137 会让前端在拼 URL 时对不上（app.js 会用 location 拼接口地址）。
const HOST = BASE.replace(/^https?:\/\//, '').replace(/\/$/, '');
const loc = { hash: '#/shelf', protocol: 'http:', href: BASE + '/', origin: BASE,
              host: HOST, pathname: '/' };
const sb = {
  document,
  window: { addEventListener() {}, scrollTo() {}, location: loc },
  location: loc,
  localStorage: { getItem: (k) => (store.has(k) ? store.get(k) : null),
                 setItem: (k, v) => store.set(k, String(v)) },
  sessionStorage: { getItem: () => null, setItem() {} },
  fetch: (...a) => fetch(...a),
  setTimeout, clearTimeout, setInterval, clearInterval,
  console, URL, URLSearchParams, confirm: () => false,
  encodeURIComponent, decodeURIComponent, JSON, Math, Date, Promise, Number,
  String, Array, Object, Error, isNaN, parseInt, parseFloat, RegExp, Set, Map,
};
sb.globalThis = sb;

/* 把整个文件包成函数跑，末尾取回要测的渲染函数 */
const code = fs.readFileSync(path.join(ROOT, 'app', 'web', 'app.js'), 'utf8');
vm.createContext(sb);
let fk = null, loadError = null;
try {
  fk = vm.runInContext(`(function(){
${code}
;return { S, esc, escNL, plainLen, fmtClock, fmtDur, highlight,
  shelfHTML, shelfLead, bookHTML, readerHTML, compareHTML, pairUp, splitSents,
  factSheetLocal, STAGE, nextTarget, nextLabel };
})()`, sb, { filename: 'app.js' });
} catch (e) { loadError = e; }

if (!fk || typeof fk.compareHTML !== 'function') {
  console.log('  [!!] app.js 在最小 DOM 环境下没能加载出渲染函数');
  console.log('       ' + (loadError ? loadError.message : '（没有异常）'));
  if (loadError && loadError.stack) console.log(loadError.stack.split('\n').slice(0, 6).join('\n'));
  process.exit(1);
}
check('app.js 能在最小 DOM 环境下完整加载', true);

/* ─────────────── 造真实数据 ─────────────── */

// 每段内容都不同：内容相同的段会命中缓存（这是对的），但那样测不出批量与逐段的行为
const paras = [];
for (let i = 1; i <= 8; i++) {
  paras.push(`第${i}节　甲${i}

家乡的端午，很多风俗和外地一样，这是第${i}种说法。系百索子。五色的丝线拧成小绳，系在手腕上。丝线是掉色的，洗脸时沾了水，手腕上就印得红一道绿一道的。

做香角子。丝丝缠成小粽子，里头装了香面，一个一个串起来，挂在帐钩上。贴五毒。红纸剪成五毒，贴在门槛上。这是第${i}家。`);
}
const BOOK = paras.join('\n\n') + '\n';

async function call(p, opts = {}) {
  const clean = p.replace(/^\/?api\//, '');
  const r = await fetch(BASE + '/api/' + clean, {
    method: opts.method || (opts.body ? 'POST' : 'GET'),
    headers: { 'Content-Type': 'application/json' },
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  const t = await r.text();
  let d = null;
  try { d = JSON.parse(t); } catch { /* 静态文件 */ }
  return { status: r.status, data: d, text: t };
}

const flat = (s) => String(s || '').replace(/[，。！？；：、“”"'（）《》…—\s]/g, '');
const gramsOf = (s, n) => {
  const b = flat(s), out = [];
  for (let i = 0; i + n <= b.length; i++) out.push(b.slice(i, i + n));
  return out;
};

console.log('\n服务：' + BASE + '\n');

// 先配好模型。渲染测试跑在 tests/serve_stub.py 上，那里的模型是假的，
// 但接口链路是真的——提示的条数、缓存、账目都照常走。
await call('settings', { body: {
  provider: 'deepseek', base_url: 'https://stub.invalid/v1',
  model: 'stub-model', api_key: 'sk-stub-0123456789' } });

// 清掉上一次跑测可能留下的书，否则计数类的断言会飘
try {
  const pre = await call('shelf');
  for (const b of pre.data.books) {
    await fetch(`${BASE}/api/books/${encodeURIComponent(b.id)}?confirm=${encodeURIComponent(b.id)}`,
      { method: 'DELETE' });
  }
} catch (e) { /* 空的就算了 */ }

// ── 空书架
try {
  const h0 = fk.shelfHTML({ books: [], counts: { books: 0, passages: 0, done: 0, written: 0 },
                            settings: {} });
  check('空书架渲染出引导文案', h0.includes('先放一本书进来'), h0.slice(0, 120));
  check('空书架有导入入口', h0.includes('btn-add2'));
} catch (e) { check('空书架渲染不抛异常', false, e.message); }

// ── 导入
const imp = await call('books', { body: { title: '渲染测试书', author: '某人', text: BOOK,
                                          passage_chars: 150 } });
if (imp.status !== 200) {
  console.log('  [!!] 造测试数据失败：' + imp.text.slice(0, 200));
  process.exit(1);
}
const bid = imp.data.book.id;
const sizes = imp.data.book.chapters.flatMap((c) => c.passages.map((p) => p.chars));
check('导入切出了多段', imp.data.book.counts.total >= 3, String(imp.data.book.counts.total));
check('每一段都不超过 400 字（分段要有兜底）',
  sizes.every((n) => n <= 400), JSON.stringify(sizes));

// ── 超长无标点粘贴：这是实测抓到的 bug，必须一直是好的
try {
  const big = '端午的鸭蛋向来有名' .repeat(200);
  const r = await call('books', { body: { title: '无标点长文', text: big, passage_chars: 300 } });
  const sz = r.data.book.chapters.flatMap((c) => c.passages.map((p) => p.chars));
  check('2000 字无标点的粘贴会被切成多段',
    r.data.book.counts.total >= 5 && sz.every((n) => n <= 400),
    JSON.stringify(sz));
  await fetch(`${BASE}/api/books/${encodeURIComponent(r.data.book.id)}?confirm=${encodeURIComponent(r.data.book.id)}`,
    { method: 'DELETE' });
} catch (e) { check('超长粘贴检查不抛异常', false, e.message); }

// ── 书架
try {
  const shelf = await call('shelf');
  const h = fk.shelfHTML(shelf.data);
  check('书架渲染出书名', h.includes('渲染测试书'));
  check('书架显示总段数与进度', h.includes('练完'));
  check('书架有进书的入口', h.includes(`data-id="${bid}"`));
  check('书架文案不含评价性措辞', !/评分|得分|相似度|保真|等级/.test(h));
  check('书架引导语能生成', fk.shelfLead(shelf.data).includes('段'));
} catch (e) { check('书架渲染不抛异常', false, e.message + '\n' + (e.stack || '')); }

// ── 书内目录
let book = (await call('books/' + bid)).data;
try {
  const h = fk.bookHTML(book);
  check('书内目录渲染出书名与统计', h.includes('渲染测试书') && h.includes('节'));
  check('书内目录列出每一段', (h.match(/class="toc-row"/g) || []).length >= 3,
    String((h.match(/class="toc-row"/g) || []).length));
  check('书内目录每段显示阶段', h.includes('未读'));
  check('书内目录有"继续"按钮', h.includes('b-next'));
  check('书内目录不出现正文（只给规模）',
    !h.includes('很多风俗和外地一样'), '正文漏进目录了');
  check('下一段能算出来', !!fk.nextTarget(book));
} catch (e) { check('书内目录渲染不抛异常', false, e.message + '\n' + (e.stack || '')); }

// ── 读书页
const ch1 = (await call(`books/${bid}/chapters/1`)).data;
try {
  const h = fk.readerHTML(ch1);
  check('读书页渲染出整节正文', h.includes('很多风俗和外地一样'));
  check('读书页有"读完了去写"入口', h.includes('r-done'));
  check('读书页说了为什么要搁一会儿', h.includes('合上') || h.includes('搁几分钟'));
  check('读书页列出这一节的每一段',
    (h.match(/class="toc-row"/g) || []).length === ch1.passages.length);
} catch (e) { check('读书页渲染不抛异常', false, e.message + '\n' + (e.stack || '')); }

// ── 开始练习
await call('settings', { body: { delay_min: 5 } });
await call(`practice/${bid}/1/1/start`, { body: { read_seconds: 60 } });
const wv = (await call(`practice/${bid}/1/1/write`)).data;
const passageText = ch1.passages[0].text;
const sents = fk.splitSents(passageText);

// ── 写稿数据：原文一个字都不许出现
try {
  check('写稿数据带句数（一句一条提示的基准）',
    wv.passage.sentences === sents.length,
    `接口说 ${wv.passage.sentences} 句，实际切出 ${sents.length} 句`);
  const blob = JSON.stringify(wv);
  const leaked = gramsOf(passageText, 14).filter((g) => blob.includes(g));
  check('写稿数据里没有任何 14 字以上的原文片段', leaked.length === 0,
    JSON.stringify(leaked.slice(0, 3)));
  check('写稿数据里没有 source 字段', !('source' in wv));
  check('等待中给出了剩余时间', wv.remaining > 0, String(wv.remaining));
  check('倒计时格式正确', fk.fmtClock(300) === '05:00' && fk.fmtClock(9) === '00:09');
} catch (e) { check('写稿数据检查不抛异常', false, e.message); }

// ── 逐句提示：一句一条，与句数一致
// 注意：拿不到提示时必须逐条报失败，不能让 .length 抛异常把整套检查打断。
// 之所以专门处理：本地开发时 8137 端口上可能跑着一个**真**服务（连的是真模型），
// 那时这个接口会失败，而一个 TypeError 会掩盖掉真正的原因（见 run_all.py 的端口检查）。
const hh = (await call(`practice/${bid}/1/1/hints`, { body: {} })).data;
const hints = (hh && Array.isArray(hh.hints)) ? hh.hints : null;
check('能拿到逐句提示', !!hints, JSON.stringify(hh).slice(0, 200));
if (!hints) {
  console.log('  [!!] 拿不到提示，后面的提示相关检查会一并失败。');
  console.log('       先确认 8137 上跑的是 tests/serve_stub.py（假模型），不是你自己的服务。');
}
check('一句一条，条数等于句数',
  !!hints && hints.length === hh.n_sent && hh.n_sent === sents.length,
  hints ? `句 ${hh.n_sent} 条 ${hints.length}，本地切出 ${sents.length}`
        : `拿不到提示（接口返回 ${JSON.stringify(hh).slice(0, 120)}）`);
check('每条带句子编号，从 1 连续',
  !!hints && hints.every((h, i) => h.no === i + 1),
  hints ? JSON.stringify(hints.map((h) => h.no)) : '拿不到提示');
check('提示里不含原文 14 字以上片段',
  !!hints && gramsOf(passageText, 14).every((g) => !JSON.stringify(hints).includes(g)),
  '拿不到提示时不通过（而不是跳过）');
check('用了模型的 token 账被记下', !!(hh && hh.usage && hh.usage.in > 0), JSON.stringify(hh && hh.usage));

// ── 再打开写稿页：提示应该已经在里面了（"提前备好"的意义）
const wv2 = (await call(`practice/${bid}/1/1/write`)).data;
check('写稿页一打开就带着提示（不用等模型）',
  wv2.hints_cached && wv2.hints.length === sents.length, String(wv2.hints.length));
try {
  const blob = JSON.stringify(wv2);
  const leaked = gramsOf(passageText, 14).filter((g) => blob.includes(g));
  check('带了提示的写稿数据里仍然没有原文', leaked.length === 0,
    JSON.stringify(leaked.slice(0, 3)));
} catch (e) { check('带提示的写稿数据检查不抛异常', false, e.message); }

// 这一轮完成之后用于"另一段也能记笔记"的那一段（先挑好，下面要用）
const _b = (await call('books/' + bid)).data;
const _c = _b.chapters[1] || _b.chapters[0];
const _p = _c.passages[1] || _c.passages[0];
const task = { ch: _c.no, p: _p.no };

// ── 单句接口：只给那一句
try {
  const s1 = (await call(`practice/${bid}/1/1/sentence/2`, { body: {} })).data;
  check('单句接口返回第 2 句', s1 && s1.no === 2, JSON.stringify(s1).slice(0, 120));
  check('单句接口给出总句数', s1.total === sents.length, String(s1.total));
  check('单句接口只给一句（不含整段）',
    flat(s1.sentence).length < flat(passageText).length * 0.6,
    `句 ${flat(s1.sentence).length} 字 / 段 ${flat(passageText).length} 字`);
  const bad = await call(`practice/${bid}/1/1/sentence/999`, { body: {} });
  check('越界的句号被拒', bad.status === 404, String(bad.status));
} catch (e) { check('单句接口检查不抛异常', false, e.message); }

// ── 单句对照要能标出"你抓住了哪些词"
try {
  const sheet = fk.factSheetLocal('家乡的端午，很多风俗和外地一样。',
    '家乡的端午，风俗一样。');
  check('单句里的词比对能算出命中的词', sheet.hit.includes('家乡'), JSON.stringify(sheet));
  check('单句里的词比对能算出漏掉的词', sheet.miss.length >= 1, JSON.stringify(sheet.miss));
  const h = fk.highlight('家乡的端午，风俗一样。', sheet.hit);
  check('单句对照里命中的词会被标出来', (h.match(/<mark>/g) || []).length >= 1, h);
} catch (e) { check('单句词比对不抛异常', false, e.message); }

// ── 交稿 → 对照
const draft = sents.slice(0, 3).join('') + '做香角子，挂在帐钩上。';
await call('settings', { body: { delay_min: 0 } });
await call(`practice/${bid}/1/1/skip-wait`, { body: {} });
const cmp = (await call(`practice/${bid}/1/1/submit`, {
  body: { draft, prompt_used: true, write_seconds: 240 },
})).data;
check('交稿拿到了对照数据', !!cmp && !!cmp.source, JSON.stringify(cmp).slice(0, 160));

// 逐句配对的纯函数。关键是漏写一句之后不能整体错位。
try {
  const pairs = fk.pairUp('甲一。甲二。甲三。甲四。', '甲一。甲三。甲四。');
  check('配对：按句号切开原文', pairs.filter((p) => p.no != null).length === 4,
    JSON.stringify(pairs.map((p) => p.src)));
  check('配对：漏写的那一句标出来，其余各就各位',
    pairs[1].mine === '' && pairs[1].missing === true
    && pairs[2].mine === '甲三。' && pairs[3].mine === '甲四。',
    JSON.stringify(pairs.map((p) => p.mine)));
  const extra = fk.pairUp('甲一。甲二。', '甲一。多出来的一句。甲二。');
  check('配对：多写的句子单独标出来，不挤掉后面的',
    extra.some((p) => p.extra && p.mine === '多出来的一句。')
    && extra.filter((p) => p.same).length === 2,
    JSON.stringify(extra));
  check('配对：两句完全对不上时不会瞎配',
    fk.pairUp('甲一。', '乙九。').every((p) => !p.same),
    JSON.stringify(fk.pairUp('甲一。', '乙九。')));
  check('切句把没有句号的尾巴也算一句',
    fk.splitSents('甲。乙').length === 2, JSON.stringify(fk.splitSents('甲。乙')));
} catch (e) { check('配对函数不抛异常', false, e.message); }

try {
  const h = fk.compareHTML(cmp);
  check('对照页同时给出原文与我的稿子',
    h.includes('很多风俗和外地一样') && h.includes('做香角子'));
  check('对照页是逐句配对的（有 原文 / 你写的 两栏）',
    (h.match(/class="pair"/g) || []).length === sents.length
    && h.includes('>原文<') && h.includes('>你写的<'),
    `pair=${(h.match(/class="pair"/g) || []).length} 句=${sents.length}`);
  check('每一句上面挂着当时那条提示',
    hh.hints.every((x) => h.includes(x.hint.slice(0, 6))),
    JSON.stringify(hh.hints.map((x) => x.hint.slice(0, 6))));
  const marks = (h.match(/<mark>/g) || []).length;
  check('你写出来的词被标出来', marks >= 1,
    `mark=${marks} hit=${JSON.stringify((cmp.facts || {}).hit)}`);
  check('列出"原文里有、你没写到的片段"',
    h.includes('原文里有、你没写到的片段') && (cmp.facts.segments || []).length >= 1,
    JSON.stringify((cmp.facts || {}).segments));
  check('对照页没有比率、没有分数',
    !/命中率|覆盖率\s*[:：]\s*\d|相似度|评分|得分/.test(h));
  check('对照页说了未出现不等于写得不好', h.includes('不等于写得不好'));
  check('对照页要求写下观察', h.includes('id="obs"') && h.includes('obs-save'));
  check('对照页有导出入口', h.includes('id="export"'));
} catch (e) { check('对照页渲染不抛异常', false, e.message + '\n' + (e.stack || '')); }

// ── 高亮
try {
  check('高亮：命中的词被 mark 包住',
    (fk.highlight('丝线拧成小绳，系在手腕上。', ['丝线', '手腕']).match(/<mark>/g) || []).length === 2);
  check('高亮：互相包含的词不会重复标',
    (fk.highlight('城隍庙送来的符。', ['城隍庙', '城隍庙送']).match(/<mark>/g) || []).length === 1);
  check('高亮：同一个词出现两次会标两次',
    (fk.highlight('手腕上有印，手腕上就红。', ['手腕']).match(/<mark>/g) || []).length === 2);
  check('高亮：不标不存在的词',
    (fk.highlight('我写了一句。', ['不存在的东西']).match(/<mark>/g) || []).length === 0);
  check('高亮：转义了 HTML',
    fk.highlight('<b>不该生效</b>', []).includes('&lt;b&gt;'));
} catch (e) { check('高亮函数不抛异常', false, e.message); }

// ── 完成态
await call(`practice/${bid}/1/1/observe`, { body: { observation: '第二句我把因果省了。' } });
const cmp2 = (await call(`practice/${bid}/1/1/compare`)).data;
check('练完之后还能翻回来看这一轮', !!cmp2 && !!cmp2.source,
  JSON.stringify(cmp2).slice(0, 120));
try {
  const h = fk.compareHTML(cmp2);
  check('完成态回显了观察原文', h.includes('第二句我把因果省了'));
  check('完成态不再要求写观察', !h.includes('id="obs-save"'));
  check('完成态给了"练下一段"', h.includes('id="next"'));
} catch (e) { check('完成态渲染不抛异常', false, e.message + '\n' + (e.stack || '')); }


// ── 笔记：跟着书走，逐句的和整段的都在同一个清单里
//
// 注意：上面"完成态"那一步已经写下一条整段笔记，所以这里不是从 0 开始——
// 那条正是"我的观察"合并进来的证据。
try {
  const nb0 = (await call(`books/${bid}/notes`)).data;
  check('整段的观察已经以笔记的形式存在',
    nb0.count === 1 && nb0.notes[0].scope === 'passage',
    JSON.stringify(nb0).slice(0, 140));
  check('那条整段笔记带着当时的稿子', !!nb0.notes[0].mine,
    JSON.stringify(nb0.notes[0]).slice(0, 140));

  const s2 = (await call(`practice/${bid}/1/1/sentence/2`, { body: {} })).data;
  const saved = await call(`practice/${bid}/1/1/note`, { body: {
    text: '第二句我把因果省了。', sent_no: 2,
    sentence: s2.sentence, mine: '系百索子', hint: hh.hints[1].hint } });
  check('能记下这一句的笔记', saved.status === 200 && saved.data.note.text,
    JSON.stringify(saved.data).slice(0, 140));

  const nb = (await call(`books/${bid}/notes`)).data;
  check('逐句笔记和整段笔记在同一个清单里',
    nb.count === 2 && nb.book.id === bid, JSON.stringify(nb).slice(0, 140));
  const one = nb.notes.find((n) => n.scope === 'sentence');
  check('逐句笔记的范围标成 sentence', !!one, JSON.stringify(nb.notes.map((n) => n.scope)));
  check('笔记里存下了原文那一句、你的那一句、当时的提示',
    one.sentence && one.mine && one.hint,
    JSON.stringify(one).slice(0, 160));
  check('笔记带句子编号（能回去找那一句）', one.sent_no === 2,
    String(one.sent_no));

  // 另一段也能记：笔记是整本书的，不是某一段的
  await call(`practice/${bid}/${task.ch}/${task.p}/start`, { body: {} });
  const other = await call(`practice/${bid}/${task.ch}/${task.p}/note`, { body: {
    text: '这一段我也记一条。', sent_no: 1, sentence: '甲。', mine: '乙。' } });
  check('另一段也能记笔记（接口没报错）', other.status === 200,
    `${other.status} ${other.text.slice(0, 160)}`);
  const nb2 = (await call(`books/${bid}/notes`)).data;
  check('不同段落的笔记归到同一本书', nb2.count === 3, String(nb2.count));
  check('笔记按时间倒序（最新的在最前）',
    nb2.notes[0].text === '这一段我也记一条。', nb2.notes[0].text);
} catch (e) { check('逐句笔记链路不抛异常', false, e.message + '\n' + (e.stack || '')); }

// ── 合并：整段笔记进同一个清单（以前是另一个"我的观察"入口）
try {
  const before = (await call(`books/${bid}/notes`)).data.count;
  // 在"另一段"上真走完一轮：交稿 → 记整段笔记
  await call('settings', { body: { delay_min: 0 } });
  await call(`practice/${bid}/${task.ch}/${task.p}/skip-wait`, { body: {} });
  const sub2 = await call(`practice/${bid}/${task.ch}/${task.p}/submit`, { body: {
    draft: '这一段我凭记忆写的一点东西，用来把这一轮走完。' } });
  check('另一段也能走完一轮（交稿）', sub2.status === 200, sub2.text.slice(0, 140));
  const ob = await call(`practice/${bid}/${task.ch}/${task.p}/observe`, { body: {
    observation: '这一段整体上我把节奏写散了。' } });
  check('写完对照能记一条整段笔记', ob.status === 200,
    `${ob.status} ${ob.text.slice(0, 140)}`);

  const nb3 = (await call(`books/${bid}/notes`)).data;
  check('整段笔记进了同一张清单（不再有两个入口）',
    nb3.count === before + 1, `${before} → ${nb3.count}`);
  check('清单里两种范围都在',
    new Set(nb3.notes.map((n) => n.scope)).size === 2,
    JSON.stringify(nb3.notes.map((n) => n.scope)));
  const wide = nb3.notes.find((n) => n.scope === 'passage');
  check('整段那条带上了当时那一稿', wide && wide.mine,
    JSON.stringify(wide).slice(0, 140));
  check('整段那条不带句子编号（它是整段的）', wide.sent_no === 0,
    String(wide.sent_no));
} catch (e) { check('整段笔记链路不抛异常', false, e.message + '\n' + (e.stack || '')); }

// ── 记录：不返回原文
const rec = (await call('records')).data;
try {
  check('记录接口返回了行', rec.rows.length === 2, String(rec.rows.length));
  check('记录行里有稿子、观察、提示',
    rec.rows[0].draft && rec.rows[0].observation && (rec.rows[0].hints || []).length > 0);
  check('记录列表里不含原文（点开那一轮才去取）',
    !Object.prototype.hasOwnProperty.call(rec.rows[0], 'source'),
    Object.keys(rec.rows[0]).join(','));
  const blob = JSON.stringify(rec);
  const leaked = gramsOf(passageText, 14).filter((g) => blob.includes(g));
  check('记录数据里没有任何 14 字以上的原文片段', leaked.length === 0,
    JSON.stringify(leaked.slice(0, 3)));
} catch (e) { check('记录数据检查不抛异常', false, e.message); }

// ── 目录状态
book = (await call('books/' + bid)).data;
try {
  const h = fk.bookHTML(book);
  check('目录里这一段变成"已练完"', h.includes('已练完'));
  check('目录里的完成数对得上（走了两轮）', book.counts.done === 2,
    String(book.counts.done));
  check('剩下没练的段仍是未读',
    (h.match(/>未读</g) || []).length === book.counts.total - 2,
    `未读 ${(h.match(/>未读</g) || []).length} 段，共 ${book.counts.total} 段`);
} catch (e) { check('目录更新后渲染不抛异常', false, e.message); }

// ── 元素引用
check('渲染过程中没有引用不存在的元素', missing.length === 0,
  '缺：' + [...new Set(missing)].join(', '));

// ── 收尾
await call('settings', { body: { delay_min: 3 } });
const del = await fetch(
  `${BASE}/api/books/${encodeURIComponent(bid)}?confirm=${encodeURIComponent(bid)}`,
  { method: 'DELETE' });
check('测试数据已清理', del.status === 200, String(del.status));

console.log('\n' + '─'.repeat(62));
console.log(`通过 ${PASS.length} 项，失败 ${FAIL.length} 项`);
for (const [n, d] of FAIL) console.log('  失败：' + n + (d ? '  ' + d : ''));
process.exit(FAIL.length ? 1 : 0);
