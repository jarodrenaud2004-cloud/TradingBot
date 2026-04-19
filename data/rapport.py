# ============================================================
#  RAPPORTS AUTOMATIQUES
# ============================================================

from datetime import datetime
from data.prix import get_prix_actuel, get_historique
from data.fred_data import analyser_macro
from data.calendrier import get_evenements_aujourd_hui
from analysis.scoring import analyser_marche
from config import MARCHES, FRED_API_KEY

def generer_rapport_matin():
    """Rapport du matin à 8h"""
    now = datetime.now().strftime("%d/%m/%Y")
    msg  = f"🌅 *RAPPORT DU MATIN — {now}*\n"
    msg += "━━━━━━━━━━━━━━━━━━\n\n"

    # Contexte macro
    msg += "📊 *CONTEXTE MACRO*\n"
    try:
        score_macro, detail_macro, _ = analyser_macro(FRED_API_KEY)
        msg += f"{detail_macro}\n\n"
    except:
        msg += "Données macro indisponibles\n\n"

    # Prix principaux
    msg += "💰 *PRIX*\n"
    for nom, info in MARCHES.items():
        prix = get_prix_actuel(info["symbole_yf"])
        if prix:
            msg += f"• {info['nom']}: `{prix}`\n"
    msg += "\n"

    # Signaux
    msg += "🎯 *SIGNAUX ACTIFS*\n"
    signaux = []
    for nom in MARCHES.keys():
        try:
            r = analyser_marche(nom)
            if r and r.get("signal"):
                signaux.append(r)
        except:
            pass

    if signaux:
        for r in signaux:
            msg += f"{r['emoji']} {r['marche']} → *{r['direction']}*\n"
    else:
        msg += "⚪ Aucun signal fort\n"
    msg += "\n"

    # Annonces du jour
    msg += "📅 *ANNONCES AUJOURD'HUI*\n"
    evenements = get_evenements_aujourd_hui()
    if evenements:
        for evt in evenements:
            msg += f"{evt['impact']} {evt['nom']} à {evt['heure']}\n"
    else:
        msg += "✅ Aucune annonce majeure\n"

    msg += "\n━━━━━━━━━━━━━━━━━━\n"
    msg += "💡 *Bonne session de trading !*"
    return msg

def generer_briefing_ouverture():
    """Briefing avant ouverture marchés EU à 9h"""
    now = datetime.now().strftime("%d/%m/%Y")
    msg  = f"🔔 *BRIEFING OUVERTURE — {now}*\n"
    msg += "━━━━━━━━━━━━━━━━━━\n\n"
    msg += "🕘 Marchés européens ouvrent dans 30 min\n\n"

    # Contexte macro
    msg += "📊 *MACRO DU MOMENT*\n"
    try:
        _, detail_macro, data_macro = analyser_macro(FRED_API_KEY)
        msg += f"{detail_macro}\n\n"
    except:
        msg += "Données indisponibles\n\n"

    # Focus actions EU
    msg += "🇪🇺 *ACTIONS EUROPÉENNES*\n"
    actions_eu = {k: v for k, v in MARCHES.items() if v["type"] == "action_eu"}
    for nom, info in actions_eu.items():
        prix = get_prix_actuel(info["symbole_yf"])
        if prix:
            msg += f"• {info['nom']}: `{prix}`\n"
    msg += "\n"

    # Indices EU
    msg += "📈 *INDICES EU*\n"
    for nom in ["CAC40", "DAX"]:
        info = MARCHES.get(nom)
        if info:
            prix = get_prix_actuel(info["symbole_yf"])
            if prix:
                msg += f"• {info['nom']}: `{prix}`\n"
    msg += "\n"

    # Annonces du jour
    evenements = get_evenements_aujourd_hui()
    if evenements:
        msg += "⚠️ *ATTENTION — Annonces aujourd'hui:*\n"
        for evt in evenements:
            msg += f"{evt['impact']} {evt['nom']} à {evt['heure']}\n"
    else:
        msg += "✅ Aucune annonce majeure aujourd'hui\n"

    msg += "\n━━━━━━━━━━━━━━━━━━\n"
    msg += "📌 *Bonne ouverture !*"
    return msg

def generer_rapport_cloture():
    """Rapport de clôture à 18h"""
    now = datetime.now().strftime("%d/%m/%Y")
    msg  = f"🌆 *RAPPORT DE CLÔTURE — {now}*\n"
    msg += "━━━━━━━━━━━━━━━━━━\n\n"

    # Prix de clôture
    msg += "💰 *PRIX DE CLÔTURE*\n"
    for nom, info in MARCHES.items():
        prix = get_prix_actuel(info["symbole_yf"])
        if prix:
            # Variation du jour
            try:
                hist = get_historique(info["symbole_yf"], periode="2d", intervalle="1d")
                if len(hist) >= 2:
                    prix_hier = hist["Close"].iloc[-2]
                    variation = ((prix - prix_hier) / prix_hier) * 100
                    emoji_var = "🟢" if variation > 0 else "🔴"
                    msg += f"• {info['nom']}: `{prix}` {emoji_var} {variation:+.2f}%\n"
                else:
                    msg += f"• {info['nom']}: `{prix}`\n"
            except:
                msg += f"• {info['nom']}: `{prix}`\n"
    msg += "\n"

    # Signaux actifs
    msg += "🎯 *SIGNAUX EN FIN DE JOURNÉE*\n"
    signaux = []
    for nom in MARCHES.keys():
        try:
            r = analyser_marche(nom)
            if r and r.get("signal"):
                signaux.append(r)
        except:
            pass

    if signaux:
        for r in signaux:
            msg += f"{r['emoji']} {r['marche']} → *{r['direction']}*\n"
    else:
        msg += "⚪ Aucun signal fort en clôture\n"

    msg += "\n━━━━━━━━━━━━━━━━━━\n"
    msg += "💤 *Bonne soirée !*"
    return msg

def detecter_volatilite():
    """
    Détecte les mouvements forts (+2% en variation journalière)
    Retourne la liste des alertes à envoyer
    """
    alertes = []
    for nom, info in MARCHES.items():
        try:
            hist = get_historique(info["symbole_yf"], periode="2d", intervalle="1d")
            if len(hist) >= 2:
                prix_actuel = hist["Close"].iloc[-1]
                prix_hier   = hist["Close"].iloc[-2]
                variation   = ((prix_actuel - prix_hier) / prix_hier) * 100

                if abs(variation) >= 5.0:
                    alertes.append({
                        "marche":    info["nom"],
                        "symbole":   nom,
                        "variation": variation,
                        "prix":      prix_actuel,
                        "direction": "HAUSSE" if variation > 0 else "BAISSE"
                    })
        except:
            pass

    return alertes

def formater_alerte_volatilite(alerte):
    """Formate le message d'alerte de volatilité"""
    emoji = "🚀" if alerte["variation"] > 0 else "💥"
    msg  = f"{emoji} *ALERTE VOLATILITÉ !*\n\n"
    msg += f"📊 *{alerte['marche']}*\n"
    msg += f"💰 Prix: `{alerte['prix']:.4f}`\n"
    msg += f"📈 Variation: `{alerte['variation']:+.2f}%`\n"
    msg += f"🔥 Mouvement: *{alerte['direction']}*\n\n"
    msg += f"⚠️ Surveille ce marché de près !"
    return msg
