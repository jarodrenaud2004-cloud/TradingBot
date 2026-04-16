# ============================================================
#  SCORING GLOBAL — Combine toutes les analyses
#  Score sur 6 → signal si ≥ 4
# ============================================================

from data.prix       import get_prix_actuel, get_multi_timeframe
from data.cot_data   import analyser_cot
from analysis.tendance import analyser_3_timeframes
from analysis.figures  import analyser_figures
from config import MARCHES, SCORE_MIN_SIGNAL

def analyser_marche(nom_marche):
    """
    Analyse complète d'un marché
    Retourne: direction, score, détails, prix
    """
    marche = MARCHES.get(nom_marche)
    if not marche:
        return None

    symbole_yf = marche["symbole_yf"]
    nom        = marche["nom"]
    type_marche = marche["type"]

    resultats = {
        "marche":  nom,
        "symbole": nom_marche,
        "type":    type_marche,
        "details": [],
        "score_total": 0,
        "direction": "NEUTRE",
        "signal": False,
    }

    # 1. Prix actuel
    prix = get_prix_actuel(symbole_yf)
    if prix:
        resultats["prix"] = prix
        resultats["details"].append(f"Prix actuel: {prix}")
    else:
        resultats["details"].append("Prix indisponible")
        return resultats

    # 2. Tendance 3 TF
    donnees_tf = get_multi_timeframe(symbole_yf)
    biais, score_tf, detail_tf = analyser_3_timeframes(donnees_tf)
    resultats["details"].append(detail_tf)
    resultats["score_total"] += score_tf
    resultats["biais_tendance"] = biais

    # 3. Figures chartistes
    score_fig, detail_fig = analyser_figures(donnees_tf)
    resultats["details"].append(detail_fig)
    resultats["score_total"] += score_fig

    # 4. COT (uniquement pour WTI, GOLD, CORN)
    if nom_marche in ["WTI", "GOLD", "CORN"]:
        score_cot, detail_cot = analyser_cot(nom_marche)
        resultats["details"].append(detail_cot)
        resultats["score_total"] += score_cot

    # Déterminer direction et signal
    score = resultats["score_total"]

    if score >= 2:
        resultats["direction"] = "BUY"
        resultats["signal"]    = True
        resultats["emoji"]     = "🟢"
    elif score <= -2:
        resultats["direction"] = "SELL"
        resultats["signal"]    = True
        resultats["emoji"]     = "🔴"
    else:
        resultats["direction"] = "NEUTRE"
        resultats["signal"]    = False
        resultats["emoji"]     = "⚪"

    return resultats

def formater_message(resultats):
    """Formate le message Telegram pour un signal"""
    if not resultats:
        return None

    emoji     = resultats.get("emoji", "⚪")
    marche    = resultats.get("marche", "?")
    direction = resultats.get("direction", "NEUTRE")
    prix      = resultats.get("prix", "?")
    score     = resultats.get("score_total", 0)
    details   = resultats.get("details", [])

    msg = f"{emoji} *SIGNAL {direction}* — {marche}\n"
    msg += f"━━━━━━━━━━━━━━━━━━\n"
    msg += f"💰 Prix: `{prix}`\n"
    msg += f"📊 Score: `{score}`\n\n"
    msg += f"📋 *Analyse:*\n"

    for d in details:
        if d and d != "Aucune figure détectée":
            msg += f"• {d}\n"

    msg += f"\n⚠️ *Toujours vérifier sur MT5 avant d'exécuter*"
    return msg
