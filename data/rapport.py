# ============================================================
#  RAPPORT JOURNALIER — Envoyé chaque matin à 8h
# ============================================================

from datetime import datetime
from data.prix import get_prix_actuel
from data.fred_data import analyser_macro
from data.calendrier import get_evenements_aujourd_hui
from analysis.scoring import analyser_marche
from config import MARCHES, FRED_API_KEY

def generer_rapport_matin():
    """Génère le rapport journalier complet"""
    now = datetime.now().strftime("%d/%m/%Y")

    msg  = f"🌅 *RAPPORT DU MATIN — {now}*\n"
    msg += "━━━━━━━━━━━━━━━━━━\n\n"

    # 1. Contexte macro
    msg += "📊 *CONTEXTE MACRO*\n"
    score_macro, detail_macro, _ = analyser_macro(FRED_API_KEY)
    msg += f"{detail_macro}\n\n"

    # 2. Prix des marchés principaux
    msg += "💰 *PRIX DU MOMENT*\n"
    for nom, info in MARCHES.items():
        prix = get_prix_actuel(info["symbole_yf"])
        if prix:
            msg += f"• {info['nom']}: `{prix}`\n"
    msg += "\n"

    # 3. Signaux détectés
    msg += "🎯 *SIGNAUX ACTIFS*\n"
    signaux = []
    for nom in MARCHES.keys():
        r = analyser_marche(nom)
        if r and r.get("signal"):
            signaux.append(r)

    if signaux:
        for r in signaux:
            msg += f"{r['emoji']} {r['marche']} → *{r['direction']}*\n"
    else:
        msg += "⚪ Aucun signal fort ce matin\n"
    msg += "\n"

    # 4. Annonces du jour
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
