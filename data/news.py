# ============================================================
#  ACTUALITÉS EN TEMPS RÉEL — Google News RSS (sans API key)
# ============================================================

import requests
import xml.etree.ElementTree as ET
from datetime import datetime

# Requêtes de recherche par marché
REQUETES_NEWS = {
    "WTI":   ["WTI crude oil price OPEC", "pétrole brut prix", "EIA oil stocks"],
    "GOLD":  ["gold price Fed inflation", "or prix dollar", "gold geopolitical"],
    "CAC40": ["CAC 40 bourse Paris", "BCE taux europe indices", "France économie bourse"],
    "DAX":   ["DAX Frankfurt bourse", "Germany economy ECB", "Allemagne indices"],
}

def _fetch_rss(query):
    """Récupère les titres depuis Google News RSS"""
    url = f"https://news.google.com/rss/search?q={requests.utils.quote(query)}&hl=fr&gl=FR&ceid=FR:fr"
    try:
        resp = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code != 200:
            return []

        root = ET.fromstring(resp.content)
        articles = []
        for item in root.findall(".//item")[:5]:
            titre = item.findtext("title", "").split(" - ")[0].strip()
            date  = item.findtext("pubDate", "")
            if titre:
                articles.append({"titre": titre, "date": date})
        return articles
    except Exception:
        return []

def get_news_marche(nom_marche, nb=4):
    """
    Retourne les dernières actualités pour un marché.
    nb = nombre d'articles max à retourner
    """
    requetes = REQUETES_NEWS.get(nom_marche, [nom_marche])
    articles = []
    vus = set()

    for requete in requetes[:2]:  # max 2 requêtes par marché
        for art in _fetch_rss(requete):
            if art["titre"] not in vus:
                articles.append(art)
                vus.add(art["titre"])
        if len(articles) >= nb:
            break

    return articles[:nb]

def formater_news(articles):
    """Formate les news pour un message Telegram"""
    if not articles:
        return "• Aucune actualité récente disponible"
    lignes = []
    for a in articles:
        lignes.append(f"• {a['titre']}")
    return "\n".join(lignes)
