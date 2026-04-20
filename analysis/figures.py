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

def detecter_tete_epaules(data):
    """
    Détecte un pattern Tête-Épaules (baissier) ou Tête-Épaules Inversé (haussier).
    Retourne: (type, force) où type = 'TE_BAISSIER', 'TE_HAUSSIER' ou None
    """
    if data is None or len(data) < 30:
        return None, 0

    highs  = data["High"].values[-30:]
    lows   = data["Low"].values[-30:]
    closes = data["Close"].values[-30:]

    # Trouver les 3 sommets pour Tête-Épaules baissier
    pivots_hauts = []
    for i in range(2, len(highs) - 2):
        if highs[i] > highs[i-1] and highs[i] > highs[i-2] and \
           highs[i] > highs[i+1] and highs[i] > highs[i+2]:
            pivots_hauts.append((i, highs[i]))

    if len(pivots_hauts) >= 3:
        # Prendre les 3 derniers pivots hauts
        ph = pivots_hauts[-3:]
        e_gauche = ph[0][1]
        tete     = ph[1][1]
        e_droite = ph[2][1]
        # Tête plus haute que les deux épaules (±3%)
        if (tete > e_gauche * 1.01 and tete > e_droite * 1.01 and
            abs(e_gauche - e_droite) / e_gauche < 0.03):
            return "TE_BAISSIER", 3

    # Trouver les 3 creux pour Tête-Épaules Inversé haussier
    pivots_bas = []
    for i in range(2, len(lows) - 2):
        if lows[i] < lows[i-1] and lows[i] < lows[i-2] and \
           lows[i] < lows[i+1] and lows[i] < lows[i+2]:
            pivots_bas.append((i, lows[i]))

    if len(pivots_bas) >= 3:
        pb = pivots_bas[-3:]
        e_gauche = pb[0][1]
        tete     = pb[1][1]
        e_droite = pb[2][1]
        if (tete < e_gauche * 0.99 and tete < e_droite * 0.99 and
            abs(e_gauche - e_droite) / e_gauche < 0.03):
            return "TE_HAUSSIER", 3

    return None, 0


def detecter_triangle(data):
    """
    Détecte les triangles chartistes :
    - Ascendant (haussier) : supports montants + résistance horizontale
    - Descendant (baissier) : support horizontal + résistances descendantes
    - Symétrique (neutre) : les deux convergent
    Retourne: (type, force) où type = 'ASCENDANT', 'DESCENDANT', 'SYMETRIQUE' ou None
    """
    if data is None or len(data) < 20:
        return None, 0

    closes = data["Close"].values[-20:]
    highs  = data["High"].values[-20:]
    lows   = data["Low"].values[-20:]

    # Régression linéaire simplifiée sur highs et lows
    n = len(closes)
    x = list(range(n))

    def pente(valeurs):
        mx = sum(x) / n
        my = sum(valeurs) / n
        num = sum((x[i] - mx) * (valeurs[i] - my) for i in range(n))
        den = sum((x[i] - mx) ** 2 for i in range(n))
        return num / den if den != 0 else 0

    pente_hauts = pente(list(highs))
    pente_bas   = pente(list(lows))

    seuil = closes.mean() * 0.0005  # seuil de significativité

    hauts_plats = abs(pente_hauts) < seuil
    hauts_mont  = pente_hauts > seuil
    hauts_desc  = pente_hauts < -seuil
    bas_plats   = abs(pente_bas) < seuil
    bas_mont    = pente_bas > seuil
    bas_desc    = pente_bas < -seuil

    if bas_mont and hauts_plats:
        return "ASCENDANT", 2     # Triangle ascendant → haussier
    elif hauts_desc and bas_plats:
        return "DESCENDANT", 2    # Triangle descendant → baissier
    elif hauts_desc and bas_mont:
        return "SYMETRIQUE", 1    # Triangle symétrique → explosion possible
    return None, 0


def detecter_biseau(data):
    """
    Détecte les biseaux (wedges) :
    - Biseau montant (bearish wedge) → signal baissier
    - Biseau descendant (bullish wedge) → signal haussier
    """
    if data is None or len(data) < 15:
        return None, 0

    highs  = data["High"].values[-15:]
    lows   = data["Low"].values[-15:]
    n      = len(highs)
    x      = list(range(n))

    def pente(valeurs):
        mx, my = sum(x)/n, sum(valeurs)/n
        num = sum((x[i]-mx)*(valeurs[i]-my) for i in range(n))
        den = sum((x[i]-mx)**2 for i in range(n))
        return num/den if den != 0 else 0

    ph = pente(list(highs))
    pb = pente(list(lows))

    # Les deux montent mais se resserrent → biseau montant (baissier)
    if ph > 0 and pb > 0 and pb > ph:
        return "BISEAU_MONTANT", 2
    # Les deux descendent mais se resserrent → biseau descendant (haussier)
    if ph < 0 and pb < 0 and ph < pb:
        return "BISEAU_DESCENDANT", 2
    return None, 0


def detecter_drapeau(data):
    """
    Détecte les drapeaux (flags) :
    - Drapeau haussier : forte hausse puis consolidation
    - Drapeau baissier : forte baisse puis consolidation
    """
    if data is None or len(data) < 15:
        return None, 0

    closes = data["Close"].values

    # Mouvement initial fort (5 premières bougies sur 15)
    debut    = closes[-15]
    milieu   = closes[-10]
    fin      = closes[-1]
    move_ini = (milieu - debut) / debut * 100
    move_con = (fin - milieu) / milieu * 100

    # Drapeau haussier : hausse forte (+3%) puis consolidation faible (<1%)
    if move_ini > 3 and abs(move_con) < 1:
        return "DRAPEAU_HAUSSIER", 2
    # Drapeau baissier : baisse forte (-3%) puis consolidation faible (<1%)
    if move_ini < -3 and abs(move_con) < 1:
        return "DRAPEAU_BAISSIER", 2
    return None, 0


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

    # Tête-Épaules
    te_type, te_force = detecter_tete_epaules(data)
    if te_type == "TE_BAISSIER":
        score -= te_force
        messages.append(f"🎯 Tête-Épaules détecté → Signal BAISSIER fort")
    elif te_type == "TE_HAUSSIER":
        score += te_force
        messages.append(f"🎯 Tête-Épaules Inversé → Signal HAUSSIER fort")

    # Triangles
    tri_type, tri_force = detecter_triangle(data)
    if tri_type == "ASCENDANT":
        score += tri_force
        messages.append(f"📐 Triangle Ascendant → Breakout haussier probable")
    elif tri_type == "DESCENDANT":
        score -= tri_force
        messages.append(f"📐 Triangle Descendant → Breakout baissier probable")
    elif tri_type == "SYMETRIQUE":
        messages.append(f"📐 Triangle Symétrique → Explosion imminente (direction incertaine)")

    # Biseaux
    bi_type, bi_force = detecter_biseau(data)
    if bi_type == "BISEAU_MONTANT":
        score -= bi_force
        messages.append(f"↗️ Biseau Montant → Signal BAISSIER (faux breakout probable)")
    elif bi_type == "BISEAU_DESCENDANT":
        score += bi_force
        messages.append(f"↘️ Biseau Descendant → Signal HAUSSIER")

    # Drapeaux
    dr_type, dr_force = detecter_drapeau(data)
    if dr_type == "DRAPEAU_HAUSSIER":
        score += dr_force
        messages.append(f"🚩 Drapeau Haussier → Continuation de la hausse")
    elif dr_type == "DRAPEAU_BAISSIER":
        score -= dr_force
        messages.append(f"🚩 Drapeau Baissier → Continuation de la baisse")

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
