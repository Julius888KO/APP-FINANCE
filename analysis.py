"""
Analyse technique, fondamentale, scoring et recommandations.
Aucune donnée n'est inventée : tout est dérivé des données disponibles.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

from config import SCORING_WEIGHTS, SCORE_BUY_MIN, SCORE_AVOID_MAX
from data import CompanySnapshot, extract_fundamentals


# ---------------------------------------------------------------------------
# Indicateurs techniques
# ---------------------------------------------------------------------------

def sma(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window=window, min_periods=max(1, window // 2)).mean()


def rsi(series: pd.Series, window: int = 14) -> pd.Series:
    """RSI classique de Wilker (14 jours)."""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / window, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def support_resistance(series: pd.Series, window: int = 20) -> tuple[float | None, float | None]:
    """Détecte un support et une résistance à partir des extrêmes récents."""
    if series.empty:
        return None, None
    recent = series.tail(window * 6)
    try:
        support = float(np.nanpercentile(recent, 10))
        resistance = float(np.nanpercentile(recent, 90))
        return support, resistance
    except Exception:
        return None, None


@dataclass
class TechnicalView:
    last: Optional[float]
    sma50: Optional[float]
    sma200: Optional[float]
    rsi14: Optional[float]
    support: Optional[float]
    resistance: Optional[float]
    trend: str
    interpretation: str
    buy_zone: Optional[tuple[float, float]]
    entry_trigger: Optional[str]
    stop_loss: Optional[float]


def build_technical_view(history: pd.DataFrame) -> TechnicalView:
    if history is None or history.empty or "Close" not in history.columns:
        return TechnicalView(None, None, None, None, None, None,
                             "indéterminée", "Données insuffisantes.",
                             None, None, None)

    close = history["Close"].dropna()
    s50 = sma(close, 50).iloc[-1] if len(close) >= 20 else None
    s200 = sma(close, 200).iloc[-1] if len(close) >= 60 else None
    r = rsi(close).iloc[-1] if len(close) >= 20 else None
    last = float(close.iloc[-1])
    supp, res = support_resistance(close)

    # Tendance
    if s50 and s200:
        if last > s50 > s200:
            trend = "haussière"
        elif last < s50 < s200:
            trend = "baissière"
        else:
            trend = "neutre"
    else:
        trend = "indéterminée"

    # Interprétation courte
    bits = []
    if r is not None:
        if r < 30:
            bits.append(f"RSI {r:.0f} : zone de survente.")
        elif r > 70:
            bits.append(f"RSI {r:.0f} : zone de surchauffe.")
        else:
            bits.append(f"RSI {r:.0f} : neutre.")
    if s200 and last:
        ecart = (last / s200 - 1) * 100
        bits.append(f"Cours {ecart:+.1f}% vs MM200.")
    interpretation = " ".join(bits) if bits else "Signal technique limité."

    # Zone d'achat préférée = entre support et -5% du niveau actuel
    buy_zone = None
    entry_trigger = None
    stop_loss = None
    if supp and last:
        lower = supp
        upper = supp * 1.05
        buy_zone = (lower, upper)
        entry_trigger = (
            f"Attendre un retour vers {upper:.2f} avec clôture au-dessus "
            f"de la MM50 (~{s50:.2f})." if s50 else
            f"Attendre un retour vers {upper:.2f}."
        )
        stop_loss = supp * 0.93

    return TechnicalView(
        last=last, sma50=float(s50) if s50 else None,
        sma200=float(s200) if s200 else None,
        rsi14=float(r) if r is not None else None,
        support=supp, resistance=res,
        trend=trend, interpretation=interpretation,
        buy_zone=buy_zone, entry_trigger=entry_trigger, stop_loss=stop_loss,
    )


# ---------------------------------------------------------------------------
# Analyse fondamentale
# ---------------------------------------------------------------------------

def revenue_eps_trend(snap: CompanySnapshot) -> dict:
    """Extrait les tendances CA / BPA sur les 3 dernières années."""
    out = {"revenue": [], "net_income": [], "eps_trend": "N/D", "rev_trend": "N/D"}
    fin = snap.financials
    if fin is None or fin.empty:
        return out

    # Les lignes varient selon les sociétés — on les recherche par label
    def _row(name_candidates):
        for n in name_candidates:
            for idx in fin.index:
                if str(idx).lower().strip() == n.lower():
                    return fin.loc[idx].dropna()
        return pd.Series(dtype=float)

    rev = _row(["Total Revenue", "Revenue", "TotalRevenue"])
    ni = _row(["Net Income", "Net Income Common Stockholders", "NetIncome"])

    if not rev.empty:
        rev = rev.sort_index(ascending=True).tail(3)
        out["revenue"] = list(zip([d.year for d in rev.index], rev.values.tolist()))
        if len(rev) >= 2:
            diffs = np.diff(rev.values)
            if np.all(diffs > 0):
                out["rev_trend"] = "en croissance"
            elif np.all(diffs < 0):
                out["rev_trend"] = "en contraction"
            else:
                out["rev_trend"] = "irrégulière"

    if not ni.empty:
        ni = ni.sort_index(ascending=True).tail(3)
        out["net_income"] = list(zip([d.year for d in ni.index], ni.values.tolist()))
        if len(ni) >= 2:
            diffs = np.diff(ni.values)
            if np.all(diffs > 0):
                out["eps_trend"] = "en amélioration"
            elif np.all(diffs < 0):
                out["eps_trend"] = "en dégradation"
            else:
                out["eps_trend"] = "irrégulière"
    return out


# ---------------------------------------------------------------------------
# Modèle de scoring
# ---------------------------------------------------------------------------

def _score_valuation(f: dict) -> float:
    """Note /20 basée sur PER, PER forward, P/B, EV/EBITDA."""
    score, denom = 0.0, 0.0
    per = f.get("per_forward") or f.get("per")
    if per is not None:
        denom += 8
        if per < 0:
            score += 1  # bénéfices négatifs : faible note
        elif per < 10:
            score += 8
        elif per < 15:
            score += 6
        elif per < 20:
            score += 4
        elif per < 30:
            score += 2
        else:
            score += 1
    pb = f.get("pb")
    if pb is not None and pb > 0:
        denom += 6
        if pb < 1:
            score += 6
        elif pb < 2:
            score += 4
        elif pb < 4:
            score += 2
        else:
            score += 1
    ev = f.get("ev_ebitda")
    if ev is not None and ev > 0:
        denom += 6
        if ev < 6:
            score += 6
        elif ev < 10:
            score += 4
        elif ev < 15:
            score += 2
        else:
            score += 1
    if denom == 0:
        return 10.0  # neutre si aucune donnée
    return (score / denom) * 20


def _score_fundamental(f: dict, trends: dict) -> float:
    """Note /20 basée sur croissance et marges."""
    s = 0.0
    # Croissance CA
    cg = f.get("croissance_ca")
    if cg is not None:
        s += min(max(cg * 100, -5), 15) / 15 * 6  # max 6 points
    else:
        s += 3
    # Marge op
    mo = f.get("marge_op")
    if mo is not None:
        s += min(max(mo * 100, -5), 30) / 30 * 6  # max 6 points
    else:
        s += 3
    # Tendance CA
    s += {"en croissance": 4, "irrégulière": 2, "en contraction": 0, "N/D": 2}.get(trends.get("rev_trend"), 2)
    # Tendance résultat
    s += {"en amélioration": 4, "irrégulière": 2, "en dégradation": 0, "N/D": 2}.get(trends.get("eps_trend"), 2)
    return min(s, 20)


def _score_balance(f: dict) -> float:
    """Note /15 basée sur endettement et liquidité."""
    s = 0.0
    denom = 0
    de = f.get("dette_eq")
    if de is not None:
        denom += 9
        if de < 30:
            s += 9
        elif de < 75:
            s += 6
        elif de < 150:
            s += 3
        else:
            s += 1
    cr = f.get("current_ratio")
    if cr is not None:
        denom += 6
        if cr > 2:
            s += 6
        elif cr > 1.2:
            s += 4
        elif cr > 1:
            s += 2
        else:
            s += 0
    if denom == 0:
        return 7.5
    return (s / denom) * 15


def _score_dividend(f: dict) -> float:
    """Note /10 basée sur rendement et soutenabilité."""
    y = f.get("rendement_div")
    if y is None or y == 0:
        return 2  # pas de dividende -> neutre bas
    pay = f.get("payout") or 0
    score = 0
    if y < 0.02:
        score += 2
    elif y < 0.04:
        score += 5
    elif y < 0.07:
        score += 8
    else:
        score += 6  # très haut rendement = risque potentiel
    # Soutenabilité via payout
    if pay and pay > 0:
        if pay < 0.5:
            score += 2
        elif pay < 0.8:
            score += 1
    return min(score, 10)


def _score_technical(tech: TechnicalView) -> float:
    """Note /15 : favorise les points d'entrée techniques convaincants."""
    s = 0.0
    if tech.rsi14 is not None:
        if tech.rsi14 < 30:
            s += 8
        elif tech.rsi14 < 45:
            s += 5
        elif tech.rsi14 < 60:
            s += 3
        else:
            s += 1
    else:
        s += 3
    if tech.trend == "haussière":
        s += 4
    elif tech.trend == "neutre":
        s += 3
    elif tech.trend == "baissière":
        s += 1
    if tech.last and tech.support and tech.last <= tech.support * 1.08:
        s += 3
    return min(s, 15)


def _score_catalyst(snap: CompanySnapshot) -> float:
    """Note /10 : volume de news récent (proxy d'intérêt) et analyst reco."""
    s = 5.0
    if snap.news:
        s += min(len(snap.news), 5) * 0.6
    reco = (snap.info or {}).get("recommendationKey", "")
    if reco in ("buy", "strong_buy"):
        s += 2
    elif reco in ("sell", "strong_sell"):
        s -= 2
    return float(max(0, min(10, s)))


def _score_risk_reward(f: dict, tech: TechnicalView, ytd_perf: float) -> float:
    """Note /10 : équilibre entre baisse subie et solidité."""
    s = 5.0
    if ytd_perf <= -40:
        s += 3  # forte décote
    elif ytd_perf <= -30:
        s += 2
    elif ytd_perf <= -20:
        s += 1
    beta = f.get("beta")
    if beta is not None:
        if beta < 1:
            s += 1
        elif beta > 1.5:
            s -= 1
    if f.get("dette_eq") and f["dette_eq"] > 200:
        s -= 2
    return float(max(0, min(10, s)))


@dataclass
class Scorecard:
    valuation: float
    fundamental: float
    balance: float
    dividend: float
    technical: float
    catalyst: float
    risk_reward: float
    total: float
    risk_level: str
    conviction: str
    profile: str
    recommendation: str
    justification: str


def classify_profile(f: dict, trends: dict, ytd: float, tech: TechnicalView) -> str:
    """Détermine le profil d'investissement."""
    per = f.get("per_forward") or f.get("per") or 0
    div = f.get("rendement_div") or 0
    margin = f.get("marge_op") or 0
    rev_trend = trends.get("rev_trend", "N/D")
    eps_trend = trends.get("eps_trend", "N/D")
    debt = f.get("dette_eq") or 0

    if rev_trend == "en contraction" and eps_trend == "en dégradation" and debt > 150:
        return "piège de valeur"
    if rev_trend == "en contraction" and div > 0.05:
        return "piège de valeur"
    if margin > 0.15 and 0 < per < 20 and rev_trend != "en contraction":
        return "qualité à prix décoté"
    if ytd < -35 and eps_trend == "en dégradation":
        return "retournement"
    if ytd < -25 and (f.get("beta") or 1) > 1.2:
        return "rebond cyclique"
    if per < 12 and div > 0.03:
        return "value"
    if margin < 0 or eps_trend == "en dégradation":
        return "spéculatif"
    return "value"


def build_scorecard(snap: CompanySnapshot, ytd_perf: float, tech: TechnicalView) -> Scorecard:
    f = extract_fundamentals(snap)
    trends = revenue_eps_trend(snap)

    val = _score_valuation(f)
    fund = _score_fundamental(f, trends)
    bal = _score_balance(f)
    div = _score_dividend(f)
    tec = _score_technical(tech)
    cat = _score_catalyst(snap)
    rr = _score_risk_reward(f, tech, ytd_perf)

    total = round(val + fund + bal + div + tec + cat + rr, 1)

    # Niveau de risque
    beta = f.get("beta") or 1.0
    debt = f.get("dette_eq") or 0
    if debt > 200 or beta > 1.6 or total < SCORE_AVOID_MAX:
        risk_level = "élevé"
    elif debt > 75 or beta > 1.2:
        risk_level = "modéré"
    else:
        risk_level = "faible"

    # Conviction
    if total >= 75:
        conviction = "élevée"
    elif total >= 55:
        conviction = "modérée"
    else:
        conviction = "faible"

    profile = classify_profile(f, trends, ytd_perf, tech)

    # Recommandation
    if profile == "piège de valeur":
        reco = "ÉVITER"
        justif = "Profil de piège de valeur : fondamentaux dégradés malgré la baisse du cours."
    elif total >= SCORE_BUY_MIN and risk_level != "élevé":
        reco = "ACHAT"
        justif = f"Score attractif ({total}/100), profil {profile}, risque {risk_level}."
    elif total <= SCORE_AVOID_MAX:
        reco = "ÉVITER"
        justif = f"Score faible ({total}/100), fondamentaux ou risques insuffisants."
    else:
        reco = "SURVEILLANCE"
        justif = f"Dossier intéressant ({total}/100) mais en attente de confirmation."

    return Scorecard(
        valuation=round(val, 1),
        fundamental=round(fund, 1),
        balance=round(bal, 1),
        dividend=round(div, 1),
        technical=round(tec, 1),
        catalyst=round(cat, 1),
        risk_reward=round(rr, 1),
        total=total,
        risk_level=risk_level,
        conviction=conviction,
        profile=profile,
        recommendation=reco,
        justification=justif,
    )


# ---------------------------------------------------------------------------
# Scénarios bull / base / bear
# ---------------------------------------------------------------------------

def build_scenarios(f: dict, tech: TechnicalView, score: Scorecard) -> dict:
    """Génère trois horizons avec scénarios bull / base / bear — en français, sans invention de chiffres."""
    last = tech.last
    res = tech.resistance
    sup = tech.support

    def _pct(a, b):
        if a and b and a > 0:
            return (b / a - 1) * 100
        return None

    upside = _pct(last, res) if last and res else None
    downside = _pct(last, sup) if last and sup else None

    horizons = {
        "Court terme (0–6 mois)": {
            "bull": (
                "Rebond technique vers la résistance "
                + (f"({res:.2f}, soit +{upside:.0f}%)" if res and upside else "")
                + " porté par un sentiment moins défensif."
            ),
            "base": (
                "Consolidation entre support et résistance en attendant le prochain catalyseur (résultats, guidance)."
            ),
            "bear": (
                "Rupture du support "
                + (f"({sup:.2f}, {downside:.0f}%)" if sup and downside else "")
                + " en cas de déception sur les résultats ou de dégradation macro."
            ),
        },
        "Moyen terme (6–24 mois)": {
            "bull": f"Normalisation des marges et retour de la croissance — profil {score.profile} récompensé.",
            "base": "Stabilisation des fondamentaux avec ré-rating progressif à mesure que la visibilité s'améliore.",
            "bear": "Persistance des vents contraires sectoriels ou dégradation du bilan si la génération de cash faiblit.",
        },
        "Long terme (2–5 ans)": {
            "bull": "Reconquête du pricing power, croissance organique soutenue, expansion des multiples.",
            "base": "Performance alignée sur la moyenne sectorielle, création de valeur modérée.",
            "bear": "Disruption structurelle, perte de parts de marché, ou érosion durable des marges.",
        },
    }
    return horizons
