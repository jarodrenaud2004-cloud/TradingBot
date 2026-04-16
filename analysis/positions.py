# ============================================================
#  PROPOSITION DE POSITIONS — Analyse complète + conseil
#  Format pro : entrée, SL, TP, ratio, contexte
# ============================================================

from data.prix import get_prix_actuel, get_historique
from analysis.scoring import analyser_marche
from analysis.figures import detecter_supports_resistances
from config import MARCHES
import pandas as pd

def proposer_position(nom_marche):
    """
    Analyse un marché et propose une position concrète
    avec entrée, Stop Loss, Take Profit et ratio
    """
    marche = MARCHES.get(nom_marche)
    if not marche:
        return None

    resultats = analyser_marche(nom_marche)
    if not resultats:
        return None

    prix = resultats.get("prix")
    if not prix:
        return None

    direction = resultats.get("direction", "NEUTRE")
    score     = resultats.get("score_total", 0)

    # Récupérer historique pour S/R
    hist = get_historique(marche["symbole_yf"], periode="3mo", intervalle="1d")
    if hist.empty:
        return None

    supports, resistances = detecter_supports_resistances(hist)

    # Calculer SL et TP selon la direction
    if direction == "BUY":
        # SL = support le plus proche en dessous
        supports_dessous = [s for s in supports if s < prix]
        sl = max(supports_dessous) if supports_dessous else prix * 0.98

        # TP = résistance la plus proche au dessus
        resistances_dessus = [r for r in resistances if r > prix]
        tp = min(resistances_dessus) if resistances_dessus else prix * 1.04

    elif direction == "SELL":
        # SL = résistance la plus proche au dessus
        resistances_dessus = [r for r in resistances if r > prix]
        sl = min(resistances_dessus) if resistances_dessus else prix * 1.02

        # TP = support le plus proche en dessous
        supports_dessous = [s for s in supports if s < prix]
        tp = max(supports_dessous) if supports_dessous else prix * 0.96

    else:
        return None

    # Calcul du ratio Risk/Reward
    risque  = abs(prix - sl)
    gain    = abs(tp - prix)
    ratio   = round(gain / risque, 2) if risque > 0 else 0

    # Variation du jour
    try:
        variation_jour = 0
        if len(hist) >= 2:
            prix_hier = hist["Close"].iloc[-2]
            variation_jour = ((prix - prix_hier) / prix_hier) * 100
    except:
        variation_jour = 0

    # Score de confiance
    if score >= 3:
        confiance = "FORTE 💪"
    elif score >= 2:
        confiance = "BONNE 👍"
    else:
        confiance = "MODÉRÉE ⚠️"

    return {
        "marche":        marche["nom"],
        "symbole":       nom_marche,
        "direction":     direction,
        "prix_entree":   round(prix, 4),
        "stop_loss":     round(sl, 4),
        "take_profit":   round(tp, 4),
        "ratio":         ratio,
        "risque_pct":    round(abs(prix - sl) / prix * 100, 2),
        "gain_pct":      round(abs(tp - prix) / prix * 100, 2),
        "variation_jour": round(variation_jour, 2),
        "confiance":     confiance,
        "score":         score,
        "details":       resultats.get("details", []),
        "emoji":         resultats.get("emoji", "⚪"),
    }

def formater_position(pos):
    """Formate une proposition de position pour Telegram"""
    if not pos:
        return None

    emoji_dir = "🟢" if pos["direction"] == "BUY" else "🔴"
    emoji_ratio = "✅" if pos["ratio"] >= 2 else "⚠️"

    msg  = f"{emoji_dir} *POSITION {pos['direction']} — {pos['marche']}*\n"
    msg += "━━━━━━━━━━━━━━━━━━\n\n"

    msg += f"💰 *Entrée:* `{pos['prix_entree']}`\n"
    msg += f"🛑 *Stop Loss:* `{pos['stop_loss']}` (-{pos['risque_pct']}%)\n"
    msg += f"🎯 *Take Profit:* `{pos['take_profit']}` (+{pos['gain_pct']}%)\n"
    msg += f"{emoji_ratio} *Ratio R/R:* `1:{pos['ratio']}`\n\n"

    msg += f"📊 *Variation du jour:* `{pos['variation_jour']:+.2f}%`\n"
    msg += f"🧠 *Confiance:* {pos['confiance']}\n\n"

    msg += f"📋 *Analyse:*\n"
    for d in pos["details"]:
        if d and "indisponible" not in d.lower():
            msg += f"• {d}\n"

    msg += f"\n⚠️ *Vérifie sur MT5 avant d'exécuter*"

    # Avertissement si ratio faible
    if pos["ratio"] < 2:
        msg += f"\n\n⚠️ *Ratio faible ({pos['ratio']}) — attendre un meilleur point d'entrée*"

    return msg

def analyser_tous_et_proposer():
    """Analyse tous les marchés et propose les meilleures positions"""
    positions = []

    for nom in MARCHES.keys():
        try:
            pos = proposer_position(nom)
            if pos and pos["direction"] != "NEUTRE" and pos["ratio"] >= 1.5:
                positions.append(pos)
        except Exception as e:
            print(f"Erreur position {nom}: {e}")

    # Trier par ratio (meilleur en premier)
    positions.sort(key=lambda x: x["ratio"], reverse=True)
    return positions
