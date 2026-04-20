# ============================================================
#  RÉGIME DE MARCHÉ — Trending / Ranging / Volatilité
#  ADX, VIX, corrélations inter-marchés, saisonnalité
# ============================================================

import numpy as np
import pandas as pd
from data.prix import get_historique, get_prix_actuel

# ── ADX (Average Directional Index) ──────────────────────
def calculer_adx(hist, periode=14):
    """
    ADX > 25 = marché en tendance forte
    ADX < 20 = marché en range (éviter le trend following)
    """
    if hist is None or len(hist) < periode + 5:
        return None

    high  = hist["High"].values
    low   = hist["Low"].values
    close = hist["Close"].values

    # True Range
    tr_vals = []
    for i in range(1, len(close)):
        tr = max(high[i] - low[i],
                 abs(high[i] - close[i-1]),
                 abs(low[i]  - close[i-1]))
        tr_vals.append(tr)

    # +DM et -DM
    pdm, ndm = [], []
    for i in range(1, len(high)):
        up   = high[i] - high[i-1]
        down = low[i-1] - low[i]
        pdm.append(up   if up > down and up > 0   else 0)
        ndm.append(down if down > up  and down > 0 else 0)

    # Lissage EWM
    def smooth(vals):
        s = pd.Series(vals)
        return s.ewm(span=periode, adjust=False).mean().values

    atr   = smooth(tr_vals)
    pdi14 = 100 * smooth(pdm) / (atr + 1e-10)
    ndi14 = 100 * smooth(ndm) / (atr + 1e-10)

    dx = 100 * abs(pdi14 - ndi14) / (pdi14 + ndi14 + 1e-10)
    adx = pd.Series(dx).ewm(span=periode, adjust=False).mean().values

    return round(adx[-1], 1)

def detecter_regime(hist):
    """
    Détecte le régime de marché.
    Retourne: (regime, adx, description)
    regime = 'TENDANCE_FORTE' | 'TENDANCE' | 'RANGE' | 'INCERTAIN'
    """
    adx = calculer_adx(hist)
    if adx is None:
        return "INCERTAIN", None, "Données insuffisantes"

    if adx >= 35:
        return "TENDANCE_FORTE", adx, f"Tendance très forte (ADX={adx}) → Trend following optimal"
    elif adx >= 25:
        return "TENDANCE", adx, f"Marché en tendance (ADX={adx}) → Trend following conseillé"
    elif adx >= 20:
        return "INCERTAIN", adx, f"Marché incertain (ADX={adx}) → Attendre confirmation"
    else:
        return "RANGE", adx, f"Marché en range (ADX={adx}) → Éviter trend following, préférer S/R"

# ── VIX (Indice de peur) ──────────────────────────────────
def get_vix():
    """
    Récupère le VIX (volatilité implicite SP500).
    VIX < 15 = calme | 15-25 = normal | 25-35 = anxieux | >35 = panique
    """
    try:
        hist = get_historique("^VIX", periode="5d", intervalle="1d")
        if hist is not None and not hist.empty:
            vix = round(hist["Close"].iloc[-1], 1)
            return vix
    except:
        pass
    return None

def interpreter_vix(vix):
    """Interprète la valeur du VIX"""
    if vix is None:
        return "INCONNU", "VIX indisponible"
    if vix < 15:
        return "CALME", f"VIX={vix} — Marché très calme, complaisance élevée ⚠️"
    elif vix < 20:
        return "NORMAL", f"VIX={vix} — Volatilité normale"
    elif vix < 25:
        return "ELEVE", f"VIX={vix} — Volatilité élevée, prudence conseillée"
    elif vix < 35:
        return "ANXIEUX", f"VIX={vix} — Marché anxieux, réduire les positions"
    else:
        return "PANIQUE", f"VIX={vix} — PANIQUE ! Opportunités mais risque extrême"

# ── Corrélations inter-marchés ────────────────────────────
PAIRES_CORRELATION = {
    ("GOLD", "DX-Y.NYB"):  "inverse",   # Or vs Dollar (corrélation inverse)
    ("WTI",  "^GSPC"):     "positive",  # Pétrole vs SP500
    ("GOLD", "^TNX"):      "inverse",   # Or vs taux 10 ans US
}

def analyser_correlations(nom_marche):
    """
    Analyse les corrélations clés pour un marché.
    Ex: Si le Dollar monte → mauvais pour l'Or
    """
    insights = []

    try:
        # Dollar Index
        dollar = get_historique("DX-Y.NYB", periode="1mo", intervalle="1d")
        if dollar is not None and not dollar.empty:
            var_dollar = (dollar["Close"].iloc[-1] - dollar["Close"].iloc[-5]) / dollar["Close"].iloc[-5] * 100

            if nom_marche == "GOLD":
                if var_dollar > 1:
                    insights.append(f"💵 Dollar en hausse (+{var_dollar:.1f}%) → Pression sur l'Or")
                elif var_dollar < -1:
                    insights.append(f"💵 Dollar en baisse ({var_dollar:.1f}%) → Favorable à l'Or")

            if nom_marche == "WTI":
                if var_dollar > 1:
                    insights.append(f"💵 Dollar fort → Pétrole plus cher pour pays étrangers (baissier)")
                elif var_dollar < -1:
                    insights.append(f"💵 Dollar faible → Soutien pour le Pétrole")
    except:
        pass

    try:
        # Taux 10 ans US
        taux = get_historique("^TNX", periode="1mo", intervalle="1d")
        if taux is not None and not taux.empty:
            var_taux = taux["Close"].iloc[-1] - taux["Close"].iloc[-5]

            if nom_marche == "GOLD":
                if var_taux > 0.1:
                    insights.append(f"📈 Taux 10Y en hausse ({var_taux:+.2f}%) → Mauvais pour l'Or")
                elif var_taux < -0.1:
                    insights.append(f"📉 Taux 10Y en baisse ({var_taux:+.2f}%) → Favorable à l'Or")

            if nom_marche in ["CAC40", "DAX"]:
                if var_taux > 0.2:
                    insights.append(f"📈 Taux US en forte hausse → Pression sur indices EU")
    except:
        pass

    try:
        # SP500 pour les actions EU
        if nom_marche in ["CAC40", "DAX", "TTE", "MC", "AIR", "BNP", "SAN", "OR"]:
            sp500 = get_historique("^GSPC", periode="5d", intervalle="1d")
            if sp500 is not None and not sp500.empty:
                var_sp = (sp500["Close"].iloc[-1] - sp500["Close"].iloc[-2]) / sp500["Close"].iloc[-2] * 100
                if var_sp > 1:
                    insights.append(f"🇺🇸 SP500 en hausse (+{var_sp:.1f}%) → Favorable aux actions EU")
                elif var_sp < -1:
                    insights.append(f"🇺🇸 SP500 en baisse ({var_sp:.1f}%) → Défavorable aux actions EU")
    except:
        pass

    return insights

# ── Saisonnalité ──────────────────────────────────────────
SAISONNALITE = {
    1:  {"WTI": "Demande hivernale soutenue", "GOLD": "Demande bijouterie Asie"},
    3:  {"CAC40": "Fin trimestre — réallocation de portefeuilles"},
    4:  {"WTI": "Début saison conduite US — hausse demande"},
    5:  {"CAC40": "Sell in May and Go Away — historiquement faible", "DAX": "Sell in May"},
    6:  {"WTI": "Pic saison conduite US"},
    9:  {"CAC40": "Septembre historiquement mauvais pour les actions"},
    10: {"GOLD": "Diwali — forte demande d'or en Inde"},
    11: {"WTI": "Baisse demande après saison conduite"},
    12: {"CAC40": "Rallye de Noël possible", "DAX": "Rallye de Noël"},
}

def get_saisonnalite(nom_marche):
    """Retourne le commentaire de saisonnalité pour le mois en cours"""
    from datetime import datetime
    mois = datetime.now().month
    commentaire = SAISONNALITE.get(mois, {}).get(nom_marche)
    if commentaire:
        return f"📅 Saisonnalité {datetime.now().strftime('%B')}: {commentaire}"
    return None

# ── Analyse complète du régime ────────────────────────────
def analyser_regime_complet(nom_marche, hist):
    """
    Analyse complète : régime ADX + VIX + corrélations + saisonnalité
    Retourne un score d'ajustement et un résumé
    """
    score_ajust = 0
    infos = []

    # 1. Régime ADX
    regime, adx, desc_regime = detecter_regime(hist)
    infos.append(f"📊 Régime: {desc_regime}")
    if regime == "RANGE":
        score_ajust -= 1  # Moins fiable en range

    # 2. VIX
    vix = get_vix()
    type_vix, desc_vix = interpreter_vix(vix)
    infos.append(f"😰 {desc_vix}")
    if type_vix in ["ANXIEUX", "PANIQUE"]:
        score_ajust -= 1  # Réduire exposition en période de panique

    # 3. Corrélations
    correlations = analyser_correlations(nom_marche)
    infos.extend(correlations)

    # 4. Saisonnalité
    saison = get_saisonnalite(nom_marche)
    if saison:
        infos.append(saison)

    return score_ajust, infos, regime, vix

def formater_regime(infos, regime, vix):
    """Formate le régime pour un message Telegram"""
    if not infos:
        return ""
    msg = "🌡️ *CONTEXTE DE MARCHÉ*\n"
    for info in infos:
        msg += f"• {info}\n"
    return msg
