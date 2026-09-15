# Internship Search & Outreach Dashboard — Build Spec

## Goal
A personal dashboard to centralize internship/job hunting: track relevant
opportunities (especially startups, which don't show up well on big job
boards), track people worth reaching out to, and track outreach status —
instead of juggling spreadsheets, browser tabs, and LinkedIn messages.

This is a personal tool, not a polished product. Prioritize "useful to me
by this weekend" over completeness. Rough edges are fine.

## Core features (MVP)

1. **Opportunity tracker**
   - Table/board of internship opportunities: company, role, source link,
     status (not applied / applied / interviewing / rejected / offer),
     date found, date applied, notes.
   - Manual add form to start. Import from CSV as a fallback for bulk adds.
   - Simple filter/sort (by status, by date, by company).

2. **Contact tracker**
   - People associated with a company/opportunity: name, role, how I
     found them (alumni, mutual connection, cold), LinkedIn/email if
     known, outreach status (not contacted / messaged / replied / call
     scheduled), notes, last contact date.
   - Link contacts to opportunities (many-to-many — one contact might be
     relevant to multiple roles at the same company).

3. **Simple dashboard/home view**
   - At-a-glance counts: opportunities by status, contacts awaiting
     follow-up (e.g. messaged >7 days ago with no reply).
   - A "needs action today" list — anything stale that needs a nudge.

## Data sources (be realistic about what's scrapable)

- **Do NOT scrape LinkedIn directly** — violates their ToS and risks
  account bans. Instead:
  - Manual entry when I find a contact via LinkedIn myself.
  - Optional: LinkedIn's official APIs are very limited for this use case,
    skip unless there's a legitimate access path.
- **Good legitimate sources for opportunities:**
  - Y Combinator's public "Work at a Startup" job board (has a public
    listings page, check for an API or just structured HTML to parse
    respectfully with rate limiting).
  - Wellfound (AngelList Talent) — check current API/ToS availability.
  - RSS feeds from company career pages where available.
  - Manual entry from Simplify/other trackers I'm already using — this
    tool can start as a *better interface* over manually-collected data
    rather than an autonomous scraper.
- Treat automated scraping as a stretch goal, not the MVP. Manual entry +
  CSV import gets 80% of the value with none of the ToS risk.

## Suggested tech stack

Keep this lightweight — it's a personal tool, not a resume project.

- **Backend:** Python + FastAPI, or just Flask if simpler feels better.
- **DB:** SQLite to start (zero setup, single file, plenty for personal
  scale). Can graduate to Postgres later if it becomes a bigger project.
- **Frontend:** Keep it simple — server-rendered templates (Jinja2) or a
  minimal React/Streamlit dashboard. Streamlit is probably the fastest
  path to something usable given the tabular, form-heavy nature of this.
- **Optional AI layer (only if genuinely useful, not for its own sake):**
  - Given a job posting's text, extract structured fields (role, key
    requirements) using an LLM call, to speed up manual entry.
  - Given a company name, suggest likely relevant people to search for
    on LinkedIn (title patterns like "recruiter," "engineering manager,"
    alumni from U of T) — this still requires me to manually search
    and add them, the AI just suggests search queries, it doesn't scrape.
  - Don't over-engineer the AI parts — this tool's value is organization,
    not automation magic.

## Non-goals (explicitly out of scope for now)

- No automated LinkedIn scraping or messaging.
- No multi-user support — this is single-user, local-first.
- No mobile app — a local web dashboard is fine.
- No fancy auth — this runs locally on my own machine.

## Stretch goals (only after MVP works)

- Browser extension or bookmarklet to quickly add a job posting from
  its page.
- Email integration (read-only) to auto-detect replies from tracked
  contacts and update status.
- Scheduled reminder notifications for stale outreach.

## Deliverable

A working local web app (can run with `python app.py` or similar single
command) with the opportunity tracker, contact tracker, and dashboard
view functional. Seed with a few example rows so I can see it working
immediately.
