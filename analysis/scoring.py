# ============================================================
#  SCORING GLOBAL — Trader 20 ans d'expérience
#  Score /10 combinant TOUS les indicateurs
# ============================================================

from data.prix         import get_prix_actuel, get_multi_timeframe, get_historique
from data.cot_data     import analyser_cot
from analysis.tendance    import analyser_3_timeframes
from analysis.figures     import analyser_figures
from analysis.indicateurs import analyser_tous_indicateurs
from analysis.chandeliers import detecter_patterns, score_chandeliers
from analysis.regime      import analyser_regime_complet
from analysis.sentiment   import score_sentiment_pour_trade
from analysis.support_resistance import detecter_zones_sr, score_sr
from config import MARCHES, SCORE_MIN_SIGNAL

def analyser_marche(nom_marche):
    """
    Analyse complète d'un marché — niveau trader expert.
    Score /10 combinant technique, fondamental, sentiment, régime.
    """
    marche = MARCHES.get(nom_marche)
    if not marche:
        return None

    symbole_yf  = marche["symbole_yf"]
    nom         = marche["nom"]
    type_marche = marche["type"]

    resultats = {
        "marche":      nom,
        "symbole":     nom_marche,
        "type":        type_marche,
        "details":     [],
        "score_total": 0,
        "score_max":   10,
        "composantes": {},
        "direction":   "NEUTRE",
        "signal":      False,
    }

    # ── 1. Prix actuel ────────────────────────────────────
    prix = get_prix_actuel(symbole_yf)
    if not prix:
        resultats["details"].append("Prix indisponible")
        return resultats
    resultats["prix"] = prix
    resultats["details"].append(f"Prix actuel: {prix}")

    # ── 2. Tendance 3 Timeframes (max ±3) ─────────────────
    try:
        donnees_tf = get_multi_timeframe(symbole_yf)
        biais, score_tf, detail_tf = analyser_3_timeframes(donnees_tf)
        score_tf = max(-3, min(3, score_tf))
        resultats["details"].append(detail_tf)
        resultats["score_total"]          += score_tf
        resultats["biais_tendance"]        = biais
        resultats["composantes"]["tendance"] = score_tf
    except:
        donnees_tf = {}
        resultats["composantes"]["tendance"] = 0

    # Récupérer données daily pour les analyses suivantes
    hist = None
    try:
        hist = get_historique(symbole_yf, periode="3mo", intervalle="1d")
    except:
        pass

    # ── 3. Figures chartistes (max ±3) ────────────────────
    try:
        score_fig, detail_fig = analyser_figures(donnees_tf)
        score_fig = max(-3, min(3, score_fig))
        resultats["details"].append(detail_fig)
        resultats["score_total"]             += score_fig
        resultats["composantes"]["figures"]   = score_fig
    except:
        resultats["composantes"]["figures"]   = 0

    # ── 4. Indicateurs techniques (RSI, MACD, Bollinger, Fibo, Volume) (max ±4) ──
    if hist is not None and not hist.empty:
        try:
            score_ind, details_ind = analyser_tous_indicateurs(hist)
            score_ind = max(-4, min(4, score_ind))
            resultats["score_total"]               += score_ind
            resultats["composantes"]["indicateurs"] = score_ind
            resultats["details_indicateurs"]        = details_ind
            # Ajouter les détails les plus importants
            for cle in ["rsi", "macd", "bollinger"]:
                val = details_ind.get(cle, "")
                if val and "indisponible" not in val:
                    resultats["details"].append(val)
        except:
            resultats["composantes"]["indicateurs"] = 0

    # ── 5. Chandeliers japonais (max ±3) ──────────────────
    if hist is not None and not hist.empty:
        try:
            patterns  = detecter_patterns(hist)
            score_ch  = max(-3, min(3, score_chandeliers(patterns)))
            resultats["score_total"]               += score_ch
            resultats["composantes"]["chandeliers"] = score_ch
            resultats["patterns_chandeliers"]       = patterns
            for p in patterns[:2]:
                resultats["details"].append(f"{p['emoji']} {p['nom']}: {p['signification']}")
        except:
            resultats["composantes"]["chandeliers"] = 0

    # ── 6. COT (max ±2) ───────────────────────────────────
    if nom_marche in ["WTI", "GOLD", "CORN", "SILVER", "WHEAT"]:
        try:
            score_cot, detail_cot = analyser_cot(nom_marche)
            score_cot = max(-2, min(2, score_cot))
            resultats["details"].append(detail_cot)
            resultats["score_total"]        += score_cot
            resultats["composantes"]["cot"]  = score_cot
        except:
            resultats["composantes"]["cot"]  = 0

    # ── 7. Régime de marché (ajustement ±1) ───────────────
    if hist is not None and not hist.empty:
        try:
            score_reg, infos_reg, regime, vix = analyser_regime_complet(nom_marche, hist)
            resultats["score_total"]          += score_reg
            resultats["composantes"]["regime"] = score_reg
            resultats["regime"]                = regime
            resultats["vix"]                   = vix
            resultats["infos_regime"]          = infos_reg
        except:
            resultats["composantes"]["regime"] = 0

    # ── 8. Supports & Résistances dynamiques (max ±2) ─────
    if hist is not None and not hist.empty and prix:
        try:
            # Utiliser 6 mois si dispo, sinon l'historique actuel
            hist_long = hist
            try:
                hist_long = get_historique(symbole_yf, periode="6mo", intervalle="1d")
            except:
                pass

            zones_sr = detecter_zones_sr(hist_long)
            resultats["zones_sr"] = zones_sr

            # Score S/R basé sur direction provisoire
            direction_test_sr = "BUY" if resultats["score_total"] >= 1 else (
                "SELL" if resultats["score_total"] <= -1 else "NEUTRE"
            )
            if direction_test_sr != "NEUTRE":
                score_sr_val, detail_sr = score_sr(prix, zones_sr, direction_test_sr)
                score_sr_val = max(-2, min(2, score_sr_val))
                resultats["score_total"]          += score_sr_val
                resultats["composantes"]["sr"]     = score_sr_val
                if detail_sr and "neutre" not in detail_sr.lower():
                    resultats["details"].append(detail_sr)
            else:
                resultats["composantes"]["sr"] = 0
        except:
            resultats["composantes"]["sr"] = 0

    # ── Déterminer direction et signal ────────────────────
    score = resultats["score_total"]

    # Ajout sentiment si direction identifiable
    if score >= 2:
        direction_test = "BUY"
    elif score <= -2:
        direction_test = "SELL"
    else:
        direction_test = "NEUTRE"

    if direction_test != "NEUTRE":
        try:
            score_sent, msg_sent = score_sentiment_pour_trade(nom_marche, direction_test)
            resultats["score_total"]              += score_sent
            resultats["composantes"]["sentiment"]  = score_sent
            score = resultats["score_total"]
        except:
            resultats["composantes"]["sentiment"]  = 0

    # ── Score qualité /10 ─────────────────────────────────
    score_qualite = min(10, max(0, 5 + score))
    resultats["score_qualite"] = score_qualite

    if score >= SCORE_MIN_SIGNAL:
        resultats["direction"] = "BUY"
        resultats["signal"]    = True
        resultats["emoji"]     = "🟢"
    elif score <= -SCORE_MIN_SIGNAL:
        resultats["direction"] = "SELL"
        resultats["signal"]    = True
        resultats["emoji"]     = "🔴"
    else:
        resultats["direction"] = "NEUTRE"
        resultats["signal"]    = False
        resultats["emoji"]     = "⚪"

    return resultats


def formater_message(resultats):
    """Formate le message Telegram avec score /10"""
    if not resultats:
        return None

    emoji     = resultats.get("emoji", "⚪")
    marche    = resultats.get("marche", "?")
    direction = resultats.get("direction", "NEUTRE")
    prix      = resultats.get("prix", "?")
    score     = resultats.get("score_total", 0)
    qualite   = resultats.get("score_qualite", 5)
    details   = resultats.get("details", [])

    # Barre de qualité visuelle
    barres  = int(qualite)
    barre   = "█" * barres + "░" * (10 - barres)

    msg  = f"{emoji} *SIGNAL {direction}* — {marche}\n"
    msg += f"━━━━━━━━━━━━━━━━━━\n"
    msg += f"💰 Prix: `{prix}`\n"
    msg += f"⭐ Qualité: `{barre}` {qualite}/10\n\n"
    msg += f"📋 *Analyse:*\n"

    for d in details:
        if d and d not in ["Aucune figure détectée", ""] and "indisponible" not in str(d).lower():
            msg += f"• {d}\n"

    msg += f"\n⚠️ *Vérifier sur le graphique avant d'exécuter*"
    return msg
