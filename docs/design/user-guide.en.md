[English](user-guide.en.md) · [中文](../设计/工具使用说明.md)

# Franklin Writing

A local writing-practice tool. **Import a book or a passage, read the original, wait a few minutes, rewrite it from memory, then compare it against the original.**

Web UI, running on your own machine. All data stays local. Only one step — "summarise the original into hints" — uses a large model, and it works whether or not you fill in a Key.

---

## How to use it

### 1. Open it

**Windows, easiest: type `fk` anywhere.**

Open a terminal (search "Terminal" in the Start menu, or Win+R and type `cmd`) and run:

```
fk
```

Any directory, no `cd`, no path to remember. If the server is not running it starts it; if it already is, it just opens the page — **and it will not start a second copy**.

> Where that comes from: a small `fk.cmd` in a directory on your PATH, with the project location written into it.
> It is not distributed with the repository (everyone's path differs), so **on a new machine you generate it again**.

**Windows, no command line: double-click `启动.cmd`.** The browser opens by itself.

> That file **must stay pure ASCII**. cmd.exe parses a `.cmd` line by line in the system OEM code page (GBK on a Chinese Windows), so a single Chinese character gets split mid-byte and the leftover bytes are run as commands — the symptom is that **the window flashes and the server never starts**. That bug really happened, which is why its messages are now in English and why a test watches for it (`tests/docs_check.py`, section 4).

**macOS / Linux:**

```bash
./启动.sh
```

**Manual:**

```bash
python app/fk_server.py              # defaults to 127.0.0.1:8137; if the port is taken it walks forward to find one
python app/fk_server.py --port 9000
python app/fk_server.py --data D:\我的书库
```

(`我的书库` means "my library"; that path is only an example.)

Requires Python 3.10 or later. **No other dependencies** — no pip install, no node, and it starts up with no network.

The server only listens on `127.0.0.1`; other machines on the same LAN cannot reach it either.

### 2. First time: fill in a Key (optional)

Click "Settings" in the top right, pick a provider, paste in your API Key.

- Supported: DeepSeek, OpenAI, Tongyi Qianwen, Kimi, Zhipu, OpenRouter, local Ollama, and any OpenAI-compatible endpoint.
- The Key is stored in `app/data/index.json`, only on this machine, and is never uploaded.
- **It works without one too**: you just don't get hint cards, and you write straight from memory. That is actually closer to what Franklin originally did.
- A Key with Chinese characters or spaces mixed in (very common when copying from a web page) is blocked on the spot with an explanation of why,
  instead of waiting until a request fails with an unreadable encoding error.

Click "Test connection" to confirm it goes through. **This is the only place in the whole tool where money is spent**, and it is cheap — see the end of this document.

### 3. Import a book

Click "＋ Import a book" on the shelf. You can:

- enter the path of a local txt / md file;
- or paste the text in directly (a good article you saw on a web page: select, copy, paste).

The tool automatically cuts it into **sections** (reading units) and **paragraphs** (practice units). By default each paragraph is about 300 characters, and this is adjustable.

**While importing, you can prepare the hints ahead of time in the same pass.** At the top of the in-book table of contents there is a line reading "sentence hints 0 / 37 paragraphs prepared" and a
"Prepare ahead" button. Clicking it builds the hints for the whole book in the background, and you can go and read at the same time —
by the time you practise that paragraph the hints are already sitting locally, with no waiting on the model.

Before you press it, it tells you roughly how many tokens it will cost, and above a certain amount it asks for confirmation once more. Not pressing it is perfectly fine too: it builds the hints for a paragraph on the spot when you get to it, and that works just as well.

### 4. Practising one paragraph: four steps

**① Read the original**
Click any paragraph in the in-book table of contents, or start reading from the first section. At this point the original is completely in front of you.

**② Let it sit for a few minutes**
When you finish reading, click "Done reading — go write this paragraph". The original closes and a countdown starts (3 minutes by default; you can change it to anywhere from 0–240 minutes in Settings).

> These few minutes are the key to this method. Write right after reading and what comes out is the text still lingering in your eyes; wait a few minutes and what comes out is what you actually remembered.
>
> While you wait you can go and practise another paragraph — the in-book table of contents shows the state of every paragraph, so by rotating through several paragraphs the waiting time isn't wasted.

**③ Sentence hints on the left, drafting paper on the right, the original nowhere**

When the countdown ends you enter the writing desk. **Not a single character of the original is here.**

On the left are the **sentence hints**: as many hints as the original has sentences, one hint per sentence. For example

```
1  讲家乡端午的几种风俗
2  列举系百索子、做香角子这类做法
3  说符的来历，以及那位道士和作者的关系
```

```
1  the several Dragon Boat Festival customs of the hometown
2  enumerate practices such as tying the hundred-cord and making incense sachets
3  where the charm came from, and the relation between that Daoist priest and the author
```

Why one hint per sentence rather than a few hints summarising the whole paragraph — because this is exactly what Franklin did:
he read an essay, **jotted a short hint for each sentence**, left it a few days, then wrote the whole thing back while looking at those hints.
And what this exercise is meant to train is precisely "writing each sentence well", so the unit of the hint should be the sentence.
A paragraph summary re-organizes the original, and that structure is the model's, not yours.

A hint only gives "what this sentence said". It **gives no wording, no technique, no evaluation**, and the tool checks this mechanically:
**if any hint contains a run of 8 or more characters identical to the original, that hint is dropped** — giving you a sentence of the original
amounts to letting you copy, and practising that way is useless.

You can: use them as a foothold; or click "No hints, write from memory" to turn them off; or click "Regenerate" for another version.
If you can't go on, leave it blank — don't make things up. When you're done, press `Ctrl+Enter` or click "Done — show the comparison".

**To practise sentence by sentence, click "Practise one sentence at a time" at the very top of the hint panel.**
You read one hint, write only that sentence, and the moment you finish it is placed side by side with that sentence of the original — the words you wrote are highlighted,
and below there is also a list of "which words in this sentence you also wrote".

**④ Comparison: look at it sentence by sentence**

The instant you submit, the page turns into a sentence-by-sentence pairing: under **each sentence of the original** sits **the sentence you wrote**,
and above the two hangs the hint from that time.

The pairing is not a naive "sentence n against sentence n" — skip one sentence and everything after it is misaligned, and what is displayed is false information.
So the tool aligns by longest common subsequence: sentences you added and sentences you skipped are marked separately, and the rest line up where they belong.

Below that:

- The words you wrote are highlighted (the ones that are in the original and that you also wrote).
- **Fragments that are in the original and that you did not write** are laid out as they are, with no evaluation.
- To look word by word, expand "by word".

At the end, write one sentence under "the differences I see". One sentence is enough, for example "in the second sentence I dropped the causation", "I joined three short sentences into one long one".
**This goes into this book's notes** — the same place as the notes you write in the single-sentence practice.

---

## Notes: one entry point, attached to the book

Whichever step you write them in, they all go into the same list:

- In the **single-sentence practice**, after finishing the comparison you can record one below — it automatically carries **that sentence of the original, what you wrote, and that hint**.
- The one sentence you write at the end of the **whole-paragraph practice** (previously called "my observations") is also a note, only its scope is marked as "whole paragraph".

Back in the in-book table of contents, **all of this book's notes** are listed below, newest first. Each one is marked as "sentence n" or "whole paragraph",
and with which section and paragraph it belongs to. You can delete them one at a time, or export them to markdown in one click.

> **Why merge the entry points**: previously "my observations" and "sentence notes" were two entry points and two sets of data,
> and you had to remember "where should this thought of mine go". Now there is one place to write and one place to look.
>
> **Why sentence and whole paragraph are still separate**: because they are two different things — "in this sentence I dropped the causation" is something you can act on,
> "I wrote this paragraph's rhythm loosely overall" is another kind of observation. What was merged is the entry point, not the content.

---

## Typing effects on input

In the input boxes of the writing desk and the single-sentence practice, **the characters you type** get one entrance animation.
The four settings are chosen from the small group of "effects" buttons next to the input box: **fade in / rise / write / off**, and your choice is remembered.

The three settings are genuinely three different ways of drawing it, not one animation with different names:

| Setting | Duration | How it is drawn |
| --- | --- | --- |
| Fade in | 280ms | scales up very slightly in place and fades in |
| Rise | 300ms | floats up from below and settles |
| Write | 340ms | wiped out from bottom to top, with a nib that follows along |

**Three key decisions, all of them settled only after actually hitting the pitfalls:**

**One: animate only "settled characters", whatever input method is used.**
When typing Chinese, pinyin letters or candidate words appear in the input box first, and only then settle into one Chinese character.
If you animate on every input event, the effect scatters across a pile of intermediate states — which is exactly why the first version's "effect was not obvious": the direction was backwards. Now it waits for the moment the input method commits a character, or for the character to go straight to screen.

**Two: what animates is the character itself, the one in the input box.**
It settles in place while scaling, so what you see is "this character was just written", not an extra character popping up beside it.

**Three: don't touch the text in the input box.** A canvas is laid over the top, and the font family and size are measured from the input box.
Wrapping every character in an element would destroy the Chinese input method, selection and undo, and it would start stuttering at a thousand characters.

**There are several hard gates on performance** (all of them watched by tests): at most **40 characters** are animated at a time — pasting 6000 characters and pasting 180 characters
schedule the same number of characters, **the amount of animation does not grow with article length**; there is a cap on characters on screen at once; deleting and moving the cursor triggers nothing;
and once "off" is selected, not one line of animation code runs.

---

## How sentence hints save money

This deserves its own section, because "calling a large model" is the easiest thing to turn into a black hole that quietly burns money.

**One: the same piece of text is generated only once.**
The cache key is **the hash of the original content + the model name + the prompt version** — **independent** of which book this text is in, or which section and paragraph. Therefore:

- the second time the same piece of text is needed, it is read locally and not a single call happens;
- if one paragraph in a book repeats another (poetry, a recurring sentence pattern), it is done only once;
- switching models invalidates the old cache (different models phrase things differently anyway, and this is intentional);
- changing the prompt invalidates it as well (the version number is written into the cache key), and you don't need to clear anything by hand.

The cache lives in `app/data/summaries.json`, plain text. Deleting it does not affect the originals or your drafts.

**Two: if it can be done ahead of time, there is nothing to wait for.**
"Prepare ahead" builds the hints for the whole book in the background (concurrency 2 by default, adjustable with the environment variable
`FK_LLM_CONCURRENCY`; for endpoints with a small free quota, set it to 1). By the time you practise that paragraph,
the hints are already local — **you don't wait on the model while practising**, and that is the main difference in how it feels.

**Three: the number of hints is decided by the number of sentences, and each hint's length is capped.**

One hint corresponds to one sentence of the original, so **the number of hints is not up to the model**: as many sentences as the original has, that many hints
(if the model gives fewer, this is reported honestly as a mismatch; if it gives more, the extras are truncated). The per-hint character cap:

| Sentences in this paragraph | Max characters per hint |
| --- | --- |
| ≤ 4 sentences | 22 |
| ≤ 8 sentences | 18 |
| More | 15 |

Output tokens are capped directly by "number of sentences × per-hint cap". An original longer than 2200 characters is truncated first —
beyond that, the extra characters mostly just add cost and do nothing to help you "remember what this paragraph was about".

**Four: do the arithmetic first, then spend.**
Before "Prepare ahead" it shows "how many paragraphs are left to do, roughly how many tokens", and when the amount is large it asks for confirmation once more.
The estimate is converted from Chinese characters and is explicitly labeled an **estimate** — it exists only so that you have a sense of the scale.

**Five: the ledger records only real numbers.**
What the Settings page shows is the `usage` **reported back** by the provider (input/output tokens, number of calls, number of hits).
If it cannot be obtained, 0 is recorded with a separate explanation: **no estimating, no pretending to know**. You can hold it directly against your bill.

**Six: hints where the model copied the original are removed.**
The prompt explicitly requires "never reuse the words and phrases of the original", but the model occasionally still cuts corners and carries a short clause of the original into a hint.
Before writing to the cache, the tool mechanically checks **hint by hint**: **if any hint contains a run of 8 or more characters identical to the original,
that hint is removed** (only that one, nothing else is dragged in with it). If not one is left, it regenerates once
(at most once — there is no point spending money on the model's stubbornness); if both attempts are copying, you get no hints at all —
better to have you write purely from memory than to stuff the original's sentences back at you.

This is not only about saving money: once a hint gives you a sentence from the original, you are no longer writing from memory, and the exercise is void.

**Seven: short paragraphs are skipped.**
Paragraphs of fewer than 40 characters skip batch generation: hints for that little content are not worth it, and you would remember it anyway.

---

## What it does not do

- **It does not score.** No score, no similarity, no "does it resemble the author", no ranking, no grade.
- **It does not evaluate your draft.** It does not say what should be changed and gives no advice.
- **It does not write for you.** Apart from pairing each sentence with one hint, it generates no sentence at all.
- **It does not show you "how much you have improved".** It only lays out the raw record; you read the pattern yourself.

The comparison page does exactly one thing: it puts the two texts and the result of a mechanical comparison in front of you. The judgment is yours.

---

## Where the data is

All in `app/data/`:

```
app/data/
  index.json        book list, every round's draft, observations, notes, settings (including the API Key)
  index.json.bak    the previous version; if something gets corrupted you can roll back
  texts/<书id>.txt  the original text of each book, one file per book
```

It is all plain text. You can open it, copy it, back it up; move the whole `app/data` to another machine and you can carry on.

**Delete this directory = nothing whatsoever is left behind by this tool.**

Each practice round can also be exported on its own as markdown ("export this round" on the comparison page), containing the sentence hints, the original, your draft and your observations.

---

## Tests

```bash
python tests/run_all.py
```

| Suite | What it checks |
| --- | --- |
| Data layer | splitting is reversible (not one character of the original is lost), paragraphing has a fallback, archive read/write, the state machine |
| Hint cards | whether the per-sentence count lines up, cache hits, the truthfulness of the ledger, batch generation, how a wrong Key ends, the copy check |
| Service layer | end-to-end HTTP; **during the writing stage no endpoint returns the original**, notes are attached to the book |
| Front-end contract | whether the elements and endpoints the JS refers to all exist (guards against "you click and nothing happens") |
| Input effects | only settled characters are animated, the three settings really do draw differently, the amount of animation does not grow with article length, it can be attached and detached |
| Front-end rendering | every page's render actually run once in Node, with real endpoint data |

360-odd checks in total. The runner starts a service with a fake model itself for the render checks and shuts it down afterwards —
so it does not depend on you starting a server by hand, and it never really calls a model or spends money.

A few self-checks deserve their own mention; every one of them was added because it **actually caught a problem during development**:

- **Before returning, the writing endpoints re-check the data they are about to send against the original**, and refuse to serve at all if a suspected leak is found.
  It caught this: a section title had been cut from the original's first sentence, and it was hung on the practice page's title bar,
  which amounted to handing you the opening of that paragraph. The practice page now shows no section title.
- **The same kind of self-check caught the model carrying a whole sentence of the original into a hint.** That is now removed at the generation step.
- **Paragraphing fallback**: paste 2000 characters with no punctuation and it used to be treated as "one paragraph", so one practice round meant memorising 2000 characters.
  Now it also splits inside sentences on punctuation, and failing that splits hard on character count, so no shape of paste produces an over-long paragraph.

---

## Layout

```
启动.cmd / 启动.sh        launch entry points
app/
  fk_store.py             data layer: splitting (sections/paragraphs), archive, state machine, notes
  fk_llm.py               talking to the model: the sentence-hint prompt, quotas, turning errors into plain language
  fk_summary.py           hint cache, ledger, batch generation, copy check
  fk_server.py            local HTTP service + factory self-check
  web/                    front end: shelf / reading / writing desk / single-sentence practice / sentence comparison
  data/                   your books, drafts, notes (+ summaries.json hint cache)
tests/                    six test suites + a service with a fake model
_probe/                   development-time probe scripts and real corpus
```

---

## Some design trade-offs

**Why should notes land on "one particular sentence", rather than a summary written for the whole paragraph?**
Because a note landing on one specific sentence is something you can act on — "in this sentence I dropped the causation" tells you what to watch next time;
"I didn't write well enough" you cannot act on. And notes that follow the book and can be leafed through at any time are far more useful than a paragraph of reflection per round.

**Why tidy the whitespace once on import?**
Articles copied from a web page often carry leading and trailing spaces, and may have lines containing nothing but whitespace.
They don't affect the content, but they make the split produce a pile of fragments with no content, and the sentence numbering drifts.
So on import the whitespace is normalized exactly once (extra whitespace inside a line compressed to one, runs of blank lines reduced to at most one),
and **not one real character is touched** — the assertion "reassembling by paragraph equals the original" still holds.

**Why use a canvas overlay for the typing effect instead of wrapping every character in an element?**
The former draws only a few dozen characters in flight, its cost is essentially unrelated to article length, and it does not touch the text in the input box at all —
the Chinese input method, selection and undo are all unaffected. The latter means maintaining an editable rich-text area with one node per character,
which starts stuttering at a thousand characters and easily breaks the input method too.

**Why does the effect wait for the character to "settle" instead of following every input event?**
Because when typing Chinese, pinyin and candidate words appear in the input box first. Animating on input events scatters the effect across a pile of intermediate states:
it looks messy and it isn't obvious — what a reader perceives is "this character was just written", not "the pinyin letters popping out one by one".

**Why are hints "one per sentence" instead of a few summarising the paragraph?**
Franklin's own practice was to jot a short hint for each sentence ("short hints of the sentiment of each
sentence"), leave it a few days, then write the whole thing back while looking at the hints. And this exercise trains precisely "writing each sentence well",
so the unit of the hint should be the sentence. A paragraph summary has two further problems: it re-organizes the original, and that structure is
the model's rather than yours; and it very easily carries the original's wording in with it, so writing from it becomes transcription.

**Why does the delay sit between "finished reading" and "start writing", rather than after submission?**
The point of the delay is to let what you read drop from your eyes into memory, so that what you write out is "what you remembered". Putting it after submission only stops you from peeking: it guards against cheating, not to help memory.

**Why two levels, "section + paragraph"?**
Reading needs to be continuous, so you read by section; practising memory cannot be too long, so you practise by paragraph. Once you have read a section's body, you can practise it paragraph by paragraph.

**Why must the split guarantee that "not one character is lost"?**
The original is stored once only, and a paragraph's position is a coordinate inside the original. So "reassembling every paragraph" must be exactly equal to the original. The tests treat this as a hard assertion — it is the precondition for every comparison feature being trustworthy.

**Why does the comparison page align by LCS instead of sentence n against sentence n?**
Because as soon as you skip one sentence, everything after it is misaligned, and what the page shows is false information — worse than showing nothing. Now sentences you added and sentences you skipped are marked separately, and the rest line up where they belong.

**Why does the hint cache key carry the model name and the prompt version?**
Because the content of a hint depends on those two things. Carrying them means the old cache invalidates itself when you switch models or change the prompt,
so you don't have to remember to clear it; and the same piece of text is done only once no matter which book it appears in, so you don't have to worry about paying twice.

**Why remove the hint that copied the original, rather than keeping it for reference?**
Because you can recall that sentence yourself anyway, and keeping it only makes you write from it. The value of a hint is "helping you remember what was said";
the moment it starts giving you the original's sentences, the exercise turns into transcription.

**Why does the ledger record only the numbers the provider reports back?**
Because only those are real. An estimate can be used to say "roughly how much this will cost", but it must not go into the ledger — that would let you think you know what you spent when in fact you don't.
