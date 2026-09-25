[English](CONTRIBUTING.en.md) · [中文](CONTRIBUTING.md)

# Contributing

The most important rule comes first, and it outweighs every other item:

> **This tool never judges writing.**
>
> No addition of any kind is accepted: scoring, similarity, "does it sound like the author", grades, rankings, "how well did you write this passage", automatically produced revision suggestions, automatically generated sentences that the user ought to write.
>
> This is not a matter of preference, it is a measured conclusion. For the basis see [`docs/research/`](docs/research/).

Want to change this rule? **You can, but you have to overturn the experiment with data**, not persuade us with opinions. Open an Issue first and post your reproduction plan.

---

## Contributions we welcome

| Area | What it is concretely | Difficulty |
| --- | --- | --- |
| **More experiments** | Human annotation (3 or more qualified readers), re-testing on a corpus with no model memory, re-running Experiment 1 while keeping the raw logs. **This is the most valuable category.** | Medium |
| **Reporting problems** | Especially the three kinds: "I clicked and nothing happened", "the split is wrong", "characters went missing". Please include reproduction steps and system information. | Low |
| **Interface and typography** | Fonts, line spacing, white space, immersion. The feel of a writing tool is the product itself. | Low–Medium |
| **Splitting rules** | Adaptation for classical Chinese, poetry, translations, technical documentation. | Medium |
| **Packaging** | Windows / macOS single file, Docker, Homebrew. | Medium |
| **Translation** | Interface strings and multilingual versions of the documentation. | Low |
| **Documentation** | Fixing typos, adding screenshots, explaining the design trade-offs more clearly. | Low |

---

## Environment and running the tests

You need **Python 3.10+**. **Node 18+** is needed only to run the frontend checks.

```bash
git clone https://github.com/luluxiuc/Franklin-Writing.git
cd Franklin-Writing
python tests/run_all.py
```

`run_all.py` starts its own **server with a fake model** to run the rendering checks, and shuts it down when it is done. **No API key needed, no network, no money.**

Running a single group:

```bash
python tests/test_store.py       # data layer
python tests/test_summary.py     # per-sentence hints and caching
python tests/test_server.py      # HTTP end-to-end, leak prevention
python tests/test_frontend.py    # frontend contract
node   tests/ui_check.mjs        # clicking a button really does something (server must be running first)
node   tests/anim_check.mjs      # typing animation
node   tests/render_check.mjs    # frontend rendering (server must be running first)
```

**Everything must be green before you submit a PR.** Documentation-only changes are the exception.

---

## Hard constraints (change one of these and it is a different project)

### 1. No judging

See the opening. There are no exceptions to this one, including "just a reference score", "just a progress bar", "the user can switch it on optionally".

### 2. Hints must be one sentence, one hint

However many sentences the original has, that is how many hints there are. This invariant is a hard assertion in the hint-card tests:

- **The count is determined by the number of sentences in the original, not by what the model says.** If the model gives too few, it is truthfully reported as misaligned; if it gives too many, they are truncated.
- **There is a character cap per hint** (22 characters at ≤4 sentences, 18 at ≤8 sentences, 15 beyond that).
- **You cannot condense a whole paragraph into a few hints.** That reorganises the original, and that structure belongs to the model rather than to the user; it also very easily drags the original's wording in.

### 3. Any run of the original that appears in a hint must be removed

If any hint contains **≥ 8 consecutive characters identical, character for character, to the original**, that hint is dropped.

**This is not only about saving money**: once a hint contains a sentence from the original, the user is no longer writing from memory and the exercise fails outright. The threshold `min_run=8` can be adjusted through discussion, but "this check must exist" cannot be touched.

### 4. During the writing stage, not one character of the original may appear

No endpoint other than the practice page and the comparison page may return the original before the user submits. The service layer has a **reverse-lookup self-check**: data on its way out is scanned against the original once more, and anything suspected of being a leak is refused.

> It really did catch one: the title of a section had been cut from the first sentence of the original, and it was attached to the practice page's title bar, which handed the opening of that passage to the user. **The practice page now shows no section title; this is deliberate, do not add it back.**

### 5. Splitting must be reversible

The original is stored only once, and a paragraph's position is a coordinate inside the original. So **stitching every paragraph back together must equal the original exactly**. This is a hard assertion in the tests, and the precondition for every comparison feature to be trustworthy.

### 6. Zero dependencies

The backend uses only the Python standard library. **No pip dependency is introduced**, including ones that look innocent. The frontend uses no framework, no build step, no CDN.

The reason: this tool has to be openable by double-click ten years from now, on an old laptop with no network. Half of its value is "the data is still there, and it opens any time".

### 7. No emoji in the interface

Hierarchy is expressed with fonts and typography, not with icon-style emoji. This one was explicitly requested by the user.

---

## Code style

- **Comments explain "why", not "what".** In particular, write clearly which pitfall a given threshold or a given ordering was settled by falling into. The most valuable comments in this repository are all of that kind.
- Chinese comments and Chinese strings, consistent with the existing code.
- No formatter and no lint rule set. Staying consistent with the surrounding code is enough.
- **New behavior must come with tests.** Especially on the frontend: asserting "the data is different" is not enough, you have to assert "the click really reaches the code".

### Three frontend lessons

All three were learned from incidents that actually happened:

**One, animation must never touch the text in the input box.**
The canvas is overlaid on top and draws, measuring font and font size from the input box. Wrapping every character in a DOM element would destroy the Chinese input method, the selection and undo, and it starts to stutter once you reach a thousand characters.

**Two, animate only "settled characters".**
While typing Chinese, pinyin and candidate words appear in the input box first. Animating on every input event scatters the effect across a pile of intermediate states, which looks messy and is not noticeable. Wait for the moment the input method commits the text.

**Three, `const` declarations must come before the functions that use them.**
It sounds silly, but it really happened: `FONTS_ANIM` was declared after the function that used it, hit the temporal dead zone, threw an exception on the function's first line, and the interface showed "**clicked the button and nothing happened**", with no message at all. There is now a set of tests that renders the template, finds the buttons, clicks them, and then checks whether the state changed.

---

## Submission workflow

1. **Open an Issue before you start**, unless it is an obvious typo or a small fix. That way you avoid writing something we will not accept.
2. Fork, and branch off `main`. Any branch name will do, as long as it is understandable.
3. When you are done, run `python tests/run_all.py`, all green.
4. Submit the PR and state three things clearly:
   - **What changed** (down to the behavior)
   - **Why** (if it fixes a bug, write out the reproduction steps)
   - **How you verified it** (which test, or how you tried it by hand)
5. When you add or change behavior, **bring the tests in the same PR**.

**About commit messages:** Chinese or English, either is fine, as long as it is understandable. No format is enforced.

---

## Contributions that will not be accepted

| Proposal | Why not |
| --- | --- |
| Adding scoring / similarity / "does it sound like the author" | Measured conclusion: it only pushes the user away from the target author. See [`docs/research/`](docs/research/). |
| Automatically revising the user's drafts, automatically writing sentences for them | Everything this tool generates is "one hint per sentence". |
| Adding login, cloud sync, an account system | Local-first is this product's identity, not a temporary implementation detail. |
| Introducing a web framework / bundler / build step | Contradicts "still openable by double-click ten years from now". |
| Adding pip dependencies | Same as above. |
| Lots of emoji / an icon-style interface | The user explicitly rejected it. |
| Turning hints into whole-paragraph summaries | Contrary both to what Franklin himself did and to the purpose of this exercise. |
| Making any of the above "optional" for the user | "Optional" does not change the fact that it will lead some users astray. |

---

## Filing an Issue

Use the [template](https://github.com/luluxiuc/Franklin-Writing/issues/new/choose). **If you have a thought that is not worked out yet, go to [Discussions](https://github.com/luluxiuc/Franklin-Writing/discussions)** rather than rushing to open an Issue.

When reporting a bug, this information is useful:

- Your system and Python version
- Reproduction steps (a stable reproduction is best)
- What kind of text you imported (plain text? pasted from a web page? classical Chinese?)
- The red errors in the browser console (if it is a frontend problem)
- **Do not paste an API key.**

---

## Releases

The maintainer handles this. The process:

1. `python tests/run_all.py` all green
2. Update [`CHANGELOG.en.md`](CHANGELOG.en.md)
3. Tag and write the release notes

---

## Code of Conduct

By participating in this project you agree to abide by the [Code of Conduct](CODE_OF_CONDUCT.en.md).

## License

This project is licensed under the [PolyForm Noncommercial License 1.0.0](LICENSE). **Submitting a contribution means you agree that your contribution is released under the same license.**
