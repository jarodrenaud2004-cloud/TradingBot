# ============================================================
#  SUPPORTS & RÉSISTANCES DYNAMIQUES
#  Détecte les zones clés avec score de force (nb de touches)
#  Un niveau touché 3+ fois = zone majeure
# ============================================================

import numpy as np
from data.prix import get_historique
from config import MARCHES


def detecter_zones_sr(hist, tolerance_pct=0.5, min_touches=2):
    """
    Détecte les zones de support/résistance dynamiques.

    Algorithme:
    1. Trouve tous les pivots hauts/bas (fenêtre 3 bougies)
    2. Regroupe les niveaux proches (tolérance %) en zones
    3. Compte les touches de chaque zone → force
    4. Trie par force décroissante

    Retourne: liste de zones { prix, touches, type, force, age }
    """
    if hist is None or len(hist) < 20:
        return []

    closes = hist["Close"].values
    highs  = hist["High"].values
    lows   = hist["Low"].values
    prix_actuel = closes[-1]
    tolerance   = prix_actuel * tolerance_pct / 100

    # ── Collecter tous les pivots ──────────────────────────
    pivots = []  # (prix, type)

    for i in range(2, len(hist) - 2):
        # Pivot haut = résistance potentielle
        if highs[i] > highs[i-1] and highs[i] > highs[i-2] and \
           highs[i] > highs[i+1] and highs[i] > highs[i+2]:
            pivots.append((highs[i], "R", i))

        # Pivot bas = support potentiel
        if lows[i] < lows[i-1] and lows[i] < lows[i-2] and \
           lows[i] < lows[i+1] and lows[i] < lows[i+2]:
            pivots.append((lows[i], "S", i))

    if not pivots:
        return []

    # ── Regrouper les niveaux proches en zones ─────────────
    zones = []
    pivots_tries = sorted(pivots, key=lambda x: x[0])

    zone_courante = None
    for prix, type_pivot, idx in pivots_tries:
        if zone_courante is None:
            zone_courante = {
                "prix":    prix,
                "touches": 1,
                "indices": [idx],
                "types":   [type_pivot],
                "somme":   prix
            }
        elif abs(prix - zone_courante["prix"]) <= tolerance:
            # Ajouter à la zone existante
            zone_courante["touches"] += 1
            zone_courante["indices"].append(idx)
            zone_courante["types"].append(type_pivot)
            zone_courante["somme"] += prix
            zone_courante["prix"]   = zone_courante["somme"] / zone_courante["touches"]
        else:
            # Nouvelle zone
            if zone_courante["touches"] >= min_touches:
                zones.append(zone_courante)
            zone_courante = {
                "prix":    prix,
                "touches": 1,
                "indices": [idx],
                "types":   [type_pivot],
                "somme":   prix
            }

    if zone_courante and zone_courante["touches"] >= min_touches:
        zones.append(zone_courante)

    # ── Enrichir chaque zone ───────────────────────────────
    zones_enrichies = []
    for z in zones:
        prix_zone = round(z["prix"], 4)
        touches   = z["touches"]

        # Type dominant (S ou R selon position vs prix actuel)
        if prix_zone < prix_actuel:
            type_zone = "SUPPORT"
        else:
            type_zone = "RESISTANCE"

        # Age de la dernière touche (en bougies)
        dernier_idx = max(z["indices"])
        age = len(hist) - 1 - dernier_idx  # bougies depuis la dernière touche

        # Force sur 5 (max 3 touches → 3, mais on peut avoir plus)
        force = min(5, touches)

        # Distance du prix actuel (%)
        distance_pct = abs(prix_zone - prix_actuel) / prix_actuel * 100

        zones_enrichies.append({
            "prix":         prix_zone,
            "touches":      touches,
            "type":         type_zone,
            "force":        force,
            "age":          age,   # bougies depuis dernière touche
            "distance_pct": round(distance_pct, 2),
        })

    # Trier : supports du plus proche au plus loin (croissant)
    # Résistances du plus proche au plus loin (décroissant d'abord)
    zones_enrichies.sort(key=lambda x: x["distance_pct"])

    return zones_enrichies


def trouver_sr_proches(prix_actuel, zones, nb=3):
    """
    Retourne les N niveaux les plus proches du prix actuel.
    Sépare supports (en dessous) et résistances (au dessus).
    """
    supports     = sorted(
        [z for z in zones if z["prix"] < prix_actuel],
        key=lambda x: x["prix"], reverse=True
    )[:nb]

    resistances  = sorted(
        [z for z in zones if z["prix"] > prix_actuel],
        key=lambda x: x["prix"]
    )[:nb]

    return supports, resistances


def score_sr(prix_actuel, zones, direction):
    """
    Score de contexte S/R pour un trade.
    BUY : +1 si on est proche d'un support fort, +1 si résistance lointaine
    SELL: +1 si on est proche d'une résistance forte, +1 si support lointain
    Max: ±2
    """
    if not zones:
        return 0, "S/R: pas de données"

    supports, resistances = trouver_sr_proches(prix_actuel, zones)

    score = 0
    details = []

    if direction == "BUY":
        # Support proche et fort → bon point d'entrée BUY
        if supports:
            s = supports[0]
            if s["distance_pct"] < 1.5 and s["force"] >= 2:
                score += 1
                details.append(f"✅ Support fort à {s['prix']} ({s['distance_pct']:.1f}%)")
            elif s["distance_pct"] < 0.5:
                score += 1
                details.append(f"✅ Sur support ({s['prix']})")

        # Résistance lointaine → bon potentiel
        if resistances:
            r = resistances[0]
            if r["distance_pct"] > 2.0:
                score += 1
                details.append(f"✅ Résistance éloignée à {r['prix']} ({r['distance_pct']:.1f}%)")
            elif r["distance_pct"] < 0.8:
                score -= 1
                details.append(f"⚠️ Résistance immédiate à {r['prix']} ({r['distance_pct']:.1f}%)")

    elif direction == "SELL":
        # Résistance proche → bon point d'entrée SELL
        if resistances:
            r = resistances[0]
            if r["distance_pct"] < 1.5 and r["force"] >= 2:
                score += 1
                details.append(f"✅ Résistance forte à {r['prix']} ({r['distance_pct']:.1f}%)")
            elif r["distance_pct"] < 0.5:
                score += 1
                details.append(f"✅ Sur résistance ({r['prix']})")

        # Support lointain → bon potentiel baissier
        if supports:
            s = supports[0]
            if s["distance_pct"] > 2.0:
                score += 1
                details.append(f"✅ Support éloigné à {s['prix']} ({s['distance_pct']:.1f}%)")
            elif s["distance_pct"] < 0.8:
                score -= 1
                details.append(f"⚠️ Support immédiat à {s['prix']} ({s['distance_pct']:.1f}%)")

    detail_str = " | ".join(details) if details else "S/R: neutre"
    return max(-2, min(2, score)), detail_str


def formater_niveaux_sr(zones, prix_actuel, nb=4):
    """Formate les niveaux S/R pour un message Telegram"""
    if not zones:
        return "📊 *SUPPORTS & RÉSISTANCES*\nAucun niveau détecté\n"

    supports, resistances = trouver_sr_proches(prix_actuel, zones, nb=nb)

    msg = "📊 *SUPPORTS & RÉSISTANCES*\n"

    # Résistances (de la plus proche à la plus éloignée — affichées en haut)
    for r in reversed(resistances):
        barres = "█" * r["force"] + "░" * (5 - r["force"])
        msg += f"🔴 `{r['prix']:>10}` {barres} {r['touches']}x ({r['distance_pct']:.1f}%)\n"

    # Prix actuel
    msg += f"▶️ `{prix_actuel:>10}` ← prix actuel\n"

    # Supports (du plus proche au plus éloigné)
    for s in supports:
        barres = "█" * s["force"] + "░" * (5 - s["force"])
        msg += f"🟢 `{s['prix']:>10}` {barres} {s['touches']}x ({s['distance_pct']:.1f}%)\n"

    msg += "\n"
    return msg


def get_zones_marche(nom_marche, periode="6mo"):
    """
    Récupère et détecte les zones S/R pour un marché donné.
    6 mois de données = niveaux significatifs.
    """
    from config import MARCHES
    info = MARCHES.get(nom_marche)
    if not info:
        return []

    hist = get_historique(info["symbole_yf"], periode=periode, intervalle="1d")
    if hist is None or hist.empty:
        return []

    return detecter_zones_sr(hist)
