"""
Central configuration for the ZivAirline CRM demo application.

Every module imports its paths and shared constants from here, so there is
exactly one place to change when something moves.
"""

from pathlib import Path

# --- Identity -------------------------------------------------------------
APP_NAME = "ZivAirline CRM"
AIRLINE_NAME = "ZivAirline"
AIRLINE_CODE = "ZV"          # IATA-style carrier code used in flight numbers
HUB_AIRPORT = "TLV"          # Ben Gurion - every route starts or ends here

# --- Paths ----------------------------------------------------------------
PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "zivairline.db"
SCHEMA_PATH = PACKAGE_DIR / "schema.sql"

# --- Data generation ------------------------------------------------------
RANDOM_SEED = 42             # fixed seed -> the same demo data every time
DAYS_IN_PAST = 45            # historical flights generated before "today"
DAYS_IN_FUTURE = 90          # future flights available for booking
FLIGHTS_PER_DAY = 4          # rotations per day (each = outbound + return)
NUM_CUSTOMERS = 900

# --- Business vocabulary --------------------------------------------------
# Kept as constants so the UI and the generator can never drift apart.
CABINS = ["Economy", "Business"]
LOYALTY_TIERS = ["Basic", "Silver", "Gold", "Platinum"]
BOOKING_CHANNELS = ["Website", "Mobile App", "Travel Agent", "Call Center", "Partner"]
BOOKING_STATUSES = ["Confirmed", "Completed", "Cancelled"]
TICKET_STATUSES = ["Confirmed", "Flown", "Cancelled"]
FLIGHT_STATUSES = ["Scheduled", "Boarding", "Departed", "Landed", "Delayed", "Cancelled"]
PAYMENT_STATUSES = ["Paid", "Pending", "Refunded"]
INTERACTION_CHANNELS = ["Phone", "Email", "Chat", "Airport Desk"]
INTERACTION_TYPES = [
    "Booking Inquiry",
    "Change Request",
    "Complaint",
    "Baggage Issue",
    "Refund Request",
    "Loyalty Question",
]
INTERACTION_STATUSES = ["Open", "In Progress", "Resolved"]
PRIORITIES = ["Low", "Medium", "High"]
CURRENCY = "USD"
