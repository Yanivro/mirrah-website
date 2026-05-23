# Mirrah blog — shared build brief

> Single source of truth for every agent working on the blog. Read this fully before generating.
> The blog lives at `waitlist.mirrah.app/blog/` and is part of the existing zero-build static site
> (`../index.html`). It must look like it grew out of that landing page — do NOT invent a new look.

---

## 0. Brand decisions (locked by mirrah-design skill — do not re-decide)

- **Section name (used everywhere): `the space between`** — lowercase. Echoes the site H1
  ("creating the space between trigger and response") and the product promise ("what goes between
  the impulse and the action"). Nav link label: `the space between`.
- **Listing-page tagline:** `what your body is doing before your mind catches up.` (lowercase, body-first)
- **Voice = web/marketing surface → ALL LOWERCASE** for all *chrome* (nav, section name, tagline,
  "x min read", buttons, category labels, CTA copy, footer). Per mirrah BRAND.md.
- **EXCEPTION — leave authored article content as-is:** the post `<title>`, the `<h1>`, the body
  H2s/H3s and prose come from the SEO content kits and stay in their authored case (Title Case) for
  search + scannability. Only the surrounding Mirrah chrome is lowercased.
- **Banned in any copy you write:** the antithesis pattern (`Not X. Y.` / `it's not about A, it's
  about B`) — this is mirrah's #1 AI-tell. Also banned: the words `just`, `should`, `calm down`,
  `journey`, `transform`, `heal` (as promise), `science-backed`, `community`, `AI-powered`. No
  exclamation marks. Body before mind. Validate before instruct.

## 1. Palette & type (harmonized: site shell + canonical accents)

Inherit the **landing-page shell** for site continuity, layered with the **canonical Mirrah
accents** from DESIGN.md. Put these in each file's `:root`:

```css
:root{
  /* base — from ../index.html (warm paper) */
  --bg:#EDE5DA; --bg2:#E4D9CC; --bg3:#D8CFC2;
  --text:#1a1510; --muted:#3a3228; --hint:rgba(26,21,16,0.6);
  --glass:rgba(255,255,255,0.55); --glass-strong:rgba(255,255,255,0.82);
  --glass-border:rgba(0,0,0,0.06);
  --neu-light:#fff; --neu-dark:#d8d4cf;
  /* canonical Mirrah accents (DESIGN.md) — semantic, never decorative */
  --coral:#C4725A; --coral-dark:#A85C46;   /* editorial accent: rules, hover, category, wordmark tie-in */
  --teal:#6AADA0;                           /* time/metadata: date · reading time */
  --lavender:#B8A5D4; --accent-deep:#6B58A8;/* reflect/heavy; --accent-deep = existing site CTA */
  --gold:#E8B878;
  --on-coral:#FFFAF0;
}
```

- **Fonts (match the site exactly):** `Cormorant Garamond` (serif — headings, the wordmark, post
  titles, often italic) + `DM Sans` (300/400/500 — body). Load from Google Fonts the same way
  `../index.html` does. Do NOT introduce Source Serif 4 / Nunito here (those belong to the
  separate carousel-cover images).
- **Accent usage:** coral = editorial accent (hairline rules, link/card hover, the small reading
  motif, category pills). teal = date + "x min read" metadata only. lavender/`--accent-deep` =
  the waitlist CTA (continuity with the landing page). Reserve color for meaning; warm paper +
  serif does most of the work. Aesthetic = **warm somatic neumorphism** (soft dual shadows on
  cream: `box-shadow:8px 8px 24px var(--neu-dark),-8px -8px 24px var(--neu-light)`), soft-glass.
- **CSS style:** write tight (multiple declarations per line) like `../index.html`. Vanilla only —
  no framework, no build, no external JS libs. `var`/plain functions if any JS at all.

## 2. The content kits (source data)

Located at `/Users/yanivrozenblat/claude-research/mirrah/content/content_kits/<kit>/`. Each kit has
`seo-blog-post.md` (YAML frontmatter + markdown body + a trailing ```json``` JSON-LD FAQPage block)
and `visual-brief.md` (the infographic panel spec). Frontmatter keys are **inconsistent across
kits** (some use `meta-title`/`meta-description`/`date-published`, others `title`/`description`/
`datePublished`, others `slug`/`canonical`/`reading_time`/`keywords`) — the generator normalizes
them. The 10 publishable posts and their canonical slugs:

| kit folder | slug (output filename) |
|---|---|
| 4-body-states-anxious-attachment-2026-05-18 | the-4-body-states-of-anxious-attachment |
| adhd-motivation-novelty-cycling-2026-05-21 | adhd-motivation-disappears-novelty-cycling |
| anxiety-excitement-same-body-2026-05-21 | anxiety-feels-like-excitement |
| body-keeps-score-debate-2026-05-21 | body-keeps-score-debate-accurate-science |
| loneliness-like-hunger-2026-05-21 | why-loneliness-feels-physical |
| masking-until-crash-2026-05-21 | adhd-autistic-masking-burnout |
| mood-is-metabolic-2026-05-21 | mood-is-metabolic |
| naming-the-feeling-2026-05-21 | does-naming-your-emotions-work |
| reaction-is-time-travel-2026-05-21 | why-do-i-overreact-to-small-things |
| relationships-metabolically-expensive-2026-05-21 | why-relationships-leave-you-exhausted |
| vagus-nerve-not-off-switch-2026-05-21 | vagus-nerve-shutdown-deep-breathing |

(`mood-is-metabolic` is missing frontmatter — the orchestrator backfills it before the build runs.)

## 3. The placeholder contract (so template + index + build.py interoperate)

**`blog/_template.html`** — a complete HTML document for ONE post. The generator does literal
string replacement of these exact tokens (they appear verbatim, no logic):

| token | filled with |
|---|---|
| `{{POST_TITLE}}` | authored title (Title Case). Goes in `<title>`, `<h1>`, og:title |
| `{{POST_DESCRIPTION}}` | meta description / dek |
| `{{POST_KEYWORD}}` | primary keyword (for meta keywords) |
| `{{POST_CANONICAL}}` | `https://mirrah.app/blog/<slug>` |
| `{{POST_SLUG}}` | slug |
| `{{POST_DATE_ISO}}` | `2026-05-21` (for `<time datetime>` + JSON-LD) |
| `{{POST_DATE_HUMAN}}` | `may 21, 2026` (lowercase, displayed) |
| `{{POST_READING_TIME}}` | integer minutes, e.g. `6` |
| `{{POST_COVER}}` | `assets/covers/<slug>.png` (relative to /blog/) |
| `{{POST_BODY_HTML}}` | the markdown body converted to HTML (see §4) |
| `{{POST_JSONLD}}` | the JSON-LD object(s), already including FAQPage; emitted inside `<script type="application/ld+json">` |

**`blog/index.html`** — a complete designed listing page. Mark the card region with literal
comments `<!-- CARDS:START -->` and `<!-- CARDS:END -->`; between them put ONE example card using
these tokens, repeated per post by the generator:

| token | filled with |
|---|---|
| `{{CARD_URL}}` | `<slug>.html` |
| `{{CARD_TITLE}}` | authored title |
| `{{CARD_DESCRIPTION}}` | description/dek |
| `{{CARD_COVER}}` | `assets/covers/<slug>.png` |
| `{{CARD_DATE_HUMAN}}` | `may 21, 2026` |
| `{{CARD_READING_TIME}}` | integer minutes |

Cards render newest-first. If a cover image is missing, the card must degrade gracefully (warm
neumorphic placeholder block with the post title — never a broken `<img>`).

## 4. Markdown → HTML rules (build.py)

The post bodies use a known subset: `#`/`##`/`###` headings, paragraphs, `**bold**`, `*italic*`,
`---` hr, `-`/`1.` lists, GitHub-style tables, `> blockquotes`, and a trailing ` ```json ``` ` fence
that is the JSON-LD (extract it → `{{POST_JSONLD}}`, do NOT render it as a code block). Special:

- Lines like `[INFOGRAPHIC: Panel 2 — One Signal, Two Stories (see visual-brief.md)]` → render as
  an on-brand **text callout** (`<aside class="infographic-callout">` styled in the template as a
  coral-tinted neumorphic pull-quote with a small "infographic" label), using the panel title text.
  These are swappable for real panel images later — keep the markup clean and class-driven.
- The final "What This Looks Like in Practice" section ends on the mirrah line — style its closing
  paragraph as a serif pull-quote (template provides `.practice-close`).
- Leave the word "Mirrah" as authored in body prose (do not lowercase mid-article — these are SEO
  articles; the chrome handles the lowercase brand voice).

## 5. End-of-post CTA (template provides; reused on every post)

A neumorphic block at the end of each article, copy in lowercase, mapped to mirrah's locked PEACE
soundbites — NO antithesis:

- line 1 (recognition): `you can name the pattern while you're inside it. you send the text anyway.`
- line 2 (answer, serif): `mirrah is what goes between the impulse and the action.`
- a single email field + button `join the waitlist →` styled like `.waitlist` on the landing page.
- under the button (small): `if you're tired of regretting what you sent at 1 am, mirrah is the right decision.`

Wire the form to post to the same Google Apps Script endpoint the landing page uses, lightweight
(no full modal): `var SHEET_URL='https://script.google.com/macros/s/AKfycbzVAYUTYBjzuu7dZspXFYULFLNK72rAMcd2G_VALUfLrHNZ0INRqaKJkZyDugFsME4_/exec';`
POST `{email, source:'mirrah-blog-'+slug, consent_date}` with `mode:'no-cors'`, then swap to an
inline success state (`you're on the list. we'll be in touch.`). Because no-cors is opaque, always
show success after the fetch. This mirrors `../index.html`'s pattern.

## 6. Don't

- Don't add stock photos, emoji icons, purple "tech" gradients, or SVG-drawn people/imagery.
- Don't invent stats, testimonials, or filler. Honest placeholder > poor implementation.
- Don't pull in any JS framework, bundler, or external CSS/JS library.
- Don't use `Color.white`/pure white anywhere — warm cream only.
