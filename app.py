"""Internship Search & Outreach Dashboard.

Single-file Flask app backed by SQLite. Run with:  python app.py
"""
import csv
import io
import os
import sqlite3
from datetime import date, datetime, timedelta

from flask import (Flask, Response, flash, g, redirect, render_template,
                   request, url_for)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "dashboard.db")

OPP_STATUSES = ["not applied", "applied", "interviewing", "rejected", "offer"]
CONTACT_STATUSES = ["not contacted", "messaged", "replied", "call scheduled"]
CONTACT_SOURCES = ["alumni", "mutual connection", "cold", "recruiter reached out", "other"]

STALE_OUTREACH_DAYS = 7      # messaged, no reply
STALE_APPLICATION_DAYS = 14  # applied, no movement
STALE_UNAPPLIED_DAYS = 5     # found but never applied

app = Flask(__name__)
app.secret_key = "local-only-personal-tool"


# --------------------------------------------------------------------------
# Database
# --------------------------------------------------------------------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS opportunities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company TEXT NOT NULL,
    role TEXT NOT NULL,
    source_link TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'not applied',
    date_found TEXT,
    date_applied TEXT,
    notes TEXT DEFAULT '',
    updated_at TEXT
);
CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    company TEXT DEFAULT '',
    role TEXT DEFAULT '',
    source TEXT DEFAULT 'cold',
    linkedin TEXT DEFAULT '',
    email TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'not contacted',
    last_contact TEXT,
    notes TEXT DEFAULT '',
    updated_at TEXT
);
CREATE TABLE IF NOT EXISTS contact_opportunities (
    contact_id INTEGER NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    opportunity_id INTEGER NOT NULL REFERENCES opportunities(id) ON DELETE CASCADE,
    PRIMARY KEY (contact_id, opportunity_id)
);
"""


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    fresh = not os.path.exists(DB_PATH)
    db = sqlite3.connect(DB_PATH)
    db.executescript(SCHEMA)
    if fresh:
        seed(db)
    db.commit()
    db.close()


def seed(db):
    today = date.today()

    def d(n):
        return (today - timedelta(days=n)).isoformat()

    now = now_iso()
    opps = [
        ("Cohere", "ML Engineering Intern", "https://cohere.com/careers", "applied", d(10), d(9),
         "Applied via site. Referral from alum would help."),
        ("Ada", "Software Engineering Intern (Summer)", "https://www.ada.cx/careers", "interviewing", d(21), d(18),
         "Phone screen done, technical round next week."),
        ("Ramp", "Software Engineer Intern", "https://ramp.com/careers", "not applied", d(8), None,
         "Found on YC Work at a Startup. Need to tailor resume."),
        ("Shopify", "Dev Degree / Engineering Intern", "https://www.shopify.com/careers", "rejected", d(40), d(38),
         "Auto-rejected. Try again next cycle."),
        ("Wealthsimple", "Backend Intern", "https://www.wealthsimple.com/en-ca/careers", "not applied", d(1), None,
         "Posted yesterday on Simplify."),
    ]
    db.executemany(
        "INSERT INTO opportunities (company, role, source_link, status, date_found, date_applied, notes, updated_at)"
        " VALUES (?,?,?,?,?,?,?,?)",
        [o + (now,) for o in opps],
    )
    contacts = [
        ("Priya Shah", "Cohere", "Engineering Manager", "alumni", "https://linkedin.com/in/example-priya", "",
         "messaged", d(12), "U of T alum, messaged about ML intern role."),
        ("Marcus Lee", "Ada", "University Recruiter", "recruiter reached out", "", "marcus@example.com",
         "replied", d(3), "Coordinating technical interview."),
        ("Dana Ortiz", "Ramp", "Senior Engineer", "cold", "https://linkedin.com/in/example-dana", "",
         "not contacted", None, "Wrote a blog post about their infra. Good hook."),
        ("Sam Nguyen", "Wealthsimple", "Software Engineer", "mutual connection", "", "",
         "call scheduled", d(1), "Coffee chat Thursday 3pm."),
    ]
    db.executemany(
        "INSERT INTO contacts (name, company, role, source, linkedin, email, status, last_contact, notes, updated_at)"
        " VALUES (?,?,?,?,?,?,?,?,?,?)",
        [c + (now,) for c in contacts],
    )
    db.executemany(
        "INSERT INTO contact_opportunities (contact_id, opportunity_id) VALUES (?,?)",
        [(1, 1), (2, 2), (3, 3), (4, 5)],
    )


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def parse_date(value):
    """Return ISO date string or None. Blank or unparseable -> None."""
    value = (value or "").strip()
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d", "%b %d, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def days_since(iso):
    if not iso:
        return None
    try:
        return (date.today() - date.fromisoformat(iso)).days
    except ValueError:
        return None


app.jinja_env.globals.update(
    OPP_STATUSES=OPP_STATUSES,
    CONTACT_STATUSES=CONTACT_STATUSES,
    CONTACT_SOURCES=CONTACT_SOURCES,
    days_since=days_since,
    today=lambda: date.today().isoformat(),
)


def opp_form(form):
    return {
        "company": form.get("company", "").strip(),
        "role": form.get("role", "").strip(),
        "source_link": form.get("source_link", "").strip(),
        "status": form.get("status") if form.get("status") in OPP_STATUSES else "not applied",
        "date_found": parse_date(form.get("date_found")) or date.today().isoformat(),
        "date_applied": parse_date(form.get("date_applied")),
        "notes": form.get("notes", "").strip(),
    }


def contact_form(form):
    return {
        "name": form.get("name", "").strip(),
        "company": form.get("company", "").strip(),
        "role": form.get("role", "").strip(),
        "source": form.get("source") if form.get("source") in CONTACT_SOURCES else "other",
        "linkedin": form.get("linkedin", "").strip(),
        "email": form.get("email", "").strip(),
        "status": form.get("status") if form.get("status") in CONTACT_STATUSES else "not contacted",
        "last_contact": parse_date(form.get("last_contact")),
        "notes": form.get("notes", "").strip(),
    }


def int_list(values):
    out = []
    for v in values:
        try:
            out.append(int(v))
        except (TypeError, ValueError):
            pass
    return out


def set_contact_links(db, contact_id, opp_ids):
    db.execute("DELETE FROM contact_opportunities WHERE contact_id = ?", (contact_id,))
    db.executemany("INSERT OR IGNORE INTO contact_opportunities VALUES (?,?)",
                   [(contact_id, oid) for oid in int_list(opp_ids)])


def set_opp_links(db, opp_id, contact_ids):
    db.execute("DELETE FROM contact_opportunities WHERE opportunity_id = ?", (opp_id,))
    db.executemany("INSERT OR IGNORE INTO contact_opportunities VALUES (?,?)",
                   [(cid, opp_id) for cid in int_list(contact_ids)])


def contacts_with_links(db, where="", params=()):
    rows = db.execute(f"SELECT * FROM contacts {where} ORDER BY name COLLATE NOCASE", params).fetchall()
    links = db.execute(
        "SELECT co.contact_id, o.id, o.company, o.role FROM contact_opportunities co"
        " JOIN opportunities o ON o.id = co.opportunity_id"
    ).fetchall()
    by_contact = {}
    for link in links:
        by_contact.setdefault(link["contact_id"], []).append(link)
    return [dict(r, opportunities=by_contact.get(r["id"], [])) for r in rows]


# --------------------------------------------------------------------------
# Dashboard
# --------------------------------------------------------------------------

@app.route("/")
def dashboard():
    db = get_db()
    counts = {s: 0 for s in OPP_STATUSES}
    for r in db.execute("SELECT status, COUNT(*) n FROM opportunities GROUP BY status"):
        counts[r["status"]] = r["n"]
    ccounts = {s: 0 for s in CONTACT_STATUSES}
    for r in db.execute("SELECT status, COUNT(*) n FROM contacts GROUP BY status"):
        ccounts[r["status"]] = r["n"]

    cutoff_msg = (date.today() - timedelta(days=STALE_OUTREACH_DAYS)).isoformat()
    stale_contacts = db.execute(
        "SELECT * FROM contacts WHERE status = 'messaged' AND (last_contact IS NULL OR last_contact <= ?)"
        " ORDER BY last_contact", (cutoff_msg,)
    ).fetchall()

    cutoff_app = (date.today() - timedelta(days=STALE_APPLICATION_DAYS)).isoformat()
    stale_apps = db.execute(
        "SELECT * FROM opportunities WHERE status = 'applied' AND (date_applied IS NULL OR date_applied <= ?)"
        " ORDER BY date_applied", (cutoff_app,)
    ).fetchall()

    cutoff_found = (date.today() - timedelta(days=STALE_UNAPPLIED_DAYS)).isoformat()
    unapplied = db.execute(
        "SELECT * FROM opportunities WHERE status = 'not applied' AND date_found <= ? ORDER BY date_found",
        (cutoff_found,)
    ).fetchall()

    uncontacted = db.execute(
        "SELECT * FROM contacts WHERE status = 'not contacted' ORDER BY updated_at"
    ).fetchall()
    calls = db.execute(
        "SELECT * FROM contacts WHERE status = 'call scheduled' ORDER BY last_contact"
    ).fetchall()
    recent = db.execute(
        "SELECT * FROM opportunities ORDER BY updated_at DESC LIMIT 5"
    ).fetchall()

    return render_template(
        "dashboard.html",
        counts=counts, ccounts=ccounts,
        stale_contacts=stale_contacts, stale_apps=stale_apps, unapplied=unapplied,
        uncontacted=uncontacted, calls=calls, recent=recent,
        total_opps=sum(counts.values()), total_contacts=sum(ccounts.values()),
        action_count=len(stale_contacts) + len(stale_apps) + len(unapplied) + len(uncontacted),
        STALE_OUTREACH_DAYS=STALE_OUTREACH_DAYS, STALE_APPLICATION_DAYS=STALE_APPLICATION_DAYS,
        STALE_UNAPPLIED_DAYS=STALE_UNAPPLIED_DAYS,
    )


# --------------------------------------------------------------------------
# Opportunities
# --------------------------------------------------------------------------

OPP_SORTS = {
    "date_found": "date_found DESC, id DESC",
    "date_found_asc": "date_found ASC, id ASC",
    "date_applied": "date_applied DESC, id DESC",
    "company": "company COLLATE NOCASE ASC, role COLLATE NOCASE ASC",
    "status": "status ASC, date_found DESC",
    "updated": "updated_at DESC",
}


@app.route("/opportunities")
def opportunities():
    db = get_db()
    status = request.args.get("status", "")
    q = request.args.get("q", "").strip()
    sort = request.args.get("sort", "date_found")
    order = OPP_SORTS.get(sort, OPP_SORTS["date_found"])

    where, params = [], []
    if status in OPP_STATUSES:
        where.append("status = ?")
        params.append(status)
    if q:
        where.append("(company LIKE ? OR role LIKE ? OR notes LIKE ?)")
        params += [f"%{q}%"] * 3
    sql = "SELECT * FROM opportunities"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += f" ORDER BY {order}"
    rows = db.execute(sql, params).fetchall()

    links = db.execute(
        "SELECT co.opportunity_id, c.id, c.name FROM contact_opportunities co JOIN contacts c ON c.id = co.contact_id"
    ).fetchall()
    by_opp = {}
    for link in links:
        by_opp.setdefault(link["opportunity_id"], []).append(link)
    rows = [dict(r, contacts=by_opp.get(r["id"], [])) for r in rows]

    return render_template("opportunities.html", rows=rows, status=status, q=q, sort=sort)


@app.route("/opportunities/new", methods=["GET", "POST"])
def opportunity_new():
    db = get_db()
    contacts = db.execute("SELECT id, name, company FROM contacts ORDER BY name COLLATE NOCASE").fetchall()
    if request.method == "POST":
        data = opp_form(request.form)
        if not data["company"] or not data["role"]:
            flash("Company and role are required.", "error")
            return render_template("opportunity_form.html", opp=data, contacts=contacts,
                                   linked=set(int_list(request.form.getlist("contact_ids")))), 400
        if data["status"] != "not applied" and not data["date_applied"]:
            data["date_applied"] = date.today().isoformat()
        cur = db.execute(
            "INSERT INTO opportunities (company, role, source_link, status, date_found, date_applied, notes, updated_at)"
            " VALUES (:company, :role, :source_link, :status, :date_found, :date_applied, :notes, :updated_at)",
            dict(data, updated_at=now_iso()),
        )
        set_opp_links(db, cur.lastrowid, request.form.getlist("contact_ids"))
        db.commit()
        flash(f"Added {data['company']}: {data['role']}.", "ok")
        return redirect(url_for("opportunities"))
    prefill = {"company": request.args.get("company", ""), "status": "not applied",
               "date_found": date.today().isoformat()}
    linked = set(int_list([request.args.get("contact_id")]))
    return render_template("opportunity_form.html", opp=prefill, contacts=contacts, linked=linked)


@app.route("/opportunities/<int:oid>/edit", methods=["GET", "POST"])
def opportunity_edit(oid):
    db = get_db()
    opp = db.execute("SELECT * FROM opportunities WHERE id = ?", (oid,)).fetchone()
    if opp is None:
        return "Not found", 404
    contacts = db.execute("SELECT id, name, company FROM contacts ORDER BY name COLLATE NOCASE").fetchall()
    if request.method == "POST":
        data = opp_form(request.form)
        if not data["company"] or not data["role"]:
            flash("Company and role are required.", "error")
            return render_template("opportunity_form.html", opp=dict(data, id=oid), contacts=contacts,
                                   linked=set(int_list(request.form.getlist("contact_ids")))), 400
        if data["status"] != "not applied" and not data["date_applied"]:
            data["date_applied"] = date.today().isoformat()
        db.execute(
            "UPDATE opportunities SET company=:company, role=:role, source_link=:source_link, status=:status,"
            " date_found=:date_found, date_applied=:date_applied, notes=:notes, updated_at=:updated_at WHERE id=:id",
            dict(data, updated_at=now_iso(), id=oid),
        )
        set_opp_links(db, oid, request.form.getlist("contact_ids"))
        db.commit()
        flash("Saved.", "ok")
        return redirect(url_for("opportunities"))
    linked = {r["contact_id"] for r in
              db.execute("SELECT contact_id FROM contact_opportunities WHERE opportunity_id = ?", (oid,))}
    return render_template("opportunity_form.html", opp=dict(opp), contacts=contacts, linked=linked)


@app.route("/opportunities/<int:oid>/status", methods=["POST"])
def opportunity_status(oid):
    """Quick status change from a list view."""
    db = get_db()
    status = request.form.get("status")
    if status in OPP_STATUSES:
        params = {"status": status, "updated_at": now_iso(), "id": oid}
        sql = "UPDATE opportunities SET status=:status, updated_at=:updated_at"
        if status != "not applied":
            sql += ", date_applied = COALESCE(date_applied, :today)"
            params["today"] = date.today().isoformat()
        db.execute(sql + " WHERE id=:id", params)
        db.commit()
    return redirect(request.referrer or url_for("opportunities"))


@app.route("/opportunities/<int:oid>/delete", methods=["POST"])
def opportunity_delete(oid):
    db = get_db()
    db.execute("DELETE FROM opportunities WHERE id = ?", (oid,))
    db.commit()
    flash("Deleted.", "ok")
    return redirect(url_for("opportunities"))


CSV_COLUMNS = ["company", "role", "source_link", "status", "date_found", "date_applied", "notes"]


@app.route("/opportunities/import", methods=["GET", "POST"])
def opportunity_import():
    if request.method == "POST":
        f = request.files.get("file")
        if not f or not f.filename:
            flash("Choose a CSV file.", "error")
            return redirect(url_for("opportunity_import"))
        text = f.read().decode("utf-8-sig", errors="replace")
        reader = csv.DictReader(io.StringIO(text))
        db = get_db()
        added = skipped = 0
        for raw in reader:
            row = {(k or "").strip().lower().replace(" ", "_"): (v or "").strip() for k, v in raw.items()}
            company = row.get("company", "")
            role = row.get("role") or row.get("title") or row.get("position", "")
            if not company or not role:
                skipped += 1
                continue
            status = row.get("status", "").lower()
            if status not in OPP_STATUSES:
                status = "applied" if row.get("date_applied") else "not applied"
            db.execute(
                "INSERT INTO opportunities (company, role, source_link, status, date_found, date_applied, notes, updated_at)"
                " VALUES (?,?,?,?,?,?,?,?)",
                (company, role, row.get("source_link") or row.get("link") or row.get("url", ""), status,
                 parse_date(row.get("date_found")) or date.today().isoformat(),
                 parse_date(row.get("date_applied")), row.get("notes", ""), now_iso()),
            )
            added += 1
        db.commit()
        flash(f"Imported {added} opportunities ({skipped} skipped for missing company/role).", "ok")
        return redirect(url_for("opportunities"))
    return render_template("import.html", columns=CSV_COLUMNS)


@app.route("/opportunities/export.csv")
def opportunity_export():
    db = get_db()
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(CSV_COLUMNS)
    for r in db.execute(f"SELECT {', '.join(CSV_COLUMNS)} FROM opportunities ORDER BY date_found DESC"):
        w.writerow([r[c] or "" for c in CSV_COLUMNS])
    return Response(out.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=opportunities.csv"})


# --------------------------------------------------------------------------
# Contacts
# --------------------------------------------------------------------------

@app.route("/contacts")
def contacts():
    db = get_db()
    status = request.args.get("status", "")
    q = request.args.get("q", "").strip()
    where, params = [], []
    if status in CONTACT_STATUSES:
        where.append("status = ?")
        params.append(status)
    if q:
        where.append("(name LIKE ? OR company LIKE ? OR role LIKE ? OR notes LIKE ?)")
        params += [f"%{q}%"] * 4
    clause = ("WHERE " + " AND ".join(where)) if where else ""
    rows = contacts_with_links(db, clause, params)
    return render_template("contacts.html", rows=rows, status=status, q=q)


@app.route("/contacts/new", methods=["GET", "POST"])
def contact_new():
    db = get_db()
    opps = db.execute("SELECT id, company, role FROM opportunities ORDER BY company COLLATE NOCASE").fetchall()
    if request.method == "POST":
        data = contact_form(request.form)
        if not data["name"]:
            flash("Name is required.", "error")
            return render_template("contact_form.html", contact=data, opps=opps,
                                   linked=set(int_list(request.form.getlist("opportunity_ids")))), 400
        if data["status"] != "not contacted" and not data["last_contact"]:
            data["last_contact"] = date.today().isoformat()
        cur = db.execute(
            "INSERT INTO contacts (name, company, role, source, linkedin, email, status, last_contact, notes, updated_at)"
            " VALUES (:name, :company, :role, :source, :linkedin, :email, :status, :last_contact, :notes, :updated_at)",
            dict(data, updated_at=now_iso()),
        )
        set_contact_links(db, cur.lastrowid, request.form.getlist("opportunity_ids"))
        db.commit()
        flash(f"Added {data['name']}.", "ok")
        return redirect(url_for("contacts"))
    prefill = {"company": request.args.get("company", ""), "status": "not contacted", "source": "cold"}
    linked = set(int_list([request.args.get("opportunity_id")]))
    return render_template("contact_form.html", contact=prefill, opps=opps, linked=linked)


@app.route("/contacts/<int:cid>/edit", methods=["GET", "POST"])
def contact_edit(cid):
    db = get_db()
    c = db.execute("SELECT * FROM contacts WHERE id = ?", (cid,)).fetchone()
    if c is None:
        return "Not found", 404
    opps = db.execute("SELECT id, company, role FROM opportunities ORDER BY company COLLATE NOCASE").fetchall()
    if request.method == "POST":
        data = contact_form(request.form)
        if not data["name"]:
            flash("Name is required.", "error")
            return render_template("contact_form.html", contact=dict(data, id=cid), opps=opps,
                                   linked=set(int_list(request.form.getlist("opportunity_ids")))), 400
        if data["status"] != "not contacted" and not data["last_contact"]:
            data["last_contact"] = date.today().isoformat()
        db.execute(
            "UPDATE contacts SET name=:name, company=:company, role=:role, source=:source, linkedin=:linkedin,"
            " email=:email, status=:status, last_contact=:last_contact, notes=:notes, updated_at=:updated_at"
            " WHERE id=:id",
            dict(data, updated_at=now_iso(), id=cid),
        )
        set_contact_links(db, cid, request.form.getlist("opportunity_ids"))
        db.commit()
        flash("Saved.", "ok")
        return redirect(url_for("contacts"))
    linked = {r["opportunity_id"] for r in
              db.execute("SELECT opportunity_id FROM contact_opportunities WHERE contact_id = ?", (cid,))}
    return render_template("contact_form.html", contact=dict(c), opps=opps, linked=linked)


@app.route("/contacts/<int:cid>/status", methods=["POST"])
def contact_status(cid):
    """Quick status change; bumps last_contact to today when the change implies contact happened."""
    db = get_db()
    status = request.form.get("status")
    if status in CONTACT_STATUSES:
        params = {"status": status, "updated_at": now_iso(), "id": cid}
        sql = "UPDATE contacts SET status=:status, updated_at=:updated_at"
        if status != "not contacted":
            sql += ", last_contact = :today"
            params["today"] = date.today().isoformat()
        db.execute(sql + " WHERE id=:id", params)
        db.commit()
    return redirect(request.referrer or url_for("contacts"))


@app.route("/contacts/<int:cid>/touch", methods=["POST"])
def contact_touch(cid):
    """'Followed up today': resets the stale clock without changing status."""
    db = get_db()
    db.execute("UPDATE contacts SET last_contact = ?, updated_at = ? WHERE id = ?",
               (date.today().isoformat(), now_iso(), cid))
    db.commit()
    return redirect(request.referrer or url_for("dashboard"))


@app.route("/contacts/<int:cid>/delete", methods=["POST"])
def contact_delete(cid):
    db = get_db()
    db.execute("DELETE FROM contacts WHERE id = ?", (cid,))
    db.commit()
    flash("Deleted.", "ok")
    return redirect(url_for("contacts"))


# --------------------------------------------------------------------------

if __name__ == "__main__":
    init_db()
    print(f"Database: {DB_PATH}")
    app.run(host="127.0.0.1", port=5000, debug=True)
