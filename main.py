# ============================================================
#  POINT D'ENTRÉE — Lance le bot
# ============================================================

import schedule
import time
import threading
import asyncio
from config import MARCHES, INTERVALLE_ANALYSE_MIN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
from analysis.scoring import analyser_marche, formater_message
from data.calendrier import verifier_alertes_proches, formater_alerte_imminente
from data.rapport import (
    generer_rapport_matin,
    generer_briefing_ouverture,
    generer_rapport_cloture,
    detecter_volatilite,
    formater_alerte_volatilite
)
from telegram_bot import lancer_bot
from telegram.ext import Application

# Garde en mémoire les signaux déjà envoyés (évite les doublons)
signaux_envoyes = set()

def envoyer_message(texte):
    """Envoie un message Telegram depuis un thread"""
    async def _send():
        app = Application.builder().token(TELEGRAM_TOKEN).build()
        async with app:
            await app.bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=texte,
                parse_mode="Markdown"
            )
    asyncio.run(_send())

def scan_automatique():
    """Scan + alertes signaux en temps réel"""
    global signaux_envoyes
    print(f"\n🔍 Scan automatique...")

    for nom_marche in MARCHES.keys():
        try:
            resultats = analyser_marche(nom_marche)
            if resultats and resultats.get("signal"):
                cle = f"{nom_marche}_{resultats['direction']}"
                if cle not in signaux_envoyes:
                    message = formater_message(resultats)
                    if message:
                        envoyer_message(f"🔔 *SIGNAL DÉTECTÉ*\n\n{message}")
                        signaux_envoyes.add(cle)
                        print(f"✅ Signal: {nom_marche} {resultats['direction']}")
            else:
                # Reset signal si plus actif
                for direction in ["BUY", "SELL"]:
                    cle = f"{nom_marche}_{direction}"
                    signaux_envoyes.discard(cle)
        except Exception as e:
            print(f"Erreur scan {nom_marche}: {e}")

def verifier_volatilite():
    """Vérifie les mouvements forts sur tous les marchés"""
    print("📊 Vérification volatilité...")
    try:
        alertes = detecter_volatilite()
        for alerte in alertes:
            message = formater_alerte_volatilite(alerte)
            envoyer_message(message)
            print(f"⚡ Volatilité: {alerte['marche']} {alerte['variation']:+.2f}%")
    except Exception as e:
        print(f"Erreur volatilité: {e}")

def verifier_calendrier():
    """Alertes 30 min avant les annonces"""
    try:
        alertes = verifier_alertes_proches()
        for evt in alertes:
            message = formater_alerte_imminente(evt)
            envoyer_message(message)
            print(f"⚠️ Alerte calendrier: {evt['nom']}")
    except Exception as e:
        print(f"Erreur calendrier: {e}")

def rapport_matin():
    try:
        envoyer_message(generer_rapport_matin())
        print("📊 Rapport matin envoyé")
    except Exception as e:
        print(f"Erreur rapport matin: {e}")

def briefing_ouverture():
    try:
        envoyer_message(generer_briefing_ouverture())
        print("🔔 Briefing ouverture envoyé")
    except Exception as e:
        print(f"Erreur briefing: {e}")

def rapport_cloture():
    try:
        envoyer_message(generer_rapport_cloture())
        print("🌆 Rapport clôture envoyé")
    except Exception as e:
        print(f"Erreur rapport clôture: {e}")

def demarrer_taches():
    """Lance toutes les tâches automatiques"""
    # Rapports journaliers
    schedule.every().day.at("08:00").do(rapport_matin)
    schedule.every().day.at("09:00").do(briefing_ouverture)
    schedule.every().day.at("18:00").do(rapport_cloture)

    # Calendrier — toutes les 15 min
    schedule.every(15).minutes.do(verifier_calendrier)

    print("✅ Tâches programmées:")
    print("   📊 Rapport matin    → 08:00")
    print("   🔔 Briefing EU      → 09:00")
    print("   🌆 Rapport clôture  → 18:00")
    print("   📅 Alertes calendrier → toutes les 15 min")

    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    print("=" * 50)
    print("   BOT DE TRADING — DÉMARRAGE")
    print("=" * 50)

    thread = threading.Thread(target=demarrer_taches, daemon=True)
    thread.start()

    lancer_bot()
