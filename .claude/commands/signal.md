Lis et analyse les dernières informations de marché disponibles, puis présente un rapport complet et actionnable pour le bot de trading.

## Étapes à suivre

1. Lis `market_reports/latest_signal.json`
2. Trouve le dernier rapport horaire dans `market_reports/hourly/` (fichier le plus récent)
3. Si on est après 20h00, lis aussi le dernier rapport quotidien dans `market_reports/daily/`

## Format de réponse attendu

Présente les informations dans cet ordre exact :

---

### 🌍 CONTEXTE GLOBAL
- Signal de marché : RISK-ON / RISK-OFF / MIXED
- Niveau d'alerte : LOW / MODERATE / HIGH / CRITICAL
- Résumé en 2-3 phrases de la situation macro

### 🚨 ALERTES & ÉVÉNEMENTS IMPORTANTS
Liste tous les événements majeurs du moment (banques centrales, géopolitique, données économiques, etc.)

### 💱 FOREX
Pour chaque paire (EUR/USD, GBP/USD, USD/JPY) :
- Niveau actuel | Biais | Confiance | Niveaux clés (support / résistance)

### 📈 INDICES
S&P500, Nasdaq, CAC40 — niveau, variation, biais

### 🏗️ MATIÈRES PREMIÈRES
Or, Argent, Pétrole WTI — niveau, biais, catalyseurs

### ⚡ RISQUES À SURVEILLER
Liste des risques principaux pouvant impacter les positions

### 🤖 DÉCISIONS DU BOT

Pour chaque actif tradé (EUR/USD, GBP/USD, USD/JPY, XAU/USD, XAG/USD, WTI, S&P500) :

| Actif | Action | Entrée | Stop-Loss | Take-Profit | Raison |
|-------|--------|--------|-----------|-------------|--------|

Applique strictement les règles de décision définies dans CLAUDE.md :
- LONG si bias=BULLISH + confidence=HIGH/MEDIUM + signal=RISK-ON/MIXED + alert=LOW/MODERATE + VIX<25
- SHORT si bias=BEARISH + confidence=HIGH/MEDIUM + signal=RISK-OFF + alert=MODERATE/HIGH
- NE PAS TRADER si alert=CRITICAL ou VIX>30 ou tous les actifs à confidence=LOW

### 📌 RÉSUMÉ EXÉCUTIF
Top 3 opportunités du moment avec justification courte.
