[English](SECURITY.en.md) · [中文](SECURITY.md)

# Security Policy

## This tool's security model

First, let us be clear about what it is, so you can judge for yourself which things are risks and which are not.

**This is a local tool.** The server listens only on `127.0.0.1`, and other machines on the same LAN cannot connect to it either. It has no account system, no cloud, no telemetry, no auto-update.

**Your data is all local:**

```
app/data/index.json        books, drafts, notes, settings (including the API key)
app/data/index.json.bak    the previous version
app/data/texts/<id>.txt    the original text of each book
app/data/summaries.json    the cache of per-sentence hints
```

**The only outbound network request is the one made by the hint feature, after you have entered an API key in settings:**

- the request goes to the provider address you chose yourself (`base_url`), and its content is only **the passage of the original that was asked to be turned into hints**;
- your drafts, notes and book list **are not sent**;
- no key entered = not a single outbound request.

---

## Reporting vulnerabilities

**Please do not report security vulnerabilities through a public Issue.**

Use GitHub's private vulnerability reporting: on the repository's **Security** tab, click **Report a vulnerability**. If you cannot use that, contact [@luluxiuc](https://github.com/luluxiuc) privately.

Please include:

- the affected version or commit
- reproduction steps
- the scope of impact (what can be read, what can be changed)
- a suggested fix direction, if you have one

**We will do our best to respond promptly.** This is a personally maintained project with no SLA, but this we promise: it will be looked at seriously on receipt, it will not be made public before it is handled, and once it is fixed it will be written up clearly in [`CHANGELOG.en.md`](CHANGELOG.en.md).

---

## The classes of problem we especially care about

In order of severity:

### 1. Leaking the original during the writing stage

**This is the most severe class of vulnerability in this project.** While the user is writing from memory, the original appearing in any endpoint, any page or any error message directly voids the exercise.

The service layer already has a reverse-lookup self-check (data on its way out is scanned against the original once more), but it cannot possibly cover every path. **If you find a way around it, please report it.**

### 2. API key leakage

- the key ending up in logs, in error messages, in exported files
- the key being sent to an address other than `base_url`
- the key being echoed anywhere on the web frontend

> One thing in passing: `app/data/index.json` stores the API key **in plain text**. This is deliberate — this tool does no encryption, because on a machine only you can log into, encryption only creates the illusion that "it is protected". **Please protect this file the way you would protect any plain-text credential.** If you think this decision should change, you are welcome to open a Discussion about it.

### 3. The local service being reached from off-machine

The service binds to `127.0.0.1`. If you find a path that makes it listen on `0.0.0.0`, or one that gets around it through a DNS rebinding attack, please report it.

### 4. Problems caused by importing malicious text

Path traversal, an oversized file exhausting memory, mishandled encoding causing a crash. **Note: the text content itself is never executed as code** — there is no `eval`, no template injection, no imported content spliced into any command. If you find the opposite, please report it.

### 5. Dependencies

This project **has no third-party dependencies** (only the Python standard library + a vanilla frontend). So there is no supply-chain dependency risk — **but please help us hold this line too**: any PR that "just adds one small dependency" weakens this property and is worth questioning in review.

---

## Out of scope

- **Copyright problems with the text you import.** The tool is only a text processor.
- **How the model provider you chose handles the passage of the original you sent it.** That is a matter between you and them; please read their privacy policy. **If this matters to you, do not enter a key** — without a key you can still use every training feature of this tool in full.
- **Other programs on your machine reading `app/data/index.json`.** Local file permissions are your operating system's responsibility.
- **Social engineering.** For example, someone impersonating the maintainer to ask you for a key. **We will never ask you for an API key.**

---

## Support scope

Only the code on the repository's latest `main` branch is in scope for support. Please confirm that the problem still exists on the latest code before reporting it.
