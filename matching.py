# Generated with AI, reviewed and modified by the team
"""
matching.py - Haversine Distance & NGO Ranking Module for Surplus Food Rescue.
Matches surplus food posts with the nearest verified NGOs based on GPS proximity,
capacity availability, operating hours, and travel time vs food expiry.
"""

import math
from datetime import datetime, timedelta
from safety import parse_datetime


def haversine(lat1, lng1, lat2, lng2):
    """
    Calculates the great-circle distance between two GPS points on Earth
    using the Haversine formula in pure Python (no external routing API).
    
    Parameters:
    - lat1, lng1: Latitude and Longitude of Point 1 in decimal degrees
    - lat2, lng2: Latitude and Longitude of Point 2 in decimal degrees
    
    Returns:
    - Distance in kilometers (float, rounded to 2 decimal places)
    """
    R = 6371.0  # Earth's radius in kilometers

    # Convert degrees to radians
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lng2 - lng1)

    # Haversine formula
    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) *
         math.sin(delta_lambda / 2.0) ** 2)

    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(R * c, 2)


def is_ngo_open(open_from, open_to, pickup_from_dt, pickup_to_dt):
    """
    Verifies if an NGO is open during the donor's proposed pickup window.
    Compares HH:MM strings.
    """
    if not open_from or not open_to:
        return True  # If hours not set, assume open

    open_start = open_from.strip()
    open_end = open_to.strip()

    pickup_start = pickup_from_dt.strftime("%H:%M")
    pickup_end = pickup_to_dt.strftime("%H:%M")

    # If the entire pickup window is before opening or after closing
    if pickup_end < open_start or pickup_start > open_end:
        return False
    return True


def rank_ngos(donation, ngos, now=None, exclude_ids=None):
    """
    Filters and ranks approved NGOs for a given food donation.

    Rules from the contract:
    1. Skip if NGO ID is in exclude_ids (e.g. previously declined)
    2. Skip unapproved NGOs (approved != 1)
    3. Skip if capacity_kg < quantity_kg
    4. Skip if closed during the pickup window
    5. Compute haversine distance
    6. Calculate travel_time = distance / 20.0 km/h
    7. Skip if now + travel_time > safe_until
    8. Rank by score = 100 - (distance_km * 10) + capacity_fit_bonus
    9. Return top 3 matches with clear reason strings

    Returns:
    - List of up to 3 dicts:
      [
        {"ngo_id": 1, "ngo_name": "...", "distance_km": 1.2, "reason": "..."},
        ...
      ]
    """
    if exclude_ids is None:
        exclude_ids = []

    # Parse reference timestamps
    now_dt = parse_datetime(now) if now else datetime.now()
    safe_until_dt = parse_datetime(donation["safe_until"])
    pickup_from_dt = parse_datetime(donation["pickup_from"])
    pickup_to_dt = parse_datetime(donation["pickup_to"])

    # Ensure donation is a dict (supports sqlite3.Row)
    donation = dict(donation) if not isinstance(donation, dict) else donation

    quantity = float(donation["quantity_kg"])
    donor_lat = float(donation["lat"])
    donor_lng = float(donation["lng"])

    candidates = []

    for raw_ngo in ngos:
        # Convert sqlite3.Row to standard dict for .get() compatibility
        ngo = dict(raw_ngo) if not isinstance(raw_ngo, dict) else raw_ngo
        ngo_id = ngo["id"]

        # Rule 1: Skip excluded (e.g. declined) NGOs
        if ngo_id in exclude_ids:
            continue

        # Rule 2: Skip unapproved NGOs
        if ngo.get("approved", 1) != 1:
            continue

        # Rule 3: Skip if capacity is insufficient
        ngo_capacity = float(ngo.get("capacity_kg") or 0)
        if ngo_capacity < quantity:
            continue

        # Rule 4: Skip if closed during pickup window
        if not is_ngo_open(ngo.get("open_from"), ngo.get("open_to"), pickup_from_dt, pickup_to_dt):
            continue

        # Rule 5: Haversine distance
        ngo_lat = float(ngo["lat"])
        ngo_lng = float(ngo["lng"])
        distance_km = haversine(donor_lat, donor_lng, ngo_lat, ngo_lng)

        # Rule 6 & 7: Check travel time at 20 km/h city average
        travel_hours = distance_km / 20.0
        estimated_arrival = now_dt + timedelta(hours=travel_hours)
        if estimated_arrival >= safe_until_dt:
            continue  # Food will spoil before delivery

        # Rule 8: Score calculation
        # Base score from proximity; small bonus for having adequate headroom in capacity
        capacity_headroom = min(10.0, (ngo_capacity - quantity) / 10.0)
        score = 100.0 - (distance_km * 10.0) + capacity_headroom

        # Calculate remaining safe time for reason string
        remaining_seconds = max(0, (safe_until_dt - now_dt).total_seconds())
        rem_hours = int(remaining_seconds // 3600)
        rem_mins = int((remaining_seconds % 3600) // 60)

        reason = (
            f"{distance_km} km, capacity OK ({int(ngo_capacity)} kg), "
            f"{rem_hours}h {rem_mins}m safe time left"
        )

        candidates.append({
            "ngo_id": ngo_id,
            "ngo_name": ngo["name"],
            "distance_km": distance_km,
            "score": score,
            "reason": reason
        })

    # Sort descending by score (highest score first)
    candidates.sort(key=lambda x: x["score"], reverse=True)

    # Return top 3 candidates (strip score from output dict as per contract)
    top_3 = []
    for c in candidates[:3]:
        top_3.append({
            "ngo_id": c["ngo_id"],
            "ngo_name": c["ngo_name"],
            "distance_km": c["distance_km"],
            "reason": c["reason"]
        })

    return top_3


if __name__ == "__main__":
    print("--- Running matching.py test cases ---")

    # Sample donation
    mock_donation = {
        "quantity_kg": 30.0,
        "cooked_at": "2026-10-30 17:00",
        "safe_until": "2026-10-30 23:00",
        "pickup_from": "2026-10-30 18:30",
        "pickup_to": "2026-10-30 21:00",
        "lat": 31.3260,
        "lng": 75.5760
    }

    # Sample NGOs in Jalandhar
    mock_ngos = [
        {"id": 1, "name": "Seva Kitchen NGO", "lat": 31.3280, "lng": 75.5780, "capacity_kg": 50, "open_from": "08:00", "open_to": "22:00", "approved": 1},
        {"id": 2, "name": "Hope Foundation Shelter", "lat": 31.3325, "lng": 75.5840, "capacity_kg": 100, "open_from": "09:00", "open_to": "21:00", "approved": 1},
        {"id": 3, "name": "Care & Share Community", "lat": 31.3180, "lng": 75.5690, "capacity_kg": 20, "open_from": "10:00", "open_to": "20:00", "approved": 1},  # capacity too low (20 < 30)
        {"id": 4, "name": "Annapurna Seva Trust", "lat": 31.3410, "lng": 75.5650, "capacity_kg": 120, "open_from": "07:00", "open_to": "23:00", "approved": 1},
        {"id": 5, "name": "Night Shelter", "lat": 31.3050, "lng": 75.5890, "capacity_kg": 80, "open_from": "22:00", "open_to": "06:00", "approved": 1}  # closed during pickup
    ]

    results = rank_ngos(mock_donation, mock_ngos, now="2026-10-30 18:30")
    print("Top matched NGOs:")
    for idx, r in enumerate(results, 1):
        print(f"{idx}. {r['ngo_name']} ({r['distance_km']} km) -> Reason: {r['reason']}")
