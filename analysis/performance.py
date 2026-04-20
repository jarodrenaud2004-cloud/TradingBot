# ============================================================
#  SUIVI DE PERFORMANCE — Comme un fonds professionnel
#  Win rate, Sharpe, drawdown, rapport mensuel
# ============================================================

import json
import os
from datetime import datetime, date
from data.prix import get_prix_actuel
from config import MARCHES

FICHIER_PERF = "paper_trades.json"

def _charger():
    if not os.path.exists(FICHIER_PERF):
        return {"solde": 250.0, "trades": [], "historique": []}
    with open(FICHIER_PERF, "r") as f:
        return json.load(f)

# ── Calcul des métriques ──────────────────────────────────
def calculer_metriques():
    """Calcule toutes les métriques de performance"""
    data = _charger()
    historique = data.get("historique", [])

    if not historique:
        return {
            "nb_trades":       0,
            "nb_gagnants":     0,
            "nb_perdants":     0,
            "win_rate":        0,
            "pl_total":        0,
            "pl_moyen":        0,
            "gain_moyen":      0,
            "perte_moyenne":   0,
            "ratio_rr_reel":   0,
            "max_drawdown":    0,
            "sharpe":          0,
            "meilleur_trade":  None,
            "pire_trade":      None,
            "serie_gagnante":  0,
            "serie_perdante":  0,
            "solde_actuel":    data.get("solde", 250.0),
            "solde_initial":   250.0,
            "performance_pct": 0,
        }

    pl_list   = [t["pl"] for t in historique]
    gagnants  = [p for p in pl_list if p > 0]
    perdants  = [p for p in pl_list if p < 0]

    # Métriques de base
    nb_total  = len(pl_list)
    win_rate  = round(len(gagnants) / nb_total * 100, 1) if nb_total > 0 else 0
    pl_total  = round(sum(pl_list), 2)
    pl_moyen  = round(pl_total / nb_total, 2) if nb_total > 0 else 0

    gain_moy  = round(sum(gagnants) / len(gagnants), 2) if gagnants else 0
    perte_moy = round(sum(perdants) / len(perdants), 2) if perdants else 0

    ratio_rr  = round(abs(gain_moy / perte_moy), 2) if perte_moy != 0 else 0

    # Max Drawdown
    solde     = 250.0
    pic       = solde
    drawdown_max = 0
    for pl in pl_list:
        solde += pl
        if solde > pic:
            pic = solde
        dd = (pic - solde) / pic * 100 if pic > 0 else 0
        if dd > drawdown_max:
            drawdown_max = dd

    # Sharpe Ratio (simplifié)
    if len(pl_list) >= 3:
        import statistics
        moy = statistics.mean(pl_list)
        std = statistics.stdev(pl_list)
        sharpe = round((moy / std) * (252 ** 0.5), 2) if std > 0 else 0
    else:
        sharpe = 0

    # Meilleur / pire trade
    meilleur = max(historique, key=lambda x: x["pl"]) if historique else None
    pire     = min(historique, key=lambda x: x["pl"]) if historique else None

    # Séries (consecutives wins/losses)
    serie_max_gain = serie_max_perte = 0
    serie_g = serie_p = 0
    for pl in pl_list:
        if pl > 0:
            serie_g += 1
            serie_p  = 0
            serie_max_gain = max(serie_max_gain, serie_g)
        else:
            serie_p += 1
            serie_g  = 0
            serie_max_perte = max(serie_max_perte, serie_p)

    solde_actuel = data.get("solde", 250.0)
    perf_pct     = round((solde_actuel - 250.0) / 250.0 * 100, 2)

    return {
        "nb_trades":       nb_total,
        "nb_gagnants":     len(gagnants),
        "nb_perdants":     len(perdants),
        "win_rate":        win_rate,
        "pl_total":        pl_total,
        "pl_moyen":        pl_moyen,
        "gain_moyen":      gain_moy,
        "perte_moyenne":   perte_moy,
        "ratio_rr_reel":   ratio_rr,
        "max_drawdown":    round(drawdown_max, 2),
        "sharpe":          sharpe,
        "meilleur_trade":  meilleur,
        "pire_trade":      pire,
        "serie_gagnante":  serie_max_gain,
        "serie_perdante":  serie_max_perte,
        "solde_actuel":    round(solde_actuel, 2),
        "solde_initial":   250.0,
        "performance_pct": perf_pct,
    }

def calculer_perf_mensuelle():
    """Performance par mois"""
    data = _charger()
    historique = data.get("historique", [])
    perf_mois = {}

    for t in historique:
        try:
            date_str = t.get("ferme_le", t.get("ouvert_le", ""))
            if date_str:
                mois = date_str[:7]  # "YYYY-MM" ou "DD/MM/YYYY"
                if "/" in mois:
                    parts = date_str.split(" ")[0].split("/")
                    mois = f"{parts[2]}-{parts[1]}"
                perf_mois[mois] = perf_mois.get(mois, 0) + t["pl"]
        except:
            pass

    return {k: round(v, 2) for k, v in sorted(perf_mois.items())}

# ── Formatage Telegram ─────────────────────────────────────
def formater_performance():
    """Rapport de performance complet pour Telegram"""
    m = calculer_metriques()

    if m["nb_trades"] == 0:
        return (
            "📈 *PERFORMANCE*\n\n"
            "Aucun trade terminé pour l'instant.\n"
            f"💳 Solde: `{m['solde_actuel']:.2f} €`\n\n"
            "Lance `/executer GOLD` ou attends une alerte automatique !"
        )

    emoji_perf = "📈" if m["performance_pct"] >= 0 else "📉"
    emoji_wr   = "✅" if m["win_rate"] >= 50 else "⚠️"
    emoji_sharpe = "🏆" if m["sharpe"] > 1 else "✅" if m["sharpe"] > 0 else "⚠️"

    msg  = "📈 *RAPPORT DE PERFORMANCE*\n"
    msg += "━━━━━━━━━━━━━━━━━━\n\n"

    msg += f"💳 *Capital:* `{m['solde_actuel']:.2f} €`\n"
    msg += f"{emoji_perf} *Performance:* `{m['performance_pct']:+.2f}%`\n"
    msg += f"💰 *P&L total:* `{m['pl_total']:+.2f} €`\n\n"

    msg += f"📊 *STATISTIQUES ({m['nb_trades']} trades)*\n"
    msg += f"{emoji_wr} *Win Rate:* `{m['win_rate']}%` ({m['nb_gagnants']}✅ / {m['nb_perdants']}❌)\n"
    msg += f"💚 *Gain moyen:* `+{m['gain_moyen']:.2f} €`\n"
    msg += f"💔 *Perte moyenne:* `{m['perte_moyenne']:.2f} €`\n"
    msg += f"⚖️ *Ratio R/R réel:* `1:{m['ratio_rr_reel']}`\n\n"

    msg += f"🎯 *QUALITÉ*\n"
    msg += f"{emoji_sharpe} *Sharpe Ratio:* `{m['sharpe']}`\n"
    msg += f"📉 *Max Drawdown:* `{m['max_drawdown']:.2f}%`\n"
    msg += f"🔥 *Meilleure série:* `{m['serie_gagnante']} wins consécutifs`\n"
    msg += f"❄️ *Pire série:* `{m['serie_perdante']} losses consécutifs`\n\n"

    if m["meilleur_trade"]:
        msg += f"🏆 *Meilleur trade:* {m['meilleur_trade'].get('marche','?')} `+{m['meilleur_trade']['pl']:.2f} €`\n"
    if m["pire_trade"]:
        msg += f"💀 *Pire trade:* {m['pire_trade'].get('marche','?')} `{m['pire_trade']['pl']:.2f} €`\n"

    # Performance mensuelle
    perf_mois = calculer_perf_mensuelle()
    if perf_mois:
        msg += f"\n📅 *PAR MOIS*\n"
        for mois, pl in list(perf_mois.items())[-3:]:
            e = "📈" if pl >= 0 else "📉"
            msg += f"{e} {mois}: `{pl:+.2f} €`\n"

    # Évaluation globale
    msg += f"\n━━━━━━━━━━━━━━━━━━\n"
    if m["win_rate"] >= 60 and m["sharpe"] > 1:
        msg += "🏆 *Excellente performance — Stratégie très efficace*"
    elif m["win_rate"] >= 50 and m["pl_total"] > 0:
        msg += "✅ *Bonne performance — Continuer dans cette direction*"
    elif m["win_rate"] >= 40:
        msg += "⚠️ *Performance correcte — Améliorer la sélection des trades*"
    else:
        msg += "🔴 *Performance à améliorer — Revoir la stratégie*"

    return msg

def formater_rapport_mensuel():
    """Rapport mensuel automatique"""
    m    = calculer_metriques()
    mois = datetime.now().strftime("%B %Y")

    msg  = f"📊 *RAPPORT MENSUEL — {mois.upper()}*\n"
    msg += "━━━━━━━━━━━━━━━━━━\n\n"
    msg += f"💳 Solde: `{m['solde_actuel']:.2f} €` (départ: 250 €)\n"
    msg += f"📈 Performance: `{m['performance_pct']:+.2f}%`\n"
    msg += f"🎯 Win Rate: `{m['win_rate']}%`\n"
    msg += f"⚖️ Sharpe: `{m['sharpe']}`\n"
    msg += f"📉 Max DD: `{m['max_drawdown']:.2f}%`\n"
    msg += f"📋 Trades: `{m['nb_trades']}` ({m['nb_gagnants']} gagnants)\n"

    return msg
