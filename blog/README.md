# the space between — mirrah blog

Static, SEO-first blog generated from the Mirrah content kits. Zero runtime dependencies:
`build.py` turns each kit's `seo-blog-post.md` into a committed static HTML page, so the deployed
site stays 100% static (GitHub Pages serves the output as-is).

## Add or update a post (the repeatable action)

1. **Make sure the content kit exists** with a finished `seo-blog-post.md` (YAML frontmatter +
   markdown body + a trailing ` ```json ``` ` JSON-LD FAQPage block) under the content-kits root
   (`content_kits_root` in `posts.json`, currently
   `/Users/yanivrozenblat/claude-research/mirrah/content/content_kits`).
2. **Register it in `posts.json`** — add
   `{ "order": N, "slug": "<url-slug>", "kit": "<folder>", "published": false }`.
   `order` controls position on the index (1 = top). The slug here is authoritative (it becomes
   `<slug>.html` and the canonical URL); frontmatter slug is ignored. New posts start as **drafts**.
3. **Add a cover image** at `assets/covers/<slug>.png` (4:5). To make one on-brand, build a hook
   frame from `_mirrah-theme/carousel-theme.css` (see any file in `_covers/` as a worked example)
   and screenshot it:
   `npx playwright screenshot --viewport-size=900,1125 "file://.../_covers/<slug>.html" assets/covers/<slug>.png`
   If the cover is missing, the card and article degrade to a tasteful neumorphic placeholder.
4. **Run the generator** from the repo root:
   ```bash
   python3 blog/build.py
   ```
   It writes `blog/<slug>.html` for every post and regenerates the card grid inside `index.html`
   (between `<!-- CARDS:START -->` / `<!-- CARDS:END -->`). Reading time is computed automatically.
5. **Commit** `blog/` and the changed `index.html`, then push. That's the deploy.

## Publishing intelligently (one at a time, on a schedule)

Posts are gated so they don't all go live at once. A post appears on the site **only when
`published: true` AND its `publish_date` (if set) is on or before today**:

- **Draft** — `"published": false` (or omitted). Not generated, not linked, no page on the server.
- **Live now** — `"published": true` with no `publish_date`, or a `publish_date` already passed.
- **Scheduled** — `"published": true` with a future `publish_date`. It stays held until that date —
  **then you must re-run `build.py`** for it to appear (this is a static site; there's no server-side
  scheduler, so either rebuild manually on the date or wire a daily cron that runs `build.py` + commits).

Flipping a post back to `published: false` and rebuilding removes its page cleanly. `build.py` prints
which posts are live vs held on every run. `posts.json` carries a `note` on posts whose source still
has author **NEEDS-SOURCING** flags — verify those claims before setting them live.

### Daily auto-publisher (launchd)

`auto-publish.sh` + a macOS launchd agent (`~/Library/LaunchAgents/app.mirrah.blog-autopublish.plist`,
label `app.mirrah.blog-autopublish`) run the build once a day (09:00). When a scheduled `publish_date`
arrives, the build output changes and the script commits + pushes to `main` (deploying via Pages); on
days with nothing newly due it pushes nothing. The job runs on this Mac because the post sources live
here, outside the repo. Logs: `~/Library/Logs/mirrah-blog-autopublish.log`.

```bash
# manage the agent
launchctl print  gui/$(id -u)/app.mirrah.blog-autopublish   # status
launchctl kickstart -k gui/$(id -u)/app.mirrah.blog-autopublish   # run it now
launchctl bootout gui/$(id -u)/app.mirrah.blog-autopublish   # disable
```

Requirements: the Mac is powered on around 09:00 (launchd runs a missed job on next wake), and git push
credentials are cached for non-interactive use (the osxkeychain helper, already set up from manual pushes).

## Note: in-body infographics

The source posts contain `[INFOGRAPHIC: …]` markers, but the captions are designer briefs, so the
generator currently **drops them** from the article body (covers still show on cards + at the top of
each post). To re-enable in-body panels later, generate real panel images and restore a callout in
`build.py` where the `INFOGRAPHIC_RE` marker is handled (the `.infographic-callout` styles still live
in `_template.html`).

## What's in here

| file | role |
|---|---|
| `build.py` | stdlib-only generator (own frontmatter parser + markdown→HTML). No pip deps. |
| `posts.json` | authoritative manifest: order, slug, source kit folder, content-kits root |
| `_template.html` | article shell with `{{POST_*}}` tokens (don't rename tokens — `build.py` relies on them) |
| `_card.html` | one index card with `{{CARD_*}}` tokens; `build.py` stamps it per post |
| `_brief.md` | the design/voice/contract brief every contributor (human or agent) should read first |
| `_covers/*.html` | cover-image sources (rendered to `assets/covers/*.png` via Playwright) |
| `index.html` | listing page; the card region is generated, the rest is hand-authored |
| `<slug>.html` | generated post pages (do not hand-edit — regenerated by `build.py`) |

## Conventions (see `_brief.md` for the full spec)

- Section name everywhere: **the space between** (lowercase). Tagline: *what your body is doing
  before your mind catches up.*
- Chrome (nav, metadata, buttons, CTA) is **all lowercase** (mirrah web voice); authored article
  titles/headings stay in their SEO Title Case.
- Inherits the landing page shell (warm paper, Cormorant Garamond + DM Sans, neumorphism). Coral =
  editorial accent, teal = date/reading-time, lavender (`--accent-deep`) = the waitlist CTA.
- The end-of-post CTA posts to the same Google Apps Script endpoint as the landing page, with
  `source: mirrah-blog-<slug>`.
- No frameworks, no build step beyond `build.py`, no external JS/CSS libraries.
