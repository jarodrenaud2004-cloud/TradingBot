# ============================================================
#  ANALYSE DE SENTIMENT — News + Fear & Greed
#  Mesure le sentiment du marché en temps réel
# ============================================================

import requests
import xml.etree.ElementTree as ET

# Mots positifs / négatifs pour analyse de sentiment
MOTS_POSITIFS = [
    "hausse", "monte", "rebond", "rally", "bull", "haussier", "record",
    "gains", "progression", "optimisme", "reprise", "croissance", "surpasse",
    "rise", "gain", "surge", "soar", "jump", "up", "high", "strong", "boost",
    "recovery", "growth", "positive", "beat", "exceed"
]

MOTS_NEGATIFS = [
    "baisse", "chute", "recul", "bear", "baissier", "panique", "crash",
    "perte", "pessimisme", "recession", "inquiet", "risque", "effondrement",
    "fall", "drop", "decline", "plunge", "sink", "low", "weak", "sell",
    "loss", "fear", "crisis", "warning", "cut", "miss"
]

MOTS_CLES_MARCHES = {
    "WTI":   ["oil", "crude", "petroleum", "OPEC", "pétrole", "barrel", "energy"],
    "GOLD":  ["gold", "or", "metal", "safe haven", "haven", "precious"],
    "CAC40": ["CAC", "France", "Paris", "indice", "index", "Europe", "EU"],
    "DAX":   ["DAX", "Germany", "Frankfurt", "Allemagne", "Europe"],
    "SILVER":["silver", "argent", "metal"],
    "CORN":  ["corn", "maïs", "grain", "agriculture", "USDA"],
    "WHEAT": ["wheat", "blé", "grain", "agriculture"],
}


def analyser_sentiment_texte(texte):
    """Analyse le sentiment d'un texte (positif/négatif/neutre)"""
    texte_lower = texte.lower()
    score_pos = sum(1 for m in MOTS_POSITIFS if m in texte_lower)
    score_neg = sum(1 for m in MOTS_NEGATIFS if m in texte_lower)
    score = score_pos - score_neg

    if score >= 2:
        return "POSITIF", score
    elif score <= -2:
        return "NEGATIF", score
    elif score > 0:
        return "LÉGÈREMENT_POSITIF", score
    elif score < 0:
        return "LÉGÈREMENT_NÉGATIF", score
    return "NEUTRE", 0


def get_sentiment_marche(nom_marche, nb_articles=8):
    """
    Analyse le sentiment global des news pour un marché.
    Retourne: (sentiment, score, details)
    """
    mots_cles = MOTS_CLES_MARCHES.get(nom_marche, [nom_marche])
    query     = " OR ".join(mots_cles[:3])

    url = f"https://news.google.com/rss/search?q={requests.utils.quote(query)}&hl=fr&gl=FR&ceid=FR:fr"

    articles = []
    try:
        resp = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code == 200:
            root = ET.fromstring(resp.content)
            for item in root.findall(".//item")[:nb_articles]:
                titre = item.findtext("title", "").split(" - ")[0].strip()
                desc  = item.findtext("description", "")
                if titre:
                    articles.append(titre + " " + desc)
    except:
        return "NEUTRE", 0, []

    if not articles:
        return "NEUTRE", 0, []

    # Analyser chaque article
    sentiments = []
    score_total = 0
    for art in articles:
        sent, score = analyser_sentiment_texte(art)
        sentiments.append((art[:80], sent, score))
        score_total += score

    # Sentiment global
    score_moy = score_total / len(articles)
    if score_moy >= 1.5:
        sentiment_global = "TRÈS_POSITIF"
    elif score_moy >= 0.5:
        sentiment_global = "POSITIF"
    elif score_moy <= -1.5:
        sentiment_global = "TRÈS_NÉGATIF"
    elif score_moy <= -0.5:
        sentiment_global = "NÉGATIF"
    else:
        sentiment_global = "NEUTRE"

    return sentiment_global, round(score_moy, 2), sentiments


def get_fear_greed_index():
    """
    Approximation du Fear & Greed Index basée sur:
    - VIX (volatilité)
    - Momentum marché
    - Sentiment news SP500
    Retourne: (score 0-100, label)
    """
    try:
        from data.prix import get_historique

        score = 50  # Neutre par défaut

        # VIX
        hist_vix = get_historique("^VIX", periode="1mo", intervalle="1d")
        if hist_vix is not None and not hist_vix.empty:
            vix = hist_vix["Close"].iloc[-1]
            vix_moy = hist_vix["Close"].mean()
            if vix < vix_moy * 0.8:
                score += 15  # VIX bas = greed
            elif vix > vix_moy * 1.3:
                score -= 20  # VIX haut = fear

        # Momentum SP500 (52 semaines)
        hist_sp = get_historique("^GSPC", periode="1y", intervalle="1wk")
        if hist_sp is not None and len(hist_sp) >= 4:
            prix_52s = hist_sp["Close"].iloc[0]
            prix_act  = hist_sp["Close"].iloc[-1]
            momentum  = (prix_act - prix_52s) / prix_52s * 100
            if momentum > 20:
                score += 15
            elif momentum > 10:
                score += 7
            elif momentum < -10:
                score -= 15
            elif momentum < -5:
                score -= 7

        # Sentiment news marché US
        sent, sent_score, _ = get_sentiment_marche("CAC40", nb_articles=5)
        if sent in ["TRÈS_POSITIF", "POSITIF"]:
            score += 10
        elif sent in ["TRÈS_NÉGATIF", "NÉGATIF"]:
            score -= 10

        # Clamp 0-100
        score = max(0, min(100, score))

        # Label
        if score >= 75:
            label = "GREED EXTRÊME 🤑"
        elif score >= 55:
            label = "GREED 😊"
        elif score >= 45:
            label = "NEUTRE 😐"
        elif score >= 25:
            label = "FEAR 😨"
        else:
            label = "FEAR EXTRÊME 😱"

        return score, label

    except Exception as e:
        return 50, "NEUTRE 😐"


def score_sentiment_pour_trade(nom_marche, direction):
    """
    Retourne un score d'ajustement basé sur le sentiment.
    Si sentiment positif et direction BUY → +1
    Si sentiment négatif et direction SELL → +1
    etc.
    """
    sentiment, score_sent, _ = get_sentiment_marche(nom_marche, nb_articles=6)

    sentiment_haussier = sentiment in ["TRÈS_POSITIF", "POSITIF"]
    sentiment_baissier = sentiment in ["TRÈS_NÉGATIF", "NÉGATIF"]

    if direction == "BUY" and sentiment_haussier:
        return 1, f"Sentiment positif confirme le BUY"
    elif direction == "SELL" and sentiment_baissier:
        return 1, f"Sentiment négatif confirme le SELL"
    elif direction == "BUY" and sentiment_baissier:
        return -1, f"⚠️ Sentiment négatif contre le BUY"
    elif direction == "SELL" and sentiment_haussier:
        return -1, f"⚠️ Sentiment positif contre le SELL"

    return 0, f"Sentiment neutre"


def formater_sentiment(nom_marche):
    """Formate le sentiment pour un message Telegram"""
    sentiment, score, articles = get_sentiment_marche(nom_marche)
    fg_score, fg_label = get_fear_greed_index()

    emojis = {
        "TRÈS_POSITIF":        "🟢🟢",
        "POSITIF":             "🟢",
        "LÉGÈREMENT_POSITIF":  "🟡",
        "NEUTRE":              "⚪",
        "LÉGÈREMENT_NÉGATIF":  "🟠",
        "NÉGATIF":             "🔴",
        "TRÈS_NÉGATIF":        "🔴🔴",
    }
    emoji = emojis.get(sentiment, "⚪")

    msg  = f"🧠 *SENTIMENT DE MARCHÉ*\n"
    msg += f"{emoji} Sentiment {nom_marche}: *{sentiment.replace('_', ' ')}* (score: {score:+.1f})\n"
    msg += f"😰 Fear & Greed: `{fg_score}/100` — {fg_label}\n"

    return msg
