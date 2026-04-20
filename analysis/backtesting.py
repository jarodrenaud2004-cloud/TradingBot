# ============================================================
#  BACKTESTING — Test de la stratégie sur l'historique
#  Simule les signaux sur 1 an de données
#  Calcule: win rate, profit factor, max drawdown, Sharpe
# ============================================================

import numpy as np
from datetime import datetime
from data.prix import get_historique
from config import MARCHES

# Paramètres de simulation
RISQUE_PAR_TRADE_PCT  = 1.0   # 1% du capital par trade
CAPITAL_INITIAL       = 250.0
SL_PCT_DEFAULT        = 1.5   # Stop loss 1.5% si pas d'autre niveau
TP_RATIO_DEFAULT      = 2.0   # Take profit = 2x le stop loss


# ── Indicateurs rapides pour le backtest ──────────────────

def _rsi(closes, period=14):
    """RSI simple pour le backtest"""
    if len(closes) < period + 1:
        return 50
    deltas = np.diff(closes)
    gains  = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_g  = np.mean(gains[-period:])
    avg_l  = np.mean(losses[-period:])
    if avg_l == 0:
        return 100
    rs  = avg_g / avg_l
    return 100 - (100 / (1 + rs))


def _ema(values, period):
    """EMA simple"""
    if len(values) < period:
        return values[-1] if len(values) > 0 else 0
    k = 2 / (period + 1)
    ema = values[0]
    for v in values[1:]:
        ema = v * k + ema * (1 - k)
    return ema


def _signal_score(closes, highs, lows, volumes, idx):
    """
    Score rapide pour le backtest (simplifié pour la vitesse).
    Utilise RSI + EMA50/200 + volume.
    Retourne: (score, direction)
    """
    if idx < 50:
        return 0, "NEUTRE"

    close_slice = closes[max(0, idx-200):idx+1]
    score = 0

    # ── Tendance EMA50 vs EMA200 ──
    ema50  = _ema(close_slice[-50:],  50)
    ema200 = _ema(close_slice[-200:], 200) if len(close_slice) >= 200 else _ema(close_slice, len(close_slice))

    if ema50 > ema200 * 1.001:
        score += 2   # Tendance haussière
    elif ema50 < ema200 * 0.999:
        score -= 2   # Tendance baissière

    # ── RSI ──
    rsi_val = _rsi(close_slice[-20:])
    if rsi_val < 35:
        score += 1   # Survendu → BUY
    elif rsi_val > 65:
        score -= 1   # Suracheté → SELL
    elif rsi_val < 45:
        score += 0.5
    elif rsi_val > 55:
        score -= 0.5

    # ── MACD rapide ──
    ema12 = _ema(close_slice[-12:], 12)
    ema26 = _ema(close_slice[-26:], 26) if len(close_slice) >= 26 else close_slice[-1]
    macd  = ema12 - ema26
    signal_line = _ema(close_slice[-9:], 9)
    if macd > signal_line and macd > 0:
        score += 1
    elif macd < signal_line and macd < 0:
        score -= 1

    # ── Volume ──
    if idx >= 20:
        vol_slice = volumes[max(0, idx-20):idx+1]
        vol_moy   = np.mean(vol_slice[:-1]) if len(vol_slice) > 1 else vol_slice[-1]
        if vol_moy > 0 and volumes[idx] > vol_moy * 1.5:
            score = score * 1.2  # Confirmation volume

    # Direction
    if score >= 2:
        return score, "BUY"
    elif score <= -2:
        return score, "SELL"
    return score, "NEUTRE"


# ── Moteur de backtesting ──────────────────────────────────

def backtest_strategie(nom_marche, periode="1y", capital=CAPITAL_INITIAL):
    """
    Backteste la stratégie sur l'historique.

    Logique:
    - Scan chaque bougie
    - Si signal (score >= 2) → simuler un trade
    - SL = 1.5%, TP = 3% (ratio 2:1)
    - Max 1 trade à la fois
    - Calcule toutes les métriques

    Retourne dict avec toutes les statistiques.
    """
    info = MARCHES.get(nom_marche)
    if not info:
        return None

    hist = get_historique(info["symbole_yf"], periode=periode, intervalle="1d")
    if hist is None or len(hist) < 60:
        return None

    closes  = hist["Close"].values
    highs   = hist["High"].values
    lows    = hist["Low"].values
    volumes = hist["Volume"].values if "Volume" in hist.columns else np.ones(len(closes))
    dates   = hist.index.tolist()

    # ── Variables de simulation ────────────────────────────
    capital_courant = capital
    trades          = []
    equity_curve    = [capital]
    position        = None   # {"direction", "entree", "sl", "tp", "idx_entree"}
    nb_jours_trade  = 0

    for i in range(50, len(closes) - 1):  # Start à 50 pour avoir assez d'historique
        prix = closes[i]

        # ── Gérer la position ouverte ──────────────────────
        if position:
            nb_jours_trade += 1
            prix_suivant = closes[i + 1]

            # Vérifier SL/TP
            if position["direction"] == "BUY":
                if lows[i + 1] <= position["sl"]:
                    # SL touché
                    pct_variation = (position["sl"] - position["entree"]) / position["entree"]
                    pl = capital_courant * RISQUE_PAR_TRADE_PCT / 100 * pct_variation / (
                        abs(position["entree"] - position["sl"]) / position["entree"]
                    )
                    pl = -capital_courant * RISQUE_PAR_TRADE_PCT / 100

                    capital_courant += pl
                    trades.append({
                        "direction": "BUY",
                        "entree":    position["entree"],
                        "sortie":    position["sl"],
                        "pl_pct":    pct_variation * 100,
                        "pl":        pl,
                        "resultat":  "SL",
                        "duree":     nb_jours_trade,
                        "date":      str(dates[i + 1])[:10],
                    })
                    position = None
                    nb_jours_trade = 0

                elif highs[i + 1] >= position["tp"]:
                    # TP touché
                    pct_variation = (position["tp"] - position["entree"]) / position["entree"]
                    pl = capital_courant * RISQUE_PAR_TRADE_PCT / 100 * TP_RATIO_DEFAULT

                    capital_courant += pl
                    trades.append({
                        "direction": "BUY",
                        "entree":    position["entree"],
                        "sortie":    position["tp"],
                        "pl_pct":    pct_variation * 100,
                        "pl":        pl,
                        "resultat":  "TP",
                        "duree":     nb_jours_trade,
                        "date":      str(dates[i + 1])[:10],
                    })
                    position = None
                    nb_jours_trade = 0

                # Timeout 15 jours
                elif nb_jours_trade >= 15:
                    pct_variation = (prix - position["entree"]) / position["entree"]
                    pl = capital_courant * RISQUE_PAR_TRADE_PCT / 100 * (pct_variation / abs(
                        position["entree"] - position["sl"]) * position["entree"])
                    pl = max(-capital_courant * RISQUE_PAR_TRADE_PCT / 100,
                             min(capital_courant * RISQUE_PAR_TRADE_PCT * TP_RATIO_DEFAULT / 100, pl))

                    capital_courant += pl
                    trades.append({
                        "direction": "BUY",
                        "entree":    position["entree"],
                        "sortie":    prix,
                        "pl_pct":    pct_variation * 100,
                        "pl":        pl,
                        "resultat":  "TIMEOUT",
                        "duree":     nb_jours_trade,
                        "date":      str(dates[i])[:10],
                    })
                    position = None
                    nb_jours_trade = 0

            elif position["direction"] == "SELL":
                if highs[i + 1] >= position["sl"]:
                    pl = -capital_courant * RISQUE_PAR_TRADE_PCT / 100
                    pct_variation = (position["sl"] - position["entree"]) / position["entree"]

                    capital_courant += pl
                    trades.append({
                        "direction": "SELL",
                        "entree":    position["entree"],
                        "sortie":    position["sl"],
                        "pl_pct":    pct_variation * 100,
                        "pl":        pl,
                        "resultat":  "SL",
                        "duree":     nb_jours_trade,
                        "date":      str(dates[i + 1])[:10],
                    })
                    position = None
                    nb_jours_trade = 0

                elif lows[i + 1] <= position["tp"]:
                    pl = capital_courant * RISQUE_PAR_TRADE_PCT / 100 * TP_RATIO_DEFAULT
                    pct_variation = (position["entree"] - position["tp"]) / position["entree"]

                    capital_courant += pl
                    trades.append({
                        "direction": "SELL",
                        "entree":    position["entree"],
                        "sortie":    position["tp"],
                        "pl_pct":    pct_variation * 100,
                        "pl":        pl,
                        "resultat":  "TP",
                        "duree":     nb_jours_trade,
                        "date":      str(dates[i + 1])[:10],
                    })
                    position = None
                    nb_jours_trade = 0

                elif nb_jours_trade >= 15:
                    pct_variation = (position["entree"] - prix) / position["entree"]
                    pl = max(-capital_courant * RISQUE_PAR_TRADE_PCT / 100,
                             min(capital_courant * RISQUE_PAR_TRADE_PCT * TP_RATIO_DEFAULT / 100,
                                 capital_courant * RISQUE_PAR_TRADE_PCT / 100 * (pct_variation / SL_PCT_DEFAULT * 100)))

                    capital_courant += pl
                    trades.append({
                        "direction": "SELL",
                        "entree":    position["entree"],
                        "sortie":    prix,
                        "pl_pct":    pct_variation * 100,
                        "pl":        pl,
                        "resultat":  "TIMEOUT",
                        "duree":     nb_jours_trade,
                        "date":      str(dates[i])[:10],
                    })
                    position = None
                    nb_jours_trade = 0

        # ── Chercher un nouveau signal ─────────────────────
        if position is None:
            score, direction = _signal_score(closes, highs, lows, volumes, i)

            if direction != "NEUTRE":
                entree = closes[i + 1]  # On entre à l'ouverture de la prochaine bougie

                if direction == "BUY":
                    sl = entree * (1 - SL_PCT_DEFAULT / 100)
                    tp = entree * (1 + SL_PCT_DEFAULT * TP_RATIO_DEFAULT / 100)
                else:
                    sl = entree * (1 + SL_PCT_DEFAULT / 100)
                    tp = entree * (1 - SL_PCT_DEFAULT * TP_RATIO_DEFAULT / 100)

                position = {
                    "direction": direction,
                    "entree":    entree,
                    "sl":        sl,
                    "tp":        tp,
                    "idx_entree": i,
                }

        equity_curve.append(capital_courant)

    # ── Calcul des métriques ───────────────────────────────
    if not trades:
        return {
            "marche":      info["nom"],
            "symbole":     nom_marche,
            "periode":     periode,
            "nb_trades":   0,
            "message":     "Aucun trade généré sur cette période."
        }

    profits  = [t["pl"] for t in trades if t["pl"] > 0]
    pertes   = [t["pl"] for t in trades if t["pl"] < 0]
    tp_count = len([t for t in trades if t["resultat"] == "TP"])
    sl_count = len([t for t in trades if t["resultat"] == "SL"])

    win_rate = tp_count / len(trades) * 100 if trades else 0

    profit_factor = (
        sum(profits) / abs(sum(pertes))
        if pertes and sum(pertes) != 0
        else float("inf")
    )

    pl_total   = sum(t["pl"] for t in trades)
    pl_total_pct = (capital_courant - capital) / capital * 100

    meilleur_trade = max(trades, key=lambda x: x["pl"]) if trades else None
    pire_trade     = min(trades, key=lambda x: x["pl"]) if trades else None

    # Max drawdown
    max_drawdown = 0
    pic = equity_curve[0]
    for v in equity_curve:
        if v > pic:
            pic = v
        dd = (pic - v) / pic * 100
        if dd > max_drawdown:
            max_drawdown = dd

    # Durée moyenne des trades
    duree_moy = np.mean([t["duree"] for t in trades]) if trades else 0

    # Sharpe (approximé sur rendements journaliers de l'equity)
    returns = np.diff(equity_curve) / equity_curve[:-1] if len(equity_curve) > 1 else [0]
    sharpe  = (np.mean(returns) / np.std(returns) * np.sqrt(252)) if np.std(returns) > 0 else 0

    # Série de gains/pertes consécutifs
    serie_courante = 1
    serie_max_gains  = 0
    serie_max_pertes = 0
    for j in range(1, len(trades)):
        if trades[j]["pl"] > 0 and trades[j-1]["pl"] > 0:
            serie_courante += 1
            serie_max_gains = max(serie_max_gains, serie_courante)
        elif trades[j]["pl"] < 0 and trades[j-1]["pl"] < 0:
            serie_courante += 1
            serie_max_pertes = max(serie_max_pertes, serie_courante)
        else:
            serie_courante = 1

    return {
        "marche":          info["nom"],
        "symbole":         nom_marche,
        "periode":         periode,
        "nb_trades":       len(trades),
        "nb_tp":           tp_count,
        "nb_sl":           sl_count,
        "nb_timeout":      len(trades) - tp_count - sl_count,
        "win_rate":        round(win_rate, 1),
        "profit_factor":   round(profit_factor, 2),
        "pl_total":        round(pl_total, 2),
        "pl_total_pct":    round(pl_total_pct, 1),
        "capital_final":   round(capital_courant, 2),
        "max_drawdown":    round(max_drawdown, 1),
        "sharpe":          round(sharpe, 2),
        "duree_moy":       round(duree_moy, 1),
        "meilleur_trade":  meilleur_trade,
        "pire_trade":      pire_trade,
        "serie_max_gains": serie_max_gains,
        "serie_max_pertes": serie_max_pertes,
        "trades":          trades[-10:],  # 10 derniers trades
    }


def formater_backtest(res):
    """Formate les résultats du backtest pour Telegram"""
    if not res:
        return "❌ Impossible de lancer le backtest."

    if res.get("nb_trades", 0) == 0:
        return (
            f"📊 *BACKTEST — {res['marche']}*\n\n"
            f"⚪ Aucun signal généré sur la période {res['periode']}.\n"
            "Le marché était peut-être en range."
        )

    # Verdict global
    if res["win_rate"] >= 55 and res["profit_factor"] >= 1.5 and res["pl_total_pct"] > 0:
        verdict = "✅ *Stratégie RENTABLE*"
        emoji   = "🟢"
    elif res["win_rate"] >= 45 and res["profit_factor"] >= 1.0:
        verdict = "⚠️ *Stratégie CORRECTE*"
        emoji   = "🟡"
    else:
        verdict = "❌ *Stratégie à AMÉLIORER*"
        emoji   = "🔴"

    msg  = f"📊 *BACKTEST — {res['marche']}*\n"
    msg += f"_{res['periode']} de données — {res['nb_trades']} trades simulés_\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━\n\n"

    # Verdict
    msg += f"{verdict}\n\n"

    # Résultats principaux
    pl_emoji = "📈" if res["pl_total_pct"] >= 0 else "📉"
    msg += f"💰 *Résultat: `{res['pl_total_pct']:+.1f}%`* ({res['capital_final']:.2f}€ → depuis {CAPITAL_INITIAL:.0f}€)\n"
    msg += f"{pl_emoji} P&L total: `{res['pl_total']:+.2f} €`\n\n"

    # Statistiques
    msg += f"📈 *STATISTIQUES*\n"
    msg += f"• Win Rate:       `{res['win_rate']:.1f}%` ({res['nb_tp']} TP / {res['nb_sl']} SL)\n"
    msg += f"• Profit Factor:  `{res['profit_factor']:.2f}`\n"
    msg += f"• Sharpe Ratio:   `{res['sharpe']:.2f}`\n"
    msg += f"• Max Drawdown:   `{res['max_drawdown']:.1f}%`\n"
    msg += f"• Durée moy:      `{res['duree_moy']:.0f} jours/trade`\n\n"

    # Séries
    msg += f"🔢 *SÉRIES*\n"
    msg += f"• Max gains consécutifs: `{res['serie_max_gains']}`\n"
    msg += f"• Max pertes consécutives: `{res['serie_max_pertes']}`\n\n"

    # Meilleur/pire trade
    if res["meilleur_trade"]:
        mt = res["meilleur_trade"]
        msg += f"🏆 Meilleur trade: `+{mt['pl']:.2f}€` ({mt['direction']} le {mt['date']})\n"
    if res["pire_trade"]:
        pt = res["pire_trade"]
        msg += f"💀 Pire trade:    `{pt['pl']:+.2f}€` ({pt['direction']} le {pt['date']})\n"
    msg += "\n"

    # Interprétation
    msg += f"💡 *INTERPRÉTATION*\n"
    if res["win_rate"] >= 55:
        msg += "✅ Plus de 55% de trades gagnants — stratégie fiable\n"
    elif res["win_rate"] >= 45:
        msg += "⚠️ Win rate moyen — le ratio R/R compense\n"
    else:
        msg += "❌ Win rate faible — attendre signaux plus forts\n"

    if res["profit_factor"] >= 2.0:
        msg += "✅ Profit Factor >2 — excellent\n"
    elif res["profit_factor"] >= 1.5:
        msg += "✅ Profit Factor >1.5 — bon\n"
    elif res["profit_factor"] >= 1.0:
        msg += "⚠️ Profit Factor borderline\n"
    else:
        msg += "❌ Profit Factor <1 — stratégie perdante\n"

    if res["max_drawdown"] < 10:
        msg += "✅ Drawdown maîtrisé (<10%)\n"
    elif res["max_drawdown"] < 20:
        msg += "⚠️ Drawdown significatif ({:.0f}%)\n".format(res["max_drawdown"])
    else:
        msg += "❌ Drawdown élevé — revoir le risk management\n"

    msg += "\n⚠️ _Backtest ≠ performance future. Passé ≠ futur._"

    return msg


def backtest_tous_marches(periode="1y"):
    """Backteste tous les marchés prioritaires"""
    from data.alertes_intelligentes import MARCHES_PRIORITAIRES
    resultats = []
    for nom in MARCHES_PRIORITAIRES:
        try:
            res = backtest_strategie(nom, periode=periode)
            if res and res.get("nb_trades", 0) > 0:
                resultats.append(res)
        except Exception as e:
            print(f"Erreur backtest {nom}: {e}")

    # Trier par rentabilité
    resultats.sort(key=lambda x: x["pl_total_pct"], reverse=True)
    return resultats


def formater_synthese_backtests(resultats):
    """Synthèse courte de tous les backtests"""
    if not resultats:
        return "❌ Aucun résultat de backtest disponible."

    msg  = "📊 *SYNTHÈSE BACKTESTS*\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━\n\n"

    for r in resultats:
        emoji = "🟢" if r["pl_total_pct"] > 0 else "🔴"
        msg += f"{emoji} *{r['symbole']}* — `{r['pl_total_pct']:+.1f}%` | "
        msg += f"WR: `{r['win_rate']:.0f}%` | DD: `{r['max_drawdown']:.0f}%`\n"

    msg += f"\n_Pour le détail: /backtest WTI_"
    return msg
