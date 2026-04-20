"""
Radar Opportunités 2026 — tableau de bord Streamlit.
Lancement : streamlit run app.py
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config import (
    APP_TITLE,
    COLORS,
    DEFAULT_DROP_THRESHOLD,
    FULL_UNIVERSE,
    EU_TICKERS,
    US_TICKERS,
    YTD_START,
)
from data import (
    CompanySnapshot,
    detect_dividend_frequency,
    dividend_trend,
    dividends_last_three_years,
    extract_fundamentals,
    fetch_company,
    fetch_market_context,
    screen_decliners,
)
from analysis import (
    Scorecard,
    TechnicalView,
    build_scenarios,
    build_scorecard,
    build_technical_view,
    revenue_eps_trend,
)
from ui import (
    inject_css,
    kpi_row,
    pill,
    price_chart,
    reco_badge,
    render_header,
    render_main_table,
    score_breakdown,
    score_gauge,
)


# ---------------------------------------------------------------------------
# Configuration de la page
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="📉",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_css()


# ---------------------------------------------------------------------------
# Aides de formatage
# ---------------------------------------------------------------------------

def fmt_large(value) -> str:
    if value is None or pd.isna(value):
        return "N/D"
    try:
        v = float(value)
    except Exception:
        return str(value)
    for unit, div in [("B$", 1e9), ("M$", 1e6), ("k$", 1e3)]:
        if abs(v) >= div:
            return f"{v / div:,.2f} {unit}"
    return f"{v:,.0f}"


def fmt_pct(v) -> str:
    if v is None or pd.isna(v):
        return "N/D"
    return f"{v * 100:+.2f}%"


def fmt_num(v, decimals: int = 2) -> str:
    if v is None or pd.isna(v):
        return "N/D"
    try:
        return f"{float(v):,.{decimals}f}"
    except Exception:
        return str(v)


# ---------------------------------------------------------------------------
# Sidebar — filtres
# ---------------------------------------------------------------------------

def sidebar_controls() -> dict:
    with st.sidebar:
        st.markdown(f"### Filtres")
        zone = st.radio(
            "Zone géographique",
            options=["États-Unis + Europe", "États-Unis", "Europe"],
            index=0,
        )
        threshold = st.slider(
            "Repli minimum YTD (%)",
            min_value=-60, max_value=-20,
            value=int(DEFAULT_DROP_THRESHOLD), step=5,
            help="Ne conserver que les sociétés en baisse d'au moins ce pourcentage depuis le 1er janvier 2026.",
        )
        limit_choice = st.select_slider(
            "Taille de l'analyse",
            options=["25", "50", "100", "200", "Tous"],
            value="Tous",
            help="Toutes les sociétés correspondant au critère sont analysées par défaut. "
                 "Réduire uniquement pour accélérer le premier chargement.",
        )
        limit = None if limit_choice == "Tous" else int(limit_choice)
    universe = FULL_UNIVERSE
    if zone == "États-Unis":
        universe = US_TICKERS
    elif zone == "Europe":
        universe = EU_TICKERS
    with st.sidebar:
        st.markdown("---")
        st.caption(
            f"Date de référence : **{YTD_START.strftime('%d/%m/%Y')}**.  \n"
            f"Univers de référence : **{len(universe)}** sociétés.  \n"
            f"Mode d'analyse : **{limit_choice}**."
        )
    return {"threshold": float(threshold), "universe": universe, "limit": limit}


# ---------------------------------------------------------------------------
# Contexte de marché
# ---------------------------------------------------------------------------

def render_market_context():
    st.markdown("### Contexte de marché")
    ctx = fetch_market_context()
    if not ctx["indices"] and not ctx["rates"]:
        st.warning("Données de marché indisponibles actuellement.")
        return

    # KPIs rapides
    kpis = []
    for name in ["S&P 500", "Euro Stoxx 50", "CAC 40", "DAX"]:
        if name in ctx["indices"]:
            d = ctx["indices"][name]
            perf = d.get("perf_3m")
            kpis.append((
                name,
                f"{d['last']:,.0f}",
                f"{perf:+.2f}% sur 3 mois" if perf is not None else "",
            ))
    if kpis:
        kpi_row(kpis[:4])

    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="rf-section-title">Indices principaux</div>', unsafe_allow_html=True)
        fig = go.Figure()
        for name, d in ctx["indices"].items():
            s = d["series"]
            norm = (s / s.iloc[0] - 1) * 100
            fig.add_trace(go.Scatter(x=norm.index, y=norm.values, name=name, mode="lines"))
        fig.update_layout(
            height=320,
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor=COLORS["surface"], plot_bgcolor=COLORS["surface"],
            font=dict(color=COLORS["text"], size=11),
            xaxis=dict(gridcolor=COLORS["border"]),
            yaxis=dict(gridcolor=COLORS["border"], title="Performance (%)"),
            legend=dict(orientation="h", y=-0.18),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown('<div class="rf-section-title">Taux, volatilité & macro</div>', unsafe_allow_html=True)
        rows = []
        for name, d in ctx["rates"].items():
            rows.append({
                "Indicateur": name,
                "Dernier": f"{d['last']:.2f}",
                "Δ 1 mois": f"{d['delta_1m']:+.2f}",
            })
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    # Lecture macro synthétique dérivée des données
    _render_macro_reading(ctx)


def _render_macro_reading(ctx: dict):
    """Produit une lecture macro synthétique basée uniquement sur les données observées."""
    vix = ctx["rates"].get("VIX (volatilité)", {}).get("last")
    t10 = ctx["rates"].get("Taux US 10 ans", {}).get("last")
    t2 = ctx["rates"].get("Taux US 2 ans", {}).get("last")
    sp = ctx["indices"].get("S&P 500", {}).get("perf_3m")

    lines = []
    if sp is not None:
        if sp > 3:
            trend = "tendance haussière des actions"
        elif sp < -3:
            trend = "correction des actions"
        else:
            trend = "marché actions sans direction marquée"
        lines.append(f"Sur 3 mois : {trend} (S&P 500 {sp:+.1f}%).")
    if vix is not None:
        regime = "faible" if vix < 15 else "modérée" if vix < 22 else "élevée"
        lines.append(f"Volatilité {regime} (VIX {vix:.1f}).")
    if t10 is not None and t2 is not None:
        spread = t10 - t2
        lines.append(
            f"Courbe des taux : 2 ans {t2:.2f}%, 10 ans {t10:.2f}% "
            f"(spread {spread:+.2f} — {'inversée' if spread < 0 else 'normale'})."
        )

    # Orientation du style
    if vix is not None and t10 is not None:
        if vix > 22:
            style = "Environnement **défensif** privilégié (qualité, dividende, faible beta)."
        elif sp is not None and sp > 3 and t10 < 4.5:
            style = "Environnement plutôt favorable aux styles **croissance** et **cycliques**."
        else:
            style = "Environnement mixte : la sélection **value / qualité décotée** reste pertinente."
        lines.append(style)

    lines.append(
        "**Principaux risques** : inflation persistante, tensions géopolitiques, "
        "resserrement du crédit, révisions de bénéfices négatives."
    )

    st.markdown(
        '<div class="rf-card"><div class="rf-section-title">Lecture macro</div>'
        + "<br>".join(lines) + "</div>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Analyse d'une société (carte détaillée)
# ---------------------------------------------------------------------------

def analyze_company(ticker: str, ytd_perf: float) -> dict:
    """Récupère les données et construit toutes les analyses d'une société."""
    snap = fetch_company(ticker)
    fund = extract_fundamentals(snap)
    tech = build_technical_view(snap.history)
    score = build_scorecard(snap, ytd_perf, tech)
    trends = revenue_eps_trend(snap)
    scenarios = build_scenarios(fund, tech, score)
    return {
        "snap": snap,
        "fund": fund,
        "tech": tech,
        "score": score,
        "trends": trends,
        "scenarios": scenarios,
        "ytd": ytd_perf,
    }


def render_company_card(analysis: dict):
    snap: CompanySnapshot = analysis["snap"]
    f = analysis["fund"]
    tech: TechnicalView = analysis["tech"]
    score: Scorecard = analysis["score"]
    trends = analysis["trends"]
    scenarios = analysis["scenarios"]
    ytd = analysis["ytd"]
    dev = f.get("devise") or ""

    with st.container():
        st.markdown('<div class="rf-card">', unsafe_allow_html=True)

        # Entête
        c1, c2 = st.columns([5, 2])
        with c1:
            st.markdown(
                f"### {f['nom']}  "
                f"<span style='color:{COLORS['muted']};font-size:14px;'>({snap.ticker})</span>",
                unsafe_allow_html=True,
            )
            st.markdown(
                pill(f["secteur"]) + pill(f["industrie"]) + pill(f["pays"]) + pill(f["bourse"]),
                unsafe_allow_html=True,
            )
        with c2:
            st.markdown(
                f"<div style='text-align:right'>{reco_badge(score.recommendation)}"
                f"<div style='color:{COLORS['muted']};font-size:12px;margin-top:6px;'>Profil : {score.profile} · Risque : {score.risk_level} · Conviction : {score.conviction}</div></div>",
                unsafe_allow_html=True,
            )

        # Métriques principales
        haut = f.get("haut_52s")
        bas = f.get("bas_52s")
        dist_haut = (f["prix"] / haut - 1) * 100 if f.get("prix") and haut else None

        kpi_row([
            ("Performance YTD", f"{ytd:+.1f}%", f"depuis le {YTD_START.strftime('%d/%m/%Y')}"),
            ("Cours actuel", fmt_num(f.get("prix")) + (f" {dev}" if dev else ""),
             f"Distance plus haut 52s : {dist_haut:+.1f}%" if dist_haut is not None else ""),
            ("Capitalisation", fmt_large(f.get("market_cap")), ""),
            ("Score global", f"{score.total:.0f}/100", f"{score.recommendation} — {score.conviction}"),
        ])

        st.markdown("<hr class='rf-divider'>", unsafe_allow_html=True)

        # Colonnes graphiques / analyse technique
        g1, g2 = st.columns([2, 1])
        with g1:
            st.markdown('<div class="rf-section-title">Évolution du cours (1 an)</div>', unsafe_allow_html=True)
            if not snap.history.empty:
                st.plotly_chart(
                    price_chart(snap.history, sma50=True, sma200=True,
                                support=tech.support, resistance=tech.resistance),
                    use_container_width=True,
                )
            else:
                st.info("Historique de cours indisponible.")
        with g2:
            st.markdown('<div class="rf-section-title">Score détaillé</div>', unsafe_allow_html=True)
            st.plotly_chart(score_gauge(score.total), use_container_width=True)
            st.plotly_chart(score_breakdown(score), use_container_width=True)

        st.markdown("<hr class='rf-divider'>", unsafe_allow_html=True)

        # Sections analytiques
        a1, a2, a3 = st.columns(3)

        with a1:
            st.markdown('<div class="rf-section-title">Analyse technique</div>', unsafe_allow_html=True)
            st.markdown(
                f"**Tendance :** {tech.trend}  \n"
                f"**RSI (14) :** {fmt_num(tech.rsi14, 1)}  \n"
                f"**MM50 :** {fmt_num(tech.sma50)}  \n"
                f"**MM200 :** {fmt_num(tech.sma200)}  \n"
                f"**Support :** {fmt_num(tech.support)}  \n"
                f"**Résistance :** {fmt_num(tech.resistance)}  \n"
                f"{tech.interpretation}"
            )
            if tech.buy_zone:
                st.markdown(
                    f"**Zone d'achat préférée :** {tech.buy_zone[0]:.2f} – {tech.buy_zone[1]:.2f}  \n"
                    f"**Déclencheur d'entrée :** {tech.entry_trigger}  \n"
                    f"**Stop suggéré :** {tech.stop_loss:.2f}" if tech.stop_loss else ""
                )

        with a2:
            st.markdown('<div class="rf-section-title">Analyse fondamentale</div>', unsafe_allow_html=True)
            st.markdown(
                f"**Croissance CA :** {fmt_pct(f.get('croissance_ca'))}  \n"
                f"**Tendance CA 3 ans :** {trends.get('rev_trend', 'N/D')}  \n"
                f"**Tendance résultat 3 ans :** {trends.get('eps_trend', 'N/D')}  \n"
                f"**Marge opérationnelle :** {fmt_pct(f.get('marge_op'))}  \n"
                f"**Marge nette :** {fmt_pct(f.get('marge_nette'))}  \n"
                f"**Dette / fonds propres :** {fmt_num(f.get('dette_eq'), 1)}  \n"
                f"**Free cash-flow :** {fmt_large(f.get('fcf'))}  \n"
                f"**PER / PER forward :** {fmt_num(f.get('per'), 1)} / {fmt_num(f.get('per_forward'), 1)}  \n"
                f"**EV/EBITDA :** {fmt_num(f.get('ev_ebitda'), 1)}  \n"
                f"**P/B :** {fmt_num(f.get('pb'), 2)}"
            )

        with a3:
            st.markdown('<div class="rf-section-title">Dividende</div>', unsafe_allow_html=True)
            y = f.get("rendement_div")
            hist = dividends_last_three_years(snap)
            freq = detect_dividend_frequency(snap)
            trend = dividend_trend(snap)
            pays_div = (y is not None and y > 0) or not hist.empty

            if pays_div:
                yield_txt = f"{y * 100:.2f} %" if y and y > 0 else "Donnée non disponible"
                payout_val = f.get("payout")
                payout_txt = f"{payout_val * 100:.1f} %" if payout_val else "Donnée non disponible"
                div_amt = f.get("div_par_action")
                div_amt_txt = f"{div_amt:.2f} {dev}" if div_amt else "Donnée non disponible"

                st.markdown(
                    f"**Verse un dividende :** Oui  \n"
                    f"**Rendement :** {yield_txt}  \n"
                    f"**Fréquence :** {freq}  \n"
                    f"**Tendance :** {trend}  \n"
                    f"**Montant annuel :** {div_amt_txt}  \n"
                    f"**Taux de distribution :** {payout_txt}"
                )

                if not hist.empty:
                    st.markdown(
                        '<div class="rf-section-title" style="margin-top:10px">Historique (3 ans)</div>',
                        unsafe_allow_html=True,
                    )
                    hist_display = hist.copy()
                    hist_display["Dividende total"] = hist_display["Dividende total"].map(
                        lambda v: f"{v:.2f} {dev}"
                    )
                    st.dataframe(hist_display, hide_index=True, use_container_width=True,
                                 height=min(180, 52 + 36 * len(hist_display)))
                else:
                    st.info("Historique des dividendes : Donnée non disponible.")

                # Évaluation de la soutenabilité
                payout = f.get("payout") or 0
                if payout and payout > 0.9:
                    st.warning("Soutenabilité fragile : ratio de distribution très élevé.")
                elif y and y > 0.08:
                    st.warning("Rendement très élevé : vigilance sur un possible ajustement.")
                elif payout and payout < 0.6 and trend in ("En croissance", "Stable"):
                    st.success("Dividende apparaissant bien couvert et durable.")
                else:
                    st.caption("Soutenabilité standard : à confirmer avec les prochains résultats.")
            else:
                st.markdown("**Verse un dividende :** Non")
                st.caption("Société ne distribuant pas de dividende actuellement.")

        st.markdown("<hr class='rf-divider'>", unsafe_allow_html=True)

        # Forces / faiblesses / risques
        f_col, w_col, r_col = st.columns(3)
        with f_col:
            st.markdown('<div class="rf-section-title">Forces</div>', unsafe_allow_html=True)
            strengths = []
            if (f.get("marge_op") or 0) > 0.15:
                strengths.append("Marges opérationnelles solides")
            if (f.get("croissance_ca") or 0) > 0.05:
                strengths.append("Croissance du chiffre d'affaires positive")
            if (f.get("dette_eq") or 999) < 60:
                strengths.append("Bilan peu endetté")
            if (f.get("fcf") or 0) > 0:
                strengths.append("Génération de trésorerie positive")
            if (f.get("rendement_div") or 0) > 0.03 and (f.get("payout") or 1) < 0.7:
                strengths.append("Dividende attractif et couvert")
            st.markdown("\n".join([f"- {s}" for s in strengths]) or "- Aucune force majeure identifiée à partir des données.")
        with w_col:
            st.markdown('<div class="rf-section-title">Faiblesses</div>', unsafe_allow_html=True)
            weaks = []
            if (f.get("marge_op") or 1) < 0.05:
                weaks.append("Marges faibles")
            if trends.get("rev_trend") == "en contraction":
                weaks.append("Chiffre d'affaires en contraction")
            if trends.get("eps_trend") == "en dégradation":
                weaks.append("Résultats en dégradation")
            if (f.get("dette_eq") or 0) > 150:
                weaks.append("Endettement élevé")
            if (f.get("payout") or 0) > 0.9:
                weaks.append("Ratio de distribution tendu")
            st.markdown("\n".join([f"- {w}" for w in weaks]) or "- Pas de faiblesse structurelle flagrante.")
        with r_col:
            st.markdown('<div class="rf-section-title">Risques clés</div>', unsafe_allow_html=True)
            risks = []
            if (f.get("beta") or 0) > 1.5:
                risks.append("Volatilité élevée (beta supérieur à 1,5)")
            if ytd < -35:
                risks.append("Momentum très dégradé")
            if score.profile == "piège de valeur":
                risks.append("Profil proche d'un piège de valeur")
            if (f.get("short_ratio") or 0) > 5:
                risks.append("Forte position vendeuse sur le titre")
            risks.append("Risque macro/sectoriel non modélisable")
            st.markdown("\n".join([f"- {r}" for r in risks]))

        # Scénarios bull / base / bear
        st.markdown("<hr class='rf-divider'>", unsafe_allow_html=True)
        st.markdown('<div class="rf-section-title">Scénarios par horizon</div>', unsafe_allow_html=True)
        for horizon, sc in scenarios.items():
            st.markdown(f"**{horizon}**")
            st.markdown(
                f"<div class='rf-scenario rf-scenario-bull'><b>Bull :</b> {sc['bull']}</div>"
                f"<div class='rf-scenario rf-scenario-base'><b>Base :</b> {sc['base']}</div>"
                f"<div class='rf-scenario rf-scenario-bear'><b>Bear :</b> {sc['bear']}</div>",
                unsafe_allow_html=True,
            )

        # News récentes
        if snap.news:
            st.markdown("<hr class='rf-divider'>", unsafe_allow_html=True)
            st.markdown('<div class="rf-section-title">Actualités récentes</div>', unsafe_allow_html=True)
            for n in snap.news[:5]:
                title = n.get("title") or n.get("headline") or ""
                publisher = n.get("publisher") or ""
                link = n.get("link") or "#"
                if title:
                    st.markdown(f"- [{title}]({link}) — *{publisher}*")

        # Justification finale
        st.markdown("<hr class='rf-divider'>", unsafe_allow_html=True)
        st.markdown(
            f"**Recommandation :** {reco_badge(score.recommendation)} &nbsp; {score.justification}",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Construction du panel complet et du tableau principal
# ---------------------------------------------------------------------------

def build_panel(threshold: float, universe: list, limit: int | None) -> pd.DataFrame:
    """Construit le panel complet des sociétés analysées.

    Non caché : utilise les fonctions cachées sous-jacentes (screen + fetch_company).
    Si `limit` est None, toutes les sociétés en baisse sont analysées.
    """
    screen = screen_decliners(threshold, list(universe))
    if screen.empty:
        return screen
    if limit is not None:
        screen = screen.head(limit)

    rows = []
    total = len(screen)
    progress = st.progress(
        0.0,
        text=f"Analyse de {total} sociétés — premier chargement ~1-2 min, puis instantané (cache)…",
    )

    def _process(row):
        tk = row["ticker"]
        analysis = analyze_company(tk, float(row["ytd_perf"]))
        f = analysis["fund"]
        s = analysis["score"]
        return {
            "Ticker": tk,
            "Société": f["nom"],
            "Secteur": f["secteur"],
            "Pays": f["pays"],
            "YTD %": row["ytd_perf"],
            "Prix": f.get("prix") or row["last_price"],
            "Capi.": fmt_large(f.get("market_cap")),
            "Dividende": f.get("rendement_div"),
            "Score": s.total,
            "Risque": s.risk_level,
            "Conviction": s.conviction,
            "Profil": s.profile,
            "Recommandation": s.recommendation,
        }

    # Parallélisation I/O bound (yfinance) avec un pool modéré pour éviter le rate-limit
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(_process, row): row for _, row in screen.iterrows()}
        done = 0
        for future in as_completed(futures):
            try:
                rows.append(future.result())
            except Exception:
                pass
            done += 1
            progress.progress(
                min(done / max(total, 1), 1.0),
                text=f"Analyse en cours — {done}/{total} sociétés traitées",
            )
    progress.empty()
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows).sort_values("Score", ascending=False).reset_index(drop=True)
    return df


# ---------------------------------------------------------------------------
# Classements
# ---------------------------------------------------------------------------

def render_rankings(df: pd.DataFrame):
    st.markdown("### Classements")
    if df.empty:
        st.info("Pas assez de données pour générer des classements.")
        return

    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="rf-section-title">Top 10 opportunités</div>', unsafe_allow_html=True)
        top = df.sort_values("Score", ascending=False).head(10)
        render_main_table(top[["Ticker", "Société", "Secteur", "YTD %", "Score", "Recommandation"]])

        st.markdown('<div class="rf-section-title">Top 5 — survente, meilleur rapport risque/récompense</div>',
                    unsafe_allow_html=True)
        over = df[(df["YTD %"] <= -30) & (df["Risque"] != "élevé")].sort_values("Score", ascending=False).head(5)
        render_main_table(over[["Ticker", "Société", "YTD %", "Score", "Profil", "Recommandation"]])

    with col2:
        st.markdown('<div class="rf-section-title">Top 5 situations à haut risque</div>', unsafe_allow_html=True)
        risky = df[df["Risque"] == "élevé"].sort_values("Score").head(5)
        render_main_table(risky[["Ticker", "Société", "YTD %", "Score", "Risque", "Recommandation"]])

        st.markdown('<div class="rf-section-title">Top 5 pièges de valeur potentiels</div>', unsafe_allow_html=True)
        traps = df[df["Profil"] == "piège de valeur"].sort_values("Score").head(5)
        if traps.empty:
            st.caption("Aucun piège de valeur clairement identifié dans l'univers courant.")
        else:
            render_main_table(traps[["Ticker", "Société", "YTD %", "Score", "Profil", "Recommandation"]])


# ---------------------------------------------------------------------------
# Portefeuille modèle
# ---------------------------------------------------------------------------

def render_model_portfolio(df: pd.DataFrame):
    st.markdown("### Portefeuille modèle")
    buys = df[df["Recommandation"] == "ACHAT"].sort_values("Score", ascending=False)
    if buys.empty:
        st.info("Aucune position ACHAT identifiée dans l'univers filtré. Le portefeuille reste en cash.")
        return

    top = buys.head(8).copy()

    # Allocation : pondération proportionnelle au score, plafonnée à 15%
    weights = top["Score"].astype(float)
    weights = weights / weights.sum()
    weights = weights.clip(upper=0.15)
    weights = weights / weights.sum() * 0.85  # on laisse 15% de cash
    top["Poids"] = weights.values

    cash_row = pd.DataFrame([{
        "Ticker": "CASH", "Société": "Liquidités", "Secteur": "—",
        "YTD %": 0, "Score": None, "Risque": "faible",
        "Profil": "défensif", "Recommandation": "—", "Poids": 0.15,
    }])

    portfolio = pd.concat([top, cash_row], ignore_index=True)

    col1, col2 = st.columns([3, 2])
    with col1:
        display = portfolio[["Ticker", "Société", "Secteur", "Profil", "Risque", "Poids"]].copy()
        display["Poids"] = display["Poids"].map(lambda x: f"{x * 100:.1f}%")
        st.dataframe(display, hide_index=True, use_container_width=True, height=400)

        st.markdown(
            '<div class="rf-section-title">Logique d\'allocation</div>'
            "Pondérations proportionnelles au score global, plafonnées à 15% par ligne afin de "
            "limiter la concentration. Une poche de liquidités de 15% est conservée pour absorber "
            "les chocs de marché et saisir d'éventuels points d'entrée supplémentaires.  \n"
            "L'objectif est un équilibre entre **profils value / qualité décotée** et **retournements** "
            "ciblés, tout en excluant les situations classées *piège de valeur*.",
            unsafe_allow_html=True,
        )
    with col2:
        fig = go.Figure(go.Pie(
            labels=portfolio["Ticker"], values=portfolio["Poids"],
            hole=0.55, textinfo="label+percent",
            marker=dict(colors=[
                COLORS["accent"], COLORS["bull"], COLORS["watch"], "#8C6BD8",
                "#4FB2B5", "#D6748D", "#6FA65A", "#C08457", COLORS["muted"],
            ]),
        ))
        fig.update_layout(
            height=380, margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor=COLORS["surface"], plot_bgcolor=COLORS["surface"],
            font=dict(color=COLORS["text"], size=12),
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------------------
# Programme principal
# ---------------------------------------------------------------------------

def main():
    controls = sidebar_controls()

    render_header(
        "Analyse sélective des valeurs en forte baisse YTD — "
        "scoring fondamental, technique et qualitatif."
    )

    tabs = st.tabs([
        "Contexte de marché",
        "Tableau comparatif",
        "Fiches sociétés",
        "Classements",
        "Portefeuille modèle",
    ])

    # Onglet 1 — Contexte de marché
    with tabs[0]:
        render_market_context()

    # Chargement du panel
    df = build_panel(controls["threshold"], controls["universe"], controls["limit"])

    # Onglet 2 — Tableau comparatif
    with tabs[1]:
        st.markdown("### Vue synthétique")
        if df.empty:
            st.warning(
                "Aucune société de l'univers ne remplit le critère de baisse minimale actuellement. "
                "Assouplissez le seuil ou élargissez la zone géographique."
            )
        else:
            # KPIs de synthèse
            avg_drop = df["YTD %"].mean()
            avg_score = df["Score"].mean()
            kpi_row([
                ("Sociétés analysées", f"{len(df)}", f"Univers : {len(controls['universe'])}"),
                ("Repli moyen YTD", f"{avg_drop:+.1f}%", ""),
                ("Score moyen", f"{avg_score:.1f}/100", ""),
                (
                    "Répartition des avis",
                    f"{(df['Recommandation'] == 'ACHAT').sum()} / "
                    f"{(df['Recommandation'] == 'SURVEILLANCE').sum()} / "
                    f"{(df['Recommandation'] == 'ÉVITER').sum()}",
                    "ACHAT / SURVEILLANCE / ÉVITER",
                ),
            ])
            st.markdown("<br>", unsafe_allow_html=True)

            # Filtres sur le tableau
            c1, c2, c3 = st.columns(3)
            with c1:
                recos = st.multiselect("Recommandation",
                                       options=sorted(df["Recommandation"].unique()),
                                       default=sorted(df["Recommandation"].unique()))
            with c2:
                secteurs = st.multiselect("Secteur",
                                          options=sorted(df["Secteur"].dropna().unique()),
                                          default=sorted(df["Secteur"].dropna().unique()))
            with c3:
                risques = st.multiselect("Niveau de risque",
                                         options=sorted(df["Risque"].unique()),
                                         default=sorted(df["Risque"].unique()))

            filtered = df[
                df["Recommandation"].isin(recos)
                & df["Secteur"].isin(secteurs)
                & df["Risque"].isin(risques)
            ]
            render_main_table(filtered)

    # Onglet 3 — Fiches détaillées
    with tabs[2]:
        st.markdown("### Fiches sociétés")
        if df.empty:
            st.info("Aucune société à afficher.")
        else:
            selected = st.selectbox(
                "Choisir une société",
                options=df["Ticker"].tolist(),
                format_func=lambda t: f"{t} — {df.loc[df['Ticker'] == t, 'Société'].iloc[0]}",
            )
            row = df[df["Ticker"] == selected].iloc[0]
            analysis = analyze_company(selected, float(row["YTD %"]))
            render_company_card(analysis)

    # Onglet 4 — Classements
    with tabs[3]:
        render_rankings(df)

    # Onglet 5 — Portefeuille modèle
    with tabs[4]:
        render_model_portfolio(df)

    st.markdown(
        f"<hr style='border-top:1px solid {COLORS['border']}; margin-top:40px;'>"
        f"<p style='color:{COLORS['muted']}; font-size:11px; text-align:center;'>"
        "Source : Yahoo Finance via yfinance. Données à titre informatif uniquement. "
        "Ce tableau de bord ne constitue pas un conseil en investissement."
        "</p>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
