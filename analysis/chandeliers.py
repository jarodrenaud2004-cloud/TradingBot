# ============================================================
#  CHANDELIERS JAPONAIS — Détection des patterns
#  Hammer, Doji, Engulfing, Morning/Evening Star, etc.
# ============================================================

import pandas as pd

def _corps(row):
    return abs(row["Close"] - row["Open"])

def _ombre_haute(row):
    return row["High"] - max(row["Open"], row["Close"])

def _ombre_basse(row):
    return min(row["Open"], row["Close"]) - row["Low"]

def _range_total(row):
    return row["High"] - row["Low"]

def _est_haussier(row):
    return row["Close"] > row["Open"]

def _est_baissier(row):
    return row["Close"] < row["Open"]

def detecter_patterns(hist):
    """
    Détecte tous les patterns de chandeliers japonais sur les dernières bougies.
    Retourne une liste de signaux avec direction et force.
    """
    if hist is None or len(hist) < 5:
        return []

    hist = hist.copy().tail(10).reset_index(drop=True)
    patterns = []

    # Récupérer les 3 dernières bougies
    n = len(hist)
    c0 = hist.iloc[-1]   # Bougie actuelle
    c1 = hist.iloc[-2] if n >= 2 else None
    c2 = hist.iloc[-3] if n >= 3 else None

    corps0    = _corps(c0)
    ombre_h0  = _ombre_haute(c0)
    ombre_b0  = _ombre_basse(c0)
    range0    = _range_total(c0)

    # Taille moyenne des corps (5 dernières bougies)
    corps_moyen = hist["Close"].sub(hist["Open"]).abs().tail(5).mean()
    if corps_moyen == 0:
        corps_moyen = 0.001

    # ── DOJI ────────────────────────────────────────────────
    # Corps très petit par rapport au range total
    if range0 > 0 and corps0 / range0 < 0.1:
        patterns.append({
            "nom":       "Doji",
            "emoji":     "➕",
            "direction": "NEUTRE",
            "force":     1,
            "signification": "Indécision du marché — retournement possible"
        })

    # ── MARTEAU (Hammer) ─────────────────────────────────────
    # Longue ombre basse, petit corps en haut, après baisse
    if (ombre_b0 >= 2 * corps0 and
        ombre_h0 <= 0.3 * corps0 and
        corps0 > 0):
        tendance = _tendance_recente(hist)
        if tendance == "BAISSE":
            patterns.append({
                "nom":       "Marteau (Hammer)",
                "emoji":     "🔨",
                "direction": "BUY",
                "force":     2,
                "signification": "Signal de retournement haussier après une baisse"
            })

    # ── ÉTOILE FILANTE (Shooting Star) ──────────────────────
    # Longue ombre haute, petit corps en bas, après hausse
    if (ombre_h0 >= 2 * corps0 and
        ombre_b0 <= 0.3 * corps0 and
        corps0 > 0):
        tendance = _tendance_recente(hist)
        if tendance == "HAUSSE":
            patterns.append({
                "nom":       "Étoile Filante (Shooting Star)",
                "emoji":     "💫",
                "direction": "SELL",
                "force":     2,
                "signification": "Signal de retournement baissier après une hausse"
            })

    # ── MARTEAU INVERSÉ ──────────────────────────────────────
    if (ombre_h0 >= 2 * corps0 and
        ombre_b0 <= 0.3 * corps0 and
        corps0 > 0):
        tendance = _tendance_recente(hist)
        if tendance == "BAISSE":
            patterns.append({
                "nom":       "Marteau Inversé",
                "emoji":     "🔄",
                "direction": "BUY",
                "force":     1,
                "signification": "Possible retournement haussier — confirmation nécessaire"
            })

    if c1 is not None:
        corps1 = _corps(c1)

        # ── AVALEMENT HAUSSIER (Bullish Engulfing) ───────────
        if (_est_baissier(c1) and _est_haussier(c0) and
            c0["Open"] < c1["Close"] and c0["Close"] > c1["Open"] and
            corps0 > corps1):
            patterns.append({
                "nom":       "Avalement Haussier (Bullish Engulfing)",
                "emoji":     "🟢",
                "direction": "BUY",
                "force":     3,
                "signification": "Fort signal d'achat — les acheteurs prennent le contrôle"
            })

        # ── AVALEMENT BAISSIER (Bearish Engulfing) ───────────
        if (_est_haussier(c1) and _est_baissier(c0) and
            c0["Open"] > c1["Close"] and c0["Close"] < c1["Open"] and
            corps0 > corps1):
            patterns.append({
                "nom":       "Avalement Baissier (Bearish Engulfing)",
                "emoji":     "🔴",
                "direction": "SELL",
                "force":     3,
                "signification": "Fort signal de vente — les vendeurs prennent le contrôle"
            })

        # ── HARAMI HAUSSIER ───────────────────────────────────
        if (_est_baissier(c1) and _est_haussier(c0) and
            c0["Open"] > c1["Close"] and c0["Close"] < c1["Open"] and
            corps0 < corps1 * 0.5):
            patterns.append({
                "nom":       "Harami Haussier",
                "emoji":     "🔼",
                "direction": "BUY",
                "force":     1,
                "signification": "Ralentissement de la baisse — possible retournement"
            })

        # ── HARAMI BAISSIER ───────────────────────────────────
        if (_est_haussier(c1) and _est_baissier(c0) and
            c0["Open"] < c1["Close"] and c0["Close"] > c1["Open"] and
            corps0 < corps1 * 0.5):
            patterns.append({
                "nom":       "Harami Baissier",
                "emoji":     "🔽",
                "direction": "SELL",
                "force":     1,
                "signification": "Ralentissement de la hausse — possible retournement"
            })

    if c1 is not None and c2 is not None:
        corps1 = _corps(c1)
        corps2 = _corps(c2)

        # ── ÉTOILE DU MATIN (Morning Star) ───────────────────
        # Bougie baissière + petite bougie + bougie haussière forte
        if (_est_baissier(c2) and corps2 > corps_moyen and
            _corps(c1) < corps_moyen * 0.5 and
            _est_haussier(c0) and corps0 > corps_moyen and
            c0["Close"] > (c2["Open"] + c2["Close"]) / 2):
            patterns.append({
                "nom":       "Étoile du Matin (Morning Star)",
                "emoji":     "🌅",
                "direction": "BUY",
                "force":     3,
                "signification": "Fort signal de retournement haussier en 3 bougies"
            })

        # ── ÉTOILE DU SOIR (Evening Star) ────────────────────
        # Bougie haussière + petite bougie + bougie baissière forte
        if (_est_haussier(c2) and corps2 > corps_moyen and
            _corps(c1) < corps_moyen * 0.5 and
            _est_baissier(c0) and corps0 > corps_moyen and
            c0["Close"] < (c2["Open"] + c2["Close"]) / 2):
            patterns.append({
                "nom":       "Étoile du Soir (Evening Star)",
                "emoji":     "🌆",
                "direction": "SELL",
                "force":     3,
                "signification": "Fort signal de retournement baissier en 3 bougies"
            })

        # ── TROIS SOLDATS BLANCS ──────────────────────────────
        if (all(_est_haussier(hist.iloc[-i]) for i in range(1, 4)) and
            all(_corps(hist.iloc[-i]) > corps_moyen for i in range(1, 4))):
            patterns.append({
                "nom":       "3 Soldats Blancs",
                "emoji":     "⚔️",
                "direction": "BUY",
                "force":     2,
                "signification": "3 grandes bougies vertes consécutives — tendance haussière forte"
            })

        # ── TROIS CORBEAUX NOIRS ──────────────────────────────
        if (all(_est_baissier(hist.iloc[-i]) for i in range(1, 4)) and
            all(_corps(hist.iloc[-i]) > corps_moyen for i in range(1, 4))):
            patterns.append({
                "nom":       "3 Corbeaux Noirs",
                "emoji":     "🦅",
                "direction": "SELL",
                "force":     2,
                "signification": "3 grandes bougies rouges consécutives — tendance baissière forte"
            })

    return patterns


def _tendance_recente(hist, n=5):
    """Détermine la tendance des n dernières bougies."""
    if len(hist) < n + 1:
        return "NEUTRE"
    closes = hist["Close"].tail(n + 1)
    debut  = closes.iloc[0]
    fin    = closes.iloc[-2]  # avant la bougie actuelle
    variation = (fin - debut) / debut * 100
    if variation > 1:
        return "HAUSSE"
    elif variation < -1:
        return "BAISSE"
    return "NEUTRE"


def formater_patterns(patterns):
    """Formate les patterns détectés pour un message Telegram."""
    if not patterns:
        return None

    # Trier par force décroissante
    patterns = sorted(patterns, key=lambda x: x["force"], reverse=True)

    msg = "🕯️ *CHANDELIERS JAPONAIS*\n"
    for p in patterns:
        etoiles = "⭐" * p["force"]
        msg += f"{p['emoji']} *{p['nom']}* {etoiles}\n"
        msg += f"   {p['signification']}\n"

    return msg


def score_chandeliers(patterns):
    """Calcule un score d'achat/vente basé sur les patterns détectés."""
    score = 0
    for p in patterns:
        if p["direction"] == "BUY":
            score += p["force"]
        elif p["direction"] == "SELL":
            score -= p["force"]
    return score
