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
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@500&display=swap" rel="stylesheet">
        <style>
        html, body, [class*="css"], .stApp, .stMarkdown, p, span, label, div, li, a {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
        }}
        .stApp {{
            background: radial-gradient(1200px 600px at 10% -10%, #0F1624 0%, {COLORS['bg']} 55%) !important;
            color: {COLORS['text']};
        }}
        .block-container {{
            padding-top: 1.4rem;
            padding-bottom: 4rem;
            max-width: 1480px;
        }}
        header[data-testid="stHeader"] {{ background: transparent; }}

        /* Typographie */
        h1, h2, h3, h4, h5 {{
            color: {COLORS['text']} !important;
            font-weight: 600 !important;
            letter-spacing: -0.015em !important;
        }}
        h1 {{ font-size: 28px !important; }}
        h2 {{ font-size: 20px !important; }}
        h3 {{ font-size: 17px !important; }}
        p, span, label, li {{
            color: {COLORS['text']} !important;
            font-size: 14px;
            line-height: 1.6;
        }}
        strong, b {{ color: {COLORS['text']} !important; font-weight: 600; }}
        a {{ color: {COLORS['accent']} !important; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}

        /* Sidebar */
        section[data-testid="stSidebar"] > div {{
            background: {COLORS['surface']};
            border-right: 1px solid {COLORS['border']};
        }}
        section[data-testid="stSidebar"] * {{ color: {COLORS['text']} !important; }}

        /* En-tête premium */
        .rf-header {{
            padding: 30px 34px;
            border-radius: 18px;
            background:
                radial-gradient(800px 300px at 100% 0%, rgba(91,157,255,0.15) 0%, transparent 70%),
                linear-gradient(135deg, #141B2C 0%, #1A2436 60%, #0F1624 100%);
            border: 1px solid {COLORS['border']};
            margin-bottom: 24px;
            box-shadow: 0 2px 30px rgba(0,0,0,0.25);
        }}
        .rf-header h1 {{ margin: 0 0 6px 0 !important; color: #FFFFFF !important; }}
        .rf-header p {{ color: {COLORS['muted']} !important; margin: 0 !important; font-size: 14px; }}
        .rf-header-accent {{ color: {COLORS['accent']} !important; font-size: 13px; margin-top: 12px !important; }}

        /* KPI cards */
        .rf-kpi {{
            padding: 18px 20px;
            border-radius: 14px;
            background: {COLORS['surface']};
            border: 1px solid {COLORS['border']};
            height: 100%;
            transition: border-color 0.2s ease, transform 0.2s ease;
        }}
        .rf-kpi:hover {{ border-color: {COLORS['accent']}; transform: translateY(-1px); }}
        .rf-kpi-label {{
            color: {COLORS['muted']} !important;
            font-size: 11px; text-transform: uppercase;
            letter-spacing: 0.1em; margin-bottom: 8px; font-weight: 500;
        }}
        .rf-kpi-value {{
            color: #FFFFFF !important; font-size: 26px; font-weight: 700;
            font-family: 'Inter', sans-serif !important; letter-spacing: -0.02em;
        }}
        .rf-kpi-sub {{
            color: {COLORS['muted']} !important; font-size: 12px; margin-top: 6px;
        }}

        /* Badges recommandation */
        .rf-badge {{
            display: inline-block;
            padding: 6px 14px;
            border-radius: 8px;
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            box-shadow: 0 2px 6px rgba(0,0,0,0.2);
        }}

        /* Cartes principales */
        .rf-card {{
            padding: 26px;
            border-radius: 16px;
            background: {COLORS['surface']};
            border: 1px solid {COLORS['border']};
            margin-bottom: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.2);
        }}

        /* Sous-titres de section */
        .rf-section-title {{
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            color: {COLORS['muted']} !important;
            margin: 2px 0 12px 0;
            font-weight: 600;
        }}
        .rf-divider {{
            border: none; border-top: 1px solid {COLORS['border']}; margin: 18px 0;
        }}

        /* Pills */
        .rf-pill {{
            display: inline-block;
            padding: 4px 11px;
            border-radius: 8px;
            background: {COLORS['surface_2']};
            border: 1px solid {COLORS['border']};
            color: {COLORS['text']} !important;
            font-size: 12px;
            margin-right: 6px;
            margin-bottom: 4px;
            font-weight: 500;
        }}

        /* Tableaux */
        [data-testid="stDataFrame"] {{
            border-radius: 12px;
            border: 1px solid {COLORS['border']};
            overflow: hidden;
        }}
        [data-testid="stDataFrame"] * {{ color: {COLORS['text']} !important; }}

        /* Onglets */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 4px;
            background: {COLORS['surface']};
            padding: 6px;
            border-radius: 12px;
            border: 1px solid {COLORS['border']};
        }}
        .stTabs [data-baseweb="tab"] {{
            background: transparent;
            color: {COLORS['muted']} !important;
            border-radius: 8px;
            padding: 8px 18px;
            font-weight: 500;
        }}
        .stTabs [aria-selected="true"] {{
            background: {COLORS['accent']} !important;
            color: #FFFFFF !important;
        }}

        /* Scénarios */
        .rf-scenario {{
            padding: 12px 16px;
            border-radius: 10px;
            background: {COLORS['surface_2']};
            border: 1px solid {COLORS['border']};
            margin-bottom: 8px;
            color: {COLORS['text']} !important;
        }}
        .rf-scenario b {{ color: #FFFFFF !important; }}
        .rf-scenario-bull {{ border-left: 3px solid {COLORS['bull']}; }}
        .rf-scenario-base {{ border-left: 3px solid {COLORS['accent']}; }}
        .rf-scenario-bear {{ border-left: 3px solid {COLORS['bear']}; }}

        /* Inputs */
        input, textarea, select, .stSelectbox > div, .stMultiSelect > div {{
            background: {COLORS['surface_2']} !important;
            color: {COLORS['text']} !important;
            border: 1px solid {COLORS['border']} !important;
        }}

        /* Alertes */
        [data-testid="stAlert"] {{
            background: {COLORS['surface']} !important;
            border: 1px solid {COLORS['border']} !important;
            color: {COLORS['text']} !important;
        }}
        [data-testid="stAlert"] * {{ color: {COLORS['text']} !important; }}

        /* Barre de progression */
        .stProgress > div > div {{ background: {COLORS['accent']} !important; }}

        /* Expander / boutons secondaires */
        .stExpander {{ background: {COLORS['surface']} !important; border: 1px solid {COLORS['border']}; border-radius: 12px; }}

        /* Caption doit rester lisible */
        [data-testid="stCaptionContainer"], .st-emotion-cache-1wmy9hl {{
            color: {COLORS['muted']} !important;
        }}

        /* Scrollbar sobre */
        ::-webkit-scrollbar {{ width: 10px; height: 10px; }}
        ::-webkit-scrollbar-track {{ background: {COLORS['bg']}; }}
        ::-webkit-scrollbar-thumb {{ background: {COLORS['border']}; border-radius: 6px; }}
        ::-webkit-scrollbar-thumb:hover {{ background: {COLORS['muted']}; }}
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

def render_main_table(df: pd.DataFrame, page_size: int = 25):
    """Tableau comparatif stylisé avec tri, filtrage, pagination et barres de progression."""
    if df.empty:
        st.info("Aucune société ne correspond aux filtres.")
        return

    # Pagination pour grands datasets
    total = len(df)
    if total > page_size:
        nb_pages = (total - 1) // page_size + 1
        page = st.number_input(
            f"Page (sur {nb_pages}) — {total} lignes",
            min_value=1, max_value=nb_pages, value=1, step=1,
            key=f"page_{id(df)}",
        )
        start = (page - 1) * page_size
        end = start + page_size
        view = df.iloc[start:end].copy()
    else:
        view = df.copy()

    # Column config — rendus natifs Streamlit (contraste parfait, tri auto)
    config = {}
    if "YTD %" in view.columns:
        config["YTD %"] = st.column_config.NumberColumn("YTD %", format="%+.1f %%", width="small")
    if "Prix" in view.columns:
        config["Prix"] = st.column_config.NumberColumn("Prix", format="%.2f", width="small")
    if "Dividende" in view.columns:
        # Transformer en % lisible ou "N/D"
        def _div_fmt(x):
            if x is None or (isinstance(x, float) and pd.isna(x)) or x == 0:
                return None
            return float(x) * 100
        view["Dividende"] = view["Dividende"].map(_div_fmt)
        config["Dividende"] = st.column_config.NumberColumn("Rendement div.", format="%.2f %%", width="small")
    if "Score" in view.columns:
        config["Score"] = st.column_config.ProgressColumn(
            "Score /100", format="%.0f", min_value=0, max_value=100, width="medium",
        )
    if "Recommandation" in view.columns:
        config["Recommandation"] = st.column_config.TextColumn("Avis", width="small")

    height = min(700, 52 + 36 * len(view))

    st.dataframe(
        view,
        column_config=config,
        hide_index=True,
        use_container_width=True,
        height=height,
    )
