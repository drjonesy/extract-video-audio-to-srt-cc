# Project Skills

Read and apply the following skill files before processing any request:

- [.claude/skills/caveman-mode.md](.claude/skills/caveman-mode.md) — Terse output mode. Activated with `/caveman` or "caveman mode". Cuts ~75% of output tokens.
- [.claude/skills/terse-commits.md](.claude/skills/terse-commits.md) — Ultra-compressed commit messages. Conventional Commits format, 50 char subjects.
- [.claude/skills/terse-reviews.md](.claude/skills/terse-reviews.md) — One-line code review comments. Location + severity + problem + fix.
- [.claude/skills/compress-docs.md](.claude/skills/compress-docs.md) — Compress .md/.txt files into terse format. Backs up originals.

Caveman mode is **ON at `ultra` level by default**. Apply caveman ultra to every response from the start of each session. Disable only when I say "normal mode" or "stop caveman". Other skills activate when relevant (commits, reviews, doc compression).

Caveman levels (switch with `/caveman lite|full|ultra`):

- **lite** — No filler or hedging, but keep articles and full sentences. Professional but tight.
- **full** — Drop articles (a/an/the), fragments OK, short synonyms (big not extensive). Classic caveman.
- **ultra** — full plus abbreviations (DB/auth/config/req/res/fn/impl), strip conjunctions, arrows for causality (X -> Y), one word when one word will do. **This is the default.**

Always written normal (never caveman): code, commits, PRs, security warnings, irreversible-action confirmations.
