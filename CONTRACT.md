# Backend-Frontend Contract (CTBF-SE-06)

**Project**: Surplus Food Rescue (CT BuildFest 2.0)  
**Roles**: `donor`, `ngo`, `volunteer`  
**Tech Stack**: Flask, SQLite3, Jinja2, Tailwind CSS (CDN), Leaflet.js (Volunteer map)

---

## 1. Database Schema (`food_rescue.db`)

### `users`
| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PRIMARY KEY AUTOINCREMENT | |
| `name` | TEXT NOT NULL | Organization or Volunteer name |
| `role` | TEXT NOT NULL | `'donor'`, `'ngo'`, or `'volunteer'` |
| `phone` | TEXT | Contact number |
| `lat` | REAL | Latitude |
| `lng` | REAL | Longitude |
| `password` | TEXT NOT NULL | Plain-text for hackathon demo |
| `capacity_kg` | REAL | NGO only: max capacity in kg |
| `open_from` | TEXT | NGO only: e.g. `"08:00"` |
| `open_to` | TEXT | NGO only: e.g. `"22:00"` |
| `approved` | INTEGER DEFAULT 1 | NGO only: 1 = approved, 0 = pending |

### `donations`
| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PRIMARY KEY AUTOINCREMENT | |
| `donor_id` | INTEGER NOT NULL | FK -> `users.id` |
| `food_type` | TEXT NOT NULL | e.g. `"Cooked Meals (Rice & Dal)"` |
| `quantity_kg` | REAL NOT NULL | Quantity in kg |
| `cooked_at` | TEXT NOT NULL | `"YYYY-MM-DD HH:MM"` |
| `safe_until` | TEXT NOT NULL | `"YYYY-MM-DD HH:MM"` |
| `pickup_from` | TEXT NOT NULL | `"YYYY-MM-DD HH:MM"` |
| `pickup_to` | TEXT NOT NULL | `"YYYY-MM-DD HH:MM"` |
| `lat` | REAL NOT NULL | Pickup latitude |
| `lng` | REAL NOT NULL | Pickup longitude |
| `status` | TEXT NOT NULL | Lifecycle status (see below) |
| `otp` | TEXT | 4-digit code generated upon NGO accept |
| `ngo_id` | INTEGER | FK -> `users.id` (accepted/matched NGO) |
| `volunteer_id` | INTEGER | FK -> `users.id` (delivering volunteer) |
| `created_at` | TEXT NOT NULL | `"YYYY-MM-DD HH:MM"` |

### `events`
| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PRIMARY KEY AUTOINCREMENT | |
| `donation_id` | INTEGER NOT NULL | FK -> `donations.id` |
| `status` | TEXT NOT NULL | New status logged |
| `time` | TEXT NOT NULL | Timestamp of change |

---

## 2. Status Lifecycle Values

```
posted -> matched -> accepted -> assigned -> picked_up -> delivered
```
Additional terminals:
- `declined`
- `expired`
- `cancelled`

---

## 3. Routes & Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` / `POST` | `/login` | Authenticate user into session by role |
| `GET` | `/logout` | Clear session and redirect to `/login` |
| `GET` / `POST` | `/donate` | Donor page; post food donation with safety check |
| `GET` | `/matches/<id>` | JSON top 3 matching NGOs with reason strings |
| `GET` | `/ngo/offers` | NGO inbox of matched food offers |
| `POST` | `/accept/<id>` | NGO accepts offer; generates 4-digit OTP |
| `POST` | `/decline/<id>` | NGO declines; re-matches or marks expired |
| `GET` | `/volunteer/tasks` | Volunteer open & assigned pickup tasks |
| `POST` | `/pickup/<id>` | Volunteer enters 4-digit OTP to confirm handoff |
| `POST` | `/deliver/<id>` | Volunteer confirms delivery to NGO shelter |
| `GET` | `/api/status/<id>` | JSON status polled every 5s |
| `GET` | `/api/stats` | JSON community impact metrics |
| `GET` | `/dashboard` | Public impact dashboard page |
| `GET` | `/reset-demo` | Drops, recreates and reseeds demo database |

---

## 4. JSON Shapes

### `/api/status/<id>`
```json
{
  "id": 1,
  "status": "matched",
  "safe_until": "2026-10-30 23:30",
  "ngo_name": "Robin Hood Army",
  "volunteer_name": "Aman Sharma"
}
```

### `/api/stats`
```json
{
  "meals_saved": 120,
  "total_kg": 60,
  "donations": 5,
  "recent": [
    {
      "id": 1,
      "food_type": "Cooked Meals (Rice & Dal)",
      "kg": 30.0,
      "ngo": "Robin Hood Army",
      "time": "Verified"
    }
  ]
}
```

---

## 5. Constant Citations
- **`MEAL_KG = 0.45`**: 1 standard meal is approximated at 0.45 kg of cooked surplus food (Benchmark: USDA / Global FoodBanking Network).
