# ============================================================
#  BOT TELEGRAM — Alertes et commandes
# ============================================================

import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, MARCHES
from analysis.scoring import analyser_marche, formater_message
from data.calendrier import formater_calendrier_semaine, get_evenements_aujourd_hui, formater_alerte_imminente
from analysis.positions import proposer_position, formater_position, analyser_tous_et_proposer

logging.basicConfig(level=logging.INFO)

# ── Sécurité : seul toi peut utiliser le bot ──────────────
def autorise(update: Update) -> bool:
    return str(update.effective_chat.id) == str(TELEGRAM_CHAT_ID)

# ── /start ─────────────────────────────────────────────────
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not autorise(update): return
    await update.message.reply_text(
        "🤖 *Bot de Trading actif !*\n\n"
        "📋 *Commandes disponibles:*\n\n"
        "📊 *Analyse:*\n"
        "/scan — Scanner tous les marchés\n"
        "/analyse WTI — Analyser un marché\n\n"
        "🎯 *Positions:*\n"
        "/position ALL — Toutes les positions\n"
        "/position WTI — Position sur un marché\n\n"
        "📅 *Calendrier:*\n"
        "/calendrier — Annonces de la semaine\n"
        "/aujourd\\_hui — Annonces du jour\n\n"
        "ℹ️ *Infos:*\n"
        "/marches — Liste des marchés\n"
        "/aide — Aide complète",
        parse_mode="Markdown"
    )

# ── /analyse ───────────────────────────────────────────────
async def cmd_analyse(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not autorise(update): return

    if not ctx.args:
        await update.message.reply_text(
            "Usage: /analyse MARCHE\nEx: /analyse WTI"
        )
        return

    marche = ctx.args[0].upper()
    if marche not in MARCHES:
        await update.message.reply_text(
            f"Marché inconnu: {marche}\n"
            f"Marchés disponibles: {', '.join(MARCHES.keys())}"
        )
        return

    await update.message.reply_text(f"⏳ Analyse de {marche} en cours...")

    resultats = analyser_marche(marche)
    message   = formater_message(resultats)

    if message:
        await update.message.reply_text(message, parse_mode="Markdown")
    else:
        await update.message.reply_text("Erreur lors de l'analyse.")

# ── /scan ──────────────────────────────────────────────────
async def cmd_scan(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not autorise(update): return

    await update.message.reply_text("⏳ Scan de tous les marchés en cours...")

    signaux = []
    neutres = []

    for nom_marche in MARCHES.keys():
        resultats = analyser_marche(nom_marche)
        if resultats:
            if resultats.get("signal"):
                signaux.append(resultats)
            else:
                neutres.append(resultats)

    if signaux:
        await update.message.reply_text(
            f"🔔 *{len(signaux)} signal(s) détecté(s) !*",
            parse_mode="Markdown"
        )
        for r in signaux:
            msg = formater_message(r)
            if msg:
                await update.message.reply_text(msg, parse_mode="Markdown")
    else:
        noms = ", ".join([r["marche"] for r in neutres])
        await update.message.reply_text(
            f"⚪ Aucun signal fort détecté.\n"
            f"Marchés analysés: {noms}"
        )

# ── /marches ───────────────────────────────────────────────
async def cmd_marches(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not autorise(update): return

    msg = "📊 *Marchés suivis:*\n\n"
    for nom, info in MARCHES.items():
        msg += f"• `{nom}` — {info['nom']} ({info['type']})\n"

    await update.message.reply_text(msg, parse_mode="Markdown")

# ── /position ──────────────────────────────────────────────
async def cmd_position(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not autorise(update): return

    if not ctx.args:
        await update.message.reply_text(
            "Usage: /position MARCHE\nEx: /position WTI\nOu: /position ALL (toutes les positions)"
        )
        return

    marche = ctx.args[0].upper()

    if marche == "ALL":
        await update.message.reply_text("⏳ Analyse de tous les marchés en cours...")
        positions = analyser_tous_et_proposer()

        if not positions:
            await update.message.reply_text(
                "⚪ Aucune position intéressante en ce moment.\n"
                "Ratio minimum requis: 1:1.5"
            )
            return

        await update.message.reply_text(
            f"🎯 *{len(positions)} position(s) proposée(s)*\n"
            f"_(triées par meilleur ratio R/R)_",
            parse_mode="Markdown"
        )
        for pos in positions[:5]:  # Max 5 positions
            msg = formater_position(pos)
            if msg:
                await update.message.reply_text(msg, parse_mode="Markdown")
        return

    if marche not in MARCHES:
        await update.message.reply_text(
            f"Marché inconnu: {marche}\n"
            f"Disponibles: {', '.join(MARCHES.keys())}\n"
            f"Ou /position ALL pour tout analyser"
        )
        return

    await update.message.reply_text(f"⏳ Calcul de la position sur {marche}...")
    pos = proposer_position(marche)
    msg = formater_position(pos)

    if msg:
        await update.message.reply_text(msg, parse_mode="Markdown")
    else:
        await update.message.reply_text(
            f"⚪ Pas de position claire sur {marche} en ce moment.\n"
            "Attends un signal plus fort."
        )

# ── /calendrier ────────────────────────────────────────────
async def cmd_calendrier(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not autorise(update): return
    msg = formater_calendrier_semaine()
    await update.message.reply_text(msg, parse_mode="Markdown")

# ── /aujourd_hui ────────────────────────────────────────────
async def cmd_aujourd_hui(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not autorise(update): return
    evenements = get_evenements_aujourd_hui()
    if not evenements:
        await update.message.reply_text("✅ Aucune annonce majeure aujourd'hui — conditions normales.")
        return
    msg = "📅 *ANNONCES D'AUJOURD'HUI:*\n\n"
    for evt in evenements:
        msg += f"{evt['impact']} *{evt['nom']}* à {evt['heure']}\n"
        msg += f"📊 {', '.join(evt['marches'])}\n"
        msg += f"💡 {evt['conseil']}\n\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

# ── /aide ──────────────────────────────────────────────────
async def cmd_aide(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not autorise(update): return
    await update.message.reply_text(
        "📖 *Comment utiliser le bot:*\n\n"
        "1. `/scan` → Analyse tous les marchés\n"
        "2. `/analyse WTI` → Analyse un marché précis\n"
        "3. `/calendrier` → Annonces de la semaine\n"
        "4. `/aujourd_hui` → Annonces du jour\n"
        "5. `/marches` → Liste des marchés\n\n"
        "🟢 BUY → Opportunité d'achat\n"
        "🔴 SELL → Opportunité de vente\n"
        "⚪ NEUTRE → Attendre\n\n"
        "⚠️ Vérifie toujours sur MT5 avant d'exécuter !",
        parse_mode="Markdown"
    )

# ── Envoi d'alerte automatique ─────────────────────────────
async def envoyer_alerte(app, message):
    """Envoie une alerte automatique sur Telegram"""
    await app.bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=message,
        parse_mode="Markdown"
    )

# ── Lancer le bot ──────────────────────────────────────────
def lancer_bot():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start",        cmd_start))
    app.add_handler(CommandHandler("analyse",      cmd_analyse))
    app.add_handler(CommandHandler("scan",         cmd_scan))
    app.add_handler(CommandHandler("position",     cmd_position))
    app.add_handler(CommandHandler("marches",      cmd_marches))
    app.add_handler(CommandHandler("calendrier",   cmd_calendrier))
    app.add_handler(CommandHandler("aujourd_hui",  cmd_aujourd_hui))
    app.add_handler(CommandHandler("aide",         cmd_aide))

    print("✅ Bot Telegram démarré !")
    print("📱 Ouvre Telegram et envoie /start à ton bot")
    app.run_polling()
