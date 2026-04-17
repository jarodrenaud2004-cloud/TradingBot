# ============================================================
#  BROKER OANDA — Exécution automatique (compte démo/réel)
#  API REST v20 — Supports: Gold, WTI, CAC40, DAX, Matières premières
# ============================================================

import oandapyV20
import oandapyV20.endpoints.orders as orders
import oandapyV20.endpoints.trades as trades
import oandapyV20.endpoints.accounts as accounts
import oandapyV20.endpoints.pricing as pricing
from config import OANDA_API_KEY, OANDA_ACCOUNT_ID, OANDA_ENVIRONMENT, RISQUE_PAR_TRADE

# ── Correspondance marchés ↔ instruments OANDA ─────────────
OANDA_INSTRUMENTS = {
    "WTI":    "WTICO_USD",   # Pétrole WTI
    "GOLD":   "XAU_USD",     # Or
    "SILVER": "XAG_USD",     # Argent
    "CORN":   "CORN_USD",    # Maïs
    "WHEAT":  "WEAT_USD",    # Blé
    "NATGAS": "NATGAS_USD",  # Gaz naturel
    "CAC40":  "FR40_EUR",    # CAC 40
    "DAX":    "DE30_EUR",    # DAX
    # Les actions européennes (TTE, MC, AIR...) ne sont pas disponibles sur OANDA
    # Pour celles-ci le bot envoie uniquement des alertes sans exécution
}

def _client():
    return oandapyV20.API(
        access_token=OANDA_API_KEY,
        environment=OANDA_ENVIRONMENT
    )

# ── Solde du compte ────────────────────────────────────────
def get_solde():
    """Retourne les infos du compte (solde, devise, etc.)"""
    try:
        client = _client()
        r = accounts.AccountSummary(OANDA_ACCOUNT_ID)
        client.request(r)
        acc = r.response["account"]
        return {
            "balance":   float(acc["balance"]),
            "currency":  acc["currency"],
            "pl":        float(acc["pl"]),
            "openTrades": int(acc["openTradeCount"]),
            "nav":       float(acc["NAV"]),
        }
    except Exception as e:
        return {"error": str(e)}

# ── Calcul des unités selon le risque ─────────────────────
def calculer_units(prix_entree, stop_loss, solde):
    """
    Calcule le nombre d'unités à trader pour risquer RISQUE_PAR_TRADE %
    Ex: solde=10 000€, risque=1%, SL=20 pts → units = 100€/20 = 5
    """
    risque_euros = solde * (RISQUE_PAR_TRADE / 100)
    distance_sl  = abs(prix_entree - stop_loss)
    if distance_sl == 0:
        return 1
    units = int(risque_euros / distance_sl)
    return max(1, units)

# ── Placer un ordre au marché ──────────────────────────────
def placer_ordre(nom_marche, direction, stop_loss=None, take_profit=None, units=None):
    """
    Place un ordre marché sur OANDA.

    Paramètres:
        nom_marche : "WTI", "GOLD", "CAC40"...
        direction  : "BUY" ou "SELL"
        stop_loss  : prix du SL (facultatif)
        take_profit: prix du TP (facultatif)
        units      : nb unités (si None, calculé automatiquement selon risque)

    Retourne un dict avec "success" ou "error"
    """
    instrument = OANDA_INSTRUMENTS.get(nom_marche)
    if not instrument:
        return {"error": f"⚠️ {nom_marche} non disponible sur OANDA (action EU)"}

    try:
        # Récupérer le prix actuel
        prix_actuel = get_prix_oanda(instrument)
        if not prix_actuel:
            return {"error": "Impossible de récupérer le prix"}

        # Calculer les unités si non fourni
        if units is None:
            solde_info = get_solde()
            if "error" in solde_info:
                return solde_info
            solde = solde_info["balance"]
            sl = stop_loss or (prix_actuel * 0.98 if direction == "BUY" else prix_actuel * 1.02)
            units = calculer_units(prix_actuel, sl, solde)

        # Unités négatives pour SELL
        units_final = abs(units) if direction == "BUY" else -abs(units)

        order_data = {
            "order": {
                "type":          "MARKET",
                "instrument":    instrument,
                "units":         str(units_final),
                "timeInForce":   "FOK",
                "positionFill":  "DEFAULT"
            }
        }

        # Ajouter SL
        if stop_loss:
            order_data["order"]["stopLossOnFill"] = {
                "price": f"{stop_loss:.5f}"
            }

        # Ajouter TP
        if take_profit:
            order_data["order"]["takeProfitOnFill"] = {
                "price": f"{take_profit:.5f}"
            }

        client = _client()
        r = orders.OrderCreate(OANDA_ACCOUNT_ID, data=order_data)
        client.request(r)

        resp = r.response
        trade_id = resp.get("orderFillTransaction", {}).get("tradeOpened", {}).get("tradeID", "?")

        return {
            "success":    True,
            "trade_id":   trade_id,
            "instrument": instrument,
            "direction":  direction,
            "units":      abs(units_final),
            "prix":       prix_actuel,
            "sl":         stop_loss,
            "tp":         take_profit,
        }

    except Exception as e:
        return {"error": str(e)}

# ── Positions ouvertes ─────────────────────────────────────
def get_positions_ouvertes():
    """Retourne toutes les positions actuellement ouvertes"""
    try:
        client = _client()
        r = trades.OpenTrades(OANDA_ACCOUNT_ID)
        client.request(r)
        return r.response.get("trades", [])
    except Exception as e:
        return []

# ── Fermer une position ────────────────────────────────────
def fermer_position(trade_id):
    """Ferme une position par son ID"""
    try:
        client = _client()
        r = trades.TradeClose(OANDA_ACCOUNT_ID, tradeID=str(trade_id))
        client.request(r)
        return {"success": True, "response": r.response}
    except Exception as e:
        return {"error": str(e)}

# ── Fermer toutes les positions ────────────────────────────
def fermer_tout():
    """Ferme toutes les positions ouvertes"""
    resultats = []
    for trade in get_positions_ouvertes():
        res = fermer_position(trade["id"])
        resultats.append({
            "trade_id":   trade["id"],
            "instrument": trade["instrument"],
            "result":     res
        })
    return resultats

# ── Prix en temps réel OANDA ───────────────────────────────
def get_prix_oanda(instrument):
    """Récupère le prix mid en temps réel depuis OANDA"""
    try:
        client = _client()
        params = {"instruments": instrument}
        r = pricing.PricingInfo(OANDA_ACCOUNT_ID, params=params)
        client.request(r)
        prices = r.response.get("prices", [])
        if prices:
            bid = float(prices[0]["bids"][0]["price"])
            ask = float(prices[0]["asks"][0]["price"])
            return (bid + ask) / 2
        return None
    except:
        return None

# ── Formater les positions ouvertes ───────────────────────
def formater_positions_telegram():
    """Formate les positions ouvertes pour un message Telegram"""
    trades_ouverts = get_positions_ouvertes()

    if not trades_ouverts:
        return "⚪ *Aucune position ouverte en ce moment.*"

    msg = f"📂 *{len(trades_ouverts)} POSITION(S) OUVERTE(S)*\n"
    msg += "━━━━━━━━━━━━━━━━━━\n\n"

    for t in trades_ouverts:
        units    = float(t["currentUnits"])
        direction = "🟢 BUY" if units > 0 else "🔴 SELL"
        pl        = float(t.get("unrealizedPL", 0))
        emoji_pl  = "📈" if pl >= 0 else "📉"
        prix_ouv  = float(t["price"])

        msg += f"{direction} *{t['instrument']}*\n"
        msg += f"💰 Entrée: `{prix_ouv:.5f}`\n"
        msg += f"{emoji_pl} P&L: `{pl:+.2f} {t.get('financing', 'USD')}`\n"
        msg += f"🔑 ID: `{t['id']}`\n\n"

    return msg
