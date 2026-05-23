# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Marketing + waitlist site for **Mirrah**, a somatic / nervous-system regulation app
("creating the space between trigger and response"). Served at **waitlist.mirrah.app**
(see `CNAME`) via GitHub Pages from `origin` (github.com/Yanivro/mirrah-website).

There is **no build system, no package manager, and no test suite** — the entire site is
hand-authored static HTML with all CSS and JS inlined in each page. Editing a file *is*
the deploy step once it's pushed to the default branch.

## Develop / preview / deploy

```bash
# Preview locally (any static server; no install step):
python3 -m http.server 8000      # then open http://localhost:8000

# Deploy: commit + push to the branch GitHub Pages serves (main). No CI, no build.
git add -A && git commit -m "..." && git push
```

There are no lint, test, or build commands — do not invent them.

## Pages

- `index.html` — the landing page. Single self-contained file (~2200 lines): `<style>` block,
  page markup, then one `<script>` block at the bottom. Links to the blog via a top-right glass
  nav pill ("the space between →") and a footer link.
- `body-map.html` — standalone interactive "body check-in" tool, linked from the landing page.
  Its results screen links back to `index.html` to join the waitlist.
- `assets/body-map-v3.html` — a working/iteration copy of the body map; not linked from the
  live site. Confirm which body-map file is live before editing.
- `assets/` — looping background videos (paired `.webm` + `.mp4`), hero stills, app screenshots,
  founder photo.
- `blog/` — the **SEO blog** ("the space between"). Generated, not hand-authored: `blog/build.py`
  (stdlib-only, no pip deps) reads `blog/posts.json` + each content kit's `seo-blog-post.md` and
  writes `blog/<slug>.html` + regenerates the card grid in `blog/index.html`. **Don't hand-edit the
  generated `blog/<slug>.html` files** — change the source kit or `blog/_template.html` and re-run
  `python3 blog/build.py`. Full workflow in `blog/README.md`; design/voice contract in
  `blog/_brief.md`. Source content lives outside this repo at
  `/Users/yanivrozenblat/claude-research/mirrah/content/content_kits`. Post covers are 4:5 images
  in `blog/assets/covers/` rendered from `blog/_covers/*.html` via the shared Mirrah carousel theme.

## Architecture notes (the non-obvious parts)

**Waitlist flow.** The hero/bottom email forms don't submit directly — `handleSubmit()`
captures the email and opens a modal (`openWaitlist()`) that collects name/OS/age/gender/alpha
opt-in/consent. `submitWaitlist()` POSTs JSON to a **Google Apps Script Web App**
(`SHEET_URL` constant in `index.html`) using `mode: 'no-cors'`. Because no-cors responses are
opaque, success is *always* shown after a timeout regardless of the actual result — there is no
real error handling on the network call by design. The `source` field distinguishes
`mirrah-waitlist` vs `mirrah-bodymap` submissions. Changing the destination = change `SHEET_URL`.

**Body-map → waitlist bridge.** When `modalSource === 'bodymap'`, a successful submit opens
`body-map.html` in a new tab after the success screen.

**Fake-but-deterministic social proof.** `getWaitlistCount()` computes the displayed waitlist
number from days elapsed since `2026-03-30` (seeded, monotonic) — it is not a real count.

**Device-aware media.** An IIFE near the bottom of `index.html` inspects `navigator.deviceMemory`,
`hardwareConcurrency`, `connection.saveData`, and effectiveType. On low-end/mobile/save-data
clients it **removes** all `.vid-bg` and `.hero-video` elements rather than loading them; capable
clients play only one video at a time via IntersectionObserver. This is a deliberate Android/GPU
mitigation (see recent commits) — preserve it when touching hero or video sections.

**Scroll reveals.** Elements with class `reveal` / `phone-reveal` / `phone-wrap` are faded in by
an IntersectionObserver adding `.visible`. New animated sections need one of these classes.

## Conventions

- **Design tokens** live as CSS custom properties in `:root` at the top of each file's `<style>`
  (warm paper `--bg:#EDE5DA`, lavender `--accent-deep:#6B58A8`, sage, etc.). Use existing tokens
  rather than new hex values. The aesthetic is neumorphic / soft-glass on a warm paper background.
- **Fonts**: `Cormorant Garamond` (serif, headings — often italic) + `DM Sans` (body), loaded from
  Google Fonts. `body-map.html` additionally uses `Nunito`.
- CSS is written tight (multiple declarations per line) to keep these large single-file pages
  scannable — match that style.
- Vanilla JS only (`var`, plain functions, no framework or build). Keep it that way.
- Copy is lowercase, calm, somatic/body-first in voice.

## Agent orchestration (cost convention)

When work can be parallelized or delegated, the Opus session acts as **orchestrator**:
dispatch self-contained subtasks to **Sonnet** agents (design, codegen, analysis) or **Haiku**
agents (mechanical/batch work) to keep cost down, and reserve Opus for planning, integration, and
edits to critical shared files (e.g. `index.html`). Give each subagent enough standalone context to
run without round-trips — the canonical `:root` design tokens, exact file paths, and a pointer to
the `mirrah-design` skill for any brand/voice decision.

## Brand & voice authority

For any Mirrah-facing copy, visual, or design decision, the **`mirrah-design`** skill is the
canonical source for brand tokens, voice rules, and component patterns — consult it before writing
marketing copy or new UI. `mirrah-pdf-maker` generates branded print handouts.
