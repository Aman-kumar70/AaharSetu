# Surplus Food Rescue (CTBF-SE-06)
> Built for **CT BuildFest 2.0** (30-Hour Hackathon)

Cooked surplus food from college hostels, campus canteens, banquets, and restaurants is often discarded while nearby shelters and NGOs struggle with food insecurity.  
**Surplus Food Rescue** connects food donors with verified local NGOs through automated proximity matching, real-time food safety timer validation, and verified volunteer pickups with 4-digit OTP handoffs.

---

## 🌟 Key Features
- **Food Safety Timer Engine (`safety.py`)**: Computes safe consumption windows per food category and rejects items with `< 1 hour` remaining or high-risk foods.
- **Smart NGO Haversine Matching (`matching.py`)**: Ranks approved NGOs by GPS proximity (Haversine formula), capacity headroom, and operating hours.
- **Verified Volunteer Pickup (`app.py`)**: 4-digit numeric OTP generated for the donor ensures fraud-free, verified physical handoffs.
- **Live Status Polling (`static/app.js`)**: Plain JavaScript polling updates state badges in real-time every 5 seconds without heavy frontend frameworks.
- **Community Impact Dashboard (`/dashboard`)**: Live metrics calculate total meals saved and food waste diverted from landfills.

---

## 🛠️ Tech Stack (Zero Build Step)
- **Backend**: Python 3, Flask 3.1.3, SQLite3 (`sqlite3.Row` dictionary mapping)
- **Frontend**: Plain HTML5 + Jinja2 Templates (located in `frontend/`)
- **Styling**: Tailwind CSS via CDN (`<script src="https://cdn.tailwindcss.com"></script>`)
- **Interactive Map**: Leaflet.js 1.9.4 + OpenStreetMap (Volunteer delivery route)
- **Distance Formula**: Haversine formula in pure Python (no paid routing API)

---

## 🚀 How to Run the App

### 1. Activate the Virtual Environment
```bash
# On Windows PowerShell:
.\venv\Scripts\Activate.ps1
```

### 2. Initialize the Database
```bash
python db.py
```
*(Creates `food_rescue.db` and seeds demo accounts in Jalandhar).*

### 3. Start the Flask Server
```bash
python app.py
```
Open **[http://127.0.0.1:5000](http://127.0.0.1:5000)** in your browser.

---

## 🔑 One-Click Demo Credentials

| Role | Name / Organization | Password | Default Landing Page |
|---|---|---|---|
| **Donor** | `Green Valley Hostel` | `demo123` | `/donate` |
| **NGO** | `Robin Hood Army` | `demo123` | `/ngo/offers` |
| **Volunteer** | `Aman Sharma` | `demo123` | `/volunteer/tasks` |

*Or click the quick-fill preset buttons directly on the `/login` screen!*

---

## 🔄 Lifecycle Workflow
```
[Donor Posts] -> [Safety Verified] -> [Matched to NGO] -> [NGO Accepts & Generates OTP]
      -> [Volunteer En Route] -> [4-Digit OTP Verified at Pickup]
      -> [Delivered to Shelter] -> [Dashboard Meals Saved Incremented]
```

To restart the demo anytime with fresh seed data, visit:  
**`http://127.0.0.1:5000/reset-demo`**

---

## 📚 AI and Open-Source Attribution

### Open-Source Libraries & CDNs
1. **Flask 3.1.3 & Werkzeug / Jinja2**: Lightweight Python web framework and templating engine.
2. **Tailwind CSS (CDN)**: Utility-first CSS framework loaded via CDN script tag without npm or build pipeline.
3. **Leaflet 1.9.4 & OpenStreetMap**: Open-source mobile-friendly interactive map for volunteer delivery route visualization.
4. **Python SQLite3 & Math**: Built-in standard library used for relational database management and Haversine distance computations.

### Benchmark Citations
- **`MEAL_KG = 0.45`**: 1 standard meal is defined as 0.45 kilograms (~1 lb) of prepared food, based on benchmarks from the **USDA** and the **Global FoodBanking Network**.

### AI Attribution
- AI assistance was utilized to accelerate MVP development under hackathon time constraints. All generated logic, schema rules, and safety timers have been reviewed and validated by the team.
