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
from data.paper_trading import (
    ouvrir_trade, fermer_trade, fermer_tous,
    formater_portefeuille, formater_historique, get_compte
)
from data.alertes_intelligentes import (
    get_position_attente, valider_position, ignorer_position,
    get_positions_en_attente
)
from analysis.performance  import formater_performance
from analysis.risk_manager import formater_etat_risque
from analysis.regime       import analyser_regime_complet, get_vix, interpreter_vix
from analysis.sentiment    import formater_sentiment, get_fear_greed_index
from data.prix             import get_historique

logging.basicConfig(level=logging.INFO)

# ── Sécurité : seul toi peut utiliser le bot ──────────────
def autorise(update: Update) -> bool:
    return str(update.effective_chat.id) == str(TELEGRAM_CHAT_ID)

# ── /start ─────────────────────────────────────────────────
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not autorise(update): return
    await update.message.reply_text(
        "🤖 *Bot de Trading actif !*\n\n"
        "📊 *Analyse:*\n"
        "/scan — Scanner tous les marchés\n"
        "/analyse WTI — Analyser un marché\n"
        "/position WTI — Proposition de position\n\n"
        "🤖 *Exécution & Suivi:*\n"
        "/executer WTI — Ouvrir une position\n"
        "/valider 1 — Valider une alerte\n"
        "/portefeuille — Positions ouvertes\n"
        "/fermer 1 — Fermer une position\n"
        "/compte — Solde du compte\n\n"
        "📊 *Analyse Expert:*\n"
        "/marche WTI — Analyse ultra-complète\n"
        "/performance — Mes statistiques\n"
        "/risque — Gestionnaire de risque\n\n"
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

# ── /compte ────────────────────────────────────────────────
async def cmd_compte(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not autorise(update): return
    c = get_compte()
    emoji = "📈" if c["pl_ouvert"] >= 0 else "📉"
    msg  = "💳 *COMPTE PAPER TRADING*\n"
    msg += "━━━━━━━━━━━━━━━━━━\n\n"
    msg += f"💰 *Solde:* `{c['solde']:,.2f} €`\n"
    msg += f"💼 *Valeur nette:* `{c['valeur_nette']:,.2f} €`\n"
    msg += f"{emoji} *P&L ouvert:* `{c['pl_ouvert']:+.2f} €`\n"
    msg += f"📈 *P&L réalisé:* `{c['pl_realise']:+.2f} €`\n"
    msg += f"📂 *Positions ouvertes:* `{c['nb_trades']}`\n"
    msg += f"📋 *Trades terminés:* `{c['nb_historique']}`"
    await update.message.reply_text(msg, parse_mode="Markdown")

# ── /executer ──────────────────────────────────────────────
async def cmd_executer(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not autorise(update): return

    if not ctx.args:
        await update.message.reply_text(
            "Usage: /executer MARCHE\nEx: /executer WTI\nEx: /executer GOLD\n\n"
            "🤖 Analyse le marché et simule une position automatiquement."
        )
        return

    marche = ctx.args[0].upper()
    if marche not in MARCHES:
        await update.message.reply_text(f"Marché inconnu: {marche}")
        return

    await update.message.reply_text(f"⏳ Analyse de {marche} en cours...")

    pos = proposer_position(marche)
    if not pos or pos["direction"] == "NEUTRE":
        await update.message.reply_text(
            f"⚪ Pas de signal clair sur {marche}.\nAucune position ouverte."
        )
        return

    if pos["ratio"] < 1.5:
        await update.message.reply_text(
            f"⚠️ Ratio trop faible ({pos['ratio']}) sur {marche}.\n"
            "Attends un meilleur point d'entrée."
        )
        return

    # Afficher l'analyse
    msg_analyse = formater_position(pos)
    if msg_analyse:
        await update.message.reply_text(msg_analyse, parse_mode="Markdown")

    # Ouvrir le trade simulé
    trade = ouvrir_trade(
        nom_marche  = marche,
        direction   = pos["direction"],
        prix_entree = pos["prix_entree"],
        stop_loss   = pos["stop_loss"],
        take_profit = pos["take_profit"],
        taille      = 100  # 100€ par trade
    )

    emoji_dir = "🟢" if pos["direction"] == "BUY" else "🔴"
    msg  = f"✅ *POSITION OUVERTE !*\n\n"
    msg += f"{emoji_dir} *{pos['direction']} {marche}*\n"
    msg += f"💰 *Entrée:* `{trade['prix_entree']}`\n"
    msg += f"🛑 *Stop Loss:* `{trade['stop_loss']}`\n"
    msg += f"🎯 *Take Profit:* `{trade['take_profit']}`\n"
    msg += f"💵 *Taille:* `100 €`\n"
    msg += f"🔑 *Trade ID:* `{trade['id']}`\n\n"
    msg += f"Suivi: /portefeuille\nFermer: /fermer {trade['id']}"
    await update.message.reply_text(msg, parse_mode="Markdown")

# ── /portefeuille ──────────────────────────────────────────
async def cmd_portefeuille(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not autorise(update): return
    msg = formater_portefeuille()
    await update.message.reply_text(msg, parse_mode="Markdown")

# ── /historique ────────────────────────────────────────────
async def cmd_historique(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not autorise(update): return
    msg = formater_historique()
    await update.message.reply_text(msg, parse_mode="Markdown")

# ── /fermer ────────────────────────────────────────────────
async def cmd_fermer(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not autorise(update): return

    if not ctx.args:
        await update.message.reply_text(
            "Usage: /fermer ID\nEx: /fermer 1\n"
            "Ou: /fermer TOUT\n\n"
            "Utilise /portefeuille pour voir tes IDs."
        )
        return

    arg = ctx.args[0].upper()

    if arg == "TOUT":
        await update.message.reply_text("⏳ Fermeture de toutes les positions...")
        resultats = fermer_tous()
        if not resultats:
            await update.message.reply_text("⚪ Aucune position ouverte.")
            return
        pl_total = sum(t["pl"] for t in resultats)
        emoji    = "📈" if pl_total >= 0 else "📉"
        msg = f"✅ *{len(resultats)} position(s) fermée(s)*\n\n"
        for t in resultats:
            e = "✅" if t["pl"] >= 0 else "❌"
            msg += f"{e} {t['direction']} {t['marche']}: `{t['pl']:+.2f} €`\n"
        msg += f"\n{emoji} *P&L total: `{pl_total:+.2f} €`*"
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    try:
        trade_id = int(arg)
    except ValueError:
        await update.message.reply_text("❌ ID invalide. Ex: /fermer 1")
        return

    trade = fermer_trade(trade_id)
    if trade:
        emoji = "📈" if trade["pl"] >= 0 else "📉"
        msg  = f"✅ *Trade #{trade_id} fermé !*\n\n"
        msg += f"📊 {trade['direction']} {trade['marche']}\n"
        msg += f"💰 Entrée: `{trade['prix_entree']}` → Clôture: `{trade['prix_cloture']}`\n"
        msg += f"{emoji} *P&L réalisé: `{trade['pl']:+.2f} €`*"
        await update.message.reply_text(msg, parse_mode="Markdown")
    else:
        await update.message.reply_text(f"❌ Trade #{trade_id} introuvable ou déjà fermé.")

# ── /aide ──────────────────────────────────────────────────
async def cmd_aide(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not autorise(update): return
    await update.message.reply_text(
        "📖 *Comment utiliser le bot:*\n\n"
        "📊 *Analyse:*\n"
        "• `/scan` → Analyse tous les marchés\n"
        "• `/analyse WTI` → Analyse un marché précis\n"
        "• `/position WTI` → Proposition de position\n\n"
        "🤖 *Exécution automatique (OANDA démo):*\n"
        "• `/executer WTI` → Ouvre une position auto\n"
        "• `/portefeuille` → Voir positions ouvertes\n"
        "• `/fermer 123` → Fermer une position\n"
        "• `/fermer TOUT` → Fermer tout\n"
        "• `/compte` → Solde du compte démo\n\n"
        "📅 *Calendrier:*\n"
        "• `/calendrier` → Annonces de la semaine\n"
        "• `/aujourd_hui` → Annonces du jour\n\n"
        "🟢 BUY → Achat\n"
        "🔴 SELL → Vente\n"
        "⚪ NEUTRE → Attendre\n\n"
        "⚠️ Mode DÉMO — aucun argent réel !",
        parse_mode="Markdown"
    )

# ── /performance ───────────────────────────────────────────
async def cmd_performance(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not autorise(update): return
    await update.message.reply_text("⏳ Calcul des performances...")
    msg = formater_performance()
    await update.message.reply_text(msg, parse_mode="Markdown")

# ── /risque ────────────────────────────────────────────────
async def cmd_risque(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not autorise(update): return
    msg = formater_etat_risque()
    await update.message.reply_text(msg, parse_mode="Markdown")

# ── /marche ────────────────────────────────────────────────
async def cmd_marche(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Analyse ultra-complète d'un marché avec tous les indicateurs"""
    if not autorise(update): return

    if not ctx.args:
        await update.message.reply_text("Usage: /marche WTI\nEx: /marche GOLD")
        return

    nom = ctx.args[0].upper()
    if nom not in MARCHES:
        await update.message.reply_text(f"Marché inconnu: {nom}")
        return

    await update.message.reply_text(f"⏳ Analyse complète de {nom}...")

    info = MARCHES[nom]
    hist = get_historique(info["symbole_yf"], periode="3mo", intervalle="1d")

    msg = f"🔬 *ANALYSE COMPLÈTE — {info['nom']}*\n"
    msg += "━━━━━━━━━━━━━━━━━━\n\n"

    # Régime
    if hist is not None and not hist.empty:
        from analysis.regime import detecter_regime, analyser_correlations, get_saisonnalite
        regime, adx, desc = detecter_regime(hist)
        msg += f"📊 *Régime:* {desc}\n"
        correls = analyser_correlations(nom)
        for c in correls:
            msg += f"• {c}\n"
        saison = get_saisonnalite(nom)
        if saison:
            msg += f"• {saison}\n"
        msg += "\n"

    # Indicateurs
    if hist is not None and not hist.empty:
        from analysis.indicateurs import analyser_tous_indicateurs, formater_indicateurs
        _, details_ind = analyser_tous_indicateurs(hist)
        msg += formater_indicateurs(details_ind) + "\n"

    # Chandeliers
    if hist is not None and not hist.empty:
        from analysis.chandeliers import detecter_patterns, formater_patterns
        patterns = detecter_patterns(hist)
        fmt = formater_patterns(patterns)
        if fmt:
            msg += fmt + "\n"

    # VIX + Sentiment
    vix = get_vix()
    _, desc_vix = interpreter_vix(vix)
    msg += f"😰 {desc_vix}\n"
    msg += formater_sentiment(nom) + "\n"

    await update.message.reply_text(msg, parse_mode="Markdown")

# ── /valider ───────────────────────────────────────────────
async def cmd_valider(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not autorise(update): return

    if not ctx.args:
        # Afficher les positions en attente
        attente = get_positions_en_attente()
        if not attente:
            await update.message.reply_text("⚪ Aucune position en attente de validation.")
            return
        msg = f"⏳ *{len(attente)} position(s) en attente:*\n\n"
        for p in attente:
            emoji = "🟢" if p["direction"] == "BUY" else "🔴"
            msg += f"{emoji} *#{p['id']} — {p['direction']} {p['marche']}*\n"
            msg += f"   Entrée: `{p['prix_entree']}` | R/R: `1:{p['ratio']}`\n"
            msg += f"   `/valider {p['id']}` pour confirmer\n\n"
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    try:
        numero = int(ctx.args[0])
    except ValueError:
        await update.message.reply_text("❌ Usage: /valider 1")
        return

    pos = valider_position(numero)
    if not pos:
        await update.message.reply_text(f"❌ Position #{numero} introuvable ou déjà traitée.")
        return

    # Ouvrir le trade dans le paper trading
    trade = ouvrir_trade(
        nom_marche  = pos["marche"],
        direction   = pos["direction"],
        prix_entree = pos["prix_entree"],
        stop_loss   = pos["stop_loss"],
        take_profit = pos["take_profit"],
        taille      = 100
    )

    emoji_dir = "🟢" if pos["direction"] == "BUY" else "🔴"
    msg  = f"✅ *POSITION #{numero} VALIDÉE ET OUVERTE !*\n\n"
    msg += f"{emoji_dir} *{pos['direction']} {pos['marche']}*\n"
    msg += f"💰 Entrée:      `{trade['prix_entree']}`\n"
    msg += f"🛑 Stop Loss:   `{trade['stop_loss']}`\n"
    msg += f"🎯 Take Profit: `{trade['take_profit']}`\n"
    msg += f"📊 Ratio R/R:   `1:{pos['ratio']}`\n"
    msg += f"💵 Taille:      `100 €`\n"
    msg += f"🔑 Trade ID:    `{trade['id']}`\n\n"
    msg += f"Suivi: /portefeuille | Fermer: /fermer {trade['id']}"
    await update.message.reply_text(msg, parse_mode="Markdown")

# ── /ignorer ───────────────────────────────────────────────
async def cmd_ignorer(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not autorise(update): return

    if not ctx.args:
        await update.message.reply_text("Usage: /ignorer 1")
        return
    try:
        numero = int(ctx.args[0])
    except ValueError:
        await update.message.reply_text("❌ Usage: /ignorer 1")
        return

    ok = ignorer_position(numero)
    if ok:
        await update.message.reply_text(f"❌ Position #{numero} ignorée.")
    else:
        await update.message.reply_text(f"❌ Position #{numero} introuvable.")

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

    app.add_handler(CommandHandler("start",          cmd_start))
    app.add_handler(CommandHandler("analyse",        cmd_analyse))
    app.add_handler(CommandHandler("scan",           cmd_scan))
    app.add_handler(CommandHandler("position",       cmd_position))
    app.add_handler(CommandHandler("marches",        cmd_marches))
    app.add_handler(CommandHandler("calendrier",     cmd_calendrier))
    app.add_handler(CommandHandler("aujourd_hui",    cmd_aujourd_hui))
    app.add_handler(CommandHandler("aide",           cmd_aide))
    # Commandes exécution OANDA
    app.add_handler(CommandHandler("executer",       cmd_executer))
    app.add_handler(CommandHandler("portefeuille",   cmd_portefeuille))
    app.add_handler(CommandHandler("historique",     cmd_historique))
    app.add_handler(CommandHandler("fermer",         cmd_fermer))
    app.add_handler(CommandHandler("compte",         cmd_compte))
    app.add_handler(CommandHandler("valider",        cmd_valider))
    app.add_handler(CommandHandler("ignorer",        cmd_ignorer))
    app.add_handler(CommandHandler("performance",    cmd_performance))
    app.add_handler(CommandHandler("risque",         cmd_risque))
    app.add_handler(CommandHandler("marche",         cmd_marche))

    print("✅ Bot Telegram démarré !")
    print("📱 Ouvre Telegram et envoie /start à ton bot")
    app.run_polling()
