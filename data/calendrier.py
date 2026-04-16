# ============================================================
#  CALENDRIER ÉCONOMIQUE — Annonces importantes
#  Alertes automatiques avant chaque publication
# ============================================================

from datetime import datetime, timedelta
import requests

# ── Événements récurrents fixes ───────────────────────────
EVENEMENTS_FIXES = [
    {
        "nom":       "EIA Stocks Pétrole",
        "impact":    "🔴 ÉLEVÉ",
        "marches":   ["WTI", "Pétrole"],
        "heure":     "16:30",
        "jour":      2,  # Mercredi (0=Lundi)
        "conseil":   "NE PAS ouvrir de position WTI 30 min avant/après"
    },
    {
        "nom":       "COT Report (CFTC)",
        "impact":    "🟡 MOYEN",
        "marches":   ["WTI", "GOLD", "CORN"],
        "heure":     "21:30",
        "jour":      4,  # Vendredi
        "conseil":   "Mise à jour du positionnement des acteurs"
    },
    {
        "nom":       "Non-Farm Payrolls (NFP)",
        "impact":    "🔴 ÉLEVÉ",
        "marches":   ["Or", "Dollar", "Indices"],
        "heure":     "14:30",
        "jour":      4,  # 1er Vendredi du mois
        "conseil":   "Volatilité extrême — éviter tout trade actif"
    },
    {
        "nom":       "WASDE Report (USDA)",
        "impact":    "🔴 ÉLEVÉ",
        "marches":   ["CORN", "BLÉ", "SOJA"],
        "heure":     "18:00",
        "jour":      -1,  # Variable (1x/mois)
        "conseil":   "NE PAS trader les grains 1h avant/après"
    },
    {
        "nom":       "Décision BCE (taux)",
        "impact":    "🔴 ÉLEVÉ",
        "marches":   ["CAC40", "DAX", "EUR/USD"],
        "heure":     "14:15",
        "jour":      3,  # Jeudi (toutes les 6 semaines)
        "conseil":   "Impact majeur sur actions européennes"
    },
    {
        "nom":       "Décision Fed (taux)",
        "impact":    "🔴 ÉLEVÉ",
        "marches":   ["Or", "WTI", "Indices US"],
        "heure":     "20:00",
        "jour":      -1,  # Variable
        "conseil":   "Impact global sur tous les marchés"
    },
    {
        "nom":       "CPI Inflation US",
        "impact":    "🔴 ÉLEVÉ",
        "marches":   ["Or", "Dollar"],
        "heure":     "14:30",
        "jour":      -1,  # Variable (mensuel)
        "conseil":   "Inflation haute = pression sur l'or"
    },
]

def get_evenements_semaine():
    """Retourne les événements de la semaine en cours"""
    aujourd_hui = datetime.now()
    debut_semaine = aujourd_hui - timedelta(days=aujourd_hui.weekday())

    evenements = []
    for evt in EVENEMENTS_FIXES:
        if evt["jour"] >= 0:
            date_evt = debut_semaine + timedelta(days=evt["jour"])
            heure = evt["heure"].split(":")
            date_evt = date_evt.replace(
                hour=int(heure[0]),
                minute=int(heure[1]),
                second=0
            )
            evenements.append({
                **evt,
                "date": date_evt,
                "dans": _temps_restant(date_evt)
            })

    return sorted(evenements, key=lambda x: x["date"])

def get_evenements_aujourd_hui():
    """Retourne les événements du jour"""
    aujourd_hui = datetime.now().date()
    return [
        e for e in get_evenements_semaine()
        if e["date"].date() == aujourd_hui
    ]

def verifier_alertes_proches():
    """
    Vérifie si un événement important est dans les 30 prochaines minutes
    Retourne la liste des alertes à envoyer
    """
    maintenant = datetime.now()
    alertes    = []

    for evt in get_evenements_semaine():
        diff = (evt["date"] - maintenant).total_seconds() / 60

        if 0 < diff <= 30:  # Dans les 30 prochaines minutes
            alertes.append(evt)

    return alertes

def _temps_restant(date_evt):
    """Retourne une chaîne lisible du temps restant"""
    maintenant = datetime.now()
    diff = date_evt - maintenant

    if diff.total_seconds() < 0:
        return "Passé"

    heures = int(diff.total_seconds() // 3600)
    minutes = int((diff.total_seconds() % 3600) // 60)

    if heures > 24:
        jours = heures // 24
        return f"dans {jours} jour(s)"
    elif heures > 0:
        return f"dans {heures}h{minutes:02d}"
    else:
        return f"dans {minutes} min"

def formater_calendrier_semaine():
    """Formate le calendrier de la semaine pour Telegram"""
    jours = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi"]
    evenements = get_evenements_semaine()

    msg = "📅 *CALENDRIER ÉCONOMIQUE — Cette semaine*\n"
    msg += "━━━━━━━━━━━━━━━━━━\n\n"

    if not evenements:
        msg += "Aucun événement majeur cette semaine."
        return msg

    for evt in evenements:
        jour_nom = jours[evt["date"].weekday()] if evt["date"].weekday() < 5 else "Weekend"
        msg += f"{evt['impact']} *{evt['nom']}*\n"
        msg += f"📆 {jour_nom} à {evt['heure']} ({evt['dans']})\n"
        msg += f"📊 Marchés: {', '.join(evt['marches'])}\n"
        msg += f"💡 {evt['conseil']}\n\n"

    return msg

def formater_alerte_imminente(evt):
    """Formate une alerte 30 min avant l'événement"""
    msg  = f"⚠️ *ANNONCE DANS 30 MIN !*\n\n"
    msg += f"{evt['impact']} *{evt['nom']}*\n"
    msg += f"🕐 {evt['heure']}\n"
    msg += f"📊 Marchés impactés: {', '.join(evt['marches'])}\n\n"
    msg += f"💡 *Conseil:* {evt['conseil']}"
    return msg
