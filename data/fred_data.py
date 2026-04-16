# ============================================================
#  FRED DATA — Données macro (taux, dollar, inflation)
# ============================================================

import requests

SERIES = {
    "DXY":       "DTWEXBGS",   # Dollar Index
    "TAUX_10Y":  "DGS10",      # Taux 10 ans US
    "INFLATION": "T10YIE",     # Inflation anticipée 10 ans
    "TAUX_REEL": "DFII10",     # Taux réel 10 ans (clé pour l'or)
}

def get_serie(serie_id, api_key, nb=5):
    try:
        url = (
            f"https://api.stlouisfed.org/fred/series/observations"
            f"?series_id={serie_id}&api_key={api_key}"
            f"&sort_order=desc&limit={nb}&file_type=json"
        )
        resp = requests.get(url, timeout=10)
        data = resp.json().get("observations", [])
        valeurs = [float(d["value"]) for d in data if d["value"] != "."]
        return valeurs
    except:
        return []

def analyser_macro(api_key):
    """Analyse le contexte macro global"""
    resultats = {}
    score = 0
    messages = []

    # Dollar
    dxy = get_serie(SERIES["DXY"], api_key)
    if len(dxy) >= 2:
        tendance_dxy = "HAUSSE" if dxy[0] > dxy[1] else "BAISSE"
        resultats["dollar"] = {"valeur": dxy[0], "tendance": tendance_dxy}
        if tendance_dxy == "BAISSE":
            score += 1
            messages.append(f"Dollar en baisse ({dxy[0]:.1f}) → Favorable matières premières")
        else:
            score -= 1
            messages.append(f"Dollar en hausse ({dxy[0]:.1f}) → Défavorable matières premières")

    # Taux réels (clé pour l'or)
    taux_reel = get_serie(SERIES["TAUX_REEL"], api_key)
    if len(taux_reel) >= 2:
        tendance_tr = "HAUSSE" if taux_reel[0] > taux_reel[1] else "BAISSE"
        resultats["taux_reel"] = {"valeur": taux_reel[0], "tendance": tendance_tr}
        if tendance_tr == "BAISSE":
            score += 1
            messages.append(f"Taux réels en baisse ({taux_reel[0]:.2f}%) → Favorable à l'or")
        else:
            messages.append(f"Taux réels en hausse ({taux_reel[0]:.2f}%) → Pression sur l'or")

    detail = " | ".join(messages) if messages else "Données macro indisponibles"
    return score, detail, resultats
