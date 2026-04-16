# ============================================================
#  CONFIGURATION DU BOT — à remplir avec tes vraies infos
# ============================================================

# --- TELEGRAM ---
TELEGRAM_TOKEN = "8716782879:AAFW10waLj_H022LAPuzSCYw7wtDTQhL40M"
TELEGRAM_CHAT_ID = "1271680288"

# --- FRED API (macro : taux, dollar, inflation) ---
FRED_API_KEY = "TON_CLE_FRED_ICI"     # Gratuit sur fred.stlouisfed.org/docs/api/

# --- EIA API (pétrole, gaz) ---
EIA_API_KEY = "TON_CLE_EIA_ICI"       # Gratuit sur eia.gov/opendata/

# --- MARCHÉS SUIVIS ---
MARCHES = {
    "WTI":  {"symbole_yf": "CL=F",  "nom": "Pétrole WTI",  "type": "energie"},
    "GOLD": {"symbole_yf": "GC=F",  "nom": "Or",            "type": "metal"},
    "CORN": {"symbole_yf": "ZC=F",  "nom": "Maïs",          "type": "agri"},
    "CAC40":{"symbole_yf": "^FCHI", "nom": "CAC 40",         "type": "indice"},
    "DAX":  {"symbole_yf": "^GDAXI","nom": "DAX",            "type": "indice"},
}

# --- GESTION DU RISQUE ---
RISQUE_PAR_TRADE = 1.0    # % du capital risqué par trade
RATIO_MIN = 2.0           # Ratio Gain/Perte minimum (1:2)
SCORE_MIN_SIGNAL = 4      # Score minimum sur 6 pour envoyer un signal

# --- INTERVALLES DE VÉRIFICATION ---
INTERVALLE_ANALYSE_MIN = 60   # Analyse toutes les 60 minutes
