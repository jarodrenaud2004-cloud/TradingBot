# ============================================================
#  INDICATEURS TECHNIQUES AVANCÉS
#  RSI divergences, MACD, Bollinger Bands, Fibonacci, Volume
# ============================================================

import pandas as pd
import numpy as np

# ── RSI ──────────────────────────────────────────────────────
def calculer_rsi(closes, periode=14):
    delta  = pd.Series(closes).diff()
    gains  = delta.clip(lower=0)
    pertes = (-delta.clip(upper=0))
    avg_g  = gains.ewm(com=periode-1, min_periods=periode).mean()
    avg_p  = pertes.ewm(com=periode-1, min_periods=periode).mean()
    rs     = avg_g / avg_p.replace(0, 1e-10)
    return 100 - (100 / (1 + rs))

def analyser_rsi(hist):
    """RSI + détection de divergences"""
    if hist is None or len(hist) < 20:
        return 0, "RSI indisponible"

    closes = hist["Close"].values
    rsi    = calculer_rsi(closes)
    rsi_vals = rsi.values
    rsi_actuel = round(rsi_vals[-1], 1)

    score    = 0
    messages = []

    # Zones extrêmes
    if rsi_actuel < 30:
        score += 2
        messages.append(f"RSI survendu ({rsi_actuel}) → Signal HAUSSIER fort")
    elif rsi_actuel < 40:
        score += 1
        messages.append(f"RSI bas ({rsi_actuel}) → Zone d'achat")
    elif rsi_actuel > 70:
        score -= 2
        messages.append(f"RSI suracheté ({rsi_actuel}) → Signal BAISSIER fort")
    elif rsi_actuel > 60:
        score -= 1
        messages.append(f"RSI élevé ({rsi_actuel}) → Zone de vente")
    else:
        messages.append(f"RSI neutre ({rsi_actuel})")

    # Divergences (sur les 10 dernières bougies)
    if len(closes) >= 15:
        prix_recent   = closes[-10:]
        rsi_recent    = rsi_vals[-10:]

        idx_min_prix  = np.argmin(prix_recent)
        idx_min_rsi   = np.argmin(rsi_recent)
        idx_max_prix  = np.argmax(prix_recent)
        idx_max_rsi   = np.argmax(rsi_recent)

        # Divergence haussière : prix fait un plus bas, RSI fait un plus haut
        if (prix_recent[-1] < prix_recent[0] and rsi_recent[-1] > rsi_recent[0] and
                rsi_recent[-1] < 50):
            score += 2
            messages.append("📈 Divergence haussière RSI → Retournement probable à la hausse")

        # Divergence baissière : prix fait un plus haut, RSI fait un plus bas
        if (prix_recent[-1] > prix_recent[0] and rsi_recent[-1] < rsi_recent[0] and
                rsi_recent[-1] > 50):
            score -= 2
            messages.append("📉 Divergence baissière RSI → Retournement probable à la baisse")

    return score, " | ".join(messages)


# ── MACD ─────────────────────────────────────────────────────
def calculer_macd(closes, rapide=12, lent=26, signal=9):
    s = pd.Series(closes)
    ema_r = s.ewm(span=rapide, adjust=False).mean()
    ema_l = s.ewm(span=lent,   adjust=False).mean()
    macd  = ema_r - ema_l
    sig   = macd.ewm(span=signal, adjust=False).mean()
    hist  = macd - sig
    return macd.values, sig.values, hist.values

def analyser_macd(hist):
    """MACD : croisements + divergences + histogramme"""
    if hist is None or len(hist) < 30:
        return 0, "MACD indisponible"

    closes = hist["Close"].values
    macd, signal, histogramme = calculer_macd(closes)

    score    = 0
    messages = []

    # Croisement récent (2 dernières bougies)
    if len(macd) >= 2:
        # Croisement haussier : MACD passe au-dessus du signal
        if macd[-2] < signal[-2] and macd[-1] > signal[-1]:
            score += 2
            messages.append("✅ MACD croisement haussier → Signal ACHAT")
        # Croisement baissier
        elif macd[-2] > signal[-2] and macd[-1] < signal[-1]:
            score -= 2
            messages.append("❌ MACD croisement baissier → Signal VENTE")
        # Position actuelle
        elif macd[-1] > signal[-1]:
            score += 1
            messages.append(f"MACD au-dessus du signal (momentum haussier)")
        else:
            score -= 1
            messages.append(f"MACD sous le signal (momentum baissier)")

    # Histogramme : accélération/décélération
    if len(histogramme) >= 3:
        if histogramme[-1] > histogramme[-2] > histogramme[-3] and histogramme[-1] > 0:
            score += 1
            messages.append("Histogramme MACD en accélération haussière")
        elif histogramme[-1] < histogramme[-2] < histogramme[-3] and histogramme[-1] < 0:
            score -= 1
            messages.append("Histogramme MACD en accélération baissière")

    return score, " | ".join(messages)


# ── BANDES DE BOLLINGER ───────────────────────────────────────
def analyser_bollinger(hist, periode=20, ecart=2):
    """Bollinger Bands : squeeze, rebond, cassure"""
    if hist is None or len(hist) < periode + 5:
        return 0, "Bollinger indisponible"

    closes = hist["Close"].values
    s      = pd.Series(closes)
    moy    = s.rolling(periode).mean()
    std    = s.rolling(periode).std()
    upper  = moy + ecart * std
    lower  = moy - ecart * std

    prix    = closes[-1]
    u       = upper.values[-1]
    l       = lower.values[-1]
    m       = moy.values[-1]
    largeur = (u - l) / m * 100  # largeur des bandes en %

    score    = 0
    messages = []

    # Squeeze (bandes très serrées = explosion imminente)
    largeur_moy = ((upper - lower) / moy * 100).rolling(20).mean().values[-1]
    if largeur < largeur_moy * 0.7:
        messages.append(f"🔥 Bollinger Squeeze ({largeur:.1f}%) → Explosion imminente")

    # Prix au contact des bandes
    if prix <= l * 1.005:
        score += 2
        messages.append(f"Prix sur bande basse Bollinger → Rebond haussier probable")
    elif prix >= u * 0.995:
        score -= 2
        messages.append(f"Prix sur bande haute Bollinger → Retournement baissier probable")
    elif prix > m:
        score += 1
        messages.append(f"Prix au-dessus de la moyenne Bollinger")
    else:
        score -= 1
        messages.append(f"Prix sous la moyenne Bollinger")

    return score, " | ".join(messages)


# ── FIBONACCI ─────────────────────────────────────────────────
NIVEAUX_FIBO = [0.236, 0.382, 0.500, 0.618, 0.786]

def calculer_fibonacci(hist):
    """Calcule les niveaux de Fibonacci sur le dernier swing"""
    if hist is None or len(hist) < 20:
        return {}, 0, None

    closes = hist["Close"].values[-30:]
    highs  = hist["High"].values[-30:]
    lows   = hist["Low"].values[-30:]

    swing_haut = max(highs)
    swing_bas  = min(lows)
    prix       = closes[-1]

    niveaux = {}
    for n in NIVEAUX_FIBO:
        # Retracement haussier (de bas vers haut)
        niveaux[f"fibo_{int(n*1000)}"] = round(swing_haut - n * (swing_haut - swing_bas), 4)

    return niveaux, swing_haut, swing_bas

def analyser_fibonacci(hist):
    """Vérifie si le prix est sur un niveau Fibonacci clé"""
    if hist is None or len(hist) < 20:
        return 0, "Fibonacci indisponible"

    niveaux, haut, bas = calculer_fibonacci(hist)
    prix  = hist["Close"].values[-1]
    score = 0
    messages = []

    niveaux_importants = {
        "fibo_382": ("38.2%", 1),
        "fibo_500": ("50%",   2),
        "fibo_618": ("61.8%", 2),
    }

    for cle, (label, force) in niveaux_importants.items():
        niveau = niveaux.get(cle, 0)
        if niveau and abs(prix - niveau) / prix < 0.008:  # Dans les 0.8%
            # Tendance détermine si rebond ou cassure
            tendance = "BUY" if prix > (haut + bas) / 2 else "SELL"
            if tendance == "BUY":
                score += force
            else:
                score -= force
            messages.append(f"📐 Prix sur Fibonacci {label} ({niveau:.4f})")

    if not messages:
        # Indiquer le niveau Fibo le plus proche
        plus_proche = min(niveaux.values(), key=lambda x: abs(x - prix))
        pct = abs(prix - plus_proche) / prix * 100
        messages.append(f"Fibonacci : niveau le plus proche à {pct:.1f}%")

    return score, " | ".join(messages)


# ── VOLUME ───────────────────────────────────────────────────
def analyser_volume(hist):
    """Analyse du volume : OBV, confirmation de mouvement"""
    if hist is None or len(hist) < 10 or "Volume" not in hist.columns:
        return 0, "Volume indisponible"

    closes  = hist["Close"].values
    volumes = hist["Volume"].values

    if volumes[-1] == 0 or sum(volumes) == 0:
        return 0, "Volume indisponible"

    score    = 0
    messages = []

    # Volume moyen sur 20 jours
    vol_moyen = np.mean(volumes[-20:]) if len(volumes) >= 20 else np.mean(volumes)
    vol_actuel = volumes[-1]
    ratio_vol  = vol_actuel / vol_moyen if vol_moyen > 0 else 1

    # Variation du prix du jour
    variation = (closes[-1] - closes[-2]) / closes[-2] * 100 if len(closes) >= 2 else 0

    if ratio_vol > 1.5:
        if variation > 0:
            score += 2
            messages.append(f"📊 Volume fort ({ratio_vol:.1f}x normal) sur hausse → Confirmation haussière")
        else:
            score -= 2
            messages.append(f"📊 Volume fort ({ratio_vol:.1f}x normal) sur baisse → Confirmation baissière")
    elif ratio_vol < 0.5:
        messages.append(f"Volume faible ({ratio_vol:.1f}x normal) → Signal peu fiable")
    else:
        messages.append(f"Volume normal ({ratio_vol:.1f}x)")

    # OBV simplifié
    obv = 0
    obv_vals = []
    for i in range(1, min(len(closes), 15)):
        if closes[i] > closes[i-1]:
            obv += volumes[i]
        elif closes[i] < closes[i-1]:
            obv -= volumes[i]
        obv_vals.append(obv)

    if len(obv_vals) >= 5:
        obv_trend = obv_vals[-1] - obv_vals[0]
        prix_trend = closes[-1] - closes[-min(len(closes), 15)]
        # Divergence OBV
        if obv_trend > 0 and prix_trend < 0:
            score += 1
            messages.append("OBV divergence haussière → Accumulation cachée")
        elif obv_trend < 0 and prix_trend > 0:
            score -= 1
            messages.append("OBV divergence baissière → Distribution cachée")

    return score, " | ".join(messages)


# ── ANALYSE COMPLÈTE INDICATEURS ─────────────────────────────
def analyser_tous_indicateurs(hist):
    """
    Lance tous les indicateurs et retourne un score global + détails.
    Retourne: (score_total, details_dict)
    """
    if hist is None or hist.empty:
        return 0, {}

    score_rsi,   detail_rsi   = analyser_rsi(hist)
    score_macd,  detail_macd  = analyser_macd(hist)
    score_boll,  detail_boll  = analyser_bollinger(hist)
    score_fibo,  detail_fibo  = analyser_fibonacci(hist)
    score_vol,   detail_vol   = analyser_volume(hist)

    score_total = score_rsi + score_macd + score_boll + score_fibo + score_vol

    details = {
        "rsi":       detail_rsi,
        "macd":      detail_macd,
        "bollinger": detail_boll,
        "fibonacci": detail_fibo,
        "volume":    detail_vol,
        "score":     score_total,
    }

    return score_total, details


def formater_indicateurs(details):
    """Formate les indicateurs pour un message Telegram"""
    if not details:
        return ""

    msg = "📊 *INDICATEURS TECHNIQUES*\n"
    mapping = {
        "rsi":       "RSI",
        "macd":      "MACD",
        "bollinger": "Bollinger",
        "fibonacci": "Fibonacci",
        "volume":    "Volume",
    }
    for cle, label in mapping.items():
        val = details.get(cle, "")
        if val and "indisponible" not in val:
            msg += f"• *{label}:* {val}\n"
    return msg
