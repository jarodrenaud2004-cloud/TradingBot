# ============================================================
#  DONNÉES DE PRIX — via yfinance (gratuit, temps réel)
# ============================================================

import yfinance as yf
import pandas as pd

def get_prix_actuel(symbole_yf):
    """Retourne le prix actuel d'un actif"""
    try:
        ticker = yf.Ticker(symbole_yf)
        data = ticker.history(period="1d", interval="1m")
        if data.empty:
            return None
        return round(data["Close"].iloc[-1], 4)
    except Exception as e:
        print(f"Erreur prix {symbole_yf}: {e}")
        return None

def get_historique(symbole_yf, periode="3mo", intervalle="1d"):
    """Retourne l'historique OHLCV"""
    try:
        ticker = yf.Ticker(symbole_yf)
        data = ticker.history(period=periode, interval=intervalle)
        return data
    except Exception as e:
        print(f"Erreur historique {symbole_yf}: {e}")
        return pd.DataFrame()

def get_multi_timeframe(symbole_yf):
    """Retourne les données sur 3 timeframes (Weekly, Daily, H1)"""
    try:
        ticker = yf.Ticker(symbole_yf)
        weekly = ticker.history(period="6mo",  interval="1wk")
        daily  = ticker.history(period="3mo",  interval="1d")
        h4     = ticker.history(period="1mo",  interval="1h")
        return {"weekly": weekly, "daily": daily, "h4": h4}
    except Exception as e:
        print(f"Erreur multi-TF {symbole_yf}: {e}")
        return None
