# AI for Teachers — Marketing Department of Agents

**Status:** Draft for review
**Author:** d3r + Claude
**Date:** 2026-05-22
**Companion spec:** [2026-05-11-scrapper-migration-design.md](2026-05-11-scrapper-migration-design.md)

---

## Why this exists

The `digital-observatory` already scrapes AI/EdTech sources, scores them with a teacher-lens prompt, and drafts per-platform/per-language posts. But each step is a script — not an *agent*. There's no editorial voice, no editor that polishes drafts, no analyst that watches what works, no executive that synthesizes the picture and tells the user what to do next.

This spec defines an **agent-staffed marketing department** that sits on top of the existing pipeline. It exists to:

1. Make every post a tap-Approve quality on first read (so HITL doesn't become tedious).
2. Surface a single daily brief that explains what's in motion, what shipped, what worked, and what to consider next — instead of forcing the user to read raw logs.
3. Bound complexity and cost: most agents stay on local Ollama; only the executive reasoning agent uses a cheap external API.
4. Provide a clear sequence to build in slices so something useful ships every 1-2 weeks.

The end goal is to market and sell the AI-for-Teachers course to high-school+ teachers (ES + EN streams) across Bluesky + X + LinkedIn (with Instagram + YouTube as Phase 7).

---

## Foundational decisions

These shaped everything below. Recorded for future-you:

| Decision | Choice | Why |
|---|---|---|
| **Reporting model** | Daily brief + real-time firehose | High visibility without being a bottleneck |
| **Approval model** | Full HITL on every post | User retains editorial control; agents must produce tap-quality drafts |
| **Agent runtime** | Scheduled jobs wrapping persona prompts; ReAct only for CMO | Local Ollama for deterministic work; cloud API only where tool-using autonomy is needed |
| **CMO LLM provider** | OpenRouter / Cerebras free tier (MVP) → swap later | Bootstrap free, migrate when value is proven |
| **Personas** | Yes — named, with persona markdown files | Better prompts, more legible briefs, matches the `agency-agents` pattern |
| **Learning loop** | Log every approve/edit/skip; manual analysis in weekly retro | Lowest risk, clearest signal, no prompt drift |
| **First slice** | Tess + Carla + Edu + Pablo (the publishing loop) | Closes end-to-end value first; analytics + executive come next |

---

## The department

Six roles. Five run on local Ollama (Ryzen via WOL). One runs on a free-tier external API. They communicate via shared state (ChromaDB + Obsidian vault) and event triggers (n8n).

### 🔭 Tess — Trend Spotter

**Brain:** Ollama `gemma3:e4b` on d3r-ser
**Schedule:** every 4 hours (shared with the existing pipeline cron)
**Persona file:** `agents/tess.md`

**Job:** scrape AI/EdTech sources → score teacher-relevance → tag with topic + audience + language targets. Already implemented today as `observatory/intelligence/ai_evaluator.py`. Slice 1 work: extract the prompt into `agents/tess.md`, give Tess a clear voice ("rigorous, never hypey, allergic to corporate news"), let her flag *why* she rejected items in the metadata.

**Reads:** RSS feeds, WordPress sites (via the existing collectors)
**Writes:** `chromadb.items[*].metadata.teacher_relevance, audience_fit, lang_targets, post_angles, topic_tags`
**Hand-off:** Carla and Mara both consume her output.

### ✍️ Carla — Copywriter (per-language, per-platform)

**Brain:** Ollama `gemma3:e4b` on d3r-ser
**Schedule:** runs after every Tess cycle, processing items with `teacher_relevance >= 7`
**Persona file:** `agents/carla.md`

**Job:** turn one Tess-tagged item into one X post + one LinkedIn post + one Bluesky post, in the chosen language(s). Already implemented today as `observatory/intelligence/drafter.py`. Slice 1 work: persona-ify (`"warm, precise, teacher-empathic; opens with a classroom scenario"`), tighten the per-platform constraints, ensure drafts pass to Edu instead of straight to Telegram.

**Reads:** ChromaDB item + Tess metadata
**Writes:** `chromadb.drafts[*]` (new collection: one row per item × platform × lang, status: `draft`)
**Hand-off:** Edu reviews her drafts.

### 📐 Edu — Editor

**Brain:** Ollama `gemma3:e4b` on d3r-ser
**Schedule:** triggered by Carla finishing a batch
**Persona file:** `agents/edu.md`

**Job:** quality gate. Reads Carla's drafts and:
- Voice/tone check (is this on-brand for the AI-for-Teachers course?)
- Fact-check (are claims about AI tools / pedagogy accurate? flag suspect lines)
- Platform-rule check (X char count, LinkedIn no-bare-links, Bluesky tone)
- Soft duplicate check (is this angle too close to what we posted last week?)
- Verdict: `approved-for-review | revise | reject` with reasoning

If verdict is `revise`, Edu writes a one-paragraph hand-back to Carla and the next cycle re-drafts. If `approved-for-review`, the draft goes to the user's Telegram for HITL approval. If `reject`, the draft is killed.

**Reads:** Carla's drafts, brand-voice rules, recent posted history (last 30 days from ChromaDB)
**Writes:** `chromadb.drafts[*].edu_verdict, edu_reasoning`
**Hand-off:** Pablo gets approved drafts; user gets a Telegram message.

### 📤 Pablo — Publisher

**Brain:** none (no LLM)
**Schedule:** triggered by user tapping ✅ Approve in Telegram
**Persona file:** none (Pablo's a mechanical worker, not a thinker — but he gets a name for consistency)

**Job:** relay an approved draft to Postiz, store the resulting `postiz_post_id`, and mark the draft `status=scheduled`. Handle errors (Postiz down, integration auth expired) by re-routing back to Telegram with a clear failure message.

**Reads:** approved drafts from Telegram callback
**Writes:** `chromadb.drafts[*].status, postiz_post_id, scheduled_at`
**Hand-off:** Ana reads scheduled posts daily.

### 📊 Ana — Analyst

**Brain:** Ollama `gemma3:e4b` on d3r-ser
**Schedule:** every evening at 23:00 CST (after typical engagement settles)
**Persona file:** `agents/ana.md`

**Job:** for each post that shipped in the last 24h:
- Pull engagement from Postiz (impressions, clicks, likes, replies, reposts)
- Compute deltas vs. the same agent's last-7d average
- Tag winners/losers by platform, language, topic
- Write a structured summary to ChromaDB that Mara will read tomorrow morning

Phase 2: Ana also computes approve/skip rates per (Carla, language, platform) so weekly retros surface prompt-tuning candidates.

**Reads:** Postiz API, ChromaDB drafts table
**Writes:** `chromadb.daily_analytics[YYYY-MM-DD]`
**Hand-off:** Mara consumes daily.

### 🎩 Mara — CMO Reporter

**Brain:** OpenRouter free tier (start with `meta-llama/llama-3.1-70b-instruct:free` or Cerebras free tier; abstract behind a `CmoClient` so swapping is one config line)
**Schedule:** daily 07:30 CST + on-demand via Telegram `/brief`
**Persona file:** `agents/mara.md`

**Job:** read everything the team produced, decide what the user needs to know, recommend next moves.

**Two-stage evolution:**
- **Mara v0 (Slice 2):** single-call summarization. The Python wrapper does all the data gathering up front (queries ChromaDB, fetches analytics, lists drafts) and hands Mara a structured "here's everything that happened" payload. Mara writes the brief. Simple, debuggable, runs fine on Ollama.
- **Mara v1 (Slice 3):** ReAct loop with tool calls — the wrapper only hands Mara the date and a tool catalog. *She* decides what to read, in what order, and what to surface. This is the version that runs on the external API; tool-using small models aren't reliable enough for autonomous reasoning, so this is where the API spend earns its keep.

Slice 2 ships v0 fast; Slice 3 upgrades to v1 once the brief content is validated.

**Tools** (Python functions exposed via OpenAI/Anthropic tool-calling schema):
- `query_chromadb(filter, limit)` — generic semantic + metadata search
- `get_daily_analytics(date)` — pull Ana's summary
- `list_drafts(status, since_hours)` — see what's in flight
- `get_postiz_scheduled()` — see queued posts
- `read_obsidian_calendar()` — see editorial intent
- `send_telegram_message(channel, text, markdown=true)` — deliver the brief or recommendations

**Output shape (each morning):**

```
🎩 Mara's brief — Friday May 22

⏱ Last 24h
  ✓ Shipped: 4 posts (2 ES, 2 EN). Avg engagement +18% vs week.
  ⚠ 1 draft was rejected by Edu (factcheck flag on token-cost numbers).

🔭 Tess flagged 7 new items, 3 high-relevance:
  • "OpenAI's new edu API tier" — k12-en, score 9/10
  • "Anthropic Claude for grading drafts" — highered-es+en, score 8/10
  • "Andrej Karpathy on classroom AI literacy" — k12+highered-en, score 8/10

✍️ Carla has 3 drafts ready for your approval.

📊 Best-performing post this week: LinkedIn-en "Why I stopped grading manually"
   → 14 reactions, 3 comments, 1 inbound DM about the course.

💡 My take: the "personal story" hook is outperforming "news commentary" 3:1.
   Consider weighting that pattern next week. Want me to add a "personal story"
   guardrail to Carla's prompt for the next cycle?
```

The "Want me to..." is a soft suggestion, not autonomous action. User replies yes/no in Telegram; if yes, Mara writes a `prompt_proposal` to ChromaDB and you review on Sunday.

**Reads:** all ChromaDB collections (items, drafts, daily_analytics), Obsidian calendar, Postiz API
**Writes:** Telegram brief + `chromadb.briefs[YYYY-MM-DD]` (archive)
**Hand-off:** the user (the only human-facing agent).

---

## Data flow

```
                     RSS / WordPress
                            │
                            ▼
                    ┌──────────────┐
                    │  Tess (4h)   │ scores teacher-relevance
                    └──────┬───────┘
                           │ writes to chromadb.items
                           ▼
                    ┌──────────────┐
                    │ Carla (4h)   │ drafts X/LinkedIn/Bluesky per lang
                    └──────┬───────┘
                           │ writes to chromadb.drafts (status=draft)
                           ▼
                    ┌──────────────┐
                    │ Edu (triggered)  │ voice/fact/platform/dup check
                    └──────┬───────┘
                           │ writes drafts[*].edu_verdict
                  ┌────────┴────────┐
                  │ approved-       │ reject
                  │  for-review     ▼
                  ▼              (dropped)
              Telegram ──── user taps ──── ✅ → Pablo → Postiz → social
                                       └── ✏️ → user edits, Pablo
                                       └── ⏭️ → drafts[*].status=skipped
                                                       │
                                                       ▼
                                              chromadb.drafts updated
                                                       │
                                                       ▼
                                              ┌──────────────┐
                                              │  Ana (23:00) │ Postiz analytics
                                              └──────┬───────┘
                                                     │
                                                     ▼
                                            chromadb.daily_analytics
                                                     │
                                                     ▼
                                              ┌──────────────┐
                                              │ Mara (07:30) │ ReAct synthesis
                                              └──────┬───────┘
                                                     │
                                                     ▼
                                            morning brief in Telegram
```

Real-time firehose: every state transition (Tess flagged new item, Carla drafted, Edu approved/rejected, Pablo shipped, Ana found a winner) fires a separate low-priority Telegram message to a second chat. User opts in by enabling that chat.

---

## Persona file format

Adopted from `agency-agents` pattern. Each agent has a markdown file at `agents/<name>.md`:

```markdown
---
name: Tess
role: Trend Spotter
emoji: 🔭
brain: ollama:gemma3:e4b
schedule: "0 */4 * * *"
vibe: "Rigorous and skeptical; allergic to hype; trusts arxiv over press releases."
tools: [chromadb, rss_feeds, wordpress_sites]
---

# 🔭 Tess — Trend Spotter

## Identity
You are Tess. You read AI and EdTech news for a living. Your reader is a
high-school or university teacher who would otherwise drown in noise.

## Critical rules
- Score teacher_relevance honestly. "AI is impressive" is not relevant; "here's
  a tool a teacher can use Monday morning" is.
- Reject corporate news, funding announcements, and infrastructure stories
  with skip_reason="corporate-news-no-classroom-angle".
- ...

## Output schema
{
  "teacher_relevance": 1-10,
  "audience_fit": [...],
  ...
}

## Examples (good and bad)
- GOOD: "OpenAI ships a new gradebook integration" → score 9, audience: k12+highered.
- BAD: "Google announces $500M for Missouri infrastructure" → skip_reason="corporate-news-no-classroom-angle"
```

Python wrappers load the markdown, parse the frontmatter, inject the work context + a slice of agent memory from ChromaDB, then call the chosen LLM.

---

## Storage layout

Two new ChromaDB collections (today there's only `items`):

| Collection | Per-row content | Used by |
|---|---|---|
| `items` *(existing)* | One RSS / WP article + Tess's evaluation | Tess writes, Carla/Mara read |
| `drafts` *(new)* | One platform-language draft, with edu_verdict, status, postiz_post_id | Carla writes, Edu updates, Pablo updates, Ana/Mara read |
| `daily_analytics` *(new)* | One row per (date, post): engagement metrics + Ana's commentary | Ana writes, Mara reads |
| `briefs` *(new, archive)* | Mara's morning briefs | Mara writes, user can search |

Obsidian vault layout extends from today's `Inbox/{es,en}/`:

```
/vault
├── Inbox/{es,en}/           ← Carla's drafts (existing)
├── Approved/{es,en}/         ← Pablo's record of shipped posts
├── Calendar.md               ← editorial calendar Mara updates weekly
└── Briefs/YYYY-MM-DD.md      ← Mara's daily brief archive (mirrors Telegram)
```

---

## Build sequence

Each slice closes a meaningful end-to-end loop. Designed so something useful ships every 1-2 weeks.

### Slice 1 — Publishing loop  *(this is what we agreed to build first)*

**Goal:** a draft can become a published Bluesky post on your tap.

- Persona-ify Tess (extract prompt → `agents/tess.md`)
- Persona-ify Carla (extract prompt → `agents/carla.md`)
- Add Edu (new module + persona)
- Add Pablo (Postiz relay; no LLM)
- New ChromaDB collection: `drafts`
- Update n8n marketing-team workflows to route through Edu before Telegram
- Postiz deployed + Bluesky connected (the open Phase 6 work)

**End state:** an article scraped → Tess scores → Carla drafts → Edu approves-for-review → Telegram → you tap ✅ → Pablo → Bluesky.

### Slice 2 — Analyst + first real Mara

- Add Ana (Postiz analytics pull, daily run)
- Add Mara v0 (single-call summarization, NOT ReAct yet — use Ollama for simplicity)
- Mara v0 reads Ana's output + drafts in flight + recent posts → produces morning brief
- New ChromaDB collections: `daily_analytics`, `briefs`

**End state:** every morning you get a Telegram brief telling you what shipped, what's in flight, what performed.

### Slice 3 — Mara as a ReAct agent

- Add OpenRouter / Cerebras integration with provider abstraction
- Move Mara to ReAct with tool calls
- On-demand `/brief` Telegram command (Mara responds in <30s)
- Mara learns to suggest prompt edits ("want me to weight personal-story hooks?")

**End state:** Mara becomes a genuine thinking layer; user can ask her things.

### Slice 4 — Real-time firehose

- Second Telegram chat
- Each state transition fires a one-line event message
- User can toggle event types (mute "Carla drafted" if too noisy)

### Phase 7+ — Future expansion (deferred)

- **Community Listener** — monitors mentions and replies on connected social accounts; flags interesting threads for engagement
- **Audience Researcher** — periodically scrapes teacher forums (Reddit r/teachers, edu-Twitter) for emerging questions/pain points; informs Tess's scoring
- **Visual Producer** — Instagram carousels (HTML-to-PNG)
- **Funnel Architect** — UTM-tagged course-pitch links; track which posts → course signups

---

## Cost + complexity envelope

| Cost item | Estimate |
|---|---|
| Local Ollama (Ryzen) | ~free, electricity only; d3r-ser autosuspends when idle |
| OpenRouter / Cerebras free tier | $0 (rate-limited; sufficient for 1 Mara run/day) |
| OpenAI gpt-4o-mini *if* we migrate | ~$0.16/month at projected usage |
| Claude Haiku 4.5 *if* we migrate | ~$1.20/month |
| Postiz | $0 (self-hosted) |
| Net infra | **$0/month MVP, <$2/month at production** |

**Code complexity:** ~6 new Python modules (1 per agent + Pablo + provider abstraction), ~6 persona markdown files, ~2 new n8n workflows, 3 new ChromaDB collections. About 1500 LOC total estimate.

---

## Open questions / risks

1. **Telegram chat capacity** — six channels feels excessive (ES drafts, EN drafts, real-time firehose, brief, retrospective, callback). Slice 1 keeps it to 2: one per language. Add the firehose channel in Slice 4 only if you actually want it.
2. **Mara's free tier rate limits** — OpenRouter's free tier varies (50-200 req/day). One Mara morning brief = ~10 ReAct iterations. Should be fine. If we hit limits, swap to gpt-4o-mini ($0.16/month).
3. **Edu's brand-voice rules** — the editor needs explicit voice guidelines. Slice 1 deliverable includes writing those (~1 page of "what makes a teacher-relatable post").
4. **Approve/skip metadata** — the existing `marketing-team-callback.json` workflow needs a small change to log approve/skip decisions to ChromaDB. Tracked as part of Slice 1.

---

## Out of scope (explicitly)

- Auto-publishing without HITL — committed to full HITL for the foreseeable future.
- Visual content (carousels, video) — Phase 7.
- LinkedIn publishing — pending LinkedIn app review.
- Auto-tuning prompts from approve/skip rates — deferred to Phase 2 after manual analysis identifies patterns worth automating.
- Multi-tenant agent definitions — these agents serve one course (AI for Teachers). Future products would clone the pattern.

---

## Success criteria

The marketing department is "working" when:

1. **End-to-end loop works:** Tess flags an item, Carla drafts, Edu approves-for-review, you tap Telegram ✅, post lands on Bluesky within 5 min.
2. **You no longer skim raw logs.** The morning brief tells you everything you need to know in 30 seconds.
3. **Edu's filter is sharp enough** that ≥80% of drafts that reach you are tap-Approve quality (you Skip <20%).
4. **Mara's recommendations land** at least once a week ("I noticed X; should we do Y?") and you take action on ~half of them.
5. **You forget about d3r-ser.** Wake-on-LAN + autosuspend + scheduled agents = the box just works.
