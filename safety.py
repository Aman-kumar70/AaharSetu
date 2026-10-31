# Generated with AI, reviewed and modified by the team
"""
safety.py - Food Safety Verification Module for Surplus Food Rescue.
Calculates consumption safety windows, enforces food type restrictions,
and verifies minimum remaining shelf life before distribution.
"""

from datetime import datetime, timedelta

# Editable dictionary: hours food remains safe to consume after cooking
# NOTE: Placeholder values based on standard FSSAI / WHO hot-holding & ambient guidelines.
# The team can calibrate these values with local food safety regulations.
SAFE_HOURS = {
    "Cooked Meals (Rice & Dal)": 6,
    "Roti & Paratha": 8,
    "Curry & Sabzi": 5,
    "Snacks & Bakery": 12,
    "Desserts & Sweets": 10,
    "Cooked Rice": 5,
    "Dal": 6,
    "Bread": 12,
}

# List of prohibited food items that present immediate microbiological hazards
BLOCKED_TYPES = [
    "Raw Meat",
    "Raw Seafood",
    "Raw Fish",
    "Unpasteurized Milk",
    "Expired Dairy",
    "Half-eaten Plates",
    "Leftover Buffet Scrapings"
]


def get_safe_hours(food_type):
    """
    Intelligently determines safe consumption hours based on exact category or keyword matching.
    Supports manual typing of foods like 'Veg Biryani', 'Aloo Paratha', 'Dal Makhani', 'Sandwiches', etc.
    """
    ft = food_type.strip().lower()

    # 1. Exact match check
    for k, v in SAFE_HOURS.items():
        if k.lower() == ft:
            return v

    # 2. Keyword category matching
    if any(w in ft for w in ["bread", "bakery", "biscuit", "toast", "puff", "snack", "sandwich", "burger"]):
        return 12
    if any(w in ft for w in ["dessert", "sweet", "mithai", "halwa", "gulab jamun", "cake", "kheer", "pastry"]):
        return 10
    if any(w in ft for w in ["roti", "paratha", "chapati", "naan", "kulcha", "puri", "phulka"]):
        return 8
    if any(w in ft for w in ["rice", "dal", "khichdi", "biryani", "pulao", "fried rice", "chawal"]):
        return 6
    if any(w in ft for w in ["curry", "sabzi", "gravy", "paneer", "kofta", "mix veg", "chole", "rajma"]):
        return 5

    return 4  # Standard safe baseline for prepared foods


def parse_datetime(dt_val):
    """
    Helper function to parse datetime from various formats:
    - 'YYYY-MM-DD HH:MM'
    - 'YYYY-MM-DDTHH:MM' (standard HTML datetime-local input)
    - 'YYYY-MM-DD HH:MM:SS'
    - datetime object (returns as-is)
    """
    if isinstance(dt_val, datetime):
        return dt_val
    if not isinstance(dt_val, str):
        raise ValueError(f"Invalid datetime value: {dt_val}")

    dt_str = dt_val.strip().replace("T", " ")
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(dt_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"Cannot parse datetime '{dt_val}'. Expected 'YYYY-MM-DD HH:MM'.")


def format_datetime(dt_obj):
    """Formats datetime object into standard 'YYYY-MM-DD HH:MM' string."""
    return dt_obj.strftime("%Y-%m-%d %H:%M")


def check_safety(food_type, cooked_at, now=None):
    """
    Validates food safety for a donation.

    Parameters:
    - food_type (str): Category of food (e.g. 'Cooked Meals (Rice & Dal)')
    - cooked_at (str or datetime): Timestamp when food was prepared
    - now (str or datetime, optional): Current reference time (defaults to datetime.now())

    Returns:
    - (ok: bool, safe_until: str or None, reason: str)
      ok = True if safe to distribute, False otherwise
      safe_until = 'YYYY-MM-DD HH:MM' string if calculated, else None
      reason = Human-readable explanation of approval or rejection
    """
    # 1. Check prohibited types
    for blocked in BLOCKED_TYPES:
        if blocked.lower() in food_type.strip().lower():
            return False, None, f"Prohibited food type: '{food_type}' cannot be accepted due to high health risk."

    # 2. Parse reference timestamps
    try:
        cooked_dt = parse_datetime(cooked_at)
    except Exception as e:
        return False, None, f"Invalid cooked_at timestamp: {e}"

    if now is None:
        now_dt = datetime.now()
    else:
        try:
            now_dt = parse_datetime(now)
        except Exception as e:
            return False, None, f"Invalid now timestamp: {e}"

    # Guard against invalid future cooking timestamps (allow 5 min clock skew)
    if cooked_dt > now_dt + timedelta(minutes=5):
        return False, None, "Cooking time cannot be in the future. Please provide the actual time the food was prepared."

    # 3. Determine safety duration (default to 4 hours if type not specifically listed)
    safe_duration_hours = get_safe_hours(food_type)
    safe_until_dt = cooked_dt + timedelta(hours=safe_duration_hours)
    safe_until_str = format_datetime(safe_until_dt)

    # 4. Check if already expired
    if now_dt >= safe_until_dt:
        return False, safe_until_str, f"Food expired at {safe_until_str}. Safe consumption window has ended."

    # 5. Check minimum 1 hour window rule
    remaining_seconds = (safe_until_dt - now_dt).total_seconds()
    remaining_minutes = int(remaining_seconds // 60)
    if remaining_seconds < 3600:
        return (
            False,
            safe_until_str,
            f"Only {remaining_minutes} minutes remaining before safe expiry ({safe_until_str}). "
            f"A minimum 1-hour window is required for safe transport and distribution."
        )

    # All checks passed!
    hours_left = remaining_minutes // 60
    mins_left = remaining_minutes % 60
    return (
        True,
        safe_until_str,
        f"Verified safe until {safe_until_str} ({hours_left}h {mins_left}m remaining)."
    )


if __name__ == "__main__":
    print("--- Running safety.py test cases ---")

    ref_now = "2026-10-30 18:30"

    # Test Sample 1: Fresh Cooked Rice & Dal (Cooked 1.5h ago -> Safe)
    ok1, until1, reason1 = check_safety("Cooked Meals (Rice & Dal)", "2026-10-30 17:00", ref_now)
    print(f"Sample 1 [Fresh]: ok={ok1}, until={until1}\n   Reason: {reason1}\n")

    # Test Sample 2: Prohibited Food (Raw Seafood -> Blocked)
    ok2, until2, reason2 = check_safety("Raw Seafood Salad", "2026-10-30 17:00", ref_now)
    print(f"Sample 2 [Blocked]: ok={ok2}, until={until2}\n   Reason: {reason2}\n")

    # Test Sample 3: Expiring Soon (<1 hour left -> Rejected)
    # Curry & Sabzi safe for 5 hours. Cooked at 13:00 -> safe until 18:00 (already expired)
    # Cooked at 13:45 -> safe until 18:45 (only 15 mins left at 18:30)
    ok3, until3, reason3 = check_safety("Curry & Sabzi", "2026-10-30 13:45", ref_now)
    print(f"Sample 3 [Urgent <1h]: ok={ok3}, until={until3}\n   Reason: {reason3}")
