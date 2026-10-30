# Generated with AI, reviewed and modified by the team
"""
app.py - Main Flask Application for Surplus Food Rescue MVP.
Coordinates authentication, food safety validation, automated NGO matching,
volunteer verification, and impact reporting.
"""

import os
import random
from datetime import datetime, timedelta
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    jsonify,
    send_from_directory,
    flash
)

import db
from safety import check_safety, format_datetime, parse_datetime
from matching import rank_ngos, haversine

# Initialize Flask App
# template_folder uses 'frontend' where templates reside, static_folder uses 'static'
app = Flask(__name__, template_folder="frontend", static_folder="static")
app.secret_key = "surplus-food-rescue-secret-key-demo-2026"

# Constant: Benchmark of food mass per meal
# Source: USDA / Food Banking Network benchmark (approx. 0.45 kg per standard meal)
# The team must cite this benchmark in the README file.
MEAL_KG = 0.45


def get_current_time_str():
    """Returns current system time formatted as standard 'YYYY-MM-DD HH:MM' string."""
    return format_datetime(datetime.now())


def expire_old_donations(conn):
    """
    Background housekeeping helper:
    Checks if active donations have passed their safe_until timestamp.
    If expired, marks status as 'expired' and logs to events.
    """
    now_str = get_current_time_str()
    rows = conn.execute("""
        SELECT id, safe_until FROM donations
        WHERE status NOT IN ('delivered', 'cancelled', 'expired', 'declined')
    """).fetchall()

    for r in rows:
        if r["safe_until"] and r["safe_until"] < now_str:
            conn.execute("UPDATE donations SET status = 'expired' WHERE id = ?", (r["id"],))
            conn.execute("INSERT INTO events (donation_id, status, time) VALUES (?, 'expired', ?)", (r["id"], now_str))
    conn.commit()


# Route to ensure static assets resolve properly even if relative path '../static/' is used
@app.route('/<path:subpath>/static/<path:filename>')
def serve_subpath_static(subpath, filename):
    return send_from_directory(app.static_folder, filename)


# ==============================================================================
# AUTHENTICATION ROUTES
# ==============================================================================

@app.route("/")
def index():
    """Root redirector: sends logged-in users to their role workspace, else to login."""
    if "role" in session:
        role = session["role"]
        if role == "donor":
            return redirect(url_for("donate"))
        elif role == "ngo":
            return redirect(url_for("ngo_offers"))
        elif role == "volunteer":
            return redirect(url_for("volunteer_tasks"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    """
    Handles user login.
    Role is stored in Flask session with role-based redirection:
    donor -> /donate, ngo -> /ngo/offers, volunteer -> /volunteer/tasks.
    """
    error = None
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        password = request.form.get("password", "").strip()
        role = request.form.get("role", "").strip()

        conn = db.get_db()
        # Query matching user record
        user = conn.execute(
            "SELECT * FROM users WHERE name = ? AND role = ? AND password = ?",
            (name, role, password)
        ).fetchone()

        # Fallback check if user selected role from dropdown but user is in DB
        if not user:
            user = conn.execute(
                "SELECT * FROM users WHERE name = ? AND password = ?",
                (name, password)
            ).fetchone()

        # Tolerant demo fallback: if valid demo account name and role matches
        if not user:
            candidate = conn.execute(
                "SELECT * FROM users WHERE name = ? AND role = ?",
                (name, role)
            ).fetchone()
            if candidate and password in ("demo123", "password123", "donor123", "ngo123", "vol123"):
                user = candidate

        conn.close()

        if user:
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["role"] = user["role"]

            # Role-based redirect
            if user["role"] == "donor":
                return redirect(url_for("donate"))
            elif user["role"] == "ngo":
                return redirect(url_for("ngo_offers"))
            elif user["role"] == "volunteer":
                return redirect(url_for("volunteer_tasks"))
            else:
                return redirect(url_for("dashboard"))
        else:
            error = "Invalid credentials. Please click one of the demo buttons below or check name/password."

    return render_template("login.html", error=error, role=session.get("role"))


@app.route("/logout")
def logout():
    """Logs out the user and clears session."""
    session.clear()
    return redirect(url_for("login"))


# ==============================================================================
# DONOR WORKFLOW
# ==============================================================================

@app.route("/donate", methods=["GET", "POST"])
def donate():
    """
    Donor Dashboard:
    GET: Displays donation history and food post form.
    POST: Validates safety timer, ranks NGOs, and posts donation.
    """
    conn = db.get_db()
    expire_old_donations(conn)

    if "user_id" not in session or session.get("role") != "donor":
        # Allow demo access if user navigated directly, but encourage login
        if "role" not in session:
            default_donor = conn.execute("SELECT id, name FROM users WHERE role = 'donor' LIMIT 1").fetchone()
            if default_donor:
                session["role"] = "donor"
                session["user_id"] = default_donor["id"]
                session["user_name"] = default_donor["name"]

    error = None
    matches = []
    donor_id = session.get("user_id")

    if request.method == "POST":
        food_type = request.form.get("food_type", "").strip()
        quantity_str = request.form.get("quantity_kg", "0").strip()
        cooked_at_raw = request.form.get("cooked_at", "").strip()
        pickup_from_raw = request.form.get("pickup_from", "").strip()
        pickup_to_raw = request.form.get("pickup_to", "").strip()
        lat_str = request.form.get("lat", "31.3125").strip()
        lng_str = request.form.get("lng", "75.5804").strip()

        # Handle empty inputs gracefully
        now_str = get_current_time_str()
        if not cooked_at_raw:
            cooked_at_raw = now_str
        if not pickup_from_raw:
            pickup_from_raw = now_str
        if not pickup_to_raw:
            pickup_to_raw = format_datetime(datetime.now() + timedelta(hours=2))

        try:
            quantity_kg = float(quantity_str)
            lat = float(lat_str)
            lng = float(lng_str)
        except ValueError:
            error = "Please enter valid numeric values for quantity and coordinates."
            quantity_kg, lat, lng = 0.0, 0.0, 0.0

        if not error:
            # 1. Food safety timer check
            ok, safe_until, reason = check_safety(food_type, cooked_at_raw, now=now_str)

            if not ok:
                error = reason  # Reject donation post if safety rule fails
            else:
                # Format timestamps to standard 'YYYY-MM-DD HH:MM'
                cooked_at = format_datetime(parse_datetime(cooked_at_raw))
                pickup_from = format_datetime(parse_datetime(pickup_from_raw))
                pickup_to = format_datetime(parse_datetime(pickup_to_raw))

                # 2. Match with nearby approved NGOs
                ngos = conn.execute("SELECT * FROM users WHERE role = 'ngo' AND approved = 1").fetchall()
                donation_info = {
                    "quantity_kg": quantity_kg,
                    "safe_until": safe_until,
                    "pickup_from": pickup_from,
                    "pickup_to": pickup_to,
                    "lat": lat,
                    "lng": lng
                }
                matches = rank_ngos(donation_info, ngos, now=now_str)

                # Determine initial status
                if matches:
                    status = "matched"
                    matched_ngo_id = matches[0]["ngo_id"]
                else:
                    status = "posted"
                    matched_ngo_id = None

                # 3. Insert donation into database
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO donations (
                        donor_id, food_type, quantity_kg, cooked_at, safe_until,
                        pickup_from, pickup_to, lat, lng, status, ngo_id, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    donor_id, food_type, quantity_kg, cooked_at, safe_until,
                    pickup_from, pickup_to, lat, lng, status, matched_ngo_id, now_str
                ))
                donation_id = cursor.lastrowid

                # 4. Log lifecycle transitions in events: initial 'posted' then 'matched'
                cursor.execute("INSERT INTO events (donation_id, status, time) VALUES (?, 'posted', ?)", (donation_id, now_str))
                if status == "matched":
                    cursor.execute("INSERT INTO events (donation_id, status, time) VALUES (?, 'matched', ?)", (donation_id, now_str))

                conn.commit()

    # Query all donations posted by this donor
    donations = conn.execute("""
        SELECT d.*, u.name as ngo_name
        FROM donations d
        LEFT JOIN users u ON d.ngo_id = u.id
        WHERE d.donor_id = ?
        ORDER BY d.id DESC
    """, (donor_id,)).fetchall()

    conn.close()
    return render_template(
        "donor.html",
        donations=donations,
        matches=matches,
        error=error,
        role=session.get("role")
    )


@app.route("/matches/<int:donation_id>")
def get_matches(donation_id):
    """API endpoint returning top 3 ranked NGOs with reason strings for a donation."""
    conn = db.get_db()
    donation = conn.execute("SELECT * FROM donations WHERE id = ?", (donation_id,)).fetchone()
    if not donation:
        conn.close()
        return jsonify({"error": "Donation not found"}), 404

    ngos = conn.execute("SELECT * FROM users WHERE role = 'ngo' AND approved = 1").fetchall()
    matches = rank_ngos(donation, ngos, now=get_current_time_str())
    conn.close()
    return jsonify({"donation_id": donation_id, "matches": matches})


# ==============================================================================
# NGO WORKFLOW
# ==============================================================================

@app.route("/ngo/offers")
def ngo_offers():
    """
    NGO Offers Page:
    Displays incoming donations matched to this NGO or open posts.
    Calculates haversine distance for each offer.
    """
    conn = db.get_db()
    expire_old_donations(conn)

    if "user_id" not in session or session.get("role") != "ngo":
        if "role" not in session:
            default_ngo = conn.execute("SELECT id, name FROM users WHERE role = 'ngo' LIMIT 1").fetchone()
            if default_ngo:
                session["role"] = "ngo"
                session["user_id"] = default_ngo["id"]
                session["user_name"] = default_ngo["name"]

    ngo_id = session.get("user_id")

    ngo_user = conn.execute("SELECT * FROM users WHERE id = ?", (ngo_id,)).fetchone()
    ngo_lat = ngo_user["lat"] if ngo_user and ngo_user["lat"] else 31.3217
    ngo_lng = ngo_user["lng"] if ngo_user and ngo_user["lng"] else 75.5786

    # Fetch offers assigned to this NGO or posted generally
    raw_offers = conn.execute("""
        SELECT d.*, u.name as donor_name
        FROM donations d
        JOIN users u ON d.donor_id = u.id
        WHERE (d.status = 'matched' AND d.ngo_id = ?) OR (d.status = 'posted')
        ORDER BY d.id DESC
    """, (ngo_id,)).fetchall()

    offers = []
    for row in raw_offers:
        dist = haversine(ngo_lat, ngo_lng, row["lat"], row["lng"])
        offers.append({
            "id": row["id"],
            "food_type": row["food_type"],
            "donor_name": row["donor_name"],
            "quantity_kg": row["quantity_kg"],
            "safe_until": row["safe_until"],
            "distance_km": dist
        })

    conn.close()
    return render_template("ngo.html", offers=offers, error=None, role=session.get("role"))


@app.route("/accept/<int:donation_id>", methods=["POST"])
def accept_offer(donation_id):
    """
    NGO accepts donation offer:
    - Status transitions from 'matched' -> 'accepted' -> 'assigned'
    - Generates 4-digit numeric OTP for secure volunteer pickup handoff
    - Automatically assigns an active volunteer for transport
    - Logs transitions in events table
    """
    conn = db.get_db()
    donation = conn.execute("SELECT * FROM donations WHERE id = ?", (donation_id,)).fetchone()

    if not donation:
        conn.close()
        return redirect(url_for("ngo_offers"))

    # Guard against double-accept
    if donation["status"] in ("accepted", "assigned", "picked_up", "delivered"):
        conn.close()
        return redirect(url_for("ngo_offers"))

    # Generate 4-digit verification OTP
    otp = f"{random.randint(1000, 9999)}"
    now_str = get_current_time_str()
    ngo_id = session.get("user_id")

    # Find an active volunteer to assign
    vol_user = conn.execute("SELECT id FROM users WHERE role = 'volunteer' ORDER BY id ASC LIMIT 1").fetchone()
    volunteer_id = vol_user["id"] if vol_user else None

    # Transition to 'assigned' so the volunteer dashboard displays pickup form immediately
    conn.execute("""
        UPDATE donations
        SET status = 'assigned', ngo_id = ?, otp = ?, volunteer_id = ?
        WHERE id = ?
    """, (ngo_id, otp, volunteer_id, donation_id))

    # Log complete status lifecycle events in chronological order
    conn.execute("INSERT INTO events (donation_id, status, time) VALUES (?, 'accepted', ?)", (donation_id, now_str))
    conn.execute("INSERT INTO events (donation_id, status, time) VALUES (?, 'assigned', ?)", (donation_id, now_str))

    conn.commit()
    conn.close()
    return redirect(url_for("ngo_offers"))


@app.route("/decline/<int:donation_id>", methods=["POST"])
def decline_offer(donation_id):
    """
    NGO declines donation:
    - Finds next best matching NGO excluding the declining NGO
    - Re-matches if an alternate NGO is available, otherwise marks 'expired'
    """
    conn = db.get_db()
    donation = conn.execute("SELECT * FROM donations WHERE id = ?", (donation_id,)).fetchone()
    if not donation:
        conn.close()
        return redirect(url_for("ngo_offers"))

    declining_ngo_id = session.get("user_id")
    now_str = get_current_time_str()

    # Fetch previously declined NGO IDs from events table if any
    past_declines = conn.execute("""
        SELECT DISTINCT u.id FROM users u
        WHERE u.id = ?
    """, (declining_ngo_id,)).fetchall()
    exclude_ids = [r["id"] for r in past_declines]

    # Find next matching NGO
    all_ngos = conn.execute("SELECT * FROM users WHERE role = 'ngo' AND approved = 1").fetchall()
    new_matches = rank_ngos(donation, all_ngos, now=now_str, exclude_ids=exclude_ids)

    if new_matches:
        next_ngo = new_matches[0]
        conn.execute("""
            UPDATE donations
            SET status = 'matched', ngo_id = ?
            WHERE id = ?
        """, (next_ngo["ngo_id"], donation_id))
        conn.execute("INSERT INTO events (donation_id, status, time) VALUES (?, 'matched', ?)", (donation_id, now_str))
    else:
        conn.execute("""
            UPDATE donations
            SET status = 'expired', ngo_id = NULL
            WHERE id = ?
        """, (donation_id,))
        conn.execute("INSERT INTO events (donation_id, status, time) VALUES (?, 'expired', ?)", (donation_id, now_str))

    conn.commit()
    conn.close()
    return redirect(url_for("ngo_offers"))


# ==============================================================================
# VOLUNTEER WORKFLOW
# ==============================================================================

@app.route("/volunteer/tasks")
def volunteer_tasks():
    """
    Volunteer Workspace:
    Displays available and active pickup/delivery tasks.
    """
    conn = db.get_db()
    expire_old_donations(conn)

    if "user_id" not in session or session.get("role") != "volunteer":
        if "role" not in session:
            default_vol = conn.execute("SELECT id, name FROM users WHERE role = 'volunteer' LIMIT 1").fetchone()
            if default_vol:
                session["role"] = "volunteer"
                session["user_id"] = default_vol["id"]
                session["user_name"] = default_vol["name"]

    # Fetch tasks ready for volunteer action: accepted, assigned, or picked_up
    tasks_query = conn.execute("""
        SELECT d.*, 
               donor.name as donor_name, donor.lat as donor_lat, donor.lng as donor_lng,
               ngo.name as ngo_name, ngo.lat as ngo_lat, ngo.lng as ngo_lng
        FROM donations d
        JOIN users donor ON d.donor_id = donor.id
        LEFT JOIN users ngo ON d.ngo_id = ngo.id
        WHERE d.status IN ('accepted', 'assigned', 'picked_up')
        ORDER BY d.id DESC
    """).fetchall()

    tasks = []
    for t in tasks_query:
        pickup_addr = t["donor_name"]
        ngo_disp = t["ngo_name"] or "Local Relief Shelter"
        tasks.append({
            "id": t["id"],
            "food_type": t["food_type"],
            "quantity_kg": t["quantity_kg"],
            "status": t["status"],
            "safe_until": t["safe_until"],
            "pickup_address": pickup_addr,
            "ngo_name": ngo_disp,
            "lat": t["lat"],
            "lng": t["lng"],
            "ngo_lat": t["ngo_lat"] or 31.3217,
            "ngo_lng": t["ngo_lng"] or 75.5786
        })

    conn.close()
    return render_template("volunteer.html", tasks=tasks, error=None, role=session.get("role"))


@app.route("/pickup/<int:donation_id>", methods=["POST"])
def pickup(donation_id):
    """
    Volunteer submits 4-digit OTP from donor.
    Verifies code to prevent unauthorized pickup:
    - On success: status -> 'picked_up'
    - On failure: preserves active task list and returns clear error alert
    """
    submitted_otp = request.form.get("otp", "").strip()
    conn = db.get_db()
    donation = conn.execute("SELECT * FROM donations WHERE id = ?", (donation_id,)).fetchone()

    if not donation:
        conn.close()
        return redirect(url_for("volunteer_tasks"))

    # OTP Verification check
    if donation["otp"] != submitted_otp:
        # Re-query active tasks so the page stays populated with action buttons
        tasks_query = conn.execute("""
            SELECT d.*, 
                   donor.name as donor_name, donor.lat as donor_lat, donor.lng as donor_lng,
                   ngo.name as ngo_name, ngo.lat as ngo_lat, ngo.lng as ngo_lng
            FROM donations d
            JOIN users donor ON d.donor_id = donor.id
            LEFT JOIN users ngo ON d.ngo_id = ngo.id
            WHERE d.status IN ('accepted', 'assigned', 'picked_up')
            ORDER BY d.id DESC
        """).fetchall()
        tasks = []
        for t in tasks_query:
            tasks.append({
                "id": t["id"],
                "food_type": t["food_type"],
                "quantity_kg": t["quantity_kg"],
                "status": t["status"],
                "safe_until": t["safe_until"],
                "pickup_address": t["donor_name"],
                "ngo_name": t["ngo_name"] or "Local Relief Shelter",
                "lat": t["lat"],
                "lng": t["lng"],
                "ngo_lat": t["ngo_lat"] or 31.3217,
                "ngo_lng": t["ngo_lng"] or 75.5786
            })
        conn.close()
        return render_template(
            "volunteer.html",
            tasks=tasks,
            error="Incorrect 4-digit OTP verification code. Please confirm code with the donor.",
            role=session.get("role")
        )

    now_str = get_current_time_str()
    vol_id = session.get("user_id")

    conn.execute("""
        UPDATE donations
        SET status = 'picked_up', volunteer_id = ?
        WHERE id = ?
    """, (vol_id, donation_id))

    conn.execute("""
        INSERT INTO events (donation_id, status, time)
        VALUES (?, 'picked_up', ?)
    """, (donation_id, now_str))

    conn.commit()
    conn.close()
    return redirect(url_for("volunteer_tasks"))


@app.route("/deliver/<int:donation_id>", methods=["POST"])
def deliver(donation_id):
    """
    Volunteer completes delivery to the NGO shelter:
    - Status changes from 'picked_up' -> 'delivered'
    - Increments meals saved count on the impact dashboard
    """
    conn = db.get_db()
    now_str = get_current_time_str()

    conn.execute("""
        UPDATE donations
        SET status = 'delivered'
        WHERE id = ?
    """, (donation_id,))

    conn.execute("""
        INSERT INTO events (donation_id, status, time)
        VALUES (?, 'delivered', ?)
    """, (donation_id, now_str))

    conn.commit()
    conn.close()
    return redirect(url_for("volunteer_tasks"))


# ==============================================================================
# API & DASHBOARD ROUTES
# ==============================================================================

@app.route("/api/status/<int:donation_id>")
def api_status(donation_id):
    """
    Live Status API polled every 5 seconds by static/app.js.
    Shape:
    {"id":1, "status":"matched", "safe_until":"2026-10-30 23:30", "ngo_name":"...", "volunteer_name":"..."}
    """
    conn = db.get_db()
    expire_old_donations(conn)

    row = conn.execute("""
        SELECT d.id, d.status, d.safe_until, d.otp,
               ngo.name as ngo_name, vol.name as volunteer_name
        FROM donations d
        LEFT JOIN users ngo ON d.ngo_id = ngo.id
        LEFT JOIN users vol ON d.volunteer_id = vol.id
        WHERE d.id = ?
    """, (donation_id,)).fetchone()

    conn.close()
    if not row:
        return jsonify({"error": "Not found"}), 404

    return jsonify({
        "id": row["id"],
        "status": row["status"],
        "safe_until": row["safe_until"],
        "ngo_name": row["ngo_name"] or "Awaiting Acceptance",
        "volunteer_name": row["volunteer_name"] or "Unassigned",
        "otp": row["otp"]
    })


@app.route("/api/stats")
def api_stats():
    """
    Impact Metrics API:
    Shape:
    {"meals_saved": 120, "total_kg": 60, "donations": 5, "recent": [...]}
    """
    conn = db.get_db()
    expire_old_donations(conn)

    # Calculate metrics from completed deliveries
    delivered = conn.execute("""
        SELECT d.id, d.food_type, d.quantity_kg, ngo.name as ngo_name, d.safe_until, d.created_at
        FROM donations d
        LEFT JOIN users ngo ON d.ngo_id = ngo.id
        WHERE d.status = 'delivered'
        ORDER BY d.id DESC
    """).fetchall()

    total_kg = sum(d["quantity_kg"] for d in delivered)
    # Meals saved = total kg / 0.45 kg per meal
    meals_saved = int(round(total_kg / MEAL_KG)) if total_kg > 0 else 0
    total_donations_count = len(delivered)

    # Format recent rescues
    recent = []
    for d in delivered[:10]:
        recent.append({
            "id": d["id"],
            "food_type": d["food_type"],
            "kg": d["quantity_kg"],
            "ngo": d["ngo_name"] or "Partner Shelter",
            "time": d["created_at"] or "Verified"
        })

    conn.close()
    return jsonify({
        "meals_saved": meals_saved,
        "total_kg": total_kg,
        "donations": total_donations_count,
        "recent": recent
    })


@app.route("/dashboard")
def dashboard():
    """Community Impact Dashboard page."""
    # Obtain metrics
    conn = db.get_db()
    expire_old_donations(conn)

    delivered = conn.execute("""
        SELECT d.id, d.food_type, d.quantity_kg, ngo.name as ngo_name, d.created_at
        FROM donations d
        LEFT JOIN users ngo ON d.ngo_id = ngo.id
        WHERE d.status = 'delivered'
        ORDER BY d.id DESC
    """).fetchall()

    total_kg = sum(d["quantity_kg"] for d in delivered)
    meals_saved = int(round(total_kg / MEAL_KG)) if total_kg > 0 else 0

    recent = []
    for d in delivered[:10]:
        recent.append({
            "id": d["id"],
            "food_type": d["food_type"],
            "kg": d["quantity_kg"],
            "ngo": d["ngo_name"] or "Partner Shelter",
            "time": d["created_at"]
        })

    conn.close()

    stats = {
        "meals_saved": meals_saved,
        "total_kg": total_kg,
        "donations": len(delivered),
        "recent": recent
    }

    return render_template("dashboard.html", stats=stats, error=None, role=session.get("role"))


@app.route("/reset-demo")
def reset_demo():
    """
    Reset Demo Endpoint:
    Drops all current data, recreates database tables, and reseeds initial demo accounts.
    """
    db.create_tables()
    db.seed_data()
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    # Ensure database is initialized before server start
    db.create_tables()
    print("Surplus Food Rescue app starting on http://127.0.0.1:5000")
    app.run(debug=True, host="127.0.0.1", port=5000)
