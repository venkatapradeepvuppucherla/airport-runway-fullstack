from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import sqlite3
from pathlib import Path

app = Flask(__name__)
app.secret_key = "change-this-secret-key"
DB_PATH = Path(__file__).with_name("airport.db")
RUNWAY_COUNT = 3

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS aircraft (
            id TEXT PRIMARY KEY,
            operation TEXT NOT NULL CHECK(operation IN ('LANDING','TAKEOFF')),
            fuel INTEGER NOT NULL CHECK(fuel BETWEEN 0 AND 100),
            priority INTEGER NOT NULL CHECK(priority BETWEEN 1 AND 5),
            waiting_time INTEGER NOT NULL CHECK(waiting_time >= 0),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS runways (
            id INTEGER PRIMARY KEY,
            available INTEGER NOT NULL DEFAULT 1 CHECK(available IN (0,1))
        );
        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            aircraft_id TEXT NOT NULL,
            operation TEXT NOT NULL,
            runway_id INTEGER NOT NULL,
            assigned_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """)
        for i in range(1, RUNWAY_COUNT + 1):
            con.execute("INSERT OR IGNORE INTO runways(id, available) VALUES (?,1)", (i,))

def aircraft_rows():
    with db() as con:
        return con.execute("SELECT * FROM aircraft").fetchall()

# Same ordering as the uploaded C++ program:
# priority ascending, fuel ascending, waiting time descending, ID ascending.
def comes_before(a, b):
    return (-a["priority"], -a["fuel"], a["waiting_time"], tuple(-ord(c) for c in a["id"])) > (
        -b["priority"], -b["fuel"], b["waiting_time"], tuple(-ord(c) for c in b["id"])
    )

def merge_sort(items):
    if len(items) <= 1:
        return items
    mid = len(items) // 2
    left, right = merge_sort(items[:mid]), merge_sort(items[mid:])
    result, i, j = [], 0, 0
    while i < len(left) and j < len(right):
        if comes_before(left[i], right[j]):
            result.append(left[i]); i += 1
        else:
            result.append(right[j]); j += 1
    return result + left[i:] + right[j:]

def bst_traversals(values):
    tree = None
    def insert(node, value):
        if node is None: return [value, None, None]
        if value < node[0]: node[1] = insert(node[1], value)
        elif value > node[0]: node[2] = insert(node[2], value)
        return node
    for value in values: tree = insert(tree, value)
    result = {"inorder": [], "preorder": [], "postorder": []}
    def walk(node):
        if not node: return
        result["preorder"].append(node[0]); walk(node[1])
        result["inorder"].append(node[0]); walk(node[2])
        result["postorder"].append(node[0])
    walk(tree)
    return result

@app.route("/")
def dashboard():
    with db() as con:
        aircraft = con.execute("SELECT * FROM aircraft").fetchall()
        runways = con.execute("SELECT * FROM runways ORDER BY id").fetchall()
        recent = con.execute("SELECT * FROM assignments ORDER BY id DESC LIMIT 8").fetchall()
    waiting = merge_sort([dict(x) for x in aircraft])
    return render_template("index.html", aircraft=waiting, runways=runways,
                           recent=recent, available=sum(r["available"] for r in runways))

@app.post("/aircraft/add")
def add_aircraft():
    aid = request.form.get("id", "").strip().upper()
    operation = request.form.get("operation", "").upper()
    try:
        fuel, priority, waiting = int(request.form["fuel"]), int(request.form["priority"]), int(request.form["waiting_time"])
        if not aid or operation not in ("LANDING", "TAKEOFF") or not 0 <= fuel <= 100 or not 1 <= priority <= 5 or waiting < 0:
            raise ValueError()
        with db() as con:
            con.execute("INSERT INTO aircraft(id,operation,fuel,priority,waiting_time) VALUES(?,?,?,?,?)",
                        (aid, operation, fuel, priority, waiting))
        flash(f"Aircraft {aid} added to the waiting queue.", "success")
    except sqlite3.IntegrityError:
        flash("That aircraft ID already exists in the waiting queue.", "error")
    except (ValueError, KeyError):
        flash("Please enter valid aircraft details.", "error")
    return redirect(url_for("dashboard"))

@app.post("/aircraft/<aid>/delete")
def delete_aircraft(aid):
    with db() as con:
        con.execute("DELETE FROM aircraft WHERE id=?", (aid,))
    flash(f"Aircraft {aid} removed from the waiting queue.", "success")
    return redirect(url_for("dashboard"))

@app.get("/api/aircraft/search")
def search_aircraft():
    q = request.args.get("id", "").strip().upper()
    with db() as con:
        row = con.execute("SELECT * FROM aircraft WHERE id=?", (q,)).fetchone()
    return jsonify(dict(row) if row else {"error": "Aircraft not found in waiting queue"}), (200 if row else 404)

@app.post("/schedule")
def schedule():
    with db() as con:
        aircraft = [dict(x) for x in con.execute("SELECT * FROM aircraft").fetchall()]
        runways = con.execute("SELECT * FROM runways WHERE available=1 ORDER BY id").fetchall()
        if not aircraft:
            flash("There are no aircraft waiting.", "error")
            return redirect(url_for("dashboard"))
        if not runways:
            flash("No runway is currently available.", "error")
            return redirect(url_for("dashboard"))
        selected = merge_sort(aircraft)[0]
        runway_id = int(request.form.get("runway_id") or runways[0]["id"])
        if runway_id not in [r["id"] for r in runways]:
            flash("Choose a runway that is currently available.", "error")
            return redirect(url_for("dashboard"))
        con.execute("INSERT INTO assignments(aircraft_id,operation,runway_id) VALUES(?,?,?)",
                    (selected["id"], selected["operation"], runway_id))
        con.execute("DELETE FROM aircraft WHERE id=?", (selected["id"],))
        con.execute("UPDATE runways SET available=0 WHERE id=?", (runway_id,))
    flash(f'{selected["id"]} ({selected["operation"]}) assigned to Runway R{runway_id}.', "success")
    return redirect(url_for("dashboard"))

@app.post("/runway/<int:rid>/release")
def release_runway(rid):
    with db() as con:
        cur = con.execute("UPDATE runways SET available=1 WHERE id=?", (rid,))
    flash(f"Runway R{rid} released." if cur.rowcount else "Runway not found.", "success")
    return redirect(url_for("dashboard"))

@app.post("/runway/<int:rid>/status")
def runway_status(rid):
    status = 1 if request.form.get("available") == "1" else 0
    with db() as con:
        cur = con.execute("UPDATE runways SET available=? WHERE id=?", (status, rid))
    flash(f"Runway R{rid} status updated.", "success" if cur.rowcount else "Runway not found.",)
    return redirect(url_for("dashboard"))

@app.get("/tools")
def tools_page():
    waiting = [dict(x) for x in aircraft_rows()]
    sorted_aircraft = merge_sort(waiting)
    traversals = bst_traversals([x["id"] for x in waiting])
    return render_template("tools.html", sorted_aircraft=sorted_aircraft, traversals=traversals)

@app.get("/api/bst/search")
def bst_search():
    q = request.args.get("id", "").strip().upper()
    ids = [x["id"] for x in aircraft_rows()]
    tree = bst_traversals(ids)
    found = q in tree["inorder"]
    return jsonify({"id": q, "found": found, "message": "Aircraft ID exists in the waiting-list BST" if found else "Aircraft ID not found in the waiting-list BST"})

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
