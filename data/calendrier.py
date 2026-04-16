# ============================================================
#  CALENDRIER ÉCONOMIQUE — API Investing.com / ForexFactory
#  Annonces en temps réel avec impact sur les marchés
# ============================================================

from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup

# ── Événements récurrents fixes (base solide) ─────────────
EVENEMENTS_FIXES = [
    # LUNDI
    {
        "nom": "PMI Manufacturier Zone Euro",
        "impact": "🔴 ÉLEVÉ",
        "marches": ["CAC40", "DAX", "EUR"],
        "heure": "10:00",
        "jour": 0,
        "conseil": "Impact fort sur actions européennes",
        "explication": "Mesure l'activité industrielle EU. >50 = expansion, <50 = contraction"
    },
    # MARDI
    {
        "nom": "PIB Zone Euro",
        "impact": "🔴 ÉLEVÉ",
        "marches": ["CAC40", "DAX", "EUR"],
        "heure": "11:00",
        "jour": 1,
        "conseil": "Impact majeur sur indices européens",
        "explication": "Croissance économique de la zone euro. Surprise positive = hausse indices"
    },
    {
        "nom": "Confiance Consommateur US",
        "impact": "🟡 MOYEN",
        "marches": ["Or", "Indices US"],
        "heure": "16:00",
        "jour": 1,
        "conseil": "Surveiller l'or et les indices US",
        "explication": "Mesure l'optimisme des consommateurs américains"
    },
    # MERCREDI
    {
        "nom": "EIA Stocks Pétrole",
        "impact": "🔴 ÉLEVÉ",
        "marches": ["WTI", "Pétrole", "TotalEnergies"],
        "heure": "16:30",
        "jour": 2,
        "conseil": "NE PAS ouvrir de position WTI 30 min avant/après",
        "explication": "Variation des stocks US. Baisse stocks = prix monte. Hausse stocks = prix baisse"
    },
    {
        "nom": "Minutes Fed (FOMC)",
        "impact": "🔴 ÉLEVÉ",
        "marches": ["Or", "Dollar", "Tous marchés"],
        "heure": "20:00",
        "jour": 2,
        "conseil": "Volatilité extrême — réduire les positions",
        "explication": "Compte-rendu de la réunion de la Fed. Ton hawkish = mauvais pour l'or"
    },
    # JEUDI
    {
        "nom": "Décision BCE (taux)",
        "impact": "🔴 ÉLEVÉ",
        "marches": ["CAC40", "DAX", "BNP", "Sanofi", "LVMH"],
        "heure": "14:15",
        "jour": 3,
        "conseil": "Impact majeur sur toutes les actions européennes",
        "explication": "Taux BCE en hausse = mauvais pour actions. Pause ou baisse = bon signe"
    },
    {
        "nom": "Inscriptions Chômage US",
        "impact": "🟡 MOYEN",
        "marches": ["Or", "Dollar"],
        "heure": "14:30",
        "jour": 3,
        "conseil": "Surveiller l'or et le dollar",
        "explication": "Chômage élevé = Fed plus accommodante = bon pour l'or"
    },
    {
        "nom": "PMI Services Zone Euro",
        "impact": "🟡 MOYEN",
        "marches": ["CAC40", "DAX"],
        "heure": "10:00",
        "jour": 3,
        "conseil": "Impact modéré sur indices EU",
        "explication": "Activité du secteur services en Europe"
    },
    # VENDREDI
    {
        "nom": "Non-Farm Payrolls (NFP)",
        "impact": "🔴 ÉLEVÉ",
        "marches": ["Or", "Dollar", "WTI", "Tous marchés"],
        "heure": "14:30",
        "jour": 4,
        "conseil": "⛔ ÉVITER tout trade — volatilité extrême",
        "explication": "Emplois créés hors agriculture US. Chiffre fort = dollar fort = or baisse"
    },
    {
        "nom": "COT Report (CFTC)",
        "impact": "🟡 MOYEN",
        "marches": ["WTI", "Or", "Maïs", "Blé"],
        "heure": "21:30",
        "jour": 4,
        "conseil": "Analyse du positionnement des hedge funds",
        "explication": "Montre qui achète/vend. Extrême short = squeeze probable"
    },
    {
        "nom": "CPI Inflation Zone Euro",
        "impact": "🔴 ÉLEVÉ",
        "marches": ["CAC40", "DAX", "Or", "BCE"],
        "heure": "11:00",
        "jour": 4,
        "conseil": "Inflation haute = BCE hawkish = mauvais pour actions",
        "explication": "Inflation EU. Surprise hausse = pression sur les taux = indices baissent"
    },
]

# ── Événements mensuels importants ───────────────────────
EVENEMENTS_MENSUELS = [
    {
        "nom": "CPI Inflation US",
        "impact": "🔴 ÉLEVÉ",
        "marches": ["Or", "Dollar", "Tous marchés"],
        "heure": "14:30",
        "conseil": "Événement le plus important du mois",
        "explication": "Inflation US. Surprise hausse = Fed hawkish = or baisse, dollar monte"
    },
    {
        "nom": "WASDE Report (USDA)",
        "impact": "🔴 ÉLEVÉ",
        "marches": ["Maïs", "Blé", "Soja"],
        "heure": "18:00",
        "conseil": "NE PAS trader les grains 1h avant/après",
        "explication": "Rapport mensuel offre/demande agricole mondial. Clé pour maïs et blé"
    },
    {
        "nom": "Réunion Fed (FOMC)",
        "impact": "🔴 ÉLEVÉ",
        "marches": ["Or", "WTI", "CAC40", "DAX", "Tous marchés"],
        "heure": "20:00",
        "conseil": "⛔ Réduire toutes les positions avant l'annonce",
        "explication": "Décision taux Fed. Hausse taux = mauvais pour or et actions"
    },
    {
        "nom": "PIB US",
        "impact": "🔴 ÉLEVÉ",
        "marches": ["Dollar", "Or", "Indices US"],
        "heure": "14:30",
        "conseil": "Impact sur dollar et or",
        "explication": "Croissance économique américaine. Fort = dollar fort = or sous pression"
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
    """Vérifie si un événement important est dans les 60 prochaines minutes"""
    maintenant = datetime.now()
    alertes = []
    alertes_envoyees = set()

    for evt in get_evenements_semaine():
        diff = (evt["date"] - maintenant).total_seconds() / 60
        cle = f"{evt['nom']}_{evt['date'].date()}"

        if 0 < diff <= 60 and cle not in alertes_envoyees:
            alertes.append({**evt, "minutes_restantes": int(diff)})
            alertes_envoyees.add(cle)

    return alertes

def _temps_restant(date_evt):
    """Retourne une chaîne lisible du temps restant"""
    maintenant = datetime.now()
    diff = date_evt - maintenant

    if diff.total_seconds() < 0:
        return "✅ Passé"

    heures = int(diff.total_seconds() // 3600)
    minutes = int((diff.total_seconds() % 3600) // 60)

    if heures > 24:
        jours = heures // 24
        return f"dans {jours}j"
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

    jour_actuel = ""
    for evt in evenements:
        if evt["date"].total_seconds() < 0 if hasattr(evt["date"], 'total_seconds') else False:
            continue

        jour_nom = jours[evt["date"].weekday()] if evt["date"].weekday() < 5 else "Weekend"

        if jour_nom != jour_actuel:
            msg += f"*── {jour_nom.upper()} ──*\n"
            jour_actuel = jour_nom

        msg += f"{evt['impact']} *{evt['nom']}*\n"
        msg += f"🕐 {evt['heure']} ({evt['dans']})\n"
        msg += f"📊 {', '.join(evt['marches'])}\n"
        msg += f"💡 _{evt['explication']}_\n\n"

    # Ajouter les événements mensuels
    msg += "*── ÉVÉNEMENTS MENSUELS (dates variables) ──*\n"
    for evt in EVENEMENTS_MENSUELS:
        msg += f"{evt['impact']} *{evt['nom']}*\n"
        msg += f"💡 _{evt['explication']}_\n\n"

    return msg

def formater_alerte_imminente(evt):
    """Formate une alerte avant l'événement"""
    minutes = evt.get("minutes_restantes", 30)
    msg  = f"⚠️ *ANNONCE DANS {minutes} MIN !*\n\n"
    msg += f"{evt['impact']} *{evt['nom']}*\n"
    msg += f"🕐 {evt['heure']}\n"
    msg += f"📊 Marchés impactés: {', '.join(evt['marches'])}\n\n"
    msg += f"📖 *Pourquoi ça compte:*\n_{evt['explication']}_\n\n"
    msg += f"💡 *À faire:* {evt['conseil']}"
    return msg
