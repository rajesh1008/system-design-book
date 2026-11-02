"""Word lists for the synthetic corpus. Every company name is invented.

Airport codes are real IATA codes, used only as places. Carrier and
hotel names are built from the lists below and match no real company
on purpose; carrier codes start with X so they read as fictional.
"""

AIRPORTS = (
    "ORD", "MDW", "BOS", "JFK", "LGA", "EWR", "ATL", "DFW", "DEN", "LAX",
    "SFO", "SEA", "MSP", "DTW", "PHL", "IAD", "DCA", "CLT", "MIA", "MCO",
    "TPA", "PHX", "LAS", "SAN", "PDX", "SLC", "AUS", "IAH", "STL", "MCI",
    "CLE", "PIT", "CVG", "IND", "MKE", "BNA", "RDU", "YYZ", "YUL", "MEX",
    "CUN", "LHR", "CDG", "FRA", "AMS", "DUB", "MAD", "FCO", "NRT", "HND",
)

CARRIER_FIRST = (
    "Lakeway", "Prairie", "Harbor", "Summit", "Northline", "Bluewing",
    "Cardinal", "Meridian", "Tidewater", "Granite", "Silverleaf",
    "Westerly", "Copperline", "Evergreen", "Juniper", "Riverbend",
    "Skyhollow", "Falconridge", "Seabright", "Highmark",
)
CARRIER_SECOND = ("Air", "Airways", "Airlines", "Aviation", "Jet", "Wings",
                  "Express")

HOTEL_FIRST = (
    "Maple", "Harborview", "Linden", "Stonegate", "Willow", "Crescent",
    "Bayfront", "Oakhurst", "Larkspur", "Ashford", "Brightwater",
    "Cedar", "Foxglove", "Hollis", "Marigold", "Northgate", "Parkside",
    "Quarry", "Rosemont", "Sterling", "Thornbury", "Vista", "Wren",
)
HOTEL_SECOND = ("Inn", "Hotel", "Suites", "Lodge", "House", "Residences",
                "Grand Hotel", "Court")

FIRST = (
    "Alex", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Jamie",
    "Avery", "Quinn", "Parker", "Drew", "Reese", "Rowan", "Emerson",
    "Hayden", "Sage", "Dana", "Kendall", "Logan", "Peyton", "Skyler",
    "Elliot", "Finley", "Harper", "Indigo", "Kai", "Lane", "Marlowe",
)
LAST = (
    "Alvarez", "Brooks", "Chen", "Dalton", "Ellis", "Foster", "Garcia",
    "Hughes", "Ito", "Jensen", "Kowalski", "Lindqvist", "Mendoza",
    "Novak", "Okafor", "Patel", "Quintero", "Rossi", "Sato", "Tran",
    "Usman", "Varga", "Walsh", "Xu", "Yilmaz", "Zimmerman",
)

MEMORY_FACTS = (
    "prefers an aisle seat", "prefers a window seat",
    "travels with a service animal", "asks for a quiet room",
    "wants refunds to the original card, not credit",
    "prefers morning departures", "needs a ground-floor room",
    "flies economy plus when the fare difference is under $80",
    "asked not to be called before 9:00 a.m.",
    "loyalty number on file with the carrier",
)
