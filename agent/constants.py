"""
Sim Companies Agent Constants & Configuration
"""

import os

# Paths
COOKIE_DB_PATH = os.path.expanduser("~/.config/Sim Companies/Partitions/simcompanies/Cookies")
CACHE_FILE_PATH = os.path.expanduser("~/.sim-company-cache.json")
PRICES_CACHE_FILE = os.path.expanduser("~/.sim-prices-cache.json")
DEFAULT_COMPANY_ID = 5960839
OLLAMA_API_URL = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_OLLAMA_MODEL = os.environ.get("SIM_COMPANY_MODEL", "qwen2.5:3b")

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# ANSI color codes
C_RESET = "\033[0m"
C_BOLD = "\033[1m"
C_GREEN = "\033[92m"
C_YELLOW = "\033[93m"
C_CYAN = "\033[96m"
C_RED = "\033[91m"
C_BLUE = "\033[94m"
C_MAGENTA = "\033[95m"
C_DIM = "\033[2m"

# Official in-game names for resources (1-155)
OFFICIAL_NAMES = {
    1: "Power",
    2: "Water",
    3: "Apples",
    4: "Oranges",
    5: "Grapes",
    6: "Grain",
    7: "Steak",
    8: "Sausages",
    9: "Eggs",
    10: "Crude oil",
    11: "Petrol",
    12: "Diesel",
    13: "Transport",
    14: "Minerals",
    15: "Bauxite",
    16: "Silicon",
    17: "Chemicals",
    18: "Aluminium",
    19: "Plastic",
    20: "Processors",
    21: "Electronic components",
    22: "Batteries",
    23: "Displays",
    24: "Smartphones",
    25: "Tablets",
    26: "Laptops",
    27: "Monitors",
    28: "Televisions",
    29: "Plant research",
    30: "Energy research",
    31: "Mining research",
    32: "Electronics research",
    33: "Breeding research",
    34: "Chemistry research",
    35: "Software",
    40: "Cotton",
    41: "Fabric",
    42: "Iron ore",
    43: "Steel",
    44: "Sand",
    45: "Glass",
    46: "Leather",
    47: "On-board computer",
    48: "Electric motor",
    49: "Luxury car interior",
    50: "Basic interior",
    51: "Car body",
    52: "Combustion engine",
    53: "Economy e-car",
    54: "Luxury e-car",
    55: "Economy car",
    56: "Luxury car",
    57: "Truck",
    58: "Automotive research",
    59: "Fashion research",
    60: "Underwear",
    61: "Gloves",
    62: "Dress",
    63: "Stiletto heel",
    64: "Handbags",
    65: "Sneakers",
    66: "Seeds",
    67: "Christmas crackers",     # Seasonal: Xmas
    68: "Gold ore",
    69: "Golden bars",
    70: "Luxury watch",
    71: "Necklace",
    72: "Sugarcane",
    73: "Ethanol",
    74: "Methane",
    75: "Carbon fibers",
    76: "Carbon composite",
    77: "Fuselage",
    78: "Wing",
    79: "High grade e-components",
    80: "Flight computer",
    81: "Cockpit",
    82: "Attitude control",
    83: "Rocket fuel",
    84: "Propellant tank",
    85: "Solid rocket booster",
    86: "Rocket engine",
    87: "Heat shield",
    88: "Ion drive",
    89: "Jet engine",
    90: "Sub-orbital 2nd stage",
    91: "Sub-orbital rocket",
    92: "Orbital booster",
    93: "Starship",
    94: "BFR",
    95: "Jumbo jet",
    96: "Luxury jet",
    97: "Single engine plane",
    98: "Quadcopter",
    99: "Satellite",
    100: "Aerospace research",
    101: "Reinforced concrete",
    102: "Bricks",
    103: "Cement",
    104: "Clay",
    105: "Limestone",
    106: "Wood",
    107: "Beams",
    108: "Planks",
    109: "Windows",
    110: "Tools",
    111: "Construction units",
    112: "Bulldozer",
    113: "Materials research",
    114: "Robots",
    115: "Cows",
    116: "Pigs",
    117: "Milk",
    118: "Coffee beans",
    119: "Coffee powder",
    120: "Vegetables",
    121: "Bread",
    122: "Cheese",
    123: "Apple pie",
    124: "Orange juice",
    125: "Apple cider",
    126: "Ginger beer",
    127: "Pizza",
    128: "Pasta",
    129: "Hamburger",
    130: "Lasagna",
    131: "Meatballs",
    132: "Cocktails",
    133: "Flour",
    134: "Butter",
    135: "Sugar",
    136: "Cocoa",
    137: "Dough",
    138: "Gravy",
    139: "Fodder",
    140: "Chocolate",
    141: "Vegetable oil",
    142: "Salad",
    143: "Samosas",
    144: "Christmas ornament",    # Seasonal: Xmas
    145: "Recipes",
    146: "Pumpkin",               # Seasonal: Autumn
    147: "Jack-o'-lantern",       # Seasonal: Halloween
    148: "Witch costume",         # Seasonal: Halloween
    149: "Pumpkin soup",          # Seasonal: Halloween
    150: "Christmas tree",        # Seasonal: Xmas
    151: "Chocolate bunny",       # Seasonal: Easter
    152: "Baklava",               # Seasonal: Ramadan
    153: "Chocolate icecream",    # Seasonal: Summer
    154: "Apple icecream",        # Seasonal: Summer
    155: "Cream egg"              # Seasonal: Easter
}

# Seasonal event IDs
SEASONAL_ITEM_IDS = {67, 144, 146, 147, 148, 149, 150, 151, 152, 153, 154, 155}

# Mapping of retail stores and active permanent goods
RETAIL_STORES = {
    "Grocery Store": {
        "code": "G",
        "desc": "Food & Agricultural Products",
        "items": [3, 4, 5, 7, 8, 9, 119, 121, 122, 123, 124, 125, 126, 127, 140],
        "seasonal": [151, 152, 153, 154, 155]
    },
    "Fashion Store": {
        "code": "H",
        "desc": "Apparel, Footwear & Luxury Accessories",
        "items": [60, 61, 62, 63, 64, 65, 70, 71],
        "seasonal": [67, 144, 146, 147, 148, 150]
    },
    "Electronics Store": {
        "code": "C",
        "desc": "Consumer Electronics & Displays",
        "items": [24, 25, 26, 27, 28],
        "seasonal": []
    },
    "Gas Station": {
        "code": "A",
        "desc": "Automotive Fuels",
        "items": [11, 12],
        "seasonal": []
    },
    "Car Dealership": {
        "code": "2",
        "desc": "Electric & Combustion Vehicles",
        "items": [53, 54, 55, 56, 57],
        "seasonal": []
    },
    "Hardware Store": {
        "code": "d",
        "desc": "Construction Materials & Tools",
        "items": [102, 103, 108, 109, 110],
        "seasonal": []
    },
    "Aerospace Sales Office": {
        "code": "B",
        "desc": "Aviation, Rockets & Satellites",
        "items": [91, 94, 95, 96, 97, 98, 99],
        "seasonal": []
    }
}
