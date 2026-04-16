# TradingBot — Contexte & Instructions

## 🔴 RÈGLE N°1 — À lire AVANT TOUT
Avant chaque analyse ou décision de trading, tu DOIS lire le fichier :
```
market_reports/latest_signal.json
```
Ce fichier est mis à jour automatiquement toutes les heures par un agent Cowork qui effectue une veille des marchés mondiaux (Forex, Indices, Matières premières, Macro).

---

## 📁 Structure des fichiers de signaux

```
market_reports/
├── latest_signal.json          ← TOUJOURS lire en premier
├── hourly/
│   └── report_YYYYMMDD_HHMM.md  ← Rapports horaires détaillés
└── daily/
    ├── report_YYYYMMDD.md        ← Rapport quotidien complet (généré à 20h00)
    └── signal_YYYYMMDD.json      ← Signal JSON quotidien détaillé
```

---

## 📊 Comment lire latest_signal.json

| Champ | Description |
|-------|-------------|
| `global_signal` | RISK-ON / RISK-OFF / MIXED — biais général du marché |
| `alert_level` | LOW / MODERATE / HIGH / CRITICAL — niveau de risque |
| `top_opportunity` | Meilleure opportunité identifiée par l'analyse |
| `assets_quick` | Biais + confiance + niveau actuel pour chaque actif |
| `risk_indicators` | VIX, taux US 10Y/2Y, Fear&Greed, DXY |

### Biais des actifs
- `bias` : BULLISH / BEARISH / NEUTRAL
- `confidence` : HIGH / MEDIUM / LOW
- `level` : dernier prix connu

---

## ⚡ Règles de décision pour le bot

### Quand prendre une position LONGUE
- `bias` = BULLISH ET `confidence` = HIGH ou MEDIUM
- `global_signal` = RISK-ON ou MIXED
- `alert_level` = LOW ou MODERATE
- VIX < 25

### Quand prendre une position COURTE
- `bias` = BEARISH ET `confidence` = HIGH ou MEDIUM
- `global_signal` = RISK-OFF
- `alert_level` = MODERATE ou HIGH

### Quand NE PAS trader
- `alert_level` = CRITICAL
- `confidence` = LOW sur tous les actifs
- VIX > 30 (volatilité extrême)
- `global_signal` = MIXED ET `alert_level` = HIGH

---

## 🎯 Actifs tradés par ce bot
- **Forex** : EUR/USD, GBP/USD, USD/JPY
- **Matières premières** : Or (XAU/USD), Argent (XAG/USD), Pétrole WTI
- **Indices** : S&P500

---

## 🔄 Workflow recommandé à chaque session

1. Lire `market_reports/latest_signal.json`
2. Vérifier `alert_level` — si CRITICAL, ne pas trader
3. Identifier les actifs avec `confidence` HIGH ou MEDIUM
4. Croiser avec les règles de décision ci-dessus
5. Proposer les positions avec niveaux d'entrée, stop-loss et take-profit
6. Pour plus de détails, lire le rapport horaire ou quotidien correspondant

---

## 📌 Signal actuel (mis à jour automatiquement)
> Le fichier `latest_signal.json` contient toujours le signal le plus récent.
> Dernière mise à jour : voir champ `last_updated` dans le JSON.

---

*Ce fichier est le pont entre la veille de marché automatisée (Cowork) et le bot de trading (Claude Code).*
