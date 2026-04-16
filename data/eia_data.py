# ============================================================
#  EIA DATA — Stocks de pétrole (gratuit, hebdomadaire)
#  Publié chaque mercredi → moteur de volatilité sur WTI
# ============================================================

import requests

def get_stocks_petrole(api_key):
    """
    Récupère les stocks de pétrole brut US depuis l'API EIA
    Variation attendue vs réelle = moteur de mouvement
    """
    try:
        url = (
            f"https://api.eia.gov/v2/petroleum/stoc/wstk/data/"
            f"?api_key={api_key}"
            f"&frequency=weekly"
            f"&data[0]=value"
            f"&facets[product][]=EPC0"
            f"&facets[duoarea][]=NUS"
            f"&sort[0][column]=period"
            f"&sort[0][direction]=desc"
            f"&length=4"
        )
        resp = requests.get(url, timeout=15)
        data = resp.json().get("response", {}).get("data", [])

        if len(data) < 2:
            return None

        stock_actuel   = data[0]["value"]  # en milliers de barils
        stock_precedent = data[1]["value"]
        variation      = stock_actuel - stock_precedent
        variation_mb   = round(variation / 1000, 2)  # en millions

        # Signal
        if variation_mb < -2:
            signal = "HAUSSIER"
            force  = "FORT" if variation_mb < -4 else "MODÉRÉ"
        elif variation_mb > 2:
            signal = "BAISSIER"
            force  = "FORT" if variation_mb > 4 else "MODÉRÉ"
        else:
            signal = "NEUTRE"
            force  = "FAIBLE"

        return {
            "stock_actuel_mb":    round(stock_actuel / 1000, 2),
            "variation_mb":       variation_mb,
            "signal":             signal,
            "force":              force,
            "date":               data[0]["period"],
        }

    except Exception as e:
        print(f"Erreur EIA: {e}")
        return None

def analyser_petrole(api_key):
    """Retourne un score EIA et une explication"""
    data = get_stocks_petrole(api_key)
    if not data:
        return 0, "Données EIA indisponibles (vérifie ta clé API)"

    signal = data["signal"]
    var    = data["variation_mb"]

    if signal == "HAUSSIER":
        return 1, f"EIA: Stocks -{abs(var)}M barils → Pression haussière pétrole"
    elif signal == "BAISSIER":
        return -1, f"EIA: Stocks +{var}M barils → Pression baissière pétrole"
    else:
        return 0, f"EIA: Variation faible ({var}M barils) → Impact neutre"
