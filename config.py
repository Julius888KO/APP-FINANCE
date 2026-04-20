"""
Configuration : univers de valeurs, seuils, paramètres de scoring et palette.
Toutes les valeurs affichées dans l'interface sont en français.
"""

from datetime import date

# ---------------------------------------------------------------------------
# Paramètres généraux
# ---------------------------------------------------------------------------

APP_TITLE = "Radar Opportunités 2026"
APP_SUBTITLE = (
    "Identification, analyse et scoring des valeurs cotées en forte baisse "
    "depuis le 1er janvier 2026 — marchés américains et européens."
)

# Date de référence pour le calcul de la performance YTD
YTD_START = date(2026, 1, 1)

# Seuil de sélection : repli d'au moins X % depuis le 1er janvier
DEFAULT_DROP_THRESHOLD = -20.0

# ---------------------------------------------------------------------------
# Univers d'investissement (US + Europe, grandes capitalisations liquides)
# Les tickers suivent la convention yfinance.
# ---------------------------------------------------------------------------

US_TICKERS = [
    # Technologie
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "AMD", "INTC",
    "ORCL", "CRM", "ADBE", "CSCO", "IBM", "QCOM", "TXN", "AVGO", "MU",
    # Santé
    "JNJ", "PFE", "MRK", "LLY", "ABBV", "BMY", "CVS", "UNH", "GILD", "AMGN",
    # Finance
    "JPM", "BAC", "WFC", "C", "GS", "MS", "BLK", "SCHW",
    # Conso & distribution
    "WMT", "TGT", "COST", "HD", "LOW", "NKE", "SBUX", "MCD", "KO", "PEP",
    "PG", "CL", "UL",
    # Industrie
    "BA", "CAT", "DE", "GE", "HON", "MMM", "LMT", "RTX",
    # Énergie & matériaux
    "XOM", "CVX", "COP", "SLB", "FCX", "NEM",
    # Communication & media
    "DIS", "NFLX", "T", "VZ", "CMCSA",
    # Autres
    "F", "GM", "PYPL", "SQ", "UBER", "ABNB", "SHOP", "SNAP", "PINS",
]

EU_TICKERS = [
    # France (Euronext Paris)
    "MC.PA", "OR.PA", "SAN.PA", "AI.PA", "BNP.PA", "CS.PA", "BN.PA",
    "KER.PA", "RI.PA", "EL.PA", "SU.PA", "CAP.PA", "ENGI.PA", "DG.PA",
    "ORA.PA", "VIV.PA", "STLA.PA", "RNO.PA", "ACA.PA", "GLE.PA",
    # Allemagne (XETRA)
    "SAP.DE", "SIE.DE", "ALV.DE", "DTE.DE", "BAS.DE", "BAYN.DE", "BMW.DE",
    "MBG.DE", "VOW3.DE", "DBK.DE", "ADS.DE", "IFX.DE", "MUV2.DE",
    # Pays-Bas
    "ASML.AS", "PHIA.AS", "HEIA.AS", "INGA.AS", "ADYEN.AS", "AD.AS",
    # Suisse
    "NESN.SW", "NOVN.SW", "ROG.SW", "UBSG.SW", "ZURN.SW",
    # Royaume-Uni
    "HSBA.L", "BP.L", "SHEL.L", "AZN.L", "GSK.L", "ULVR.L", "BATS.L",
    "LLOY.L", "BARC.L", "RIO.L", "VOD.L",
    # Italie / Espagne
    "ENI.MI", "ISP.MI", "UCG.MI", "ENEL.MI", "STLAM.MI",
    "SAN.MC", "BBVA.MC", "TEF.MC", "IBE.MC",
]

FULL_UNIVERSE = sorted(set(US_TICKERS + EU_TICKERS))

# Indices de référence pour le contexte macro
MARKET_INDICES = {
    "S&P 500": "^GSPC",
    "Nasdaq 100": "^NDX",
    "Dow Jones": "^DJI",
    "Euro Stoxx 50": "^STOXX50E",
    "DAX": "^GDAXI",
    "CAC 40": "^FCHI",
    "FTSE 100": "^FTSE",
}

RATES_AND_VOL = {
    "Taux US 10 ans": "^TNX",
    "Taux US 2 ans": "^IRX",
    "VIX (volatilité)": "^VIX",
    "Pétrole (WTI)": "CL=F",
    "Or": "GC=F",
    "EUR/USD": "EURUSD=X",
}

# ---------------------------------------------------------------------------
# Paramètres du modèle de scoring (total /100)
# ---------------------------------------------------------------------------

SCORING_WEIGHTS = {
    "valuation": 20,
    "fundamental": 20,
    "balance_sheet": 15,
    "dividend": 10,
    "technical": 15,
    "catalyst": 10,
    "risk_reward": 10,
}

# Seuils de recommandation
SCORE_BUY_MIN = 65
SCORE_AVOID_MAX = 40

# ---------------------------------------------------------------------------
# Palette graphique — style sobre, premium, lisible
# ---------------------------------------------------------------------------

COLORS = {
    "bg": "#0E1117",
    "surface": "#161B22",
    "border": "#262C36",
    "text": "#E6EDF3",
    "muted": "#8B949E",
    "accent": "#4C9AFF",
    "buy": "#2FB67C",
    "watch": "#E0A83B",
    "avoid": "#D86464",
    "bull": "#2FB67C",
    "bear": "#D86464",
    "neutral": "#8B949E",
}

BADGE_STYLE = {
    "ACHAT": {"bg": "#0F3D2E", "fg": "#2FB67C"},
    "SURVEILLANCE": {"bg": "#3D2F0F", "fg": "#E0A83B"},
    "ÉVITER": {"bg": "#3D1515", "fg": "#D86464"},
}
