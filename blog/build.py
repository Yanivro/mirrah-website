#!/usr/bin/env python3
"""
Mirrah blog static-site generator.
stdlib only — no pip dependencies.
Run from repo root: python3 blog/build.py
Run from blog/: python3 build.py
"""

import json
import os
import re
import sys
from datetime import datetime

# ── path resolution ───────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BLOG_DIR = SCRIPT_DIR  # build.py lives in blog/


def blog_path(*parts):
    return os.path.join(BLOG_DIR, *parts)


# ── frontmatter parser ────────────────────────────────────────────────────────

def parse_frontmatter(text):
    """
    Parse YAML-ish frontmatter between the opening --- and closing ---.
    Handles:
      - key: value
      - key: "quoted value"
      - key: [inline, array]
      - key:               # bare key starts a block list
        - item1
        - item2
    Returns (frontmatter_dict, body_text).
    """
    lines = text.split('\n')
    if not lines[0].strip() == '---':
        return {}, text

    fm_lines = []
    end_idx = None
    for i, line in enumerate(lines[1:], 1):
        if line.strip() == '---':
            end_idx = i
            break
        fm_lines.append(line)

    if end_idx is None:
        return {}, text

    body = '\n'.join(lines[end_idx + 1:])
    fm = _parse_yaml_block(fm_lines)
    return fm, body


def _parse_yaml_block(lines):
    """Minimal YAML block parser for frontmatter."""
    result = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        # Skip blank lines and comments
        if not line.strip() or line.strip().startswith('#'):
            i += 1
            continue

        # Check for block-list item (  - value) at top level — should not happen
        # but skip gracefully
        if re.match(r'^\s+-\s', line) and not result:
            i += 1
            continue

        m = re.match(r'^([A-Za-z0-9_\-]+)\s*:(.*)', line)
        if not m:
            i += 1
            continue

        key = m.group(1)
        rest = m.group(2).strip()

        if not rest:
            # Could be a block list: next lines are "  - item"
            block_items = []
            j = i + 1
            while j < len(lines) and re.match(r'^\s+-\s+', lines[j]):
                block_items.append(lines[j].strip()[2:].strip())
                j += 1
            if block_items:
                result[key] = block_items
                i = j
                continue
            else:
                result[key] = ''
                i += 1
                continue

        # Inline array  [a, b, c]
        if rest.startswith('[') and rest.endswith(']'):
            inner = rest[1:-1]
            items = [_unquote(s.strip()) for s in inner.split(',') if s.strip()]
            result[key] = items
            i += 1
            continue

        # Quoted string
        result[key] = _unquote(rest)
        i += 1

    return result


def _unquote(s):
    """Strip surrounding quotes from a YAML scalar."""
    s = s.strip()
    if (s.startswith('"') and s.endswith('"')) or \
       (s.startswith("'") and s.endswith("'")):
        return s[1:-1]
    return s


# ── field normalisation ───────────────────────────────────────────────────────

def normalise(fm, slug):
    """
    Produce a normalised dict from the inconsistent frontmatter keys.
    slug is always taken from posts.json (authoritative).
    """
    def first(*keys):
        for k in keys:
            v = fm.get(k)
            if v:
                if isinstance(v, list):
                    return v[0] if v else ''
                return str(v).strip()
        return ''

    title = first('meta-title', 'title')
    description = first('meta-description', 'description')
    keyword = first('primary-keyword')
    if not keyword:
        kws = fm.get('keywords') or fm.get('secondary-keywords') or \
              fm.get('secondary_keywords') or fm.get('target_keyword') or ''
        if isinstance(kws, list):
            keyword = kws[0] if kws else ''
        else:
            keyword = str(kws).strip()

    date_iso = first('date-published', 'datePublished', 'date_published',
                     'date-updated', 'dateModified')
    # normalise to YYYY-MM-DD
    date_iso = re.sub(r'[^\d\-]', '', date_iso)[:10]
    if not date_iso:
        date_iso = datetime.today().strftime('%Y-%m-%d')

    try:
        dt = datetime.strptime(date_iso, '%Y-%m-%d')
        date_human = dt.strftime('%B %-d, %Y').lower()  # e.g. "may 21, 2026"
    except ValueError:
        date_human = date_iso

    canonical = first('canonical', 'canonicalUrl')
    if not canonical:
        canonical = f'https://mirrah.app/blog/{slug}'

    cover = f'assets/covers/{slug}.png'

    return {
        'title': title,
        'description': description,
        'keyword': keyword,
        'date_iso': date_iso,
        'date_human': date_human,
        'canonical': canonical,
        'slug': slug,
        'cover': cover,
    }


# ── JSON-LD extractor ─────────────────────────────────────────────────────────

def _is_publisher_section_heading(heading_text):
    """
    Return True if a heading marks a publisher-only section that should be stripped.
    Matches:
      - headings containing 'schema' AND ('add to page head' OR 'when published')
      - headings equal to or starting with 'changelog'
    Case-insensitive.
    """
    h = heading_text.lower().strip()
    if h == 'changelog' or h.startswith('changelog'):
        return True
    if 'schema' in h and ('add to page head' in h or 'when published' in h):
        return True
    return False


def strip_publisher_sections(body):
    """
    Remove publisher-only sections from the body (before markdown conversion).
    A section is a heading line and everything until the next heading of the
    same or higher level (or end of file).
    Also removes orphaned lead-in paragraphs that contain "JSON-LD" and
    immediately precede a fenced code block that was already stripped.
    """
    lines = body.split('\n')
    result = []
    skip = False
    skip_level = 0  # the heading level being skipped (number of '#' chars)

    for line in lines:
        stripped = line.strip()
        # Detect heading level
        heading_match = re.match(r'^(#{1,6})\s+(.*)', stripped)
        if heading_match:
            hashes = heading_match.group(1)
            level = len(hashes)
            text = heading_match.group(2).strip()
            if skip:
                # If this heading is same level or higher (fewer #), end the skip
                if level <= skip_level:
                    skip = False
                    skip_level = 0
                    # Now check if this new heading itself should be skipped
                    if _is_publisher_section_heading(text):
                        skip = True
                        skip_level = level
                        continue
                    else:
                        result.append(line)
                        continue
                else:
                    # Sub-heading inside skipped section — also skip
                    continue
            else:
                if _is_publisher_section_heading(text):
                    skip = True
                    skip_level = level
                    continue
                else:
                    result.append(line)
                    continue
        else:
            if skip:
                continue
            result.append(line)

    body_clean = '\n'.join(result)

    # Remove orphaned lead-in paragraphs that contain "JSON-LD"
    # (a paragraph whose text contains "JSON-LD", followed optionally by
    # blank lines and then nothing meaningful / end of body)
    # These appear between stripped sections when the intro para was in its own
    # section. Pattern: a non-blank line containing "JSON-LD", surrounded by blanks.
    body_clean = re.sub(
        r'\n[ \t]*[^\n]*JSON-LD[^\n]*\n',
        '\n',
        body_clean
    )

    return body_clean


def extract_jsonld(body):
    """
    Collect ALL JSON-LD from the body:
      - Every ```json ... ``` fence whose content contains "@context" →
        wrap in <script type="application/ld+json">
      - Every ```html ... ``` fence that contains a
        <script type="application/ld+json"> tag → extract the script tag verbatim
    Remove each matched fence from the body.
    Return (jsonld_scripts_str, body_without_fences).
    If nothing found, return ('', body).
    """
    scripts = []

    # Pattern for ```json fences containing "@context"
    json_fence_re = re.compile(
        r'```json[ \t]*\n([\s\S]*?)\n```',
        re.MULTILINE
    )
    # Pattern for ```html fences containing a ld+json script tag
    html_fence_re = re.compile(
        r'```html[ \t]*\n([\s\S]*?)\n```',
        re.MULTILINE
    )

    # Collect all fences to remove, sorted by position
    removals = []  # list of (start, end, script_text_or_None)

    for m in json_fence_re.finditer(body):
        content = m.group(1).strip()
        if '"@context"' in content:
            script = f'<script type="application/ld+json">\n{content}\n</script>'
            removals.append((m.start(), m.end(), script))

    for m in html_fence_re.finditer(body):
        content = m.group(1)
        if '<script type="application/ld+json"' in content:
            # Extract the script tag(s) verbatim from inside the fence
            script_tag_re = re.compile(
                r'<script type="application/ld\+json"[\s\S]*?</script>',
                re.IGNORECASE
            )
            found = script_tag_re.findall(content)
            if found:
                removals.append((m.start(), m.end(), '\n'.join(found)))

    if not removals:
        return '', body

    # Sort by start position, then rebuild body with fences removed
    removals.sort(key=lambda x: x[0])

    # Build cleaned body by excising each fence region
    body_parts = []
    prev_end = 0
    for start, end, script in removals:
        body_parts.append(body[prev_end:start].rstrip())
        scripts.append(script)
        prev_end = end

    body_parts.append(body[prev_end:].lstrip('\n'))
    body_clean = '\n'.join(part for part in body_parts if part or part == '')
    # Tidy up excessive blank lines left by removals
    body_clean = re.sub(r'\n{3,}', '\n\n', body_clean).strip()

    jsonld_str = '\n'.join(scripts)
    return jsonld_str, body_clean


# ── H1 stripper ───────────────────────────────────────────────────────────────

def strip_leading_h1(body):
    """Remove the first # Heading line from the body (template supplies the H1)."""
    lines = body.split('\n')
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('# ') and not stripped.startswith('## '):
            lines.pop(i)
            # Also remove a following blank line if present
            if i < len(lines) and lines[i].strip() == '':
                lines.pop(i)
            break
        elif stripped == '':
            continue
        else:
            # Non-blank, non-H1 first content line — don't strip
            break
    return '\n'.join(lines)


# ── reading time ──────────────────────────────────────────────────────────────

def reading_time(html_body):
    """Estimate reading time from rendered HTML (strip tags, count words)."""
    plain = re.sub(r'<[^>]+>', ' ', html_body)
    words = len(plain.split())
    return max(1, round(words / 220))


# ── Markdown → HTML converter ─────────────────────────────────────────────────

def html_escape(s):
    """Escape raw text for HTML — & < > only."""
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def inline_markdown(s):
    """
    Convert inline markdown in a string to HTML.
    Order matters: links before bold/italic so URLs with * don't break.
    """
    # Escape raw HTML chars first
    s = html_escape(s)
    # Links: [text](url)
    s = re.sub(
        r'\[([^\]]+)\]\(([^)]+)\)',
        lambda m: f'<a href="{m.group(2)}">{m.group(1)}</a>',
        s
    )
    # Bold: **text**
    s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
    # Italic: *text* (not **)
    s = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<em>\1</em>', s)
    # Italic: _text_
    s = re.sub(r'(?<!_)_(?!_)(.+?)(?<!_)_(?!_)', r'<em>\1</em>', s)
    return s


# ── Block-level state machine ─────────────────────────────────────────────────

class Converter:
    """
    Stateful block-level markdown → HTML converter.
    Handles: h2/h3, paragraphs, ul/ol, blockquote, tables, hr,
    infographic callouts, FAQ sections, practice-close last paragraph,
    and JSON-LD fences (already extracted before calling, so ignored here).
    """

    INFOGRAPHIC_RE = re.compile(
        r'^\[INFOGRAPHIC:\s*(.+?)\s*\]$',
        re.IGNORECASE
    )

    def __init__(self):
        self.html_parts = []
        self.paragraph_buf = []
        self.ul_buf = []
        self.ol_buf = []
        self.bq_buf = []
        self.table_buf = []
        self.in_faq = False
        self.faq_items = []    # list of (question_html, answer_lines)
        self.faq_q_pending = None
        self.faq_ans_buf = []
        self.all_paragraphs = []  # track output paragraph indices for practice-close

    # ── flush helpers ──────────────────────────────────────────────────────────

    def _flush_paragraph(self, extra_class=None):
        if not self.paragraph_buf:
            return
        inner = inline_markdown(' '.join(self.paragraph_buf))
        cls = f' class="{extra_class}"' if extra_class else ''
        self.html_parts.append(f'<p{cls}>{inner}</p>')
        self.paragraph_buf = []

    def _flush_ul(self):
        if not self.ul_buf:
            return
        items = ''.join(f'<li>{inline_markdown(s)}</li>' for s in self.ul_buf)
        self.html_parts.append(f'<ul>{items}</ul>')
        self.ul_buf = []

    def _flush_ol(self):
        if not self.ol_buf:
            return
        items = ''.join(f'<li>{inline_markdown(s)}</li>' for s in self.ol_buf)
        self.html_parts.append(f'<ol>{items}</ol>')
        self.ol_buf = []

    def _flush_bq(self):
        if not self.bq_buf:
            return
        inner = ''.join(f'<p>{inline_markdown(s)}</p>' for s in self.bq_buf)
        self.html_parts.append(f'<blockquote>{inner}</blockquote>')
        self.bq_buf = []

    def _flush_table(self):
        if not self.table_buf:
            return
        rows = self.table_buf
        self.table_buf = []
        if len(rows) < 2:
            return

        def split_cells(row):
            row = row.strip().strip('|')
            return [c.strip() for c in row.split('|')]

        header_cells = split_cells(rows[0])
        # row[1] is separator — skip
        body_rows = rows[2:]

        ths = ''.join(f'<th>{inline_markdown(c)}</th>' for c in header_cells)
        thead = f'<thead><tr>{ths}</tr></thead>'

        tbody_rows = []
        for r in body_rows:
            tds = ''.join(f'<td>{inline_markdown(c)}</td>' for c in split_cells(r))
            tbody_rows.append(f'<tr>{tds}</tr>')
        tbody = f'<tbody>{"".join(tbody_rows)}</tbody>'
        self.html_parts.append(f'<table>{thead}{tbody}</table>')

    def _flush_all_blocks(self):
        self._flush_paragraph()
        self._flush_ul()
        self._flush_ol()
        self._flush_bq()
        self._flush_table()

    # ── FAQ helpers ────────────────────────────────────────────────────────────

    def _start_faq(self):
        self.in_faq = True
        self.faq_items = []
        self.faq_q_pending = None
        self.faq_ans_buf = []

    def _close_faq_item(self):
        if self.faq_q_pending is not None:
            ans = ' '.join(self.faq_ans_buf).strip()
            self.faq_items.append((self.faq_q_pending, ans))
            self.faq_q_pending = None
            self.faq_ans_buf = []

    def _flush_faq(self):
        self._close_faq_item()
        if not self.faq_items:
            self.in_faq = False
            return
        parts = ['<div class="faq-section">']
        for q, a in self.faq_items:
            parts.append(
                f'<div class="faq-item">'
                f'<button class="faq-toggle">{q} <span class="faq-icon">+</span></button>'
                f'<div class="faq-body"><p>{inline_markdown(a)}</p></div>'
                f'</div>'
            )
        parts.append('</div>')
        self.html_parts.append(''.join(parts))
        self.in_faq = False
        self.faq_items = []

    # ── FAQ line processing ────────────────────────────────────────────────────

    def _process_faq_line(self, line):
        stripped = line.strip()
        if not stripped:
            # blank line in FAQ: end of an answer paragraph
            return
        # A **bold question** paragraph?
        bq_match = re.match(r'^\*\*(.+?)\*\*$', stripped)
        if bq_match:
            self._close_faq_item()
            self.faq_q_pending = html_escape(bq_match.group(1))
            return
        # A heading inside FAQ — end the FAQ, emit the heading
        if stripped.startswith('## '):
            self._flush_faq()
            heading_text = stripped[3:].strip()
            self.html_parts.append(f'<h2>{inline_markdown(heading_text)}</h2>')
            return
        if stripped.startswith('### '):
            self._flush_faq()
            heading_text = stripped[4:].strip()
            self.html_parts.append(f'<h3>{inline_markdown(heading_text)}</h3>')
            return
        # HR — end FAQ
        if stripped == '---':
            self._flush_faq()
            self.html_parts.append('<hr>')
            return
        # Otherwise it's an answer line
        if self.faq_q_pending is not None:
            self.faq_ans_buf.append(stripped)

    # ── main convert ──────────────────────────────────────────────────────────

    @staticmethod
    def _strip_production_artifacts(body):
        """Remove internal production scaffolding from the body so readers never see it:
        ⚠ NEEDS-SOURCING notes (standalone lines, inline fragments, and inside table cells),
        inline source-file citations like [body_vs_mind.md], and "before publishing" asides.

        NOTE: this only HIDES the notes from readers. It does not resolve the underlying
        unsourced-claim flags the author left — that stays an editorial decision.
        """
        WARN = '⚠️?'   # ⚠ optionally followed by the emoji variation selector
        out = []
        for line in body.split('\n'):
            s = line.strip()
            # 1) whole-line production note (optionally wrapped in * _ > ) → drop it
            core = s.lstrip('*_> ').rstrip('*_ ')
            if core.startswith('⚠'):
                continue
            # 2) table row → keep the cell content, only remove the warning glyph
            if s.startswith('|'):
                line = re.sub(r'[ \t]*⚠️?[ \t]*', ' ', line)
                out.append(re.sub(r'[ \t]{2,}', ' ', line).rstrip())
                continue
            # 3) inline "⚠ [ … ]" bracketed caveat (content follows) → drop only the bracket span
            line = re.sub(r'\s*' + WARN + r'\s*\[[^\]\n]*\]', '', line)
            # 4) inline "⚠ …" note → drop from the marker to end of line
            line = re.sub(r'\s*' + WARN + r'\s*\S.*$', '', line)
            # 5) inline internal-file citations: [body_vs_mind.md], [a.md, b.md] (never INFOGRAPHIC markers)
            line = re.sub(r'\s*\[(?!INFOGRAPHIC)[^\]\n]*\.md[^\]\n]*\]', '', line)
            # 6) trailing "— … before publishing …" production aside
            line = re.sub(r'\s*[—–-]\s*[^—–.]*?before\s+publish\w*[^.]*\.?\s*$', '.', line, flags=re.IGNORECASE)
            # tidy spacing left behind
            line = re.sub(r'\s+([.,;:])', r'\1', line)
            line = re.sub(r'[ \t]{2,}', ' ', line).rstrip()
            out.append(line)
        return '\n'.join(out)

    def convert(self, markdown_body):
        """
        Convert markdown body text to HTML string.
        """
        markdown_body = self._strip_production_artifacts(markdown_body)
        lines = markdown_body.split('\n')
        # We do two passes:
        # Pass 1: build html_parts via line-by-line state machine
        # Pass 2: post-process practice-close

        i = 0
        while i < len(lines):
            line = lines[i]
            raw = line.rstrip()
            stripped = raw.strip()

            # ── FAQ mode ────────────────────────────────────────────────────
            if self.in_faq:
                self._process_faq_line(raw)
                i += 1
                continue

            # ── blank line ────────────────────────────────────────────────────
            if not stripped:
                self._flush_all_blocks()
                i += 1
                continue

            # ── h2 / h3 ───────────────────────────────────────────────────────
            if stripped.startswith('### '):
                self._flush_all_blocks()
                heading_text = stripped[4:].strip()
                self.html_parts.append(f'<h3>{inline_markdown(heading_text)}</h3>')
                i += 1
                continue

            if stripped.startswith('## '):
                self._flush_all_blocks()
                heading_text = stripped[3:].strip()
                # Detect FAQ section heading
                if re.match(r'^Frequently Asked Questions', heading_text, re.IGNORECASE):
                    self.html_parts.append(f'<h2>{inline_markdown(heading_text)}</h2>')
                    self._start_faq()
                else:
                    self.html_parts.append(f'<h2>{inline_markdown(heading_text)}</h2>')
                i += 1
                continue

            # ── skip h1 (already stripped, but guard) ─────────────────────────
            if stripped.startswith('# ') and not stripped.startswith('## '):
                i += 1
                continue

            # ── hr ────────────────────────────────────────────────────────────
            if stripped == '---':
                self._flush_all_blocks()
                self.html_parts.append('<hr>')
                i += 1
                continue

            # ── infographic marker ──────────────────────────────────────────────
            # In-body [INFOGRAPHIC: …] callouts are removed for now (the source
            # captions are designer briefs, and real panel images aren't ready).
            # Covers still appear on cards + at the top of each post. Drop the marker
            # entirely; re-enable a callout here when real panel images exist.
            if self.INFOGRAPHIC_RE.match(stripped):
                self._flush_all_blocks()
                i += 1
                continue

            # ── blockquote ────────────────────────────────────────────────────
            if stripped.startswith('> '):
                self._flush_paragraph()
                self._flush_ul()
                self._flush_ol()
                self._flush_table()
                self.bq_buf.append(stripped[2:])
                i += 1
                continue
            else:
                self._flush_bq()

            # ── unordered list ────────────────────────────────────────────────
            if re.match(r'^[\-\*] ', stripped):
                self._flush_paragraph()
                self._flush_ol()
                self._flush_table()
                self.ul_buf.append(stripped[2:])
                i += 1
                continue
            else:
                self._flush_ul()

            # ── ordered list ──────────────────────────────────────────────────
            if re.match(r'^\d+[\.\)] ', stripped):
                self._flush_paragraph()
                self._flush_ul()
                self._flush_table()
                # strip the "1. " prefix
                item_text = re.sub(r'^\d+[\.\)] ', '', stripped)
                self.ol_buf.append(item_text)
                i += 1
                continue
            else:
                self._flush_ol()

            # ── table ─────────────────────────────────────────────────────────
            if '|' in stripped and stripped.startswith('|'):
                self._flush_paragraph()
                self.table_buf.append(stripped)
                i += 1
                continue
            else:
                if self.table_buf:
                    # Check for italic *Source:* line immediately after table
                    self._flush_table()
                    # We'll check the current line below as a potential table-note
                    # (don't skip — fall through to paragraph handling)

            # ── table-note (italic *Source:* or _Source:_ line after table) ───
            source_match = re.match(r'^[\*_]Source:', stripped)
            if source_match:
                # strip the outer * or _ markers
                inner = re.sub(r'^[\*_](.*?)[\*_]$', r'\1', stripped)
                self.html_parts.append(
                    f'<em class="table-note">{html_escape(inner)}</em>'
                )
                i += 1
                continue

            # ── paragraph ────────────────────────────────────────────────────
            self.paragraph_buf.append(stripped)
            i += 1

        # end of lines — flush everything remaining
        if self.in_faq:
            self._flush_faq()
        self._flush_all_blocks()

        # ── post-process: practice-close ──────────────────────────────────────
        # Find the last <p> that contains "Mirrah" or "mirrah" and is in the
        # "What This Looks Like in Practice" section.
        # Strategy: find the last <p>...</p> in the output and check if it
        # belongs to the practice section (after the last h2).
        # We inject class="practice-close" on the very last <p> in the body
        # IF the document has a "What This Looks Like in Practice" heading.
        html = self._inject_practice_close('\n'.join(self.html_parts))
        return html

    def _inject_practice_close(self, html):
        """
        Add class="practice-close" to the last <p> in the document
        if there is a 'What This Looks Like in Practice' h2 section.
        """
        practice_h2 = re.search(
            r'<h2>[^<]*What This Looks Like in Practice[^<]*</h2>',
            html, re.IGNORECASE
        )
        if not practice_h2:
            return html

        # Find all <p> tags after the practice h2
        after = html[practice_h2.end():]
        # Find the last standalone <p> (not inside aside/blockquote/etc.)
        # We target the last <p>...</p> in the whole document
        # (which should be in the practice section if the section is last)
        last_p = list(re.finditer(r'<p>(.*?)</p>', html, re.DOTALL))
        if not last_p:
            return html

        # Walk backwards to find the last <p> that is after the practice heading
        for m in reversed(last_p):
            if m.start() > practice_h2.end():
                # Replace this occurrence
                new_tag = f'<p class="practice-close">{m.group(1)}</p>'
                html = html[:m.start()] + new_tag + html[m.end():]
                break

        return html


def markdown_to_html(body):
    c = Converter()
    return c.convert(body)


# ── token replacement ─────────────────────────────────────────────────────────

def fill_template(template, tokens):
    """Simple literal token replacement; no logic."""
    result = template
    for key, value in tokens.items():
        result = result.replace(key, str(value))
    return result


# ── card builder ─────────────────────────────────────────────────────────────

def build_card(card_template, meta, rt):
    tokens = {
        '{{CARD_URL}}': f'{meta["slug"]}.html',
        '{{CARD_TITLE}}': html_escape(meta['title']),
        '{{CARD_DESCRIPTION}}': html_escape(meta['description']),
        '{{CARD_COVER}}': meta['cover'],
        '{{CARD_DATE_HUMAN}}': meta['date_human'],
        '{{CARD_READING_TIME}}': str(rt),
    }
    return fill_template(card_template, tokens)


# ── index.html card region updater ───────────────────────────────────────────

START_MARKER = '<!-- CARDS:START -->'
END_MARKER   = '<!-- CARDS:END -->'

def update_index(index_path, cards_html):
    with open(index_path, 'r', encoding='utf-8') as f:
        content = f.read()

    start_pos = content.find(START_MARKER)
    end_pos   = content.find(END_MARKER)
    if start_pos == -1 or end_pos == -1:
        print('[WARN] index.html: CARDS markers not found — index not updated.')
        return

    new_content = (
        content[:start_pos + len(START_MARKER)]
        + '\n'
        + cards_html
        + content[end_pos:]
    )
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(new_content)


# ── per-post build ────────────────────────────────────────────────────────────

def build_post(post_entry, kits_root, template, card_template):
    slug = post_entry['slug']
    kit  = post_entry['kit']
    md_path = os.path.join(kits_root, kit, 'seo-blog-post.md')

    if not os.path.exists(md_path):
        raise FileNotFoundError(f'Source file not found: {md_path}')

    with open(md_path, 'r', encoding='utf-8') as f:
        raw = f.read()

    fm, body = parse_frontmatter(raw)
    meta = normalise(fm, slug)

    # Fallback title from slug if missing
    if not meta['title']:
        meta['title'] = slug.replace('-', ' ').title()
    if not meta['description']:
        meta['description'] = meta['title']

    # Extract JSON-LD first (```json and ```html ld+json fences) so we capture
    # schema blocks before strip_publisher_sections removes their sections.
    jsonld, body = extract_jsonld(body)

    # Strip publisher-only sections (schema headings, changelog, lead-ins, etc.)
    body = strip_publisher_sections(body)

    # Strip leading H1
    body = strip_leading_h1(body)

    # Convert markdown → HTML
    body_html = markdown_to_html(body)

    # Reading time
    rt = reading_time(body_html)

    # Fill article template
    # The template wraps {{POST_JSONLD}} in a single <script> tag.
    # extract_jsonld now returns fully-formed <script> tag(s), so we replace
    # the entire wrapper + token string to avoid double-wrapping.
    JSONLD_PLACEHOLDER = '<script type="application/ld+json">{{POST_JSONLD}}</script>'
    tokens = {
        '{{POST_TITLE}}':        html_escape(meta['title']),
        '{{POST_DESCRIPTION}}':  html_escape(meta['description']),
        '{{POST_KEYWORD}}':      html_escape(meta['keyword']),
        '{{POST_CANONICAL}}':    meta['canonical'],
        '{{POST_SLUG}}':         meta['slug'],
        '{{POST_DATE_ISO}}':     meta['date_iso'],
        '{{POST_DATE_HUMAN}}':   meta['date_human'],
        '{{POST_READING_TIME}}': str(rt),
        '{{POST_COVER}}':        meta['cover'],
        '{{POST_BODY_HTML}}':    body_html,
        JSONLD_PLACEHOLDER:      jsonld,
    }
    article_html = fill_template(template, tokens)

    # Write output file
    out_path = blog_path(f'{slug}.html')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(article_html)

    # Build card
    card = build_card(card_template, meta, rt)

    return rt, card


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    # Load posts.json
    posts_json_path = blog_path('posts.json')
    with open(posts_json_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)

    kits_root = manifest['content_kits_root']
    posts = sorted(manifest['posts'], key=lambda p: p['order'])

    # Load templates
    template_path     = blog_path('_template.html')
    card_template_path = blog_path('_card.html')
    index_path        = blog_path('index.html')

    with open(template_path, 'r', encoding='utf-8') as f:
        template = f.read()
    with open(card_template_path, 'r', encoding='utf-8') as f:
        card_template = f.read()

    today_iso = datetime.today().strftime('%Y-%m-%d')

    def is_live(post):
        """A post goes live only when explicitly published AND its publish_date
        (if any) has arrived. This is the lever for rolling posts out intelligently
        over time instead of dumping all at once. Default = draft (not live)."""
        if not post.get('published', False):
            return False
        pd = post.get('publish_date')
        return (not pd) or (pd <= today_iso)

    cards = []
    built = 0
    errors = 0
    held = []

    for post in posts:
        slug = post['slug']
        if not is_live(post):
            # Draft or scheduled-for-later: don't publish. Remove any stale page so
            # flipping a post back to draft cleanly un-publishes it.
            stale = blog_path(f'{slug}.html')
            if os.path.exists(stale):
                os.remove(stale)
            reason = 'scheduled ' + post['publish_date'] if post.get('published') and post.get('publish_date') else 'draft'
            held.append((slug, reason))
            continue
        try:
            rt, card = build_post(post, kits_root, template, card_template)
            cards.append(card)
            print(f'  ✓ {slug}  ({rt} min)')
            built += 1
        except Exception as e:
            print(f'  ✗ {slug}  ERROR: {e}')
            errors += 1

    # Update index.html card region (only live posts; empty region is valid)
    cards_html = ('\n'.join(cards) + '\n') if cards else '\n'
    update_index(index_path, cards_html)
    print(f'\n  index.html updated with {len(cards)} published card(s).')

    if held:
        print(f'\n  Held back ({len(held)}):')
        for slug, reason in held:
            print(f'    • {slug}  [{reason}]')

    print(f'\n  Build complete: {built} published, {len(held)} held, {errors} errors.')
    if errors:
        sys.exit(1)


if __name__ == '__main__':
    main()
