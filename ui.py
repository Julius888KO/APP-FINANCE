"""
Composants d'interface réutilisables : en-tête, cartes KPI, badges,
graphiques Plotly, tableaux stylisés.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config import APP_TITLE, APP_SUBTITLE, BADGE_STYLE, COLORS


# ---------------------------------------------------------------------------
# Feuille de style globale
# ---------------------------------------------------------------------------

def inject_css():
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-color: {COLORS['bg']};
        }}
        .block-container {{
            padding-top: 1.5rem;
            padding-bottom: 4rem;
            max-width: 1400px;
        }}
        header[data-testid="stHeader"] {{
            background: transparent;
        }}
        h1, h2, h3, h4 {{
            color: {COLORS['text']};
            letter-spacing: -0.01em;
        }}
        p, span, label, div {{
            color: {COLORS['text']};
        }}
        .rf-header {{
            padding: 26px 28px;
            border-radius: 14px;
            background: linear-gradient(135deg, #111827 0%, #1a2332 60%, #0f1d2e 100%);
            border: 1px solid {COLORS['border']};
            margin-bottom: 22px;
        }}
        .rf-header h1 {{
            font-size: 28px; margin: 0 0 4px 0; font-weight: 600;
        }}
        .rf-header p {{
            color: {COLORS['muted']}; margin: 0; font-size: 14px;
        }}
        .rf-kpi {{
            padding: 16px 18px;
            border-radius: 12px;
            background: {COLORS['surface']};
            border: 1px solid {COLORS['border']};
            height: 100%;
        }}
        .rf-kpi-label {{
            color: {COLORS['muted']}; font-size: 12px; text-transform: uppercase;
            letter-spacing: 0.08em; margin-bottom: 6px;
        }}
        .rf-kpi-value {{
            color: {COLORS['text']}; font-size: 24px; font-weight: 600;
        }}
        .rf-kpi-sub {{
            color: {COLORS['muted']}; font-size: 12px; margin-top: 4px;
        }}
        .rf-badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 600;
            letter-spacing: 0.04em;
        }}
        .rf-card {{
            padding: 22px;
            border-radius: 14px;
            background: {COLORS['surface']};
            border: 1px solid {COLORS['border']};
            margin-bottom: 18px;
        }}
        .rf-section-title {{
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: {COLORS['muted']};
            margin: 4px 0 10px 0;
        }}
        .rf-divider {{
            border: none; border-top: 1px solid {COLORS['border']}; margin: 14px 0;
        }}
        .rf-pill {{
            display: inline-block;
            padding: 3px 10px;
            border-radius: 8px;
            background: #1f2733;
            color: {COLORS['muted']};
            font-size: 12px;
            margin-right: 6px;
        }}
        .stDataFrame, .stTable {{
            border-radius: 10px;
        }}
        [data-testid="stMetricValue"] {{
            color: {COLORS['text']};
        }}
        .rf-scenario {{
            padding: 12px 14px;
            border-radius: 10px;
            background: #11161D;
            border: 1px solid {COLORS['border']};
            margin-bottom: 8px;
        }}
        .rf-scenario-bull {{ border-left: 3px solid {COLORS['bull']}; }}
        .rf-scenario-base {{ border-left: 3px solid {COLORS['neutral']}; }}
        .rf-scenario-bear {{ border-left: 3px solid {COLORS['bear']}; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# En-tête
# ---------------------------------------------------------------------------

def render_header(market_snapshot: str = ""):
    st.markdown(
        f"""
        <div class="rf-header">
            <h1>{APP_TITLE}</h1>
            <p>{APP_SUBTITLE}</p>
            {f'<p style="margin-top:10px;color:{COLORS["accent"]};font-size:13px;">{market_snapshot}</p>' if market_snapshot else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Cartes KPI
# ---------------------------------------------------------------------------

def kpi_card(label: str, value: str, sub: str = ""):
    st.markdown(
        f"""
        <div class="rf-kpi">
            <div class="rf-kpi-label">{label}</div>
            <div class="rf-kpi-value">{value}</div>
            <div class="rf-kpi-sub">{sub}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def kpi_row(kpis: list[tuple[str, str, str]]):
    cols = st.columns(len(kpis))
    for col, (label, value, sub) in zip(cols, kpis):
        with col:
            kpi_card(label, value, sub)


# ---------------------------------------------------------------------------
# Badges et pills
# ---------------------------------------------------------------------------

def reco_badge(reco: str) -> str:
    style = BADGE_STYLE.get(reco, {"bg": "#1f2733", "fg": COLORS["muted"]})
    return (
        f'<span class="rf-badge" style="background:{style["bg"]};color:{style["fg"]};">{reco}</span>'
    )


def pill(text: str) -> str:
    return f'<span class="rf-pill">{text}</span>'


# ---------------------------------------------------------------------------
# Graphiques Plotly
# ---------------------------------------------------------------------------

def _apply_layout(fig: go.Figure, height: int = 340, title: str | None = None) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=40 if title else 15, b=10),
        paper_bgcolor=COLORS["surface"],
        plot_bgcolor=COLORS["surface"],
        font=dict(color=COLORS["text"], size=12),
        title=dict(text=title, font=dict(size=14, color=COLORS["text"])) if title else None,
        xaxis=dict(gridcolor=COLORS["border"], showspikes=False),
        yaxis=dict(gridcolor=COLORS["border"]),
        legend=dict(orientation="h", y=-0.15, x=0),
    )
    return fig


def price_chart(history: pd.DataFrame, sma50=None, sma200=None, support=None, resistance=None) -> go.Figure:
    fig = go.Figure()
    close = history["Close"].dropna()
    fig.add_trace(go.Scatter(
        x=close.index, y=close.values, name="Cours",
        line=dict(color=COLORS["accent"], width=2),
        fill="tozeroy", fillcolor="rgba(76,154,255,0.06)",
    ))
    if sma50 is not None and len(close) >= 50:
        s50 = close.rolling(50, min_periods=10).mean()
        fig.add_trace(go.Scatter(
            x=s50.index, y=s50.values, name="MM50",
            line=dict(color=COLORS["bull"], width=1.2, dash="dot"),
        ))
    if sma200 is not None and len(close) >= 60:
        s200 = close.rolling(200, min_periods=30).mean()
        fig.add_trace(go.Scatter(
            x=s200.index, y=s200.values, name="MM200",
            line=dict(color=COLORS["watch"], width=1.2, dash="dash"),
        ))
    if support:
        fig.add_hline(y=support, line_dash="dot", line_color=COLORS["bull"],
                      annotation_text=f"Support {support:.2f}", annotation_position="bottom right")
    if resistance:
        fig.add_hline(y=resistance, line_dash="dot", line_color=COLORS["bear"],
                      annotation_text=f"Résistance {resistance:.2f}", annotation_position="top right")
    return _apply_layout(fig, height=360)


def score_gauge(total: float) -> go.Figure:
    color = COLORS["buy"] if total >= 65 else COLORS["watch"] if total >= 45 else COLORS["avoid"]
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=total,
        number=dict(suffix=" /100", font=dict(size=26, color=COLORS["text"])),
        gauge=dict(
            axis=dict(range=[0, 100], tickcolor=COLORS["muted"]),
            bar=dict(color=color, thickness=0.3),
            bgcolor=COLORS["surface"],
            borderwidth=0,
            steps=[
                {"range": [0, 40], "color": "#2a1616"},
                {"range": [40, 65], "color": "#2a2416"},
                {"range": [65, 100], "color": "#16291f"},
            ],
        ),
    ))
    return _apply_layout(fig, height=220)


def score_breakdown(score) -> go.Figure:
    labels = ["Valorisation", "Fondamentaux", "Bilan", "Dividende", "Technique", "Catalyseurs", "Risque/Récompense"]
    values = [score.valuation, score.fundamental, score.balance, score.dividend,
              score.technical, score.catalyst, score.risk_reward]
    maxes = [20, 20, 15, 10, 15, 10, 10]
    pct = [v / m * 100 for v, m in zip(values, maxes)]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=labels, x=pct, orientation="h",
        marker=dict(color=COLORS["accent"]),
        text=[f"{v:.1f}/{m}" for v, m in zip(values, maxes)],
        textposition="auto",
    ))
    fig.update_xaxes(range=[0, 110], showticklabels=False)
    return _apply_layout(fig, height=280)


# ---------------------------------------------------------------------------
# Tableau principal
# ---------------------------------------------------------------------------

def render_main_table(df: pd.DataFrame):
    """Tableau comparatif stylisé avec tri/filtrage."""
    if df.empty:
        st.info("Aucune société ne correspond aux filtres.")
        return

    styled = df.copy()
    # Formatage
    if "YTD %" in styled:
        styled["YTD %"] = styled["YTD %"].map(lambda x: f"{x:+.1f}%" if pd.notna(x) else "N/D")
    if "Prix" in styled:
        styled["Prix"] = styled["Prix"].map(lambda x: f"{x:,.2f}" if pd.notna(x) else "N/D")
    if "Dividende" in styled:
        styled["Dividende"] = styled["Dividende"].map(
            lambda x: f"{x * 100:.2f}%" if isinstance(x, (int, float)) and pd.notna(x) and x > 0 else "—"
        )
    if "Score" in styled:
        styled["Score"] = styled["Score"].map(lambda x: f"{x:.0f}")

    st.dataframe(
        styled,
        hide_index=True,
        use_container_width=True,
        height=min(600, 48 + 35 * len(styled)),
    )
