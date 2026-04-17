# ============================================================
#  CONFIGURATION DU BOT
# ============================================================

# --- TELEGRAM ---
TELEGRAM_TOKEN = "8716782879:AAFW10waLj_H022LAPuzSCYw7wtDTQhL40M"
TELEGRAM_CHAT_ID = "1271680288"

# --- FRED API (macro : taux, dollar, inflation) ---
FRED_API_KEY = "5e8e0565152711ecedacb05ea3f15d23"

# --- EIA API (pétrole, gaz) ---
EIA_API_KEY = "PS3P22MNbdWxLpwbjfOPymHvj4nKqvBAynRrt7ze"

# --- MARCHÉS SUIVIS ---
MARCHES = {
    # Matières premières
    "WTI":    {"symbole_yf": "CL=F",   "nom": "Pétrole WTI",   "type": "energie"},
    "GOLD":   {"symbole_yf": "GC=F",   "nom": "Or",             "type": "metal"},
    "SILVER": {"symbole_yf": "SI=F",   "nom": "Argent",         "type": "metal"},
    "CORN":   {"symbole_yf": "ZC=F",   "nom": "Maïs",           "type": "agri"},
    "WHEAT":  {"symbole_yf": "ZW=F",   "nom": "Blé",            "type": "agri"},
    "NATGAS": {"symbole_yf": "NG=F",   "nom": "Gaz Naturel",    "type": "energie"},

    # Indices européens
    "CAC40":  {"symbole_yf": "^FCHI",  "nom": "CAC 40",         "type": "indice"},
    "DAX":    {"symbole_yf": "^GDAXI", "nom": "DAX",            "type": "indice"},

    # Actions européennes
    "TTE":    {"symbole_yf": "TTE.PA", "nom": "TotalEnergies",  "type": "action_eu"},
    "MC":     {"symbole_yf": "MC.PA",  "nom": "LVMH",           "type": "action_eu"},
    "AIR":    {"symbole_yf": "AIR.PA", "nom": "Airbus",         "type": "action_eu"},
    "BNP":    {"symbole_yf": "BNP.PA", "nom": "BNP Paribas",    "type": "action_eu"},
    "SAN":    {"symbole_yf": "SAN.PA", "nom": "Sanofi",         "type": "action_eu"},
    "OR":     {"symbole_yf": "OR.PA",  "nom": "L'Oréal",        "type": "action_eu"},
}

# --- OANDA (exécution automatique — compte démo) ---
OANDA_API_KEY     = "TON_TOKEN_OANDA_ICI"       # ← à remplacer après inscription
OANDA_ACCOUNT_ID  = "TON_ACCOUNT_ID_OANDA_ICI"  # ← ex: 101-001-XXXXXXX-001
OANDA_ENVIRONMENT = "practice"                   # "practice" = démo / "live" = réel

# --- GESTION DU RISQUE ---
RISQUE_PAR_TRADE = 1.0
RATIO_MIN = 2.0
SCORE_MIN_SIGNAL = 2

# --- INTERVALLES ---
INTERVALLE_ANALYSE_MIN = 60
HEURE_RAPPORT_MATIN = "08:00"
