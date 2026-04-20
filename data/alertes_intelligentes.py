# ============================================================
#  ALERTES INTELLIGENTES — Détection mouvement anormal
#  Score statistique (z-score) + contexte complet
# ============================================================

import json
import os
import math
from datetime import datetime
from data.prix       import get_historique, get_prix_actuel
from data.news       import get_news_marche, formater_news
from data.fred_data  import analyser_macro
from data.eia_data   import analyser_petrole
from data.cot_data   import analyser_cot
from analysis.scoring      import analyser_marche
from analysis.positions    import proposer_position
from analysis.chandeliers  import detecter_patterns, formater_patterns, score_chandeliers
from config import MARCHES, FRED_API_KEY, EIA_API_KEY

# Marchés prioritaires avec le plus de données et de fiabilité
MARCHES_PRIORITAIRES = ["WTI", "GOLD", "CAC40", "DAX"]

# Seuil : mouvement > Z_SCORE_SEUIL écarts-types = anormal
Z_SCORE_SEUIL = 1.8   # ~95% des mouvements sont en dessous

# Score technique minimum pour alerter
SCORE_MIN = 1

# Si z-score extrême, alerter même sans signal technique fort
Z_SCORE_EXTREME = 2.0

# Fichier des positions en attente de validation
FICHIER_ATTENTE = "positions_attente.json"

# ── Gestion des positions en attente ──────────────────────
def _charger_attente():
    if not os.path.exists(FICHIER_ATTENTE):
        return {"positions": [], "compteur": 0}
    with open(FICHIER_ATTENTE, "r") as f:
        return json.load(f)

def _sauvegarder_attente(data):
    with open(FICHIER_ATTENTE, "w") as f:
        json.dump(data, f, indent=2, default=str)

def ajouter_position_attente(position_data):
    """Ajoute une position en attente de validation. Retourne son numéro."""
    data = _charger_attente()
    data["compteur"] += 1
    position_data["id"]     = data["compteur"]
    position_data["statut"] = "EN_ATTENTE"
    position_data["cree_le"] = datetime.now().strftime("%d/%m/%Y %H:%M")
    data["positions"].append(position_data)
    _sauvegarder_attente(data)
    return data["compteur"]

def get_position_attente(numero):
    """Récupère une position en attente par son numéro."""
    data = _charger_attente()
    for p in data["positions"]:
        if p["id"] == numero and p["statut"] == "EN_ATTENTE":
            return p
    return None

def valider_position(numero):
    """Marque une position comme validée et la retire de la liste."""
    data = _charger_attente()
    for p in data["positions"]:
        if p["id"] == numero and p["statut"] == "EN_ATTENTE":
            p["statut"] = "VALIDEE"
            _sauvegarder_attente(data)
            return p
    return None

def ignorer_position(numero):
    """Ignore une position en attente."""
    data = _charger_attente()
    for p in data["positions"]:
        if p["id"] == numero and p["statut"] == "EN_ATTENTE":
            p["statut"] = "IGNOREE"
            _sauvegarder_attente(data)
            return True
    return False

def get_positions_en_attente():
    data = _charger_attente()
    return [p for p in data["positions"] if p["statut"] == "EN_ATTENTE"]

# ── Détection de mouvement anormal (z-score) ──────────────
def calculer_zscore(nom_marche):
    """
    Compare le mouvement du jour à la volatilité historique (20 jours).
    Retourne: z_score, variation_jour, volatilite_normale
    """
    info = MARCHES.get(nom_marche)
    if not info:
        return None, 0, 0

    hist = get_historique(info["symbole_yf"], periode="3mo", intervalle="1d")
    if hist is None or len(hist) < 10:
        return None, 0, 0

    # Calcul des rendements journaliers
    hist = hist.copy()
    hist["return"] = hist["Close"].pct_change() * 100

    # Volatilité sur 20 derniers jours
    returns_hist = hist["return"].dropna().iloc[-21:-1]  # 20 jours hors aujourd'hui
    if len(returns_hist) < 5:
        return None, 0, 0

    moyenne = returns_hist.mean()
    ecart   = returns_hist.std()
    if ecart == 0:
        return None, 0, 0

    # Variation du jour
    if len(hist) >= 2:
        variation_jour = hist["return"].iloc[-1]
    else:
        return None, 0, 0

    z_score = (variation_jour - moyenne) / ecart
    return round(z_score, 2), round(variation_jour, 3), round(ecart, 3)

# ── Contexte macro complet ─────────────────────────────────
def get_contexte_macro(nom_marche):
    """Rassemble toutes les données macro disponibles pour un marché."""
    contexte = {}

    # FRED (macro global)
    try:
        score_macro, detail_macro, _ = analyser_macro(FRED_API_KEY)
        contexte["macro"] = detail_macro
    except:
        contexte["macro"] = None

    # Chandeliers japonais
    try:
        info = MARCHES.get(nom_marche)
        if info:
            from data.prix import get_historique
            hist = get_historique(info["symbole_yf"], periode="1mo", intervalle="1d")
            if hist is not None and not hist.empty:
                patterns = detecter_patterns(hist)
                contexte["chandeliers"] = formater_patterns(patterns)
                contexte["score_chandeliers"] = score_chandeliers(patterns)
    except:
        contexte["chandeliers"] = None
        contexte["score_chandeliers"] = 0

    # Figures chartistes
    try:
        from analysis.figures import detecter_triangle, detecter_tete_epaules, detecter_biseau, detecter_drapeau
        figures = []
        if hist is not None and not hist.empty:
            te_type, _ = detecter_tete_epaules(hist)
            if te_type:
                figures.append("🎯 Tête-Épaules " + ("Inversé → HAUSSIER" if te_type == "TE_HAUSSIER" else "→ BAISSIER"))
            tri, _ = detecter_triangle(hist)
            if tri:
                figures.append(f"📐 Triangle {tri.replace('_', ' ').title()}")
            bi, _ = detecter_biseau(hist)
            if bi:
                figures.append(f"↗ Biseau {bi.replace('_', ' ').title()}")
            dr, _ = detecter_drapeau(hist)
            if dr:
                figures.append(f"🚩 {dr.replace('_', ' ').title()}")
        contexte["figures"] = "\n".join(f"• {f}" for f in figures) if figures else None
    except:
        contexte["figures"] = None

    # EIA (pétrole/gaz uniquement)
    if nom_marche in ["WTI", "NATGAS"]:
        try:
            signal_eia, detail_eia = analyser_petrole(EIA_API_KEY)
            contexte["eia"] = detail_eia
        except:
            contexte["eia"] = None

    # COT (positionnement fonds)
    if nom_marche in ["WTI", "GOLD", "SILVER", "CORN", "WHEAT"]:
        try:
            signal_cot, detail_cot = analyser_cot(nom_marche)
            contexte["cot"] = detail_cot
        except:
            contexte["cot"] = None

    # Indicateurs techniques avancés
    if hist is not None and not hist.empty:
        try:
            from analysis.indicateurs import analyser_tous_indicateurs
            _, details_ind = analyser_tous_indicateurs(hist)
            contexte["indicateurs"] = details_ind
        except:
            contexte["indicateurs"] = {}

    # Régime de marché
    try:
        from analysis.regime import analyser_regime_complet, formater_regime
        _, infos_reg, regime, vix = analyser_regime_complet(nom_marche, hist)
        contexte["regime_msg"] = formater_regime(infos_reg, regime, vix)
    except:
        contexte["regime_msg"] = None

    # Sentiment
    try:
        from analysis.sentiment import formater_sentiment
        contexte["sentiment_msg"] = formater_sentiment(nom_marche)
    except:
        contexte["sentiment_msg"] = None

    return contexte

# ── Construire le message d'alerte complet ─────────────────
def construire_alerte(nom_marche, resultats, pos, z_score, variation, volatilite_normale, news, contexte, numero):
    """Construit le message Telegram ultra-détaillé."""

    emoji_dir  = "🟢" if pos["direction"] == "BUY" else "🔴"
    emoji_z    = "🚀" if variation > 0 else "💥"
    force_mvt  = "EXCEPTIONNEL" if abs(z_score) > 3 else "FORT" if abs(z_score) > 2 else "NOTABLE"

    msg  = f"🚨 *ALERTE SIGNAL #{numero} — {pos['marche'].upper()}*\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━\n\n"

    # Mouvement détecté
    msg += f"{emoji_z} *MOUVEMENT {force_mvt}*\n"
    msg += f"📈 Variation: `{variation:+.2f}%`\n"
    msg += f"📊 Volatilité normale: `±{volatilite_normale:.2f}%`\n"
    msg += f"⚡ Intensité: `{abs(z_score):.1f}x` la normale\n\n"

    # Position proposée
    emoji_ratio = "✅" if pos["ratio"] >= 2 else "⚠️"
    msg += f"{emoji_dir} *POSITION PROPOSÉE*\n"
    msg += f"Direction: *{pos['direction']}*\n"
    msg += f"💰 Entrée:     `{pos['prix_entree']}`\n"
    msg += f"🛑 Stop Loss:  `{pos['stop_loss']}` (-{pos['risque_pct']}%)\n"
    msg += f"🎯 Take Profit: `{pos['take_profit']}` (+{pos['gain_pct']}%)\n"
    msg += f"{emoji_ratio} Ratio R/R: `1:{pos['ratio']}`\n"
    msg += f"🧠 Confiance: {pos['confiance']}\n\n"

    # Analyse technique
    msg += f"📋 *ANALYSE TECHNIQUE*\n"
    for d in pos["details"]:
        if d and "indisponible" not in d.lower():
            msg += f"• {d}\n"
    msg += "\n"

    # Chandeliers japonais
    chandelier_msg = contexte.get("chandeliers")
    if chandelier_msg:
        msg += chandelier_msg + "\n"

    # Figures chartistes
    figures_msg = contexte.get("figures")
    if figures_msg:
        msg += f"📐 *FIGURES CHARTISTES*\n{figures_msg}\n\n"

    # News réelles
    msg += f"📰 *ACTUALITÉS RÉCENTES*\n"
    msg += formater_news(news) + "\n\n"

    # Indicateurs techniques
    details_ind = contexte.get("indicateurs", {})
    if details_ind:
        from analysis.indicateurs import formater_indicateurs
        ind_msg = formater_indicateurs(details_ind)
        if ind_msg:
            msg += ind_msg + "\n"

    # Régime de marché + corrélations
    regime_msg = contexte.get("regime_msg")
    if regime_msg:
        msg += regime_msg + "\n"

    # Sentiment
    sentiment_msg = contexte.get("sentiment_msg")
    if sentiment_msg:
        msg += sentiment_msg + "\n"

    # News réelles
    msg += f"📰 *ACTUALITÉS RÉCENTES*\n"
    msg += formater_news(news) + "\n\n"

    # Contexte macro
    msg += f"🌍 *CONTEXTE MACRO*\n"
    if contexte.get("macro"):
        msg += f"{contexte['macro']}\n"
    if contexte.get("eia"):
        msg += f"🛢️ EIA: {contexte['eia']}\n"
    if contexte.get("cot"):
        msg += f"📊 COT: {contexte['cot']}\n"
    msg += "\n"

    # Score qualité
    qualite = contexte.get("score_qualite", 5)
    barres  = "█" * qualite + "░" * (10 - qualite)
    msg += f"⭐ *Score qualité: `{barres}` {qualite}/10*\n\n"

    # Validation
    msg += "━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"✅ `/valider {numero}` → Ouvrir la position\n"
    msg += f"❌ `/ignorer {numero}` → Passer"

    return msg

# ── Scanner les marchés prioritaires ──────────────────────
def scanner_signaux_forts():
    """
    Scanne les marchés prioritaires.
    Retourne les alertes à envoyer (mouvements anormaux + signal fort).
    """
    alertes = []

    for nom_marche in MARCHES_PRIORITAIRES:
        try:
            # 1. Vérifier si le mouvement est statistiquement anormal
            z_score, variation, volatilite_normale = calculer_zscore(nom_marche)
            if z_score is None:
                continue

            if abs(z_score) < Z_SCORE_SEUIL:
                continue  # Mouvement normal, pas d'alerte

            # 2. Vérifier le signal technique
            resultats = analyser_marche(nom_marche)
            if not resultats:
                continue

            score     = resultats.get("score_total", 0)
            direction = resultats.get("direction", "NEUTRE")

            # Cas extrême : mouvement très fort → alerter même sans signal technique
            extreme = abs(z_score) >= Z_SCORE_EXTREME
            if not extreme:
                if abs(score) < SCORE_MIN:
                    continue  # Signal technique trop faible

            # 3. Déterminer la direction (signal technique ou mouvement)
            if direction == "NEUTRE" or abs(score) < SCORE_MIN:
                # Pas de signal technique → la direction suit le mouvement du prix
                direction = "SELL" if variation < 0 else "BUY"

            # Cohérence mouvement/signal (seulement si signal technique présent)
            if abs(score) >= SCORE_MIN and direction != "NEUTRE":
                if direction == "BUY" and variation < 0:
                    continue
                if direction == "SELL" and variation > 0:
                    continue

            # 4. Calculer la position
            pos = proposer_position(nom_marche)
            if not pos or pos["ratio"] < 1.8:
                continue  # Ratio insuffisant

            # 5. Récupérer news et contexte
            news     = get_news_marche(nom_marche, nb=4)
            contexte = get_contexte_macro(nom_marche)

            # 5b. Score qualité global
            score_qualite = resultats.get("score_qualite", 5)
            contexte["score_qualite"] = score_qualite

            # Vérification risque
            from analysis.risk_manager import peut_ouvrir_trade
            from data.paper_trading import get_compte
            try:
                compte = get_compte()
                nb_pos = compte.get("nb_trades", 0)
                autorise, msg_risque = peut_ouvrir_trade(nom_marche, direction, compte["solde"], nb_pos)
                if not autorise:
                    print(f"⛔ {nom_marche}: {msg_risque}")
                    continue
            except:
                pass

            # 6. Enregistrer en attente
            position_data = {
                "marche":      nom_marche,
                "direction":   direction,
                "prix_entree": pos["prix_entree"],
                "stop_loss":   pos["stop_loss"],
                "take_profit": pos["take_profit"],
                "ratio":       pos["ratio"],
                "z_score":     z_score,
                "variation":   variation,
                "score":       score,
            }
            numero = ajouter_position_attente(position_data)

            # 7. Construire le message
            message = construire_alerte(
                nom_marche, resultats, pos,
                z_score, variation, volatilite_normale,
                news, contexte, numero
            )

            alertes.append({
                "numero":  numero,
                "marche":  nom_marche,
                "message": message,
            })

        except Exception as e:
            print(f"Erreur alerte {nom_marche}: {e}")

    return alertes
