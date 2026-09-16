# Job Dash

Personal internship search and outreach dashboard. Single-user, local-first,
one Python file plus templates, SQLite for storage.

## Run

```
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000. The first run creates `dashboard.db` next to
`app.py` and seeds it with a few example rows. Delete that file to start clean.

## What it does

- **Dashboard** (`/`): counts of opportunities and contacts by status, plus a
  "needs action today" list with one-click buttons:
  - contacts you messaged 7+ days ago with no reply
  - applications with no movement for 14+ days
  - opportunities found 5+ days ago that you never applied to
  - contacts you have not reached out to yet
  - upcoming calls and recently updated opportunities
- **Opportunities** (`/opportunities`): table with search, status filter,
  sort, inline status dropdown, edit, delete, CSV import and export.
- **Contacts** (`/contacts`): same, with a "Touch" button that stamps
  last-contact as today. Contacts link to any number of opportunities and
  vice versa.

- **Discover** (`/discover`): postings pulled automatically from public
  sources. Filter by company, location, category, source and age. "Track"
  copies a posting into the opportunity tracker, "Dismiss" hides it.
  Postings a source stops listing are marked expired.

Thresholds for stale items are constants at the top of `app.py`.

## Where discovered postings come from

- The [SimplifyJobs Summer 2027 internship list](https://github.com/SimplifyJobs/Summer2027-Internships),
  a community-maintained GitHub repo. The app reads the JSON file the repo
  publishes, not the README, so it is one request per refresh.
- Public job-board APIs from Greenhouse, Lever and Ashby, which companies
  expose on purpose to power their own careers pages. You choose which
  companies to watch on the Discover page. Eight are watched by default.
- Only titles containing intern, internship or co-op are kept, matched on
  whole words so "Internal Audit" is excluded.

Discovery runs in the background on startup if the last run is more than
six hours old, and on demand via the Refresh button. LinkedIn is never
touched. Wellfound and YC Work at a Startup are not included because
neither offers a public listings API.

## CSV import

Header row required. Columns: `company, role, source_link, status,
date_found, date_applied, notes`. `title`/`position` work for role and
`link`/`url` for source_link, so a spreadsheet or Simplify export usually
imports after minor header renames. Extra columns are ignored.

## Not included (by design, see the spec)

No LinkedIn scraping, no auth, no multi-user, no AI extraction yet.
