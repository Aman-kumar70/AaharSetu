# Generated with AI, reviewed and modified by the team
"""
db.py - Database helper functions for Surplus Food Rescue.
Handles SQLite connection, table schema creation, and seeding demo data.
"""

import sqlite3
from datetime import datetime, timedelta

# Constant database filename
DB_NAME = "food_rescue.db"


def get_db(db_name=DB_NAME):
    """
    Creates and returns a connection to the SQLite database.
    row_factory = sqlite3.Row allows column access by name like row['name']
    in addition to integer indices row[0].
    Configured with a 30-second timeout, busy_timeout, and WAL mode to prevent
    'database is locked' errors under concurrent polling and writes.
    """
    conn = sqlite3.connect(db_name, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 30000;")
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
    except Exception:
        pass
    return conn


def create_tables(conn=None):
    """
    Creates the tables required for Surplus Food Rescue if they do not exist:
    - users: stores donors, NGOs, and volunteers
    - donations: stores food donation posts and lifecycle status
    - events: logs every status transition with a timestamp
    """
    close_when_done = False
    if conn is None:
        conn = get_db()
        close_when_done = True

    cursor = conn.cursor()

    # 1. Users Table
    # role can be 'donor', 'ngo', or 'volunteer'
    # capacity_kg, open_from, open_to, and approved are specific to NGOs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        role TEXT NOT NULL,
        phone TEXT,
        lat REAL,
        lng REAL,
        password TEXT NOT NULL,
        capacity_kg REAL,
        open_from TEXT,
        open_to TEXT,
        approved INTEGER DEFAULT 1
    );
    """)

    # 2. Donations Table
    # status lifecycle: posted -> matched -> accepted -> assigned -> picked_up -> delivered
    # additional statuses: declined, expired, cancelled
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS donations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        donor_id INTEGER NOT NULL,
        food_type TEXT NOT NULL,
        quantity_kg REAL NOT NULL,
        cooked_at TEXT NOT NULL,
        safe_until TEXT NOT NULL,
        pickup_from TEXT NOT NULL,
        pickup_to TEXT NOT NULL,
        lat REAL NOT NULL,
        lng REAL NOT NULL,
        status TEXT NOT NULL DEFAULT 'posted',
        otp TEXT,
        ngo_id INTEGER,
        volunteer_id INTEGER,
        created_at TEXT NOT NULL,
        FOREIGN KEY (donor_id) REFERENCES users (id),
        FOREIGN KEY (ngo_id) REFERENCES users (id),
        FOREIGN KEY (volunteer_id) REFERENCES users (id)
    );
    """)

    # 3. Events Table
    # Logs every lifecycle state change for audit trails and timeline tracking
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        donation_id INTEGER NOT NULL,
        status TEXT NOT NULL,
        time TEXT NOT NULL,
        FOREIGN KEY (donation_id) REFERENCES donations (id)
    );
    """)

    conn.commit()

    if close_when_done:
        conn.close()


def seed_data(conn=None):
    """
    Seeds initial demo data into the users table:
    - 5 NGOs with realistic capacities, operating hours, and coordinates
    - 3 Donors (Hostel Mess, Campus Canteen, City Restaurant)
    - 3 Volunteers
    
    NOTE ON PASSWORDS:
    For this hackathon demo, passwords are plain text strings like 'password123'.
    In a real-world production application, passwords MUST be salted and hashed
    using libraries such as bcrypt or werkzeug.security.
    """
    close_when_done = False
    if conn is None:
        conn = get_db()
        close_when_done = True

    cursor = conn.cursor()

    # Clear existing users to avoid duplicate seeding during demo restarts
    cursor.execute("DELETE FROM events;")
    cursor.execute("DELETE FROM donations;")
    cursor.execute("DELETE FROM users;")
    try:
        cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('users', 'donations', 'events');")
    except Exception:
        pass

    # Demo users list
    # Coordinates are sample locations in Jalandhar, Punjab (approx lat ~31.3, lng ~75.5)
    # The team can update exact lat/lng via Google Maps coordinates.
    demo_users = [
        # --- 5 NGOs ---
        # (name, role, phone, lat, lng, password, capacity_kg, open_from, open_to, approved)
        ("Robin Hood Army", "ngo", "9814055555", 31.3217, 75.5786, "demo123", 100.0, "08:00", "22:00", 1),
        ("Seva Kitchen NGO", "ngo", "9814011111", 31.3260, 75.5760, "ngo123", 50.0, "08:00", "22:00", 1),
        ("Hope Foundation Shelter", "ngo", "9814022222", 31.3325, 75.5840, "ngo123", 100.0, "09:00", "21:00", 1),
        ("Care & Share Community Home", "ngo", "9814033333", 31.3180, 75.5690, "ngo123", 40.0, "10:00", "20:00", 1),
        ("Annapurna Seva Trust", "ngo", "9814044444", 31.3410, 75.5650, "ngo123", 120.0, "07:00", "23:00", 1),
        ("Robin Hood Army Jalandhar", "ngo", "9814055556", 31.3050, 75.5890, "ngo123", 75.0, "08:30", "22:30", 1),

        # --- Donors ---
        ("Green Valley Hostel", "donor", "9872011110", 31.3125, 75.5804, "demo123", None, None, None, 1),
        ("NITJ Boys Hostel 7 Mess", "donor", "9872011111", 31.3959, 75.5358, "donor123", None, None, None, 1),
        ("Central Campus Canteen", "donor", "9872022222", 31.3965, 75.5370, "donor123", None, None, None, 1),
        ("Haveli Heritage Restaurant", "donor", "9872033333", 31.2820, 75.6480, "donor123", None, None, None, 1),

        # --- Volunteers ---
        ("Aman Sharma", "volunteer", "9781011110", 31.3125, 75.5804, "demo123", None, None, None, 1),
        ("Aarav Sharma", "volunteer", "9781011111", 31.3300, 75.5700, "vol123", None, None, None, 1),
        ("Priya Singh", "volunteer", "9781022222", 31.3850, 75.5400, "vol123", None, None, None, 1),
        ("Rohan Verma", "volunteer", "9781033333", 31.3100, 75.6000, "vol123", None, None, None, 1)
    ]

    cursor.executemany("""
    INSERT INTO users (name, role, phone, lat, lng, password, capacity_kg, open_from, open_to, approved)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, demo_users)

    # Fetch IDs for the seeded demo users
    user_map = {}
    for row in cursor.execute("SELECT id, name FROM users").fetchall():
        user_map[row["name"]] = row["id"]

    # Initial sample donations for hackathon demo presentation
    # Statuses: assigned (ready for volunteer OTP pickup), matched (waiting for NGO accept), delivered (rescued meals)
    now = datetime.now()
    t_minus_1h = (now - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M")
    t_plus_5h = (now + timedelta(hours=5)).strftime("%Y-%m-%d %H:%M")
    t_pickup_start = now.strftime("%Y-%m-%d %H:%M")
    t_pickup_end = (now + timedelta(hours=3)).strftime("%Y-%m-%d %H:%M")

    demo_donations = [
        # (donor_name, food_type, quantity_kg, cooked_at, safe_until, pickup_from, pickup_to, lat, lng, status, otp, ngo_name, vol_name, created_at)
        (
            user_map.get("Green Valley Hostel"),
            "Cooked Meals (Rice & Dal)",
            30.0,
            t_minus_1h,
            t_plus_5h,
            t_pickup_start,
            t_pickup_end,
            31.3125,
            75.5804,
            "assigned",
            "4821",
            user_map.get("Robin Hood Army"),
            user_map.get("Aman Sharma"),
            t_minus_1h
        ),
        (
            user_map.get("Central Campus Canteen"),
            "Roti & Mixed Sabzi",
            15.0,
            t_minus_1h,
            t_plus_5h,
            t_pickup_start,
            t_pickup_end,
            31.3965,
            75.5370,
            "matched",
            None,
            user_map.get("Robin Hood Army"),
            None,
            t_minus_1h
        ),
        (
            user_map.get("Haveli Heritage Restaurant"),
            "Lunch Snacks & Sandwiches",
            25.0,
            t_minus_1h,
            t_plus_5h,
            t_pickup_start,
            t_pickup_end,
            31.2820,
            75.6480,
            "delivered",
            "7192",
            user_map.get("Hope Foundation Shelter"),
            user_map.get("Aman Sharma"),
            t_minus_1h
        )
    ]

    for d in demo_donations:
        cursor.execute("""
        INSERT INTO donations (donor_id, food_type, quantity_kg, cooked_at, safe_until, pickup_from, pickup_to, lat, lng, status, otp, ngo_id, volunteer_id, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, d)
        d_id = cursor.lastrowid

        # Insert audit log into events
        cursor.execute("""
        INSERT INTO events (donation_id, status, time)
        VALUES (?, ?, ?);
        """, (d_id, d[9], d[13]))

    conn.commit()

    if close_when_done:
        conn.close()


if __name__ == "__main__":
    print("Creating tables...")
    create_tables()
    print("Seeding initial demo data...")
    seed_data()
    print("Database setup complete! 'food_rescue.db' is ready.")
