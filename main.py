# ============================================================
#  POINT D'ENTRÉE — Lance le bot
# ============================================================

import schedule
import time
import threading
import asyncio
from config import MARCHES, INTERVALLE_ANALYSE_MIN, HEURE_RAPPORT_MATIN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
from analysis.scoring import analyser_marche, formater_message
from data.calendrier import verifier_alertes_proches, formater_alerte_imminente
from data.rapport import generer_rapport_matin
from telegram_bot import lancer_bot
from telegram.ext import Application

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
    """Scan automatique toutes les heures"""
    print(f"\n🔍 Scan automatique en cours...")
    for nom_marche in MARCHES.keys():
        try:
            resultats = analyser_marche(nom_marche)
            if resultats and resultats.get("signal"):
                message = formater_message(resultats)
                if message:
                    envoyer_message(f"🔔 *ALERTE AUTOMATIQUE*\n\n{message}")
                    print(f"✅ Signal: {nom_marche} {resultats['direction']}")
        except Exception as e:
            print(f"Erreur scan {nom_marche}: {e}")

def verifier_calendrier():
    """Vérifie les annonces importantes dans les 30 prochaines minutes"""
    alertes = verifier_alertes_proches()
    for evt in alertes:
        try:
            message = formater_alerte_imminente(evt)
            envoyer_message(message)
            print(f"⚠️ Alerte: {evt['nom']}")
        except Exception as e:
            print(f"Erreur calendrier: {e}")

def rapport_matin():
    """Envoie le rapport du matin"""
    try:
        print("📊 Envoi du rapport du matin...")
        rapport = generer_rapport_matin()
        envoyer_message(rapport)
    except Exception as e:
        print(f"Erreur rapport: {e}")

def demarrer_taches():
    """Lance toutes les tâches automatiques"""
    schedule.every(INTERVALLE_ANALYSE_MIN).minutes.do(scan_automatique)
    schedule.every(15).minutes.do(verifier_calendrier)
    schedule.every().day.at(HEURE_RAPPORT_MATIN).do(rapport_matin)

    print(f"✅ Scan automatique toutes les {INTERVALLE_ANALYSE_MIN} min")
    print(f"✅ Rapport matin chaque jour à {HEURE_RAPPORT_MATIN}")
    print(f"✅ Alertes calendrier toutes les 15 min")

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
