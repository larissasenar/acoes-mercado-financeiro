import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.express as px
from datetime import datetime
from streamlit_extras.metric_cards import style_metric_cards
from streamlit_extras.grid import grid

st.set_page_config(layout="wide")

def build_sidebar():
    st.markdown("# 📈 Projeto em Python para Investidores")

    df = pd.read_csv("tickers_ibra_corrigido.csv")
    df["label"] = df["empresa"] + " (" + df["ticker"] + ")"
    selected_labels = st.multiselect("Selecione as Empresas", options=df["label"], placeholder="Códigos")

    selected_tickers = [label.split("(")[-1].replace(")", "") for label in selected_labels]
    tickers = [t + ".SA" for t in selected_tickers]

    # Tipo de preço fixo como "Close"
    price_col = "Close"

    start_date = st.date_input("De", format="DD/MM/YYYY", value=datetime(2023, 1, 2))
    end_date = st.date_input("Até", format="DD/MM/YYYY", value=datetime.today())

    if start_date > end_date:
        st.error("Data inicial não pode ser maior que a data final.")
        return None, None, None

    if tickers:
        df_prices = yf.download(tickers, start=start_date, end=end_date)

        if isinstance(df_prices.columns, pd.MultiIndex):
            if price_col in df_prices.columns.levels[0]:
                prices = df_prices[price_col].copy()
            else:
                st.error(f"Coluna '{price_col}' não disponível nos dados.")
                return None, None, None
        else:
            if price_col in df_prices.columns:
                prices = df_prices[[price_col]].copy()
                prices.columns = [selected_tickers[0]]
            else:
                st.error(f"Coluna '{price_col}' não disponível nos dados.")
                return None, None, None

        prices.columns = [col.rstrip(".SA") for col in prices.columns]

        try:
            ibov = yf.download("^BVSP", start=start_date, end=end_date)[price_col]
            prices["IBOV"] = ibov
        except Exception:
            st.warning("Não foi possível carregar o IBOV.")
            prices["IBOV"] = np.nan

        return selected_tickers, prices, price_col

    return None, None, None

def build_main(tickers, prices):
    st.header("🧮 Pesos Personalizados")

    weights = {}
    total_weight = 0

    for ticker in tickers:
        w = st.slider(f"Peso de {ticker}", 0.0, 1.0, value=1.0/len(tickers), step=0.01)
        weights[ticker] = w
        total_weight += w

    weights_array = np.array([weights[t] for t in tickers])
    if total_weight > 0:
        weights_array /= total_weight

    carteira = prices[tickers] @ weights_array
    prices["portfolio"] = carteira

    norm_prices = 100 * prices / prices.iloc[0]
    returns = prices.pct_change().dropna()
    vols = returns.std() * np.sqrt(252)
    rets = (norm_prices.iloc[-1] - 100) / 100

    mygrid = grid(5, 5, 5, 5, 5, 5, vertical_align="top")
    for t in prices.columns:
        c = mygrid.container(border=True)
        c.subheader(t, divider="red")
        colA, colB, colC = c.columns(3)
        if t == "portfolio":
            colA.image("images/pie-chart-dollar-svgrepo-com.svg")
        elif t == "IBOV":
            colA.image("images/pie-chart-svgrepo-com.svg")
        else:
            colA.image(f"https://raw.githubusercontent.com/thefintz/icones-b3/main/icones/{t}.png", width=85)
        colB.metric(label="Retorno", value=f"{rets[t]:.0%}")
        colC.metric(label="Volatilidade", value=f"{vols[t]:.0%}")
        style_metric_cards(background_color="rgba(255,255,255,0)")

    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.subheader("📈 Desempenho Relativo")
        st.line_chart(norm_prices, height=600)

    with col2:
        st.subheader("📉 Risco-Retorno")
        fig = px.scatter(
            x=vols,
            y=rets,
            text=vols.index,
            color=rets / vols,
            color_continuous_scale=px.colors.sequential.Bluered_r,
        )
        fig.update_traces(textfont_color="white", marker=dict(size=45), textfont_size=10)
        fig.update_layout(
            height=600,
            xaxis_title="Volatilidade (anualizada)",
            yaxis_title="Retorno Total",
            xaxis_tickformat=".0%",
            yaxis_tickformat=".0%",
            coloraxis_colorbar_title="Sharpe",
        )
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("📋 Tabela de Retornos Acumulados")
    tabela = pd.DataFrame({
        "Retorno (%)": (norm_prices.iloc[-1] / norm_prices.iloc[0] - 1) * 100
    }).round(2)
    st.dataframe(tabela)

# Executa app
with st.sidebar:
    tickers, prices, price_col = build_sidebar()

st.title("📊 Python para Investidores")
if tickers and prices is not None:
    build_main(tickers, prices)
else:
    st.info("Use a barra lateral para selecionar as ações.")
