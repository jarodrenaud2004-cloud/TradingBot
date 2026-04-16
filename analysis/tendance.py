# ============================================================
#  ANALYSE DE TENDANCE — 3 Timeframes (Weekly, Daily, H4)
#  Méthode : Higher Highs / Higher Lows (ebook)
# ============================================================

import pandas as pd

def detecter_tendance(data):
    """
    Détecte la tendance sur un dataframe OHLCV
    Retourne: HAUSSIER, BAISSIER, ou NEUTRE
    """
    if data is None or len(data) < 10:
        return "NEUTRE"

    closes = data["Close"].values
    highs  = data["High"].values
    lows   = data["Low"].values

    # Moyennes mobiles simples
    ma20 = closes[-20:].mean() if len(closes) >= 20 else closes.mean()
    ma50 = closes[-50:].mean() if len(closes) >= 50 else closes.mean()

    prix_actuel = closes[-1]

    # Structure Higher Highs / Higher Lows
    recent_high = highs[-5:].max()
    prev_high   = highs[-10:-5].max()
    recent_low  = lows[-5:].min()
    prev_low    = lows[-10:-5].min()

    hh = recent_high > prev_high  # Higher High
    hl = recent_low  > prev_low   # Higher Low
    lh = recent_high < prev_high  # Lower High
    ll = recent_low  < prev_low   # Lower Low

    if hh and hl and prix_actuel > ma20 > ma50:
        return "HAUSSIER"
    elif lh and ll and prix_actuel < ma20 < ma50:
        return "BAISSIER"
    else:
        return "NEUTRE"

def analyser_3_timeframes(donnees_tf):
    """
    Analyse la tendance sur Weekly, Daily et H4
    Retourne un biais global et un score
    """
    if not donnees_tf:
        return "NEUTRE", 0, "Données indisponibles"

    t_weekly = detecter_tendance(donnees_tf.get("weekly"))
    t_daily  = detecter_tendance(donnees_tf.get("daily"))
    t_h4     = detecter_tendance(donnees_tf.get("h4"))

    # Compter les votes
    votes_h = sum(1 for t in [t_weekly, t_daily, t_h4] if t == "HAUSSIER")
    votes_b = sum(1 for t in [t_weekly, t_daily, t_h4] if t == "BAISSIER")

    if votes_h >= 2:
        biais = "HAUSSIER"
        score = 1
        detail = f"Tendance HAUSSIÈRE ({votes_h}/3 TF) — W:{t_weekly} D:{t_daily} H4:{t_h4}"
    elif votes_b >= 2:
        biais = "BAISSIER"
        score = -1
        detail = f"Tendance BAISSIÈRE ({votes_b}/3 TF) — W:{t_weekly} D:{t_daily} H4:{t_h4}"
    else:
        biais = "NEUTRE"
        score = 0
        detail = f"Tendance MIXTE — W:{t_weekly} D:{t_daily} H4:{t_h4}"

    return biais, score, detail
