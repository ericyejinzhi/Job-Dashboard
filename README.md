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

Thresholds for stale items are constants at the top of `app.py`.

## CSV import

Header row required. Columns: `company, role, source_link, status,
date_found, date_applied, notes`. `title`/`position` work for role and
`link`/`url` for source_link, so a spreadsheet or Simplify export usually
imports after minor header renames. Extra columns are ignored.

## Not included (by design, see the spec)

No LinkedIn scraping, no auth, no multi-user. Automated sourcing from
YC Work at a Startup or company RSS feeds is a stretch goal.
