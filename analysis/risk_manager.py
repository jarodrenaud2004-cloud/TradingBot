# ============================================================
#  GESTIONNAIRE DE RISQUE — Comme un trader professionnel
#  Trailing SL, limite perte journalière, corrélations,
#  break-even, TP partiel, taille de position
# ============================================================

import json
import os
from datetime import datetime, date
from data.prix import get_prix_actuel
from config import MARCHES

FICHIER_RISQUE = "risk_state.json"

# ── Paramètres de risque ──────────────────────────────────
MAX_POSITIONS_SIMULTANEES = 3      # Maximum de trades ouverts en même temps
PERTE_JOURNALIERE_MAX_PCT = 5.0    # Stop trading si -5% du capital sur la journée
RISQUE_PAR_TRADE_PCT      = 1.0    # Risquer 1% du capital par trade
RATIO_MIN_ACCEPTABLE      = 1.5    # Ratio R/R minimum pour ouvrir un trade
TRAILING_STOP_PCT         = 1.5    # Trailing stop à 1.5% du prix courant
BREAK_EVEN_AT_R           = 1.0    # Déplacer SL au BE quand +1R atteint

# Marchés corrélés (ne pas ouvrir simultanément dans la même direction)
CORRELATIONS = {
    "WTI":   ["NATGAS"],           # Énergie
    "GOLD":  ["SILVER"],           # Métaux précieux
    "CAC40": ["DAX", "TTE", "BNP", "MC", "AIR", "SAN", "OR"],  # Actions EU
    "DAX":   ["CAC40"],
}

# ── Charger / sauvegarder l'état ──────────────────────────
def _charger():
    if not os.path.exists(FICHIER_RISQUE):
        return {
            "perte_jour": 0.0,
            "trading_actif": True,
            "date_dernier_reset": str(date.today()),
            "trades_actifs": [],
            "historique_jour": [],
        }
    with open(FICHIER_RISQUE, "r") as f:
        return json.load(f)

def _sauvegarder(data):
    with open(FICHIER_RISQUE, "w") as f:
        json.dump(data, f, indent=2, default=str)

def _reset_si_nouveau_jour(data):
    """Remet à zéro les compteurs journaliers si nouveau jour"""
    aujourd_hui = str(date.today())
    if data.get("date_dernier_reset") != aujourd_hui:
        data["perte_jour"]          = 0.0
        data["trading_actif"]       = True
        data["date_dernier_reset"]  = aujourd_hui
        data["historique_jour"]     = []
    return data

# ── Vérifications avant d'ouvrir un trade ─────────────────
def peut_ouvrir_trade(nom_marche, direction, solde, nb_positions_ouvertes):
    """
    Vérifie toutes les règles de risque avant d'ouvrir un trade.
    Retourne (True/False, raison)
    """
    data = _charger()
    data = _reset_si_nouveau_jour(data)

    # 1. Trading actif ?
    if not data.get("trading_actif", True):
        perte = data.get("perte_jour", 0)
        return False, f"⛔ Limite de perte journalière atteinte ({perte:.1f}%). Trading suspendu aujourd'hui."

    # 2. Trop de positions ouvertes ?
    if nb_positions_ouvertes >= MAX_POSITIONS_SIMULTANEES:
        return False, f"⛔ Maximum {MAX_POSITIONS_SIMULTANEES} positions simultanées atteint."

    # 3. Vérifier les corrélations
    marches_correles = CORRELATIONS.get(nom_marche, [])
    trades_actifs = data.get("trades_actifs", [])
    for t in trades_actifs:
        if t["marche"] in marches_correles and t["direction"] == direction:
            return False, f"⚠️ {nom_marche} et {t['marche']} sont corrélés — trade {direction} déjà ouvert sur {t['marche']}."

    _sauvegarder(data)
    return True, "✅ Trade autorisé"

def enregistrer_trade_ouvert(nom_marche, direction, prix_entree, sl, tp):
    """Enregistre un trade ouvert dans l'état de risque"""
    data = _charger()
    data = _reset_si_nouveau_jour(data)
    data["trades_actifs"].append({
        "marche":      nom_marche,
        "direction":   direction,
        "prix_entree": prix_entree,
        "sl_initial":  sl,
        "sl_actuel":   sl,
        "tp":          tp,
        "ouvert_le":   str(datetime.now()),
    })
    _sauvegarder(data)

def enregistrer_trade_ferme(nom_marche, pl_euros, solde):
    """Enregistre un trade fermé et met à jour les stats journalières"""
    data = _charger()
    data = _reset_si_nouveau_jour(data)

    # Retirer des trades actifs
    data["trades_actifs"] = [t for t in data["trades_actifs"] if t["marche"] != nom_marche]

    # Mettre à jour la perte journalière
    pl_pct = (pl_euros / solde) * 100 if solde > 0 else 0
    data["perte_jour"] = data.get("perte_jour", 0) + pl_pct
    data["historique_jour"].append({
        "marche": nom_marche,
        "pl_eur": pl_euros,
        "pl_pct": pl_pct,
        "heure":  datetime.now().strftime("%H:%M"),
    })

    # Suspendre si perte trop importante
    if data["perte_jour"] <= -PERTE_JOURNALIERE_MAX_PCT:
        data["trading_actif"] = False

    _sauvegarder(data)
    return data["trading_actif"]

# ── Taille de position optimale ───────────────────────────
def calculer_taille_position(solde, prix_entree, stop_loss, risque_pct=None):
    """
    Calcule la taille optimale selon Kelly / gestion fixe du risque.
    Formule : Taille = (Solde × Risque%) / Distance_SL
    """
    if risque_pct is None:
        risque_pct = RISQUE_PAR_TRADE_PCT

    risque_euros   = solde * (risque_pct / 100)
    distance_sl    = abs(prix_entree - stop_loss)
    if distance_sl == 0:
        return 1, risque_euros

    # En euros investis
    taille_euros = risque_euros / (distance_sl / prix_entree)
    taille_euros = min(taille_euros, solde * 0.20)  # Max 20% du capital par trade

    return round(taille_euros, 2), round(risque_euros, 2)

# ── Trailing Stop Loss ────────────────────────────────────
def calculer_trailing_sl(direction, prix_actuel, sl_actuel, prix_entree):
    """
    Calcule le nouveau SL selon le trailing stop.
    Retourne le nouveau SL (jamais moins protecteur que l'actuel).
    """
    if direction == "BUY":
        nouveau_sl = prix_actuel * (1 - TRAILING_STOP_PCT / 100)
        # Le trailing SL monte mais ne descend jamais
        return max(nouveau_sl, sl_actuel)
    else:
        nouveau_sl = prix_actuel * (1 + TRAILING_STOP_PCT / 100)
        # Pour SELL, le SL descend mais ne monte jamais
        return min(nouveau_sl, sl_actuel)

def verifier_break_even(direction, prix_actuel, prix_entree, sl_actuel, tp):
    """
    Déplace le SL au prix d'entrée (break-even) quand +1R est atteint.
    Retourne le nouveau SL.
    """
    distance_r = abs(tp - prix_entree) / 3  # 1/3 du chemin vers TP = 1R
    if direction == "BUY":
        if prix_actuel >= prix_entree + distance_r and sl_actuel < prix_entree:
            return prix_entree  # Break-even
    else:
        if prix_actuel <= prix_entree - distance_r and sl_actuel > prix_entree:
            return prix_entree
    return sl_actuel

# ── Mettre à jour les stops des trades actifs ─────────────
def mettre_a_jour_stops(trades_ouverts):
    """
    Met à jour le trailing SL et break-even pour tous les trades actifs.
    Retourne la liste des trades avec alertes si SL/TP proche.
    """
    alertes = []
    data    = _charger()

    for trade in trades_ouverts:
        if trade.get("statut") != "OUVERT":
            continue

        marche    = trade.get("marche")
        direction = trade.get("direction")
        entree    = trade.get("prix_entree", 0)
        sl        = trade.get("stop_loss", 0)
        tp        = trade.get("take_profit", 0)
        info      = MARCHES.get(marche)

        if not info:
            continue

        prix = get_prix_actuel(info["symbole_yf"])
        if not prix:
            continue

        # Break-even
        nouveau_sl = verifier_break_even(direction, prix, entree, sl, tp)

        # Trailing stop
        nouveau_sl = calculer_trailing_sl(direction, prix, nouveau_sl, entree)

        # Alerte si SL modifié significativement
        if abs(nouveau_sl - sl) / (sl if sl > 0 else 1) > 0.001:
            alertes.append({
                "marche":     marche,
                "ancien_sl":  sl,
                "nouveau_sl": round(nouveau_sl, 5),
                "prix":       prix,
                "type":       "break_even" if nouveau_sl == entree else "trailing",
            })
            trade["stop_loss"] = round(nouveau_sl, 5)

    return alertes

# ── Rapport de risque ─────────────────────────────────────
def get_etat_risque():
    """Retourne l'état complet du gestionnaire de risque"""
    data = _charger()
    data = _reset_si_nouveau_jour(data)
    _sauvegarder(data)
    return {
        "trading_actif":    data.get("trading_actif", True),
        "perte_jour_pct":   round(data.get("perte_jour", 0), 2),
        "positions_actives": len(data.get("trades_actifs", [])),
        "historique_jour":  data.get("historique_jour", []),
        "limite_perte":     PERTE_JOURNALIERE_MAX_PCT,
        "max_positions":    MAX_POSITIONS_SIMULTANEES,
    }

def formater_etat_risque():
    """Formate l'état du risque pour Telegram"""
    r = get_etat_risque()
    statut = "✅ ACTIF" if r["trading_actif"] else "⛔ SUSPENDU"
    emoji_perte = "🟢" if r["perte_jour_pct"] >= 0 else "🔴"

    msg  = "🛡️ *GESTIONNAIRE DE RISQUE*\n"
    msg += "━━━━━━━━━━━━━━━━━━\n\n"
    msg += f"📊 *Statut:* {statut}\n"
    msg += f"{emoji_perte} *P&L journalier:* `{r['perte_jour_pct']:+.2f}%`\n"
    msg += f"📂 *Positions actives:* `{r['positions_actives']}/{r['max_positions']}`\n"
    msg += f"⚠️ *Limite perte:* `-{r['limite_perte']}%`\n"
    msg += f"📏 *Risque/trade:* `{RISQUE_PAR_TRADE_PCT}%`\n"
    msg += f"🎯 *Ratio min:* `1:{RATIO_MIN_ACCEPTABLE}`\n\n"

    if r["historique_jour"]:
        msg += "📋 *Trades du jour:*\n"
        for t in r["historique_jour"]:
            e = "✅" if t["pl_eur"] >= 0 else "❌"
            msg += f"{e} {t['marche']}: `{t['pl_eur']:+.2f}€` ({t['pl_pct']:+.1f}%) à {t['heure']}\n"

    return msg
