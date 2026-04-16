# Market Reports — TradingBot

Ce dossier est alimenté automatiquement par les tâches planifiées Cowork.

## Structure

```
market_reports/
├── hourly/          → Rapports horaires (rapport_YYYYMMDD_HHMM.md)
├── daily/           → Rapports quotidiens 20h00 (report_YYYYMMDD.md + signal_YYYYMMDD.json)
└── latest_signal.json  → Signal le plus récent (mis à jour à chaque rapport)
```

## Pour Claude Code

Lis `latest_signal.json` pour obtenir le signal de marché le plus récent.
Les champs clés pour le bot de trading :
- `global_signal` : RISK-ON / RISK-OFF / MIXED
- `alert_level` : LOW / MODERATE / HIGH / CRITICAL
- `assets` : biais et niveaux clés par actif (EURUSD, GBPUSD, USDJPY, XAUUSD, SP500, WTI)
- `opportunities` : liste des opportunités identifiées

## Fréquence
- **Rapports horaires** : toutes les heures
- **Rapport quotidien** : chaque jour à 20h00 (plus détaillé)
