# ============================================================
#  DÉTECTION DE FIGURES CHARTISTES (ebook)
#  Double Top/Bottom, Support/Résistance, Compression
# ============================================================

import pandas as pd
import numpy as np

def detecter_supports_resistances(data, nb_niveaux=3):
    """Détecte les niveaux de support et résistance clés"""
    if data is None or len(data) < 20:
        return [], []

    highs  = data["High"].values
    lows   = data["Low"].values

    # Trouver les pivots hauts (résistances)
    resistances = []
    for i in range(2, len(highs) - 2):
        if highs[i] > highs[i-1] and highs[i] > highs[i-2] and \
           highs[i] > highs[i+1] and highs[i] > highs[i+2]:
            resistances.append(round(highs[i], 4))

    # Trouver les pivots bas (supports)
    supports = []
    for i in range(2, len(lows) - 2):
        if lows[i] < lows[i-1] and lows[i] < lows[i-2] and \
           lows[i] < lows[i+1] and lows[i] < lows[i+2]:
            supports.append(round(lows[i], 4))

    # Garder les plus récents
    return sorted(set(supports))[-nb_niveaux:], sorted(set(resistances))[-nb_niveaux:]

def detecter_double_bottom(data):
    """Détecte un Double Bottom (signal haussier)"""
    if data is None or len(data) < 20:
        return False, 0

    lows   = data["Low"].values[-20:]
    closes = data["Close"].values[-20:]

    # Trouver 2 creux similaires
    min1_idx = np.argmin(lows[:10])
    min2_idx = np.argmin(lows[10:]) + 10

    min1 = lows[min1_idx]
    min2 = lows[min2_idx]

    # Les 2 creux doivent être proches (moins de 1% d'écart)
    if abs(min1 - min2) / min1 < 0.01:
        prix_actuel = closes[-1]
        ligne_cou   = max(closes[min1_idx:min2_idx])
        if prix_actuel > ligne_cou * 0.995:
            return True, ligne_cou

    return False, 0

def detecter_double_top(data):
    """Détecte un Double Top (signal baissier)"""
    if data is None or len(data) < 20:
        return False, 0

    highs  = data["High"].values[-20:]
    closes = data["Close"].values[-20:]

    max1_idx = np.argmax(highs[:10])
    max2_idx = np.argmax(highs[10:]) + 10

    max1 = highs[max1_idx]
    max2 = highs[max2_idx]

    if abs(max1 - max2) / max1 < 0.01:
        prix_actuel = closes[-1]
        ligne_cou   = min(closes[max1_idx:max2_idx])
        if prix_actuel < ligne_cou * 1.005:
            return True, ligne_cou

    return False, 0

def detecter_compression(data):
    """Détecte une phase de compression (range serré = explosion prochaine)"""
    if data is None or len(data) < 10:
        return False, 0

    closes  = data["Close"].values[-10:]
    volatilite = (closes.max() - closes.min()) / closes.mean() * 100

    # Compression si volatilité < 2% sur les 10 dernières bougies
    if volatilite < 2.0:
        return True, round(volatilite, 2)

    return False, round(volatilite, 2)

def analyser_figures(donnees_tf):
    """Analyse complète des figures sur le timeframe daily"""
    if not donnees_tf:
        return 0, "Données indisponibles"

    data = donnees_tf.get("daily")
    if data is None or data.empty:
        return 0, "Données daily indisponibles"

    messages = []
    score    = 0

    # Double Bottom
    db, niveau = detecter_double_bottom(data)
    if db:
        score += 1
        messages.append(f"Double Bottom détecté → Signal HAUSSIER (ligne de cou: {niveau:.4f})")

    # Double Top
    dt, niveau = detecter_double_top(data)
    if dt:
        score -= 1
        messages.append(f"Double Top détecté → Signal BAISSIER (ligne de cou: {niveau:.4f})")

    # Compression
    comp, vol = detecter_compression(data)
    if comp:
        messages.append(f"Compression détectée (volatilité: {vol}%) → Explosion imminente")

    # Supports / Résistances
    supports, resistances = detecter_supports_resistances(data)
    prix_actuel = data["Close"].values[-1]

    if supports:
        support_proche = min(supports, key=lambda x: abs(x - prix_actuel))
        if abs(support_proche - prix_actuel) / prix_actuel < 0.005:
            score += 1
            messages.append(f"Prix sur support clé: {support_proche:.4f}")

    if resistances:
        resistance_proche = min(resistances, key=lambda x: abs(x - prix_actuel))
        if abs(resistance_proche - prix_actuel) / prix_actuel < 0.005:
            score -= 1
            messages.append(f"Prix sur résistance clé: {resistance_proche:.4f}")

    detail = " | ".join(messages) if messages else "Aucune figure détectée"
    return score, detail
