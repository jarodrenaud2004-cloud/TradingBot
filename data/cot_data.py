# ============================================================
#  COT DATA — Commitments of Traders (CFTC)
#  Positionnement des gros acteurs (gratuit, hebdomadaire)
# ============================================================

import requests
import pandas as pd

# Codes CFTC pour chaque marché
COT_CODES = {
    "WTI":  "067651",  # Crude Oil WTI
    "GOLD": "088691",  # Gold
    "CORN": "002602",  # Corn
}

def get_cot_data(marche):
    """
    Récupère les données COT depuis l'API CFTC
    Retourne les positions des commerciaux et spéculateurs
    """
    code = COT_CODES.get(marche)
    if not code:
        return None

    try:
        url = f"https://publicreporting.cftc.gov/api/odata/v1/FinComDataItems?$filter=CFTC_Contract_Market_Code eq '{code}'&$orderby=Report_Date_as_MM_DD_YYYY desc&$top=4"
        resp = requests.get(url, timeout=15)

        if resp.status_code != 200:
            return None

        data = resp.json().get("value", [])
        if not data:
            return None

        dernier = data[0]

        long_non_com  = int(dernier.get("NonComm_Positions_Long_All",  0))
        short_non_com = int(dernier.get("NonComm_Positions_Short_All", 0))
        long_com      = int(dernier.get("Comm_Positions_Long_All",     0))
        short_com     = int(dernier.get("Comm_Positions_Short_All",    0))
        open_interest = int(dernier.get("Open_Interest_All",           0))

        # Ratio longs/shorts des spéculateurs
        total = long_non_com + short_non_com
        ratio_longs = round((long_non_com / total * 100), 1) if total > 0 else 50

        # Signal COT
        if ratio_longs > 70:
            signal = "SURACHETÉ"   # Trop de longs → danger baisse
        elif ratio_longs < 30:
            signal = "SURVENDU"    # Trop de shorts → potentiel squeeze
        else:
            signal = "NEUTRE"

        return {
            "marche":         marche,
            "long_speculateurs":  long_non_com,
            "short_speculateurs": short_non_com,
            "ratio_longs":    ratio_longs,
            "signal":         signal,
            "open_interest":  open_interest,
            "date":           dernier.get("Report_Date_as_MM_DD_YYYY", "?"),
        }

    except Exception as e:
        print(f"Erreur COT {marche}: {e}")
        return None

def analyser_cot(marche):
    """Retourne un score COT et une explication"""
    data = get_cot_data(marche)
    if not data:
        return 0, "Données COT indisponibles"

    signal = data["signal"]
    ratio  = data["ratio_longs"]

    if signal == "SURVENDU":
        return 1, f"COT: Marché survendu ({ratio}% longs) → Squeeze possible"
    elif signal == "SURACHETÉ":
        return -1, f"COT: Marché suracheté ({ratio}% longs) → Retournement possible"
    else:
        return 0, f"COT: Positionnement neutre ({ratio}% longs)"
