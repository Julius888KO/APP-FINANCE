# Radar Opportunités 2026

Tableau de bord Streamlit qui identifie, analyse et classe les sociétés cotées (US + Europe) en forte baisse depuis le 1er janvier 2026, puis leur attribue un score global, une recommandation (ACHAT / SURVEILLANCE / ÉVITER) et propose un portefeuille modèle.

## Fonctionnalités

- **Contexte de marché** : indices, taux, volatilité, lecture macro synthétique.
- **Screening** : toutes les valeurs en repli d'au moins 20 % depuis le 1er janvier 2026.
- **Analyse par société** : performance, technique (MM50/MM200, RSI, supports/résistances), fondamentale (CA, marges, dette, valorisation), dividende, forces/faiblesses, risques, scénarios bull / base / bear.
- **Modèle de scoring /100** : valorisation, qualité fondamentale, bilan, dividende, technique, catalyseurs, risque/récompense.
- **Classements** : top opportunités, valeurs risquées, pièges de valeur, titres survendus.
- **Portefeuille modèle** : allocation proportionnelle au score, plafonnée, avec poche de liquidités.

## Installation

```bash
cd stock_dashboard
pip install -r requirements.txt
```

## Lancement

```bash
streamlit run app.py
```

L'application s'ouvre dans le navigateur à l'adresse indiquée par Streamlit (par défaut http://localhost:8501).

## Structure du projet

```
stock_dashboard/
├── app.py           # Application Streamlit (point d'entrée)
├── config.py        # Univers de tickers, paramètres de scoring, palette
├── data.py          # Récupération des données via yfinance
├── analysis.py      # Indicateurs techniques, scoring, scénarios
├── ui.py            # Composants visuels réutilisables
├── requirements.txt
└── README.md
```

## Notes

- Les données proviennent de Yahoo Finance via la bibliothèque `yfinance`. Une connexion Internet est requise.
- Les données indisponibles sont clairement signalées « N/D » : aucune valeur n'est inventée.
- Ce tableau de bord est un outil d'analyse et ne constitue pas un conseil en investissement.
