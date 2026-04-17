# ============================================================
#  PAPER TRADING — Simulation de trades (sans broker réel)
#  Enregistre les trades, calcule P&L en temps réel
# ============================================================

import json
import os
from datetime import datetime
from data.prix import get_prix_actuel
from config import MARCHES

FICHIER_TRADES  = "paper_trades.json"
SOLDE_INITIAL   = 10000.0   # 10 000 € de départ

# ── Charger / sauvegarder ─────────────────────────────────
def _charger():
    if not os.path.exists(FICHIER_TRADES):
        return {"solde": SOLDE_INITIAL, "trades": [], "historique": []}
    with open(FICHIER_TRADES, "r") as f:
        return json.load(f)

def _sauvegarder(data):
    with open(FICHIER_TRADES, "w") as f:
        json.dump(data, f, indent=2, default=str)

# ── Ouvrir une position ────────────────────────────────────
def ouvrir_trade(nom_marche, direction, prix_entree, stop_loss, take_profit, taille=100):
    """
    Ouvre un trade simulé.
    taille = montant en euros investis (ex: 100€)
    """
    data = _charger()

    # Calcul des unités selon le prix
    units = round(taille / prix_entree, 6) if prix_entree > 0 else 1

    trade = {
        "id":           len(data["trades"]) + 1,
        "marche":       nom_marche,
        "direction":    direction,
        "prix_entree":  prix_entree,
        "stop_loss":    stop_loss,
        "take_profit":  take_profit,
        "units":        units,
        "taille_eur":   taille,
        "ouvert_le":    datetime.now().strftime("%d/%m/%Y %H:%M"),
        "statut":       "OUVERT",
        "pl":           0.0,
    }

    data["trades"].append(trade)
    _sauvegarder(data)
    return trade

# ── Fermer une position ────────────────────────────────────
def fermer_trade(trade_id, prix_cloture=None):
    """Ferme un trade et calcule le P&L réalisé"""
    data = _charger()

    for trade in data["trades"]:
        if trade["id"] == trade_id and trade["statut"] == "OUVERT":
            # Prix de clôture = prix actuel si non fourni
            if not prix_cloture:
                info = MARCHES.get(trade["marche"])
                if info:
                    prix_cloture = get_prix_actuel(info["symbole_yf"])
                if not prix_cloture:
                    return None

            # Calcul P&L
            if trade["direction"] == "BUY":
                pl = (prix_cloture - trade["prix_entree"]) * trade["units"]
            else:
                pl = (trade["prix_entree"] - prix_cloture) * trade["units"]

            pl = round(pl, 2)

            trade["statut"]      = "FERME"
            trade["prix_cloture"] = round(prix_cloture, 5)
            trade["pl"]           = pl
            trade["ferme_le"]    = datetime.now().strftime("%d/%m/%Y %H:%M")

            # Mettre à jour le solde
            data["solde"] = round(data["solde"] + pl, 2)

            # Archiver
            data["historique"].append(trade)
            data["trades"] = [t for t in data["trades"] if t["id"] != trade_id]

            _sauvegarder(data)
            return trade

    return None

# ── Fermer tout ────────────────────────────────────────────
def fermer_tous():
    data = _charger()
    resultats = []
    for trade in list(data["trades"]):
        if trade["statut"] == "OUVERT":
            result = fermer_trade(trade["id"])
            if result:
                resultats.append(result)
    return resultats

# ── Mettre à jour les P&L en temps réel ───────────────────
def mettre_a_jour_pl():
    """Calcule le P&L non réalisé pour chaque trade ouvert"""
    data = _charger()
    for trade in data["trades"]:
        if trade["statut"] == "OUVERT":
            info = MARCHES.get(trade["marche"])
            if not info:
                continue
            prix = get_prix_actuel(info["symbole_yf"])
            if not prix:
                continue
            if trade["direction"] == "BUY":
                pl = (prix - trade["prix_entree"]) * trade["units"]
            else:
                pl = (trade["prix_entree"] - prix) * trade["units"]
            trade["pl"]           = round(pl, 2)
            trade["prix_actuel"]  = round(prix, 5)

            # Vérifier SL / TP atteints
            if trade["direction"] == "BUY":
                if prix <= trade["stop_loss"]:
                    trade["statut_alerte"] = "⛔ SL ATTEINT"
                elif prix >= trade["take_profit"]:
                    trade["statut_alerte"] = "✅ TP ATTEINT"
                else:
                    trade["statut_alerte"] = ""
            else:
                if prix >= trade["stop_loss"]:
                    trade["statut_alerte"] = "⛔ SL ATTEINT"
                elif prix <= trade["take_profit"]:
                    trade["statut_alerte"] = "✅ TP ATTEINT"
                else:
                    trade["statut_alerte"] = ""

    _sauvegarder(data)
    return data["trades"]

# ── Infos du compte ────────────────────────────────────────
def get_compte():
    data    = _charger()
    trades  = mettre_a_jour_pl()
    pl_open = sum(t["pl"] for t in trades)
    pl_hist = sum(t["pl"] for t in data.get("historique", []))
    return {
        "solde":         data["solde"],
        "pl_ouvert":     round(pl_open, 2),
        "pl_realise":    round(pl_hist, 2),
        "valeur_nette":  round(data["solde"] + pl_open, 2),
        "nb_trades":     len(trades),
        "nb_historique": len(data.get("historique", [])),
    }

# ── Formatage Telegram ─────────────────────────────────────
def formater_portefeuille():
    trades = mettre_a_jour_pl()
    compte = get_compte()

    if not trades:
        return (
            "⚪ *Aucune position ouverte.*\n\n"
            f"💳 Solde: `{compte['solde']:,.2f} €`\n"
            f"📊 Trades réalisés: `{compte['nb_historique']}`\n"
            f"📈 P&L total réalisé: `{compte['pl_realise']:+.2f} €`"
        )

    msg  = f"📂 *{len(trades)} POSITION(S) OUVERTE(S)*\n"
    msg += "━━━━━━━━━━━━━━━━━━\n\n"

    for t in trades:
        emoji_dir = "🟢" if t["direction"] == "BUY" else "🔴"
        emoji_pl  = "📈" if t["pl"] >= 0 else "📉"
        alerte    = f"\n{t.get('statut_alerte','')}" if t.get("statut_alerte") else ""

        msg += f"{emoji_dir} *{t['direction']} {t['marche']}* (ID: {t['id']})\n"
        msg += f"💰 Entrée: `{t['prix_entree']}` → Actuel: `{t.get('prix_actuel', '...')}`\n"
        msg += f"🛑 SL: `{t['stop_loss']}` | 🎯 TP: `{t['take_profit']}`\n"
        msg += f"{emoji_pl} P&L: `{t['pl']:+.2f} €`{alerte}\n"
        msg += f"📅 Ouvert le: {t['ouvert_le']}\n\n"

    emoji_net = "📈" if compte["pl_ouvert"] >= 0 else "📉"
    msg += "━━━━━━━━━━━━━━━━━━\n"
    msg += f"💳 *Solde:* `{compte['solde']:,.2f} €`\n"
    msg += f"{emoji_net} *P&L ouvert:* `{compte['pl_ouvert']:+.2f} €`\n"
    msg += f"💼 *Valeur nette:* `{compte['valeur_nette']:,.2f} €`"
    return msg

def formater_historique():
    data = _charger()
    hist = data.get("historique", [])

    if not hist:
        return "📋 *Aucun trade terminé pour l'instant.*"

    msg  = f"📋 *HISTORIQUE — {len(hist)} trade(s)*\n"
    msg += "━━━━━━━━━━━━━━━━━━\n\n"

    pl_total = 0
    for t in hist[-10:]:  # 10 derniers
        emoji = "✅" if t["pl"] >= 0 else "❌"
        emoji_dir = "🟢" if t["direction"] == "BUY" else "🔴"
        msg += f"{emoji} {emoji_dir} {t['direction']} *{t['marche']}*\n"
        msg += f"   {t['ouvert_le']} → {t.get('ferme_le','?')}\n"
        msg += f"   P&L: `{t['pl']:+.2f} €`\n\n"
        pl_total += t["pl"]

    emoji_total = "📈" if pl_total >= 0 else "📉"
    msg += f"━━━━━━━━━━━━━━━━━━\n"
    msg += f"{emoji_total} *P&L total réalisé: `{pl_total:+.2f} €`*"
    return msg
