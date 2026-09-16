"""
Hand-written reference data for the demo: the airports ZivAirline serves,
the fleet, the agents, and the name pools used to invent customers.

Keeping it here (and not inside the generator) makes the generator readable
and lets anyone change the network without touching any logic.
"""

# (iata, airport name, city, country, region, distance from TLV in km)
AIRPORTS = [
    ("TLV", "Ben Gurion International",      "Tel Aviv",    "Israel",         "Middle East",       0),
    ("LCA", "Larnaca International",         "Larnaca",     "Cyprus",         "Europe",          230),
    ("IST", "Istanbul Airport",              "Istanbul",    "Turkey",         "Europe",         1130),
    ("ATH", "Athens International",          "Athens",      "Greece",         "Europe",         1250),
    ("AUH", "Zayed International",           "Abu Dhabi",   "UAE",            "Middle East",    2050),
    ("DXB", "Dubai International",           "Dubai",       "UAE",            "Middle East",    2100),
    ("BUD", "Budapest Ferenc Liszt",         "Budapest",    "Hungary",        "Europe",         2210),
    ("FCO", "Leonardo da Vinci Fiumicino",   "Rome",        "Italy",          "Europe",         2280),
    ("WAW", "Warsaw Chopin",                 "Warsaw",      "Poland",         "Europe",         2280),
    ("VIE", "Vienna International",          "Vienna",      "Austria",        "Europe",         2360),
    ("MUC", "Munich Airport",                "Munich",      "Germany",        "Europe",         2560),
    ("PRG", "Vaclav Havel Prague",           "Prague",      "Czechia",        "Europe",         2630),
    ("ZRH", "Zurich Airport",                "Zurich",      "Switzerland",    "Europe",         2830),
    ("FRA", "Frankfurt Airport",             "Frankfurt",   "Germany",        "Europe",         2920),
    ("BCN", "Josep Tarradellas Barcelona",   "Barcelona",   "Spain",          "Europe",         3140),
    ("CDG", "Paris Charles de Gaulle",       "Paris",       "France",         "Europe",         3280),
    ("AMS", "Amsterdam Schiphol",            "Amsterdam",   "Netherlands",    "Europe",         3330),
    ("LHR", "London Heathrow",               "London",      "United Kingdom", "Europe",         3580),
    ("BOM", "Chhatrapati Shivaji Maharaj",   "Mumbai",      "India",          "Asia",           4050),
    ("BKK", "Suvarnabhumi Airport",          "Bangkok",     "Thailand",       "Asia",           7400),
    ("JFK", "John F. Kennedy International", "New York",    "United States",  "North America",  9100),
    ("YYZ", "Toronto Pearson International", "Toronto",     "Canada",         "North America",  9200),
    ("LAX", "Los Angeles International",     "Los Angeles", "United States",  "North America", 12100),
]

# (tail number, model, body type, economy seats, business seats, range km, year built)
FLEET = [
    ("4X-ZVA", "Boeing 737-800",   "Narrow-body", 162, 12,  5400, 2014),
    ("4X-ZVB", "Boeing 737-800",   "Narrow-body", 162, 12,  5400, 2015),
    ("4X-ZVC", "Boeing 737-800",   "Narrow-body", 162, 12,  5400, 2016),
    ("4X-ZVD", "Boeing 737-800",   "Narrow-body", 162, 12,  5400, 2017),
    ("4X-ZVE", "Boeing 737 MAX 8", "Narrow-body", 168, 16,  6500, 2021),
    ("4X-ZVF", "Boeing 737 MAX 8", "Narrow-body", 168, 16,  6500, 2022),
    ("4X-ZVG", "Airbus A320neo",   "Narrow-body", 150, 12,  6300, 2019),
    ("4X-ZVH", "Airbus A320neo",   "Narrow-body", 150, 12,  6300, 2020),
    ("4X-ZVI", "Airbus A321neo",   "Narrow-body", 184, 16,  7400, 2022),
    ("4X-ZVJ", "Airbus A321neo",   "Narrow-body", 184, 16,  7400, 2023),
    ("4X-ZVK", "Boeing 787-9",     "Wide-body",   250, 30, 14000, 2018),
    ("4X-ZVL", "Boeing 787-9",     "Wide-body",   250, 30, 14000, 2019),
    ("4X-ZVM", "Boeing 787-9",     "Wide-body",   250, 30, 14000, 2021),
    ("4X-ZVN", "Airbus A350-900",  "Wide-body",   280, 32, 15000, 2023),
]

# (agent id, full name, email, team, hired on)
AGENTS = [
    ("AG-01", "Noa Bar-Lev",    "noa.barlev@zivairline.com",     "Sales",     "2019-03-11"),
    ("AG-02", "Daniel Roth",    "daniel.roth@zivairline.com",    "Sales",     "2020-07-01"),
    ("AG-03", "Maya Shahar",    "maya.shahar@zivairline.com",    "Service",   "2018-01-22"),
    ("AG-04", "Omer Katz",      "omer.katz@zivairline.com",      "Service",   "2021-09-05"),
    ("AG-05", "Lior Ben-Ami",   "lior.benami@zivairline.com",    "Corporate", "2017-05-14"),
    ("AG-06", "Tamar Friedman", "tamar.friedman@zivairline.com", "Corporate", "2022-02-28"),
]

FIRST_NAMES = [
    "Noa", "Yael", "Tamar", "Maya", "Shira", "Adi", "Roni", "Michal", "Dana", "Hila",
    "Itai", "Omer", "Yonatan", "Eitan", "Amit", "Guy", "Nadav", "Tomer", "Lior", "Idan",
    "Emma", "Olivia", "Sophia", "Isabella", "Mia", "Charlotte", "Amelia", "Harper",
    "James", "Oliver", "Lucas", "Ethan", "Daniel", "Henry", "Leo", "Adam",
    "Anna", "Elena", "Sofia", "Laura", "Marta", "Julia", "Nina", "Clara",
    "Marco", "Pierre", "Andreas", "Viktor", "Stefan", "Nikos", "Ahmed", "Omar",
    "Priya", "Rahul", "Wei", "Yuki", "Carlos", "Diego", "Miguel", "Rafael",
]

LAST_NAMES = [
    "Levi", "Cohen", "Mizrahi", "Peretz", "Shapira", "Avraham", "Dayan", "Barkai",
    "Friedman", "Golan", "Harel", "Nissim", "Ohana", "Regev", "Segal", "Tzur",
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Miller", "Davis", "Wilson",
    "Muller", "Schmidt", "Fischer", "Weber", "Becker", "Hoffmann",
    "Rossi", "Ferrari", "Russo", "Greco", "Bianchi",
    "Dubois", "Martin", "Bernard", "Moreau", "Laurent",
    "Garcia", "Martinez", "Lopez", "Sanchez", "Torres",
    "Novak", "Kowalski", "Petrov", "Ivanov", "Popescu",
    "Papadopoulos", "Yilmaz", "Kaya", "Sharma", "Patel", "Chen", "Tanaka", "Kim",
]

# Where the customers live, and the relative weight of each market.
CUSTOMER_MARKETS = [
    ("Israel",         ["Tel Aviv", "Jerusalem", "Haifa", "Beer Sheva", "Netanya", "Ramat Gan"], 45),
    ("United States",  ["New York", "Los Angeles", "Miami", "Chicago"],                          12),
    ("United Kingdom", ["London", "Manchester"],                                                  8),
    ("France",         ["Paris", "Lyon", "Marseille"],                                            7),
    ("Germany",        ["Berlin", "Munich", "Frankfurt"],                                         7),
    ("Italy",          ["Rome", "Milan"],                                                         5),
    ("Spain",          ["Madrid", "Barcelona"],                                                   4),
    ("Canada",         ["Toronto", "Montreal"],                                                   4),
    ("UAE",            ["Dubai", "Abu Dhabi"],                                                    4),
    ("Greece",         ["Athens", "Thessaloniki"],                                                4),
]

# Subject lines per interaction topic - makes the service log look real.
INTERACTION_SUBJECTS = {
    "Booking Inquiry": [
        "Availability for next month", "Question about fare rules",
        "Group travel quote", "Child fare eligibility",
    ],
    "Change Request": [
        "Move to an earlier flight", "Name spelling correction",
        "Seat change request", "Add a second bag",
    ],
    "Complaint": [
        "Long delay at departure", "Meal not as ordered",
        "Rude service at the gate", "Broken seat entertainment",
    ],
    "Baggage Issue": [
        "Bag did not arrive", "Damaged suitcase",
        "Excess baggage charge dispute", "Lost item on board",
    ],
    "Refund Request": [
        "Refund after cancellation", "Duplicate charge on card",
        "Medical cancellation refund", "Taxes refund request",
    ],
    "Loyalty Question": [
        "Missing miles from last flight", "Tier upgrade eligibility",
        "Redeem points for an upgrade", "Points expiry date",
    ],
}
