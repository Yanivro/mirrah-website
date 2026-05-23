#!/bin/bash
# Mirrah blog daily auto-publisher — run by launchd (app.mirrah.blog-autopublish).
#
# Rebuilds the blog from posts.json. When a scheduled post's publish_date has
# arrived, build.py emits its page + adds it to the index, which shows up as a
# git change; we then commit and push, deploying via GitHub Pages. On any day
# with nothing newly due, there's no diff and nothing is pushed.
#
# Safe by design: only commits when blog/ or index.html actually changed, only
# operates on main, and aborts (without pushing) if the build fails.

set -euo pipefail

# launchd runs with a minimal PATH — set one that finds git + python3.
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

REPO="/Users/yanivrozenblat/claude-projects/mirrah-website"
cd "$REPO"

ts() { date '+%Y-%m-%d %H:%M:%S'; }

branch="$(git rev-parse --abbrev-ref HEAD)"
if [ "$branch" != "main" ]; then
  echo "$(ts) skip — on branch '$branch', not main"
  exit 0
fi

# Sync with remote first so the push can fast-forward (autostash guards stray state).
git pull --rebase --autostash origin main

python3 blog/build.py

if [ -n "$(git status --porcelain blog index.html)" ]; then
  git add blog index.html
  git commit -m "Auto-publish scheduled blog post(s) [$(date '+%Y-%m-%d')]

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
  git push origin main
  echo "$(ts) published — pushed to main"
else
  echo "$(ts) nothing newly due — no changes"
fi
