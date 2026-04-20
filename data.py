"""
Couche de récupération des données de marché via yfinance.
Toutes les fonctions renvoient des structures propres et gèrent
l'absence de données sans invention de valeurs.
"""

# Pas d'import "from __future__ import annotations" ici :
# incompatible avec @dataclass sous Python 3.14 (utilisé par Streamlit Cloud).

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional, Union

import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

from config import YTD_START, FULL_UNIVERSE, MARKET_INDICES, RATES_AND_VOL


# ---------------------------------------------------------------------------
# Structures de données
# ---------------------------------------------------------------------------

@dataclass
class CompanySnapshot:
    """Regroupe les données brutes nécessaires à l'analyse d'une société."""
    ticker: str
    info: dict = field(default_factory=dict)
    history: pd.DataFrame = field(default_factory=pd.DataFrame)
    dividends: pd.Series = field(default_factory=pd.Series)
    financials: pd.DataFrame = field(default_factory=pd.DataFrame)
    cashflow: pd.DataFrame = field(default_factory=pd.DataFrame)
    balance: pd.DataFrame = field(default_factory=pd.DataFrame)
    news: list = field(default_factory=list)
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Utilitaires
# ---------------------------------------------------------------------------

def _safe_get(d: dict, *keys, default=None):
    """Retourne la première valeur non-nulle parmi les clés demandées."""
    if not isinstance(d, dict):
        return default
    for k in keys:
        v = d.get(k)
        if v is not None and v != "" and not (isinstance(v, float) and np.isnan(v)):
            return v
    return default


# ---------------------------------------------------------------------------
# Chargement de l'univers
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_price_history(tickers: list[str], period: str = "1y") -> pd.DataFrame:
    """Télécharge en une seule requête l'historique des cours de clôture."""
    if not tickers:
        return pd.DataFrame()
    try:
        data = yf.download(
            tickers,
            period=period,
            interval="1d",
            auto_adjust=True,
            progress=False,
            group_by="ticker",
            threads=True,
        )
    except Exception:
        return pd.DataFrame()

    # yfinance renvoie une structure MultiIndex quand plusieurs tickers ; on isole "Close".
    if isinstance(data.columns, pd.MultiIndex):
        closes = {}
        for t in tickers:
            try:
                closes[t] = data[t]["Close"]
            except Exception:
                continue
        return pd.DataFrame(closes)
    # Cas d'un seul ticker
    if "Close" in data.columns:
        return data[["Close"]].rename(columns={"Close": tickers[0]})
    return pd.DataFrame()


@st.cache_data(ttl=3600, show_spinner=False)
def screen_decliners(threshold: float, universe: list[str] | None = None) -> pd.DataFrame:
    """
    Sélectionne les valeurs dont la performance depuis le 1er janvier 2026
    est inférieure ou égale au seuil (ex. -20%).
    """
    universe = universe or FULL_UNIVERSE
    prices = fetch_price_history(universe, period="2y")
    if prices.empty:
        return pd.DataFrame(columns=["ticker", "ytd_perf", "last_price"])

    start_ts = pd.Timestamp(YTD_START)
    # On prend le premier cours disponible à partir de la date de référence
    ytd_prices = prices.loc[prices.index >= start_ts]
    if ytd_prices.empty:
        return pd.DataFrame(columns=["ticker", "ytd_perf", "last_price"])

    first = ytd_prices.iloc[0]
    last = ytd_prices.iloc[-1]
    perf = ((last - first) / first) * 100.0

    df = pd.DataFrame({
        "ticker": perf.index,
        "ytd_perf": perf.values,
        "last_price": last.values,
    }).dropna()
    df = df[df["ytd_perf"] <= threshold].sort_values("ytd_perf")
    return df.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Détail par société
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_company(ticker: str) -> CompanySnapshot:
    """Récupère les informations détaillées d'une société."""
    snap = CompanySnapshot(ticker=ticker)
    try:
        t = yf.Ticker(ticker)
        try:
            snap.info = t.info or {}
        except Exception:
            snap.info = {}
        try:
            snap.history = t.history(period="2y", auto_adjust=True)
        except Exception:
            snap.history = pd.DataFrame()
        try:
            snap.dividends = t.dividends
        except Exception:
            snap.dividends = pd.Series(dtype=float)
        try:
            snap.financials = t.financials if t.financials is not None else pd.DataFrame()
        except Exception:
            snap.financials = pd.DataFrame()
        try:
            snap.cashflow = t.cashflow if t.cashflow is not None else pd.DataFrame()
        except Exception:
            snap.cashflow = pd.DataFrame()
        try:
            snap.balance = t.balance_sheet if t.balance_sheet is not None else pd.DataFrame()
        except Exception:
            snap.balance = pd.DataFrame()
        try:
            snap.news = (t.news or [])[:5]
        except Exception:
            snap.news = []
    except Exception as e:
        snap.error = str(e)
    return snap


# ---------------------------------------------------------------------------
# Données macro / contexte de marché
# ---------------------------------------------------------------------------

@st.cache_data(ttl=1800, show_spinner=False)
def fetch_market_context() -> dict:
    """Retourne un tableau de bord synthétique du contexte de marché."""
    out = {"indices": {}, "rates": {}, "errors": []}

    all_tickers = list(MARKET_INDICES.values()) + list(RATES_AND_VOL.values())
    try:
        data = yf.download(
            all_tickers,
            period="3mo",
            interval="1d",
            auto_adjust=True,
            progress=False,
            group_by="ticker",
            threads=True,
        )
    except Exception as e:
        out["errors"].append(str(e))
        return out

    def _series(tk: str) -> pd.Series:
        try:
            if isinstance(data.columns, pd.MultiIndex):
                return data[tk]["Close"].dropna()
            return data["Close"].dropna()
        except Exception:
            return pd.Series(dtype=float)

    for label, tk in MARKET_INDICES.items():
        s = _series(tk)
        if s.empty:
            continue
        last = float(s.iloc[-1])
        ref = float(s.iloc[0])
        out["indices"][label] = {
            "last": last,
            "perf_3m": (last / ref - 1) * 100 if ref else None,
            "series": s,
        }

    for label, tk in RATES_AND_VOL.items():
        s = _series(tk)
        if s.empty:
            continue
        last = float(s.iloc[-1])
        prev = float(s.iloc[-min(len(s), 22)])
        out["rates"][label] = {
            "last": last,
            "delta_1m": last - prev,
            "series": s,
        }

    return out


# ---------------------------------------------------------------------------
# Aides d'extraction
# ---------------------------------------------------------------------------

def extract_fundamentals(snap: CompanySnapshot) -> dict:
    """Extrait un dictionnaire normalisé de métriques fondamentales."""
    info = snap.info or {}
    out = {
        "nom": _safe_get(info, "longName", "shortName", default=snap.ticker),
        "pays": _safe_get(info, "country", default="N/D"),
        "bourse": _safe_get(info, "exchange", "fullExchangeName", default="N/D"),
        "secteur": _safe_get(info, "sector", default="N/D"),
        "industrie": _safe_get(info, "industry", default="N/D"),
        "devise": _safe_get(info, "currency", default=""),
        "market_cap": _safe_get(info, "marketCap"),
        "prix": _safe_get(info, "currentPrice", "regularMarketPrice"),
        "haut_52s": _safe_get(info, "fiftyTwoWeekHigh"),
        "bas_52s": _safe_get(info, "fiftyTwoWeekLow"),
        "per": _safe_get(info, "trailingPE"),
        "per_forward": _safe_get(info, "forwardPE"),
        "ev_ebitda": _safe_get(info, "enterpriseToEbitda"),
        "pb": _safe_get(info, "priceToBook"),
        "marge_op": _safe_get(info, "operatingMargins"),
        "marge_nette": _safe_get(info, "profitMargins"),
        "croissance_ca": _safe_get(info, "revenueGrowth"),
        "croissance_bpa": _safe_get(info, "earningsGrowth"),
        "dette_eq": _safe_get(info, "debtToEquity"),
        "current_ratio": _safe_get(info, "currentRatio"),
        "fcf": _safe_get(info, "freeCashflow"),
        "rendement_div": _safe_get(info, "dividendYield"),
        "payout": _safe_get(info, "payoutRatio"),
        "div_par_action": _safe_get(info, "dividendRate"),
        "recommendation": _safe_get(info, "recommendationKey"),
        "beta": _safe_get(info, "beta"),
        "short_ratio": _safe_get(info, "shortRatio"),
        "resume": _safe_get(info, "longBusinessSummary", default=""),
    }
    return out


def dividends_last_three_years(snap: CompanySnapshot) -> pd.DataFrame:
    """Retourne les dividendes agrégés par année civile sur les 3 dernières années complètes."""
    s = snap.dividends
    if s is None or s.empty:
        return pd.DataFrame()
    current_year = datetime.now().year
    yearly = s.groupby(s.index.year).sum().sort_index()
    # Années complètes uniquement, puis les 3 plus récentes
    complete = yearly[yearly.index < current_year].tail(3)
    if complete.empty:
        return pd.DataFrame()
    return pd.DataFrame({
        "Année": [int(y) for y in complete.index],
        "Dividende total": [float(v) for v in complete.values],
    })


def detect_dividend_frequency(snap: CompanySnapshot) -> str:
    """Détermine la fréquence de distribution à partir des intervalles observés."""
    s = snap.dividends
    if s is None or s.empty or len(s) < 2:
        return "Donnée non disponible"
    try:
        recent = s.sort_index().tail(12).index
        deltas = np.diff(recent.astype("int64")) / (24 * 3600 * 1e9)  # en jours
        if len(deltas) == 0:
            return "Donnée non disponible"
        median = float(np.median(deltas))
    except Exception:
        return "Donnée non disponible"
    if median < 45:
        return "Mensuelle"
    if median < 130:
        return "Trimestrielle"
    if median < 250:
        return "Semestrielle"
    return "Annuelle"


def dividend_trend(snap: CompanySnapshot) -> str:
    """Détermine la tendance du dividende : croissant / stable / déclinant / suspendu."""
    hist = dividends_last_three_years(snap)
    if hist.empty or len(hist) < 2:
        return "Donnée non disponible"
    vals = hist["Dividende total"].values
    if vals[-1] == 0:
        return "Suspendu"
    diffs = np.diff(vals)
    if np.all(diffs > 0):
        return "En croissance"
    if np.all(diffs < 0):
        return "En baisse"
    if abs(vals[-1] - vals[0]) / max(vals[0], 1e-9) < 0.05:
        return "Stable"
    return "Irrégulier"
