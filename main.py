# ============================================================
#  POINT D'ENTRÉE — Lance le bot
# ============================================================

import schedule
import time
import threading
import asyncio
from config import MARCHES, INTERVALLE_ANALYSE_MIN
from analysis.scoring import analyser_marche, formater_message
from telegram_bot import lancer_bot, envoyer_alerte
from data.calendrier import verifier_alertes_proches, formater_alerte_imminente
from telegram.ext import Application
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID

def scan_automatique():
    """Scan automatique toutes les heures"""
    print(f"\n🔍 Scan automatique en cours...")

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    async def _scan():
        for nom_marche in MARCHES.keys():
            resultats = analyser_marche(nom_marche)
            if resultats and resultats.get("signal"):
                message = formater_message(resultats)
                if message:
                    await app.bot.send_message(
                        chat_id=TELEGRAM_CHAT_ID,
                        text=f"🔔 *ALERTE AUTOMATIQUE*\n\n{message}",
                        parse_mode="Markdown"
                    )
                    print(f"✅ Signal envoyé: {nom_marche} {resultats['direction']}")

    asyncio.run(_scan())

def verifier_calendrier():
    """Vérifie les annonces importantes dans les 30 prochaines minutes"""
    alertes = verifier_alertes_proches()
    if not alertes:
        return

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    async def _alerter():
        for evt in alertes:
            message = formater_alerte_imminente(evt)
            await app.bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=message,
                parse_mode="Markdown"
            )
            print(f"⚠️ Alerte calendrier: {evt['nom']}")

    asyncio.run(_alerter())

def demarrer_scan_auto():
    """Lance le scan automatique en arrière-plan"""
    schedule.every(INTERVALLE_ANALYSE_MIN).minutes.do(scan_automatique)
    schedule.every(15).minutes.do(verifier_calendrier)  # Vérifie toutes les 15 min
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    print("=" * 50)
    print("   BOT DE TRADING — DÉMARRAGE")
    print("=" * 50)

    # Lance le scan automatique dans un thread séparé
    thread_scan = threading.Thread(target=demarrer_scan_auto, daemon=True)
    thread_scan.start()
    print(f"✅ Scan automatique toutes les {INTERVALLE_ANALYSE_MIN} minutes")

    # Lance le bot Telegram (bloque ici)
    lancer_bot()
